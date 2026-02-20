
#!/usr/bin/env bash
set -euo pipefail

TAG=$(date +%Y%m%d-%H%M%S)
echo "=== Building image with tag: $TAG ==="

# Rebuild image in ACR with unique tag + latest
az acr build --registry aqnl2sqlnextacr \
    --image "nl2sql-next:${TAG}" \
    --image nl2sql-next:latest \
    --file Dockerfile .

echo "=== Updating ACA to use nl2sql-next:${TAG} ==="

# Update ACA app with the unique tag to force a new revision
az containerapp update \
    --name aq-nl2sql-next-app \
    --resource-group aq-nl2sql-next-rg \
    --image "aqnl2sqlnextacr.azurecr.io/nl2sql-next:${TAG}"

echo "=== Done. Revision deployed with tag: $TAG ==="