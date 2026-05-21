from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import UploadFile

from app.config import Settings
from app.models import JobInputs, JobRecord, PipelineStep, StepStatus


STEP_DEFS = [
    ("ingest", "素材获取"),
    ("asr", "文案提取"),
    ("rewrite", "AI 改写"),
    ("tts", "语音克隆"),
    ("lipsync", "口型同步"),
    ("edit", "剪辑封面"),
    ("publish", "发布准备"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.root = settings.jobs_dir
        self.root.mkdir(parents=True, exist_ok=True)

    def create_job(self, inputs: JobInputs) -> JobRecord:
        job_id = uuid4().hex[:12]
        job_dir = self.job_dir(job_id)
        (job_dir / "inputs").mkdir(parents=True, exist_ok=True)
        (job_dir / "outputs").mkdir(parents=True, exist_ok=True)
        record = JobRecord(
            id=job_id,
            created_at=now_iso(),
            updated_at=now_iso(),
            inputs=inputs,
            steps=[PipelineStep(key=key, label=label) for key, label in STEP_DEFS],
        )
        self.save(record)
        return record

    def job_dir(self, job_id: str) -> Path:
        return self.root / job_id

    def path_for(self, job_id: str, *parts: str) -> Path:
        path = self.job_dir(job_id).joinpath(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def save_upload(self, job_id: str, upload: Optional[UploadFile], name: str) -> Optional[Path]:
        if not upload or not upload.filename:
            return None
        suffix = Path(upload.filename).suffix or ".bin"
        destination = self.path_for(job_id, "inputs", f"{name}{suffix}")
        with destination.open("wb") as handle:
            shutil.copyfileobj(upload.file, handle)
        return destination

    def get(self, job_id: str) -> JobRecord:
        path = self.path_for(job_id, "job.json")
        return JobRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, record: JobRecord) -> None:
        record.updated_at = now_iso()
        path = self.path_for(record.id, "job.json")
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def list_jobs(self) -> list[JobRecord]:
        jobs: list[JobRecord] = []
        for path in sorted(self.root.glob("*/job.json"), reverse=True):
            try:
                jobs.append(JobRecord.model_validate_json(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return jobs

    def set_step(self, record: JobRecord, key: str, status: StepStatus, message: str = "") -> None:
        for step in record.steps:
            if step.key == key:
                step.status = status
                step.message = message
                break
        self.save(record)
