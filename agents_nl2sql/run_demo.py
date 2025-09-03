from __future__ import annotations
import argparse
from .state import Flags
from .nodes import ingest, schema_ctx, intent, sql_gen, sanitize, execute


def main() -> int:
    p = argparse.ArgumentParser(description="Agents NL2SQL Demo")
    p.add_argument("--query", required=True, help="Natural language question or raw SQL if --explain-only")
    p.add_argument("--no-exec", action="store_true", help="Do not execute generated SQL")
    p.add_argument("--no-reasoning", action="store_true")
    p.add_argument("--explain-only", action="store_true", help="Treat input as SQL and only sanitize/preview")
    p.add_argument("--refresh-schema", action="store_true")
    args = p.parse_args()

    flags = Flags(no_exec=args.no_exec, no_reasoning=args.no_reasoning,
                  explain_only=args.explain_only, refresh_schema=args.refresh_schema)

    state = ingest.run(args.query, flags)
    state = schema_ctx.run(state)

    if state.flags.explain_only:
        state.sql_raw = args.query
    else:
        state = intent.run(state)
        state = sql_gen.run(state)

    state = sanitize.run(state)
    state = execute.run(state)

    # Print a compact output
    print("=== NL2SQL Agents Demo ===")
    if state.errors:
        print("Errors:")
        for e in state.errors:
            print(" -", e)
    print("\nSchema ctx (truncated):", (state.schema_context[:200] + "...") if state.schema_context else "<none>")
    print("\nSQL (sanitized):\n", state.sql_sanitized or "<none>")
    print("\nExecution preview:\n", state.execution_result.preview or "<none>")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
