#!/usr/bin/env bash
cat >&2 <<'EOF'
install.sh: 410 Gone

This legacy root passthrough is retired because it selected mutable upstream
bytes. No replacement installer is active without a complete input lock.
EOF
exit 78
