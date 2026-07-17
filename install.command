#!/usr/bin/env bash
cat >&2 <<'EOF'
install.command: 410 Gone

The legacy macOS network passthrough is retired. It will not fetch or execute
mutable installer bytes. No replacement is active without a complete lock.
EOF
exit 78
