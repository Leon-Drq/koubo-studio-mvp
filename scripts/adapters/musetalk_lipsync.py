#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo", default=os.getenv("MUSETALK_DIR", "models/MuseTalk"))
    parser.add_argument("--python", default=os.getenv("MUSETALK_PYTHON", sys.executable))
    parser.add_argument("--ffmpeg-path", default=os.getenv("MUSETALK_FFMPEG_PATH", ""))
    parser.add_argument("--batch-size", default=os.getenv("MUSETALK_BATCH_SIZE", "8"))
    parser.add_argument("--bbox-shift", default=os.getenv("MUSETALK_BBOX_SHIFT", "0"))
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.exists():
        raise SystemExit(f"MuseTalk repo not found: {repo}")

    cache_root = Path(os.getenv("KOUBO_MODEL_CACHE", Path.cwd() / "models" / "cache")).resolve()
    os.environ.setdefault("HF_HOME", str(cache_root / "huggingface"))
    os.environ.setdefault("HF_HUB_CACHE", str(cache_root / "huggingface" / "hub"))
    os.environ.setdefault("TORCH_HOME", str(cache_root / "torch"))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_root / "xdg"))
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:128")

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output_name = output.name

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config_path = tmp_path / "koubo_musetalk.yaml"
        result_dir = tmp_path / "results"
        config_path.write_text(
            "task_0:\n"
            f"  video_path: \"{Path(args.video).resolve().as_posix()}\"\n"
            f"  audio_path: \"{Path(args.audio).resolve().as_posix()}\"\n"
            f"  result_name: \"{output_name}\"\n"
            f"  bbox_shift: {args.bbox_shift}\n",
            encoding="utf-8",
        )

        command = [
            args.python,
            "-m",
            "scripts.inference",
            "--inference_config",
            str(config_path),
            "--result_dir",
            str(result_dir),
            "--unet_model_path",
            "models/musetalkV15/unet.pth",
            "--unet_config",
            "models/musetalkV15/musetalk.json",
            "--version",
            "v15",
            "--batch_size",
            str(args.batch_size),
            "--use_float16",
            "--output_vid_name",
            output_name,
        ]
        if args.bbox_shift:
            command.extend(["--bbox_shift", str(args.bbox_shift)])
        if args.ffmpeg_path:
            command.extend(["--ffmpeg_path", args.ffmpeg_path])

        subprocess.run(command, cwd=repo, check=True)

        candidates = list(result_dir.rglob(output_name))
        if not candidates:
            raise SystemExit("MuseTalk finished but did not produce the expected output video.")
        shutil.copyfile(candidates[0], output)


if __name__ == "__main__":
    main()
