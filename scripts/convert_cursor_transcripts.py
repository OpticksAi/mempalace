#!/usr/bin/env python3
"""
convert_cursor_transcripts.py — Collect and convert Cursor Agent JSONL transcripts
into files that `mempalace mine --mode convos` can ingest directly.

Usage:
    python scripts/convert_cursor_transcripts.py <source_dir> <output_dir> --developer alice [--incremental]

source_dir  — root containing agent-transcripts folders
              (e.g. copied from %USERPROFILE%\.cursor\projects\*\agent-transcripts)
output_dir  — where converted transcript files are written
--developer — developer name (used for wing tagging in filenames)
--incremental — skip files that already have a converted counterpart
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path


def extract_text_from_content(content_blocks, role):
    """Pull readable text from Cursor's message.content block array."""
    if not isinstance(content_blocks, list):
        return ""
    parts = []
    for block in content_blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "text":
            continue
        raw = block.get("text", "")
        if role == "user":
            uq = re.search(r"<user_query>(.*?)</user_query>", raw, re.DOTALL)
            if uq:
                raw = uq.group(1).strip()
        parts.append(raw.strip())
    return " ".join(parts).strip()


def convert_jsonl(jsonl_path):
    """Convert a single Cursor JSONL file to MemPalace transcript format."""
    messages = []
    with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict):
                continue
            role = entry.get("role", "")
            message = entry.get("message", {})
            if not isinstance(message, dict):
                continue
            content_blocks = message.get("content", [])
            text = extract_text_from_content(content_blocks, role)
            if not text:
                continue
            if role in ("user", "assistant"):
                messages.append((role, text))

    if len(messages) < 2:
        return None

    lines = []
    i = 0
    while i < len(messages):
        role, text = messages[i]
        if role == "user":
            lines.append(f"> {text}")
            if i + 1 < len(messages) and messages[i + 1][0] == "assistant":
                lines.append(messages[i + 1][1])
                i += 2
            else:
                i += 1
        else:
            lines.append(text)
            i += 1
        lines.append("")
    return "\n".join(lines)


def find_jsonl_files(source_dir):
    """Walk source_dir and yield all .jsonl files (skip subagents)."""
    source = Path(source_dir)
    for jsonl_path in sorted(source.rglob("*.jsonl")):
        if "subagents" in jsonl_path.parts:
            continue
        yield jsonl_path


def main():
    parser = argparse.ArgumentParser(description="Convert Cursor Agent JSONL to MemPalace transcripts")
    parser.add_argument("source_dir", help="Root folder with agent-transcripts")
    parser.add_argument("output_dir", help="Output folder for converted transcripts")
    parser.add_argument("--developer", required=True, help="Developer name for wing tagging")
    parser.add_argument("--incremental", action="store_true", help="Skip already-converted files")
    args = parser.parse_args()

    source = Path(args.source_dir)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    if not source.exists():
        print(f"Error: source directory not found: {source}")
        sys.exit(1)

    converted = 0
    skipped = 0
    empty = 0

    for jsonl_path in find_jsonl_files(source):
        session_id = jsonl_path.stem
        out_file = output / f"{args.developer}_{session_id}.txt"

        if args.incremental and out_file.exists():
            skipped += 1
            continue

        transcript = convert_jsonl(jsonl_path)
        if transcript is None:
            empty += 1
            continue

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(transcript)
        converted += 1

    print(f"Done: {converted} converted, {skipped} skipped, {empty} empty/too-short")
    print(f"Output: {output}")
    if converted > 0:
        print(f"\nNext step:")
        print(f"  mempalace mine {output} --mode convos --wing wing_{args.developer}")


if __name__ == "__main__":
    main()
