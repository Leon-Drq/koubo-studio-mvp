from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.services.command import CommandError, run_template
from app.services.media import mux_audio


def render_lipsync(video: Path, audio: Path, settings: Settings, output: Path) -> tuple[Path, str]:
    if settings.lipsync_command.strip():
        try:
            run_template(settings.lipsync_command, video=video, audio=audio, output=output)
            return output, "LIPSYNC_COMMAND"
        except CommandError as exc:
            fallback = f"口型模型失败，已使用合成预览 fallback：{exc}"
        else:
            fallback = ""
    else:
        fallback = "未配置口型模型，使用原视频配音预览"

    mux_audio(video, audio, output)
    return output, fallback
