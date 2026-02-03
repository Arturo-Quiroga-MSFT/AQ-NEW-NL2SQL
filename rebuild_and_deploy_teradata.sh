#!/bin/bash
# Quick rebuild and redeploy for TERADATA-FI schema fix

set -e

echo "================================================================================"
echo "TERADATA-FI Schema Fix - Rebuild & Redeploy"
echo "================================================================================"
echo ""

# Configuration from .env.azure
ACR_NAME="acrnl2sqlddo6f5dplg5v4"
IMAGE_NAME="nl2sql-multimodel"
TAG="teradata-$(date +%Y%m%d-%H%M)"

echo "📦 Building Docker image..."
echo "   Registry: $ACR_NAME"
echo "   Image: $IMAGE_NAME:$TAG"
echo ""

# Build from project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

az acr build \
  --registry "$ACR_NAME" \
  --image "$IMAGE_NAME:$TAG" \
  --file azure_deployment/Dockerfile.multimodel \
  .

echo ""
echo "✅ Image built successfully: $ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG"
echo ""

# Update nl2sql-app-dev
echo "🚀 Updating Container Apps..."
echo ""

echo "1. Updating nl2sql-app-dev..."
az containerapp update \
  --name nl2sql-app-dev \
  --resource-group rg-nl2sql-app \
  --image "$ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG" \
  --output table

echo ""
echo "✅ nl2sql-app-dev updated"
echo ""

# Optionally update other apps
read -p "Update nl2sql-streamlit-app and agents-nl2sql-streamlit-app? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "2. Updating nl2sql-streamlit-app..."
    az containerapp update \
      --name nl2sql-streamlit-app \
      --resource-group AI-FOUNDRY-RG \
      --image "$ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG" \
      --output table
    
    echo ""
    echo "3. Updating agents-nl2sql-streamlit-app..."
    az containerapp update \
      --name agents-nl2sql-streamlit-app \
      --resource-group AI-FOUNDRY-RG \
      --image "$ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG" \
      --output table
    
    echo ""
    echo "✅ All Container Apps updated"
fi

echo ""
echo "================================================================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "================================================================================"
echo ""
echo "Changes deployed:"
echo "  ✓ Database name: TERADATA-FI"
echo "  ✓ Removed vw_LoanPortfolio references"
echo "  ✓ Updated to star schema (fact/dimension tables)"
echo "  ✓ Dynamic database name from AZURE_SQL_DB env var"
echo ""
echo "Test the app:"
echo "  https://nl2sql-app-dev.graydune-e88e02b6.eastus.azurecontainerapps.io"
echo ""
echo "Next steps:"
echo "  1. Open the app URL"
echo "  2. Click 'Refresh schema cache' button"
echo "  3. Try a query like: 'Show the 10 most recent loans'"
echo ""