from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

import httpx

from app.config import Settings
from app.services.command import binary_path


class DownloadResult:
    def __init__(self, video: Optional[Path], title: str = "", description: str = ""):
        self.video = video
        self.title = title
        self.description = description


DOUYIN_MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 "
    "Mobile/15E148 Safari/604.1"
)


def _is_douyin_url(url: str) -> bool:
    return "douyin.com" in url.lower()


def _http_proxy(settings: Optional[Settings]) -> str | None:
    if settings and settings.ytdlp_proxy.strip():
        return settings.ytdlp_proxy.strip()
    return None


def _extract_douyin_video_id(url: str, client: httpx.Client) -> str:
    direct = re.search(r"/video/(\d+)", url)
    if direct:
        return direct.group(1)

    response = client.get(url, follow_redirects=True)
    response.raise_for_status()
    final_url = str(response.url)
    redirected = re.search(r"/video/(\d+)", final_url)
    if redirected:
        return redirected.group(1)

    embedded = re.search(r'"(?:aweme_id|group_id|item_id)"\s*:\s*"(\d{8,})"', response.text)
    if embedded:
        return embedded.group(1)

    raise RuntimeError("无法从抖音分享链接解析 video_id。")


def _find_douyin_detail(payload: object) -> dict:
    if isinstance(payload, dict):
        if isinstance(payload.get("aweme"), dict):
            return payload["aweme"]
        if isinstance(payload.get("aweme_detail"), dict):
            return payload["aweme_detail"]
        if isinstance(payload.get("videoInfoRes"), dict):
            found = _find_douyin_detail(payload["videoInfoRes"])
            if found:
                return found
        if isinstance(payload.get("item_list"), list) and payload["item_list"]:
            first = payload["item_list"][0]
            if isinstance(first, dict) and isinstance(first.get("video"), dict):
                return first
        for value in payload.values():
            found = _find_douyin_detail(value)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_douyin_detail(value)
            if found:
                return found
    return {}


def _extract_router_data(html: str) -> dict:
    match = re.search(r"window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>", html, re.S)
    if not match:
        match = re.search(r"window\._ROUTER_DATA\s*=\s*(\{.*\})", html, re.S)
    if not match:
        raise RuntimeError("抖音页面里没有找到 window._ROUTER_DATA。")
    return json.loads(match.group(1))


def _pick_play_url(detail: dict) -> str:
    video = detail.get("video") or {}
    candidates = [
        video.get("play_addr", {}).get("url_list") or [],
        video.get("play_addr_h264", {}).get("url_list") or [],
        video.get("download_addr", {}).get("url_list") or [],
    ]
    for urls in candidates:
        for item in urls:
            if item:
                return str(item).replace("playwm", "play")
    raise RuntimeError("抖音页面里没有找到可下载的视频地址。")


def _download_douyin_direct(url: str, output_dir: Path, settings: Optional[Settings]) -> DownloadResult:
    headers = {
        "User-Agent": DOUYIN_MOBILE_UA,
        "Referer": "https://www.douyin.com/",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    proxy = _http_proxy(settings)
    client_kwargs = {"headers": headers, "timeout": 30.0, "follow_redirects": True}
    if proxy:
        client_kwargs["proxy"] = proxy

    with httpx.Client(**client_kwargs) as client:
        video_id = _extract_douyin_video_id(url, client)
        page = client.get(f"https://www.iesdouyin.com/share/video/{video_id}/")
        page.raise_for_status()
        payload = _extract_router_data(page.text)
        detail = _find_douyin_detail(payload)
        if not detail:
            raise RuntimeError("抖音页面解析成功，但没有找到 aweme 详情。")

        play_url = _pick_play_url(detail)
        video_path = output_dir / "source.mp4"
        with client.stream("GET", play_url, headers={**headers, "Referer": str(page.url)}) as response:
            response.raise_for_status()
            with video_path.open("wb") as handle:
                for chunk in response.iter_bytes():
                    if chunk:
                        handle.write(chunk)

    title = (detail.get("desc") or "").strip()
    return DownloadResult(video_path, title, title)


def download_video(url: str, output_dir: Path, settings: Optional[Settings] = None) -> DownloadResult:
    downloader = binary_path("yt-dlp")
    url = url.strip()
    if not url:
        return DownloadResult(None)

    if not downloader:
        if _is_douyin_url(url):
            return _download_douyin_direct(url, output_dir, settings)
        return DownloadResult(None)

    template = output_dir / "source.%(ext)s"
    command = [
        downloader,
        "--no-playlist",
        "--write-info-json",
        "--merge-output-format",
        "mp4",
        "-o",
        str(template),
    ]
    if settings:
        if settings.ytdlp_cookies_file.strip():
            command.extend(["--cookies", settings.ytdlp_cookies_file.strip()])
        if settings.ytdlp_cookies_from_browser.strip():
            command.extend(["--cookies-from-browser", settings.ytdlp_cookies_from_browser.strip()])
        if settings.ytdlp_proxy.strip():
            command.extend(["--proxy", settings.ytdlp_proxy.strip()])
    command.append(url)

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as exc:
        if _is_douyin_url(url):
            try:
                return _download_douyin_direct(url, output_dir, settings)
            except Exception as direct_exc:
                detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
                raise RuntimeError(f"yt-dlp 解析失败，抖音直接解析 fallback 也失败：{direct_exc}\n\n原始 yt-dlp 错误：{detail}") from direct_exc
        raise

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
