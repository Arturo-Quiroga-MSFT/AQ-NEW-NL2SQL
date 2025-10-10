# Integrating NL2SQL Pipeline into Microsoft Teams using M365 Agents SDK

## Executive Summary

Based on analysis of the Microsoft 365 Agents SDK documentation, we can successfully integrate your Azure AI-powered NL2SQL pipeline into Microsoft Teams. The SDK provides the perfect bridge between your existing Python NL2SQL application and Teams messaging.

**Key Finding:** Your current `nl2sql_azureai_universal` app can be wrapped in an M365 Agents SDK container with minimal changes, exposing it as a Teams bot that responds to natural language database queries.

---

## Architecture Overview

### Current State (Standalone NL2SQL)
```
User (CLI) → nl2sql_main.py → Azure AI Agents → SQL Generation → Azure SQL → Results
```

### Future State (Teams-Integrated NL2SQL)
```
Teams User → Teams Message → M365 Agent Container → nl2sql_main.py logic → 
Azure AI Agents → SQL Generation → Azure SQL → Results → Adaptive Card → Teams
```

---

## M365 Agents SDK - What We Can Leverage

### 1. **Agent Container (Core Foundation)**

The SDK provides `AgentApplication` which handles:
- ✅ **Activity Management**: Receives/sends messages to Teams
- ✅ **Turn-based Conversation**: Manages conversation state between queries
- ✅ **Authentication**: Built-in Azure Bot Service authentication
- ✅ **Multi-Channel**: Works with Teams, M365 Copilot, Web Chat
- ✅ **Storage**: MemoryStorage, BlobStorage, CosmosDB for conversation state

**Python Example from SDK:**
```python
from microsoft_agents.hosting.core import AgentApplication, TurnContext, TurnState
from microsoft_agents.hosting.aiohttp import CloudAdapter
from microsoft_agents.authentication.msal import MsalConnectionManager

# Create agent container
AGENT_APP = AgentApplication[TurnState](
    storage=STORAGE,
    adapter=ADAPTER,
    authorization=AUTHORIZATION,
)

# Handle incoming messages
@AGENT_APP.activity("message")
async def on_message(context: TurnContext, state: TurnState):
    user_query = context.activity.text
    
    # YOUR NL2SQL LOGIC GOES HERE
    # Call nl2sql_main.py functions
    
    await context.send_activity(f"Results: {results}")
```

### 2. **Teams Integration (Channel Support)**

The SDK includes `TeamsActivityHandler` for Teams-specific features:
- ✅ **Adaptive Cards**: Rich formatting for SQL results
- ✅ **File Uploads**: Export results as CSV/Excel
- ✅ **Message Extensions**: Query from compose box
- ✅ **Typing Indicators**: Show "bot is typing..." during SQL generation
- ✅ **@Mentions**: Respond when mentioned in channels

**Import:**
```python
from microsoft_agents.hosting.teams import TeamsActivityHandler
```

### 3. **Azure Bot Service Integration**

- ✅ **Endpoint**: `https://your-app.azurewebsites.net/api/messages`
- ✅ **Authentication**: Managed Identity or Client Secret
- ✅ **Channels**: Automatic Teams channel connection
- ✅ **Web Chat**: Test in Azure Portal before Teams deployment

### 4. **Deployment Options**

The SDK supports multiple deployment methods:
- ✅ **Azure App Service**: Deploy as webapp (same as current architecture)
- ✅ **Azure Container Apps**: Deploy as container
- ✅ **Local Development**: Dev tunnels for testing
- ✅ **CI/CD**: GitHub Actions, Azure DevOps pipelines

### 5. **State Management**

Built-in storage options for conversation context:
- ✅ **MemoryStorage**: In-memory (dev/testing)
- ✅ **BlobStorage**: Azure Blob Storage (production)
- ✅ **CosmosDB**: Cosmos DB (production, multi-region)

**Use Case:** Store user's previous queries, database context, preferences

```python
from microsoft_agents.storage.blob import BlobStorage
from microsoft_agents.storage.cosmos import CosmosDbStorage

# Production storage
STORAGE = BlobStorage(connection_string="...", container_name="nl2sql-state")
```

### 6. **Authentication Options**

Multiple auth patterns supported:
- ✅ **SSO**: Single Sign-On with Microsoft Entra ID
- ✅ **OAuth**: Access user's Graph API data
- ✅ **MSAL**: Microsoft Authentication Library
- ✅ **Managed Identity**: For Azure resource access

**Benefit:** Can authenticate user, check their database permissions before running SQL

---

## Integration Architecture

### Proposed Architecture: Wrapper Pattern

**Strategy:** Wrap your existing NL2SQL pipeline with M365 Agents SDK agent container.

```
┌─────────────────────────────────────────────────────────────────┐
│ Microsoft Teams                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ User: "How many loans are in default status?"           │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS POST
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Azure Bot Service                                               │
│  - Validates sender                                             │
│  - Routes to messaging endpoint                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Azure App Service (Your App)                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ /api/messages Endpoint                                  │   │
│  │  - M365 Agents SDK CloudAdapter                         │   │
│  │  - AgentApplication container                           │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                      │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │ teams_nl2sql_agent.py (NEW)                            │   │
│  │  - Receives Teams message                               │   │
│  │  - Extracts user query                                  │   │
│  │  - Shows typing indicator                               │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                      │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │ nl2sql_pipeline.py (EXISTING - Refactored)             │   │
│  │  - extract_intent(query)                                │   │
│  │  - generate_sql(intent, schema_context)                 │   │
│  │  - execute_sql(sql_query)                               │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                      │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │ schema_reader.py (EXISTING)                             │   │
│  │  - get_sql_database_schema_context()                    │   │
│  └───────────────────────┬─────────────────────────────────┘   │
│                          │                                      │
│  ┌───────────────────────▼─────────────────────────────────┐   │
│  │ sql_executor.py (EXISTING)                              │   │
│  │  - execute_sql_query(sql)                               │   │
│  └───────────────────────┬─────────────────────────────────┘   │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ Azure SQL Database (TERADATA-FI)                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Results Formatting Layer (NEW)                                  │
│  - Format as Adaptive Card                                      │
│  - Add action buttons (Export, Explain, Refine)                 │
│  - Show SQL query (collapsible)                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Microsoft Teams (Response)                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 📊 Query Results (12 loans in default)                  │   │
│  │ ┌────────────────────────────────────────────────────┐   │   │
│  │ │ LoanID | Customer | Balance | Days Past Due       │   │   │
│  │ │ L001   | Acme     | $50,000 | 45                   │   │   │
│  │ │ L002   | TechCo   | $75,000 | 62                   │   │   │
│  │ └────────────────────────────────────────────────────┘   │   │
│  │ [📥 Export] [🔍 Show SQL] [✏️ Refine Query]           │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Core Agent Wrapper (Week 1)

**Goal:** Get basic Teams bot responding to queries

**Tasks:**
1. **Install M365 Agents SDK**
   ```bash
   pip install microsoft-agents-sdk
   ```

2. **Create Azure Bot Resource**
   - Go to Azure Portal
   - Create "Azure Bot" resource
   - Record: App ID, Tenant ID, Client Secret
   - Add Microsoft Teams channel

3. **Create `teams_nl2sql_agent.py`** (NEW FILE)
   ```python
   """
   Microsoft Teams wrapper for NL2SQL pipeline using M365 Agents SDK
   """
   import logging
   from microsoft_agents.hosting.core import (
       AgentApplication, TurnContext, TurnState, MemoryStorage
   )
   from microsoft_agents.hosting.aiohttp import CloudAdapter
   from microsoft_agents.authentication.msal import MsalConnectionManager
   from microsoft_agents.activity import load_configuration_from_env
   
   # Import your existing NL2SQL functions
   from nl2sql_pipeline import extract_intent, generate_sql, format_results
   from sql_executor import execute_sql_query
   from schema_reader import get_sql_database_schema_context
   
   # Setup logging
   logger = logging.getLogger(__name__)
   
   # Load configuration from environment
   from os import environ
   from dotenv import load_dotenv
   load_dotenv()
   
   agents_config = load_configuration_from_env(environ)
   
   # Initialize agent components
   STORAGE = MemoryStorage()
   CONNECTION_MANAGER = MsalConnectionManager(**agents_config)
   ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)
   
   # Create agent application
   AGENT_APP = AgentApplication[TurnState](
       storage=STORAGE,
       adapter=ADAPTER,
       **agents_config
   )
   
   @AGENT_APP.conversation_update("membersAdded")
   async def on_members_added(context: TurnContext, state: TurnState):
       """Welcome message when bot is added to conversation"""
       await context.send_activity(
           "👋 Hi! I'm your NL2SQL assistant. "
           "Ask me questions about the database in natural language!\n\n"
           "Examples:\n"
           "• How many loan applications do we have?\n"
           "• Show top 10 customers by loan balance\n"
           "• What is the total payment volume this month?"
       )
       return True
   
   @AGENT_APP.activity("message")
   async def on_message(context: TurnContext, state: TurnState):
       """Handle incoming messages with NL2SQL pipeline"""
       try:
           user_query = context.activity.text
           logger.info(f"Received query: {user_query}")
           
           # Show typing indicator
           await context.send_activity({"type": "typing"})
           
           # Step 1: Extract intent (using your existing Azure AI Agents)
           intent = extract_intent(user_query)
           logger.info(f"Intent extracted: {intent}")
           
           # Step 2: Get schema context
           schema_context = get_sql_database_schema_context()
           
           # Step 3: Generate SQL
           sql_query = generate_sql(intent, schema_context)
           logger.info(f"Generated SQL: {sql_query}")
           
           # Step 4: Execute SQL
           results = execute_sql_query(sql_query)
           logger.info(f"Query returned {len(results)} rows")
           
           # Step 5: Format results for Teams
           response_text = format_results_for_teams(results, sql_query)
           
           # Send response
           await context.send_activity(response_text)
           
       except Exception as e:
           logger.error(f"Error processing query: {e}", exc_info=True)
           await context.send_activity(
               f"❌ Sorry, I encountered an error: {str(e)}\n\n"
               "Please try rephrasing your question or contact support."
           )
   
   @AGENT_APP.error
   async def on_error(context: TurnContext, error: Exception):
       """Global error handler"""
       logger.error(f"Unhandled error: {error}", exc_info=True)
       await context.send_activity(
           "⚠️ The bot encountered an unexpected error. "
           "Please try again or contact support."
       )
   
   def format_results_for_teams(results, sql_query):
       """Format SQL results as Teams-friendly message"""
       if not results:
           return "No results found for your query."
       
       # Limit to first 10 rows for display
       display_rows = results[:10]
       
       # Create simple text table
       columns = list(display_rows[0].keys())
       col_widths = {c: max(len(c), max(len(str(r[c])) for r in display_rows)) 
                     for c in columns}
       
       # Header
       header = " | ".join(c.ljust(col_widths[c]) for c in columns)
       separator = "-+-".join("-" * col_widths[c] for c in columns)
       
       # Rows
       rows = []
       for r in display_rows:
           rows.append(" | ".join(str(r[c]).ljust(col_widths[c]) for c in columns))
       
       # Assemble message
       message = f"**📊 Query Results ({len(results)} total)**\n\n"
       message += f"```\n{header}\n{separator}\n" + "\n".join(rows) + "\n```\n\n"
       
       if len(results) > 10:
           message += f"_Showing first 10 of {len(results)} results_\n\n"
       
       message += f"<details><summary>🔍 View SQL Query</summary>\n\n```sql\n{sql_query}\n```\n</details>"
       
       return message
   ```

4. **Create `start_server.py`** (NEW FILE)
   ```python
   """
   aiohttp server to host the Teams agent
   """
   from aiohttp import web
   from microsoft_agents.hosting.aiohttp import aiohttp_handler
   from teams_nl2sql_agent import AGENT_APP, CONNECTION_MANAGER
   
   async def messages_handler(request):
       """Handle incoming messages from Teams"""
       return await aiohttp_handler(
           request=request,
           agent_application=AGENT_APP,
           auth_configuration=CONNECTION_MANAGER.get_default_connection_configuration()
       )
   
   def start_server():
       """Start the aiohttp web server"""
       app = web.Application()
       app.router.add_post("/api/messages", messages_handler)
       
       web.run_app(app, host="0.0.0.0", port=3978)
   
   if __name__ == "__main__":
       print("Starting NL2SQL Teams Agent...")
       print("Listening on http://localhost:3978/api/messages")
       start_server()
   ```

5. **Refactor `nl2sql_main.py` into reusable functions** (MODIFY EXISTING)
   ```python
   """
   Refactored nl2sql_main.py to export reusable functions
   """
   # Keep all existing code, but export these functions:
   
   def extract_intent(query: str) -> str:
       """Extract intent from natural language query"""
       # Your existing logic
       return intent_entities
   
   def generate_sql(intent: str, schema_context: str = None) -> str:
       """Generate SQL from intent"""
       # Your existing logic
       return sanitized_sql
   
   def execute_and_format(sql: str) -> dict:
       """Execute SQL and return formatted results"""
       # Your existing logic
       return {
           "rows": rows,
           "count": len(rows),
           "sql": sql,
           "duration": duration
       }
   
   # Keep existing main() for CLI usage
   if __name__ == "__main__":
       sys.exit(main())
   ```

6. **Update `.env` with Bot Configuration**
   ```bash
   # Existing Azure AI + SQL config
   PROJECT_ENDPOINT=...
   MODEL_DEPLOYMENT_NAME=...
   AZURE_SQL_SERVER=...
   AZURE_SQL_DB=...
   
   # NEW: Azure Bot Service config
   CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=<bot-app-id>
   CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=<bot-secret>
   CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=<tenant-id>
   ```

7. **Create `requirements_teams.txt`**
   ```
   # Existing dependencies
   azure-ai-projects>=1.0.0
   azure-identity>=1.19.0
   pyodbc>=5.2.0
   python-dotenv>=1.0.0
   
   # NEW: M365 Agents SDK
   microsoft-agents-sdk>=1.0.0
   aiohttp>=3.8.0
   ```

8. **Test Locally with Dev Tunnel**
   ```bash
   # Install dev tunnel
   # https://learn.microsoft.com/azure/developer/dev-tunnels/get-started
   
   # Start tunnel
   devtunnel host -p 3978 --allow-anonymous
   
   # Note the URL: https://abc123.devtunnels.ms
   
   # Update Azure Bot messaging endpoint to:
   # https://abc123.devtunnels.ms/api/messages
   
   # Run agent
   python start_server.py
   
   # Test in Azure Portal: Azure Bot > Test in Web Chat
   ```

### Phase 2: Rich Adaptive Cards (Week 2)

**Goal:** Display results in beautiful, interactive cards

**Tasks:**
1. **Install Adaptive Cards library**
   ```bash
   pip install adaptivecards
   ```

2. **Create `adaptive_card_builder.py`** (NEW FILE)
   ```python
   """
   Build Adaptive Cards for SQL query results
   """
   from typing import List, Dict, Any
   
   def build_results_card(results: List[Dict], sql_query: str, row_count: int) -> dict:
       """Build Adaptive Card for query results"""
       
       # Limit display
       display_rows = results[:10]
       columns = list(display_rows[0].keys()) if display_rows else []
       
       card = {
           "type": "AdaptiveCard",
           "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
           "version": "1.4",
           "body": [
               {
                   "type": "Container",
                   "items": [
                       {
                           "type": "TextBlock",
                           "text": f"📊 Query Results",
                           "size": "Large",
                           "weight": "Bolder"
                       },
                       {
                           "type": "TextBlock",
                           "text": f"{row_count} rows returned",
                           "isSubtle": True,
                           "spacing": "None"
                       }
                   ]
               },
               {
                   "type": "Container",
                   "separator": True,
                   "spacing": "Medium",
                   "items": build_table_rows(display_rows, columns)
               }
           ],
           "actions": [
               {
                   "type": "Action.Submit",
                   "title": "📥 Export to CSV",
                   "data": {"action": "export", "sql": sql_query}
               },
               {
                   "type": "Action.ShowCard",
                   "title": "🔍 View SQL",
                   "card": {
                       "type": "AdaptiveCard",
                       "body": [
                           {
                               "type": "TextBlock",
                               "text": sql_query,
                               "wrap": True,
                               "fontType": "Monospace"
                           }
                       ]
                   }
               },
               {
                   "type": "Action.Submit",
                   "title": "✏️ Refine Query",
                   "data": {"action": "refine", "sql": sql_query}
               }
           ]
       }
       
       if row_count > 10:
           card["body"].append({
               "type": "TextBlock",
               "text": f"_Showing first 10 of {row_count} results_",
               "isSubtle": True,
               "spacing": "Medium"
           })
       
       return card
   
   def build_table_rows(rows: List[Dict], columns: List[str]) -> List[Dict]:
       """Build table rows for Adaptive Card"""
       items = []
       
       # Header row
       header_columns = [
           {
               "type": "Column",
               "width": "auto",
               "items": [
                   {
                       "type": "TextBlock",
                       "text": col,
                       "weight": "Bolder",
                       "wrap": True
                   }
               ]
           }
           for col in columns
       ]
       
       items.append({
           "type": "ColumnSet",
           "columns": header_columns
       })
       
       # Data rows
       for row in rows:
           row_columns = [
               {
                   "type": "Column",
                   "width": "auto",
                   "items": [
                       {
                           "type": "TextBlock",
                           "text": str(row[col]),
                           "wrap": True
                       }
                   ]
               }
               for col in columns
           ]
           
           items.append({
               "type": "ColumnSet",
               "columns": row_columns,
               "separator": True
           })
       
       return items
   ```

3. **Update `teams_nl2sql_agent.py` to use Adaptive Cards**
   ```python
   from adaptive_card_builder import build_results_card
   
   @AGENT_APP.activity("message")
   async def on_message(context: TurnContext, state: TurnState):
       # ... existing code ...
       
       # Create Adaptive Card
       card = build_results_card(results, sql_query, len(results))
       
       # Send as attachment
       await context.send_activity({
           "type": "message",
           "attachments": [{
               "contentType": "application/vnd.microsoft.card.adaptive",
               "content": card
           }]
       })
   ```

### Phase 3: Advanced Features (Week 3-4)

**Features to Add:**

1. **Conversation State**
   - Remember previous queries
   - Support follow-up questions ("Show me more details")
   - User preferences (default database, row limits)

2. **File Export**
   - Export results as CSV
   - Export results as Excel
   - Save to SharePoint/OneDrive

3. **Query Templates**
   - Predefined queries users can trigger
   - Message extensions for quick queries
   - Suggested queries based on schema

4. **Security & Permissions**
   - SSO with Microsoft Entra ID
   - Row-level security based on user identity
   - Audit logging of queries

5. **Performance Optimizations**
   - Cache frequently-run queries
   - Stream large result sets
   - Pagination for big tables

---

## Deployment Strategy

### Local Development
```bash
# Terminal 1: Start dev tunnel
devtunnel host -p 3978 --allow-anonymous

# Terminal 2: Run agent
python start_server.py

# Test in Azure Portal Web Chat
```

### Production Deployment

**Option A: Azure App Service (Recommended)**
```bash
# Deploy to App Service
az webapp up --name nl2sql-teams-bot --resource-group rg-nl2sql

# Configure endpoint in Azure Bot
# https://nl2sql-teams-bot.azurewebsites.net/api/messages
```

**Option B: Azure Container Apps**
```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements_teams.txt .
RUN pip install -r requirements_teams.txt
COPY . .
CMD ["python", "start_server.py"]
```

### Teams Manifest

**Create `manifest.json`:**
```json
{
  "$schema": "https://developer.microsoft.com/json-schemas/teams/v1.16/MicrosoftTeams.schema.json",
  "manifestVersion": "1.16",
  "version": "1.0.0",
  "id": "<<AAD_APP_CLIENT_ID>>",
  "packageName": "com.yourcompany.nl2sql",
  "developer": {
    "name": "Your Company",
    "websiteUrl": "https://yourcompany.com",
    "privacyUrl": "https://yourcompany.com/privacy",
    "termsOfUseUrl": "https://yourcompany.com/terms"
  },
  "name": {
    "short": "NL2SQL Assistant",
    "full": "Natural Language to SQL Query Assistant"
  },
  "description": {
    "short": "Ask database questions in natural language",
    "full": "AI-powered assistant that converts your natural language questions into SQL queries and returns results directly in Teams"
  },
  "icons": {
    "outline": "outline.png",
    "color": "color.png"
  },
  "accentColor": "#0078D4",
  "bots": [
    {
      "botId": "<<AAD_APP_CLIENT_ID>>",
      "scopes": ["personal", "team", "groupChat"],
      "supportsFiles": false,
      "isNotificationOnly": false,
      "commandLists": [
        {
          "scopes": ["personal", "team", "groupChat"],
          "commands": [
            {
              "title": "help",
              "description": "Show available commands and examples"
            },
            {
              "title": "schema",
              "description": "View database schema information"
            }
          ]
        }
      ]
    }
  ],
  "permissions": ["identity", "messageTeamMembers"],
  "validDomains": ["<<BOT_DOMAIN>>"]
}
```

**Deploy to Teams:**
```bash
# Zip manifest files
zip manifest.zip manifest.json outline.png color.png

# Upload to Microsoft Admin Center
# Settings > Integrated Apps > Upload Custom App
```

---

## Code Reusability Analysis

### What You Can Reuse (90%+)

✅ **schema_reader.py** - Use as-is  
✅ **sql_executor.py** - Use as-is  
✅ **nl2sql_main.py** - Refactor into functions (minor changes)  
✅ **Azure AI Agent setup** - Same agents, same prompts  
✅ **Schema discovery logic** - No changes needed  
✅ **SQL generation** - No changes needed  
✅ **.env configuration** - Add bot credentials  

### What You Need to Add (10%)

🆕 **teams_nl2sql_agent.py** - M365 Agents SDK wrapper (~200 lines)  
🆕 **start_server.py** - aiohttp server (~50 lines)  
🆕 **adaptive_card_builder.py** - Rich formatting (~150 lines)  
🆕 **manifest.json** - Teams app manifest (~50 lines)  
🆕 **requirements_teams.txt** - Add M365 SDK dependencies  

---

## Benefits of Teams Integration

### For Users
1. ✅ **No CLI Required**: Natural Teams chat interface
2. ✅ **Rich Formatting**: Beautiful adaptive cards with tables
3. ✅ **Collaboration**: Share queries and results in channels
4. ✅ **Mobile Access**: Query from Teams mobile app
5. ✅ **Export Options**: CSV/Excel export with one click
6. ✅ **Contextual**: Ask follow-up questions in same conversation

### For Your Organization
1. ✅ **Centralized**: All database queries through one bot
2. ✅ **Audit Trail**: All queries logged (who, what, when)
3. ✅ **Access Control**: Leverage Teams permissions
4. ✅ **Scalable**: Azure App Service auto-scaling
5. ✅ **Secure**: Bot-to-Bot authentication, encrypted traffic
6. ✅ **Discoverable**: Available in Teams app store

### Technical Benefits
1. ✅ **95% Code Reuse**: Minimal changes to existing pipeline
2. ✅ **Same AI Backend**: Azure AI Agents, no migration needed
3. ✅ **Multi-Channel**: Works in Teams AND M365 Copilot
4. ✅ **Production-Ready**: Built on enterprise-grade SDK
5. ✅ **Extensible**: Easy to add new features (file export, etc.)

---

## Sample User Experience

### Scenario 1: Simple Query
```
User: @NL2SQL How many loans are in default?

Bot: [Typing indicator...]

Bot: [Adaptive Card]
     📊 Query Results (12 rows)
     
     Status  | Count | Total Balance
     --------|-------|---------------
     Default | 12    | $847,500
     
     [📥 Export] [🔍 View SQL] [✏️ Refine Query]
```

### Scenario 2: Follow-up Question
```
User: Show me those 12 loans with borrower details

Bot: [Adaptive Card]
     📊 Query Results (12 rows)
     
     LoanID | Borrower      | Balance  | Days Past Due
     -------|---------------|----------|---------------
     L001   | Acme Corp     | $50,000  | 45
     L002   | TechStartup   | $75,000  | 62
     ...
     
     [📥 Export] [🔍 View SQL] [✏️ Refine Query]
```

### Scenario 3: Complex Analysis
```
User: What's the month-over-month trend in loan originations for 2024?

Bot: [Adaptive Card with Chart]
     📊 Query Results (12 rows)
     
     Month    | Applications | Approved | Avg Amount
     ---------|--------------|----------|------------
     Jan 2024 | 245          | 198      | $125,000
     Feb 2024 | 287          | 234      | $135,000
     ...
     
     📈 [View Trend Chart]
     [📥 Export] [🔍 View SQL] [✏️ Refine Query]
```

---

## Next Steps

### Immediate (This Week)
1. ✅ Review this document
2. ✅ Create Azure Bot resource
3. ✅ Install M365 Agents SDK: `pip install microsoft-agents-sdk`
4. ✅ Set up dev tunnel for local testing
5. ✅ Refactor nl2sql_main.py into reusable functions

### Short Term (Next 2 Weeks)
1. ✅ Build basic Teams agent wrapper
2. ✅ Test with simple queries in Web Chat
3. ✅ Deploy to Azure App Service
4. ✅ Create Teams manifest
5. ✅ Test in Teams (personal chat)

### Medium Term (Next Month)
1. ✅ Add Adaptive Cards for rich formatting
2. ✅ Implement conversation state
3. ✅ Add export functionality (CSV/Excel)
4. ✅ Deploy to Teams channels
5. ✅ User acceptance testing

### Long Term (Next Quarter)
1. ✅ Add SSO and permission checking
2. ✅ Implement query templates/shortcuts
3. ✅ Add to M365 Copilot
4. ✅ Performance optimizations
5. ✅ Production monitoring and analytics

---

## Estimated Effort

### Development Time
- **Phase 1 (Basic Agent)**: 3-5 days
- **Phase 2 (Adaptive Cards)**: 2-3 days
- **Phase 3 (Advanced Features)**: 5-10 days
- **Testing & Refinement**: 3-5 days

**Total**: ~2-3 weeks for production-ready Teams bot

### Resources Needed
- 1 Python developer (familiar with your NL2SQL code)
- Access to Azure subscription
- Teams admin access for app deployment
- Test environment for validation

---

## Conclusion

The Microsoft 365 Agents SDK provides an **ideal bridge** between your existing NL2SQL pipeline and Microsoft Teams. With ~90% code reuse and only ~400 lines of new wrapper code, you can:

✅ Deploy your NL2SQL assistant to Teams  
✅ Provide rich, interactive experiences with Adaptive Cards  
✅ Scale to thousands of users with Azure infrastructure  
✅ Extend to M365 Copilot with minimal additional work  

**Recommendation:** Start with Phase 1 (basic agent) to validate the integration, then progressively add advanced features based on user feedback.

---

## References

- [M365 Agents SDK Docs](https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/)
- [Python Samples on GitHub](https://github.com/microsoft/Agents/tree/main/samples/python)
- [Adaptive Cards Designer](https://adaptivecards.io/designer/)
- [Azure Bot Service Docs](https://learn.microsoft.com/en-us/azure/bot-service/)
- [Teams App Manifest Schema](https://learn.microsoft.com/en-us/microsoftteams/platform/resources/schema/manifest-schema)
