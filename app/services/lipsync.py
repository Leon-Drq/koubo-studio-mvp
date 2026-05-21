from __future__ import annotations

from pathlib import Path

import httpx

from app.config import Settings
from app.services.api_clients import ApiClientError, render_lipsync_api
from app.services.command import CommandError, run_template
from app.services.media import mux_audio
from app.services.providers import normalize_provider, should_try_api


def render_lipsync(video: Path, audio: Path, settings: Settings, output: Path, provider: str = "auto") -> tuple[Path, str]:
    selected = normalize_provider(provider, settings.default_lipsync_provider)
    api_failure = ""
    if should_try_api(selected, bool(settings.lipsync_api_url)):
        try:
            return render_lipsync_api(video, audio, settings, output)
        except (ApiClientError, httpx.HTTPError) as exc:
            api_failure = f"口型 API 失败，"
    elif selected == "api" and not settings.lipsync_api_url:
        api_failure = "口型 API 未配置，"

    if settings.lipsync_command.strip():
        try:
            run_template(settings.lipsync_command, video=video, audio=audio, output=output)
            return output, api_failure + "LIPSYNC_COMMAND"
        except CommandError as exc:
            fallback = f"{api_failure}口型模型失败，已使用合成预览 fallback：{exc}"
        else:
            fallback = ""
    else:
        fallback = api_failure + "未配置口型模型，使用原视频配音预览"

    mux_audio(video, audio, output)
    return output, fallback
