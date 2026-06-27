#!/usr/bin/env bash
# bootstrap.sh — stand up the repo-independent RAPP brainstem from the PUBLIC
# RAPP Cave, from nothing, in one command. The cave is a PUBLIC front door:
# anyone can pull the egg with plain curl — no GitHub auth, no collaborator gate.
#
# Public one-liner (anybody, anywhere):
#
#   curl -fsSL https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/bootstrap.sh | bash
#
# What it does, touching the grail repo ZERO times:
#   1. verify Python (no gh needed)
#   2. pull cubby-rapp-installer.egg from the public cave with plain curl
#      (raw.githubusercontent.com, falling back to the Pages mirror)
#   3. extract the pure-stdlib hatch.py FROM the egg (always in sync)
#   4. hatch → ~/.brainstem/cubbies/rapp-installer/ + build venv + launch serve.py
set -euo pipefail

# Public raw base (default) + Pages fallback. Both HTTPS only.
EGG_URL_RAW="${RAPP_CAVE_EGG_URL:-https://raw.githubusercontent.com/kody-w/RAPP/main/cave/rapplications/rapp-installer/cubby-rapp-installer.egg}"
EGG_URL_PAGES="${RAPP_CAVE_EGG_URL_PAGES:-https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/cubby-rapp-installer.egg}"
EGG_NAME="cubby-rapp-installer.egg"
PORT="${PORT:-7077}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

say() { printf '\033[36m[bootstrap]\033[0m %s\n' "$*"; }
die() { printf '\033[31m[bootstrap] %s\033[0m\n' "$*" >&2; exit 1; }

# 1. prerequisites ----------------------------------------------------------
command -v curl >/dev/null 2>&1 || die "curl not found. Install curl first."
PY="$(command -v python3.11 || command -v python3.12 || command -v python3.13 || command -v python3 || true)"
[ -n "$PY" ] || die "Python 3 not found. Install Python 3.11+ first."
say "curl ✓   python ✓ ($PY)"

# 2. pull the egg from the public cave (plain curl — no auth) ---------------
EGG="$WORK/$EGG_NAME"
case "$EGG_URL_RAW$EGG_URL_PAGES" in *http://*) die "refusing plaintext http:// egg URL (MITM risk) — use https://";; esac
say "pulling $EGG_NAME from the public cave (no auth needed)…"
if curl -fsSL "$EGG_URL_RAW" -o "$EGG" 2>/dev/null && [ -s "$EGG" ]; then
  say "got it from raw.githubusercontent.com"
else
  say "raw fetch failed — falling back to the Pages mirror…"
  curl -fsSL "$EGG_URL_PAGES" -o "$EGG" \
    || die "could not fetch the egg from the public cave. Check your network and that the cave is published."
fi
[ -s "$EGG" ] || die "fetched egg is empty"
say "egg: $(wc -c < "$EGG" | tr -d ' ') bytes"

# 3. extract the hatcher straight out of the egg (single source of truth) ----
HATCH="$WORK/hatch.py"
"$PY" - "$EGG" "$HATCH" <<'PY' || die "could not extract hatch.py from the egg"
import sys, zipfile
egg, out = sys.argv[1], sys.argv[2]
open(out, "wb").write(zipfile.ZipFile(egg).read("cubby/rapplications/rapp-installer/hatch.py"))
PY
[ -s "$HATCH" ] || die "could not extract hatch.py from the egg"

# 4. hatch (build venv + lay down files), clean up, then launch from the cubby
say "hatching the egg → ~/.brainstem/cubbies/rapp-installer/ (grail untouched)…"
"$PY" "$HATCH" "$EGG"
CUBBY="$HOME/.brainstem/cubbies/rapp-installer"
SERVE="$CUBBY/rapplications/rapp-installer/serve.py"
VENV_PY="$HOME/.brainstem/venv/bin/python"
[ -x "$VENV_PY" ] || VENV_PY="$PY"
[ -f "$SERVE" ] || die "hatch finished but serve.py missing at $SERVE"
rm -rf "$WORK"; trap - EXIT            # clean the temp dir before we hand off (exec replaces us)
say "launching → http://localhost:$PORT"
exec env PORT="$PORT" "$VENV_PY" "$SERVE"
