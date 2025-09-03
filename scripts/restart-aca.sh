#!/bin/bash
# restart-aca.sh: Stop and then start the Azure Container App, with a 10 second wait in between

RESOURCE_GROUP="AI-FOUNDRY-RG"
CONTAINER_APP="nl2sql-streamlit-app"

az containerapp stop \
  --name "$CONTAINER_APP" \
  --resource-group "$RESOURCE_GROUP"

sleep 10

ez containerapp start \
  --name "$CONTAINER_APP" \
  --resource-group "$RESOURCE_GROUP"
