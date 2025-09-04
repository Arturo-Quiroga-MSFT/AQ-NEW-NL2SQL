
#!/usr/bin/env bash
# restart-aca.sh
# Purpose: Restart an Azure Container App (ACA) by triggering a revision restart (no stop/start workaround needed).
# Requires: az CLI with containerapp extension supporting 'az containerapp revision restart'.

set -euo pipefail


# Allow overrides via env vars when invoking:
#   RESOURCE_GROUP=rg-name CONTAINER_APP=app-name REVISION_NAME=rev-name ./restart-aca.sh
RESOURCE_GROUP="${RESOURCE_GROUP:-AI-FOUNDRY-RG}"
CONTAINER_APP="${CONTAINER_APP:-nl2sql-streamlit-app}"

# If REVISION_NAME is not set, auto-detect the latest active revision
REVISION_NAME="${REVISION_NAME:-}"
if [[ -z "$REVISION_NAME" ]]; then
  echo "[INFO] No REVISION_NAME provided. Detecting latest active revision..."
  # Query for the active revision name (should be only one active at a time)
  REVISION_NAME=$(az containerapp revision list \
    --name "$CONTAINER_APP" \
    --resource-group "$RESOURCE_GROUP" \
    --query "[?active].name | [0]" \
    -o tsv)
  echo "[DEBUG] az containerapp revision list output: $REVISION_NAME"
  if [[ -z "$REVISION_NAME" ]]; then
    echo "[WARN] Could not determine the latest active revision for $CONTAINER_APP in $RESOURCE_GROUP using active filter. Trying first revision as fallback..."
    # Print the full JSON for debugging
    FULL_JSON=$(az containerapp revision list --name "$CONTAINER_APP" --resource-group "$RESOURCE_GROUP" -o json)
    echo "[DEBUG] Full revision list JSON: $FULL_JSON"
    # Try to extract the first revision name
    REVISION_NAME=$(echo "$FULL_JSON" | python3 -c 'import sys, json; j=json.load(sys.stdin); print(j[0]["name"] if j and "name" in j[0] else "")' 2>/dev/null)
    if [[ -z "$REVISION_NAME" ]]; then
      echo "[ERROR] Still could not determine a revision name. Please check your container app status."
      exit 1
    fi
    echo "[INFO] Fallback: Using first revision name: $REVISION_NAME"
  else
    echo "[INFO] Latest active revision detected: $REVISION_NAME"
  fi
fi


echo "[INFO] Restarting Azure Container App revision"
echo "       Resource Group : ${RESOURCE_GROUP}"
echo "       Container App  : ${CONTAINER_APP}"
echo "       Revision Name  : ${REVISION_NAME}"

if ! command -v az >/dev/null 2>&1; then
  echo "[ERROR] Azure CLI 'az' not found in PATH. Install from https://learn.microsoft.com/cli/azure/install-azure-cli" >&2
  exit 127
fi

# Ensure user is logged in
if ! az account show >/dev/null 2>&1; then
  echo "[INFO] Not logged in. Attempting 'az login'..."
  az login || { echo "[ERROR] az login failed" >&2; exit 1; }
fi

# Ensure the containerapp extension exists
if ! az extension show --name containerapp >/dev/null 2>&1; then
  echo "[INFO] 'containerapp' extension not found. Installing..."
  az extension add --name containerapp || {
    echo "[ERROR] Failed to install 'containerapp' extension." >&2
    exit 1
  }
fi



echo "[STEP] Restarting revision..."
if az containerapp revision restart --name "${CONTAINER_APP}" --resource-group "${RESOURCE_GROUP}" --revision "$REVISION_NAME"; then
  echo "[SUCCESS] Container app revision '$REVISION_NAME' restart completed."
else
  echo "[ERROR] Failed to restart container app revision '$REVISION_NAME'." >&2
  exit 1
fi

