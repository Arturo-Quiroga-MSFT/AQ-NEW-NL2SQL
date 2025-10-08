#!/bin/bash

# ============================================================================
# Azure Container Apps Deployment Script for NL2SQL Multi-Model App
# ============================================================================
# This script automates the deployment of the NL2SQL application to Azure
# Container Apps with all necessary infrastructure.
#
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - .env.azure file configured with your settings
#   - Appropriate Azure permissions
#
# Usage:
#   ./deploy.sh [OPTIONS]
#
# Options:
#   --skip-build    Skip Docker image build (use existing image)
#   --skip-infra    Skip infrastructure deployment
#   --preview       Preview deployment without applying
#   --help          Show this help message
# ============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Helper Functions
# ============================================================================

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

show_help() {
    cat << EOF
Azure Container Apps Deployment Script for NL2SQL Multi-Model App

Usage: ./deploy.sh [OPTIONS]

Options:
    --skip-build    Skip Docker image build (use existing image)
    --skip-infra    Skip infrastructure deployment (only update app)
    --preview       Preview deployment without applying (what-if mode)
    --help          Show this help message

Examples:
    ./deploy.sh                    # Full deployment
    ./deploy.sh --skip-build       # Deploy without rebuilding image
    ./deploy.sh --preview          # Preview changes only
    ./deploy.sh --skip-infra       # Update app only

Prerequisites:
    1. Azure CLI installed: https://aka.ms/InstallAzureCLI
    2. Logged in: az login
    3. .env.azure file configured with your settings

For more information, see DEPLOYMENT_GUIDE.md
EOF
}

# ============================================================================
# Parse Arguments
# ============================================================================

SKIP_BUILD=false
SKIP_INFRA=false
PREVIEW_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-infra)
            SKIP_INFRA=true
            shift
            ;;
        --preview)
            PREVIEW_MODE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# ============================================================================
# Check Prerequisites
# ============================================================================

log_info "Checking prerequisites..."

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    log_error "Azure CLI is not installed. Please install it from: https://aka.ms/InstallAzureCLI"
    exit 1
fi

# Check if logged in to Azure
if ! az account show &> /dev/null; then
    log_error "Not logged in to Azure. Please run: az login"
    exit 1
fi

# Check if .env.azure exists
if [ ! -f .env.azure ]; then
    log_error ".env.azure file not found. Please copy .env.template to .env.azure and configure it."
    exit 1
fi

log_success "Prerequisites check passed"

# ============================================================================
# Load Environment Variables
# ============================================================================

log_info "Loading environment variables from .env.azure..."
set -a
source .env.azure
set +a

# Validate required variables
REQUIRED_VARS=(
    "RESOURCE_GROUP"
    "LOCATION"
    "ACR_NAME"
    "CONTAINER_APP_NAME"
    "IMAGE_NAME"
    "AZURE_OPENAI_API_KEY"
    "AZURE_OPENAI_ENDPOINT"
    "AZURE_SQL_SERVER"
    "AZURE_SQL_PASSWORD"
)

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        log_error "Required variable $var is not set in .env.azure"
        exit 1
    fi
done

log_success "Environment variables loaded"

# ============================================================================
# Display Deployment Configuration
# ============================================================================

echo ""
log_info "Deployment Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  Location: $LOCATION"
echo "  ACR Name: $ACR_NAME"
echo "  Container App: $CONTAINER_APP_NAME"
echo "  Image: $IMAGE_NAME:${IMAGE_TAG:-latest}"
echo "  Environment: ${ENVIRONMENT:-dev}"
echo ""

if [ "$PREVIEW_MODE" = true ]; then
    log_warning "Running in PREVIEW mode - no changes will be applied"
fi

# Confirm deployment
if [ "$PREVIEW_MODE" = false ]; then
    read -p "Continue with deployment? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Deployment cancelled"
        exit 0
    fi
fi

# ============================================================================
# Create Resource Group (if it doesn't exist)
# ============================================================================

if [ "$SKIP_INFRA" = false ]; then
    log_info "Checking resource group..."
    
    if ! az group show --name "$RESOURCE_GROUP" &> /dev/null; then
        log_info "Creating resource group: $RESOURCE_GROUP"
        az group create \
            --name "$RESOURCE_GROUP" \
            --location "$LOCATION" \
            --tags "Environment=${ENVIRONMENT:-dev}" "Project=${PROJECT_NAME:-nl2sql}" "ManagedBy=Script"
        log_success "Resource group created"
    else
        log_success "Resource group already exists"
    fi
fi

# ============================================================================
# Build and Push Docker Image
# ============================================================================

if [ "$SKIP_BUILD" = false ]; then
    log_info "Building and pushing Docker image to ACR..."
    
    # Check if ACR exists
    if ! az acr show --name "$ACR_NAME" --resource-group "$RESOURCE_GROUP" &> /dev/null; then
        log_warning "ACR does not exist. It will be created during infrastructure deployment."
        SKIP_BUILD=true
    else
        log_info "Building image: $IMAGE_NAME:${IMAGE_TAG:-latest}"
        
        if [ "$PREVIEW_MODE" = false ]; then
            # Build from parent directory (project root)
            cd ..
            az acr build \
                --registry "$ACR_NAME" \
                --image "$IMAGE_NAME:${IMAGE_TAG:-latest}" \
                --file azure_deployment/Dockerfile.multimodel \
                .
            cd azure_deployment
            
            log_success "Docker image built and pushed to ACR"
        else
            log_info "[PREVIEW] Would build and push Docker image"
        fi
    fi
fi

# ============================================================================
# Deploy Infrastructure with Bicep
# ============================================================================

if [ "$SKIP_INFRA" = false ]; then
    log_info "Deploying infrastructure with Bicep..."
    
    # Update parameters file with values from .env.azure
    PARAMS_FILE="infra/main.parameters.json"
    TEMP_PARAMS_FILE="infra/main.parameters.tmp.json"
    
    cat > "$TEMP_PARAMS_FILE" << EOF
{
  "\$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "projectName": {"value": "${PROJECT_NAME:-nl2sql}"},
    "environment": {"value": "${ENVIRONMENT:-dev}"},
    "imageName": {"value": "$IMAGE_NAME"},
    "imageTag": {"value": "${IMAGE_TAG:-latest}"},
    "azureOpenAiApiKey": {"value": "$AZURE_OPENAI_API_KEY"},
    "azureOpenAiEndpoint": {"value": "$AZURE_OPENAI_ENDPOINT"},
    "azureOpenAiApiVersion": {"value": "${AZURE_OPENAI_API_VERSION:-2025-04-01-preview}"},
    "azureSqlServer": {"value": "$AZURE_SQL_SERVER"},
    "azureSqlDatabase": {"value": "$AZURE_SQL_DB"},
    "azureSqlUser": {"value": "$AZURE_SQL_USER"},
    "azureSqlPassword": {"value": "$AZURE_SQL_PASSWORD"},
    "minReplicas": {"value": ${MIN_REPLICAS:-1}},
    "maxReplicas": {"value": ${MAX_REPLICAS:-3}},
    "cpuCores": {"value": "${CPU_CORES:-1.0}"},
    "memorySize": {"value": "${MEMORY_SIZE:-2.0Gi}"}
  }
}
EOF
    
    if [ "$PREVIEW_MODE" = true ]; then
        log_info "Running deployment preview (what-if)..."
        az deployment group what-if \
            --resource-group "$RESOURCE_GROUP" \
            --template-file infra/main.bicep \
            --parameters "$TEMP_PARAMS_FILE"
    else
        log_info "Deploying infrastructure..."
        DEPLOYMENT_OUTPUT=$(az deployment group create \
            --resource-group "$RESOURCE_GROUP" \
            --template-file infra/main.bicep \
            --parameters "$TEMP_PARAMS_FILE" \
            --output json)
        
        # Clean up temp file
        rm -f "$TEMP_PARAMS_FILE"
        
        log_success "Infrastructure deployed successfully"
        
        # Extract and display outputs
        APP_URL=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.containerAppUrl.value')
        ACR_LOGIN_SERVER=$(echo "$DEPLOYMENT_OUTPUT" | jq -r '.properties.outputs.containerRegistryLoginServer.value')
        
        log_success "Deployment completed!"
        echo ""
        log_info "Deployment Outputs:"
        echo "  App URL: $APP_URL"
        echo "  ACR Login Server: $ACR_LOGIN_SERVER"
        echo ""
    fi
else
    log_info "Skipping infrastructure deployment"
fi

# ============================================================================
# Build Image After Infrastructure (if skipped earlier)
# ============================================================================

if [ "$SKIP_BUILD" = true ] && [ "$SKIP_INFRA" = false ] && [ "$PREVIEW_MODE" = false ]; then
    log_info "Building and pushing Docker image now that ACR exists..."
    
    # Build from parent directory (project root)
    cd ..
    az acr build \
        --registry "$ACR_NAME" \
        --image "$IMAGE_NAME:${IMAGE_TAG:-latest}" \
        --file azure_deployment/Dockerfile.multimodel \
        .
    cd azure_deployment
    
    log_success "Docker image built and pushed to ACR"
fi

# ============================================================================
# Update Container App (if only updating app)
# ============================================================================

if [ "$SKIP_INFRA" = true ]; then
    log_info "Updating Container App with new image..."
    
    if [ "$PREVIEW_MODE" = false ]; then
        ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
        
        az containerapp update \
            --name "$CONTAINER_APP_NAME" \
            --resource-group "$RESOURCE_GROUP" \
            --image "$ACR_LOGIN_SERVER/$IMAGE_NAME:${IMAGE_TAG:-latest}"
        
        log_success "Container App updated"
    else
        log_info "[PREVIEW] Would update Container App with new image"
    fi
fi

# ============================================================================
# Get Application Status
# ============================================================================

if [ "$PREVIEW_MODE" = false ] && [ "$SKIP_INFRA" = false ]; then
    log_info "Checking application status..."
    
    APP_URL=$(az containerapp show \
        --name "$CONTAINER_APP_NAME" \
        --resource-group "$RESOURCE_GROUP" \
        --query "properties.configuration.ingress.fqdn" -o tsv)
    
    echo ""
    log_success "🎉 Deployment Complete!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "  🌐 Application URL: https://$APP_URL"
    echo ""
    echo "  📊 View logs:"
    echo "     az containerapp logs show --name $CONTAINER_APP_NAME --resource-group $RESOURCE_GROUP --follow"
    echo ""
    echo "  🔧 Manage app:"
    echo "     https://portal.azure.com/#@/resource/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$CONTAINER_APP_NAME"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
fi

log_success "Script completed successfully!"
