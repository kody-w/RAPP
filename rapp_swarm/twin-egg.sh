#!/usr/bin/env bash

set -eu

cat >&2 <<'EOF'
410 Gone: the contained Twin Stack egg executable is retired.
RAPP/1 rev-5 has no ratified section 9 mapping for this aggregate shape, and
the contained rapp_swarm runtime must not package, inspect, or restore it.
See RAPP1_STATUS.md.
EOF
exit 78
