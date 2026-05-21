from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.services.command import has_binary


def run_ffmpeg(args: list[str]) -> None:
    if not has_binary("ffmpeg"):
        raise RuntimeError("ffmpeg is not installed.")
    subprocess.run(["ffmpeg", "-y", *args], check=True, capture_output=True, text=True)


def ffprobe_duration(path: Path) -> float:
    if not has_binary("ffprobe"):
        return 0.0
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    return float(payload.get("format", {}).get("duration") or 0.0)


def extract_audio(video: Path, output: Path) -> Path:
    run_ffmpeg(["-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(output)])
    return output


def mux_audio(video: Path, audio: Path, output: Path) -> Path:
    duration = ffprobe_duration(audio)
    args = [
        "-stream_loop",
        "-1",
        "-i",
        str(video),
        "-i",
        str(audio),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-shortest",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
    ]
    if duration > 0:
        args.extend(["-t", f"{duration:.2f}"])
    args.append(str(output))
    run_ffmpeg(args)
    return output


def make_silent_audio(output: Path, seconds: float) -> Path:
    run_ffmpeg(["-f", "lavfi", "-i", "anullsrc=channel_layout=mono:sample_rate=16000", "-t", f"{seconds:.2f}", str(output)])
    return output


def generate_cover(video: Path, output: Path) -> Path:
    run_ffmpeg(["-ss", "00:00:01", "-i", str(video), "-frames:v", "1", "-q:v", "2", str(output)])
    return output


def burn_subtitles(video: Path, srt: Path, output: Path) -> Path:
    subtitle_path = str(srt).replace(":", "\\:")
    run_ffmpeg(["-i", str(video), "-vf", f"subtitles={subtitle_path}", "-c:a", "copy", str(output)])
    return output
