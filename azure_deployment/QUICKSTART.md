# 🚀 Quick Start: Deploy to Azure Container Apps

Get your NL2SQL Multi-Model app running in Azure in under 10 minutes!

## Prerequisites

- ✅ Azure subscription with Contributor access
- ✅ [Azure CLI](https://aka.ms/InstallAzureCLI) installed
- ✅ Your Azure OpenAI and SQL Database credentials ready

## 3-Step Deployment

### Step 1: Login to Azure

```bash
az login
```

### Step 2: Configure Environment

```bash
# Copy the template
cp .env.template .env.azure

# Edit with your credentials
nano .env.azure  # or use your favorite editor
```

**Required values to update in `.env.azure`:**
- `AZURE_OPENAI_API_KEY` - Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Your endpoint URL
- `AZURE_SQL_SERVER` - Your SQL server hostname
- `AZURE_SQL_DB` - Your database name
- `AZURE_SQL_USER` - Your SQL username
- `AZURE_SQL_PASSWORD` - Your SQL password
- `RESOURCE_GROUP` - Choose a name (e.g., `rg-nl2sql-app`)
- `LOCATION` - Azure region (e.g., `eastus`, `westus2`)
- `ACR_NAME` - Choose unique name (e.g., `nl2sqlacr12345`)

### Step 3: Deploy!

```bash
./deploy.sh
```

That's it! ✨

## What Gets Deployed?

The script automatically creates:

1. **Resource Group** - Container for all resources
2. **Azure Container Registry** - Stores your Docker images
3. **User-Assigned Managed Identity** - Secure authentication
4. **Log Analytics Workspace** - Application monitoring
5. **Container Apps Environment** - Isolated network boundary
6. **Container App** - Your running NL2SQL application

## After Deployment

The script will display your app URL:

```
🎉 Deployment Complete!

🌐 Application URL: https://nl2sql-app-xxx.azurecontainerapps.io
```

Visit the URL to start using your app!

## Useful Commands

### View logs
```bash
az containerapp logs show \
  --name nl2sql-multimodel-app \
  --resource-group rg-nl2sql-app \
  --follow
```

### Update app with new code
```bash
# Make your code changes, then:
./deploy.sh --skip-infra
```

### Preview changes before deploying
```bash
./deploy.sh --preview
```

### Scale the app
```bash
az containerapp update \
  --name nl2sql-multimodel-app \
  --resource-group rg-nl2sql-app \
  --min-replicas 2 \
  --max-replicas 5
```

## Troubleshooting

### "Image not found" error
The first deployment might take 5-10 minutes to build the Docker image. Wait for the ACR build to complete.

### "Container app won't start"
Check the logs:
```bash
az containerapp logs show --name nl2sql-multimodel-app --resource-group rg-nl2sql-app --tail 100
```

### Environment variables not working
Make sure your `.env.azure` file has all required values and re-run the deployment.

## Cost Estimate

**Monthly cost** (approximate):
- Container Apps: $15-30 (1-2 replicas, 1 vCPU, 2GB RAM)
- Container Registry: $5 (Basic tier)
- Log Analytics: $2-5 (based on logs volume)
- **Total: ~$22-40/month**

*Note: Azure OpenAI costs are based on usage and not included above.*

## Next Steps

- 📖 Read the full [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for advanced options
- 🔐 Set up [Azure Key Vault](DEPLOYMENT_GUIDE.md#use-azure-key-vault-for-secrets) for secrets
- 📊 Enable [Application Insights](DEPLOYMENT_GUIDE.md#enable-application-insights) for monitoring
- 🔄 Configure [CI/CD with GitHub Actions](DEPLOYMENT_GUIDE.md#github-actions-workflow)

## Need Help?

- Full documentation: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- Azure Container Apps docs: https://learn.microsoft.com/azure/container-apps/
- Azure CLI reference: https://learn.microsoft.com/cli/azure/

---

**Happy deploying! 🎉**
