# Azure Container Apps Deployment Guide

This guide explains how to deploy the NL2SQL Teams Bot to Azure Container Apps (ACA).

## Why Azure Container Apps?

Azure Container Apps offers several advantages over Azure Web Apps for this bot:

- **Better control**: Full control over the container environment
- **Easier troubleshooting**: Access to container logs and metrics
- **Better scaling**: Automatic scaling based on HTTP traffic
- **Cost-effective**: Pay only for what you use
- **Modern deployment**: Uses Docker containers for consistency

## Prerequisites

1. **Azure CLI** installed and logged in
2. **Docker** installed and running
3. **Azure Bot** registration completed with:
   - Bot ID (Application ID)
   - Bot Password (Client Secret)
   - Tenant ID
4. **Azure OpenAI** deployment with:
   - Endpoint URL
   - Deployment name
   - API key
5. **SQL Database** with connection details

## Deployment Methods

### Method 1: Automated Deployment (Recommended)

Run the deployment script:

```bash
cd nl2sql_azureai_universal
./deploy_to_aca.sh
```

The script will:
1. Create an Azure Container Registry (ACR)
2. Build the Docker image
3. Push the image to ACR
4. Create a Container Apps environment
5. Deploy your bot as a container app
6. Prompt you for environment variables

### Method 2: Manual Deployment

If you prefer more control, follow these steps:

#### Step 1: Create Azure Container Registry

```bash
RESOURCE_GROUP="AQ-BOT-RG"
ACR_NAME="nl2sqlacr"  # Must be globally unique
LOCATION="eastus"

az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true
```

#### Step 2: Build and Push Docker Image

```bash
cd nl2sql_azureai_universal

# Build the image
docker build -t nl2sql-teams-bot:latest .

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

# Tag the image
docker tag nl2sql-teams-bot:latest $ACR_LOGIN_SERVER/nl2sql-teams-bot:latest

# Login to ACR
az acr login --name $ACR_NAME

# Push the image
docker push $ACR_LOGIN_SERVER/nl2sql-teams-bot:latest
```

#### Step 3: Create Container Apps Environment

```bash
CONTAINER_APP_ENV="nl2sql-env"

az containerapp env create \
  --name $CONTAINER_APP_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION
```

#### Step 4: Deploy Container App

```bash
# Get ACR credentials
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)

# Create the container app
az containerapp create \
  --name nl2sql-teams-bot \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_APP_ENV \
  --image $ACR_LOGIN_SERVER/nl2sql-teams-bot:latest \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --target-port 3978 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1.0 \
  --memory 2Gi \
  --env-vars \
    BOT_ID="<your-bot-id>" \
    BOT_PASSWORD="<your-bot-password>" \
    BOT_TENANT_ID="<your-tenant-id>" \
    AZURE_OPENAI_ENDPOINT="<your-openai-endpoint>" \
    AZURE_OPENAI_DEPLOYMENT="<your-deployment-name>" \
    AZURE_OPENAI_API_VERSION="2024-02-15-preview" \
    AZURE_OPENAI_API_KEY="<your-api-key>" \
    DATABASE_SERVER="<your-db-server>" \
    DATABASE_NAME="<your-db-name>" \
    DATABASE_USERNAME="<your-db-username>" \
    DATABASE_PASSWORD="<your-db-password>" \
    PORT="3978"
```

## Post-Deployment

### Get the Bot Endpoint URL

```bash
APP_URL=$(az containerapp show \
  --name nl2sql-teams-bot \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "Bot Endpoint: https://$APP_URL/api/messages"
```

### Update Azure Bot Configuration

1. Go to Azure Portal
2. Navigate to your Bot registration
3. Go to **Configuration** → **Messaging endpoint**
4. Update with: `https://<your-app-url>/api/messages`
5. Click **Apply**

### View Logs

To monitor your bot in real-time:

```bash
az containerapp logs show \
  --name nl2sql-teams-bot \
  --resource-group $RESOURCE_GROUP \
  --follow
```

### Test the Bot

1. Open Microsoft Teams
2. Go to **Apps** → **Built for your org**
3. Find your NL2SQL bot
4. Start a conversation

## Updating the Deployment

When you make code changes:

```bash
cd nl2sql_azureai_universal

# Rebuild the image
docker build -t nl2sql-teams-bot:latest .

# Tag and push
docker tag nl2sql-teams-bot:latest $ACR_LOGIN_SERVER/nl2sql-teams-bot:latest
docker push $ACR_LOGIN_SERVER/nl2sql-teams-bot:latest

# Update the container app
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_LOGIN_SERVER/nl2sql-teams-bot:latest
```

## Troubleshooting

### Check Container Status

```bash
az containerapp show \
  --name nl2sql-teams-bot \
  --resource-group $RESOURCE_GROUP \
  --query properties.runningStatus
```

### View Recent Logs

```bash
az containerapp logs show \
  --name nl2sql-teams-bot \
  --resource-group $RESOURCE_GROUP \
  --tail 100
```

### Check Environment Variables

```bash
az containerapp show \
  --name nl2sql-teams-bot \
  --resource-group $RESOURCE_GROUP \
  --query properties.template.containers[0].env
```

### Restart the Container

```bash
az containerapp revision restart \
  --name nl2sql-teams-bot \
  --resource-group $RESOURCE_GROUP
```

## Cost Optimization

Container Apps charges based on:
- vCPU seconds used
- Memory GB-seconds used
- HTTP requests

To minimize costs:
- Set `--min-replicas 0` to scale to zero when idle
- Reduce `--cpu` and `--memory` if your workload allows
- Use the Basic tier for development/testing

## Security Best Practices

1. **Use Azure Key Vault** for secrets:
   ```bash
   az containerapp secret set \
     --name nl2sql-teams-bot \
     --resource-group $RESOURCE_GROUP \
     --secrets bot-password=<password>
   ```

2. **Enable system-assigned managed identity**:
   ```bash
   az containerapp identity assign \
     --name nl2sql-teams-bot \
     --resource-group $RESOURCE_GROUP \
     --system-assigned
   ```

3. **Restrict network access** using VNet integration

## Additional Resources

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Bot Framework Documentation](https://dev.botframework.com/)
- [Microsoft 365 Agents SDK](https://github.com/microsoft/agents-sdk)
