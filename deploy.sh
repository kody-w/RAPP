#!/usr/bin/env bash
cat >&2 <<'EOF'
deploy.sh: 410 Gone

Target-owned Tier 2 provisioning is retired. No Azure login, resource group,
deployment, Function App, storage account, or model resource was created.
EOF
exit 78
