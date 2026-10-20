"""Shared cleaning for Patrik Slack export → Modelfile / training data."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "patrik_2026.txt"

SKIP_SUBSTR = (
    "hsm pin",
    "so pin",
    "orosanmälan",
    "lvu",
    "foster care",
    "social service",
    "soc. called",
)

LINE_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\]\s*(.*)$")

SYSTEM_PROMPT = """You are Patrik, a software engineer colleague chatting at work (often Slack).
Speak casually and collaboratively, short messages when natural, dry understated humor.
Ask direct questions when needed. Prefer English; rare Swedish is fine.
Never mention you are an AI or language model. Do not invent secrets or credentials."""


def clean_message(msg: str, max_len: int = 2000) -> str | None:
    msg = msg.strip()
    if not msg:
        return None
    low = msg.lower()
    if any(s in low for s in SKIP_SUBSTR):
        return None
    if msg.startswith("[file:") or msg.startswith("[attachment:"):
        return None
    msg = re.sub(r"\s*\[file:.*?\]", "", msg)
    msg = re.sub(r"\s*\[attachment:.*?\]", "", msg)
    msg = re.sub(r"<https?://[^>]+>", "", msg)
    msg = re.sub(r"https?://\S+", "", msg)
    msg = re.sub(r":[a-z0-9_+]+:", "", msg)
    msg = re.sub(r"\s+", " ", msg).strip()
    if len(msg) < 3 or len(msg) > max_len:
        return None
    # Drop obvious log dumps / huge JSON
    if msg.count("{") > 3 and len(msg) > 400:
        return None
    return msg


def load_messages(path: Path | None = None, max_len: int = 2000) -> list[tuple[str, str]]:
    """Return (timestamp, cleaned_message) pairs."""
    export = path or EXPORT
    rows: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in export.read_text(encoding="utf-8").splitlines():
        match = LINE_RE.match(raw)
        if not match:
            continue
        ts, body = match.group(1), match.group(2)
        cleaned = clean_message(body, max_len=max_len)
        if cleaned is None or cleaned in seen:
            continue
        seen.add(cleaned)
        rows.append((ts, cleaned))
    return rows
