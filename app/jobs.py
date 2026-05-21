from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Optional

from app.config import Settings
from app.models import JobRecord, JobStatus, StepStatus, to_api_path
from app.services.asr import safe_transcribe
from app.services.downloader import download_video
from app.services.llm import rewrite_script
from app.services.lipsync import render_lipsync
from app.services.media import burn_subtitles, extract_audio, generate_cover
from app.services.publish import prepare_publish_report
from app.services.subtitles import write_srt
from app.services.tts import synthesize_speech
from app.storage import JobStore


def _step_status(provider_message: str, fallback_is_warning: bool = False) -> StepStatus:
    lowered = provider_message.lower()
    if "失败" in provider_message or "未配置" in provider_message or (fallback_is_warning and "fallback" in lowered):
        return StepStatus.warning
    return StepStatus.done


class PipelineRunner:
    def __init__(self, settings: Settings, store: JobStore):
        self.settings = settings
        self.store = store

    def run(self, job_id: str, competitor_file: Optional[Path], avatar_video: Optional[Path], voice_sample: Optional[Path], bgm_file: Optional[Path]) -> None:
        record = self.store.get(job_id)
        record.status = JobStatus.running
        self.store.save(record)
        try:
            self._run(record, competitor_file, avatar_video, voice_sample, bgm_file)
            record.status = JobStatus.completed
            self.store.save(record)
        except Exception as exc:
            record.status = JobStatus.failed
            record.error = str(exc)
            record.meta["traceback"] = traceback.format_exc()
            self.store.save(record)

    def _run(self, record: JobRecord, competitor_file: Optional[Path], avatar_video: Optional[Path], voice_sample: Optional[Path], bgm_file: Optional[Path]) -> None:
        job_dir = self.store.job_dir(record.id)
        inputs_dir = job_dir / "inputs"
        outputs_dir = job_dir / "outputs"

        self.store.set_step(record, "ingest", StepStatus.running, "正在整理素材")
        source_video = competitor_file
        download_title = ""
        download_description = ""
        if not source_video and record.inputs.competitor_url:
            result = download_video(record.inputs.competitor_url, inputs_dir)
            source_video = result.video
            download_title = result.title
            download_description = result.description

        source_audio = None
        if source_video:
            source_audio = outputs_dir / "source.wav"
            extract_audio(source_video, source_audio)
            record.artifacts.source_video = to_api_path(source_video)
            record.artifacts.source_audio = to_api_path(source_audio)
            self.store.set_step(record, "ingest", StepStatus.done, "已获取对标视频和音频")
        else:
            self.store.set_step(record, "ingest", StepStatus.warning, "未获取视频，继续使用文本输入")

        self.store.set_step(record, "asr", StepStatus.running, "正在提取口播文案")
        provided = record.inputs.source_text or download_description or download_title
        transcript_path = outputs_dir / "transcript.txt"
        transcript, asr_provider = safe_transcribe(source_audio, self.settings, transcript_path, provided, record.inputs.asr_provider)
        record.artifacts.transcript = to_api_path(transcript_path)
        self.store.set_step(record, "asr", _step_status(asr_provider), asr_provider)

        self.store.set_step(record, "rewrite", StepStatus.running, "正在改写脚本")
        script_path = outputs_dir / "script.txt"
        script, title, topics, rewrite_provider = rewrite_script(
            transcript,
            self.settings,
            script_path,
            record.inputs.product_brief,
            record.inputs.tone,
            record.inputs.llm_provider,
        )
        record.artifacts.rewritten_script = to_api_path(script_path)
        record.artifacts.title = title
        record.artifacts.topics = topics
        self.store.set_step(record, "rewrite", _step_status(rewrite_provider, True), rewrite_provider)

        self.store.set_step(record, "tts", StepStatus.running, "正在生成口播音频")
        if voice_sample:
            record.meta["voice_sample"] = to_api_path(voice_sample)
        speech_path = outputs_dir / "speech.mp3"
        speech_audio, tts_provider = synthesize_speech(
            script,
            self.settings,
            speech_path,
            record.inputs.voice_name,
            voice_sample,
            record.inputs.tts_provider,
        )
        record.artifacts.speech_audio = to_api_path(speech_audio)
        self.store.set_step(record, "tts", _step_status(tts_provider, True), tts_provider)

        self.store.set_step(record, "lipsync", StepStatus.running, "正在合成口型视频")
        if not avatar_video:
            raise RuntimeError("请上传真人静默视频。")
        lipsync_path = outputs_dir / "lipsync.mp4"
        lip_sync_video, lipsync_provider = render_lipsync(avatar_video, speech_audio, self.settings, lipsync_path, record.inputs.lipsync_provider)
        record.artifacts.lip_sync_video = to_api_path(lip_sync_video)
        self.store.set_step(record, "lipsync", _step_status(lipsync_provider, True), lipsync_provider)

        self.store.set_step(record, "edit", StepStatus.running, "正在生成字幕和封面")
        if bgm_file:
            record.meta["bgm_file"] = to_api_path(bgm_file)
        srt_path = outputs_dir / "subtitles.srt"
        write_srt(script, speech_audio, srt_path)
        record.artifacts.srt = to_api_path(srt_path)

        final_path = outputs_dir / "final.mp4"
        if self.settings.burn_subtitles:
            try:
                burn_subtitles(lip_sync_video, srt_path, final_path)
            except Exception:
                final_path = lip_sync_video
        else:
            final_path = lip_sync_video
        cover_path = outputs_dir / "cover.jpg"
        try:
            generate_cover(final_path, cover_path)
            record.artifacts.cover_image = to_api_path(cover_path)
        except Exception:
            pass
        record.artifacts.final_video = to_api_path(final_path)
        self.store.set_step(record, "edit", StepStatus.done, "已生成成片、字幕和封面")

        self.store.set_step(record, "publish", StepStatus.running, "正在生成发布清单")
        reports = prepare_publish_report(record.inputs.platforms, final_path, title, topics)
        report_path = outputs_dir / "publish_report.json"
        report_path.write_text(json.dumps([item.model_dump() for item in reports], ensure_ascii=False, indent=2), encoding="utf-8")
        record.artifacts.publish_report = to_api_path(report_path)
        record.meta["publish"] = [item.model_dump() for item in reports]
        self.store.set_step(record, "publish", StepStatus.done, "已生成发布清单")
