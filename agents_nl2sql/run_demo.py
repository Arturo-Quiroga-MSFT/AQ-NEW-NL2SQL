from __future__ import annotations
import datetime
import decimal
def convert_dates(obj):
    """Recursively convert date/datetime/decimal objects in dicts/lists to serializable types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: convert_dates(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_dates(i) for i in obj]
    elif isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    elif isinstance(obj, decimal.Decimal):
        return float(obj)
    else:
        return obj
import argparse
import os
import json
from agents_nl2sql.state import Flags
from .nodes import ingest, schema_ctx, intent, sql_gen, sanitize, execute
from .nodes import reasoning

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
                    if not state.flags.no_reasoning:
                        state = reasoning.run(state)
                    state = sql_gen.run(state)
                state = sanitize.run(state)
                state = execute.run(state)
    else:
        state = schema_ctx.run(state)
        if state.flags.explain_only:
            state.sql_raw = args.query
        else:
            state = intent.run(state)
            if not state.flags.no_reasoning:
                state = reasoning.run(state)
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
    print("\nReasoning:\n", state.reasoning or "<none>")
    print("\nSQL (sanitized):\n", state.sql_sanitized or "<none>")
    print("\nExecution preview:\n", state.execution_result.preview or "<none>")

    # Persist results under RESULTS/
    try:
        os.makedirs("RESULTS", exist_ok=True)
        # Build a safe filename stem from the query
        slug = "".join(ch if ch.isalnum() or ch in (" ", "_", "-") else "_" for ch in state.user_query).strip()
        slug = "_".join(slug.split())
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"agents_nl2sql_run_{slug}_{ts}"

        # Cost computation if pricing available
        usage = state.token_usage
        pricing = state.pricing
        cost_line = ""
        if pricing and pricing.input_per_1k is not None and pricing.output_per_1k is not None:
            cost_in = (usage.prompt or 0) / 1000.0 * float(pricing.input_per_1k)
            cost_out = (usage.completion or 0) / 1000.0 * float(pricing.output_per_1k)
            cost_total = cost_in + cost_out
            currency = pricing.currency or "USD"
            cost_line = (
                f"Token usage: prompt={usage.prompt}, completion={usage.completion}, total={usage.total}\n"
                f"Pricing: in/1k={pricing.input_per_1k} {currency}, out/1k={pricing.output_per_1k} {currency} (source={pricing.source})\n"
                f"Estimated cost: in={cost_in:.4f} {currency}, out={cost_out:.4f} {currency}, total={cost_total:.4f} {currency}\n"
            )
        else:
            cost_line = f"Token usage: prompt={usage.prompt}, completion={usage.completion}, total={usage.total}\n"

        # Compose run log text
        lines = []
        lines.append("=== NL2SQL Agents Demo Run ===")
        lines.append(f"Run ID: {state.run_id}")
        lines.append(f"Started: {datetime.datetime.fromtimestamp(state.started_at).isoformat()}")
        lines.append("")
        lines.append(f"Query: {state.user_query}")
        lines.append(f"Flags: no_exec={state.flags.no_exec}, no_reasoning={state.flags.no_reasoning}, explain_only={state.flags.explain_only}, refresh_schema={state.flags.refresh_schema}")
        if state.errors:
            lines.append("")
            lines.append("Errors:")
            for e in state.errors:
                lines.append(f" - {e}")
        lines.append("")
        sc = (state.schema_context or "").strip()
        lines.append("Schema context:")
        lines.append(sc if sc else "<none>")
        lines.append("")
        ie = state.intent_entities
        lines.append("Intent/Entities:")
        lines.append(json.dumps(ie, indent=2) if ie is not None else "<none>")
        lines.append("")
        lines.append("Reasoning:")
        lines.append((state.reasoning or "<none>").strip())
        lines.append("")
        lines.append("SQL (sanitized):")
        lines.append((state.sql_sanitized or "<none>").strip())
        lines.append("")
        lines.append("Execution preview:")
        lines.append((state.execution_result.preview or "<none>").strip())
        lines.append("")
        lines.append(cost_line.rstrip())

        txt_path = os.path.join("RESULTS", f"{base}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        # JSON sidecar with exact rows if any
        rows = state.execution_result.rows or []
        if rows:
            json_path = os.path.join("RESULTS", f"{base}.json")
            # Convert all date/datetime objects to strings before dumping
            rows_serializable = convert_dates(rows)
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(rows_serializable, jf, ensure_ascii=False, indent=2)
            print(f"\nArtifacts: wrote {os.path.basename(txt_path)} and {os.path.basename(json_path)} to RESULTS/")
        else:
            print(f"\nArtifact: wrote {os.path.basename(txt_path)} to RESULTS/")
    except Exception as ex:
        print(f"\n[warn] Failed to persist run artifacts: {ex}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
