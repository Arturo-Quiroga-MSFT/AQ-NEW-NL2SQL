# 🚀 Deploying to Azure Container Apps

This repository includes a complete, production-ready deployment solution for the NL2SQL Multi-Model Streamlit application to Azure Container Apps.

## 📁 Location

All Azure Container Apps deployment files are organized in the **`azure_deployment/`** directory:

```
azure_deployment/
├── README.md                    # Deployment directory overview
├── QUICKSTART.md               # 🚀 3-step quick start guide
├── DEPLOYMENT_GUIDE.md         # 📖 Comprehensive deployment guide
├── DEPLOYMENT_CHECKLIST.md     # ✅ Validation checklist
├── AZURE_DEPLOYMENT.md         # 📊 Architecture & implementation
├── .env.template               # 🔧 Configuration template
├── Dockerfile.multimodel       # 🐳 Production Docker image
├── deploy.sh                   # 🎯 Automated deployment script
└── infra/
    ├── main.bicep              # Infrastructure as Code
    └── main.parameters.json    # Bicep parameters
```

## 🎯 Quick Start

```bash
# Navigate to deployment directory
cd azure_deployment

# Login to Azure
az login

# Configure your settings
cp .env.template .env.azure
nano .env.azure  # Add your credentials

# Deploy!
./deploy.sh
```

## 📚 Documentation

Start with **[azure_deployment/QUICKSTART.md](azure_deployment/QUICKSTART.md)** for the fastest path to deployment.

For comprehensive information, see **[azure_deployment/DEPLOYMENT_GUIDE.md](azure_deployment/DEPLOYMENT_GUIDE.md)**.

## 💰 Cost

**~$22-40/month** for infrastructure
- Container Apps: $15-30
- Container Registry: $5
- Log Analytics: $2-5

*(Azure OpenAI and SQL costs are separate and usage-based)*

## 🔐 Security

✅ Managed Identity (no credentials stored)  
✅ HTTPS only with TLS  
✅ Azure Key Vault integration ready  
✅ RBAC with least privilege  
✅ Network isolation  

## 🏗️ What Gets Deployed

- Azure Container Registry (ACR)
- User-Assigned Managed Identity
- Log Analytics Workspace
- Container Apps Environment
- Container App running your Streamlit multi-model app

## ✨ Features

- **One-Command Deployment** - Fully automated
- **Production Ready** - Azure best practices
- **Auto-Scaling** - HTTP-based (1-3 replicas)
- **Easy Updates** - Simple script to redeploy
- **Monitoring** - Built-in Log Analytics
- **Cost Optimized** - Right-sized resources

## 🔄 Common Operations

```bash
cd azure_deployment

# Update app with new code
./deploy.sh --skip-infra

# Preview changes
./deploy.sh --preview

# View logs
az containerapp logs show \
  --name nl2sql-multimodel-app \
  --resource-group rg-nl2sql-app \
  --follow
```

## 🆘 Need Help?

1. **Quick Start**: [azure_deployment/QUICKSTART.md](azure_deployment/QUICKSTART.md)
2. **Full Guide**: [azure_deployment/DEPLOYMENT_GUIDE.md](azure_deployment/DEPLOYMENT_GUIDE.md)
3. **Checklist**: [azure_deployment/DEPLOYMENT_CHECKLIST.md](azure_deployment/DEPLOYMENT_CHECKLIST.md)
4. **Architecture**: [azure_deployment/AZURE_DEPLOYMENT.md](azure_deployment/AZURE_DEPLOYMENT.md)

---

**Ready to deploy?** Head to the [`azure_deployment/`](azure_deployment/) directory and follow the [QUICKSTART.md](azure_deployment/QUICKSTART.md)! 🎉
