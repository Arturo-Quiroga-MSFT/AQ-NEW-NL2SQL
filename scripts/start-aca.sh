#!/bin/bash
# start-aca.sh: Start the Azure Container App after changes

RESOURCE_GROUP="AI-FOUNDRY-RG"
CONTAINER_APP="nl2sql-streamlit-app"

az containerapp start \
  --name "$CONTAINER_APP" \
  --resource-group "$RESOURCE_GROUP"
