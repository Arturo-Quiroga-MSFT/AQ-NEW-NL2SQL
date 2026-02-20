cd nl2sql_next

# Rebuild image in ACR
az acr build --registry aqnl2sqlnextacr \
    --image nl2sql-next:$(date +%Y%m%d-%H%M%S) \
    --image nl2sql-next:latest \
    --file Dockerfile .

# Update ACA app to use new image
az containerapp update \
    --name aq-nl2sql-next-app \
    --resource-group aq-nl2sql-next-rg \
    --image aqnl2sqlnextacr.azurecr.io/nl2sql-next:latest