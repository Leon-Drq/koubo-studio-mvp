#!/usr/bin/env python
from __future__ import annotations

import argparse
import os
import re


TAG_RE = re.compile(r"<\s*\|\s*[^>]+?\|\s*>")


def clean_text(value: str) -> str:
    return TAG_RE.sub("", value).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default=os.getenv("FUNASR_MODEL", "iic/SenseVoiceSmall"))
    parser.add_argument("--vad-model", default=os.getenv("FUNASR_VAD_MODEL", "fsmn-vad"))
    parser.add_argument("--punc-model", default=os.getenv("FUNASR_PUNC_MODEL", "ct-punc"))
    parser.add_argument("--device", default=os.getenv("FUNASR_DEVICE", "cuda:0"))
    args = parser.parse_args()

    cache_root = os.getenv("KOUBO_MODEL_CACHE", os.path.join(os.getcwd(), "models", "cache"))
    os.environ.setdefault("MODELSCOPE_CACHE", os.path.join(cache_root, "modelscope"))

    from funasr import AutoModel

    kwargs = {"model": args.model, "device": args.device, "trust_remote_code": True, "disable_update": True}
    if args.vad_model:
        kwargs["vad_model"] = args.vad_model
    if args.punc_model:
        kwargs["punc_model"] = args.punc_model

    model = AutoModel(**kwargs)
    result = model.generate(input=args.input, batch_size_s=300)
    text = ""
    if result:
        first = result[0]
        if isinstance(first, dict):
            if first.get("sentence_info"):
                text = "".join(item.get("text", "") for item in first["sentence_info"])
            else:
                text = first.get("text", "")
        else:
            text = str(first)

    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(clean_text(text))


if __name__ == "__main__":
    main()
