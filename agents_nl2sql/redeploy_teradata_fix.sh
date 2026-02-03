#!/bin/bash
# Script to rebuild and redeploy Container Apps for TERADATA-FI schema

set -e

echo "======================================================================"
echo "Rebuilding and Redeploying Container Apps for TERADATA-FI Schema"
echo "======================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ACR_NAME="acrnl2sqlddo6f5dplg5v4"
IMAGE_NAME="nl2sql-multimodel"
TAG="teradata-fix-$(date +%Y%m%d-%H%M%S)"

echo -e "${BLUE}Step 1: Building Docker image in ACR...${NC}"
echo "Image: $IMAGE_NAME:$TAG"
echo ""

cd ..
az acr build \
  --registry "$ACR_NAME" \
  --image "$IMAGE_NAME:$TAG" \
  --file azure_deployment/Dockerfile.multimodel \
  .

echo ""
echo -e "${GREEN}✅ Docker image built successfully${NC}"
echo ""

# Update nl2sql-app-dev
echo -e "${BLUE}Step 2: Updating nl2sql-app-dev...${NC}"
az containerapp update \
  --name nl2sql-app-dev \
  --resource-group rg-nl2sql-app \
  --image "$ACR_NAME.azurecr.io/$IMAGE_NAME:$TAG"

echo -e "${GREEN}✅ nl2sql-app-dev updated${NC}"
echo ""

# Ask if user wants to update other apps
read -p "Update agents-nl2sql-streamlit-app as well? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Updating agents-nl2sql-streamlit-app...${NC}"
    
    # Build agents image
    cd agents_nl2sql
    az acr build \
      --registry "$ACR_NAME" \
      --image "agents-nl2sql:$TAG" \
      --file ../azure_deployment/Dockerfile.multimodel \
      ..
    
    az containerapp update \
      --name agents-nl2sql-streamlit-app \
      --resource-group AI-FOUNDRY-RG \
      --image "$ACR_NAME.azurecr.io/agents-nl2sql:$TAG"
    
    echo -e "${GREEN}✅ agents-nl2sql-streamlit-app updated${NC}"
    cd ..
fi

echo ""
echo "======================================================================"
echo -e "${GREEN}✅ Deployment Complete!${NC}"
echo "======================================================================"
echo ""
echo "The Container Apps have been updated with:"
echo "  - New database name: TERADATA-FI"
echo "  - Updated schema references (removed vw_LoanPortfolio)"
echo "  - Star schema support (fact and dimension tables)"
echo ""
echo "Test the apps:"
echo "  nl2sql-app-dev: https://nl2sql-app-dev.graydune-e88e02b6.eastus.azurecontainerapps.io"
echo ""
echo "The schema cache will be refreshed automatically on first use."
echo "Or click the 'Refresh schema cache' button in the UI."
echo ""