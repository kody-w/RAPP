#!/usr/bin/env bash

cat >&2 <<'EOF'
rapp_swarm/provision-twin.sh: 410 Gone

Legacy Tier-2 provisioning is blocked by RAPP1_DEPLOYMENT_GUARD.json.
No cloud resources were created and no code was published.

Maintainers: see RAPP1_STATUS.md.
EOF

exit 78
