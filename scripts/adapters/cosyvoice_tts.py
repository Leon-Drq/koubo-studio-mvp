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
    parser.add_argument("--repo", default=os.getenv("COSYVOICE_DIR", "models/CosyVoice"))
    parser.add_argument("--model-dir", default=os.getenv("COSYVOICE_MODEL_DIR", "models/CosyVoice/pretrained_models/CosyVoice2-0.5B"))
    parser.add_argument("--mode", default=os.getenv("COSYVOICE_MODE", "cross_lingual"))
    parser.add_argument("--prompt-text", default=os.getenv("COSYVOICE_PROMPT_TEXT", ""))
    parser.add_argument("--fp16", action="store_true", default=os.getenv("COSYVOICE_FP16", "true").lower() == "true")
    args = parser.parse_args()

    source_text = Path(args.input).read_text(encoding="utf-8").strip()
    if not source_text:
        raise SystemExit("TTS input text is empty.")
    if not args.voice_sample:
        raise SystemExit("CosyVoice requires --voice-sample for local voice cloning.")

    repo = Path(args.repo).resolve()
    model_dir = Path(args.model_dir).resolve()
    if not repo.exists():
        raise SystemExit(f"CosyVoice repo not found: {repo}")
    if not model_dir.exists():
        raise SystemExit(f"CosyVoice model dir not found: {model_dir}")

    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(repo / "third_party" / "Matcha-TTS"))

    from cosyvoice.cli.cosyvoice import CosyVoice, CosyVoice2
    from cosyvoice.utils.file_utils import load_wav
    import torch
    import torchaudio

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    wav_output = output if output.suffix.lower() == ".wav" else output.with_suffix(".cosyvoice.wav")

    model_name = model_dir.name.lower()
    model_cls = CosyVoice2 if "cosyvoice2" in model_name or "cosyvoice3" in model_name else CosyVoice
    cosyvoice = model_cls(str(model_dir), load_jit=False, load_trt=False, fp16=args.fp16)
    mode = args.mode.strip().lower().replace("-", "_")
    prompt_wav = load_wav(str(Path(args.voice_sample).resolve()), 16000)
    chunks = []

    if mode == "zero_shot" and args.prompt_text.strip():
        iterator = cosyvoice.inference_zero_shot(source_text, args.prompt_text.strip(), prompt_wav, stream=False)
    else:
        iterator = cosyvoice.inference_cross_lingual(source_text, prompt_wav, stream=False)

    for item in iterator:
        speech = item.get("tts_speech")
        if speech is not None:
            chunks.append(speech.cpu())

    if not chunks:
        raise SystemExit("CosyVoice finished but did not produce speech.")

    audio = torch.cat(chunks, dim=1)
    torchaudio.save(str(wav_output), audio, cosyvoice.sample_rate)

    if wav_output != output:
        convert_audio(wav_output, output)
        wav_output.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
