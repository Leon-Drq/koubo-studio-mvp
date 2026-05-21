from __future__ import annotations

import shlex
import subprocess
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
        return subprocess.run(args, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise CommandError(detail) from exc


def has_binary(name: str) -> bool:
    return subprocess.run(["which", name], capture_output=True).returncode == 0
