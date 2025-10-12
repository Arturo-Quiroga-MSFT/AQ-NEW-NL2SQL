# NL2SQL Azure AI Universal – Code Audit & Quick Wins (2025-10-12)

## Scope
Focused exclusively on `nl2sql_azureai_universal` subtree (Teams bot + universal Azure AI Agents NL→SQL pipeline). Covers structure inventory, dependency manifests, runtime entrypoints, container build, configuration, and implemented hardening improvements (“quick wins”).

---
## Component Overview
| Area | Key Files | Notes |
|------|-----------|-------|
| Service Host | `start_server.py` | aiohttp + `/api/messages` (Bot Framework) + lightweight `/healthz` middleware. |
| Teams Integration | `teams_nl2sql_agent.py` | Command parsing, Adaptive Cards, session thread mapping, reset commands. |
| Core Pipeline | `nl2sql_main.py` | 3-agent architecture (intent, SQL, insights), token accounting, schema loading, execution. |
| Presentation | `adaptive_cards.py` | Rich Adaptive Card templates (success, error, welcome, help) with truncation added. |
| Data / Execution | `schema_reader.py`, `sql_executor.py` | Schema caching + pyodbc execution (unchanged in this pass). |
| Deployment | `Dockerfile`, `deploy_to_aca.sh`, `azure.config`, `startup.sh` | Multi-stage image, non-root, healthcheck; App Service config fallback. |
| Maintenance Scripts | `cleanup_old_agents.py`, `list_agents.py`, `run_teams_bot.sh` | Agent cleanup; local dev start. |
| Pricing / Config | `azure_openai_pricing.json`, `.env.example`, `config.py` | Centralized settings introduced (new). |

---
## Dependency Manifests
- Dev / flexible: `requirements.txt` (some `>=` ranges)
- Production / pinned: `requirements-production.txt` (locks Azure AI betas, pyodbc, auth libs)
- Critical stacks: Microsoft Agents SDK (0.4.0), Azure AI Projects/Inference (beta), `aiohttp`, `pyodbc`, `pydantic`, `python-dotenv`.

Risk: Beta Azure AI SDKs may introduce breaking changes; monitor release notes.

---
## Quick Wins Implemented (2025-10-12)
### 1. Centralized Configuration (`config.py`)
- Introduced `Settings` dataclass with:
  - `project_endpoint`, `model_deployment_name`
  - `session_ttl_seconds` (default 1800)
  - `max_sql_preview_chars` (default 800)
  - `allow_non_select` (default False; enables strict read-only)
- Simplifies future extension (feature flags, remote config).

### 2. Session Lifecycle & Memory Control
- `_SESSION_AGENTS` entries now include `last_used` timestamp.
- Added `_cleanup_stale_sessions()` executed per query call to evict idle sessions > TTL.
- Prevents unbounded growth for long-lived bot deployments.

### 3. Insights Thread Reuse
- `generate_insights()` now reuses the conversation thread (if provided) instead of creating a new thread every invocation.
- Reduces token usage and preserves broader context continuity.

### 4. Read-Only SQL Enforcement
- Added `is_read_only_sql()` guard; rejects non-`SELECT` / non-CTE queries unless `ALLOW_NON_SELECT_SQL=true` set.
- Enforced both in public `execute_and_format()` and CLI execution path.
- Mitigates accidental destructive statements from LLM drift.

### 5. Typed API Contracts
- Introduced `TypedDict` structures: `ExecutionResult`, `NL2SQLResult` for stronger IDE hints and safer refactors.

### 6. Adaptive Card Payload Safety
- Added SQL truncation with configurable limit (`MAX_SQL_PREVIEW_CHARS`).
- Displays footer fact `SQL: truncated` when applied.
- Reduces risk of Teams payload size overflows / user scroll fatigue.

### 7. Safer Agent Cleanup
- `cleanup_session_agents()` skips non-agent metadata keys (`last_used`).

---
## Non-Modified but Assessed Areas
| Topic | Current Status | Recommendation |
|-------|----------------|----------------|
| Cost / Pricing | USD pricing via JSON or env; single currency | Optional: multi-currency support like root edition. |
| Retry Strategy | Single forced reset attempt on assistant missing | Consider exponential backoff + telemetry counters. |
| Schema Caching | External module (unchanged) | Add TTL logging & metrics (hit/miss). |
| Adaptive Cards | Rich & comprehensive | Add optional compact mode for mobile. |
| Logging | `print()` debugging style | Consider structured logging (JSON) for production ingestion. |
| Security | No destructive SQL (guard added) | Add allowlist/denylist regex if compliance requires. |

---
## Risks & Mitigations
| Risk | Impact | Mitigation Implemented | Future Action |
|------|--------|------------------------|---------------|
| Unbounded sessions | Memory creep | TTL eviction added | Optional periodic async task. |
| Destructive SQL execution | Data integrity | Read-only guard added | Add explicit audit log. |
| Large card payloads | Teams rejection / truncation | SQL truncation | Consider result row truncation toggle per user preference. |
| Beta SDK surface changes | Runtime failures | None intrinsic | Track version pin upgrades & create smoke tests. |
| Lost insight context (old design) | Higher token use | Thread reuse now | N/A. |

---
## Configuration Environment Variables (New / Relevant)
| Variable | Default | Description |
|----------|---------|-------------|
| `SESSION_TTL_SECONDS` | 1800 | Idle seconds before session agents auto-cleaned. |
| `MAX_SQL_PREVIEW_CHARS` | 800 | Adaptive Card SQL preview truncation threshold. |
| `ALLOW_NON_SELECT_SQL` | false | If true, bypasses read-only guard (use with caution). |

---
## Suggested Next Enhancements (Not Implemented Yet)
1. Add pytest suite for:
   - `is_read_only_sql` edge cases
   - Session TTL eviction
   - SQL truncation formatting
2. Structured logging adapter (e.g., `logging` + JSON handler).
3. Observability hooks: latency per stage, token usage histogram.
4. Optional metrics endpoint or integration with Azure Monitor / App Insights.
5. CTE + multi-statement safe splitter (guard against accidental second statement).
6. Replace simple regex sanitization with `sqlparse` for robust parsing (optional).

---
## Verification Notes
- Post-patch lint/compile check: no errors reported for modified files (`nl2sql_main.py`, `adaptive_cards.py`, `config.py`).
- No runtime tests executed in this pass (lack of direct DB/agent context in environment). Recommended to add a lightweight smoke script with mocks.

---
## File Change Summary
| File | Added / Modified | Purpose |
|------|------------------|---------|
| `config.py` | Added | Central settings + environment parsing. |
| `nl2sql_main.py` | Modified | Session TTL, read-only enforcement, TypedDicts, thread reuse, central settings. |
| `adaptive_cards.py` | Modified | SQL truncation & indicator. |

---
## How to Toggle New Behaviors
```bash
# Allow write queries (NOT recommended in production)
export ALLOW_NON_SELECT_SQL=true

# Shorten session TTL to 5 minutes for aggressive cleanup
env SESSION_TTL_SECONDS=300 python start_server.py

# Increase SQL preview to 1500 characters
export MAX_SQL_PREVIEW_CHARS=1500
```

---
## High-Level Impact
| Category | Improvement |
|----------|------------|
| Security | Read-only enforcement reduces blast radius. |
| Reliability | Session TTL curbs resource growth. |
| Cost Efficiency | Insights reuse lowers token consumption. |
| UX | Truncated SQL prevents oversized cards. |
| Maintainability | Central config & TypedDicts clarify contracts. |

---
## Acknowledgements
Generated automatically based on repository state and modifications performed on 2025-10-12.

---
*End of Report*
