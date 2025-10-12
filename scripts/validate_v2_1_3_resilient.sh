#!/usr/bin/env bash
# Validation script for v2.1.3-resilient deployment
# Usage: export APP=nl2sql-teams-bot RG=AQ-BOT-RG ACR=nl2sqlacr1760120779 && ./scripts/validate_v2_1_3_resilient.sh
set -euo pipefail

: "${APP:?APP (Container App name) not set}"
: "${RG:?RG (resource group) not set}"
: "${ACR:?ACR registry name not set}"

IMAGE_TAG=v2.1.3-resilient
IMAGE="$ACR.azurecr.io/nl2sql-teams-bot:$IMAGE_TAG"

banner() { echo -e "\n==== $* ===="; }

banner "Switching image (if not already)"
az containerapp update -n "$APP" -g "$RG" --image "$IMAGE" --revision-suffix v213resilient || true

banner "Listing revisions"
az containerapp revision list -n "$APP" -g "$RG" --query "[].{name:name,traffic:trafficWeight,healthy:healthState}" -o table

FQDN=$(az containerapp show -n "$APP" -g "$RG" --query properties.configuration.ingress.fqdn -o tsv)

banner "Health check"
curl -fsS "https://$FQDN/healthz" | jq '.' || (echo "Health endpoint failed" && exit 1)

banner "Tail recent logs (showing up to 120 lines)"
az containerapp logs show -n "$APP" -g "$RG" --tail 120 || true

banner "Agent creation log scan"
az containerapp logs show -n "$APP" -g "$RG" --tail 400 | grep -Ei "created.*(intent|sql|insights).*agent" || echo "(No explicit creation lines matched — ensure logging present)"

banner "Missing agent error scan (should be zero)"
if az containerapp logs show -n "$APP" -g "$RG" --tail 400 | grep -F "No assistant found"; then
  echo "Detected missing agent errors (unexpected on clean start)."; exit 2
else
  echo "No missing agent errors detected."
fi

echo -e "\nValidation base pass. Run functional queries via Teams now: 'Count customers by state' then follow-up insights prompt."