#!/usr/bin/env python3
"""Interactive CLI for NL2SQL — ask questions, see generated SQL and results."""
from __future__ import annotations

import sys
import os

# Ensure nl2sql_next is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.nl2sql import ask


def _format_table(columns: list, rows: list, max_col: int = 30) -> str:
    """Simple ASCII table formatter."""
    if not columns:
        return "(no results)"

    # Truncate cell values
    def trunc(v: object) -> str:
        s = str(v) if v is not None else "NULL"
        return s[:max_col] + "…" if len(s) > max_col else s

    headers = [trunc(c) for c in columns]
    data = [[trunc(v) for v in row] for row in rows]
    widths = [max(len(h), *(len(d[i]) for d in data) if data else [0]) for i, h in enumerate(headers)]

    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    hdr = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |"

    lines = [sep, hdr, sep]
    for row in data:
        lines.append("| " + " | ".join(v.ljust(w) for v, w in zip(row, widths)) + " |")
    lines.append(sep)
    lines.append(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")
    return "\n".join(lines)


def main() -> None:
    print("=== NL2SQL Interactive CLI ===")
    print("Type a question in plain English. Type 'quit' to exit.\n")

    while True:
        try:
            question = input("Question> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        print("\n⏳ Generating SQL …")
        result = ask(question)

        print(f"\n📝 SQL:\n{result['sql']}\n")

        if result["error"]:
            print(f"❌ Error: {result['error']}\n")
        else:
            print(_format_table(result["columns"], result["rows"]))
            print()


if __name__ == "__main__":
    main()
