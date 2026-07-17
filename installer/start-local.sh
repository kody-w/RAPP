#!/usr/bin/env bash
cat >&2 <<'EOF'
installer/start-local.sh: 410 Gone

This launcher referenced removed local web and swarm paths. It is retired and
starts no process. Use the pinned Tier 1 brainstem entrypoint after install.
EOF
exit 78
