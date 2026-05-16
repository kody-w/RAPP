#!/usr/bin/env bash
#
# kody-w/RAPP — thin grail re-fetcher (Mirror Spec compliant)
#
# This repo mirrors the grail kernel at kody-w/rapp-installer. The actual
# install logic lives in grail, so this script re-fetches grail's installer
# on every run and pipes it to bash. The mirror's installer cannot drift,
# because it does not *contain* the install logic.
#
#   curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
#
# Pass --rappter to also hatch the rappter-distro (full-bodied organism)
# after the kernel install completes:
#
#   curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --rappter
#
# Any other args (e.g. --here, --local) pass straight through to grail.
#
# Mirror Spec: https://kody-w.github.io/RAPP/pages/vault/Architecture/Mirror%20Spec
#
set -e

GRAIL_INSTALLER_URL="https://raw.githubusercontent.com/kody-w/rapp-installer/main/install.sh"
RAPPTER_DISTRO_URL="https://raw.githubusercontent.com/kody-w/rappter-distro/main/install.sh"

# Strip --rappter from passthrough args (grail doesn't know about it)
HATCH_RAPPTER=0
PASSTHROUGH=()
for arg in "$@"; do
    case "$arg" in
        --rappter|--with-rappter) HATCH_RAPPTER=1 ;;
        *) PASSTHROUGH+=("$arg") ;;
    esac
done

# Run grail's installer
curl -fsSL "$GRAIL_INSTALLER_URL" | bash -s -- "${PASSTHROUGH[@]}"

# Optionally hatch the rappter-distro on top
if [ "$HATCH_RAPPTER" = "1" ]; then
    echo ""
    echo "  --rappter requested → hatching rappter-distro..."
    echo ""
    curl -fsSL "$RAPPTER_DISTRO_URL" | bash
fi
