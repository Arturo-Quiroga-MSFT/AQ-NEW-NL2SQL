#!/usr/bin/env bash
set -euo pipefail

# Purpose: Configure secrets & environment variables for the Agents NL2SQL Container App.
# Fixes prior issues:
#  - Secret names must be lowercase alphanumeric or '-' (no uppercase / underscores)
#  - secretref:<name> must reference the secret NAME, not the secret VALUE
#  - Avoid committing raw secrets (use exported env vars instead)

RESOURCE_GROUP="AI-FOUNDRY-RG"
APP_NAME="agents-nl2sql-streamlit-app"

# Required (export these before running):
#   export OPENAI_KEY="<rotated-openai-key>"
#   export SQL_PASSWORD="<rotated-sql-password>"
OPENAI_KEY="${OPENAI_KEY:-}"
SQL_PASSWORD="${SQL_PASSWORD:-}"

# Non-secret runtime configuration (adjust as needed)
OPENAI_ENDPOINT="https://aq-ai-foundry-sweden-central.openai.azure.com/"
OPENAI_DEPLOYMENT="gpt-5"
SQL_SERVER="aqsqlserver001.database.windows.net"
SQL_DB="TERADATA-FI"
SQL_USER="<YOUR_DB_USER>"

# Secret names (MUST be lowercase + hyphens)
SECRET_NAME_OPENAI="openai-api-key"
SECRET_NAME_SQLPWD="sql-password"

info() { echo -e "[INFO] $*"; }
err() { echo -e "[ERROR] $*" >&2; }

info "Checking Azure login context"
az account show -o table >/dev/null 2>&1 || { err "Not logged in. Run: az login"; exit 1; }

info "Verifying Container App exists: $APP_NAME"
az containerapp show -g "$RESOURCE_GROUP" -n "$APP_NAME" --query name -o tsv >/dev/null || { err "Container App $APP_NAME not found in $RESOURCE_GROUP"; exit 2; }

if [[ -z "$OPENAI_KEY" || -z "$SQL_PASSWORD" ]]; then
  err "OPENAI_KEY and/or SQL_PASSWORD env vars are empty. Export them first."
  exit 3
fi

info "Setting secrets ($SECRET_NAME_OPENAI, $SECRET_NAME_SQLPWD)"
az containerapp secret set \
  -g "$RESOURCE_GROUP" -n "$APP_NAME" \
  --secrets "$SECRET_NAME_OPENAI=$OPENAI_KEY" "$SECRET_NAME_SQLPWD=$SQL_PASSWORD"

info "Listing secret names (values are NOT shown)"
az containerapp secret list -g "$RESOURCE_GROUP" -n "$APP_NAME" -o table || true

info "Mapping env vars to secrets + static values"
az containerapp update \
  -g "$RESOURCE_GROUP" -n "$APP_NAME" \
  --set-env-vars \
    AZURE_OPENAI_API_KEY=secretref:$SECRET_NAME_OPENAI \
    AZURE_SQL_PASSWORD=secretref:$SECRET_NAME_SQLPWD \
    AZURE_OPENAI_ENDPOINT="$OPENAI_ENDPOINT" \
    AZURE_OPENAI_DEPLOYMENT_NAME="$OPENAI_DEPLOYMENT" \
    AZURE_SQL_SERVER="$SQL_SERVER" \
    AZURE_SQL_DB="$SQL_DB" \
    AZURE_SQL_USER="$SQL_USER"

info "Current image reference (for awareness)"
az containerapp show -g "$RESOURCE_GROUP" -n "$APP_NAME" --query 'properties.template.containers[0].image' -o tsv || true

FQDN=$(az containerapp show -g "$RESOURCE_GROUP" -n "$APP_NAME" --query properties.configuration.ingress.fqdn -o tsv || echo '')
info "Ingress FQDN: $FQDN"

cat <<'EOF'
Next steps:
  1. If prior secrets were exposed publicly, ensure they are rotated in Azure OpenAI + SQL.
  2. Trigger a new image deploy (push to main) if you need updated code.
  3. Open the FQDN above and run a sample query in the Agents UI.
  4. To re-run with new secrets: export OPENAI_KEY / SQL_PASSWORD then rerun this script.
EOF