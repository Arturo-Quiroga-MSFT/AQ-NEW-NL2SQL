# LangChain vs Azure AI Agent Service: Implementation Comparison

This document provides a side-by-side comparison of the two NL2SQL implementations.

## Code Architecture Comparison

### Intent Extraction

#### LangChain Version
```python
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate

# Initialize model
llm = AzureChatOpenAI(...)

# Create prompt template
intent_prompt = ChatPromptTemplate.from_messages([
    ("system", "You extract intent from queries..."),
    ("user", "{query}")
])

# Create chain
intent_chain = intent_prompt | llm

# Execute
result = intent_chain.invoke({"query": query})
intent_entities = result.content
```

#### Azure AI Agent Service Version
```python
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# Initialize client
project_client = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential()
)

# Create agent
agent = project_client.agents.create_agent(
    model=MODEL_DEPLOYMENT_NAME,
    name="intent-extractor",
    instructions="You extract intent from queries..."
)

# Create thread and message
thread = project_client.agents.threads.create()
project_client.agents.messages.create(
    thread_id=thread.id,
    role="user",
    content=query
)

# Run agent
run = project_client.agents.runs.create_and_process(
    thread_id=thread.id,
    agent_id=agent.id
)

# Get response
messages = project_client.agents.messages.list(thread_id=thread.id)
intent_entities = messages[0].text_messages[0].text.value

# Clean up
project_client.agents.delete_agent(agent_id)
```

### SQL Generation

#### LangChain Version
```python
# Create prompt with schema context
sql_prompt = ChatPromptTemplate.from_messages([
    ("system", f"Schema: {schema_context}\nGenerate T-SQL..."),
    ("user", "{intent}")
])

# Create chain
sql_chain = sql_prompt | llm

# Execute
result = sql_chain.invoke({"intent": intent_entities})
raw_sql = result.content
```

#### Azure AI Agent Service Version
```python
# Create SQL generation agent with schema in instructions
agent = project_client.agents.create_agent(
    model=MODEL_DEPLOYMENT_NAME,
    name="sql-generator",
    instructions=f"Schema: {schema_context}\nGenerate T-SQL..."
)

# Create thread and message
thread = project_client.agents.threads.create()
project_client.agents.messages.create(
    thread_id=thread.id,
    role="user",
    content=f"Intent: {intent_entities}\n\nGenerate the SQL query:"
)

# Run agent
run = project_client.agents.runs.create_and_process(
    thread_id=thread.id,
    agent_id=agent_id
)

# Get response
messages = project_client.agents.messages.list(thread_id=thread.id)
raw_sql = messages[0].text_messages[0].text.value

# Clean up
project_client.agents.delete_agent(agent_id)
```

## Key Differences

### 1. Authentication

| Aspect | LangChain | Azure AI Agent Service |
|--------|-----------|------------------------|
| **Method** | API Key | DefaultAzureCredential |
| **Environment Variable** | `AZURE_OPENAI_API_KEY` | None (uses Azure auth) |
| **Security** | Static key | Managed identity / Azure CLI |
| **Best Practice** | ❌ Keys in code/env | ✅ Azure native auth |

### 2. Execution Model

| Aspect | LangChain | Azure AI Agent Service |
|--------|-----------|------------------------|
| **Pattern** | Chain-based | Agent + Thread-based |
| **State Management** | Stateless chains | Stateful threads |
| **Prompt Format** | ChatPromptTemplate | Agent instructions |
| **Response Handling** | `.content` attribute | Message list iteration |

### 3. Dependencies

#### LangChain Version
```
langchain>=0.2.0
langchain-openai>=0.2.0
pydantic>=2.0
python-dotenv
pyodbc
requests
streamlit
pandas
```

#### Azure AI Agent Service Version
```
azure-ai-projects>=1.0.0
azure-identity>=1.19.0
python-dotenv
pyodbc
requests
streamlit
pandas
```

**Difference**: 
- LangChain: 3 LangChain packages + Pydantic
- Azure AI: 2 Azure packages only

### 4. Token Usage Tracking

#### LangChain Version
```python
# Automatic via callback
result = chain.invoke(query)
usage = result.response_metadata.get("token_usage", {})
prompt_tokens = usage.get("prompt_tokens", 0)
completion_tokens = usage.get("completion_tokens", 0)
```

#### Azure AI Agent Service Version
```python
# From run object
run = project_client.agents.runs.create_and_process(...)
if hasattr(run, 'usage') and run.usage:
    prompt_tokens = run.usage.prompt_tokens
    completion_tokens = run.usage.completion_tokens
```

**Similarity**: Both provide automatic token tracking

### 5. Error Handling

#### LangChain Version
```python
try:
    result = chain.invoke(query)
    return result.content
except Exception as e:
    print(f"LangChain error: {e}")
    return ""
```

#### Azure AI Agent Service Version
```python
try:
    run = project_client.agents.runs.create_and_process(...)
    if run.status == "failed":
        print(f"Agent run failed: {run.error}")
        return ""
    return get_response_from_messages(thread_id)
except Exception as e:
    print(f"Azure AI error: {e}")
    return ""
finally:
    # Always clean up agent
    project_client.agents.delete_agent(agent_id)
```

**Difference**: Azure AI requires explicit agent cleanup

## Performance Comparison

### Agent Creation Overhead

| Metric | LangChain | Azure AI Agent Service |
|--------|-----------|------------------------|
| **Model Init** | Once per process | Once per process |
| **Agent Creation** | N/A | Per request (~100-200ms) |
| **Thread Creation** | N/A | Per request (~50-100ms) |
| **Total Overhead** | ~0ms | ~150-300ms |

**Recommendation**: For production, Azure AI agents should be created once and reused, not created per request.

### Optimization Strategy

#### Current Implementation (per-request agents)
```python
def extract_intent(query):
    agent_id = _create_intent_agent()  # Creates agent
    try:
        # Use agent
        return result
    finally:
        project_client.agents.delete_agent(agent_id)  # Deletes agent
```

**Pros**: Clean, no state management
**Cons**: Higher latency (agent creation overhead)

#### Optimized Implementation (persistent agents)
```python
# Module-level agent creation
INTENT_AGENT_ID = None
SQL_AGENT_ID = None

def get_or_create_intent_agent():
    global INTENT_AGENT_ID
    if INTENT_AGENT_ID is None:
        agent = project_client.agents.create_agent(...)
        INTENT_AGENT_ID = agent.id
    return INTENT_AGENT_ID

def extract_intent(query):
    agent_id = get_or_create_intent_agent()  # Reuses agent
    # Use agent (no deletion)
    return result
```

**Pros**: Lower latency, efficient resource use
**Cons**: Agent lifecycle management needed

## Feature Comparison

| Feature | LangChain | Azure AI Agent Service |
|---------|-----------|------------------------|
| **Prompt Templates** | ✅ Rich templating | ⚠️ Instructions only |
| **Chain Composition** | ✅ Complex chains | ❌ Not applicable |
| **Conversation Memory** | ✅ Various memory types | ✅ Thread-based |
| **Function Calling** | ✅ Via tools | ✅ Native function tools |
| **Streaming** | ✅ Token-level streaming | ✅ Event-based streaming |
| **Observability** | ⚠️ Custom callbacks | ✅ Built-in Azure tracing |
| **Multi-Agent** | ✅ Via LangGraph | ✅ Connected agents |
| **Document Search** | ✅ Via vectorstores | ✅ File search tool |
| **Code Execution** | ⚠️ Via custom tools | ✅ Code interpreter tool |

## Cost Comparison

**Both implementations have identical token usage costs** since they use the same underlying Azure OpenAI model.

The difference is in infrastructure:

### LangChain Version
- **Runtime Cost**: Compute only (App Service, Container Apps, etc.)
- **No Additional Services**: Direct API calls to Azure OpenAI

### Azure AI Agent Service Version
- **Runtime Cost**: Compute only
- **Azure AI Foundry**: No additional cost for Agent Service
- **Optional Services**: Application Insights, Tracing (small additional cost)

**Bottom Line**: Cost is essentially the same, but Azure AI provides better observability out-of-the-box.

## When to Use Each

### Use LangChain When:

1. **Framework Flexibility**: You need to integrate with other LLM providers (OpenAI, Anthropic, etc.)
2. **Rich Ecosystem**: You want to leverage LangChain's extensive toolkit (vectorstores, document loaders, etc.)
3. **Complex Chains**: You need sophisticated chain composition (LangGraph, ReAct agents, etc.)
4. **Existing Investment**: Your team already knows LangChain
5. **Rapid Prototyping**: You want quick iteration with familiar tools

### Use Azure AI Agent Service When:

1. **Azure Native**: You're fully committed to Azure ecosystem
2. **Enterprise Security**: You need DefaultAzureCredential and managed identity
3. **Built-in Observability**: You want Azure AI Foundry tracing and monitoring
4. **Simplified Stack**: You prefer fewer dependencies
5. **Agent Persistence**: You need long-running, stateful agents
6. **Multi-Agent Systems**: You're building connected agent architectures
7. **Production Azure Workloads**: You're deploying to Azure services

## Migration Path

### From LangChain to Azure AI Agent Service

1. **Replace authentication**:
   ```python
   # Before: API key
   llm = AzureChatOpenAI(api_key=API_KEY, ...)
   
   # After: DefaultAzureCredential
   client = AIProjectClient(credential=DefaultAzureCredential(), ...)
   ```

2. **Convert prompts to agent instructions**:
   ```python
   # Before: ChatPromptTemplate
   prompt = ChatPromptTemplate.from_messages([...])
   
   # After: agent instructions
   agent = client.agents.create_agent(instructions="...")
   ```

3. **Replace chain execution with agent runs**:
   ```python
   # Before: chain.invoke()
   result = chain.invoke({"query": query})
   
   # After: agent run
   thread = client.agents.threads.create()
   client.agents.messages.create(thread_id=thread.id, content=query)
   run = client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent_id)
   ```

4. **Update response handling**:
   ```python
   # Before: result.content
   response = result.content
   
   # After: message list
   messages = client.agents.messages.list(thread_id=thread.id)
   response = messages[0].text_messages[0].text.value
   ```

### From Azure AI Agent Service to LangChain

1. **Add API key authentication**
2. **Convert agent instructions to prompt templates**
3. **Remove thread management**
4. **Replace agent runs with chain invocations**
5. **Install LangChain packages**

## Testing Both Implementations

### Run LangChain Version
```bash
cd nl2sql_standalone_Langchain
source ../.venv/bin/activate
python nl2sql_main.py --query "How many customers?"
```

### Run Azure AI Agent Service Version
```bash
cd nl2sql_standalone_AzureAI
source ../.venv/bin/activate
az login  # Authenticate with Azure
python nl2sql_main.py --query "How many customers?"
```

## Conclusion

Both implementations provide the same NL→SQL capabilities with different architectural approaches:

- **LangChain**: Framework-agnostic, rich ecosystem, flexible chains
- **Azure AI Agent Service**: Azure-native, enterprise auth, built-in observability

The choice depends on your:
- **Cloud strategy** (multi-cloud vs. Azure-first)
- **Security requirements** (API keys vs. managed identity)
- **Team expertise** (LangChain familiarity vs. Azure expertise)
- **Future roadmap** (framework flexibility vs. Azure integration)

Both are production-ready and maintained in this repository for different use cases.
