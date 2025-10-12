#!/bin/bash

# ========================================
# Deploy NL2SQL Teams Bot to Azure Container Apps
# Fill in the environment variables below with your actual values
# ========================================

# Azure Resources
RESOURCE_GROUP="AQ-BOT-RG"
CONTAINER_APP_NAME="nl2sql-teams-bot"
CONTAINER_APP_ENV="nl2sql-env"
ACR_NAME="nl2sqlacr1760120779"
IMAGE_NAME="nl2sql-teams-bot:latest"

# Bot Configuration
BOT_ID="<YOUR_BOT_ID_HERE>"
BOT_PASSWORD="<YOUR_CLIENT_SECRET_HERE>"
BOT_TENANT_ID="<YOUR_TENANT_ID_HERE>"

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT="https://your-instance.openai.azure.com/"
AZURE_OPENAI_DEPLOYMENT="gpt-4o"
AZURE_OPENAI_API_VERSION="2024-08-01-preview"
AZURE_OPENAI_API_KEY="<YOUR_OPENAI_API_KEY_HERE>"

# Database Configuration
DATABASE_SERVER="your-server.database.windows.net"
DATABASE_NAME="your-database-name"
DATABASE_USERNAME="<YOUR_DB_USERNAME>"
DATABASE_PASSWORD="<YOUR_DB_PASSWORD>"

# Get ACR credentials
echo "Getting ACR credentials..."
ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)

# Deploy Container App
echo "Deploying container app..."
az containerapp create \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_APP_ENV \
  --image "$ACR_LOGIN_SERVER/$IMAGE_NAME" \
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
    CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID="$BOT_ID" \
    CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET="$BOT_PASSWORD" \
    CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID="$BOT_TENANT_ID" \
    BOT_ID="$BOT_ID" \
    BOT_PASSWORD="$BOT_PASSWORD" \
    BOT_TENANT_ID="$BOT_TENANT_ID" \
    AZURE_TENANT_ID="$BOT_TENANT_ID" \
    AZURE_CLIENT_ID="$BOT_ID" \
    AZURE_CLIENT_SECRET="$BOT_PASSWORD" \
    AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT" \
    AZURE_OPENAI_DEPLOYMENT="$AZURE_OPENAI_DEPLOYMENT" \
    AZURE_OPENAI_DEPLOYMENT_NAME="$AZURE_OPENAI_DEPLOYMENT" \
    AZURE_OPENAI_API_VERSION="$AZURE_OPENAI_API_VERSION" \
    AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
    PROJECT_ENDPOINT="https://aq-ai-foundry-sweden-central.services.ai.azure.com/api/projects/firstProject" \
    MODEL_DEPLOYMENT_NAME="$AZURE_OPENAI_DEPLOYMENT" \
    AZURE_SQL_SERVER="$DATABASE_SERVER" \
    AZURE_SQL_DB="$DATABASE_NAME" \
    AZURE_SQL_USER="$DATABASE_USERNAME" \
    AZURE_SQL_PASSWORD="$DATABASE_PASSWORD" \
    DATABASE_SERVER="$DATABASE_SERVER" \
    DATABASE_NAME="$DATABASE_NAME" \
    DATABASE_USERNAME="$DATABASE_USERNAME" \
    DATABASE_PASSWORD="$DATABASE_PASSWORD" \
    AZURE_SUBSCRIPTION_ID="7a28b21e-0d3e-4435-a686-d92889d4ee96" \
    AZURE_AI_RESOURCE_GROUP="AI-FOUNDRY-RG" \
    AZURE_AI_PROJECT_NAME="firstProject" \
    PORT="3978" \
    HOST="0.0.0.0"

# Get the app URL
echo ""
echo "Getting app URL..."
APP_URL=$(az containerapp show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Bot Endpoint: https://$APP_URL/api/messages"
echo ""
echo "Next Steps:"
echo "1. Update your Azure Bot registration messaging endpoint:"
echo "   https://$APP_URL/api/messages"
echo ""
echo "2. View logs with:"
echo "   az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""
