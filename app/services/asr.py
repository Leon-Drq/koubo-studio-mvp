from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Optional

from app.config import Settings
from app.services.command import CommandError, has_binary, run_template


DEMO_TRANSCRIPT = """最近有不少朋友问我，为什么同样是做内容，有的人越做越轻松，有的人越做越累。
其实核心不是每天发多少条，而是有没有把一个卖点讲清楚。
今天这条口播，我们就把痛点、解决方案和行动理由拆开讲，让用户听完马上知道为什么现在需要它。"""


def transcribe_audio(audio: Optional[Path], settings: Settings, output: Path, provided_text: str = "") -> tuple[str, str]:
    if provided_text.strip():
        text = provided_text.strip()
        output.write_text(text, encoding="utf-8")
        return text, "使用用户提供的文案"

    if audio and settings.asr_command.strip():
        run_template(settings.asr_command, audio=audio, text=output)
        text = output.read_text(encoding="utf-8").strip()
        return text, "ASR_COMMAND"

    if audio and has_binary("whisper"):
        subprocess.run(
            [
                "whisper",
                str(audio),
                "--language",
                "Chinese",
                "--model",
                "base",
                "--output_format",
                "txt",
                "--output_dir",
                str(output.parent),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        guessed = output.parent / f"{audio.stem}.txt"
        if guessed.exists():
            guessed.replace(output)
        text = output.read_text(encoding="utf-8").strip()
        return text, "whisper CLI"

    text = DEMO_TRANSCRIPT
    output.write_text(text, encoding="utf-8")
    if audio:
        return text, "未配置 ASR，使用演示文案"
    return text, "无对标音频，使用演示文案"


def safe_transcribe(audio: Optional[Path], settings: Settings, output: Path, provided_text: str = "") -> tuple[str, str]:
    try:
        return transcribe_audio(audio, settings, output, provided_text)
    except (CommandError, subprocess.CalledProcessError, RuntimeError) as exc:
        output.write_text(DEMO_TRANSCRIPT, encoding="utf-8")
        return DEMO_TRANSCRIPT, f"ASR 失败，已使用演示文案：{exc}"
