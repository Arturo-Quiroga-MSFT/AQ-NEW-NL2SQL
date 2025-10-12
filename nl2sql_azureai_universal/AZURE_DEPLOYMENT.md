# Deploy NL2SQL Bot to Azure App Service - Production Guide

## 📋 Prerequisites

- ✅ Azure subscription with permissions to create resources
- ✅ Azure CLI installed: https://docs.microsoft.com/cli/azure/install-azure-cli
- ✅ Git installed for deployment
- ✅ Bot working locally with dev tunnel

---

## 🚀 Deployment Steps

### Step 1: Login to Azure

```bash
az login
```

### Step 2: Set Your Subscription

```bash
# List subscriptions
az account list --output table

# Set the subscription you want to use
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

### Step 3: Create Resource Group (if you don't have one)

```bash
# Create resource group in your preferred region
az group create \
  --name rg-nl2sql-bot \
  --location eastus
```

### Step 4: Create App Service Plan

```bash
# Create Linux App Service Plan (B1 - Basic tier is good for start)
az appservice plan create \
  --name plan-nl2sql-bot \
  --resource-group rg-nl2sql-bot \
  --location eastus \
  --is-linux \
  --sku B1
```

**SKU Options:**
- `F1` - Free (limited, good for testing)
- `B1` - Basic $13/month (recommended for dev/test)
- `S1` - Standard $70/month (recommended for production)
- `P1V2` - Premium $146/month (high performance)

### Step 5: Create Web App

```bash
# Create Python 3.11 web app
az webapp create \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot \
  --plan plan-nl2sql-bot \
  --runtime "PYTHON:3.11"
```

**Important**: The app name must be globally unique. If `nl2sql-teams-bot` is taken, try:
- `nl2sql-bot-yourcompany`
- `nl2sql-teams-yourname`
- `nl2sql-bot-$(date +%s)` (adds timestamp)

Your bot URL will be: `https://YOUR-APP-NAME.azurewebsites.net`

### Step 6: Configure Application Settings

Set all your environment variables in Azure:

```bash
# Set bot credentials
az webapp config appsettings set \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot \
  --settings \
    CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTID="<YOUR_BOT_ID_HERE>" \
    CONNECTIONS__SERVICE_CONNECTION__SETTINGS__CLIENTSECRET="<YOUR_CLIENT_SECRET_HERE>" \
    CONNECTIONS__SERVICE_CONNECTION__SETTINGS__TENANTID="<YOUR_TENANT_ID_HERE>"

# Set Azure AI credentials (from your .env file)
az webapp config appsettings set \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot \
  --settings \
    PROJECT_CONNECTION_STRING="YOUR_PROJECT_CONNECTION_STRING" \
    MODEL_DEPLOYMENT_NAME="gpt-4o"

# Set database connection
az webapp config appsettings set \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot \
  --settings \
    DB_SERVER="YOUR_DB_SERVER" \
    DB_DATABASE="YOUR_DB_NAME" \
    DB_DRIVER="{ODBC Driver 18 for SQL Server}"
```

**To get your current environment variables:**
```bash
cd /Users/arturoquiroga/GITHUB/AQ-NEW-NL2SQL/nl2sql_azureai_universal
cat .env
```

### Step 7: Enable HTTPS Only

```bash
az webapp update \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot \
  --https-only true
```

### Step 8: Configure Startup Command

```bash
az webapp config set \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot \
  --startup-file "python start_server.py"
```

### Step 9: Deploy the Code

#### Option A: Deploy from Local Git (Recommended)

```bash
# Navigate to your bot directory
cd /Users/arturoquiroga/GITHUB/AQ-NEW-NL2SQL/nl2sql_azureai_universal

# Initialize git if not already
git init

# Add all necessary files
git add \
  start_server.py \
  teams_nl2sql_agent.py \
  nl2sql_main.py \
  schema_reader.py \
  sql_executor.py \
  requirements-production.txt \
  .python_version

# Create .python_version file
echo "3.11" > .python_version
git add .python_version

# Commit
git commit -m "Production deployment"

# Get deployment credentials
az webapp deployment user set \
  --user-name nl2sql-deployer \
  --password "YourSecurePassword123!"

# Configure local git deployment
az webapp deployment source config-local-git \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot

# Add Azure as a git remote (you'll get this URL from previous command)
git remote add azure https://nl2sql-deployer@nl2sql-teams-bot.scm.azurewebsites.net/nl2sql-teams-bot.git

# Push to Azure
git push azure main
```

#### Option B: Deploy ZIP File

```bash
# Navigate to bot directory
cd /Users/arturoquiroga/GITHUB/AQ-NEW-NL2SQL/nl2sql_azureai_universal

# Create deployment package
zip -r deploy.zip \
  start_server.py \
  teams_nl2sql_agent.py \
  nl2sql_main.py \
  schema_reader.py \
  sql_executor.py \
  requirements-production.txt \
  -x "*.pyc" -x "__pycache__/*" -x ".env"

# Deploy
az webapp deployment source config-zip \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot \
  --src deploy.zip
```

#### Option C: Deploy from GitHub

If your code is in GitHub:

```bash
az webapp deployment source config \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot \
  --repo-url https://github.com/Arturo-Quiroga-MSFT/AQ-NEW-NL2SQL \
  --branch main \
  --manual-integration
```

### Step 10: Monitor Deployment

```bash
# Watch deployment logs
az webapp log tail \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot

# Check if app is running
az webapp show \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot \
  --query "defaultHostName" \
  --output tsv
```

### Step 11: Verify Deployment

Your bot should be accessible at:
```
https://nl2sql-teams-bot.azurewebsites.net/api/messages
```

Test it:
```bash
curl https://nl2sql-teams-bot.azurewebsites.net/api/messages
```

---

## 🔧 Step 12: Update Azure Bot Service

Update your bot's messaging endpoint:

```bash
# Get your Azure Bot resource name
BOT_NAME="aq_r2d2_bot"  # Replace with your bot name

# Update messaging endpoint
az bot update \
  --name $BOT_NAME \
  --resource-group AQ-BOT \
  --endpoint "https://nl2sql-teams-bot.azurewebsites.net/api/messages"
```

**Or via Azure Portal:**
1. Go to Azure Portal → Your Bot Resource
2. Settings → Configuration
3. Update **Messaging endpoint** to: `https://nl2sql-teams-bot.azurewebsites.net/api/messages`
4. Click **Apply**

---

## 📱 Step 13: Update Teams App Manifest

Update the manifest for production:

```bash
cd /Users/arturoquiroga/GITHUB/AQ-NEW-NL2SQL/nl2sql_azureai_universal/teams_app
```

Edit `manifest.json`:
- Change `validDomains`: `["nl2sql-teams-bot.azurewebsites.net"]`
- Update version: `"version": "1.1.0"`

Recreate the package:
```bash
zip -r nl2sql-teams-app-production.zip manifest.json color.png outline.png
```

Upload to Teams:
1. Remove the old dev version from Teams
2. Upload `nl2sql-teams-app-production.zip`
3. Test!

---

## 🔍 Troubleshooting

### Check Application Logs

```bash
# Stream logs
az webapp log tail \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot

# Download logs
az webapp log download \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot \
  --log-file bot-logs.zip
```

### Enable Detailed Logging

```bash
az webapp log config \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot \
  --application-logging filesystem \
  --detailed-error-messages true \
  --failed-request-tracing true \
  --web-server-logging filesystem
```

### SSH into Container

```bash
az webapp ssh \
  --name nl2sql-teams-bot \
  --resource-group rg-nl2sql-bot
```

### Common Issues

**Bot not responding:**
- Check logs: `az webapp log tail`
- Verify environment variables are set
- Ensure messaging endpoint is correct
- Check if app is running: `az webapp show`

**Database connection fails:**
- Verify DB credentials in app settings
- Check if Azure can reach your database
- May need to add Azure App Service IPs to database firewall

**Authentication fails:**
- Verify bot credentials are correct
- Check tenant ID matches
- Ensure client secret hasn't expired

---

## 💰 Cost Estimation

**Monthly costs for production setup:**
- App Service Plan (B1): ~$13/month
- Azure Bot Service: Free tier available
- Azure AI (GPT-4o): Pay per token used
- Database: Depends on your SQL Server plan

**Total estimated**: $20-50/month for small-medium usage

---

## 🎯 Next Steps After Deployment

1. **Monitor Performance**
   - Set up Application Insights
   - Configure alerts for errors
   - Monitor token usage

2. **Secure Secrets**
   - Move secrets to Azure Key Vault
   - Use Managed Identity

3. **Scale**
   - Upgrade App Service Plan if needed
   - Enable auto-scaling
   - Add CDN for static content

4. **CI/CD**
   - Set up GitHub Actions
   - Automated testing
   - Blue-green deployments

---

## 📚 Useful Commands

```bash
# Restart app
az webapp restart --name nl2sql-teams-bot --resource-group rg-nl2sql-bot

# Stop app
az webapp stop --name nl2sql-teams-bot --resource-group rg-nl2sql-bot

# Start app
az webapp start --name nl2sql-teams-bot --resource-group rg-nl2sql-bot

# Delete app (cleanup)
az webapp delete --name nl2sql-teams-bot --resource-group rg-nl2sql-bot

# View app settings
az webapp config appsettings list --name nl2sql-teams-bot --resource-group rg-nl2sql-bot
```

---

Ready to deploy? Start with Step 1! 🚀
