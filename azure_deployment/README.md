# Azure Container Apps Deployment

This directory contains all the files needed to deploy the NL2SQL Multi-Model Streamlit application to Azure Container Apps.

## 📁 Directory Structure

```
azure_deployment/
├── README.md                    # This file
├── QUICKSTART.md               # 🚀 Start here! 3-step deployment guide
├── DEPLOYMENT_GUIDE.md         # 📖 Comprehensive deployment documentation
├── DEPLOYMENT_CHECKLIST.md     # ✅ Step-by-step validation checklist
├── AZURE_DEPLOYMENT.md         # 📊 Implementation summary & architecture
├── .env.template               # 🔧 Environment configuration template
├── Dockerfile.multimodel       # 🐳 Production Docker image
├── deploy.sh                   # 🎯 Automated deployment script
└── infra/
    ├── main.bicep              # Infrastructure as Code (Bicep)
    └── main.parameters.json    # Bicep parameters template

Note: The Dockerfile builds from the project root.
A .dockerignore file in the root directory optimizes the build context.
```

## 🚀 Quick Start

### 1. Login to Azure
```bash
az login
```

### 2. Configure Environment
```bash
cd azure_deployment
cp .env.template .env.azure
nano .env.azure  # Add your credentials
```

### 3. Deploy
```bash
./deploy.sh
```

**That's it!** Your app will be live in ~10 minutes.

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Fast 3-step deployment
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete guide with all details
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Validation checklist
- **[AZURE_DEPLOYMENT.md](AZURE_DEPLOYMENT.md)** - Architecture & implementation summary

## 🏗️ What Gets Deployed

- **Azure Container Registry** - Stores Docker images
- **User-Assigned Managed Identity** - Secure authentication
- **Log Analytics Workspace** - Application monitoring
- **Container Apps Environment** - Isolated network boundary
- **Container App** - Running Streamlit multi-model app

## 💰 Cost Estimate

~$22-40/month for infrastructure (Azure OpenAI/SQL costs separate)

## 🔐 Security Features

✅ Managed Identity (no credentials)  
✅ HTTPS only  
✅ Secrets management  
✅ RBAC with least privilege  
✅ Network isolation  

## 🛠️ Deployment Options

### Option 1: Automated Script (Recommended)
```bash
./deploy.sh
```

### Option 2: Bicep Infrastructure as Code
```bash
az deployment group create \
  --resource-group rg-nl2sql-app \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json
```

### Option 3: Manual Azure CLI
Follow commands in `DEPLOYMENT_GUIDE.md`

## 🔄 Updating Your Deployment

```bash
# Update app code
./deploy.sh --skip-infra

# Preview changes
./deploy.sh --preview

# View logs
az containerapp logs show \
  --name nl2sql-multimodel-app \
  --resource-group rg-nl2sql-app \
  --follow
```

## 📊 Monitoring

```bash
# View application logs
az containerapp logs show --name <app-name> --resource-group <rg-name> --follow

# Get app URL
az containerapp show --name <app-name> --resource-group <rg-name> --query properties.configuration.ingress.fqdn -o tsv

# Check app status
az containerapp show --name <app-name> --resource-group <rg-name> --query properties.runningStatus
```

## 🆘 Troubleshooting

### Container won't start
```bash
az containerapp logs show --name <app-name> --resource-group <rg-name> --tail 100
```

### Can't access app
1. Check if URL is correct (should start with https://)
2. Verify ingress is enabled and external
3. Check firewall rules on SQL database

### High costs
1. Scale down replicas: `az containerapp update --min-replicas 0`
2. Review Azure OpenAI token usage
3. Consider lower-tier resources for dev/test

## 🧹 Cleanup

To delete all resources:
```bash
az group delete --name <resource-group-name> --yes
```

## 📖 Additional Resources

- [Azure Container Apps Docs](https://learn.microsoft.com/azure/container-apps/)
- [Azure CLI Reference](https://learn.microsoft.com/cli/azure/)
- [Bicep Documentation](https://learn.microsoft.com/azure/azure-resource-manager/bicep/)
- [Streamlit Deployment](https://docs.streamlit.io/deploy)

## ✅ Success Criteria

Your deployment is ready when:
- ✅ App URL returns HTTP 200
- ✅ Streamlit UI loads
- ✅ Can execute test queries
- ✅ Results are formatted correctly
- ✅ Logs show no errors
- ✅ Costs are within expected range

---

**Need help?** Start with [QUICKSTART.md](QUICKSTART.md) or see [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for comprehensive instructions.
