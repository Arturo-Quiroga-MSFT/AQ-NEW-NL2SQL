# Deploying NL2SQL Multi-Model App to Azure Container Apps

This guide walks you through deploying the multi-model NL2SQL Streamlit application to Azure Container Apps, making it accessible to others via a public URL.

## 🎯 What You'll Deploy

- **Container App**: Running the Streamlit multi-model UI (`app_multimodel.py`)
- **Container Apps Environment**: Isolated environment for your app
- **Azure Container Registry (ACR)**: Stores your Docker container images
- **Managed Identity**: Secure authentication without storing credentials
- **Key Vault** (optional): For secure secrets management

## 📋 Prerequisites

1. **Azure Subscription**: Active subscription with appropriate permissions
2. **Azure CLI**: Installed and configured ([Install Guide](https://learn.microsoft.com/cli/azure/install-azure-cli))
3. **Docker**: Installed locally (optional, for local testing)
4. **Environment Variables**: All required Azure OpenAI and SQL credentials

### Required Permissions

You need the following roles:
- **Contributor** role on the resource group
- **Managed Identity Contributor** for creating managed identities
- **AcrPull** for pulling images from ACR

## 🚀 Quick Start Deployment

### Option 1: Automated Deployment (Recommended)

```bash
# 1. Clone and navigate to the project
cd /path/to/AQ-NEW-NL2SQL

# 2. Copy and configure environment template
cp .env.template .env.azure
# Edit .env.azure with your Azure credentials

# 3. Run the deployment script
chmod +x deploy.sh
./deploy.sh
```

### Option 2: Manual Step-by-Step Deployment

Follow the detailed steps below for full control over the deployment process.

---

## 📝 Detailed Step-by-Step Deployment

### Step 1: Set Up Azure CLI and Login

```bash
# Login to Azure
az login

# Set your subscription (if you have multiple)
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Verify your account
az account show
```

### Step 2: Define Variables

```bash
# Resource naming (customize these)
export RESOURCE_GROUP="rg-nl2sql-app"
export LOCATION="eastus"
export ACR_NAME="nl2sqlacr$(date +%s)"  # Unique name
export CONTAINER_APP_ENV="nl2sql-env"
export CONTAINER_APP_NAME="nl2sql-multimodel-app"
export USER_IDENTITY_NAME="nl2sql-identity"

# Image configuration
export IMAGE_NAME="nl2sql-multimodel"
export IMAGE_TAG="latest"
```

### Step 3: Create Resource Group

```bash
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### Step 4: Create Azure Container Registry

```bash
# Create ACR
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled false

# Enable ACR for Container Apps (requires managed identity)
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --query loginServer -o tsv)
echo "ACR Login Server: $ACR_LOGIN_SERVER"
```

### Step 5: Build and Push Docker Image to ACR

```bash
# Navigate to project root
cd /path/to/AQ-NEW-NL2SQL

# Build image directly in ACR (no local Docker needed!)
az acr build \
  --registry $ACR_NAME \
  --image $IMAGE_NAME:$IMAGE_TAG \
  --file Dockerfile.multimodel \
  .

# Verify image was pushed
az acr repository list --name $ACR_NAME --output table
az acr repository show-tags --name $ACR_NAME --repository $IMAGE_NAME --output table
```

### Step 6: Create User-Assigned Managed Identity

```bash
# Create managed identity
az identity create \
  --resource-group $RESOURCE_GROUP \
  --name $USER_IDENTITY_NAME

# Get identity details
IDENTITY_CLIENT_ID=$(az identity show \
  --resource-group $RESOURCE_GROUP \
  --name $USER_IDENTITY_NAME \
  --query clientId -o tsv)

IDENTITY_ID=$(az identity show \
  --resource-group $RESOURCE_GROUP \
  --name $USER_IDENTITY_NAME \
  --query id -o tsv)

IDENTITY_PRINCIPAL_ID=$(az identity show \
  --resource-group $RESOURCE_GROUP \
  --name $USER_IDENTITY_NAME \
  --query principalId -o tsv)

echo "Identity Client ID: $IDENTITY_CLIENT_ID"
echo "Identity Resource ID: $IDENTITY_ID"
echo "Identity Principal ID: $IDENTITY_PRINCIPAL_ID"
```

### Step 7: Grant Managed Identity Access to ACR

```bash
# Get ACR resource ID
ACR_ID=$(az acr show --name $ACR_NAME --query id -o tsv)

# Grant AcrPull role to managed identity
az role assignment create \
  --assignee $IDENTITY_PRINCIPAL_ID \
  --role AcrPull \
  --scope $ACR_ID

echo "✅ Managed identity can now pull images from ACR"
```

### Step 8: Create Container Apps Environment

```bash
# Create environment
az containerapp env create \
  --name $CONTAINER_APP_ENV \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

echo "✅ Container Apps environment created"
```

### Step 9: Create Container App with Environment Variables

Create a file `env-vars.yaml` with your secrets:

```yaml
# env-vars.yaml
- name: AZURE_OPENAI_API_KEY
  value: "your-azure-openai-key"
- name: AZURE_OPENAI_ENDPOINT
  value: "https://your-endpoint.openai.azure.com/"
- name: AZURE_OPENAI_API_VERSION
  value: "2025-04-01-preview"
- name: AZURE_SQL_SERVER
  value: "your-server.database.windows.net"
- name: AZURE_SQL_DB
  value: "your-database"
- name: AZURE_SQL_USER
  value: "your-username"
- name: AZURE_SQL_PASSWORD
  secretRef: sql-password
```

Create secrets file `secrets.yaml`:

```yaml
# secrets.yaml
- name: sql-password
  value: "your-sql-password"
```

Deploy the container app:

```bash
az containerapp create \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_APP_ENV \
  --image $ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG \
  --target-port 8501 \
  --ingress external \
  --registry-server $ACR_LOGIN_SERVER \
  --user-assigned $IDENTITY_ID \
  --registry-identity $IDENTITY_ID \
  --cpu 1.0 \
  --memory 2.0Gi \
  --min-replicas 1 \
  --max-replicas 3 \
  --env-vars-file env-vars.yaml \
  --secrets-file secrets.yaml

echo "✅ Container app deployed!"
```

### Step 10: Get Application URL

```bash
# Get the app URL
APP_URL=$(az containerapp show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.configuration.ingress.fqdn -o tsv)

echo "🎉 Your app is live at: https://$APP_URL"
```

---

## 🔧 Using Bicep for Infrastructure as Code

For a more maintainable deployment, use the provided Bicep templates:

```bash
# Deploy using Bicep
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json

# Get outputs
az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name main \
  --query properties.outputs
```

---

## 🔐 Security Best Practices

### 1. Use Azure Key Vault for Secrets

```bash
# Create Key Vault
az keyvault create \
  --name "kv-nl2sql-$RANDOM" \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Store secrets
az keyvault secret set --vault-name "kv-nl2sql" --name "sql-password" --value "your-password"
az keyvault secret set --vault-name "kv-nl2sql" --name "openai-key" --value "your-key"

# Grant managed identity access to Key Vault
az keyvault set-policy \
  --name "kv-nl2sql" \
  --object-id $IDENTITY_PRINCIPAL_ID \
  --secret-permissions get list
```

### 2. Network Security

- Use **private networking** for production environments
- Configure **firewall rules** on Azure SQL
- Enable **virtual network integration**

### 3. Authentication

- Configure **Azure AD authentication** for SQL Database
- Use **managed identities** instead of connection strings
- Enable **Azure AD authentication** on the Container App

---

## 🔄 Continuous Deployment (CI/CD)

### GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Azure Container Apps

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      - name: Build and push image
        run: |
          az acr build \
            --registry ${{ secrets.ACR_NAME }} \
            --image nl2sql-multimodel:${{ github.sha }} \
            --file Dockerfile.multimodel \
            .
      
      - name: Deploy to Container Apps
        run: |
          az containerapp update \
            --name ${{ secrets.CONTAINER_APP_NAME }} \
            --resource-group ${{ secrets.RESOURCE_GROUP }} \
            --image ${{ secrets.ACR_NAME }}.azurecr.io/nl2sql-multimodel:${{ github.sha }}
```

---

## 📊 Monitoring and Logs

### View Application Logs

```bash
# Stream logs in real-time
az containerapp logs show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow

# Get recent logs
az containerapp logs show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --tail 100
```

### Enable Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app nl2sql-insights \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app nl2sql-insights \
  --resource-group $RESOURCE_GROUP \
  --query instrumentationKey -o tsv)

# Update container app with Application Insights
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=$INSTRUMENTATION_KEY"
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Container App Won't Start

```bash
# Check logs
az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --tail 50

# Check replica status
az containerapp replica list \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --output table
```

#### 2. Can't Pull Image from ACR

```bash
# Verify managed identity has AcrPull role
az role assignment list \
  --assignee $IDENTITY_PRINCIPAL_ID \
  --scope $ACR_ID \
  --output table

# Re-assign if needed
az role assignment create \
  --assignee $IDENTITY_PRINCIPAL_ID \
  --role AcrPull \
  --scope $ACR_ID
```

#### 3. Environment Variables Not Working

```bash
# List current environment variables
az containerapp show \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --query properties.template.containers[0].env

# Update environment variables
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars KEY=VALUE
```

---

## 🔄 Updating Your Deployment

### Update Container Image

```bash
# Build new version
az acr build \
  --registry $ACR_NAME \
  --image $IMAGE_NAME:v2 \
  --file Dockerfile.multimodel \
  .

# Update container app to use new image
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --image $ACR_LOGIN_SERVER/$IMAGE_NAME:v2
```

### Update Environment Variables

```bash
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    NEW_VAR=value \
    ANOTHER_VAR=value
```

### Scale the App

```bash
# Scale replicas
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 2 \
  --max-replicas 5

# Scale resources
az containerapp update \
  --name $CONTAINER_APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --cpu 2.0 \
  --memory 4.0Gi
```

---

## 💰 Cost Optimization

### Estimated Monthly Costs

- **Container Apps**: ~$15-50/month (1-2 replicas, 1 vCPU, 2GB RAM)
- **Azure Container Registry**: ~$5/month (Basic tier)
- **Egress Traffic**: Variable based on usage
- **Azure OpenAI**: Based on token usage (track via app logs)

### Cost-Saving Tips

1. **Use consumption-only pricing** for Container Apps
2. **Set appropriate min/max replicas** (min=0 for dev, min=1 for prod)
3. **Monitor token usage** to optimize model selection
4. **Use Basic ACR tier** for development
5. **Enable auto-scale** based on HTTP traffic

---

## 📚 Additional Resources

- [Azure Container Apps Documentation](https://learn.microsoft.com/azure/container-apps/)
- [Streamlit Deployment Guide](https://docs.streamlit.io/deploy)
- [Azure CLI Reference](https://learn.microsoft.com/cli/azure/)
- [Managed Identities Overview](https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/)

---

## 🎉 Next Steps

After deployment:

1. ✅ Test the app at the provided URL
2. ✅ Set up monitoring and alerts
3. ✅ Configure custom domain (optional)
4. ✅ Enable HTTPS with custom certificate
5. ✅ Set up CI/CD pipeline
6. ✅ Configure authentication/authorization
7. ✅ Review and optimize costs

**Your NL2SQL Multi-Model app is now live and accessible to your users!** 🚀
