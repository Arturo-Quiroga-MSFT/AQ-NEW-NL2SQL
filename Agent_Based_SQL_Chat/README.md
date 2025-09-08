# DB Assistant – Natural Language Driven Schema & Data Orchestration

_Date: 2025-09-08_ Arturo Quiroga

## 1. Objectives
Provide a reusable, demo‑friendly system to go from natural language ("create a star schema for loan risk analysis") to:
- Validated schema specification (YAML DSL)
- Deterministic migration SQL (idempotent, ordered)
- Synthetic data generation (configurable distributions, volume control)
- Optional multi-agent orchestration (design, review, migration, seeding, query suggestion)
- Interfaces: CLI, Streamlit UI, REST API
- Governance: safety, auditability, rollback & drift detection

## 2. Mechanism Options (Adopt Incrementally)
| Track | Name | Description | When to Use |
|-------|------|-------------|-------------|
| 1 | CLI (Typer) | NL → YAML → Plan → Apply → Seed | Fastest initial scaffold & scripting |
| 2 | Streamlit DB Builder | Browser UI replicating in-editor Copilot flow | Live demos & non-technical users |
| 3 | Multi-Agent Service | LangGraph or tool-based agent endpoints | Extensibility & experimentation |
| 4 | GitOps Schema-as-Code | PR-based review, auto-plan, manual apply | Team collaboration & audit |
| 5 | Full Platform | Ephemeral DB sandboxes, metrics, rollback | Advanced staging / productization |

Recommendation: Implement Track 1 now, design for pluggability so 2 & 3 reuse core modules.

## 3. High-Level Architecture
```
DB_Assistant/
  cli/                # Typer command entrypoints (design, plan, apply, seed, inspect, suggest-queries)
  core/               # Pure logic, no I/O side-effects beyond DB execution where needed
    schema_models.py  # Pydantic models (Dimension, Fact, Column, Index, ForeignKey, SchemaSpec)
    schema_parser.py  # YAML <-> model conversion
    validators.py     # Naming/style/type checks
    migration_planner.py  # Diff engine: current → target → ordered operations
    ddl_renderer.py   # Turns operations into executable SQL (with dependency order)
    data_generator.py # Deterministic + stochastic synthetic data batches
    distributions.py  # Utility distributions (normal, lognormal, weighted categorical, etc.)
  agents/             # (Later) LLM-driven components
    design_agent.py
    review_agent.py
    data_agent.py
  templates/          # Reusable schema starter templates (star schema baselines)
  schema_specs/       # Canonical & proposal YAML specs
    current.yml
    proposals/
  migrations/         # Generated SQL migration artifacts
  seeding_profiles/   # Configs describing volumes & distributions
  api/                # (Later) FastAPI or Streamlit wrapper for service mode
  tests/              # Unit + property tests (models, diff, SQL ordering, generators)
  README.md
```

## 4. YAML Schema DSL (Example)
```yaml
version: 1
warehouse: contoso_finance
entities:
  dimensions:
    - name: dim_company
      surrogate_key: company_key
      natural_key: company_id
      columns:
        - name: company_id
          type: VARCHAR(50)
          nullable: false
        - name: region
          type: VARCHAR(40)
          nullable: false
        - name: industry
          type: VARCHAR(60)
      indexes:
        - name: ix_dim_company_region
          columns: [region]
    - name: dim_date
      surrogate_key: date_key
      columns:
        - name: date_key
          type: INT
          nullable: false
        - name: calendar_date
          type: DATE
          nullable: false
  facts:
    - name: fact_loan_payments
      grain: "loan_id, payment_date"
      foreign_keys:
        - column: company_key
          references: dim_company(company_key)
        - column: date_key
          references: dim_date(date_key)
      measures:
        - name: principal_paid
          type: DECIMAL(18,2)
        - name: interest_paid
          type: DECIMAL(18,2)
      columns:
        - name: loan_id
          type: VARCHAR(50)
          nullable: false
        - name: payment_date
          type: DATE
          nullable: false
      partitioning:
        strategy: RANGE
        column: payment_date
```

## 5. NL → Schema Flow
1. Input prompt (user intent)
2. Design Agent (LLM) proposes draft YAML
3. Validator enforces conventions (snake_case, types, prefixing)
4. Diff planner compares with `current.yml`
5. Plan shown to user for approval
6. DDL ordered & applied (transaction group per logical unit, where safe)
7. Seed phase populates dimension → fact tables
8. Query suggestions / test harness optional

## 6. Migration Planning Principles
- No implicit destructive changes (drops require `--allow-breaking`)
- Order: dimensions (no FK dependencies) → facts → indexes → FKs → views
- Hash/Checksum each migration file for drift detection
- Idempotence: Skip create if table exists with identical signature
- Version lineage: store applied migration IDs in `db_assistant_migrations` table

## 7. CLI Command Surface (Proposed)
| Command | Purpose | Key Flags |
|---------|---------|-----------|
| `dbx design "<prompt>"` | Generate YAML proposal | `--out` `--model gpt-4o` |
| `dbx plan --target proposal.yml` | Diff & produce migration SQL | `--current current.yml` `--out` |
| `dbx apply migration.sql` | Execute ordered operations | `--create-backup` `--require-approval` |
| `dbx seed --profile default.yml` | Synthetic data load | `--batch-size` `--dry-run` |
| `dbx inspect` | Reverse-engineer live schema to YAML | `--out` |
| `dbx suggest-queries --topic "covenant breaches"` | NL query ideas | `--limit` |
| `dbx validate schema.yml` | Lint schema spec | `--strict` |
| `dbx orchestrate "<question>"` | Multi-agent NL→SQL pipeline (LangGraph) | `--no-exec` `--explain-only` `--no-reasoning` `--refresh-schema` `--json` |

## 8. Synthetic Data Generation Strategy
Layers:
1. Referential skeleton (keys, surrogate IDs)
2. Distribution assignment (categorical weighting, numeric models)
3. Correlated attribute synthesis (region ↔ industry ↔ risk tiers)
4. Temporal spread (date dimension & fact temporal logic)
5. Optional LLM augmentation for text columns only

Performance Approach:
- Vectorized batch generation with numpy/pandas
- Bulk insert patterns (parameter batching / BCP / staging table) for large volumes
- Deterministic seed for reproducibility (seed stored in run log)

## 9. Streamlit DB Builder (Track 2)
Pages:
1. Prompt & Draft (editable YAML)
2. Plan (diff visualization + DDL preview)
3. Apply (logging console + rollback note)
4. Seed (profile selection + progress bar)
5. Explore (sample queries + result grid)
6. Metrics (token usage & timings)
7. Export (download YAML & SQL)

## 10. Multi-Agent Service (Track 3)
Agents:
- DesignAgent: NL → YAML
- ReviewAgent: Constraint enforcement & risk flagging
- MigrationAgent: Diff → operations → SQL
- DataAgent: Seeding batches & distribution simulation
- QueryAgent: Analytical query suggestions

REST Endpoints:
- POST `/design`, `/plan`, `/apply`, `/seed`, `/suggest-queries`

## 11. GitOps Flow (Track 4)
1. Proposal YAML committed under `schema_specs/proposals/`
2. CI: Validate + plan → artifact (migration.sql)
3. PR review of diff & plan
4. Merge triggers staging apply
5. Promotion to prod with manual approval gate

## 12. Security & Governance
| Area | Control |
|------|---------|
| Credentials | Use Azure AD / Managed Identity where possible; fallback limited SQL user |
| Destructive Ops | Explicit flag & backup snapshot required |
| Validation | Reject unknown data types & ambiguous grains |
| Audit | Log each run: phase, time, token cost, row counts |
| Least Privilege | Separate reader vs migrator identities |

## 13. Observability
- `db_assistant_runs` table (run_id, phase, status, timings, seed, token_usage)
- Migration checksum ledger
- Drift detection job (reverse‑engineer vs current.yml)
- Optional export to Log Analytics for central monitoring

## 14. Demo Script (Narrative)
1. Enter NL prompt for loan risk star schema
2. Show generated YAML + diagram (future enhancement)
3. Display migration plan, highlight new tables & indexes
4. Apply with progress messages
5. Seed using default profile (show row counts)
6. Run suggested analytical query (e.g., top exposure by region)
7. Show metrics panel (execution times + token summary)

## 15. Technology Choices
| Component | Choice | Rationale |
|----------|--------|-----------|
| CLI | Typer | Concise, composable commands |
| Models | Pydantic | Validation + serialization |
| DB Exec | pyodbc / SQLAlchemy Core | Azure SQL flexibility |
| Diff | Structural model comparison | Resilient to ordering |
| LLM | Azure OpenAI (GPT-4o) | Structured extraction, reasoning |
| Orchestration (later) | LangGraph | Deterministic multi-step flows |
| Data Gen | numpy + Faker | Speed + variability |

## 16. Implementation Phases
### Phase 0 (Scaffold)
- Create directory structure & placeholder modules
- Pydantic models (Dimension, Fact, Column, ForeignKey, SchemaSpec)
- Basic YAML parser & validator (naming + type whitelist)
- Minimal DDL generator (CREATE TABLE only)
- `dbx` Typer skeleton (design stub, plan stub, apply executing simple DDL)

### Phase 1 (Core Functionality)
- Diff engine & ordered operation graph
- Index & FK generation
- Seeding engine (dimensions then facts)
- Validation enhancements (grain, surrogate keys)
- Reverse inspection (live DB → YAML)

### Phase 2 (LLM & UX)
- DesignAgent integration (prompt templates)
- ReviewAgent style enforcement
- Query suggestion command
- Streamlit UI prototype

### Phase 3 (Resilience & Governance)
- Migration ledger table & checksum
- Backups (export schema & optional BACPAC / table copy)
- Drift detection command
- Failure & rollback strategy

### Phase 4 (Service Layer & GitOps)
- REST API (FastAPI) endpoints
- GitHub Actions: schema lint + plan artifact
- PR gating & staging deployment

### Phase 5 (Enhancements)
- Ephemeral sandbox DB creation
- Data volume stress modes
- Diagram generation (Mermaid / Graphviz)
- Metrics export to Log Analytics / Application Insights

## 17. Immediate Next Steps (Actionable)
Already Implemented (baseline scaffold complete):
- Core CLI (`design`, `plan`, `apply`, `inspect`, `seed`, `report`, `impact`)
- Migration ledger & idempotent DDL
- Column evolution (ADD/ALTER/DROP) with impact risk analyzer
- Deterministic seeding & extended stats reporting

Next Enhancements To Implement:
1. Automated test suite (planner diffs, impact risk classification, report stats) under `tests/`.
2. Dry‑run guard for high‑risk operations requiring `--allow-breaking` on apply.
3. Expanded distribution library (correlated distributions, temporal drift patterns).
4. GitHub Action workflow: validate + plan + impact JSON artifact on PR (ADDED: `.github/workflows/db_assistant_ci.yml`).
5. Diagram generation (Mermaid) auto-updated in `docs/` from schema spec.

Environment Activation:
Always activate the project virtual environment before running commands:
```bash
source .venv/bin/activate
```
Then run CLI commands, e.g.:
```bash
python -m DB_Assistant.cli.main plan --target DB_Assistant/schema_specs/live_after_alter_drop.yml --current DB_Assistant/schema_specs/live_post_enhancements.yml
python -m DB_Assistant.cli.main impact DB_Assistant/schema_specs/live_after_alter_drop.yml --current DB_Assistant/schema_specs/live_post_enhancements.yml --summary-only
python -m DB_Assistant.cli.main report fact_loan_payments --percentiles 90,95,99

# Orchestrate an NL question to SQL (rich panels):
python -m DB_Assistant.cli.main orchestrate "For each region list top 5 companies by total principal" --no-exec

# Machine-readable JSON output:
python -m DB_Assistant.cli.main orchestrate "For each region list top 5 companies by total principal" --no-exec --json | jq .

## CI Trigger Note
This line added on 2025-09-05 to intentionally trigger the GitHub Actions workflow (no [skip ci] token present).
```

## 18. Future Enhancements (Backlog Ideas)
- Materialized view creation suggestions
- Automatic indexing heuristics (selectivity estimation)
- Data quality test harness (row count, null ratio checks)
- Semantic layer export (dbt, metrics layer YAML)
- Cost simulation (storage + row estimate)

## 19. Contribution Guidelines (Draft)
- All schema changes must have: YAML spec + migration SQL + test (reverse inspection round-trip)
- Run `dbx validate` before committing new specs
- Avoid mixing application code changes with migration artifacts
- Document synthetic data profile rationales

## 20. Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Hallucinated datatypes | Strict whitelist & normalization pass |
| Ordering issues (FK before table) | Topological sort in planner |
| Large seed slowness | Batch inserts + configurable batch size |
| Accidentally destructive change | Explicit flag + backup + plan review |
| Schema drift | Scheduled reverse inspection + diff report |

## 21. License & Attribution
Internal architectural scaffold. No external proprietary content embedded. Azure-specific usage (pyodbc + TDS) assumed.

---
**Status:** Planning complete. Awaiting instruction to scaffold Phase 0. 
 
## 22. CI & Safety Additions
- CI pipeline (`db_assistant_ci.yml`) runs tests, generates a sample migration + impact JSON as artifacts on PRs and main pushes.
- `apply` command now refuses to run high-risk operations unless `--allow-breaking` is specified (and an impact sidecar file marks them as high).
- `plan --impact-meta` creates `yourplan.sql.impact.json` enabling automated gating.

### Example Gated Apply Flow
```bash
python -m DB_Assistant.cli.main plan --target target.yml --current current.yml --out migrations/20250905_add_changes.sql --impact-meta
python -m DB_Assistant.cli.main apply migrations/20250905_add_changes.sql   # may block
python -m DB_Assistant.cli.main apply migrations/20250905_add_changes.sql --allow-breaking  # override
```

> Provide "Proceed Phase 0" (or adjustments) to continue.
