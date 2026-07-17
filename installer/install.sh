#!/usr/bin/env bash
printf '%s\n' \
    "installer/install.sh: 410 Gone" \
    "" \
    "No complete target-owned lock covers the immutable source tree and every" \
    "executable or dependency input. This installer therefore refuses to fetch," \
    "verify, install, or execute any release. There is no tag-based fallback." \
    "" \
    "No pinned kernel byte was changed. Maintainers: see RAPP1_STATUS.md." >&2
exit 78
