from __future__ import annotations

import subprocess
from pathlib import Path

from app.config import Settings
from app.services.command import CommandError, has_binary, run_template
from app.services.media import make_silent_audio, run_ffmpeg


def _estimate_seconds(text: str) -> float:
    chars = max(len(text.strip()), 40)
    return min(max(chars / 5.2, 8.0), 180.0)


def synthesize_speech(script: str, settings: Settings, output: Path, voice_name: str) -> tuple[Path, str]:
    input_path = output.with_suffix(".input.txt")
    input_path.write_text(script, encoding="utf-8")

    if settings.tts_command.strip():
        try:
            run_template(settings.tts_command, input=input_path, audio=output, voice=voice_name)
            return output, "TTS_COMMAND"
        except CommandError as exc:
            fallback = f"TTS_COMMAND 失败，已尝试本机 fallback：{exc}"
        else:
            fallback = ""
    else:
        fallback = ""

    if has_binary("say") and has_binary("ffmpeg"):
        aiff_path = output.with_suffix(".aiff")
        try:
            subprocess.run(["say", "-o", str(aiff_path), script], check=True, capture_output=True, text=True)
            run_ffmpeg(["-i", str(aiff_path), "-ar", "44100", "-ac", "2", str(output)])
            aiff_path.unlink(missing_ok=True)
            return output, fallback or "macOS say fallback"
        except Exception:
            aiff_path.unlink(missing_ok=True)

    if has_binary("ffmpeg"):
        make_silent_audio(output, _estimate_seconds(script))
        return output, fallback or "静音音频 fallback"

    raise RuntimeError("需要配置 TTS_COMMAND，或安装 ffmpeg/say 以运行 fallback。")
