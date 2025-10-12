# Redis Integration Guide for NL2SQL Teams Bot

## Step 1: Create Azure Cache for Redis

```bash
# Set variables
RESOURCE_GROUP="AQ-BOT-RG"
REDIS_NAME="nl2sql-redis-cache"
LOCATION="eastus"

# Create Redis Cache (Basic C0 - 250MB, good for testing)
az redis create \
  --name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Basic \
  --vm-size C0

# Get connection details
az redis show \
  --name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "{hostname:hostName,sslPort:sslPort}" \
  --output table

# Get access keys
az redis list-keys \
  --name $REDIS_NAME \
  --resource-group $RESOURCE_GROUP \
  --query primaryKey \
  --output tsv
```

## Step 2: Update requirements.txt

Add to `/nl2sql_azureai_universal/requirements.txt`:
```
redis>=5.0.0
```

## Step 3: Update Container App Environment Variables

```bash
# Set Redis configuration
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --set-env-vars \
    "REDIS_HOST=nl2sql-redis-cache.redis.cache.windows.net" \
    "REDIS_PORT=6380" \
    "REDIS_PASSWORD=<YOUR_REDIS_KEY>" \
    "REDIS_SSL=true" \
    "REDIS_TTL_DAYS=7"
```

Or store password in Key Vault (recommended):
```bash
# Create Key Vault secret
az keyvault secret set \
  --vault-name <your-keyvault> \
  --name "redis-password" \
  --value "<YOUR_REDIS_KEY>"

# Update Container App to use secret reference
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --set-env-vars \
    "REDIS_HOST=nl2sql-redis-cache.redis.cache.windows.net" \
    "REDIS_PORT=6380" \
    "REDIS_PASSWORD=secretref:redis-password" \
    "REDIS_SSL=true"
```

## Step 4: Update teams_nl2sql_agent.py

Replace the simple dictionary with Redis store:

```python
# In the imports section, add:
from conversation_store import RedisConversationStore

# Replace CONVERSATION_HISTORY = {} with:
CONVERSATION_STORE = RedisConversationStore(
    use_fallback=True  # Falls back to in-memory if Redis unavailable
)

# In on_message(), replace:
conversation_data = CONVERSATION_HISTORY.get(conversation_id, {})
# With:
conversation_data = CONVERSATION_STORE.get_history(conversation_id)

# Replace:
CONVERSATION_HISTORY[conversation_id] = {...}
# With:
CONVERSATION_STORE.save_history(
    conversation_id=conversation_id,
    last_query=user_query,
    last_sql=result.get("sql", ""),
    last_results=result.get("results", {})
)
```

## Step 5: Add Health Check Endpoint (Optional)

Add to teams_nl2sql_agent.py:

```python
@AGENT_APP.activity("healthcheck")
async def on_healthcheck(context: TurnContext, state: TurnState):
    """Health check endpoint."""
    redis_health = CONVERSATION_STORE.health_check()
    
    health_status = {
        "status": "healthy",
        "redis": redis_health
    }
    
    await context.send_activity(MessageFactory.text(
        f"Health: {json.dumps(health_status, indent=2)}"
    ))
```

## Benefits of Redis vs In-Memory Dict

| Feature | In-Memory Dict | Redis |
|---------|---------------|-------|
| Persists across restarts | ❌ No | ✅ Yes |
| Multi-instance support | ❌ No | ✅ Yes |
| Automatic expiration | ❌ No | ✅ Yes (TTL) |
| Memory limit | Container limit | Configurable |
| Production ready | ❌ No | ✅ Yes |

## Cost Estimate

- **Basic C0 (250MB)**: ~$16/month - Good for testing
- **Standard C1 (1GB)**: ~$55/month - Better for production
- **Premium P1 (6GB)**: ~$200/month - High availability + clustering

## Testing Locally

```bash
# Run Redis locally with Docker
docker run -d -p 6379:6379 redis:latest

# Set local environment variables
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_PASSWORD=""
export REDIS_SSL=false

# Run your bot
python start_server.py
```
