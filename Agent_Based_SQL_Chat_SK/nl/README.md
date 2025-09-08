# NL Interpreter Layer

Goal: Provide a generic, extensible natural language → intent → DSL → SQL pipeline for day-to-day DB admin tasks (read, inspect, modify schema, manage indexes, perform diagnostics) with safety, auditability, and multi-strategy parsing.

## Architecture Layers
1. Normalization & Preprocess
2. Deterministic Rules (Pattern Catalog)
3. Semantic Similarity (Embeddings)
4. Guarded LLM Fallback (Optional Feature Flag)
5. Slot Filling & Metadata Enrichment
6. Intermediate DSL (Intent Model)
7. Risk Analysis & Policy Gate
8. SQL Rendering
9. Audit & Active Learning (Unknown / Clarification Logs)

## Intent Catalog (Initial)
| Intent | Description | Example NL |
|--------|-------------|-----------|
| list_tables | List all base tables (optionally filter by pattern) | "show schema", "list all tables" |
| describe_table | Show column definitions | "describe table dim_customer" |
| row_count | Count rows in a table | "row count for fact_loans" |
| list_indexes | List indexes for a table | "list indexes on dim_customer" |
| create_table | Create a new table with columns | "create table staging.payments with columns id int, amount decimal(18,2)" |
| drop_table | Drop an existing table (if exists) | "drop table staging.payments" |
| add_column | Add a column | "add column notes varchar(100) to staging.payments" |
| drop_column | Drop a column | "drop column notes from staging.payments" |
| create_index | Create an index | "create index on staging.payments(id, created_at)" |
| star_overview | Star schema summary | "star overview" |
| orphan_check | Foreign key orphan detection | "check orphan facts" |
| null_density | Column null density analysis | "null density for fact_loans" |
| top_values | Top value distribution | "top values for dim_region.region_name" |
| unknown | Fallback when intent cannot be derived | any unsupported phrase |

## Files
- `normalize.py` – text normalization, typo fixes, tokenization.
- `intents.yaml` – data-driven catalog for deterministic & semantic mapping.
- `rules.py` – applies regex/slot patterns.
- `embeddings.py` – loads embedding model, caches vectors, similarity search.
- `classifier.py` – orchestrates rule → semantic → LLM fallback.
- `dsl.py` – dataclasses for NLAction, Clarification, Unknown.
- `renderer.py` – convert NLAction into parameterized SQL (with safety guards).
- `evaluation.md` – guidelines for test coverage & accuracy metrics.

## Safety Principles
- Never execute raw user text directly.
- All SQL must come from renderer functions with explicit parameter binding where possible.
- Assign risk levels: high (DROP/TRUNCATE), medium (ALTER), low (SELECT/describe).
- Require explicit confirmation for high/medium before execution.

## Extensibility
Adding a new intent:
1. Add an entry to `intents.yaml` with patterns and semantic_aliases.
2. Implement any slot post-processing function if needed.
3. Map to a renderer function producing safe SQL.
4. Add unit tests covering rule + semantic + ambiguity cases.

## Roadmap (Incremental)
- Phase 1: Extract existing rules into catalog + DSL + tests.
- Phase 2: Add semantic similarity with sentence-transformers (local) or Azure embeddings.
- Phase 3: Add LLM fallback (strict JSON schema) behind environment feature flag.
- Phase 4: Active learning log & periodic catalog updates.
- Phase 5: Add advanced intents (index fragmentation, statistics stale check, size by table, partition usage).

## Tests
Create `tests/test_nl_classifier.py` with parameterized cases:
- Typical phrasing variants
- Typos
- Ambiguous phrases
- Unsupported phrases -> unknown

## Metrics
- Precision / recall per intent
- Unknown rate trend over time
- Average disambiguation prompts per session

---
This module is a foundation; actual implementation to follow in subsequent commits.
