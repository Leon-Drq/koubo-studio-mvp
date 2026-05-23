#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess


def ollama_bin() -> str:
    configured = os.getenv("OLLAMA_BIN", "").strip()
    if configured:
        return configured
    resolved = shutil.which("ollama")
    if resolved:
        return resolved
    local = Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"
    if local.exists():
        return str(local)
    return "ollama"


def ollama_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("OLLAMA_MODELS", str((Path.cwd() / "models" / "ollama").resolve()))
    return env


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"))
    args = parser.parse_args()

    source = open(args.input, encoding="utf-8").read()
    prompt = source + "\n\n请输出中文电商口播脚本，60-90 秒，包含钩子、痛点、解决方案、行动号召。"
    proc = subprocess.run(
        [ollama_bin(), "run", args.model, prompt],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=ollama_env(),
        timeout=180,
    )
    open(args.output, "w", encoding="utf-8").write(proc.stdout.strip())


if __name__ == "__main__":
    main()
