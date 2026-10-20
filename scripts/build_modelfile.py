"""Build Modelfile SYSTEM prompt from local patrik_2026.txt export."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "patrik_2026.txt"
OUT = ROOT / "Modelfile"

SKIP_SUBSTR = (
    "hsm pin",
    "so pin",
    "orosanmälan",
    "lvu",
    "foster care",
    "social service",
    "soc. called",
)


def clean_messages(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        match = re.match(r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\]\s*(.*)$", raw)
        if not match:
            continue
        msg = match.group(1).strip()
        if not msg:
            continue
        low = msg.lower()
        if any(s in low for s in SKIP_SUBSTR):
            continue
        if msg.startswith("[file:") or msg.startswith("[attachment:"):
            continue
        msg = re.sub(r"\s*\[file:.*?\]", "", msg)
        msg = re.sub(r"\s*\[attachment:.*?\]", "", msg)
        msg = re.sub(r"<https?://[^>]+>", "", msg)
        msg = re.sub(r"https?://\S+", "", msg)
        msg = re.sub(r":[a-z0-9_+]+:", "", msg)
        msg = re.sub(r"\s+", " ", msg).strip()
        if len(msg) < 3 or len(msg) > 280:
            continue
        if msg not in lines:
            lines.append(msg)
    return lines


def pick_sample(messages: list[str], limit: int = 40) -> list[str]:
    short = [m for m in messages if len(m) < 80][:25]
    medium = [m for m in messages if 80 <= len(m) <= 220][:25]
    sample: list[str] = []
    for a, b in zip(short, medium):
        sample.extend([a, b])
    return sample[:limit]


def main() -> None:
    if not EXPORT.exists():
        raise SystemExit(f"missing export: {EXPORT}")

    messages = clean_messages(EXPORT.read_text(encoding="utf-8"))
    sample = pick_sample(messages)
    examples = "\n".join(f"- {s}" for s in sample)

    modelfile = f"""# Patrik — colleague persona on top of gemma4:e2b
# Create with: ollama create patrik -f Modelfile
# Style examples derived from local Slack export (patrik_2026.txt; gitignored).
# Regenerate with: python scripts/build_modelfile.py

FROM gemma4:e2b

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 8192

SYSTEM \"\"\"
You are Patrik, a software engineer colleague chatting at work (often Slack).

Tone and style — match these closely:
- Casual, concise teammate voice. Short messages are fine ("Nice!", "Cool", "ok", "Yes").
- Collaborative and practical: ping people, offer to take tickets, ask clarifying questions, suggest next steps.
- Dry understated humor and light irony; occasional wink-style asides without being mean.
- Mix English with rare Swedish words when natural (e.g. Kundkännedom). Prefer English.
- Talk about work concretely: MRs, tickets, sprints, mobbing, boards, pipes, APIs, tests, coverage, office days.
- Ask direct questions when you need something: approvals, who joins a meeting, status, ownership.
- Sound human: share light personal context sparingly (office plans, lunch) without oversharing.
- Never mention you are an AI or language model. Stay in character as Patrik.
- Do not invent secrets, credentials, PINs, or internal access details.

Example messages that sound like you:
{examples}
\"\"\"
"""
    OUT.write_text(modelfile, encoding="utf-8")
    print(f"wrote {OUT} ({len(sample)} examples from {len(messages)} cleaned messages)")


if __name__ == "__main__":
    main()
