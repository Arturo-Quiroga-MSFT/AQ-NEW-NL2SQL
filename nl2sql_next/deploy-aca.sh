#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  deploy-aca.sh — Build, push, and deploy NL2SQL to Azure
#                  Container Apps with Entra ID (Managed Identity)
#
#  Usage:
#    cd nl2sql_next && ./deploy-aca.sh
#
#  Prerequisites:
#    - az CLI logged in (az login)
#    - Docker running (for local build) OR use --acr-build
#    - .env file with Azure OpenAI credentials
# ──────────────────────────────────────────────────────────────
set -euo pipefail

# ── Configuration ────────────────────────────────────────────
PREFIX="aq-nl2sql-next"
LOCATION="eastus2"
RG="${PREFIX}-rg"
ACR_NAME="aqnl2sqlnextacr"      # ACR names: alphanumeric only
ACA_ENV="${PREFIX}-aca-env"
ACA_APP="${PREFIX}-app"
IMAGE_NAME="nl2sql-next"
IMAGE_TAG="$(date +%Y%m%d-%H%M%S)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Load .env for secrets ────────────────────────────────────
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
    echo "✓ Loaded .env"
else
    echo "ERROR: $SCRIPT_DIR/.env not found. Copy .env.example → .env and fill values."
    exit 1
fi

# Validate required env vars
for var in AZURE_OPENAI_API_KEY AZURE_OPENAI_ENDPOINT AZURE_SQL_SERVER AZURE_SQL_DB; do
    if [ -z "${!var:-}" ]; then
        echo "ERROR: $var is not set in .env"
        exit 1
    fi
done

echo ""
echo "═══════════════════════════════════════════════════"
echo "  NL2SQL → Azure Container Apps Deployment"
echo "═══════════════════════════════════════════════════"
echo "  Resource Group:  $RG"
echo "  Location:        $LOCATION"
echo "  ACR:             $ACR_NAME"
echo "  ACA Environment: $ACA_ENV"
echo "  ACA App:         $ACA_APP"
echo "  Image:           $IMAGE_NAME:$IMAGE_TAG"
echo "═══════════════════════════════════════════════════"
echo ""

# ── Step 1: Resource Group ───────────────────────────────────
echo "▸ Step 1/7: Creating resource group..."
az group create \
    --name "$RG" \
    --location "$LOCATION" \
    --output none
echo "  ✓ Resource group '$RG' ready"

# ── Step 2: Azure Container Registry ────────────────────────
echo "▸ Step 2/7: Creating container registry..."
az acr create \
    --name "$ACR_NAME" \
    --resource-group "$RG" \
    --sku Basic \
    --admin-enabled true \
    --output none 2>/dev/null || echo "  (ACR already exists)"
echo "  ✓ ACR '$ACR_NAME' ready"

# ── Step 3: Build & push image via ACR Tasks ────────────────
echo "▸ Step 3/7: Building image in ACR (cloud build)..."
az acr build \
    --registry "$ACR_NAME" \
    --image "$IMAGE_NAME:$IMAGE_TAG" \
    --image "$IMAGE_NAME:latest" \
    --file "$SCRIPT_DIR/Dockerfile" \
    "$SCRIPT_DIR"
echo "  ✓ Image built and pushed: $ACR_NAME.azurecr.io/$IMAGE_NAME:$IMAGE_TAG"

# ── Step 4: ACA Environment ─────────────────────────────────
echo "▸ Step 4/7: Creating ACA environment..."
az containerapp env create \
    --name "$ACA_ENV" \
    --resource-group "$RG" \
    --location "$LOCATION" \
    --output none 2>/dev/null || echo "  (ACA environment already exists)"
echo "  ✓ ACA environment '$ACA_ENV' ready"

# ── Step 5: Get ACR credentials ─────────────────────────────
echo "▸ Step 5/7: Fetching ACR credentials..."
ACR_SERVER="${ACR_NAME}.azurecr.io"
ACR_USER=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASS=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)
echo "  ✓ ACR credentials retrieved"

# ── Step 6: Create/Update ACA App ───────────────────────────
echo "▸ Step 6/7: Deploying container app..."

# Check if app already exists
APP_EXISTS=$(az containerapp show \
    --name "$ACA_APP" \
    --resource-group "$RG" \
    --query "name" -o tsv 2>/dev/null || echo "")

if [ -z "$APP_EXISTS" ]; then
    echo "  Creating new container app..."
    az containerapp create \
        --name "$ACA_APP" \
        --resource-group "$RG" \
        --environment "$ACA_ENV" \
        --image "$ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG" \
        --registry-server "$ACR_SERVER" \
        --registry-username "$ACR_USER" \
        --registry-password "$ACR_PASS" \
        --target-port 8000 \
        --ingress external \
        --min-replicas 0 \
        --max-replicas 3 \
        --cpu 1.0 \
        --memory 2.0Gi \
        --system-assigned \
        --secrets \
            "azure-openai-key=${AZURE_OPENAI_API_KEY}" \
        --env-vars \
            "AZURE_OPENAI_API_KEY=secretref:azure-openai-key" \
            "AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}" \
            "AZURE_OPENAI_DEPLOYMENT_NAME=${AZURE_OPENAI_DEPLOYMENT_NAME:-gpt-4.1}" \
            "AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION:-2025-04-01-preview}" \
            "AZURE_SQL_SERVER=${AZURE_SQL_SERVER}" \
            "AZURE_SQL_DB=${AZURE_SQL_DB}" \
            "AZURE_SQL_AUTH=entra" \
        --output none
else
    echo "  Updating existing container app..."
    az containerapp update \
        --name "$ACA_APP" \
        --resource-group "$RG" \
        --image "$ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG" \
        --output none

    # Update secrets and env vars
    az containerapp secret set \
        --name "$ACA_APP" \
        --resource-group "$RG" \
        --secrets "azure-openai-key=${AZURE_OPENAI_API_KEY}" \
        --output none 2>/dev/null || true

    az containerapp update \
        --name "$ACA_APP" \
        --resource-group "$RG" \
        --set-env-vars \
            "AZURE_OPENAI_API_KEY=secretref:azure-openai-key" \
            "AZURE_OPENAI_ENDPOINT=${AZURE_OPENAI_ENDPOINT}" \
            "AZURE_OPENAI_DEPLOYMENT_NAME=${AZURE_OPENAI_DEPLOYMENT_NAME:-gpt-4.1}" \
            "AZURE_OPENAI_API_VERSION=${AZURE_OPENAI_API_VERSION:-2025-04-01-preview}" \
            "AZURE_SQL_SERVER=${AZURE_SQL_SERVER}" \
            "AZURE_SQL_DB=${AZURE_SQL_DB}" \
            "AZURE_SQL_AUTH=entra" \
        --output none
fi
echo "  ✓ Container app deployed"

# ── Step 7: Configure Managed Identity for SQL ──────────────
echo "▸ Step 7/7: Configuring managed identity..."

IDENTITY_PRINCIPAL=$(az containerapp show \
    --name "$ACA_APP" \
    --resource-group "$RG" \
    --query "identity.principalId" -o tsv)

APP_URL=$(az containerapp show \
    --name "$ACA_APP" \
    --resource-group "$RG" \
    --query "properties.configuration.ingress.fqdn" -o tsv)

echo "  ✓ Managed identity principal: $IDENTITY_PRINCIPAL"

echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✓ DEPLOYMENT COMPLETE"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  App URL:    https://$APP_URL"
echo "  Image:      $ACR_SERVER/$IMAGE_NAME:$IMAGE_TAG"
echo "  Principal:  $IDENTITY_PRINCIPAL"
echo ""
echo "═══════════════════════════════════════════════════"
echo "  ⚠  REQUIRED: Grant SQL access to managed identity"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  Connect to Azure SQL as admin and run:"
echo ""
echo "    CREATE USER [${ACA_APP}] FROM EXTERNAL PROVIDER;"
echo "    ALTER ROLE db_datareader ADD MEMBER [${ACA_APP}];"
echo "    ALTER ROLE db_datawriter ADD MEMBER [${ACA_APP}];"
echo ""
echo "  (Only needed on first deployment)"
echo "═══════════════════════════════════════════════════"
