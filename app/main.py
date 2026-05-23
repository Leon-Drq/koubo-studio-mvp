from __future__ import annotations

import mimetypes
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.jobs import PipelineRunner
from app.models import CreateJobResponse, JobInputs, JobRecord
from app.storage import JobStore
from app.services.downloader import download_video
from app.services.media import extract_audio
from app.services.asr import transcribe_audio
from app.services.llm import rewrite_script

executor = ThreadPoolExecutor(max_workers=2)
app = FastAPI(title="Koubo Studio MVP")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


def extract_first_url(text: str) -> str:
    match = re.search(r"https?://\S+", text)
    if not match:
        return ""
    return match.group(0).rstrip("，。；;、,.!！?？)）]】\"'")


def get_store(settings: Settings = Depends(get_settings)) -> JobStore:
    return JobStore(settings)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/api/health")
def health(settings: Settings = Depends(get_settings)) -> dict[str, object]:
    return {
        "ok": True,
        "app": settings.app_name,
        "adapters": {
            "asr": {"local": bool(settings.asr_command), "api": bool(settings.asr_api_url), "default": settings.default_asr_provider},
            "llm": {"local": bool(settings.llm_command), "api": bool(settings.llm_api_url), "default": settings.default_llm_provider},
            "tts": {
                "local": bool(settings.tts_command or settings.f5_tts_command or settings.indextts_command),
                "api": bool(settings.tts_api_url),
                "default": settings.default_tts_provider,
            },
            "tts_models": {
                "default": settings.default_tts_model,
                "f5": bool(settings.f5_tts_command or settings.tts_command),
                "indextts2": bool(settings.indextts_command),
            },
            "lipsync": {
                "local": bool(settings.lipsync_command),
                "latentsync": bool(settings.latentsync_command),
                "api": bool(settings.lipsync_api_url),
                "default": settings.default_lipsync_provider,
                "musetalk_batch_size": settings.musetalk_batch_size,
                "musetalk_bbox_shift": settings.musetalk_bbox_shift,
            },
        },
    }


@app.post("/api/jobs", response_model=CreateJobResponse)
def create_job(
    background_tasks: BackgroundTasks,
    competitor_url: str = Form(""),
    source_text: str = Form(""),
    product_brief: str = Form(""),
    tone: str = Form("电商口播"),
    voice_name: str = Form("default"),
    asr_provider: str = Form("auto"),
    llm_provider: str = Form("auto"),
    tts_provider: str = Form("auto"),
    tts_model: str = Form("f5"),
    lipsync_provider: str = Form("auto"),
    musetalk_batch_size: int = Form(8),
    musetalk_bbox_shift: int = Form(0),
    platforms: str = Form("local"),
    competitor_file: Optional[UploadFile] = File(None),
    avatar_video: Optional[UploadFile] = File(None),
    voice_sample: Optional[UploadFile] = File(None),
    bgm_file: Optional[UploadFile] = File(None),
    settings: Settings = Depends(get_settings),
    store: JobStore = Depends(get_store),
) -> CreateJobResponse:
    selected_platforms = [item.strip() for item in platforms.split(",") if item.strip()]
    record = store.create_job(
        JobInputs(
            competitor_url=competitor_url.strip(),
            source_text=source_text.strip(),
            product_brief=product_brief.strip(),
            tone=tone.strip(),
            voice_name=voice_name.strip() or "default",
            asr_provider=asr_provider.strip() or settings.default_asr_provider,
            llm_provider=llm_provider.strip() or settings.default_llm_provider,
            tts_provider=tts_provider.strip() or settings.default_tts_provider,
            tts_model=tts_model.strip() or settings.default_tts_model,
            lipsync_provider=lipsync_provider.strip() or settings.default_lipsync_provider,
            musetalk_batch_size=max(1, min(musetalk_batch_size, 64)),
            musetalk_bbox_shift=max(-30, min(musetalk_bbox_shift, 30)),
            platforms=selected_platforms,
        )
    )
    competitor_path = store.save_upload(record.id, competitor_file, "competitor")
    avatar_path = store.save_upload(record.id, avatar_video, "avatar")
    voice_path = store.save_upload(record.id, voice_sample, "voice_sample")
    bgm_path = store.save_upload(record.id, bgm_file, "bgm")

    runner = PipelineRunner(settings, store)
    background_tasks.add_task(executor.submit, runner.run, record.id, competitor_path, avatar_path, voice_path, bgm_path)
    return CreateJobResponse(id=record.id, status=record.status)


@app.get("/api/jobs", response_model=list[JobRecord])
def list_jobs(store: JobStore = Depends(get_store)) -> list[JobRecord]:
    return store.list_jobs()


@app.get("/api/jobs/{job_id}", response_model=JobRecord)
def get_job(job_id: str, store: JobStore = Depends(get_store)) -> JobRecord:
    try:
        return store.get(job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


@app.get("/api/files/{job_id}/{section}/{filename}")
def get_file(job_id: str, section: str, filename: str, store: JobStore = Depends(get_store)) -> FileResponse:
    if section not in {"inputs", "outputs"}:
        raise HTTPException(status_code=404, detail="File not found")
    path = store.path_for(job_id, section, filename)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@app.post("/api/extract-script")
def extract_script(body: dict, settings: Settings = Depends(get_settings)):
    """从链接中提取口播文案"""
    url = extract_first_url(body.get("url", "").strip())
    if not url:
        raise HTTPException(status_code=400, detail="没有在输入内容中找到可解析的 URL")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # 下载视频
            result = download_video(url, tmpdir_path, settings)
            if not result.video:
                raise HTTPException(status_code=400, detail="Failed to download video from URL")

            # 提取音频
            audio_path = tmpdir_path / "audio.wav"
            extract_audio(result.video, audio_path)

            # 转录音频
            transcript_path = tmpdir_path / "transcript.txt"
            script, provider = transcribe_audio(audio_path, settings, transcript_path, "", "auto")

            return {
                "script": script,
                "title": result.title,
                "description": result.description,
                "provider": provider,
            }
    except HTTPException:
        raise
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        if "Fresh cookies" in detail or "cookies" in detail.lower():
            detail = f"{detail}\n\n抖音需要浏览器 cookies。请导出 douyin.com 的 Netscape cookies.txt，并在 .env 里设置 YTDLP_COOKIES_FILE=你的cookies文件路径。"
        raise HTTPException(status_code=400, detail=f"下载或解析视频失败：{detail}") from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error extracting script: {str(exc)}")


@app.post("/api/rewrite-script")
def rewrite_script_endpoint(body: dict, settings: Settings = Depends(get_settings)):
    """改写口播文案并生成标题话题"""
    source = str(body.get("source_text", "")).strip()
    product_brief = str(body.get("product_brief", "")).strip()
    tone = str(body.get("tone", "电商口播")).strip() or "电商口播"
    provider = str(body.get("provider", settings.default_llm_provider)).strip() or settings.default_llm_provider
    if not source:
        raise HTTPException(status_code=400, detail="请先输入或提取对标文案")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "script.txt"
            script, title, topics, used_provider = rewrite_script(source, settings, output_path, product_brief, tone, provider)
            return {
                "script": script,
                "title": title,
                "topics": topics,
                "provider": used_provider,
            }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"文案改写失败：{str(exc)}")
