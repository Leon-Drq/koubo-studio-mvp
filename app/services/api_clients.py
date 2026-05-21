from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Optional

import httpx

from app.config import Settings


class ApiClientError(RuntimeError):
    pass


def _headers(api_key: str) -> dict[str, str]:
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


def _write_binary_or_json_asset(response: httpx.Response, output: Path, url_keys: tuple[str, ...], b64_keys: tuple[str, ...]) -> Path:
    content_type = response.headers.get("content-type", "")
    if content_type.startswith(("audio/", "video/", "application/octet-stream")):
        output.write_bytes(response.content)
        return output

    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiClientError("API response was neither binary media nor JSON.") from exc

    media_url = _find_first(payload, url_keys)
    if media_url:
        media = httpx.get(str(media_url), timeout=120)
        media.raise_for_status()
        output.write_bytes(media.content)
        return output

    encoded = _find_first(payload, b64_keys)
    if encoded:
        raw = str(encoded)
        if "," in raw and raw.startswith("data:"):
            raw = raw.split(",", 1)[1]
        output.write_bytes(base64.b64decode(raw))
        return output

    raise ApiClientError(f"API JSON did not contain any of: {', '.join(url_keys + b64_keys)}")


def _find_first(payload: Any, keys: tuple[str, ...]) -> Optional[Any]:
    if isinstance(payload, dict):
        for key in keys:
            if payload.get(key):
                return payload[key]
        for value in payload.values():
            found = _find_first(value, keys)
            if found:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _find_first(item, keys)
            if found:
                return found
    return None


def transcribe_audio_api(audio: Path, settings: Settings, output: Path) -> tuple[str, str]:
    if not settings.asr_api_url:
        raise ApiClientError("ASR_API_URL is empty.")

    data: dict[str, str] = {}
    if settings.asr_api_model:
        data["model"] = settings.asr_api_model
    with audio.open("rb") as handle:
        files = {settings.asr_api_file_field: (audio.name, handle, "application/octet-stream")}
        response = httpx.post(settings.asr_api_url, headers=_headers(settings.asr_api_key), data=data, files=files, timeout=300)
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if content_type.startswith("text/"):
        text = response.text.strip()
    else:
        payload = response.json()
        text = _find_first(payload, ("text", "transcript", "result", "content")) or ""
        text = str(text).strip()
    if not text:
        raise ApiClientError("ASR API returned empty text.")
    output.write_text(text, encoding="utf-8")
    return text, "ASR API"


def rewrite_script_api(source: str, settings: Settings, output: Path, product_brief: str, tone: str) -> tuple[str, str]:
    if not settings.llm_api_url:
        raise ApiClientError("LLM_API_URL is empty.")

    prompt = (
        "你是电商口播编导。请把原文案改写成 60-90 秒中文口播脚本，"
        "包含钩子、痛点、解决方案、行动号召，避免夸大承诺。\n\n"
        f"风格：{tone}\n商品卖点：{product_brief}\n\n原文案：\n{source}"
    )
    payload = {
        "model": settings.llm_api_model,
        "temperature": settings.llm_api_temperature,
        "messages": [
            {"role": "system", "content": "你只输出改写后的口播脚本，不输出解释。"},
            {"role": "user", "content": prompt},
        ],
    }
    response = httpx.post(settings.llm_api_url, headers=_headers(settings.llm_api_key), json=payload, timeout=180)
    response.raise_for_status()
    data = response.json()
    script = ""
    choices = data.get("choices") if isinstance(data, dict) else None
    if choices:
        message = choices[0].get("message") or {}
        script = str(message.get("content") or choices[0].get("text") or "").strip()
    if not script:
        script = str(_find_first(data, ("content", "text", "result")) or "").strip()
    if not script:
        raise ApiClientError("LLM API returned empty script.")
    output.write_text(script, encoding="utf-8")
    return script, "LLM API"


def synthesize_speech_api(script: str, settings: Settings, output: Path, voice_name: str, voice_sample: Optional[Path] = None) -> tuple[Path, str]:
    if not settings.tts_api_url:
        raise ApiClientError("TTS_API_URL is empty.")

    mode = (settings.tts_api_mode or "json").lower()
    if mode == "multipart" or voice_sample:
        data = {
            settings.tts_api_text_field: script,
            settings.tts_api_voice_field: voice_name or settings.tts_api_voice,
            "model": settings.tts_api_model,
        }
        files = {}
        handle = None
        try:
            if voice_sample:
                handle = voice_sample.open("rb")
                files[settings.tts_api_file_field] = (voice_sample.name, handle, "application/octet-stream")
            response = httpx.post(settings.tts_api_url, headers=_headers(settings.tts_api_key), data=data, files=files or None, timeout=600)
        finally:
            if handle:
                handle.close()
    else:
        payload = {
            "model": settings.tts_api_model,
            settings.tts_api_text_field: script,
            settings.tts_api_voice_field: voice_name or settings.tts_api_voice,
        }
        response = httpx.post(settings.tts_api_url, headers=_headers(settings.tts_api_key), json=payload, timeout=600)

    response.raise_for_status()
    _write_binary_or_json_asset(response, output, ("audio_url", "url", "file_url"), ("audio_base64", "base64", "data"))
    return output, "TTS API"


def render_lipsync_api(video: Path, audio: Path, settings: Settings, output: Path) -> tuple[Path, str]:
    if not settings.lipsync_api_url:
        raise ApiClientError("LIPSYNC_API_URL is empty.")

    with video.open("rb") as video_handle, audio.open("rb") as audio_handle:
        files = {
            settings.lipsync_api_video_field: (video.name, video_handle, "application/octet-stream"),
            settings.lipsync_api_audio_field: (audio.name, audio_handle, "application/octet-stream"),
        }
        response = httpx.post(settings.lipsync_api_url, headers=_headers(settings.lipsync_api_key), files=files, timeout=1800)
    response.raise_for_status()
    _write_binary_or_json_asset(response, output, ("video_url", "url", "file_url"), ("video_base64", "base64", "data"))
    return output, "Lip-sync API"
