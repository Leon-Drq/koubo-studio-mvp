from __future__ import annotations

import mimetypes
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

executor = ThreadPoolExecutor(max_workers=2)
app = FastAPI(title="Koubo Studio MVP")
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


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
            "asr": bool(settings.asr_command),
            "llm": bool(settings.llm_command),
            "tts": bool(settings.tts_command),
            "lipsync": bool(settings.lipsync_command),
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
