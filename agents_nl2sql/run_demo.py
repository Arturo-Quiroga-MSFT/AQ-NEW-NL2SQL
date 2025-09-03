from __future__ import annotations
import argparse
from .state import Flags
from .nodes import ingest, schema_ctx, intent, sql_gen, sanitize, execute

try:
    from .graph import build as build_graph  # type: ignore
    _HAS_GRAPH = True
except Exception:
    _HAS_GRAPH = False


def main() -> int:
    p = argparse.ArgumentParser(description="Agents NL2SQL Demo")
    p.add_argument("--query", required=True, help="Natural language question or raw SQL if --explain-only")
    p.add_argument("--no-exec", action="store_true", help="Do not execute generated SQL")
    p.add_argument("--no-reasoning", action="store_true")
    p.add_argument("--explain-only", action="store_true", help="Treat input as SQL and only sanitize/preview")
    p.add_argument("--refresh-schema", action="store_true")
    p.add_argument("--use-graph", action="store_true", help="Use LangGraph orchestrator if available")
    args = p.parse_args()

    flags = Flags(no_exec=args.no_exec, no_reasoning=args.no_reasoning,
                  explain_only=args.explain_only, refresh_schema=args.refresh_schema)

    state = ingest.run(args.query, flags)
    if args.use_graph and _HAS_GRAPH:
        graph = build_graph()
        # seed: if explain-only, set sql_raw now, graph will route to sanitize
        if args.explain_only:
            tmp = schema_ctx.run(state)
            tmp.sql_raw = args.query
            out = graph.invoke(tmp)
        else:
            out = graph.invoke(schema_ctx.run(state))
        # Try to coerce graph output to our Pydantic state if needed
        if hasattr(out, "errors"):
            state = out  # already a GraphState
        elif isinstance(out, dict):
            try:
                from .state import GraphState as GS
                state = GS(**out)  # type: ignore
            except Exception:
                # fallback: abandon graph output and run linear
                state = schema_ctx.run(state)
                if state.flags.explain_only:
                    state.sql_raw = args.query
                else:
                    state = intent.run(state)
                    state = sql_gen.run(state)
                state = sanitize.run(state)
                state = execute.run(state)
    else:
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
