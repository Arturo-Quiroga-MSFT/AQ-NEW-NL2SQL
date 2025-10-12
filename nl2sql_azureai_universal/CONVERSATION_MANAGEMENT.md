# Conversation Management - Thread-Based Architecture

## Overview

The NL2SQL Teams Bot now supports **natural conversation flow** using Azure AI Agents' native thread management. Users can ask follow-up questions without repeating context, and the AI maintains conversation history automatically.

## Architecture

### Thread-Based Design

```
User Query 1: "Show top 5 customers"
    ↓
[Create New Thread] → thread_abc123
    ↓
AI Response: [Returns 5 customers]
    ↓
Store: conversation_id → thread_abc123

User Query 2: "Tell me about the third one"
    ↓
[Reuse Thread] → thread_abc123
    ↓
AI has context from Query 1 ✅
    ↓
AI Response: [Details about customer in row 3]
```

### Key Components

#### 1. Thread Storage (`CONVERSATION_THREADS`)
```python
# Simple in-memory dictionary
CONVERSATION_THREADS = {
    "teams_conversation_id_1": "thread_abc123",
    "teams_conversation_id_2": "thread_xyz789",
    ...
}
```

#### 2. Modified Pipeline Functions

**`extract_intent(query, thread_id=None)`**
- Accepts optional `thread_id` parameter
- If `thread_id` provided: Reuses existing thread
- If `thread_id` is None: Creates new thread
- Returns: `(intent_json, thread_id)` tuple

**`generate_sql(intent_entities, thread_id=None)`**
- Accepts optional `thread_id` parameter
- Reuses same thread from intent extraction
- Returns: `(sql_query, thread_id)` tuple

**`process_nl_query(query, execute=True, thread_id=None)`**
- Main entry point for Teams bot
- Passes `thread_id` through entire pipeline
- Returns result dict with `thread_id` field

#### 3. Teams Bot Integration

```python
# Get existing thread for this conversation
conversation_id = context.activity.conversation.id
thread_id = CONVERSATION_THREADS.get(conversation_id)

# Track if this is a follow-up
is_conversation = thread_id is not None

# Execute query with thread context
result = process_nl_query(user_query, execute=True, thread_id=thread_id)

# Store thread for next query
CONVERSATION_THREADS[conversation_id] = result.get("thread_id")
```

## User Experience

### Visual Indicators

#### First Query (New Conversation)
```
┌─────────────────────────────────────┐
│ ✅ Query Results                    │
│    Found 5 result(s)                │
├─────────────────────────────────────┤
│ 📝 Generated SQL                    │
│ SELECT TOP 5 ...                    │
├─────────────────────────────────────┤
│ [Results Table]                     │
└─────────────────────────────────────┘
```

#### Follow-Up Query (Active Conversation)
```
┌─────────────────────────────────────┐
│ 💬 Conversation Active • I remember │
│    our previous queries             │
├─────────────────────────────────────┤
│ ✅ Query Results                    │
│    Found 1 result(s)                │
├─────────────────────────────────────┤
│ 📝 Generated SQL                    │
│ SELECT * FROM ...                   │
│ WHERE CustomerKey = 58              │
├─────────────────────────────────────┤
│ [Results Table]                     │
└─────────────────────────────────────┘
```

### Commands

#### `/reset` - Start Fresh Conversation
Clears the thread for current conversation, allowing user to start over without context.

```
User: /reset
Bot: ✅ Conversation reset! Starting fresh. Previous context cleared.
```

#### `/help` - Show Help with Conversation Features
Updated help text includes conversation management guidance.

## Example Conversations

### Scenario 1: Customer Inquiry
```
User: "Show me top 5 customers by loan balance"
Bot: [Shows 5 customers] (No conversation badge)

User: "Tell me about the customer in row 3"
Bot: [Shows details for CUST00058] (💬 Conversation badge appears)

User: "What was their total balance?"
Bot: [Shows balance details] (💬 Conversation badge appears)

User: /reset
Bot: ✅ Conversation reset!

User: "Show accounts in California"
Bot: [New query results] (No badge - fresh start)
```

### Scenario 2: Complex Analysis
```
User: "List all active loans"
Bot: [Shows active loans]

User: "Filter those by amounts over $1M"
Bot: [Filters previous results naturally] (💬 badge)

User: "Group by state"
Bot: [Groups filtered results] (💬 badge)

User: "Which state has the highest total?"
Bot: [Aggregates grouped data] (💬 badge)
```

## Technical Implementation

### Code Changes Summary

#### 1. `nl2sql_main.py`
- **Lines 212-265**: `extract_intent()` - Added thread reuse logic
- **Lines 267-338**: `generate_sql()` - Added thread reuse logic  
- **Lines 433-480**: `process_nl_query()` - Added thread_id parameter and return

#### 2. `teams_nl2sql_agent.py`
- **Line 87**: Changed `CONVERSATION_HISTORY` → `CONVERSATION_THREADS`
- **Lines 180-217**: Added `/reset` command handler
- **Lines 258-268**: Thread management in message handler
- **Removed**: ~60 lines of manual context injection code

#### 3. `adaptive_cards.py`
- **Lines 91-92**: Added `is_conversation` parameter to `create_success_card()`
- **Lines 112-127**: Added conversation badge to success cards
- **Lines 437-438**: Added `is_conversation` parameter to `create_error_card()`
- **Lines 463-478**: Added conversation badge to error cards

### Why This Approach Works

#### ✅ Advantages

1. **Native SDK Support**: Uses Azure AI Agents' built-in conversation management
2. **Automatic Context**: AI naturally understands references like "the third one", "their balance"
3. **Simple Code**: Removed 60+ lines of manual context injection
4. **Scalable**: Threads maintained by Azure, not manual data formatting
5. **Transparent**: Visual indicators show users when context is active

#### ❌ Previous Approach (Deprecated)

The old approach manually injected context:
```python
# OLD: Manual context injection (removed)
context_info = f"Previous query returned: {last_results}"
context_info += f"Row [1]: {row_1_data}, Row [2]: {row_2_data}..."
enhanced_query = context_info + user_query  # Fragile!
```

**Problems:**
- Brittle: "Row 1" confused AI (thought it was SQL `ROW` keyword)
- Limited: Only stored last query, not full conversation
- Manual: Required complex string formatting
- Not conversational: AI couldn't naturally understand references

#### ✅ Current Approach (Thread-Based)

```python
# NEW: Thread-based conversation (current)
thread_id = CONVERSATION_THREADS.get(conversation_id)
result = process_nl_query(query, thread_id=thread_id)
CONVERSATION_THREADS[conversation_id] = result["thread_id"]
```

**Benefits:**
- Clean: 3 lines vs 60+ lines
- Natural: AI understands "the third customer", "their balance"
- Robust: Azure manages conversation state
- Conversational: True multi-turn dialogue

## Deployment History

| Revision | Date | Changes |
|----------|------|---------|
| 0000018 | Oct 10, 2025 | Last version with manual context injection |
| 0000019 | Oct 11, 2025 | Thread-based conversation management |
| 0000020 | Oct 11, 2025 | Added conversation indicators to Adaptive Cards |

## Future Enhancements

### Planned Features

1. **Thread Metadata Tracking**
   - Query count per thread
   - Thread creation time
   - Auto-expire threads after N queries or time limit

2. **Smart Follow-Up Suggestions**
   - "💡 Try asking: 'Show their transaction history'"
   - Context-aware suggestions based on query type

3. **Conversation Analytics**
   - Track average conversation length
   - Identify common follow-up patterns
   - Optimize prompts based on usage

4. **Multi-User Thread Management**
   - Separate threads per user in group chats
   - Thread tagging/naming
   - Thread history view

### Potential Improvements

- **Persistent Storage**: Move from in-memory dict to Redis/CosmosDB for multi-instance support
- **Thread Cleanup**: Background job to remove old/inactive threads
- **Export Thread**: Allow users to export conversation history
- **Thread Branching**: Save/restore conversation checkpoints

## Testing

### Manual Test Scenarios

#### Test 1: Basic Follow-Up
```
✅ Query: "Show top 5 customers"
✅ Follow-up: "Tell me about row 3"
✅ Expected: Details for 3rd customer shown
✅ Verify: 💬 badge appears on follow-up
```

#### Test 2: Reset Functionality
```
✅ Query: "Show customers"
✅ Follow-up: "Filter by state"
✅ Command: /reset
✅ Query: "Show loans"
✅ Expected: No reference to previous customers
✅ Verify: No 💬 badge after reset
```

#### Test 3: Multiple References
```
✅ Query: "List accounts"
✅ Follow-up: "Show the top 10"
✅ Follow-up: "What's the total amount?"
✅ Expected: Each follow-up understands previous context
✅ Verify: 💬 badge on all follow-ups
```

#### Test 4: Error with Context
```
✅ Query: "Show customers"
✅ Follow-up: "Foobar xyz123" (invalid)
✅ Expected: Error card with 💬 badge
✅ Verify: Conversation not broken by error
```

## Troubleshooting

### Issue: Follow-up questions not working

**Symptom**: Bot doesn't understand "row 3" or "the third one"

**Check:**
1. Verify `CONVERSATION_THREADS` has entry for conversation
   ```python
   print(f"Thread ID: {CONVERSATION_THREADS.get(conversation_id)}")
   ```
2. Check if thread_id is being passed to `process_nl_query()`
3. Verify thread exists in Azure AI Agents service

**Fix**: Use `/reset` to start fresh, then try again

### Issue: Memory leaks (too many threads)

**Symptom**: Dictionary grows indefinitely

**Solution**: Implement thread cleanup:
```python
# Planned: Auto-cleanup old threads
from datetime import datetime, timedelta

THREAD_METADATA = {
    "thread_abc": {"created": datetime.now(), "last_used": datetime.now()}
}

# Clean threads older than 1 hour
def cleanup_old_threads():
    cutoff = datetime.now() - timedelta(hours=1)
    for conv_id, metadata in list(THREAD_METADATA.items()):
        if metadata["last_used"] < cutoff:
            del CONVERSATION_THREADS[conv_id]
            del THREAD_METADATA[conv_id]
```

### Issue: Conversation badge not appearing

**Check:**
1. `is_conversation` parameter passed to card builder?
2. `thread_id` exists before query execution?

**Debug:**
```python
print(f"Thread ID before query: {thread_id}")
print(f"Is conversation: {thread_id is not None}")
```

## References

- [Azure AI Agents SDK Documentation](https://learn.microsoft.com/azure/ai-services/agents)
- [Adaptive Cards Schema](https://adaptivecards.io/explorer/)
- [Thread Management Best Practices](https://platform.openai.com/docs/assistants/how-it-works/managing-threads-and-messages)

## Changelog

### Version 2.0 (October 11, 2025)
- ✅ Implemented thread-based conversation management
- ✅ Added conversation indicators to Adaptive Cards
- ✅ Added `/reset` command
- ✅ Updated help text with conversation guidance
- ✅ Removed 60+ lines of manual context injection
- ✅ Simplified codebase with native SDK features

### Version 1.0 (October 10, 2025)
- ❌ Manual context injection (deprecated)
- ❌ Dictionary-based result storage (replaced)
- ❌ Brittle "Row 1, Row 2" formatting (removed)

---

**Status**: ✅ Production Ready (Revision 0000020)
**Last Updated**: October 11, 2025
**Maintained By**: Arturo Quiroga
