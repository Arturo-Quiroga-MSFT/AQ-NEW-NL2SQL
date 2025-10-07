# Agent Persistence in Azure AI NL2SQL Pipeline

## Summary

✅ **Agents NOW PERSIST in Azure AI Foundry** - they are NOT deleted after use

## Agent Architecture

### Number of Agents: **2 Persistent Agents**

1. **`intent-extractor-persistent`**
   - Purpose: Analyzes natural language queries
   - Extracts: intent, entities, metrics, filters, group_by
   - Returns: JSON structure

2. **`sql-generator-persistent`**
   - Purpose: Generates T-SQL queries
   - Uses: Database schema context in instructions
   - Returns: SQL query string

## Agent Lifecycle

### Previous Behavior (❌ Removed)
```python
# Created fresh for each query
agent_id = _create_intent_agent()
try:
    # Use agent
    ...
finally:
    # DELETED after use
    project_client.agents.delete_agent(agent_id)
```

**Problem**: 
- ~300-400ms overhead per query (agent creation time)
- New agents created for every single query
- Agents were deleted immediately after use

### New Behavior (✅ Current)
```python
# Get or create persistent agent
agent_id = _get_or_create_intent_agent()
# Use agent
...
# Agent is NOT deleted - persists in Azure AI Foundry
```

**Benefits**:
- ✅ Agents are created once and reused
- ✅ Faster subsequent queries (no creation overhead)
- ✅ Agents persist in Azure AI Foundry portal
- ✅ Can be managed, monitored, and traced in Azure AI Foundry

## Persistence Behavior

### Within Same Python Process
```python
# First query
python nl2sql_main.py --query "How many customers?"
# Creates: intent-extractor-persistent, sql-generator-persistent
# Agents stored in global variables

# Second query (if run in same process/script)
python nl2sql_main.py --query "How many loans?"
# Reuses: same agent IDs from global variables
# No creation overhead
```

### Across Separate CLI Invocations
```bash
# Terminal 1
python nl2sql_main.py --query "How many customers?"
# Creates agents with IDs: asst_ABC123, asst_XYZ789
# Process exits, global variables cleared

# Terminal 2 (new process)
python nl2sql_main.py --query "How many loans?"
# Creates NEW agents with IDs: asst_DEF456, asst_UVW012
# Cannot reuse previous agents (different process)
```

**Result**: Each CLI invocation creates new agents because Python process exits

### In Azure AI Foundry (Persistent Storage)
```
All agents persist in Azure AI Foundry project:
- asst_5dR8IrZCEuF4xJRZz3ymblJa (intent-extractor-persistent)
- asst_rEROMPLs03RyQJhXUZVsaYqu (sql-generator-persistent)
- asst_htBCW8FTGCmftUwQf3MaBlUQ (intent-extractor-persistent)
- asst_GBDvBxJ1LPRZFBMZGZHBcexJ (sql-generator-persistent)
...and more from previous runs
```

**Important**: Agents remain in Azure AI Foundry even after script exits!

## How to Verify Agents

### List All Agents
```bash
python list_agents.py
```

Output shows:
- Agent ID
- Agent name
- Model used
- Creation timestamp
- Total count

### Check in Azure AI Foundry Portal
1. Go to [Azure AI Foundry](https://ai.azure.com)
2. Open your project: `firstProject`
3. Navigate to: **Agents** section
4. View all persistent agents

## Agent Reuse Strategy

### Current Implementation (Per-Process Reuse)
```python
# Global variables at module level
_INTENT_AGENT_ID = None
_SQL_AGENT_ID = None

def _get_or_create_intent_agent():
    global _INTENT_AGENT_ID
    if _INTENT_AGENT_ID is None:
        # Create agent
        _INTENT_AGENT_ID = agent.id
    return _INTENT_AGENT_ID
```

**Scope**: Single Python process only

### For Production (Cross-Process Reuse)

To reuse agents across CLI invocations, you would need to:

1. **Store Agent IDs Persistently**
   ```python
   # Save to file
   with open('.agent_ids.json', 'w') as f:
       json.dump({
           'intent_agent_id': _INTENT_AGENT_ID,
           'sql_agent_id': _SQL_AGENT_ID
       }, f)
   
   # Load on startup
   if os.path.exists('.agent_ids.json'):
       with open('.agent_ids.json', 'r') as f:
           ids = json.load(f)
           _INTENT_AGENT_ID = ids['intent_agent_id']
           _SQL_AGENT_ID = ids['sql_agent_id']
   ```

2. **Verify Agents Still Exist**
   ```python
   try:
       # Try to use existing agent
       agent = client.agents.get_agent(_INTENT_AGENT_ID)
   except Exception:
       # Agent was deleted, create new one
       _INTENT_AGENT_ID = None
   ```

3. **Use Named Agents**
   - Search for agent by name instead of creating new ones
   - Reuse existing agent if name matches

## Schema Change Handling

The SQL agent is automatically recreated if the schema changes:

```python
def _get_or_create_sql_agent(schema_context):
    global _SQL_AGENT_ID, _SQL_AGENT_SCHEMA
    
    # Recreate if schema changed
    if _SQL_AGENT_SCHEMA != schema_context:
        # Delete old agent
        if _SQL_AGENT_ID:
            project_client.agents.delete_agent(_SQL_AGENT_ID)
        # Create new agent with updated schema
        agent = project_client.agents.create_agent(
            instructions=f"Schema: {schema_context}..."
        )
```

## Cleanup Old Agents

Since agents persist in Azure AI Foundry, you may want to clean up old ones:

### Manual Cleanup Script
```bash
python cleanup_agents.py
```

This would:
1. List all agents
2. Filter by name pattern (e.g., `*-persistent`)
3. Delete agents older than X days
4. Keep only the most recent N agents

### Azure AI Foundry Portal
1. Go to Agents section
2. Select agents to delete
3. Click Delete

## Performance Impact

### Before (Deleted After Use)
```
Query 1: Create agents (400ms) + Execute (2s) = 2.4s
Query 2: Create agents (400ms) + Execute (2s) = 2.4s
Query 3: Create agents (400ms) + Execute (2s) = 2.4s
Total: 7.2s
```

### After (Persistent Agents - Same Process)
```
Query 1: Create agents (400ms) + Execute (2s) = 2.4s
Query 2: Reuse agents (0ms) + Execute (2s) = 2.0s
Query 3: Reuse agents (0ms) + Execute (2s) = 2.0s
Total: 6.4s (11% faster)
```

### After (Persistent Agents - Separate CLI Calls)
```
Query 1: Create agents (400ms) + Execute (2s) = 2.4s
Query 2: Create agents (400ms) + Execute (2s) = 2.4s  # New process
Query 3: Create agents (400ms) + Execute (2s) = 2.4s  # New process
Total: 7.2s (same as before)
```

**Conclusion**: Performance benefit only applies within same Python process

## Best Practices

### ✅ Do This
1. **Keep agents persistent** - Don't delete after use
2. **Monitor agent count** - Run `list_agents.py` periodically
3. **Use descriptive names** - `intent-extractor-persistent` vs `agent-123`
4. **Clean up old agents** - Delete unused agents from portal
5. **Log agent creation** - `[DEBUG]` messages show when agents are created

### ❌ Don't Do This
1. Delete agents after every use (defeats persistence)
2. Create agents with generic names (hard to identify)
3. Let agents accumulate indefinitely (portal becomes cluttered)
4. Assume cross-process reuse (requires additional implementation)

## Debug Output

The implementation now includes debug messages:

```
[DEBUG] Created persistent intent agent: asst_5dR8IrZCEuF4xJRZz3ymblJa
[DEBUG] Created persistent SQL agent: asst_rEROMPLs03RyQJhXUZVsaYqu
```

These show when agents are:
- **Created** (first time)
- **Reused** (no debug message = reusing existing agent)
- **Recreated** (schema change = "Deleted old SQL agent")

## Summary

| Aspect | Status |
|--------|--------|
| **Number of Agents** | 2 (intent + SQL) |
| **Persistence** | ✅ Yes, in Azure AI Foundry |
| **Deletion** | ❌ No, agents persist |
| **Reuse** | ✅ Within same process |
| **Cross-CLI Reuse** | ❌ No (requires additional code) |
| **Schema Handling** | ✅ Auto-recreate if schema changes |
| **Monitoring** | ✅ Via `list_agents.py` or portal |

The agents are now persistent and will remain in your Azure AI Foundry project! 🎉
