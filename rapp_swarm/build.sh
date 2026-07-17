#!/usr/bin/env bash

cat >&2 <<'EOF'
rapp_swarm/build.sh: 410 Gone

Legacy Tier-2 packaging is blocked by RAPP1_DEPLOYMENT_GUARD.json.
No files were generated, removed, copied, or prepared for deployment.

Maintainers: see RAPP1_STATUS.md.
EOF

exit 78
