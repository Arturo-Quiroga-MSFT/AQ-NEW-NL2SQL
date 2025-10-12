#!/bin/bash

# ========================================
# Deploy NL2SQL Teams Bot to Azure Container Apps
# ========================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
RESOURCE_GROUP="AQ-BOT-RG"
LOCATION="eastus"
ACR_NAME="nl2sqlacr$(date +%s)"  # Unique name with timestamp
CONTAINER_APP_NAME="nl2sql-teams-bot"
CONTAINER_APP_ENV="nl2sql-env"
IMAGE_NAME="nl2sql-teams-bot"
IMAGE_TAG="latest"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}NL2SQL Teams Bot - Azure Container Apps Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Function to print status
print_status() {
    echo -e "${YELLOW}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    print_error "Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged in
print_status "Checking Azure login status..."
if ! az account show &> /dev/null; then
    print_error "Not logged in to Azure. Please run 'az login' first."
    exit 1
fi
print_success "Azure login verified"

# Check if resource group exists, create if not
print_status "Checking resource group..."
if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
    print_status "Creating resource group $RESOURCE_GROUP..."
    az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
    print_success "Resource group created"
else
    print_success "Resource group exists"
fi

# Create Azure Container Registry
print_status "Creating Azure Container Registry..."
az acr create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$ACR_NAME" \
    --sku Basic \
    --admin-enabled true
print_success "Container Registry created: $ACR_NAME"

# Get ACR credentials
print_status "Getting ACR credentials..."
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query passwords[0].value -o tsv)
ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
print_success "ACR credentials retrieved"

# Build and push Docker image
print_status "Building Docker image..."
cd "$(dirname "$0")"
docker build -t "$IMAGE_NAME:$IMAGE_TAG" .
print_success "Docker image built"

print_status "Tagging image for ACR..."
docker tag "$IMAGE_NAME:$IMAGE_TAG" "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG"
print_success "Image tagged"

print_status "Logging in to ACR..."
az acr login --name "$ACR_NAME"
print_success "Logged in to ACR"

print_status "Pushing image to ACR..."
docker push "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG"
print_success "Image pushed to ACR"

# Create Container Apps Environment
print_status "Creating Container Apps Environment..."
az containerapp env create \
    --name "$CONTAINER_APP_ENV" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION"
print_success "Container Apps Environment created"

# Get environment variables (prompt user)
echo ""
echo -e "${YELLOW}Please provide the following environment variables:${NC}"
read -p "BOT_ID (from Azure Bot registration): " BOT_ID
read -p "BOT_PASSWORD (from Azure Bot registration): " BOT_PASSWORD
read -p "BOT_TENANT_ID: " BOT_TENANT_ID
read -p "AZURE_OPENAI_ENDPOINT: " AZURE_OPENAI_ENDPOINT
read -p "AZURE_OPENAI_DEPLOYMENT: " AZURE_OPENAI_DEPLOYMENT
read -p "AZURE_OPENAI_API_VERSION: " AZURE_OPENAI_API_VERSION
read -p "AZURE_OPENAI_API_KEY: " AZURE_OPENAI_API_KEY
read -p "DATABASE_SERVER: " DATABASE_SERVER
read -p "DATABASE_NAME: " DATABASE_NAME
read -p "DATABASE_USERNAME: " DATABASE_USERNAME
read -p "DATABASE_PASSWORD: " DATABASE_PASSWORD

# Create Container App
print_status "Creating Container App..."
az containerapp create \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$CONTAINER_APP_ENV" \
    --image "$ACR_LOGIN_SERVER/$IMAGE_NAME:$IMAGE_TAG" \
    --registry-server "$ACR_LOGIN_SERVER" \
    --registry-username "$ACR_USERNAME" \
    --registry-password "$ACR_PASSWORD" \
    --target-port 3978 \
    --ingress external \
    --min-replicas 1 \
    --max-replicas 3 \
    --cpu 1.0 \
    --memory 2Gi \
    --env-vars \
        BOT_ID="$BOT_ID" \
        BOT_PASSWORD="$BOT_PASSWORD" \
        BOT_TENANT_ID="$BOT_TENANT_ID" \
        AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT" \
        AZURE_OPENAI_DEPLOYMENT="$AZURE_OPENAI_DEPLOYMENT" \
        AZURE_OPENAI_API_VERSION="$AZURE_OPENAI_API_VERSION" \
        AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
        DATABASE_SERVER="$DATABASE_SERVER" \
        DATABASE_NAME="$DATABASE_NAME" \
        DATABASE_USERNAME="$DATABASE_USERNAME" \
        DATABASE_PASSWORD="$DATABASE_PASSWORD" \
        PORT="3978"

print_success "Container App created"

# Get the app URL
APP_URL=$(az containerapp show \
    --name "$CONTAINER_APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query properties.configuration.ingress.fqdn -o tsv)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}Container App URL: https://$APP_URL${NC}"
echo -e "${GREEN}Bot Endpoint: https://$APP_URL/api/messages${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update your Azure Bot registration with the new messaging endpoint:"
echo "   https://$APP_URL/api/messages"
echo ""
echo "2. Test your bot in Teams"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
echo ""
