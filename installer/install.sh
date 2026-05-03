#!/usr/bin/env bash
set -e

# RAPP Brainstem Installer (minimal — sacred OOTB simplicity).
#
#   curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
#
# Project-local (own dir, own port, own agents/, gitignored alongside repo):
#   curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --here
#
# Pin to a specific tagged release:
#   BRAINSTEM_VERSION=0.15.9 curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
#
# Anything fancier — snapshots, kernel upgrades, peer registration,
# autostart on login — is delivered by the brainstem itself, on demand,
# via /api/lifecycle/* and the LLM's handshake. The shell side stays
# minimal on purpose. If you want the brainstem to upgrade itself, ask
# it after install — don't grow this file.

# ── Color setup ──────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

# ── Mode selection (global default vs --here) ────────────────────────
LOCAL_MODE=0
for arg in "$@"; do
    case "$arg" in --here|--local) LOCAL_MODE=1 ;; esac
done
[ "${BRAINSTEM_LOCAL:-0}" = "1" ] && LOCAL_MODE=1
case "${RAPP_INSTALL_MODE:-}" in
    local)  LOCAL_MODE=1 ;;
    global) LOCAL_MODE=0 ;;
esac

# ── Agent-assist handshake ───────────────────────────────────────────
# When an LLM (Claude Code, Copilot CLI, etc.) runs the installer with
# RAPP_INSTALL_ASSIST=1 and no explicit mode chosen, print a structured
# question and exit. The agent relays the choice to the user and re-
# invokes with RAPP_INSTALL_MODE=global|local.
_mode_chosen=0
[ "$LOCAL_MODE" = "1" ] && _mode_chosen=1
[ -n "${RAPP_INSTALL_MODE:-}" ] && _mode_chosen=1
if [ "${RAPP_INSTALL_ASSIST:-0}" = "1" ] && [ "$_mode_chosen" = "0" ]; then
    cat << 'HANDSHAKE'
<<<RAPP_INSTALLER_HANDSHAKE v=1>>>

RAPP Brainstem — local-first AI agent server, powered by GitHub Copilot.

QUESTION FOR THE USER — pick one of two install modes:

  GLOBAL (default) — one brainstem at ~/.brainstem, port 7071.
    Re-invoke as (env on the bash side of the pipe):
      curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | RAPP_INSTALL_MODE=global bash

  LOCAL — project-scoped brainstem at ./.brainstem, picks its own port.
    Re-invoke from the target project directory:
      curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | RAPP_INSTALL_MODE=local bash

NOTE — env must be on the BASH side of the pipe, not the curl side.
After install, ask the brainstem to upgrade itself, snapshot itself,
or register with peers — those operations live behind /api/lifecycle/*
and run only after the brainstem confirms with you.

<<<END_RAPP_INSTALLER_HANDSHAKE>>>
HANDSHAKE
    exit 0
fi

# ── Path resolution ──────────────────────────────────────────────────
if [ "$LOCAL_MODE" = "1" ]; then
    BRAINSTEM_HOME="$(pwd)/.brainstem"
else
    BRAINSTEM_HOME="$HOME/.brainstem"
fi
SRC_DIR="$BRAINSTEM_HOME/src"
KERNEL_DIR="$SRC_DIR/rapp_brainstem"
VENV_DIR="$BRAINSTEM_HOME/venv"
REPO_URL="https://github.com/kody-w/RAPP.git"

# ── Pin selection ────────────────────────────────────────────────────
# Default: track main HEAD. Set BRAINSTEM_VERSION=X.Y.Z to pin to a
# tagged release (frozen, no surprises after a bad merge).
PIN_REF="main"
if [ -n "${BRAINSTEM_VERSION:-}" ]; then
    PIN_REF="brainstem-v${BRAINSTEM_VERSION}"
fi

# ── Banner ───────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}  🧠 RAPP Brainstem${NC}"
echo "  Local-first AI agent server · powered by GitHub Copilot"
[ "$LOCAL_MODE" = "1" ] && echo "  Mode: project-local (./.brainstem)"
[ -n "${BRAINSTEM_VERSION:-}" ] && echo "  Pin:  brainstem-v${BRAINSTEM_VERSION}"
echo ""

# ── Prereq check ─────────────────────────────────────────────────────
need() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}✗ missing prerequisite: $1${NC}"
        echo "  install $1 and re-run the one-liner."
        exit 1
    fi
}
need git
need python3

# ── Clone (sparse — only rapp_brainstem/ + installer/) ───────────────
mkdir -p "$BRAINSTEM_HOME"
if [ -d "$SRC_DIR/.git" ]; then
    echo -e "${CYAN}▸ getting latest...${NC}"
    git -C "$SRC_DIR" fetch -q --depth 1 origin "$PIN_REF" || {
        echo -e "${RED}✗ git fetch failed for ref ${PIN_REF}${NC}"; exit 1; }
    git -C "$SRC_DIR" checkout -q FETCH_HEAD
else
    echo -e "${CYAN}▸ getting code...${NC}"
    rm -rf "$SRC_DIR"
    git clone -q --depth 1 --branch "$PIN_REF" --filter=blob:none --no-checkout "$REPO_URL" "$SRC_DIR" || {
        echo -e "${RED}✗ git clone failed for ref ${PIN_REF}${NC}"; exit 1; }
    git -C "$SRC_DIR" sparse-checkout init --cone
    git -C "$SRC_DIR" sparse-checkout set rapp_brainstem installer
    git -C "$SRC_DIR" checkout -q
fi

if [ ! -f "$KERNEL_DIR/brainstem.py" ]; then
    echo -e "${RED}✗ clone succeeded but $KERNEL_DIR/brainstem.py is missing${NC}"
    exit 1
fi

# ── Venv + deps (silent on the happy path) ───────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
echo -e "${CYAN}▸ installing dependencies...${NC}"
"$VENV_DIR/bin/pip" install -q --upgrade pip
"$VENV_DIR/bin/pip" install -q -r "$KERNEL_DIR/requirements.txt"

# ── .env bootstrap (preserve any existing .env) ──────────────────────
if [ ! -f "$KERNEL_DIR/.env" ] && [ -f "$KERNEL_DIR/.env.example" ]; then
    cp "$KERNEL_DIR/.env.example" "$KERNEL_DIR/.env"
fi

# ── Pick the launcher: utils/boot.py if it exists (wires organs, senses,
# /web/ static, /api/snapshot/*, /api/senses/*, /api/workspace/*); fall
# back to bare brainstem.py for older clones that predate the wrapper.
# brainstem.py is the kernel; boot.py is the launcher (Article XXXIII).
LAUNCHER="brainstem.py"
if [ -f "$KERNEL_DIR/utils/boot.py" ]; then
    LAUNCHER="utils/boot.py"
fi

# ── --here / no-autostart mode: print the start command and exit ─────
# Power-user mode. The user knows what they're doing; they want a path.
if [ "$LOCAL_MODE" = "1" ] || [ "${RAPP_NO_AUTOSTART:-0}" = "1" ]; then
    echo ""
    echo -e "${GREEN}✓ ready${NC}  ${VENV_DIR}/bin/python ${KERNEL_DIR}/${LAUNCHER}"
    echo ""
    exit 0
fi

# ── Global mode: launch + open browser. Magic. ───────────────────────
PORT="${PORT:-7071}"
LOG_FILE="$BRAINSTEM_HOME/brainstem.log"
echo -e "${CYAN}▸ starting your brainstem...${NC}"
( cd "$KERNEL_DIR" && PORT=$PORT nohup "$VENV_DIR/bin/python" "$LAUNCHER" > "$LOG_FILE" 2>&1 & )

# Brief health check (non-fatal — slow boots still succeed)
sleep 2
if command -v curl &> /dev/null && curl -fsS "http://localhost:$PORT/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ ready at http://localhost:$PORT${NC}"
else
    echo -e "${YELLOW}△ still starting — give it a few more seconds${NC}"
fi

if [ "${RAPP_NO_BROWSER:-0}" != "1" ]; then
    if command -v open &> /dev/null; then
        open "http://localhost:$PORT" 2>/dev/null || true
    elif command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:$PORT" 2>/dev/null || true
    fi
fi

echo ""
