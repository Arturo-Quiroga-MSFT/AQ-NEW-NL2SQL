#!/bin/bash
# stop-aca.sh: Stop the Azure Container App (deallocate resources)

RESOURCE_GROUP="AI-FOUNDRY-RG"
CONTAINER_APP="nl2sql-streamlit-app"

az containerapp stop \
  --name "$CONTAINER_APP" \
  --resource-group "$RESOURCE_GROUP"
