#!/usr/bin/env bash
cat >&2 <<'EOF'
install.sh: 410 Gone

This legacy root passthrough is retired because it selected mutable upstream
bytes. Use the target-owned pinned installer at installer/install.sh.
EOF
exit 78
