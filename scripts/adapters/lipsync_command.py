#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import shutil
import subprocess


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--audio", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repo", default=os.getenv("MUSETALK_DIR", ""))
    args = parser.parse_args()

    if not args.repo:
        raise SystemExit("Set MUSETALK_DIR to your MuseTalk checkout, or replace LIPSYNC_COMMAND with your own wrapper.")

    config = os.getenv("MUSETALK_CONFIG", "configs/inference/test.yaml")
    command = [
        "python",
        "-m",
        "scripts.inference",
        "--inference_config",
        config,
        "--result_dir",
        os.path.dirname(os.path.abspath(args.output)),
    ]
    subprocess.run(command, cwd=args.repo, check=True)
    candidates = sorted(os.path.join(args.repo, "results", name) for name in os.listdir(os.path.join(args.repo, "results"))) if os.path.exists(os.path.join(args.repo, "results")) else []
    if not candidates:
        raise SystemExit("MuseTalk finished but no result file was found. Customize this wrapper for your config.")
    shutil.copyfile(candidates[-1], args.output)


if __name__ == "__main__":
    main()
