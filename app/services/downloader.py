from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from app.services.command import has_binary


class DownloadResult:
    def __init__(self, video: Optional[Path], title: str = "", description: str = ""):
        self.video = video
        self.title = title
        self.description = description


def download_video(url: str, output_dir: Path) -> DownloadResult:
    if not url.strip() or not has_binary("yt-dlp"):
        return DownloadResult(None)

    template = output_dir / "source.%(ext)s"
    subprocess.run(
        [
            "yt-dlp",
            "--no-playlist",
            "--write-info-json",
            "--merge-output-format",
            "mp4",
            "-o",
            str(template),
            url,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    candidates = sorted(output_dir.glob("source.*"))
    video = next((p for p in candidates if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}), None)
    info_path = output_dir / "source.info.json"
    title = ""
    description = ""
    if info_path.exists():
        info = json.loads(info_path.read_text(encoding="utf-8"))
        title = info.get("title") or ""
        description = info.get("description") or ""
    return DownloadResult(video, title, description)
