#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo", default=os.getenv("LATENTSYNC_DIR", "models/LatentSync"))
    parser.add_argument("--python", default=os.getenv("LATENTSYNC_PYTHON", sys.executable))
    parser.add_argument("--config", default=os.getenv("LATENTSYNC_CONFIG", "configs/unet/stage2.yaml"))
    parser.add_argument("--checkpoint", default=os.getenv("LATENTSYNC_CHECKPOINT", "checkpoints/latentsync_unet.pt"))
    parser.add_argument("--steps", default=os.getenv("LATENTSYNC_STEPS", "20"))
    parser.add_argument("--guidance-scale", default=os.getenv("LATENTSYNC_GUIDANCE_SCALE", "1.5"))
    parser.add_argument("--deepcache", action="store_true", default=os.getenv("LATENTSYNC_DEEPCACHE", "true").lower() == "true")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.exists():
        raise SystemExit(f"LatentSync repo not found: {repo}")

    cache_root = Path(os.getenv("KOUBO_MODEL_CACHE", Path.cwd() / "models" / "cache")).resolve()
    os.environ.setdefault("HF_HOME", str(cache_root / "huggingface"))
    os.environ.setdefault("HF_HUB_CACHE", str(cache_root / "huggingface" / "hub"))
    os.environ.setdefault("TORCH_HOME", str(cache_root / "torch"))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_root / "xdg"))
    os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "max_split_size_mb:128")

    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        args.python,
        "-m",
        "scripts.inference",
        "--unet_config_path",
        args.config,
        "--inference_ckpt_path",
        args.checkpoint,
        "--inference_steps",
        str(args.steps),
        "--guidance_scale",
        str(args.guidance_scale),
        "--video_path",
        str(Path(args.video).resolve()),
        "--audio_path",
        str(Path(args.audio).resolve()),
        "--video_out_path",
        str(output),
    ]
    if args.deepcache:
        command.append("--enable_deepcache")

    subprocess.run(command, cwd=repo, check=True)
    if not output.exists():
        raise SystemExit("LatentSync finished but did not produce the expected output video.")


if __name__ == "__main__":
    main()
