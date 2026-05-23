#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_executable(name: str) -> str:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    scripts_dir = Path(sys.executable).parent
    for candidate in (scripts_dir / name, scripts_dir / f"{name}.exe", scripts_dir / f"{name}.cmd"):
        if candidate.exists():
            return str(candidate)
    raise SystemExit(f"{name} was not found.")


def bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def convert_audio(input_path: Path, output_path: Path) -> Path:
    ffmpeg = find_executable("ffmpeg")
    subprocess.run([ffmpeg, "-y", "-i", str(input_path), str(output_path)], check=True)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--voice", default="")
    parser.add_argument("--voice-sample", default="")
    parser.add_argument("--model-dir", default=os.getenv("INDEXTTS_MODEL_DIR", "models/IndexTTS/checkpoints"))
    parser.add_argument("--cfg", default=os.getenv("INDEXTTS_CFG", "models/IndexTTS/checkpoints/config.yaml"))
    parser.add_argument("--repo", default=os.getenv("INDEXTTS_DIR", "models/IndexTTS"))
    parser.add_argument("--fp16", action="store_true", default=bool_env("INDEXTTS_FP16", True))
    parser.add_argument("--cuda-kernel", action="store_true", default=bool_env("INDEXTTS_CUDA_KERNEL", False))
    parser.add_argument("--deepspeed", action="store_true", default=bool_env("INDEXTTS_DEEPSPEED", False))
    args = parser.parse_args()

    source_text = Path(args.input).read_text(encoding="utf-8").strip()
    if not source_text:
        raise SystemExit("TTS input text is empty.")
    if not args.voice_sample:
        raise SystemExit("IndexTTS2 requires --voice-sample for zero-shot voice cloning.")

    repo = Path(args.repo).resolve()
    if repo.exists():
        sys.path.insert(0, str(repo))

    from indextts.infer_v2 import IndexTTS2

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    wav_output = output if output.suffix.lower() == ".wav" else output.with_suffix(".indextts.wav")

    tts = IndexTTS2(
        cfg_path=str(Path(args.cfg).resolve()),
        model_dir=str(Path(args.model_dir).resolve()),
        use_fp16=args.fp16,
        use_cuda_kernel=args.cuda_kernel,
        use_deepspeed=args.deepspeed,
    )
    tts.infer(
        spk_audio_prompt=str(Path(args.voice_sample).resolve()),
        text=source_text,
        output_path=str(wav_output),
        verbose=True,
    )

    if wav_output != output:
        convert_audio(wav_output, output)
        wav_output.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
