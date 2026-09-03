#!/bin/bash
# rapp_swarm/provision-twin-lite.sh — minimal cloud deploy for a Twin Stack
# cloud estate. Skips creating a new Azure OpenAI deployment (cheap + avoids
# regional quota collisions); instead reuses the AZURE_OPENAI_* keys from
# the root .env (e.g., the existing rappter OpenAI).
#
# Provisions per twin:
#     rg-twin-<name>           resource group (free)
#     sttwin<hash>             Storage Account (LRS, ~few cents/mo)
#     twin-<name>              Function App (Flex Consumption, $0 idle)
#
# Then:
#     applies .env keys as appSettings
#     bash rapp_swarm/build.sh         (vendor swarm/* into _swarm/)
#     func azure functionapp publish    (deploy function_app.py)
#
#     bash rapp_swarm/provision-twin-lite.sh kody
#     bash rapp_swarm/provision-twin-lite.sh molly
#
# Tear down:
#     az group delete --name rg-twin-kody --yes --no-wait

# Historical source provenance (fullest known implementation).
# commit: 4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6
# blob: 895ddfee47e57dd77a17d1bde4c9c7c80fbdfeab
# sha256: 2be7348ff7cf7cd6a8bdc7243dd9afd047f86dc8ca8dcb898d1bd8828336ade5
historical_provision_twin_lite() (
set -e
set -o pipefail

NAME="${1:-}"
[ -z "$NAME" ] && { echo "usage: $0 <twin-name>"; exit 2; }
NAME=$(echo "$NAME" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9')
[ -z "$NAME" ] && { echo "twin-name must contain [a-z0-9]"; exit 2; }

SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-3d0e6986-1b31-4189-a394-b3289d54efb0}"
LOCATION="${LOCATION:-eastus2}"

# Stable identifiers
RG="rg-twin-${NAME}"
HASH=$(printf '%s' "$NAME" | shasum | cut -c1-6)
STORAGE_ACCT="sttwin${NAME}${HASH}"     # ≤24 chars, lowercase
APP_NAME="twin-${NAME}-${HASH}"

cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"

command -v az   >/dev/null || { echo "✗ install: brew install azure-cli"; exit 1; }
command -v func >/dev/null || { echo "✗ install: brew tap azure/functions && brew install azure-functions-core-tools@4"; exit 1; }

# ── 1. Login + subscription ────────────────────────────────────────────

if ! az account show >/dev/null 2>&1; then
    az login >/dev/null
fi
az account set --subscription "$SUBSCRIPTION_ID"
echo "▶ Subscription: $(az account show --query name -o tsv)"
echo "▶ Tenant:       $(az account show --query tenantId -o tsv)"

# ── 2. Resource group ──────────────────────────────────────────────────

echo "▶ Ensuring $RG in $LOCATION"
az group create --name "$RG" --location "$LOCATION" \
    --tags "twin=$NAME" "stack=TwinStack" "owner=wildhaven-ai-homes" \
    --output none

# ── 3. Storage account ─────────────────────────────────────────────────

echo "▶ Creating Storage Account $STORAGE_ACCT"
az storage account create \
    --name "$STORAGE_ACCT" --resource-group "$RG" --location "$LOCATION" \
    --sku Standard_LRS --kind StorageV2 \
    --allow-blob-public-access false --min-tls-version TLS1_2 \
    --output none

# ── 4. Function App (Consumption Y1 — broadly available, $0 idle) ─────
# Using Consumption (Linux) instead of Flex to avoid the Flex preview
# requirements (Flex needs a separate App Service Plan + special storage
# config that's overkill for a single-twin smoke test).

echo "▶ Creating Function App $APP_NAME (Consumption Linux, Python 3.11)"
az functionapp create \
    --name "$APP_NAME" --resource-group "$RG" \
    --storage-account "$STORAGE_ACCT" \
    --consumption-plan-location "$LOCATION" \
    --runtime python --runtime-version 3.11 \
    --functions-version 4 \
    --os-type Linux \
    --output none

# ── 5. App settings from .env ──────────────────────────────────────────

ENV_FILE="$ROOT/.env"
SETTINGS=("BRAINSTEM_HOME=/tmp/.rapp-swarm" "TWIN_NAME=$NAME")
if [ -f "$ENV_FILE" ]; then
    while IFS='=' read -r k v; do
        [ -z "$k" ] && continue
        case "$k" in '#'*) continue;; esac
        v="${v%\"}"; v="${v#\"}"; v="${v%\'}"; v="${v#\'}"
        case "$k" in
            AZURE_OPENAI_API_KEY|AZURE_OPENAI_ENDPOINT|AZURE_OPENAI_DEPLOYMENT| \
            AZURE_OPENAI_DEPLOYMENT_NAME|AZURE_OPENAI_API_VERSION| \
            OPENAI_API_KEY|ANTHROPIC_API_KEY|ASSISTANT_NAME| \
            CHARACTERISTIC_DESCRIPTION|USE_CLOUD_STORAGE)
                [ -n "$v" ] && SETTINGS+=("$k=$v")
                ;;
        esac
    done < "$ENV_FILE"
fi
echo "▶ Setting ${#SETTINGS[@]} app settings"
az functionapp config appsettings set \
    --name "$APP_NAME" --resource-group "$RG" \
    --settings "${SETTINGS[@]}" \
    --output none

# CORS — let the brainstem hatch page reach this endpoint
az functionapp cors add --name "$APP_NAME" --resource-group "$RG" \
    --allowed-origins "https://kody-w.github.io" "http://localhost:8000" "http://127.0.0.1:8000" \
    --output none 2>/dev/null || true

# ── 6. Vendor swarm core + publish ─────────────────────────────────────

echo "▶ Vendoring swarm core"
bash "$(pwd)/build.sh"

echo "▶ Publishing function_app.py to $APP_NAME (this takes 1-2 min)"
func azure functionapp publish "$APP_NAME" --python --build remote

# ── 7. Final report ────────────────────────────────────────────────────

URL="https://${APP_NAME}.azurewebsites.net"
cat <<EOF

════════════════════════════════════════════════════════════════════
  ✓ Twin provisioned (lite): $NAME
════════════════════════════════════════════════════════════════════
  Resource group:    $RG
  Function App:      $APP_NAME
  URL:               $URL
  Region:            $LOCATION
  Azure OpenAI:      reused from root .env (no new deployment)

  Health check:      curl $URL/api/health?deep=true
  LLM provider:      curl $URL/api/llm/status

  Hatch ${NAME^}'s cloud:
    1. https://kody-w.github.io/RAPP/rapp_brainstem/web/onboard/
    2. Endpoint = $URL
    3. Click "${NAME^}'s cloud" → 🚀 Push to endpoint

  Tear down:
    az group delete --name $RG --yes --no-wait
EOF
)

print_plan() {
    printf '%s\n' \
        '{"schema":"rapp-swarm-deployment-plan/1.0","mode":"plan","variant":"lite","target":"azure-twin-estate","resources":["resource-group","storage-account","function-app"],"reuse_openai_configuration":true,"publish":false,"historical_source_commit":"4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6","effects":[]}' \
        'No Azure login, subscription selection, resource creation, environment read, vendoring, publish, or CORS mutation occurs in plan mode.'
}

refuse_deploy() {
    printf '%s\n' \
        '{"schema":"rapp-effect-refusal/1.0","operation":"provision-twin-lite","code":"authenticated-registry-unavailable","effects_started":false,"requirements":["reviewed-dependency-injection","exact-target-receipt","authenticated-fresh-section-13-evidence"]}' \
        'Current authority cannot authenticate a deployment target; refusal occurs before az, func, build.sh, or credential access.' >&2
    return 78
}

if [[ "${BASH_SOURCE[0]}" != "$0" ]]; then
    unset -f historical_provision_twin_lite print_plan refuse_deploy
    return 0
fi

case "${1:-plan}" in
    plan|--plan|inspect|--inspect|check|--check)
        print_plan
        ;;
    deploy|--deploy|apply|--apply|run|--run)
        refuse_deploy
        ;;
    help|-h|--help)
        printf '%s\n' \
            'Usage: provision-twin-lite.sh [--plan|--inspect|--check|--deploy] [twin-name]' \
            'Historical usage retained inside historical_provision_twin_lite().' \
            'Default: deterministic read-only Azure resource plan.' \
            '--deploy requires reviewed dependency injection, an exact target receipt,' \
            'and authenticated fresh RAPP/1 section-13 evidence; unavailable here.'
        ;;
    *)
        printf 'Unknown mode: %s\n' "$1" >&2
        exit 2
        ;;
esac
