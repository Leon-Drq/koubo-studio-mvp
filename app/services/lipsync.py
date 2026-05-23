from __future__ import annotations

from pathlib import Path

import httpx

from app.config import Settings
from app.services.api_clients import ApiClientError, render_lipsync_api
from app.services.command import CommandError, run_template
from app.services.media import mux_audio


def _selected_provider(provider: str, default: str) -> str:
    selected = (provider or default or "auto").strip().lower()
    aliases = {
        "standard": "musetalk",
        "local": "musetalk",
        "high": "latentsync",
        "high_quality": "latentsync",
        "quality": "latentsync",
        "mux": "preview",
    }
    return aliases.get(selected, selected)


def _render_musetalk(video: Path, audio: Path, settings: Settings, output: Path, api_failure: str, batch_size: int, bbox_shift: int) -> tuple[Path, str] | None:
    if not settings.lipsync_command.strip():
        return None
    try:
        run_template(
            settings.lipsync_command,
            video=video,
            audio=audio,
            output=output,
            batch_size=batch_size,
            bbox_shift=bbox_shift,
        )
        return output, api_failure + f"MuseTalk batch={batch_size} bbox_shift={bbox_shift}"
    except CommandError as exc:
        raise CommandError(f"{api_failure}MuseTalk 失败：{exc}") from exc


def render_lipsync(
    video: Path,
    audio: Path,
    settings: Settings,
    output: Path,
    provider: str = "auto",
    batch_size: int | None = None,
    bbox_shift: int | None = None,
) -> tuple[Path, str]:
    selected = _selected_provider(provider, settings.default_lipsync_provider)
    musetalk_batch_size = batch_size or settings.musetalk_batch_size
    musetalk_bbox_shift = settings.musetalk_bbox_shift if bbox_shift is None else bbox_shift
    api_failure = ""

    if selected == "preview":
        mux_audio(video, audio, output)
        return output, "快速预览：原视频配音"

    if selected in {"auto", "api"} and settings.lipsync_api_url:
        try:
            return render_lipsync_api(video, audio, settings, output)
        except (ApiClientError, httpx.HTTPError) as exc:
            api_failure = f"口型 API 失败，"
    elif selected == "api" and not settings.lipsync_api_url:
        api_failure = "口型 API 未配置，"

    if selected == "latentsync":
        if settings.latentsync_command.strip():
            try:
                run_template(settings.latentsync_command, video=video, audio=audio, output=output)
                return output, api_failure + "LatentSync 高质量"
            except CommandError as exc:
                api_failure += f"LatentSync 失败，回退 MuseTalk：{exc}；"
        else:
            api_failure += "LatentSync 未配置，回退 MuseTalk；"

    if selected in {"auto", "musetalk", "latentsync"}:
        try:
            result = _render_musetalk(video, audio, settings, output, api_failure, musetalk_batch_size, musetalk_bbox_shift)
            if result:
                return result
        except CommandError as exc:
            fallback = f"{exc}，已使用合成预览 fallback"
        else:
            fallback = api_failure + "未配置 MuseTalk，使用原视频配音预览"
    else:
        fallback = api_failure + "未配置口型模型，使用原视频配音预览"

    mux_audio(video, audio, output)
    return output, fallback
