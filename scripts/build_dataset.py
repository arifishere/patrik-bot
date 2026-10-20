"""Turn patrik_2026.txt into a Patrik-messages-only training JSONL.

Formats chosen for common auto-detect (HF / Unsloth / LlamaFactory-style UIs):
  patrik_dataset.jsonl  — {"text": "<message>"}
  patrik_sft_chat.jsonl — {"messages": [{"role": "assistant", "content": "<message>"}]}
  patrik_sft_text.jsonl — same as patrik_dataset.jsonl

Usage:
  python scripts/build_dataset.py
"""

from __future__ import annotations

import json
from pathlib import Path

from patrik_export import EXPORT, load_messages

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data"


def main() -> None:
    if not EXPORT.exists():
        raise SystemExit(f"missing export: {EXPORT}")

    rows = load_messages()
    if not rows:
        raise SystemExit("no usable messages after cleaning")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    text_path = OUT_DIR / "patrik_sft_text.jsonl"
    chat_path = OUT_DIR / "patrik_sft_chat.jsonl"
    canon_path = OUT_DIR / "patrik_dataset.jsonl"
    meta_path = OUT_DIR / "patrik_dataset.meta.json"

    with text_path.open("w", encoding="utf-8") as text_f, chat_path.open(
        "w", encoding="utf-8"
    ) as chat_f, canon_path.open("w", encoding="utf-8") as canon_f:
        for _, message in rows:
            text_line = json.dumps({"text": message}, ensure_ascii=False)
            chat_line = json.dumps(
                {"messages": [{"role": "assistant", "content": message}]},
                ensure_ascii=False,
            )
            text_f.write(text_line + "\n")
            canon_f.write(text_line + "\n")
            chat_f.write(chat_line + "\n")

    meta = {
        "source": EXPORT.name,
        "format": {
            "patrik_dataset.jsonl": "text",
            "patrik_sft_text.jsonl": "text",
            "patrik_sft_chat.jsonl": "messages",
        },
        "examples": len(rows),
        "notes": (
            "Patrik-only messages. Use patrik_dataset.jsonl (column: text) for "
            "auto-detect, or patrik_sft_chat.jsonl (column: messages) for chat SFT. "
            "No system/user fields."
        ),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {len(rows)} examples -> {OUT_DIR}")
    for path in (canon_path, text_path, chat_path, meta_path):
        print(f"  {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
