# NL2SQL Teams Integration - Visual Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Microsoft Teams                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  👤 User Types: "How many loans in default status?"         │   │
│  └──────────────────────────────────────────────────────────────┘   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ HTTPS POST
                             │ (Encrypted)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Azure Bot Service                                │
│  • Validates message sender (Teams)                                 │
│  • Authenticates bot identity                                       │
│  • Routes to messaging endpoint                                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ POST /api/messages
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Azure App Service (Your NL2SQL App)                    │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  aiohttp Web Server (Port 3978)                               │ │
│  │  • Endpoint: /api/messages                                    │ │
│  │  • Handler: aiohttp_handler()                                 │ │
│  └───────────────────────┬───────────────────────────────────────┘ │
│                          │                                          │
│  ┌───────────────────────▼───────────────────────────────────────┐ │
│  │  M365 Agents SDK Components                                   │ │
│  │  ┌─────────────────────────────────────────────────────────┐  │ │
│  │  │ CloudAdapter                                            │  │ │
│  │  │  • Converts HTTP → Bot Protocol                         │  │ │
│  │  │  • Handles authentication                               │  │ │
│  │  └─────────────────────┬───────────────────────────────────┘  │ │
│  │  ┌─────────────────────▼───────────────────────────────────┐  │ │
│  │  │ AgentApplication                                        │  │ │
│  │  │  • Activity routing                                     │  │ │
│  │  │  • Turn management                                      │  │ │
│  │  │  • Event handlers                                       │  │ │
│  │  └─────────────────────┬───────────────────────────────────┘  │ │
│  │  ┌─────────────────────▼───────────────────────────────────┐  │ │
│  │  │ TurnContext & TurnState                                 │  │ │
│  │  │  • Current message                                      │  │ │
│  │  │  • User information                                     │  │ │
│  │  │  • Conversation state                                   │  │ │
│  │  └─────────────────────┬───────────────────────────────────┘  │ │
│  └────────────────────────┼─────────────────────────────────────┘ │
│                           │                                        │
│  ┌────────────────────────▼──────────────────────────────────────┐ │
│  │  teams_nl2sql_agent.py (YOUR NEW WRAPPER CODE)              │ │
│  │  ┌──────────────────────────────────────────────────────┐   │ │
│  │  │ @AGENT_APP.activity("message")                       │   │ │
│  │  │ async def on_message(context, state):                │   │ │
│  │  │     user_query = context.activity.text               │   │ │
│  │  │     await context.send_activity({"type": "typing"})  │   │ │
│  │  │                                                       │   │ │
│  │  │     # Call your existing NL2SQL pipeline             │   │ │
│  │  │     intent = extract_intent(user_query)              │   │ │
│  │  │     sql = generate_sql(intent)                       │   │ │
│  │  │     results = execute_sql_query(sql)                 │   │ │
│  │  │                                                       │   │ │
│  │  │     # Format and send response                       │   │ │
│  │  │     card = build_adaptive_card(results)              │   │ │
│  │  │     await context.send_activity(card)                │   │ │
│  │  └──────────────────────┬───────────────────────────────┘   │ │
│  └─────────────────────────┼─────────────────────────────────────┘ │
│                            │                                       │
│  ┌─────────────────────────▼─────────────────────────────────────┐ │
│  │  YOUR EXISTING NL2SQL PIPELINE (95% UNCHANGED)               │ │
│  │  ┌──────────────────────────────────────────────────────┐   │ │
│  │  │ nl2sql_main.py (Refactored to export functions)     │   │ │
│  │  │  • extract_intent(query) → intent JSON              │   │ │
│  │  │  • generate_sql(intent) → SQL string                │   │ │
│  │  │  • format_results(rows) → formatted output          │   │ │
│  │  └──────────────────────┬───────────────────────────────┘   │ │
│  └─────────────────────────┼─────────────────────────────────────┘ │
│                            │                                       │
│  ┌─────────────────────────▼─────────────────────────────────────┐ │
│  │  Azure AI Foundry Agents (UNCHANGED)                         │ │
│  │  ┌──────────────────────────────────────────────────────┐   │ │
│  │  │ Intent Extraction Agent                              │   │ │
│  │  │  • Analyzes natural language                         │   │ │
│  │  │  • Extracts entities, filters, metrics               │   │ │
│  │  └──────────────────────────────────────────────────────┘   │ │
│  │  ┌──────────────────────────────────────────────────────┐   │ │
│  │  │ SQL Generation Agent                                 │   │ │
│  │  │  • Receives: intent + schema context                 │   │ │
│  │  │  • Generates: T-SQL query                            │   │ │
│  │  └──────────────────────┬───────────────────────────────┘   │ │
│  └─────────────────────────┼─────────────────────────────────────┘ │
│                            │                                       │
│  ┌─────────────────────────▼─────────────────────────────────────┐ │
│  │  schema_reader.py (UNCHANGED)                                │ │
│  │  • get_sql_database_schema_context()                         │ │
│  │  • Returns: tables, columns, relationships                   │ │
│  │  • Cached for 24 hours                                       │ │
│  └─────────────────────────┬─────────────────────────────────────┘ │
│                            │                                       │
│  ┌─────────────────────────▼─────────────────────────────────────┐ │
│  │  sql_executor.py (UNCHANGED)                                 │ │
│  │  • execute_sql_query(sql)                                    │ │
│  │  • Returns: List[Dict] of results                            │ │
│  └─────────────────────────┬─────────────────────────────────────┘ │
└────────────────────────────┼───────────────────────────────────────┘
                             │
                             │ SQL Query
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Azure SQL Database                                │
│                     (TERADATA-FI)                                   │
│  • dim.Customers, dim.Dates, dim.Products, etc.                    │
│  • fact.LoanApplications, fact.Loans, fact.Payments, etc.          │
│  • Returns query results                                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             │ Results (List[Dict])
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                Response Formatting (NEW)                            │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  adaptive_card_builder.py                                     │ │
│  │  • build_results_card(results, sql, count)                    │ │
│  │  • Creates Adaptive Card JSON                                 │ │
│  │  • Adds action buttons (Export, View SQL, Refine)             │ │
│  └───────────────────────┬───────────────────────────────────────┘ │
└─────────────────────────┬───────────────────────────────────────────┘
                          │
                          │ Adaptive Card JSON
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Response sent back through SDK                         │
│  context.send_activity({                                            │
│    "type": "message",                                               │
│    "attachments": [{                                                │
│      "contentType": "application/vnd.microsoft.card.adaptive",      │
│      "content": { /* Adaptive Card */ }                             │
│    }]                                                               │
│  })                                                                 │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Azure Bot Service                                │
│  • Receives response from bot                                       │
│  • Routes back to Teams                                             │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Microsoft Teams                                 │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  📊 Query Results (12 rows)                                  │   │
│  │  ┌────────────────────────────────────────────────────────┐  │   │
│  │  │ Status  │ Count │ Total Balance                        │  │   │
│  │  ├─────────┼───────┼──────────────────────────────────────┤  │   │
│  │  │ Default │ 12    │ $847,500                             │  │   │
│  │  └────────────────────────────────────────────────────────┘  │   │
│  │  [📥 Export CSV] [🔍 View SQL] [✏️ Refine Query]           │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

```
User Query Flow:
─────────────────

1. User types in Teams
   ↓
2. Teams → Azure Bot Service (authentication)
   ↓
3. Azure Bot → Your App (/api/messages)
   ↓
4. CloudAdapter converts HTTP to Bot Protocol
   ↓
5. AgentApplication routes to message handler
   ↓
6. teams_nl2sql_agent.on_message() receives query
   ↓
7. Calls extract_intent(query) → Azure AI Agent
   ↓
8. Calls generate_sql(intent) → Azure AI Agent
   ↓
9. Calls execute_sql_query(sql) → Azure SQL
   ↓
10. Formats results as Adaptive Card
   ↓
11. Sends back through context.send_activity()
   ↓
12. AgentApplication → CloudAdapter → aiohttp
   ↓
13. HTTP Response → Azure Bot Service
   ↓
14. Azure Bot → Teams
   ↓
15. User sees beautiful card with results
```

## Component Responsibility Matrix

```
┌─────────────────────────┬──────────────┬────────────────────────┐
│ Component               │ Ownership    │ Responsibility         │
├─────────────────────────┼──────────────┼────────────────────────┤
│ Microsoft Teams         │ Microsoft    │ UI, user interaction   │
│ Azure Bot Service       │ Microsoft    │ Auth, routing          │
│ M365 Agents SDK         │ Microsoft    │ Bot protocol, adapters │
│ teams_nl2sql_agent.py   │ YOU (NEW)    │ Message handling       │
│ nl2sql_main.py          │ YOU (MODIFY) │ NL2SQL pipeline        │
│ schema_reader.py        │ YOU (KEEP)   │ Schema discovery       │
│ sql_executor.py         │ YOU (KEEP)   │ SQL execution          │
│ adaptive_card_builder.py│ YOU (NEW)    │ Response formatting    │
│ Azure AI Agents         │ YOU (KEEP)   │ Intent, SQL generation │
│ Azure SQL Database      │ YOU (KEEP)   │ Data storage           │
└─────────────────────────┴──────────────┴────────────────────────┘
```

## Code Reuse Visualization

```
YOUR EXISTING CODE (Keep & Reuse: ~950 lines)
┌────────────────────────────────────────────────┐
│ schema_reader.py          354 lines  ✅ KEEP  │
│ sql_executor.py            30 lines  ✅ KEEP  │
│ nl2sql_main.py (core)     500 lines  ✅ KEEP  │
│ Azure AI Agent setup       66 lines  ✅ KEEP  │
└────────────────────────────────────────────────┘

MINOR MODIFICATIONS (Refactor: ~67 lines)
┌────────────────────────────────────────────────┐
│ nl2sql_main.py            ~67 lines  🔧 MODIFY│
│ • Wrap logic in functions                     │
│ • Export: extract_intent()                    │
│ • Export: generate_sql()                      │
│ • Export: format_results()                    │
└────────────────────────────────────────────────┘

NEW CODE (Add: ~450 lines)
┌────────────────────────────────────────────────┐
│ teams_nl2sql_agent.py    ~200 lines  🆕 NEW   │
│ start_server.py           ~50 lines  🆕 NEW   │
│ adaptive_card_builder.py ~150 lines  🆕 NEW   │
│ manifest.json             ~50 lines  🆕 NEW   │
└────────────────────────────────────────────────┘

EFFORT BREAKDOWN
┌────────────────────────────────────────────────┐
│ Keep as-is:        950 lines (68%)            │
│ Minor changes:      67 lines (5%)             │
│ New code:          450 lines (32%)            │
├────────────────────────────────────────────────┤
│ TOTAL:           1,467 lines (100%)           │
└────────────────────────────────────────────────┘
```

## Deployment Architecture

```
Development Environment:
┌──────────────────────────────────────────────────────────┐
│ Your Laptop                                              │
│  ┌────────────────────────────────────────────────────┐  │
│  │ python start_server.py                             │  │
│  │ → http://localhost:3978                            │  │
│  └─────────────────┬──────────────────────────────────┘  │
└────────────────────┼─────────────────────────────────────┘
                     │
                     │ devtunnel (for local testing)
                     │ https://abc123.devtunnels.ms
                     ▼
           ┌─────────────────────┐
           │ Azure Bot Service   │
           │ Messaging Endpoint  │
           └─────────────────────┘
                     │
                     ▼
           ┌─────────────────────┐
           │ Teams Web Chat      │
           │ (Test in Portal)    │
           └─────────────────────┘

Production Environment:
┌──────────────────────────────────────────────────────────┐
│ Azure App Service                                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │ nl2sql-teams-bot.azurewebsites.net                 │  │
│  │ • Auto-scaling: 1-10 instances                     │  │
│  │ • Always On: Enabled                               │  │
│  │ • HTTPS Only: Enforced                             │  │
│  └─────────────────┬──────────────────────────────────┘  │
└────────────────────┼─────────────────────────────────────┘
                     │
                     │ HTTPS
                     ▼
           ┌─────────────────────┐
           │ Azure Bot Service   │
           │ Production Channel  │
           └─────────────────────┘
                     │
                     ├─── Microsoft Teams
                     ├─── M365 Copilot
                     └─── Web Chat
```

## State Management Flow

```
Conversation State (Optional but Recommended):
┌─────────────────────────────────────────────────────────┐
│ User sends first query: "How many loans?"               │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ TurnState saved to Storage:                             │
│ {                                                       │
│   "user_id": "user@company.com",                        │
│   "conversation_id": "19:abc123...",                    │
│   "last_query": "How many loans?",                      │
│   "last_sql": "SELECT COUNT(*) FROM fact.Loans",        │
│   "last_intent": {...},                                 │
│   "database": "TERADATA-FI",                            │
│   "timestamp": "2025-01-06T15:30:00Z"                   │
│ }                                                       │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ User sends follow-up: "Show me the details"            │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Agent retrieves TurnState from Storage                 │
│ • Knows context: previous query was about loans        │
│ • Can reference: last_sql to enhance query             │
│ • Maintains continuity across conversation             │
└─────────────────────────────────────────────────────────┘
```

## Error Handling Flow

```
Error Scenarios & Handling:
┌─────────────────────────────────────────────────────────┐
│ 1. User sends invalid query                             │
│    → Intent extraction fails gracefully                 │
│    → Send helpful error message with examples           │
│    → Log error for analysis                             │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 2. SQL generation produces invalid SQL                  │
│    → Catch SQL syntax error                             │
│    → Retry with clarified intent                        │
│    → If retry fails, ask user to rephrase               │
│    → Log for training data                              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 3. Database connection fails                            │
│    → Retry with exponential backoff                     │
│    → If persistent, send friendly error message         │
│    → Alert operations team                              │
│    → Log for monitoring                                 │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 4. Query timeout (large result set)                     │
│    → Suggest adding filters to narrow results           │
│    → Offer to add LIMIT clause                          │
│    → Save partial results if available                  │
│    → Log slow queries for optimization                  │
└─────────────────────────────────────────────────────────┘
```

## Security Layers

```
Security in Depth:
┌─────────────────────────────────────────────────────────┐
│ Layer 1: Teams Identity                                │
│ • User authenticated by Microsoft                       │
│ • Only corporate users can access bot                   │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Bot Service Authentication                     │
│ • Validates sender is actually Teams                    │
│ • Prevents spoofing attacks                             │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 3: App Service Authentication                     │
│ • Managed Identity for Azure resources                  │
│ • No hardcoded credentials                              │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 4: SQL Security                                   │
│ • Parameterized queries prevent SQL injection           │
│ • Database user has read-only access                    │
│ • Row-level security (optional)                         │
└───────────────────────┬─────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 5: Audit Logging                                  │
│ • All queries logged with user identity                 │
│ • Anomaly detection for unusual patterns                │
│ • Compliance reporting available                        │
└─────────────────────────────────────────────────────────┘
```

## Performance Optimization

```
Caching Strategy:
┌──────────────────────────────────────────────────────┐
│ Schema Cache (24h TTL)                               │
│ • Cached by schema_reader.py                         │
│ • Refreshed on deployment or manual trigger          │
│ • Reduces DB roundtrips for metadata                 │
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────┐
│ Query Results Cache (5min TTL) - Optional            │
│ • Cache identical queries                            │
│ • Key: hash(sql_query)                               │
│ • Reduces DB load for repeated queries               │
└────────────────┬─────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────┐
│ Agent Session Cache (conversation duration)          │
│ • Reuse Azure AI agents across turns                 │
│ • Avoid recreating agents for each message           │
│ • Maintains context efficiently                      │
└──────────────────────────────────────────────────────┘

Response Time Optimization:
┌──────────────────────────────────────────────────────┐
│ Target: <5 seconds end-to-end                        │
│ ├─ Intent Extraction: 1-2 sec                        │
│ ├─ SQL Generation: 2-3 sec                           │
│ ├─ SQL Execution: 0.5-2 sec                          │
│ └─ Response Formatting: <0.5 sec                     │
└──────────────────────────────────────────────────────┘
```

---

## Summary

This visual guide shows:
1. ✅ **Architecture**: How all components fit together
2. ✅ **Data Flow**: Request/response journey
3. ✅ **Code Reuse**: What you keep vs what's new
4. ✅ **Deployment**: Dev and prod environments
5. ✅ **State Management**: Conversation continuity
6. ✅ **Error Handling**: Graceful failure modes
7. ✅ **Security**: Multi-layer protection
8. ✅ **Performance**: Caching and optimization

**Bottom Line:** Your existing NL2SQL pipeline fits perfectly into the M365 Agents SDK architecture with minimal changes and maximum benefit.
