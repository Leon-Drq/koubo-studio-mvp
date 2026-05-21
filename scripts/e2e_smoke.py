from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.jobs import PipelineRunner
from app.models import JobInputs
from app.storage import JobStore


def make_video(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=0x253442:s=720x1280:d=6:r=25",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        avatar = tmp_path / "avatar.mp4"
        make_video(avatar)

        settings = Settings(data_dir=tmp_path / "data")
        settings.jobs_dir.mkdir(parents=True, exist_ok=True)
        store = JobStore(settings)
        job = store.create_job(
            JobInputs(
                source_text="同样是做口播，为什么别人一条视频就能讲清楚卖点？核心是结构，不是语速。",
                product_brief="轻量化电商口播数字人平台，适合本地部署和团队批量生产。",
                tone="电商口播",
                platforms=["local", "douyin"],
            )
        )
        PipelineRunner(settings, store).run(job.id, None, avatar, None, None)
        done = store.get(job.id)
        assert done.status == "completed", done.error
        assert done.artifacts.final_video, "missing final video"
        assert Path(done.artifacts.final_video).exists(), done.artifacts.final_video
        assert done.artifacts.srt and Path(done.artifacts.srt).exists(), "missing subtitles"
        print(f"e2e ok: {done.artifacts.final_video}")


if __name__ == "__main__":
    main()
