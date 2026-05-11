#!/usr/bin/env bash
# RAPP Brainstem — project-local installer shim (macOS / Linux).
#
# One-liner:
#     curl -fsSL https://kody-w.github.io/RAPP/installer/here.sh | bash
#
# Mirror of installer/here.ps1 for the bash side. Exports the `here` env
# var (install.sh reads it as a local-mode trigger) and runs the real
# installer.
#
# Equivalent to:
#     curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | here=1 bash
#     curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- HERE
#     curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --here
#
# Recommended one-URL pair:
#     curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash   # global
#     curl -fsSL https://kody-w.github.io/RAPP/installer/here.sh    | bash   # local

set -e
export here=1
exec bash -c "curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | here=1 bash"
