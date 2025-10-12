# Azure Container Apps Deployment - Next Steps

## ✅ Completed Steps

1. **Created Dockerfile** - Multi-stage Docker image with all dependencies including microsoft-agents SDK
2. **Created Azure Container Registry** - `nl2sqlacr1760120779.azurecr.io`
3. **Built and Pushed Docker Image** - Image successfully built in ACR and ready for deployment
4. **Created Container Apps Environment** - `nl2sql-env` in AQ-BOT-RG resource group

## 📋 Next Steps

### Step 1: Edit the Deployment Script

Open the file `deploy_aca_command.sh` and fill in your credentials:

```bash
# Bot Configuration
BOT_ID="YOUR_BOT_ID_HERE"                    # From Azure Bot registration
BOT_PASSWORD="YOUR_BOT_PASSWORD_HERE"        # From Azure Bot registration
BOT_TENANT_ID="YOUR_TENANT_ID_HERE"          # Your Azure AD Tenant ID

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT="YOUR_OPENAI_ENDPOINT_HERE"      # e.g., https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT="YOUR_DEPLOYMENT_NAME_HERE"    # e.g., gpt-4o
AZURE_OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE"

# Database Configuration
DATABASE_SERVER="YOUR_DB_SERVER_HERE"        # e.g., your-server.database.windows.net
DATABASE_NAME="YOUR_DB_NAME_HERE"
DATABASE_USERNAME="YOUR_DB_USERNAME_HERE"
DATABASE_PASSWORD="YOUR_DB_PASSWORD_HERE"
```

### Step 2: Run the Deployment Script

```bash
cd /Users/arturoquiroga/GITHUB/AQ-NEW-NL2SQL/nl2sql_azureai_universal
./deploy_aca_command.sh
```

### Step 3: Update Azure Bot Configuration

After deployment completes, you'll get a bot endpoint URL. Update your Azure Bot registration:

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to your Bot registration (in AQ-BOT-RG resource group)
3. Go to **Configuration** → **Messaging endpoint**
4. Update with the URL from the deployment output
5. Click **Apply**

### Step 4: Test the Bot

1. Open Microsoft Teams
2. Go to **Apps** → **Built for your org**
3. Find your NL2SQL bot
4. Start a conversation
5. Try asking: "How many customers do we have?"

## 🔍 Monitoring and Troubleshooting

### View Logs in Real-Time

```bash
az containerapp logs show \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --follow
```

### Check Container Status

```bash
az containerapp show \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --query properties.runningStatus
```

### View Recent Logs

```bash
az containerapp logs show \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --tail 100
```

### Restart the Container

```bash
az containerapp revision restart \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG
```

## 🔄 Updating Your Deployment

When you make code changes:

1. **Rebuild the image in ACR:**
   ```bash
   cd nl2sql_azureai_universal
   az acr build --registry nl2sqlacr1760120779 --image nl2sql-teams-bot:latest .
   ```

2. **Update the container app:**
   ```bash
   az containerapp update \
     --name nl2sql-teams-bot \
     --resource-group AQ-BOT-RG \
     --image nl2sqlacr1760120779.azurecr.io/nl2sql-teams-bot:latest
   ```

## 📊 Resources Created

| Resource | Name | Type | Purpose |
|----------|------|------|---------|
| Resource Group | AQ-BOT-RG | Resource Group | Container for all resources |
| Container Registry | nl2sqlacr1760120779 | ACR | Stores Docker image |
| Container App Environment | nl2sql-env | ACA Environment | Hosting environment |
| Container App | nl2sql-teams-bot | Container App | Your bot application |
| Log Analytics Workspace | workspace-B15f | Log Analytics | Logs and monitoring |

## 💰 Cost Considerations

Azure Container Apps pricing is based on:
- **vCPU-seconds**: $0.000024/vCPU-second
- **Memory GB-seconds**: $0.000003/GB-second
- **Requests**: First 2 million/month free

With current configuration (1 vCPU, 2 GB RAM, 1 replica):
- **Idle cost**: ~$5-10/day
- **Under load**: Variable based on usage

To reduce costs:
- Set `--min-replicas 0` to scale to zero when idle
- Reduce `--cpu` and `--memory` if workload allows

## 🔒 Security Best Practices

Consider implementing these security enhancements:

1. **Use Azure Key Vault for secrets:**
   ```bash
   az containerapp secret set \
     --name nl2sql-teams-bot \
     --resource-group AQ-BOT-RG \
     --secrets bot-password=<password>
   ```

2. **Enable managed identity:**
   ```bash
   az containerapp identity assign \
     --name nl2sql-teams-bot \
     --resource-group AQ-BOT-RG \
     --system-assigned
   ```

3. **Use VNet integration** for private database access

## 📚 Additional Resources

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Bot Framework Documentation](https://dev.botframework.com/)
- [Microsoft 365 Agents SDK](https://github.com/microsoft/agents-sdk)
- [Deployment Guide](./CONTAINER_APPS_DEPLOYMENT.md)

## ❓ Common Issues

### Issue: Bot not responding in Teams
**Solution**: Check that the messaging endpoint is updated in Azure Bot configuration

### Issue: Container fails to start
**Solution**: Check logs with `az containerapp logs show` and verify environment variables

### Issue: Database connection errors
**Solution**: Verify database server allows connections from Azure and credentials are correct

### Issue: "microsoft_agents module not found"
**Solution**: This has been fixed in the Dockerfile - rebuild image if you see this error

---

**Status**: Ready for final deployment after credentials are added to `deploy_aca_command.sh`
