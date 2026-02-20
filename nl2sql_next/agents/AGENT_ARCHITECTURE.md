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

## Tool-Use Architecture — Admin Assistant with Write Capabilities

> This section documents the planned evolution of the `admin_assist` mode from a
> question-answering system into a **tool-using agent** that can **read and write**
> to the database with proper security gates.

### Motivation

The current admin assistant answers questions about the schema using
its system prompt + schema context. It cannot execute queries, inspect live
data, or make changes. MCP (Model Context Protocol) tools in VS Code demonstrate
how powerful tool-equipped LLMs are — the same pattern should be available in
the app itself.

### Why Not MCP Directly?

| Consideration | MCP Server | Native Tool-Use (Responses API) |
|---------------|-----------|-------------------------------|
| Designed for | IDE integration (VS Code, etc.) | Any application |
| Transport | JSON-RPC over stdio/SSE | HTTP to Azure OpenAI |
| Client library needed | Yes (Python MCP client) | No — built into SDK |
| Security gates | Not built-in — your responsibility | Not built-in — your responsibility |
| DB connection | Separate server process | Reuse existing pyodbc in `db.py` |
| Tool definitions | MCP schema | OpenAI function schema (JSON) |
| Dependency footprint | MCP SDK + server process | Zero new dependencies |

**Decision:** Use **Azure OpenAI Responses API native tool-use** (function calling).
The app already has direct DB access via pyodbc, and the Responses API supports
`tools=` parameter natively — no extra protocol layer needed.

### Architecture

```
User: "Add an index on FactOrders.OrderDateKey"
                │
                ▼
    ┌───────────────────────────────────┐
    │  LLM (Responses API + tools=[])   │
    │  Sees: list_tables, describe_table│
    │  run_read_query, run_write_query, │
    │  run_ddl                          │
    └───────────┬───────────────────────┘
                │ returns tool_call:
                │ run_ddl(sql="CREATE INDEX ...", explanation="...")
                ▼
    ┌───────────────────────────────────┐
    │  Security Gate (core/tools.py)     │
    │  Classify operation tier:          │
    │    T0 (read) → auto-execute        │
    │    T1 (write) → needs approval     │
    │    T2 (DDL) → needs approval       │
    │    T3 (destructive) → BLOCKED      │
    └───────────┬───────────────────────┘
                │
        ┌───────┴──────────────────┐
        │                          │
   T0: auto                  T1/T2: approval needed
        │                          │
        ▼                          ▼
   Execute via             Frontend shows confirmation
   pyodbc, return          dialog (SQL + explanation +
   result to LLM           impact warning)
                                   │
                              User: Approve / Reject
                                   │
                                   ▼
                              Execute via pyodbc
                              Return result to LLM
                                   │
                                   ▼
                          LLM generates final
                          response to user
```

### Security Tiers

| Tier | Operations | Gate | Risk | Examples |
|------|-----------|------|------|----------|
| **T0: Free** ✅ | SELECT, SHOW, DESCRIBE, list_tables, describe_table | Auto-execute | None — read-only | "Show all tables", "Describe DimCustomer" |
| **T1: Review** ✅ | INSERT, UPDATE, DELETE (data modification) | Show SQL + Approve button | Low — data modification | "Insert a test customer", "Update product price" |
| **T2: Approve** | ALTER, CREATE INDEX, CREATE VIEW (DDL) | Show SQL + impact warning + Approve | Medium — schema change | "Add index", "Add column to DimProduct" |
| **T3: Blocked** | DROP TABLE, TRUNCATE, DROP DATABASE, xp_, sp_ | Hard block — never execute | Critical — irreversible | "Drop the customers table", "Truncate all facts" |

### Tool Definitions

```python
ADMIN_TOOLS = [
    {
        "type": "function",
        "name": "list_tables",
        "description": "List all tables in the database with their schemas, row counts, and types",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "type": "function",
        "name": "describe_table",
        "description": "Show column names, data types, nullability, and constraints for a table",
        "parameters": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Schema-qualified table name, e.g. dim.DimCustomer"
                }
            },
            "required": ["table_name"]
        }
    },
    {
        "type": "function",
        "name": "run_read_query",
        "description": "Execute a read-only SELECT query against the database",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "The SELECT query to execute"}
            },
            "required": ["sql"]
        }
    },
    {
        "type": "function",
        "name": "run_write_query",
        "description": "Execute a data modification statement (INSERT, UPDATE, DELETE). "
                       "Requires user approval before execution.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "The SQL write statement"},
                "explanation": {
                    "type": "string",
                    "description": "Plain English explanation of what this will do and why"
                }
            },
            "required": ["sql", "explanation"]
        }
    },
    {
        "type": "function",
        "name": "run_ddl",
        "description": "Execute a DDL statement (CREATE INDEX, ALTER TABLE, CREATE VIEW). "
                       "Requires user approval before execution.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "The DDL statement"},
                "explanation": {
                    "type": "string",
                    "description": "What this changes in the schema and the expected impact"
                }
            },
            "required": ["sql", "explanation"]
        }
    },
]
```

### Conversation Flow (approval path)

```
Step 1 — User asks:
    "Add an index on FactOrders for OrderDateKey to speed up date range queries"

Step 2 — LLM responds with tool_call:
    tool_call(run_ddl,
        sql="CREATE NONCLUSTERED INDEX IX_FactOrders_OrderDateKey
             ON fact.FactOrders(OrderDateKey)",
        explanation="Creates a non-clustered index on the OrderDateKey column
                    in FactOrders to improve date-range query performance")

Step 3 — Backend classifies: DDL → Tier 2 → needs approval
    API returns:
    {
        "pending_approval": true,
        "approval_id": "abc-123",
        "tool_name": "run_ddl",
        "sql": "CREATE NONCLUSTERED INDEX ...",
        "explanation": "Creates a non-clustered index ...",
        "tier": "T2",
        "warning": "This modifies the database schema."
    }

Step 4 — Frontend shows confirmation card:
    ┌─────────────────────────────────────────────┐
    │  ⚠️  Schema Change — Approval Required       │
    ├─────────────────────────────────────────────┤
    │  CREATE NONCLUSTERED INDEX                  │
    │  IX_FactOrders_OrderDateKey                 │
    │  ON fact.FactOrders(OrderDateKey)           │
    ├─────────────────────────────────────────────┤
    │  Creates a non-clustered index on the       │
    │  OrderDateKey column to improve date-range  │
    │  query performance.                         │
    ├─────────────────────────────────────────────┤
    │  [✅ Approve]         [❌ Reject]            │
    └─────────────────────────────────────────────┘

Step 5 — User clicks Approve
    Frontend: POST /api/approve { "approval_id": "abc-123" }

Step 6 — Backend executes via pyodbc, returns result to LLM

Step 7 — LLM generates final response:
    "Done. Index IX_FactOrders_OrderDateKey has been created on
     fact.FactOrders(OrderDateKey). Date range queries on FactOrders
     should now be significantly faster."
```

### Implementation Plan

| Phase | What | Files | Risk |
|-------|------|-------|------|
| **Phase 1** ✅ | Read-only tools: `list_tables`, `describe_table`, `run_read_query` | `core/tools.py` (new), update `nl2sql.py` admin path | Zero — no writes |
| **Phase 2** ✅ | Approval UI: frontend confirmation dialog + `/api/approve` endpoint | `api.py`, `App.tsx`, `App.css` | Zero — UI only |
| **Phase 3** ✅ | Write tools: `run_write_query` with T1 gate | `core/tools.py`, `db.py` | Low — guarded by approval |
| **Phase 4** | DDL tools: `run_ddl` with T2 gate + audit logging | `core/tools.py`, `core/audit.py` (new) | Medium — schema changes |
| **Phase 5** ✅ | Containerization + ACA deployment | `Dockerfile`, `.dockerignore`, `deploy-aca.sh`, `api.py` | Low — infra only |

### Phases 1-3: Implementation Notes (completed)

Phases 1-3 are fully implemented. Key implementation details:

**Tool-use loop** (`core/nl2sql.py :: answer_admin()`):
- Uses Azure OpenAI Responses API with `tools=TOOLS_ALL` parameter
- Standard loop: call LLM → check for `function_call` items in `response.output` → execute tools → feed results back → repeat until text response
- Returns 3-tuple: `(text, usage_dict, pending_approval_or_None)`

**Mixed-batch handling**: When the LLM returns multiple tool calls in one response
(e.g., a read + a write), safe tools (T0) execute immediately, and the loop pauses
at the first approval-required tool (T1+). After approval/rejection, `resume_after_approval()`
replays the pending state and continues the loop.

**Approval flow** (`api.py`):
- `_pending_approvals: dict[str, dict]` — in-memory store keyed by UUID
- `POST /api/approve` — accepts `{approval_id, approved}`, executes or rejects, returns LLM's final response
- Frontend `ApprovalCard` component shows SQL + explanation + approve/reject buttons

**Router fix**: `core/router.py` updated to classify INSERT/UPDATE/DELETE as `admin_assist`
(previously misrouted to `data_query`).

**Prompt strengthening**: Admin system prompt includes "CRITICAL RULE FOR WRITE OPERATIONS" —
forces the LLM to always invoke `run_write_query` tool instead of asking for text-based confirmation.

**Actual tool definitions** are in `core/tools.py :: TOOLS_ALL` (4 tools: `list_tables`,
`describe_table`, `run_read_query`, `run_write_query`). Security classification is in
`TOOL_TIERS` dict. `_is_write_dml()` validates SQL before executing writes.

### Audit Logging (Phase 4)

Every write/DDL operation gets logged:

```python
@dataclass
class AuditEntry:
    timestamp: datetime
    user: str          # session_id for now, user identity later
    tool: str          # "run_write_query" or "run_ddl"
    sql: str           # the exact SQL executed
    explanation: str   # LLM's explanation
    tier: str          # T1, T2
    approved: bool     # user approved?
    result: str        # "success", "error: ...", or "rejected"
    rows_affected: int # for writes
```

Store in a local SQLite file (`audit.db`) or a dedicated Azure SQL table.

### Relationship to Agent Architecture

This tool-use implementation is the natural **first agent** in the pipeline.
The admin assistant with tools becomes an autonomous agent that:
- Receives a goal (user question)
- Plans which tools to call
- Executes tools in a loop
- Composes a response

If the multi-agent refactor happens later, this becomes `AdminToolAgent` with
zero code changes — the tool-use loop is already agent-shaped.

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `AGENT_ARCHITECTURE.md` | This document — design notes and decision record |
| *(future)* `base.py` | Base agent class and shared types |
| *(future)* `intent_agent.py` | Intent classification agent |
| *(future)* `sql_agent.py` | SQL generation agent |
| *(future)* `validator_agent.py` | SQL error correction agent |
| *(future)* `admin_agent.py` | DB admin assistant agent with tools |
| *(future)* `orchestrator.py` | Pipeline coordinator |

---

---

## Deployment

The entire application (FastAPI backend + React frontend) is containerized and
deployed to **Azure Container Apps**. This is orthogonal to the agent architecture —
whether the pipeline uses functions or agents, the deployment model is the same.

See the main `README.md` for full containerization and ACA deployment details.

- **Live URL**: `https://aq-nl2sql-next-app.orangegrass-878e4c2c.eastus2.azurecontainerapps.io`
- **Auth**: System-assigned managed identity → `DefaultAzureCredential` → Azure SQL
- **Secrets**: Azure OpenAI API key stored as ACA secret

---

*Last updated: Feb 21, 2026*
