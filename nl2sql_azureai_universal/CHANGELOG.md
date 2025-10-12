# Changelog

All notable changes to the NL2SQL Teams Bot project.

## [2.1.0] - 2024-01-XX - Business Insights Agent ⭐ NEW

### 🎉 Major Features

#### Three-Agent Architecture
- **Third Agent Added**: Data Insights Agent analyzes query results and provides business intelligence
- **Intelligence Layer**: Mimics original Streamlit UI with dedicated insights generation
- **Emoji Indicators**: Visual system for quick comprehension (📊📈📉⚠️✅💡🎯🔍)
- **Business Focus**: Actionable insights, not technical details

#### Insights Features
- **Automatic Analysis**: Every successful query gets 3-5 business insights
- **Context-Aware**: Considers original question, SQL executed, and results
- **Concise Output**: One-sentence insights with visual indicators
- **Non-Blocking**: Insights failures don't break main query execution

### 📝 Code Changes

#### Modified Files

**nl2sql_main.py**
- `_get_or_create_insights_agent()`: NEW - Creates persistent insights agent
- `generate_insights()`: NEW - Generates business insights from query results
- `process_nl_query()`: Integrated insights generation after SQL execution

**adaptive_cards.py**
- `create_success_card()`: Added `insights` parameter
- Added insights container with "💡 Business Insights" header
- Insights display between results table and metadata footer

**teams_nl2sql_agent.py**
- Updated card creation to pass `insights` from pipeline results

#### New Files

**INSIGHTS_FEATURE.md**
- Complete documentation of insights agent
- Emoji indicator reference
- Implementation details and examples
- Testing recommendations and troubleshooting

### 🎯 Agent System

1. **Intent Agent**: Natural language → Structured intent JSON
2. **SQL Agent**: Intent + Schema → Executable SQL
3. **Insights Agent**: Results + Context → Business insights ⭐ NEW

### 📊 Example Output

```
Query: "Show top 10 customers by revenue"

Results: [10 rows displayed]

💡 Business Insights:
📊 Top 10 customers generated $4.2M (38% of total)
📈 Average revenue per customer: $420K
🎯 Revenue concentrated in top 3 customers
⚠️ 2 customers showing declining trends
💡 Consider diversification strategy
```

### 🔧 Technical Details

- **Dedicated Threads**: Each insights generation uses separate thread
- **Token Usage**: +500-1000 tokens per query (~25-35% increase)
- **Response Time**: +1-2 seconds for insights generation
- **Error Handling**: Graceful fallback if insights fail

### 🚀 Deployment

- **Revision 0000021**: Business insights agent implementation

---

## [2.0.0] - October 11, 2025 - Thread-Based Conversations

### 🎉 Major Features

#### Native Conversation Management
- **Thread-Based Architecture**: Replaced manual context injection with Azure AI Agents' native thread management
- **Natural Follow-Ups**: Users can ask "tell me about row 3" without repeating data
- **Conversation Continuity**: AI maintains full conversation context across queries

#### Visual Enhancements
- **Conversation Indicators**: Added "💬 Conversation Active" badge to Adaptive Cards
- **Context Awareness**: Cards show when AI is using conversation history
- **Smart Detection**: Badge automatically appears/disappears based on thread state

#### Commands
- **`/reset`**: Clear conversation history and start fresh
- **`/help`**: Updated with conversation management guidance
- **`/about`**: Information about the bot

### 📝 Code Changes

#### Modified Files

**nl2sql_main.py**
- `extract_intent()`: Added `thread_id` parameter, returns `(intent, thread_id)` tuple
- `generate_sql()`: Added `thread_id` parameter, returns `(sql, thread_id)` tuple  
- `process_nl_query()`: Added `thread_id` parameter, returns thread_id in response dict

**teams_nl2sql_agent.py**
- Replaced `CONVERSATION_HISTORY` dict with `CONVERSATION_THREADS` dict
- Removed ~60 lines of manual context injection code
- Added thread management in `on_message()` handler
- Added `/reset` command handler
- Updated `/help` with conversation features

**adaptive_cards.py**
- `create_success_card()`: Added `is_conversation` parameter
- `create_error_card()`: Added `is_conversation` parameter
- Added conversation badge UI component to both card types

#### New Files

**CONVERSATION_MANAGEMENT.md**
- Complete documentation of thread-based architecture
- User guide with example conversations
- Technical implementation details
- Troubleshooting guide

**CHANGELOG.md** (this file)
- Version history and release notes

### 🗑️ Removed

- Manual context injection logic (~60 lines)
- "Row 1, Row 2" formatting code
- Brittle string concatenation for conversation context
- Complex conversation state management

### 🔧 Technical Improvements

- **Cleaner Code**: Reduced complexity by using SDK features properly
- **Better AI Understanding**: Native threads > manual data injection
- **Scalable**: Azure manages thread state, not manual dictionaries
- **Maintainable**: 3 lines of thread management vs 60+ lines of manual code

### 📊 Performance

- **Token Efficiency**: AI doesn't process redundant context strings
- **Response Quality**: Better understanding of follow-up questions
- **Error Reduction**: No more "Incorrect syntax near 'row'" errors

### 🚀 Deployment

- **Revision 0000019**: Thread-based conversation implementation
- **Revision 0000020**: Conversation indicators in Adaptive Cards

---

## [1.0.0] - October 10, 2025 - Initial Release

### Features

- Natural Language to SQL query generation
- Azure AI Agents integration
- Adaptive Cards UI
- Intent extraction + SQL generation pipeline
- Schema-agnostic database support
- Dynamic schema discovery
- SQL sanitization and validation
- Result formatting and display

### Components

- Teams bot with M365 Agents SDK
- Azure AI Foundry Agent Service
- Azure SQL Database connectivity
- Full-width Adaptive Cards
- Error handling and suggestions

### Known Limitations

- No conversation history (each query independent)
- Manual result caching attempted but brittle
- Follow-up questions required explicit context

---

## Migration Guide: v1.0 → v2.0

### For Users

**Before (v1.0):**
```
You: "Show top 5 customers"
Bot: [Shows 5 customers]

You: "Tell me about CUST00058"  ← Must specify customer ID explicitly
Bot: [Shows customer details]
```

**After (v2.0):**
```
You: "Show top 5 customers"
Bot: [Shows 5 customers]

You: "Tell me about the third one"  ← Natural reference!
Bot: [Shows customer details] 💬
```

### For Developers

**Before (v1.0):**
```python
# Manual context injection
conversation_data = CONVERSATION_HISTORY.get(conversation_id, {})
last_results = conversation_data.get("last_results")
context_info = f"Previous results: {format_results(last_results)}"
enhanced_query = context_info + user_query

result = process_nl_query(enhanced_query)  # No thread_id
```

**After (v2.0):**
```python
# Thread-based conversation
thread_id = CONVERSATION_THREADS.get(conversation_id)
result = process_nl_query(user_query, thread_id=thread_id)
CONVERSATION_THREADS[conversation_id] = result["thread_id"]
```

### API Changes

**`process_nl_query()`**
```python
# v1.0
def process_nl_query(query: str, execute: bool = True) -> Dict[str, Any]

# v2.0
def process_nl_query(
    query: str, 
    execute: bool = True, 
    thread_id: Optional[str] = None  # NEW
) -> Dict[str, Any]
```

**Response Changes**
```python
# v1.0 response
{
    "intent": "...",
    "sql": "...",
    "results": {...},
    "token_usage": {...},
    "elapsed_time": 1.23
}

# v2.0 response (added thread_id)
{
    "intent": "...",
    "sql": "...",
    "results": {...},
    "token_usage": {...},
    "elapsed_time": 1.23,
    "thread_id": "thread_abc123"  # NEW
}
```

### Backward Compatibility

✅ **Fully backward compatible** - If `thread_id` not provided, functions create new thread automatically.

```python
# v1.0 style calls still work
result = process_nl_query("Show customers")  

# v2.0 style enables conversations
result = process_nl_query("Show customers", thread_id=existing_thread)
```

---

## Roadmap

### v2.1 (Planned)
- [ ] Thread metadata tracking (query count, age)
- [ ] Auto-expire old threads (TTL)
- [ ] Conversation analytics dashboard
- [ ] Export conversation history

### v2.2 (Planned)
- [ ] Smart follow-up suggestions
- [ ] "💡 Try asking..." context-aware prompts
- [ ] Query templates based on conversation patterns

### v3.0 (Future)
- [ ] Multi-user thread management
- [ ] Thread branching/checkpoints
- [ ] Persistent storage (Redis/CosmosDB)
- [ ] Thread sharing between users

---

## Contributors

- Arturo Quiroga (@Arturo-Quiroga-MSFT)

## License

Internal Microsoft Project
