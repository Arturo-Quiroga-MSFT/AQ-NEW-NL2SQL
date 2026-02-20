# Agent-Based Architecture — Design Notes

> Planning document for a potential multi-agent refactor of the NL2SQL pipeline.
> Written Feb 2026 while the current function-based pipeline is working well.

---

## Current Pipeline (function-based)

```
User Question
    │
    ▼
┌──────────────┐
│ Intent Router │  router.py  →  classify()
│ (LLM call #1)│
└──────┬───────┘
       │
       ├── data_query ──────────────────────┐
       │                                    ▼
       │                          ┌──────────────────┐
       │                          │ Schema Extraction│  schema.py
       │                          └────────┬─────────┘
       │                                   ▼
       │                          ┌──────────────────┐
       │                          │  SQL Generation  │  generate_sql()
       │                          │  (LLM call #2)   │
       │                          └────────┬─────────┘
       │                                   ▼
       │                          ┌──────────────────┐
       │                          │  Execute & Check │  db.py → run query
       │                          └────────┬─────────┘
       │                                   │ error?
       │                                   ▼
       │                          ┌──────────────────┐
       │                          │ Error Correction │  _generate_sql_fix()
       │                          │ (LLM call #3, #4)│  up to MAX_RETRIES
       │                          └──────────────────┘
       │
       └── admin_assist ────────────────────┐
                                            ▼
                                  ┌──────────────────┐
                                  │ Admin Assistant  │  answer_admin()
                                  │ (LLM call #2)    │
                                  └──────────────────┘
```

All of this lives in 3 Python files: `router.py`, `nl2sql.py`, `schema.py` plus `db.py` for execution.

---

## Candidate Agents

| # | Agent Name | Current Code | Responsibility |
|---|-----------|-------------|----------------|
| 1 | **Intent Classifier** | `router.classify()` | Route to data_query or admin_assist (or future modes) |
| 2 | **Schema Selector** | `schema.extract_schema()` | Pick relevant tables/columns for the question |
| 3 | **SQL Generator** | `generate_sql()` | Produce SQL from NL + schema + few-shots |
| 4 | **SQL Validator** | `_generate_sql_fix()` | Receive SQL + error, produce corrected SQL |
| 5 | **Admin Assistant** | `answer_admin()` | Answer DB-related questions without SQL |
| 6 | **Orchestrator** | `ask()` / `Conversation.ask()` | Coordinate agents, manage state, accumulate stats |

---

## Pros of Multi-Agent

- **Separation of concerns** — each agent has a focused system prompt, shorter and more precise. The current `nl2sql.py` handles generation, correction, and admin in one file.
- **Independent model selection** — use gpt-4.1 for cheap classification, gpt-5.2 for SQL generation, a smaller model for validation. Each agent picks its own model and parameters.
- **Easier to test** — unit-test each agent in isolation (e.g., "given this schema + question, does the SQL agent produce valid SQL?").
- **Composability** — easy to add new agents later (query optimizer, visualization recommender, security auditor) without modifying existing code.
- **Observability** — per-agent token counts, latency, success rates. The stats infrastructure is already in place — agents make attribution cleaner.
- **Retry isolation** — the error-correction loop is already agent-like; making it a formal agent clarifies the contract.

---

## Cons / Risks

- **Latency overhead** — every agent boundary = another LLM round-trip. The current pipeline does router → generation → (optional retries). More agents = more hops. Acceptable for demos; users notice in production.
- **Over-engineering for 2 modes** — with exactly 2 intents (data_query, admin_assist) and 1 generation path, the function-based approach is already clean. Agents shine at 5+ intents or with dynamic routing.
- **State passing complexity** — agents must share context (schema, conversation history, partial SQL). Functions pass arguments directly. Agents need a shared state object or message-passing protocol.
- **Debugging difficulty** — "why did it produce bad SQL?" becomes "which agent went wrong?" — requires good per-agent logging.
- **Framework dependency** — adopting MAF, LangGraph, or CrewAI couples the project to that framework's lifecycle. The current code is dependency-free (raw Responses API calls only).

---

## Recommendation

**Not yet — but keep the door open.**

### Why not now

1. The current architecture is already well-factored — `router.py`, `nl2sql.py`, `schema.py` are clean modules with clear boundaries. That's 80% of what agents provide, without the overhead.
2. The sweet spot for agents is dynamic routing or parallel execution (e.g., "run SQL generation AND a safety check in parallel, then merge"). There's no such need today.

### When to convert

- When a **3rd or 4th capability** is added beyond data_query / admin_assist (e.g., "explain this table", "suggest an index", "generate a chart").
- When **parallel agent execution** is needed (e.g., SQL generation + security audit simultaneously).
- When **different teams** own different stages and need independent deployability.

### How to convert (lightweight approach)

If/when the time comes, use a **framework-free** pattern:

```python
class BaseAgent:
    """Minimal agent contract."""
    name: str
    model: str

    def run(self, state: PipelineState) -> AgentResult:
        raise NotImplementedError

class PipelineState(TypedDict):
    question: str
    schema: str
    conversation_history: list
    intent: str
    sql: str | None
    results: list | None
    error: str | None
    tokens: dict

class AgentResult(TypedDict):
    output: Any
    tokens: dict
    elapsed_ms: int
```

Then a simple orchestrator:

```python
class Orchestrator:
    def run(self, question: str) -> dict:
        state = PipelineState(question=question, ...)

        # 1. Classify
        state = IntentAgent().run(state)

        # 2. Branch
        if state["intent"] == "data_query":
            state = SchemaAgent().run(state)
            state = SQLGeneratorAgent().run(state)
            if state.get("error"):
                state = SQLValidatorAgent().run(state)
        else:
            state = AdminAgent().run(state)

        return state
```

No framework required. Each agent is independently testable. State is a plain dict.

---

## Existing Agent Work (reference)

The `agents_nl2sql/` directory at the repo root contains a prior LangGraph-based implementation with:
- `graph.py` — LangGraph state graph
- `state.py` — shared state definition
- `nodes/` — individual processing nodes
- `tools/` — LangGraph tool definitions

That implementation uses a different tech stack (LangGraph + LangChain) but the architectural patterns are relevant.

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `AGENT_ARCHITECTURE.md` | This document — design notes and decision record |
| *(future)* `base.py` | Base agent class and shared types |
| *(future)* `intent_agent.py` | Intent classification agent |
| *(future)* `sql_agent.py` | SQL generation agent |
| *(future)* `validator_agent.py` | SQL error correction agent |
| *(future)* `admin_agent.py` | DB admin assistant agent |
| *(future)* `orchestrator.py` | Pipeline coordinator |

---

*Last updated: Feb 20, 2026*
