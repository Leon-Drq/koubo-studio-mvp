from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Union


class CommandError(RuntimeError):
    pass


def run_template(command_template: str, **paths: Union[Path, str]) -> subprocess.CompletedProcess[str]:
    if not command_template.strip():
        raise CommandError("Command template is empty.")
    values = {key: shlex.quote(str(value)) for key, value in paths.items()}
    rendered = command_template.format_map(values)
    args = shlex.split(rendered)
    try:
        return subprocess.run(args, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise CommandError(detail) from exc
    except OSError as exc:
        raise CommandError(str(exc)) from exc


def has_binary(name: str) -> bool:
    return binary_path(name) is not None


def binary_path(name: str) -> str | None:
    resolved = shutil.which(name)
    if resolved:
        return resolved

    scripts_dir = Path(sys.executable).parent
    candidates = [scripts_dir / name, scripts_dir / f"{name}.exe", scripts_dir / f"{name}.cmd"]
    match = next((path for path in candidates if path.exists()), None)
    return str(match) if match else None
