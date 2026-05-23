from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    warning = "warning"
    failed = "failed"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class PipelineStep(BaseModel):
    key: str
    label: str
    status: StepStatus = StepStatus.pending
    message: str = ""


class JobInputs(BaseModel):
    competitor_url: str = ""
    source_text: str = ""
    product_brief: str = ""
    tone: str = "电商口播"
    voice_name: str = "default"
    asr_provider: str = "auto"
    llm_provider: str = "auto"
    tts_provider: str = "auto"
    tts_model: str = "f5"
    lipsync_provider: str = "auto"
    musetalk_batch_size: int = 8
    musetalk_bbox_shift: int = 0
    platforms: list[str] = Field(default_factory=list)


class JobArtifacts(BaseModel):
    source_video: Optional[str] = None
    source_audio: Optional[str] = None
    transcript: Optional[str] = None
    rewritten_script: Optional[str] = None
    title: Optional[str] = None
    topics: list[str] = Field(default_factory=list)
    speech_audio: Optional[str] = None
    srt: Optional[str] = None
    lip_sync_video: Optional[str] = None
    final_video: Optional[str] = None
    cover_image: Optional[str] = None
    publish_report: Optional[str] = None


class JobRecord(BaseModel):
    id: str
    status: JobStatus = JobStatus.queued
    created_at: str
    updated_at: str
    inputs: JobInputs
    steps: list[PipelineStep]
    artifacts: JobArtifacts = Field(default_factory=JobArtifacts)
    error: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class CreateJobResponse(BaseModel):
    id: str
    status: JobStatus


class PublishedReport(BaseModel):
    platform: str
    status: str
    message: str


def to_api_path(path: Optional[Union[Path, str]]) -> Optional[str]:
    if not path:
        return None
    return str(path).replace("\\", "/")
