from __future__ import annotations

import re
from pathlib import Path

from app.services.media import ffprobe_duration


def _split_script(script: str) -> list[str]:
    pieces = re.split(r"(?<=[。！？!?])\s*|\n+", script)
    return [piece.strip() for piece in pieces if piece.strip()]


def _fmt_time(seconds: float) -> str:
    ms = int((seconds - int(seconds)) * 1000)
    whole = int(seconds)
    s = whole % 60
    m = (whole // 60) % 60
    h = whole // 3600
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def write_srt(script: str, audio_path: Path, output: Path) -> Path:
    parts = _split_script(script)
    duration = ffprobe_duration(audio_path) or max(len(script) / 5.2, 8.0)
    slot = duration / max(len(parts), 1)
    lines: list[str] = []
    for idx, text in enumerate(parts, start=1):
        start = (idx - 1) * slot
        end = min(idx * slot - 0.08, duration)
        lines.extend([str(idx), f"{_fmt_time(start)} --> {_fmt_time(end)}", text, ""])
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
