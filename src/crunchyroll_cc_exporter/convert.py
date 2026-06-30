from __future__ import annotations

import html
import re

_TIMESTAMP_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})"
    r"\s+-->\s+"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}\.\d{3}|\d{1,2}:\d{2}\.\d{3})"
    r"(?:\s+.*)?"
)


def _clean_payload(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r"</?[^>]+>", "", text)
    text = re.sub(r"\{\\[^}]*\}", "", text)
    lines = [line.strip() for line in text.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def _convert_timestamp(timestamp: str) -> str:
    timestamp = timestamp.strip()
    if re.match(r"^\d{1,2}:\d{2}\.\d{3}$", timestamp):
        timestamp = "00:" + timestamp
    return timestamp.replace(".", ",")


def vtt_to_srt(vtt_text: str) -> str:
    """Convert a WebVTT caption file to SRT.

    The converter intentionally strips simple HTML/VTT styling tags while
    preserving text, role labels, and line breaks.
    """
    normalized = vtt_text.replace("\ufeff", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if lines and lines[0].strip().startswith("WEBVTT"):
        lines = lines[1:]

    blocks: list[str] = []
    current: list[str] = []
    skip_block = False
    for line in lines:
        stripped = line.strip()
        if not current and stripped in {"NOTE", "STYLE", "REGION"}:
            skip_block = True
        if stripped == "":
            if current and not skip_block:
                blocks.append("\n".join(current))
            current = []
            skip_block = False
        elif not skip_block:
            current.append(line)
    if current and not skip_block:
        blocks.append("\n".join(current))

    output: list[str] = []
    index = 1
    for block in blocks:
        block_lines = block.split("\n")
        match = None
        timestamp_line_index = None
        for i, line in enumerate(block_lines[:3]):
            match = _TIMESTAMP_RE.match(line.strip())
            if match:
                timestamp_line_index = i
                break
        if match is None or timestamp_line_index is None:
            continue
        payload = _clean_payload("\n".join(block_lines[timestamp_line_index + 1 :]))
        if not payload:
            continue
        output.append(str(index))
        output.append(
            f"{_convert_timestamp(match.group('start'))} --> "
            f"{_convert_timestamp(match.group('end'))}"
        )
        output.append(payload)
        output.append("")
        index += 1
    return "\n".join(output)
