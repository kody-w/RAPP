#!/usr/bin/env bash
cat >&2 <<'EOF'
install.command: 410 Gone

The legacy macOS network passthrough is retired. It will not fetch or execute
mutable installer bytes. Use installer/install.sh from a verified checkout.
EOF
exit 78
