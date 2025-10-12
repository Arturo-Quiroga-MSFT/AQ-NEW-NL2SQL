# Troubleshooting Log - Azure Container Apps Deployment

## Issues Encountered and Resolved

### Issue 1: Missing Dependencies (microsoft_agents module)
**Error**: `ModuleNotFoundError: No module named 'microsoft_agents'`

**Cause**: Azure Web App didn't install dependencies properly from requirements.txt

**Solution**: Switched from Azure Web Apps to Azure Container Apps
- Created Dockerfile with explicit dependency installation
- Used Azure Container Registry Build for consistent environment

---

### Issue 2: SDK Version Compatibility
**Error**: `TypeError: AIProjectClient.__init__() missing 3 required positional arguments`

**Cause**: Mismatch between SDK API versions (beta 1.0.0b6 vs 1.1.0b4)

**Solution**: 
- Updated `requirements.txt` to use `azure-ai-projects>=1.0.0b12`
- Simplified initialization to use endpoint-based API
- Rebuilt Docker image with updated dependencies

**Code Change**:
```python
# Before (broken with beta SDK)
project_client = AIProjectClient(
    subscription_id=subscription_id,
    resource_group_name=resource_group,
    project_name=project_name,
    credential=DefaultAzureCredential(),
)

# After (works with newer SDK)
project_client = AIProjectClient(
    endpoint=PROJECT_ENDPOINT,
    credential=DefaultAzureCredential(),
)
```

---

### Issue 3: Authentication Failure - DefaultAzureCredential
**Error**: 
```
DefaultAzureCredential failed to retrieve a token from the included credentials.
EnvironmentCredential authentication unavailable. Environment variables are not fully configured.
```

**Cause**: Container didn't have Azure authentication environment variables

**Solution**: Added Azure authentication environment variables to Container App
```bash
az containerapp update \
  --set-env-vars \
    AZURE_TENANT_ID="<YOUR_TENANT_ID_HERE>" \
    AZURE_CLIENT_ID="<YOUR_BOT_ID_HERE>" \
    AZURE_CLIENT_SECRET="<YOUR_CLIENT_SECRET_HERE>"
```

---

### Issue 4: Azure AI Foundry Permission Denied
**Error**: 
```
(PermissionDenied) The principal 'ee822b72-e1f4-41b3-a80e-33bb30ea3e5f' lacks the required data action 
'Microsoft.CognitiveServices/accounts/AIServices/agents/write' to perform 
POST '/api/projects/{projectName}/assistants'
```

**Cause**: Bot's service principal didn't have permissions to create AI agents in Azure AI Foundry

**Solution**: Granted necessary Azure RBAC roles
```bash
# Grant Cognitive Services OpenAI Contributor role
az role assignment create \
  --assignee <YOUR_BOT_ID_HERE> \
  --role "Cognitive Services OpenAI Contributor" \
  --scope /subscriptions/.../Microsoft.CognitiveServices/accounts/aq-ai-foundry-Sweden-Central

# Grant Cognitive Services User role
az role assignment create \
  --assignee <YOUR_BOT_ID_HERE> \
  --role "Cognitive Services User" \
  --scope /subscriptions/.../Microsoft.CognitiveServices/accounts/aq-ai-foundry-Sweden-Central
```

---

## Final Working Configuration

### Environment Variables Set in Container App

**Bot Authentication**:
- `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID`
- `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET`
- `CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID`
- `BOT_ID`
- `BOT_PASSWORD`
- `BOT_TENANT_ID`

**Azure Authentication (for DefaultAzureCredential)**:
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`

**Azure AI Foundry**:
- `PROJECT_ENDPOINT`
- `MODEL_DEPLOYMENT_NAME`
- `AZURE_SUBSCRIPTION_ID`
- `AZURE_AI_RESOURCE_GROUP`
- `AZURE_AI_PROJECT_NAME`

**Azure OpenAI**:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_API_KEY`

**Database**:
- `AZURE_SQL_SERVER`
- `AZURE_SQL_DB`
- `AZURE_SQL_USER`
- `AZURE_SQL_PASSWORD`

### Azure RBAC Roles Assigned

Service Principal: `<YOUR_BOT_ID_HERE>`

Roles on `aq-ai-foundry-Sweden-Central`:
- ✅ **Cognitive Services OpenAI Contributor** - Allows creating/managing AI agents
- ✅ **Cognitive Services User** - Allows using AI services

---

## Key Learnings

1. **Azure Container Apps > Azure Web Apps** for containerized bots
   - Better control over dependencies
   - Clearer error messages
   - Easier troubleshooting with logs

2. **Azure AI SDK Beta Versions** are unstable
   - Use `>=` version constraints to allow updates
   - Endpoint-based initialization is preferred over subscription-based

3. **DefaultAzureCredential Requires Environment Variables** in containers
   - Always set AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET
   - Or use managed identity (more secure for production)

4. **Azure AI Foundry Requires Explicit RBAC**
   - Service principals need both Contributor and User roles
   - Permissions can take 30-60 seconds to propagate

---

## Testing Checklist

- [x] Bot receives messages from Teams
- [x] Bot authenticates to Azure (DefaultAzureCredential)
- [x] Bot can access Azure AI Foundry project
- [x] Bot can create AI agents
- [ ] Bot processes NL query successfully
- [ ] Bot generates SQL query
- [ ] Bot executes SQL against database
- [ ] Bot returns results to Teams

---

## Next Steps

1. **Test the bot** in Teams with: "how many customers do we have"
2. **Monitor logs** for any database connection issues
3. **Document** the complete working solution
4. **Consider** using Azure Key Vault for secrets
5. **Consider** enabling system-assigned managed identity for better security

---

**Status**: 🟡 In Testing  
**Last Updated**: October 10, 2025  
**Deployment**: Azure Container Apps (East US)
