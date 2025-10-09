# These commands help you list and view log files in your Azure Container App
# Execute a command inside the running container
az containerapp exec \
  --name nl2sql-app-dev \
  --resource-group rg-nl2sql-app \
  --command "ls -la /app/RESULTS"

# View a specific log file
az containerapp exec \
  --name nl2sql-app-dev \
  --resource-group rg-nl2sql-app \
  --command "cat /app/RESULTS/nl2sql_multimodel_v2_run_20251009_143147.txt"