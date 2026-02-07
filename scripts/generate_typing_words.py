#!/usr/bin/env python3
"""
Generate HTML spans and CSS nth-child delays for word-by-word typing.

Example:
  python scripts/generate_typing_words.py \\
    --text "Hello world from MyST." \\
    --delay 0.075 \\
    --duration 0.01 \\
    --selector ".landing-hero .typing-word"
"""
from __future__ import annotations

import argparse
import math
import sys
import textwrap


def format_seconds(value: float) -> str:
    s = f"{value:.3f}".rstrip("0").rstrip(".")
    return s if s else "0"


def build_words(text: str) -> list[str]:
    # Normalize whitespace to single spaces.
    words = [w for w in text.strip().split() if w]
    return words


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate HTML spans and CSS delays for word-by-word typing."
    )
    parser.add_argument(
        "--text",
        help="Text to animate (whitespace will be normalized).",
    )
    parser.add_argument(
        "--text-file",
        help="Path to a UTF-8 text file to animate.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.075,
        help="Delay between words in seconds (ignored if --total is set).",
    )
    parser.add_argument(
        "--total",
        type=float,
        help="Total duration in seconds for all words. Overrides --delay.",
    )
    parser.add_argument(
        "--start-delay",
        type=float,
        default=0.0,
        help="Initial delay before the first word (seconds).",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.01,
        help="Per-word reveal animation duration (seconds).",
    )
    parser.add_argument(
        "--selector",
        default=".landing-hero .typing-word",
        help="CSS selector for nth-child delay rules.",
    )
    parser.add_argument(
        "--html-only",
        action="store_true",
        help="Output only HTML spans.",
    )
    parser.add_argument(
        "--css-only",
        action="store_true",
        help="Output only CSS rules.",
    )

    args = parser.parse_args()

    if not args.text and not args.text_file:
        parser.error("Provide --text or --text-file.")
    if args.text and args.text_file:
        parser.error("Provide only one of --text or --text-file.")
    if args.delay <= 0:
        parser.error("--delay must be > 0.")
    if args.total is not None and args.total <= 0:
        parser.error("--total must be > 0.")
    if args.duration <= 0:
        parser.error("--duration must be > 0.")

    if args.text_file:
        try:
            text = open(args.text_file, "r", encoding="utf-8").read()
        except OSError as exc:
            print(f"Failed to read text file: {exc}", file=sys.stderr)
            return 1
    else:
        text = args.text

    words = build_words(text)
    if not words:
        print("No words found after normalization.", file=sys.stderr)
        return 1

    if args.total is not None:
        if len(words) == 1:
            delay = 0.0
        else:
            delay = args.total / (len(words) - 1)
    else:
        delay = args.delay

    html_lines = ['<span class="typing-words" aria-hidden="true">']
    for i, word in enumerate(words):
        trailing = " " if i < len(words) - 1 else ""
        html_lines.append(f'  <span class="typing-word">{word}{trailing}</span>')
    html_lines.append("</span>")

    css_lines = []
    for i in range(len(words)):
        d = args.start_delay + (i * delay)
        css_lines.append(
            f"{args.selector}:nth-child({i + 1}) {{ animation-delay: {format_seconds(d)}s; }}"
        )

    if not args.css_only:
        print("<!-- HTML -->")
        print("\n".join(html_lines))
    if not args.html_only:
        if not args.css_only:
            print("\n<!-- CSS -->")
        print("\n".join(css_lines))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
