from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.models import PublishedReport


def prepare_publish_report(platforms: list[str], final_video: Optional[Path], title: str, topics: list[str]) -> list[PublishedReport]:
    if not platforms:
        platforms = ["local"]
    reports: list[PublishedReport] = []
    for platform in platforms:
        if platform == "local":
            reports.append(PublishedReport(platform="local", status="ready", message="视频已导出到本地，可手动上传。"))
            continue
        reports.append(
            PublishedReport(
                platform=platform,
                status="manual",
                message=f"MVP 已生成标题和话题，{platform} 自动发布需接官方开放平台或浏览器发布器。",
            )
        )
    return reports
