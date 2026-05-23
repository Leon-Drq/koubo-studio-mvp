from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from app.config import Settings


def _ollama_bin(settings: Settings) -> str | None:
    configured = settings.ollama_bin.strip()
    if configured:
        return configured
    resolved = shutil.which("ollama")
    if resolved:
        return resolved
    local = Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe"
    if local.exists():
        return str(local)
    return None


def unload_ollama_before_media(settings: Settings) -> str:
    if not settings.auto_unload_ollama_before_media or not settings.ollama_model:
        return ""

    binary = _ollama_bin(settings)
    if not binary:
        return ""

    try:
        subprocess.run([binary, "stop", settings.ollama_model], check=False, capture_output=True, text=True, timeout=20)
        time.sleep(1.0)
        return f"已卸载 Ollama {settings.ollama_model} 释放显存"
    except Exception:
        return ""
