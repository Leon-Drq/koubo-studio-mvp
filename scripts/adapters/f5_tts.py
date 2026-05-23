#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TAG_RE = re.compile(r"<\s*\|\s*[^>]+?\|\s*>")


def find_executable(name: str) -> str:
    resolved = shutil.which(name)
    if resolved:
        return resolved
    scripts_dir = Path(sys.executable).parent
    for candidate in (scripts_dir / name, scripts_dir / f"{name}.exe", scripts_dir / f"{name}.cmd"):
        if candidate.exists():
            return str(candidate)
    raise SystemExit(f"{name} was not found. Install F5-TTS in the model environment first.")


def clean_asr_text(value: str) -> str:
    return TAG_RE.sub("", value).strip()


def convert_ref_audio(input_path: str, output_path: Path) -> Path:
    ffmpeg = find_executable("ffmpeg")
    subprocess.run(
        [ffmpeg, "-y", "-i", input_path, "-vn", "-ac", "1", "-ar", "16000", str(output_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return output_path


def media_duration(path: Path) -> float:
    ffprobe = find_executable("ffprobe")
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        return float(proc.stdout.strip() or "0")
    except ValueError:
        return 0.0


def expected_speech_duration(text: str) -> float:
    speech_chars = len(re.sub(r"\s+", "", text))
    target_cps = float(os.getenv("F5_TTS_TARGET_CPS", "5.2"))
    return min(max(speech_chars / max(target_cps, 1.0), 4.0), 180.0)


def atempo_filter(speed_factor: float) -> str:
    factors: list[float] = []
    remaining = speed_factor
    while remaining < 0.5:
        step = max(remaining**0.5, 0.5)
        factors.append(step)
        remaining /= step
    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0
    factors.append(remaining)
    return ",".join(f"atempo={factor:.4f}" for factor in factors)


def stretch_if_too_fast(audio_path: Path, text: str, tmp_path: Path) -> Path:
    if os.getenv("F5_TTS_SPEED_GUARD", "true").lower() in {"0", "false", "no"}:
        return audio_path

    actual = media_duration(audio_path)
    expected = expected_speech_duration(text)
    if actual <= 0 or actual >= expected * 0.78:
        return audio_path

    ffmpeg = find_executable("ffmpeg")
    stretched_path = tmp_path / "speech_speed_guard.wav"
    speed_factor = actual / expected
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(audio_path),
            "-filter:a",
            atempo_filter(speed_factor),
            str(stretched_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return stretched_path


def transcribe_ref_audio(audio_path: str, tmp_path: Path, device: str) -> str:
    wav_path = convert_ref_audio(audio_path, tmp_path / "ref_audio_16k.wav")

    from funasr import AutoModel

    cache_root = os.getenv("KOUBO_MODEL_CACHE", os.path.join(os.getcwd(), "models", "cache"))
    os.environ.setdefault("MODELSCOPE_CACHE", os.path.join(cache_root, "modelscope"))

    kwargs = {
        "model": os.getenv("FUNASR_MODEL", "iic/SenseVoiceSmall"),
        "device": os.getenv("FUNASR_DEVICE", "cuda:0" if device.startswith("cuda") else "cpu"),
        "trust_remote_code": True,
        "disable_update": True,
    }
    vad_model = os.getenv("FUNASR_VAD_MODEL", "fsmn-vad")
    punc_model = os.getenv("FUNASR_PUNC_MODEL", "ct-punc")
    if vad_model:
        kwargs["vad_model"] = vad_model
    if punc_model:
        kwargs["punc_model"] = punc_model

    model = AutoModel(**kwargs)
    result = model.generate(input=str(wav_path), batch_size_s=300)
    if not result:
        text = ""
    else:
        first = result[0]
        if isinstance(first, dict):
            if first.get("sentence_info"):
                text = clean_asr_text("".join(item.get("text", "") for item in first["sentence_info"]))
            else:
                text = clean_asr_text(first.get("text", ""))
        else:
            text = clean_asr_text(str(first))

    del model
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--voice", default="")
    parser.add_argument("--voice-sample", default="")
    parser.add_argument("--model", default=os.getenv("F5_TTS_MODEL", "F5TTS_v1_Base"))
    parser.add_argument("--ref-audio", default=os.getenv("F5_REF_AUDIO", ""))
    parser.add_argument("--ref-text", default=os.getenv("F5_REF_TEXT", ""))
    parser.add_argument("--device", default=os.getenv("F5_TTS_DEVICE", "cuda"))
    args = parser.parse_args()

    cache_root = Path(os.getenv("KOUBO_MODEL_CACHE", Path.cwd() / "models" / "cache")).resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(cache_root / "huggingface"))
    os.environ.setdefault("HF_HUB_CACHE", str(cache_root / "huggingface" / "hub"))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache_root / "xdg"))
    os.environ.setdefault("CACHED_PATH_CACHE_ROOT", str(cache_root / "cached_path"))

    source_text = Path(args.input).read_text(encoding="utf-8").strip()
    if not source_text:
        raise SystemExit("TTS input text is empty.")

    ref_audio = args.voice_sample.strip() or args.ref_audio.strip()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    cli = find_executable("f5-tts_infer-cli")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        wav_name = "speech.wav"
        ref_text = args.ref_text.strip()
        if ref_audio and not ref_text:
            ref_text = transcribe_ref_audio(ref_audio, tmp_path, args.device).strip()
            if not ref_text:
                ref_text = "这是一段参考声音。"

        command = [
            cli,
            "--model",
            args.model,
            "--gen_text",
            source_text,
            "--output_dir",
            str(tmp_path),
            "--output_file",
            wav_name,
            "--device",
            args.device,
            "--remove_silence",
        ]
        if ref_audio:
            command.extend(["--ref_audio", ref_audio, "--ref_text", ref_text])
        subprocess.run(command, check=True)

        wav_path = tmp_path / wav_name
        if not wav_path.exists():
            raise SystemExit("F5-TTS finished but did not produce speech.wav.")
        wav_path = stretch_if_too_fast(wav_path, source_text, tmp_path)

        if output.suffix.lower() == ".wav":
            shutil.copyfile(wav_path, output)
        else:
            ffmpeg = find_executable("ffmpeg")
            subprocess.run([ffmpeg, "-y", "-i", str(wav_path), str(output)], check=True)


if __name__ == "__main__":
    main()
