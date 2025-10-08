# Multi-Model NL2SQL Architecture

## 🏗️ System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                              │
│                      (Streamlit Web App)                            │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  • Example Questions (12 quick-start buttons)                │  │
│  │  • Text Input Area                                           │  │
│  │  • Model Selection (gpt-4.1 vs gpt-5-mini)                  │  │
│  │  • Control Toggles (Skip exec, Explain-only, No reasoning)  │  │
│  │  • Run Button                                                │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    MULTI-MODEL PIPELINE                             │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  STAGE 1: INTENT EXTRACTION                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Model: gpt-4o-mini                                        │  │
│  │  Cost: $0.00015 per 1K input tokens                       │  │
│  │  Purpose: Parse natural language → structured intent       │  │
│  │  Input: User question + schema context                     │  │
│  │  Output: JSON with intent, entities, filters, etc.         │  │
│  │  Typical Tokens: ~1,500 (mostly input)                     │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 2 (Optional): REASONING                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Model: Selected model (gpt-4.1 or gpt-5-mini)           │  │
│  │  Purpose: Explain high-level query plan                   │  │
│  │  Input: Intent + schema                                    │  │
│  │  Output: Natural language explanation                      │  │
│  │  Typical Tokens: ~2,000                                    │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 3: SQL GENERATION                                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Model: USER SELECTED                                      │  │
│  │  ┌──────────────────────────┬──────────────────────────┐  │  │
│  │  │  Option A: gpt-4.1       │  Option B: gpt-5-mini    │  │  │
│  │  │  Cost: $0.00277/1K in    │  Cost: $0.0003/1K in     │  │  │
│  │  │  Best: Complex queries    │  Best: Simple queries    │  │  │
│  │  │  Accuracy: Highest        │  Speed: Faster           │  │  │
│  │  └──────────────────────────┴──────────────────────────┘  │  │
│  │  Purpose: Generate accurate T-SQL query                   │  │
│  │  Input: Intent + full schema context                      │  │
│  │  Output: T-SQL with proper syntax, JOINs, etc.           │  │
│  │  Typical Tokens: ~4,000 (large schema context)           │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  SQL SANITIZATION & EXTRACTION                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  • Extract SQL from markdown code blocks                  │  │
│  │  • Remove comments and explanation text                   │  │
│  │  • Validate basic syntax                                   │  │
│  │  • Add safety warnings if needed                          │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  SQL EXECUTION                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Database: Azure SQL Database (CONTOSO-FI)                │  │
│  │  Driver: pyodbc with ODBC Driver 18                        │  │
│  │  Security: Encrypted connection, SQL auth                  │  │
│  │  Output: List of dictionaries (rows)                      │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│  STAGE 4: RESULT FORMATTING                                      │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Model: gpt-4.1-mini                                       │  │
│  │  Cost: $0.00055 per 1K input tokens                       │  │
│  │  Purpose: Create natural language summary                  │  │
│  │  Input: Question + SQL + results (first 20 rows)          │  │
│  │  Output: Professional summary with insights                │  │
│  │  Typical Tokens: ~2,500                                    │  │
│  │  Features:                                                  │  │
│  │    • Key findings highlighted                              │  │
│  │    • Statistics and patterns identified                    │  │
│  │    • Natural language answer to original question          │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    RESULTS PRESENTATION                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  1. Intent & Entities (from Stage 1)                        │  │
│  │  2. Reasoning (optional, from Stage 2)                      │  │
│  │  3. Generated SQL (from Stage 3)                            │  │
│  │  4. Data Table (interactive, sortable)                      │  │
│  │  5. AI Summary (from Stage 4) ⭐ NEW!                       │  │
│  │  6. Export Options (CSV, Excel, Copy SQL)                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│              TOKEN USAGE & COST BREAKDOWN                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  PER-STAGE METRICS:                                          │  │
│  │                                                               │  │
│  │  🎯 Intent (gpt-4o-mini)                                     │  │
│  │     Input: 256 tokens    Output: 128 tokens                 │  │
│  │     Cost: $0.000384                                          │  │
│  │                                                               │  │
│  │  🧠 SQL (gpt-4.1)                                            │  │
│  │     Input: 2,048 tokens  Output: 512 tokens                 │  │
│  │     Cost: $0.011344                                          │  │
│  │                                                               │  │
│  │  📝 Formatting (gpt-4.1-mini)                                │  │
│  │     Input: 1,024 tokens  Output: 256 tokens                 │  │
│  │     Cost: $0.001126                                          │  │
│  │                                                               │  │
│  │  TOTAL: 4,224 tokens, $0.012854 USD                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       LOGGING & PERSISTENCE                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  File: RESULTS/nl2sql_multimodel_run_YYYYMMDD_HHMMSS.txt    │  │
│  │  Contains:                                                    │  │
│  │    • User question                                           │  │
│  │    • Intent & entities                                       │  │
│  │    • Reasoning (if enabled)                                  │  │
│  │    • Generated SQL                                           │  │
│  │    • Query results (JSON)                                    │  │
│  │    • AI summary                                              │  │
│  │    • Per-model token usage and costs                        │  │
│  │    • Elapsed time                                            │  │
│  │    • Model configuration used                                │  │
│  │                                                               │  │
│  │  Optional: Upload to Azure Blob Storage                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow

```
User Question
    │
    ├─→ + Schema Context ─→ gpt-4o-mini ─→ Intent/Entities
    │                                          │
    │                                          ▼
    └─→ + Schema Context + Intent ─→ gpt-4.1/gpt-5-mini ─→ SQL Query
                                              │
                                              ▼
                                     Azure SQL Database
                                              │
                                              ▼
                                        Result Rows
                                              │
                                              ▼
    Question + SQL + Results ─→ gpt-4.1-mini ─→ AI Summary
                                              │
                                              ▼
                                    Complete Response
```

## 💰 Token Flow & Cost Distribution

```
Typical Query Breakdown (6,000 total tokens):

Intent Extraction (gpt-4o-mini)
▓▓░░░░░░░░░░░░░░░░░░  10% (600 tokens)
Cost: $0.0006

SQL Generation (gpt-4.1)
▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░  60% (3,600 tokens)
Cost: $0.0154

Result Formatting (gpt-4.1-mini)
▓▓▓▓▓▓░░░░░░░░░░░░░░  30% (1,800 tokens)
Cost: $0.0030

Total: $0.0190 per query
(vs $0.042 for gpt-4.1 only = 55% savings!)
```

## 🎯 Model Selection Decision Tree

```
User Question Received
        │
        ▼
   [Simple query?] ───Yes──→ Use gpt-5-mini for SQL
        │                    (1-2 tables, basic filters)
        No                   Cost: ~$0.007 per query
        │
        ▼
   [Complex query?] ──Yes──→ Use gpt-4.1 for SQL
        │                    (Multi-table joins, CTEs)
        No                   Cost: ~$0.024 per query
        │
        ▼
   [User preference]
        │
        └──→ Let user choose in UI
             (Default: gpt-4.1)
```

## 🏗️ Component Architecture

```
app_multimodel.py (Main Application)
│
├── UI Layer (Streamlit)
│   ├── Sidebar
│   │   ├── Model Selection Radio Buttons
│   │   ├── Environment Status
│   │   ├── Schema Refresh Button
│   │   └── Multi-Model Strategy Explanation
│   │
│   └── Main Content
│       ├── Example Questions Grid
│       ├── Query Input Area
│       ├── Control Toggles
│       ├── Run Configuration Display
│       ├── Results Display
│       └── Cost Breakdown Panel
│
├── Multi-Model Pipeline
│   ├── parse_nl_query_with_gpt4o_mini()
│   │   └── Returns: Structured intent JSON
│   │
│   ├── generate_reasoning_with_selected_model()
│   │   └── Returns: High-level plan text
│   │
│   ├── generate_sql_with_selected_model()
│   │   └── Returns: T-SQL query string
│   │
│   └── format_results_with_gpt41_mini()
│       └── Returns: Natural language summary
│
├── Support Functions
│   ├── _make_llm(deployment_name, max_tokens)
│   │   └── Factory for Azure OpenAI instances
│   │
│   ├── _accumulate_usage(stage, usage)
│   │   └── Track tokens per stage
│   │
│   ├── _get_pricing_for_deployment(deployment)
│   │   └── Fetch pricing from config
│   │
│   └── _extract_usage_from_message(msg)
│       └── Parse token usage from response
│
├── Shared Modules (from nl2sql_standalone_Langchain/)
│   ├── schema_reader.py
│   │   ├── get_sql_database_schema_context()
│   │   └── refresh_schema_cache()
│   │
│   ├── sql_executor.py
│   │   └── execute_sql_query()
│   │
│   └── 1_nl2sql_main.py
│       ├── extract_and_sanitize_sql()
│       ├── _format_table()
│       └── _load_pricing_config()
│
└── Configuration
    ├── Environment Variables (.env)
    ├── Pricing Config (azure_openai_pricing_updated_oct2025.json)
    └── Model Constants (INTENT_MODEL, SQL_MODEL_DEFAULT, etc.)
```

## 🔐 Security & Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Environment Variables (from .env)                          │
│  • AZURE_OPENAI_API_KEY (encrypted in transit)             │
│  • AZURE_OPENAI_ENDPOINT                                    │
│  • AZURE_SQL_PASSWORD (encrypted in transit)               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Streamlit App (runs locally or in secure environment)      │
│  • No credentials in code                                   │
│  • HTTPS for Azure OpenAI                                   │
│  • Encrypted SQL connection (TrustServerCertificate=yes)   │
└─────────────────────────────────────────────────────────────┘
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
    ┌──────────────────┐  ┌──────────────────┐
    │  Azure OpenAI     │  │  Azure SQL DB    │
    │  • API Key auth   │  │  • SQL auth      │
    │  • HTTPS only     │  │  • TLS 1.2+     │
    │  • Multi-region   │  │  • Firewall     │
    └──────────────────┘  └──────────────────┘
```

## 📊 Performance Characteristics

```
Stage                Model           Avg Latency    Avg Tokens    Avg Cost
─────────────────────────────────────────────────────────────────────────
Intent Extraction    gpt-4o-mini     0.5-1.5s      500-1,000     $0.0003
Reasoning (opt)      gpt-4.1         1.0-2.0s      1,000-2,000   $0.0040
SQL Generation       gpt-4.1         2.0-4.0s      2,000-4,000   $0.0150
SQL Generation       gpt-5-mini      1.0-2.0s      2,000-4,000   $0.0015
SQL Execution        Azure SQL       0.1-2.0s      N/A           N/A
Result Formatting    gpt-4.1-mini    1.0-2.0s      1,500-2,500   $0.0020
─────────────────────────────────────────────────────────────────────────
Total (gpt-4.1)                      5-10s         5,000-9,500   $0.0213
Total (gpt-5-mini)                   3-7s          5,000-9,500   $0.0078
```

## 🎨 UI/UX Flow

```
User Arrives
    │
    ▼
[Example Questions] ─── Click ───→ Auto-fill query
    │
    ▼
[Type Question]
    │
    ▼
[Select SQL Model] (Sidebar)
    │  ├─→ gpt-4.1 (accurate)
    │  └─→ gpt-5-mini (fast & cheap)
    │
    ▼
[Press Run]
    │
    ├─→ See "Run Configuration" (models used)
    │
    ├─→ See "Intent & Entities" (parsed by gpt-4o-mini)
    │
    ├─→ See "Reasoning" (optional)
    │
    ├─→ See "Generated SQL" (by selected model)
    │
    ├─→ See "Results Table" (from Azure SQL)
    │
    ├─→ See "AI Summary" (by gpt-4.1-mini) ⭐
    │
    └─→ See "Cost Breakdown" (per model)
        │
        ├─→ Intent: $X.XX
        ├─→ SQL: $X.XX
        ├─→ Formatting: $X.XX
        └─→ Total: $X.XX
```

## 🔌 Integration Points

```
app_multimodel.py
        │
        ├─── LangChain (Azure OpenAI integration)
        │    ├── AzureChatOpenAI class
        │    ├── ChatPromptTemplate
        │    └── Message chain invocation
        │
        ├─── Azure OpenAI API
        │    ├── Endpoint: AZURE_OPENAI_ENDPOINT
        │    ├── API Key: AZURE_OPENAI_API_KEY
        │    ├── API Version: 2025-04-01-preview
        │    └── Deployments: gpt-4o-mini, gpt-4.1, gpt-5-mini, gpt-4.1-mini
        │
        ├─── Azure SQL Database
        │    ├── Server: AZURE_SQL_SERVER
        │    ├── Database: CONTOSO-FI
        │    ├── Driver: ODBC Driver 18
        │    └── Protocol: TLS 1.2+
        │
        ├─── File System
        │    ├── Schema Cache: DATABASE_SETUP/schema_cache.json
        │    ├── Pricing Config: azure_openai_pricing_updated_oct2025.json
        │    └── Run Logs: RESULTS/nl2sql_multimodel_run_*.txt
        │
        └─── Azure Blob Storage (Optional)
             ├── Connection String: AZURE_STORAGE_CONNECTION_STRING
             ├── Container: nl2sql-logs
             └── Upload: Run logs for durable storage
```

---

## 📈 Scalability Considerations

### Horizontal Scaling
- ✅ Stateless app (no session affinity needed)
- ✅ Each instance independent
- ✅ Load balancer compatible

### Vertical Scaling
- ✅ Low memory footprint (~100MB per instance)
- ✅ CPU usage minimal (mostly I/O wait)
- ✅ Can run on small VMs

### Cost Scaling
- ✅ Linear with query volume
- ✅ Multi-model reduces cost growth
- ✅ Predictable pricing model

---

This architecture enables **cost-optimized, high-quality NL2SQL** by using the right model for each task!
