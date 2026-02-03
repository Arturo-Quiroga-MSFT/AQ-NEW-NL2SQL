# Azure Container Apps - Configuration Updates Without Rebuilding

## Overview

This guide explains how to modify configuration settings for the NL2SQL Teams Bot deployed on Azure Container Apps (ACA) **without rebuilding the Docker image**. This approach is ideal for:

- 🔄 Changing AI model deployments (e.g., gpt-4.1 → gpt-5-mini)
- 🔧 Updating database connection strings
- 🔐 Rotating secrets and API keys
- ⚙️ Modifying application settings
- 🚀 Quick configuration changes that don't require code changes

## Key Concepts

### Environment Variables in ACA

Azure Container Apps allows you to set environment variables that override or supplement the variables defined in your Docker image. When you update these variables:

1. **No Docker rebuild required** - The existing image is reused
2. **New revision is created automatically** - ACA creates a new revision with the updated configuration
3. **Zero-downtime deployment** - Traffic is automatically routed to the new revision
4. **Instant rollback capability** - Previous revisions remain available for quick rollback

### When to Use This Approach

✅ **Use environment variable updates for:**
- Model deployment names
- API endpoints and keys
- Database credentials
- Feature flags
- Configuration parameters
- Non-sensitive settings

❌ **Rebuild Docker image when:**
- Code changes are required
- Python dependencies need updates
- Dockerfile modifications needed
- System-level packages must be updated

---

## Step-by-Step Guide

### 1. View Current Environment Variables

First, check what environment variables are currently configured:

```bash
az containerapp show \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --query "properties.template.containers[0].env" \
  --output table
```

Or for JSON output with full details:

```bash
az containerapp show \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --query "properties.template.containers[0].env" \
  -o json
```

### 2. Update Single or Multiple Environment Variables

#### Example: Change AI Model to gpt-5-mini

```bash
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --set-env-vars \
    "MODEL_DEPLOYMENT_NAME=gpt-5-mini" \
    "AZURE_OPENAI_DEPLOYMENT=gpt-5-mini" \
    "AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini"
```

#### Example: Update Database Connection

```bash
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --set-env-vars \
    "AZURE_SQL_SERVER=newserver.database.windows.net" \
    "AZURE_SQL_DB=NewDatabase" \
    "AZURE_SQL_USER=newuser"
```

#### Example: Update API Keys

```bash
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --set-env-vars \
    "AZURE_OPENAI_API_KEY=new-api-key-here"
```

### 3. Verify New Revision Created

After updating, verify a new revision was created and is receiving traffic:

```bash
az containerapp revision list \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --query "[?properties.active].{Name:name, Created:properties.createdTime, Traffic:properties.trafficWeight, Status:properties.healthState}" \
  --output table
```

Expected output:
```
Name                       Created                    Traffic    Status
-------------------------  -------------------------  ---------  --------
nl2sql-teams-bot--0000007  2025-10-10T21:43:48+00:00  0          Healthy
nl2sql-teams-bot--0000008  2025-10-10T21:52:38+00:00  100        Healthy
```

The newest revision should have `Traffic: 100` and `Status: Healthy`.

### 4. Monitor Application Logs

Check the logs to ensure the app started successfully with new configuration:

```bash
az containerapp logs show \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --tail 50 \
  --follow
```

Look for:
- ✅ "NL2SQL Teams Bot Server Starting..."
- ✅ "Model Deployment: gpt-5-mini" (or your new model)
- ✅ No connection errors or startup failures

---

## Common Configuration Updates

### AI Model Updates

Our NL2SQL bot uses three related environment variables for model configuration:

| Variable | Purpose | Example |
|----------|---------|---------|
| `MODEL_DEPLOYMENT_NAME` | Primary model identifier used by the AI agent | `gpt-5-mini` |
| `AZURE_OPENAI_DEPLOYMENT` | Azure OpenAI deployment name | `gpt-5-mini` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Alternative deployment name (for compatibility) | `gpt-5-mini` |

**Update command:**
```bash
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --set-env-vars \
    "MODEL_DEPLOYMENT_NAME=gpt-5-mini" \
    "AZURE_OPENAI_DEPLOYMENT=gpt-5-mini" \
    "AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini"
```

### Database Configuration

| Variable | Purpose | Example |
|----------|---------|---------|
| `AZURE_SQL_SERVER` | SQL Server hostname | `aqsqlserver001.database.windows.net` |
| `AZURE_SQL_DB` | Database name | `TERADATA-FI` |
| `AZURE_SQL_USER` | Database username | `<YOUR_DB_USER>` |
| `AZURE_SQL_PASSWORD` | Database password | `YourSecurePassword` |

### Azure OpenAI Configuration

| Variable | Purpose | Example |
|----------|---------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | `https://aq-ai-foundry-sweden-central.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | API key for authentication | `your-api-key` |
| `AZURE_OPENAI_API_VERSION` | API version to use | `2025-04-01-preview` |

### Bot Framework Configuration

| Variable | Purpose | Example |
|----------|---------|---------|
| `BOT_ID` | Microsoft Bot Framework App ID | `eaeae491-4271-4deb-8d63-fcfeda076760` |
| `BOT_PASSWORD` | Bot client secret | `your-bot-secret` |
| `BOT_TENANT_ID` | Azure AD Tenant ID | `a172a259-b1c7-4944-b2e1-6d551f954711` |

---

## Advanced Scenarios

### Force New Revision Without Config Changes

Sometimes you want to force a restart/new revision even without configuration changes:

```bash
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --set-env-vars "DEPLOYMENT_TIMESTAMP=$(date +%s)"
```

This adds/updates a timestamp variable, forcing ACA to create a new revision.

### Remove an Environment Variable

To remove an environment variable completely:

```bash
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --remove-env-vars "VARIABLE_NAME"
```

### Update Multiple Variables from File

If you have many variables to update, create a script:

```bash
#!/bin/bash
# update-aca-config.sh

az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --set-env-vars \
    "MODEL_DEPLOYMENT_NAME=$MODEL_NAME" \
    "AZURE_SQL_SERVER=$DB_SERVER" \
    "AZURE_SQL_DB=$DB_NAME" \
    "AZURE_OPENAI_API_KEY=$OPENAI_KEY"
```

### Rollback to Previous Revision

If the new configuration causes issues, rollback instantly:

```bash
# List revisions
az containerapp revision list \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --output table

# Activate previous revision
az containerapp revision activate \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --revision nl2sql-teams-bot--0000007
```

---

## Best Practices

### 1. **Document Configuration Changes**
Keep a log of what you changed and when:
```bash
# Good practice: Add comment before update
echo "$(date): Changing model to gpt-5-mini for better performance" >> deployment-log.txt
az containerapp update ...
```

### 2. **Test in Non-Production First**
If you have dev/staging environments, test configuration changes there first.

### 3. **Use Secrets for Sensitive Data**
For highly sensitive values (API keys, passwords), consider using Azure Key Vault references:

```bash
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --secrets "azure-openai-key=keyvaultref:https://your-vault.vault.azure.net/secrets/openai-key,identityref:system"
```

### 4. **Monitor After Updates**
Always check logs after configuration updates:
```bash
az containerapp logs show --name nl2sql-teams-bot --resource-group AQ-BOT-RG --tail 100 --follow
```

### 5. **Keep Local .env in Sync**
Update your local `.env` file to match ACA configuration for consistency:
```bash
# Local .env file
MODEL_DEPLOYMENT_NAME=gpt-5-mini
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
```

---

## Troubleshooting

### Issue: Update Command Doesn't Create New Revision

**Solution:** Add a timestamp variable to force new revision:
```bash
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --set-env-vars "DEPLOYMENT_TIMESTAMP=$(date +%s)"
```

### Issue: New Revision Shows Unhealthy

**Problem:** Configuration error preventing app startup.

**Solution:**
1. Check logs: `az containerapp logs show --name nl2sql-teams-bot --resource-group AQ-BOT-RG --tail 100`
2. Identify the error (missing variable, invalid value, etc.)
3. Fix the configuration or rollback to previous revision

### Issue: Changes Not Taking Effect

**Problem:** Old revision still receiving traffic.

**Solution:**
```bash
# Check traffic distribution
az containerapp revision list --name nl2sql-teams-bot --resource-group AQ-BOT-RG --output table

# If needed, deactivate old revision
az containerapp revision deactivate \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --revision nl2sql-teams-bot--0000007
```

---

## Real-World Example: Model Switch Story

### Context
The NL2SQL Teams Bot was initially deployed with `gpt-4.1` model. After testing, we found `gpt-5-mini` provided better performance for SQL generation tasks.

### What We Did

1. **Identified the configuration variables:**
   ```bash
   az containerapp show \
     --name nl2sql-teams-bot \
     --resource-group AQ-BOT-RG \
     --query "properties.template.containers[0].env" | grep -i model
   ```

2. **Updated to gpt-5-mini:**
   ```bash
   az containerapp update \
     --name nl2sql-teams-bot \
     --resource-group AQ-BOT-RG \
     --set-env-vars \
       "MODEL_DEPLOYMENT_NAME=gpt-5-mini" \
       "AZURE_OPENAI_DEPLOYMENT=gpt-5-mini" \
       "AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5-mini"
   ```

3. **Verified new revision:**
   - New revision `0000008` created automatically
   - 100% traffic routed to new revision
   - Status: Healthy

4. **Tested in Teams:**
   - Query: "how many customers do we have"
   - Result: Worked perfectly with gpt-5-mini
   - Performance: Better response time and accuracy

### Time Saved
- ❌ Docker rebuild + push: ~5-10 minutes
- ✅ Environment variable update: ~30 seconds
- **Total time saved: 9.5 minutes per configuration change!**

---

## Reference Commands

### Quick Reference Table

| Task | Command |
|------|---------|
| View all env vars | `az containerapp show --name <app> --resource-group <rg> --query "properties.template.containers[0].env"` |
| Update env vars | `az containerapp update --name <app> --resource-group <rg> --set-env-vars "VAR=value"` |
| Remove env var | `az containerapp update --name <app> --resource-group <rg> --remove-env-vars "VAR"` |
| List revisions | `az containerapp revision list --name <app> --resource-group <rg>` |
| View logs | `az containerapp logs show --name <app> --resource-group <rg> --tail 100` |
| Rollback revision | `az containerapp revision activate --name <app> --resource-group <rg> --revision <rev-name>` |
| Force new revision | `az containerapp update --name <app> --resource-group <rg> --set-env-vars "DEPLOYMENT_TIMESTAMP=$(date +%s)"` |

---

## Summary

**Key Takeaways:**

1. ✅ **Environment variables can be updated without rebuilding Docker images**
2. ✅ **ACA automatically creates new revisions with updated configuration**
3. ✅ **Zero-downtime deployments** - traffic routes seamlessly to new revision
4. ✅ **Instant rollback** - previous revisions remain available
5. ✅ **Perfect for configuration-only changes** like model switches, API keys, database connections

This approach dramatically speeds up configuration changes and makes your deployment more agile and maintainable!

---

## Related Documentation

- [Azure Container Apps Environment Variables](https://learn.microsoft.com/en-us/azure/container-apps/environment-variables)
- [Azure Container Apps Revisions](https://learn.microsoft.com/en-us/azure/container-apps/revisions)
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Full deployment instructions
- [AZURE_DEPLOYMENT.md](./AZURE_DEPLOYMENT.md) - Azure-specific deployment details
