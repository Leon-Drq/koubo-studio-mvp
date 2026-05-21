#!/usr/bin/env python
from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default="base")
    parser.add_argument("--language", default="Chinese")
    args = parser.parse_args()

    import whisper

    model = whisper.load_model(args.model)
    result = model.transcribe(args.input, language=args.language)
    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(result["text"].strip())


if __name__ == "__main__":
    main()
