# Teams NL2SQL Bot - Phase 1 Implementation

## 🎉 What We've Built

A Microsoft Teams bot that enables natural language database queries directly in Teams chat! Users can ask questions in plain English and get SQL results back instantly.

### Architecture

```
Teams Message
    ↓
M365 Agents SDK (teams_nl2sql_agent.py)
    ↓
NL2SQL Pipeline (nl2sql_main.py)
    ├─ Extract Intent (Azure AI Agent)
    ├─ Generate SQL (Azure AI Agent)
    └─ Execute Query (sql_executor.py)
    ↓
Format Results
    ↓
Teams Response
```

### Code Reuse: 90%+

- ✅ **Existing Code Reused**: `nl2sql_main.py`, `schema_reader.py`, `sql_executor.py`
- ✅ **New Wrapper Code**: `teams_nl2sql_agent.py` (~270 lines), `start_server.py` (~100 lines)
- ✅ **Total New Code**: ~370 lines

## 📁 Files Created/Modified

### Modified Files

1. **requirements.txt**
   - Added comments for M365 Agents SDK installation (from TestPyPI)

2. **nl2sql_main.py**
   - Added `process_nl_query()` - Complete NL→SQL→Results pipeline
   - Added `execute_and_format()` - Execute SQL and format results
   - Added `get_token_usage()` - Get token statistics
   - Added `reset_token_usage()` - Reset counters
   - ✅ CLI still works! Backward compatible.

### New Files

3. **teams_nl2sql_agent.py** (~270 lines)
   - M365 Agents SDK wrapper
   - Handles Teams messages
   - Calls existing NL2SQL functions
   - Formats results for Teams
   - Event handlers:
     * `@on_members_added` - Welcome message
     * `@on_message` - Process queries
     * `@on_error` - Error handling
   - Built-in commands:
     * `/help` - Show help
     * `/about` - About the bot

4. **start_server.py** (~100 lines)
   - aiohttp web server
   - Hosts `/api/messages` endpoint
   - JWT authentication middleware
   - Port 3978 (standard bot port)

5. **run_teams_bot.sh**
   - Helper script to start bot
   - Activates venv automatically
   - Checks for dependencies

## 🚀 Quick Start (Local Testing)

### Prerequisites Checklist

- [x] Python 3.9-3.11
- [x] Virtual environment with packages installed
- [x] M365 Agents SDK installed from TestPyPI
- [ ] Azure Bot resource created
- [ ] Dev tunnel installed
- [ ] .env updated with bot credentials

### Step 1: Verify Installation

Make sure you've installed the M365 Agents SDK packages in your .venv:

```bash
# Activate your virtual environment first!
source ../.venv/bin/activate

# Then install M365 SDK packages
pip install -i https://test.pypi.org/simple/ microsoft-agents-core
pip install -i https://test.pypi.org/simple/ microsoft-agents-authorization
pip install -i https://test.pypi.org/simple/ microsoft-agents-connector
pip install -i https://test.pypi.org/simple/ microsoft-agents-builder
pip install -i https://test.pypi.org/simple/ microsoft-agents-authentication-msal
pip install -i https://test.pypi.org/simple/ microsoft-agents-hosting-aiohttp
```

Verify installation:

```bash
python -c "from microsoft_agents.hosting.core import AgentApplication; print('✅ SDK installed!')"
```

### Step 2: Create Azure Bot Resource

1. Go to [Azure Portal](https://portal.azure.com)
2. Create new resource → Search for "Azure Bot"
3. Fill in details:
   - **Bot handle**: `nl2sql-teams-bot` (or your choice)
   - **Subscription**: Your subscription
   - **Resource group**: Create new or use existing
   - **Pricing tier**: F0 (Free)
   - **Microsoft App ID**: Create new
   - **App type**: Multi Tenant
4. Click "Create"
5. After creation, go to the bot resource:
   - Copy the **Microsoft App ID** (Client ID)
   - Go to "Configuration" → "Manage" next to Microsoft App ID
   - Create a new **Client Secret**
   - Copy the secret value (you won't see it again!)
   - Note your **Tenant ID** (from Entra ID)

### Step 3: Update .env File

Add these lines to your `.env` file:

```bash
# Azure Bot Configuration (for Teams integration)
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID=<your-app-id-here>
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET=<your-client-secret-here>
CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID=<your-tenant-id-here>
```

Replace the placeholders with your actual values from Step 2.

### Step 4: Install Dev Tunnel

```bash
# macOS
brew install devtunnels

# Or download from Microsoft
# https://learn.microsoft.com/azure/developer/dev-tunnels/get-started
```

Verify installation:

```bash
devtunnel --version
```

### Step 5: Start Dev Tunnel

```bash
# Login to dev tunnel
devtunnel user login

# Create and host tunnel on port 3978
devtunnel host -p 3978 --allow-anonymous
```

You'll see output like:

```
Hosting port: 3978
Connect via browser: https://abc123xyz.devtunnels.ms
Tunnel URL: https://abc123xyz.devtunnels.ms
```

**Copy the tunnel URL** - you'll need it in the next step!

### Step 6: Update Azure Bot Messaging Endpoint

1. Go back to your Azure Bot resource in Azure Portal
2. Navigate to "Configuration"
3. Update **Messaging endpoint** to:
   ```
   https://<your-tunnel-url>/api/messages
   ```
   Example: `https://abc123xyz.devtunnels.ms/api/messages`
4. Click "Apply"

### Step 7: Add Microsoft Teams Channel

1. In your Azure Bot resource, go to "Channels"
2. Click on "Microsoft Teams" icon
3. Accept the terms
4. Click "Apply"
5. Teams channel is now enabled!

### Step 8: Start the Bot

```bash
# Activate venv and start bot
./run_teams_bot.sh

# Or manually:
source ../.venv/bin/activate
python start_server.py
```

You should see:

```
============================================================
🤖 NL2SQL Teams Bot Server Starting...
============================================================
Host: localhost
Port: 3978
Endpoint: http://localhost:3978/api/messages
============================================================

======== Running on http://localhost:3978 ========
```

### Step 9: Test in Web Chat

1. Go to your Azure Bot resource
2. Click "Test in Web Chat" (left sidebar)
3. Send a message: "How many loans do we have?"
4. The bot should respond with SQL and results!

### Step 10: Test in Microsoft Teams

1. In Azure Bot, go to "Channels"
2. Click "Microsoft Teams" → "Open in Teams"
3. Teams will open with your bot
4. Start chatting with natural language queries!

## 💬 Example Conversations

### Basic Query

**You**: How many customers are in California?

**Bot**: 
```
✅ Query Results

Generated SQL:
```sql
SELECT COUNT(*) AS customer_count
FROM dim.Customers
WHERE State = 'CA'
```

Found 1 result(s):

customer_count
--------------
45
```

### Complex Query

**You**: Show me top 10 loans with balance over $50,000

**Bot**:
```
✅ Query Results

Generated SQL:
```sql
SELECT TOP 10 
    l.LoanNumber,
    c.CustomerName,
    l.OriginalAmount,
    b.CurrentBalance
FROM fact.Loans l
JOIN dim.Customers c ON l.CustomerKey = c.CustomerKey
JOIN fact.LoanBalances b ON l.LoanKey = b.LoanKey
WHERE b.CurrentBalance > 50000
ORDER BY b.CurrentBalance DESC
```

Found 10 result(s):

LoanNumber | CustomerName     | OriginalAmount | CurrentBalance
-----------|------------------|----------------|---------------
LN-001234  | Acme Corp        | 100000.00      | 87500.00
LN-002345  | TechStart Inc    | 95000.00       | 82300.00
...
```

## 🎯 Built-in Commands

- `/help` - Show help message with examples
- `/about` - Show bot information and architecture

## 🔧 Troubleshooting

### Issue: "Module not found: microsoft_agents"

**Solution**: Make sure you're using your virtual environment:

```bash
source ../.venv/bin/activate
pip list | grep microsoft-agents
```

If packages aren't installed, install them from TestPyPI (see Step 1).

### Issue: "401 Unauthorized" when testing

**Solution**: Check your .env file has correct bot credentials:

```bash
# Verify credentials are set
grep CONNECTIONS__SERVICE .env
```

Make sure you copied the Client Secret immediately after creating it (it's only shown once!).

### Issue: Bot doesn't respond in Web Chat

**Solution**: Check these:

1. Dev tunnel is running: `devtunnel host -p 3978 --allow-anonymous`
2. Bot server is running: `python start_server.py`
3. Messaging endpoint is correct in Azure Bot configuration
4. Endpoint format: `https://<tunnel-url>/api/messages`

### Issue: "Cannot resolve import" in VS Code

**Solution**: This is just a linting issue. The code will work if packages are installed in your venv. You can:

1. Ignore it (code works fine)
2. Set Python interpreter in VS Code to your .venv
3. Restart VS Code after installing packages

## 📊 What's Next?

### Remaining Tasks (Phase 1)

- [ ] **Task 5**: Update .env with Azure Bot credentials (see Step 3 above)
- [ ] **Task 6**: Test locally with dev tunnel (Steps 4-10 above)

### Phase 2 (Week 2) - Adaptive Cards UI

- [ ] Create `adaptive_card_builder.py`
- [ ] Format results as rich Adaptive Cards
- [ ] Add action buttons:
  - 📥 Export to CSV/Excel
  - 👁️ View SQL query
  - 🔄 Refine query
- [ ] Add data visualization (charts)

### Phase 3 (Week 3-4) - Production Features

- [ ] Conversation state management
- [ ] Query history
- [ ] SSO integration
- [ ] Role-based permissions
- [ ] Query result caching
- [ ] Production deployment (Azure App Service)

## 📚 Documentation

See also:

- `TEAMS_INTEGRATION_GUIDE.md` - Complete implementation guide
- `TEAMS_INTEGRATION_SUMMARY.md` - Quick reference
- `TEAMS_INTEGRATION_ARCHITECTURE.md` - Visual architecture diagrams

## 🤝 Getting Help

If you run into issues:

1. Check troubleshooting section above
2. Review M365 Agents SDK docs: https://learn.microsoft.com/microsoft-365/agents-sdk/
3. Check Azure Bot Service docs: https://learn.microsoft.com/azure/bot-service/

## 🎉 Success Criteria

You'll know it's working when:

1. ✅ Bot starts without errors
2. ✅ Dev tunnel shows "Connect via browser" URL
3. ✅ Azure Bot Web Chat receives messages
4. ✅ Bot responds with SQL query and results
5. ✅ Teams channel shows the bot
6. ✅ You can chat with bot in Teams!

**Ready to test?** Follow Steps 1-10 above! 🚀
