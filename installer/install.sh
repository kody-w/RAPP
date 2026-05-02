#!/bin/bash
set -e

# RAPP Brainstem Installer
# Usage:
#   curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
#
# Project-local install (scoped to the current directory, own port, own
# agents/, never committed — runs alongside any global brainstem):
#   cd ~/my-project
#   curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --here
#
# Pin to a specific released version (fallback if a newer release breaks):
#   BRAINSTEM_VERSION=0.5.1 curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
#
# Every VERSION bump in the repo is tagged `brainstem-vX.Y.Z` and that
# tag's tree is immutable — the install will check out exactly that
# commit, no matter what main looks like later. See VERSIONS.md.

# ── Install mode: global (default) vs. project-local ────────────────
# One-liner stays generic:
#   curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
# → installs globally at ~/.brainstem.
#
# To install project-local (./.brainstem, own port, own agents, gitignored):
#   curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash -s -- --here
# or via env on the BASH side of the pipe (env must apply to bash, not curl):
#   curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | BRAINSTEM_LOCAL=1 bash
#   curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | RAPP_INSTALL_MODE=local bash
#
# AGENT HANDSHAKE: When an agent (Copilot CLI, Claude Code, etc.) runs
# this installer, it sets RAPP_INSTALL_ASSIST=1 on the bash side:
#   curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | RAPP_INSTALL_ASSIST=1 bash
# The script then prints a structured prompt describing the two modes
# and exits — the agent relays the choice to the user and re-invokes
# with RAPP_INSTALL_MODE=global|local. This way the one-liner stays
# generic: humans running it directly get the global default silently;
# agents stop and ask first.

LOCAL_MODE=0
for arg in "$@"; do
    case "$arg" in
        --here|--local) LOCAL_MODE=1 ;;
    esac
done
[ "${BRAINSTEM_LOCAL:-0}" = "1" ] && LOCAL_MODE=1
case "${RAPP_INSTALL_MODE:-}" in
    local)  LOCAL_MODE=1 ;;
    global) LOCAL_MODE=0 ;;
esac

# Agent-assist handshake: fire only if an agent asked for assist AND
# no explicit mode has been chosen yet.
_mode_chosen=0
[ "$LOCAL_MODE" = "1" ] && _mode_chosen=1
[ -n "${RAPP_INSTALL_MODE:-}" ] && _mode_chosen=1
if [ "${RAPP_INSTALL_ASSIST:-0}" = "1" ] && [ "$_mode_chosen" = "0" ]; then
    cat << 'HANDSHAKE'
<<<RAPP_INSTALLER_HANDSHAKE v=1>>>

RAPP Brainstem — local-first AI agent server, powered by GitHub Copilot.
Full skill manifest (learnable context, agent protocol, architecture):
  https://kody-w.github.io/RAPP/pages/docs/skill.md
Fetch that once and cache it as your skill for rapp-brainstem.

QUESTION FOR THE USER — pick one of two install modes:

  GLOBAL (recommended default) — one brainstem for the whole machine.
    Installs at ~/.brainstem. Runs on port 7071. Has a `brainstem`
    CLI and auto-starts on login.
    Re-invoke as (env on the bash side of the pipe):
      curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | RAPP_INSTALL_MODE=global bash

  LOCAL — project-scoped brainstem for the current directory.
    Installs at ./.brainstem/. Picks its own port (7072+). No global
    CLI, no background service. Gitignored automatically. Runs
    alongside the global brainstem if one exists.
    Re-invoke as (from the target project directory, env on bash side):
      curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | RAPP_INSTALL_MODE=local bash

HEURISTIC — if the user is inside a specific project or repo and
mentioned isolation, suggest LOCAL. Otherwise suggest GLOBAL.

NOTE — env must be on the BASH side of the pipe, not the curl side.
`ENV=VAL curl ... | bash` sets ENV only for curl; bash never sees it.
`curl ... | ENV=VAL bash` is the working form.

<<<END_RAPP_INSTALLER_HANDSHAKE>>>
HANDSHAKE
    exit 0
fi

if [ "$LOCAL_MODE" = "1" ]; then
    BRAINSTEM_HOME="$(pwd)/.brainstem"
else
    BRAINSTEM_HOME="$HOME/.brainstem"
fi
BRAINSTEM_BIN="$HOME/.local/bin"
VENV_DIR="$BRAINSTEM_HOME/venv"
REPO_URL="https://github.com/kody-w/RAPP.git"
REMOTE_VERSION_URL="https://raw.githubusercontent.com/kody-w/RAPP/main/rapp_brainstem/VERSION"

# Pin selection (sources, in order):
#   1. BRAINSTEM_VERSION=X.Y.Z env var       → tag brainstem-vX.Y.Z (explicit pin)
#   2. RAPP_INSTALL_TRACK=main env var       → main HEAD (developer / unstable opt-in)
#   3. Default: latest brainstem-vX.Y.Z tag  → frozen release (production-safe)
#
# Defaulting to the latest tagged release rather than `main` HEAD prevents
# the "main was broken for 8 minutes and 200 users got it" failure mode.
# Releases are immutable; main is a moving target.
PIN_VERSION="${BRAINSTEM_VERSION:-}"
PIN_TAG=""
PIN_EXPLICIT=0  # 1 → user passed BRAINSTEM_VERSION; 0 → defaulted to latest tag
INSTALL_TRACK="${RAPP_INSTALL_TRACK:-release}"
if [ -n "$PIN_VERSION" ]; then
    PIN_TAG="brainstem-v${PIN_VERSION}"
    PIN_EXPLICIT=1
elif [ "$INSTALL_TRACK" != "main" ]; then
    # Resolve the latest brainstem-v* tag from the remote. Falls back to
    # main HEAD only if no tags exist (fresh repo, brand-new variant).
    LATEST_TAG="$(
        git ls-remote --tags --refs "$REPO_URL" 'brainstem-v*' 2>/dev/null \
            | awk -F/ '{print $NF}' \
            | sort -V \
            | tail -n1
    )"
    if [ -n "$LATEST_TAG" ]; then
        PIN_TAG="$LATEST_TAG"
        PIN_VERSION="${LATEST_TAG#brainstem-v}"
    fi
fi

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

read_input() {
    local prompt="$1" default="$2" result
    if [ -t 0 ]; then
        read -p "$prompt" result
    else
        read -p "$prompt" result < /dev/tty
    fi
    echo "${result:-$default}"
}

print_banner() {
    echo ""
    echo -e "${CYAN}"
    echo "  🧠 RAPP Brainstem"
    echo -e "${NC}"
    echo "  Portable · Shareable · Vibe Swarm Building Tool"
    echo "  Powered by GitHub Copilot — no API keys needed"
    echo ""
}

detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then echo "macos"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then echo "linux"
    else echo "unknown"
    fi
}

# Ensure Homebrew is on PATH — curl|bash sessions don't source shell profiles
ensure_brew_on_path() {
    if command -v brew &> /dev/null; then return 0; fi
    if [[ -x "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -x "/usr/local/bin/brew" ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
}

find_python() {
    for cmd in python3.11 python3.12 python3.13 python3; do
        if command -v "$cmd" &> /dev/null; then
            version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null) || continue
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [[ -n "$major" && -n "$minor" ]] && [ "$major" -ge 3 ] 2>/dev/null && [ "$minor" -ge 11 ] 2>/dev/null; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    if [[ "$(detect_os)" == "macos" ]]; then
        for p in /opt/homebrew/bin/python3.11 /usr/local/bin/python3.11 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12; do
            if [[ -x "$p" ]]; then echo "$p"; return 0; fi
        done
    fi
    return 1
}

install_python() {
    local os_type=$(detect_os)
    echo -e "  ${YELLOW}Installing Python 3.11...${NC}"
    if [[ "$os_type" == "macos" ]]; then
        if ! command -v brew &> /dev/null; then
            echo -e "  ${YELLOW}Installing Homebrew first...${NC}"
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            if [[ -f "/opt/homebrew/bin/brew" ]]; then eval "$(/opt/homebrew/bin/brew shellenv)"; fi
        fi
        brew install python@3.11
        export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
    elif [[ "$os_type" == "linux" ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv python3-pip
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y python3.11 python3-pip
        else
            echo -e "  ${RED}✗${NC} Cannot auto-install Python 3.11 on this system"
            echo "    Install manually from https://python.org"
            exit 1
        fi
    fi
}

# Compare two semver strings. Returns 0 if $1 > $2, 1 otherwise.
version_gt() {
    local IFS=.
    local i a=($1) b=($2)
    for ((i=0; i<${#a[@]}; i++)); do
        local va=${a[i]:-0}
        local vb=${b[i]:-0}
        if (( va > vb )); then return 0; fi
        if (( va < vb )); then return 1; fi
    done
    return 1  # equal
}

check_for_upgrade() {
    local version_file="$BRAINSTEM_HOME/src/rapp_brainstem/VERSION"

    # No existing install — always proceed
    if [ ! -f "$version_file" ]; then
        return 0
    fi

    local local_version
    local_version=$(cat "$version_file" 2>/dev/null | tr -d '[:space:]')

    # Fetch remote version
    local remote_version
    remote_version=$(curl -fsSL "$REMOTE_VERSION_URL" 2>/dev/null | tr -d '[:space:]') || true

    if [[ -z "$remote_version" ]]; then
        echo -e "  ${YELLOW}⚠${NC} Could not check remote version — upgrading anyway"
        return 0
    fi

    echo -e "  Local version:  ${CYAN}${local_version}${NC}"
    echo -e "  Remote version: ${CYAN}${remote_version}${NC}"

    if [[ "$local_version" == "$remote_version" ]]; then
        echo ""
        echo -e "  ${GREEN}✓ Already up to date (v${local_version})${NC}"
        echo ""
        return 1  # no upgrade needed
    fi

    if version_gt "$remote_version" "$local_version"; then
        echo -e "  ${YELLOW}⬆${NC} Upgrade available: ${local_version} → ${remote_version}"
        return 0
    fi

    echo -e "  ${GREEN}✓ Already up to date (v${local_version})${NC}"
    echo ""
    return 1
}

check_prereqs() {
    echo "Checking prerequisites..."

    # On macOS, ensure Homebrew is on PATH (curl|bash doesn't source shell profiles)
    if [[ "$(detect_os)" == "macos" ]]; then
        ensure_brew_on_path
    fi

    # Python 3.11+
    PYTHON_CMD=$(find_python) || true
    if [[ -n "$PYTHON_CMD" ]]; then
        version=$("$PYTHON_CMD" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        echo -e "  ${GREEN}✓${NC} Python $version ($PYTHON_CMD)"
    else
        echo -e "  ${YELLOW}⚠${NC} Python 3.11+ not found"
        install_python
        PYTHON_CMD=$(find_python) || true
        if [[ -z "$PYTHON_CMD" ]]; then
            echo -e "  ${RED}✗${NC} Failed to install Python 3.11"
            exit 1
        fi
        version=$("$PYTHON_CMD" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        echo -e "  ${GREEN}✓${NC} Python $version installed"
    fi
    export PYTHON_CMD

    # Git
    if command -v git &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} Git $(git --version | cut -d' ' -f3)"
    else
        echo -e "  ${YELLOW}⚠${NC} Git not found, installing..."
        if [[ "$(detect_os)" == "macos" ]]; then
            xcode-select --install 2>/dev/null || brew install git
        elif command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y git
        else
            echo -e "  ${RED}✗${NC} Git required — install from https://git-scm.com"
            exit 1
        fi
    fi

    # GitHub CLI (required for Copilot token auth)
    if command -v gh &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} GitHub CLI $(gh --version | head -1 | awk '{print $3}')"
    else
        echo -e "  ${YELLOW}⚠${NC} GitHub CLI not found, installing..."
        local os_type=$(detect_os)
        if [[ "$os_type" == "macos" ]]; then
            if command -v brew &> /dev/null; then
                brew install gh
            else
                echo -e "  ${YELLOW}⚠${NC} Installing Homebrew first..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                ensure_brew_on_path
                brew install gh
            fi
        elif [[ "$os_type" == "linux" ]]; then
            if command -v apt-get &> /dev/null; then
                (type -p wget >/dev/null || sudo apt-get install -y wget) \
                    && sudo mkdir -p -m 755 /etc/apt/keyrings \
                    && out=$(mktemp) && wget -nv -O"$out" https://cli.github.com/packages/githubcli-archive-keyring.gpg \
                    && cat "$out" | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
                    && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
                    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
                    && sudo apt-get update && sudo apt-get install -y gh
            elif command -v dnf &> /dev/null; then
                sudo dnf install -y 'dnf-command(config-manager)' \
                    && sudo dnf config-manager --add-repo https://cli.github.com/packages/rpm/gh-cli.repo \
                    && sudo dnf install -y gh
            else
                echo -e "  ${YELLOW}⚠${NC} Cannot auto-install GitHub CLI — install from https://cli.github.com"
            fi
        fi
        if command -v gh &> /dev/null; then
            echo -e "  ${GREEN}✓${NC} GitHub CLI installed"
        else
            echo -e "  ${YELLOW}!${NC} GitHub CLI not installed — install later from https://cli.github.com"
        fi
    fi
}

# Stage just rapp_brainstem/ from kody-w/RAPP into a throwaway directory.
# The caller copies the brainstem source out and discards the stage — the
# user's installed copy at ~/.brainstem/src/ is **plain files**, never a
# git clone. That decoupling is intentional: this directory is the user's
# experimental playground and clicking the "Open in VS Code" shortcut
# must not let an accidental commit-and-push leak edits back into the
# upstream RAPP repo. Re-running the one-liner is the only upgrade path.
stage_brainstem_framework() {
    local stage="$1"
    git clone --quiet --filter=blob:none --no-checkout "$REPO_URL" "$stage" || return 1
    git -C "$stage" sparse-checkout init --cone 2>/dev/null || true
    git -C "$stage" sparse-checkout set rapp_brainstem 2>/dev/null || true
    git -C "$stage" checkout --quiet main || return 1
    if [ -n "$PIN_TAG" ]; then
        git -C "$stage" checkout --quiet "$PIN_TAG" 2>/dev/null || \
            echo -e "  ${YELLOW}⚠${NC} Pin tag ${PIN_TAG} not found — staying on main"
    fi
}

# Run the framework's bond.py CLI. Always uses the freshest bond.py
# available — the staged one during a bond, the installed one otherwise.
# bond.py is stdlib-only by design so it works before the venv is built.
#
# Returns 2 if bond.py is unavailable (e.g. pinning to an older release
# that pre-dates the bonding lifecycle). Callers MUST tolerate that —
# the legacy backup/restore path is the safety net. Every call site
# guards with `|| true` so `set -e` doesn't abort the whole install when
# the older kernel can't run bond.
_run_bond() {
    local bond_root=""
    if [ -f "$STAGE/rapp_brainstem/utils/bond.py" ]; then
        bond_root="$STAGE/rapp_brainstem"
    elif [ -f "$BRAINSTEM_HOME/src/rapp_brainstem/utils/bond.py" ]; then
        bond_root="$BRAINSTEM_HOME/src/rapp_brainstem"
    else
        return 2
    fi
    (cd "$bond_root" && "$PYTHON_CMD" -m utils.bond "$@")
}

_bond_available() {
    [ -f "$STAGE/rapp_brainstem/utils/bond.py" ] || \
        [ -f "$BRAINSTEM_HOME/src/rapp_brainstem/utils/bond.py" ]
}

# Numeric semver compare. Returns 0 if $1 > $2.
_version_gt() {
    [ "$1" = "$2" ] && return 1
    local greater
    greater=$(printf '%s\n%s\n' "$1" "$2" | sort -V | tail -n1)
    [ "$greater" = "$1" ]
}

# Initialize the local git repo at ~/.brainstem/.bond/backups/.git the
# first time we lay down a backup. Once it exists, every bond auto-
# commits — `git log` becomes the lineage of the organism's evolution
# and `git checkout <sha>` is a working revert mechanism even after the
# sliding window has pruned the on-disk directory.
#
# The .gitignore is conservative: secrets (.env) and large blobs
# (pre-bond.egg) stay out of history. Custom agents, soul, rappid, and
# the bond log all get versioned. Identity files in git let `git log`
# read like a biography.
#
# All silent on failure. Git is required by the installer prereqs, but
# if it's somehow gone or the user revoked permissions, we still have
# the on-disk backup directory tier and the immutable emergency baseline.
_init_backup_git() {
    local backups_dir="$BRAINSTEM_HOME/.bond/backups"
    [ -d "$backups_dir" ] || mkdir -p "$backups_dir"

    # Already initialized? Nothing to do.
    if [ -d "$backups_dir/.git" ]; then
        return 0
    fi

    command -v git >/dev/null 2>&1 || return 0

    (
        cd "$backups_dir" || exit 0
        git init --quiet 2>/dev/null || exit 0
        # Local-only commits — never need a remote for this.
        # Use a stable identity so the user doesn't need git config set up.
        git config user.email "brainstem@local" 2>/dev/null || true
        git config user.name  "brainstem"        2>/dev/null || true
        # Some hosts default commit.gpgsign=true globally; the repo
        # creator may not have a key. Disable per-repo so we never
        # blow up on a sign attempt.
        git config commit.gpgsign false           2>/dev/null || true
        # Conservative ignore: secrets + large blobs out of history.
        # Sanitized soul/agents/rappid/bonds is what gets versioned.
        cat > .gitignore <<'GITIGNORE'
# Secrets — never commit. The on-disk backup keeps them; git is for
# non-sensitive history only.
**/.env
**/.copilot_session
**/.copilot_token

# Egg blobs — large, binary, already a self-contained backup. The
# on-disk pre-bond.egg is the canonical restore vehicle.
**/*.egg
GITIGNORE
        git add .gitignore 2>/dev/null || true
        git commit -m "init local backup history" --quiet 2>/dev/null || true
    )
}

# Commit the freshly-written backup directory to the local git repo so
# that even after the sliding window prunes it from disk, the contents
# survive in `git log`. Safe to call when git isn't available — it just
# no-ops.
_commit_backup_to_git() {
    local backup_dir="$1"
    [ -n "$backup_dir" ] || return 0
    [ -d "$backup_dir" ] || return 0
    local backups_dir="$BRAINSTEM_HOME/.bond/backups"
    [ -d "$backups_dir/.git" ] || return 0
    command -v git >/dev/null 2>&1 || return 0

    local rel
    rel=$(basename "$backup_dir")
    (
        cd "$backups_dir" || exit 0
        git add "$rel" 2>/dev/null || true
        # Skip the commit if there's nothing staged (e.g. .env-only
        # backups where every file was ignored).
        if git diff --cached --quiet 2>/dev/null; then
            return 0
        fi
        git commit -m "${rel}" --quiet 2>/dev/null || true
    )
}

# Sliding-window backup pruner. Keeps the last N pre-bond backups under
# ~/.brainstem/.bond/backups/ and removes older ones, so the directory
# doesn't grow without bound. N defaults to 5; user can override via
# BRAINSTEM_BACKUP_KEEP=10 (or BRAINSTEM_BACKUP_KEEP=0 to keep none —
# discouraged but supported). The static emergency baseline at
# ~/.brainstem/.bond/emergency-baseline/ is *never* touched by this.
_prune_backups() {
    local backups_dir="$BRAINSTEM_HOME/.bond/backups"
    [ -d "$backups_dir" ] || return 0
    local keep="${BRAINSTEM_BACKUP_KEEP:-5}"
    case "$keep" in
        ''|*[!0-9]*) keep=5 ;;
    esac
    # Newest-first by mtime; drop everything past index $keep.
    local count=0
    while IFS= read -r dir; do
        count=$((count + 1))
        if [ "$count" -gt "$keep" ]; then
            rm -rf "$dir" 2>/dev/null || true
        fi
    done < <(ls -1dt "$backups_dir"/*/ 2>/dev/null)
}

# Emergency baseline — the immutable "in case of catastrophic failure"
# snapshot. Set ONCE on first install (or first bond from a legacy
# install that predates this concept) and never overwritten by future
# bonds. Contains the absolute minimum to boot a working chat surface:
#
#   brainstem.py, basic_agent.py, soul.md, VERSION, requirements.txt,
#   start.sh, index.html
#
# `brainstem safe-mode` boots from this baseline regardless of whatever
# state the live src/ tree is in. Custom user agents are NOT included
# here — they live in the live agents/ dir and the per-bond backups.
# Refresh with: brainstem doctor refresh-emergency.
_seed_emergency_baseline() {
    local src_root="$1"
    local baseline="$BRAINSTEM_HOME/.bond/emergency-baseline"
    if [ -d "$baseline" ] && [ -f "$baseline/brainstem.py" ]; then
        return 0  # already seeded — never overwrite
    fi
    if [ ! -f "$src_root/brainstem.py" ]; then
        return 0  # nothing to copy from
    fi
    mkdir -p "$baseline/agents"
    for f in brainstem.py basic_agent.py soul.md VERSION requirements.txt start.sh start.ps1 index.html; do
        [ -f "$src_root/$f" ] && cp "$src_root/$f" "$baseline/$f" 2>/dev/null || true
    done
    # The agents/ subdir gets only basic_agent.py — emergency mode is
    # bare metal. User agents are NOT mirrored here (they're already
    # preserved in per-bond backups).
    if [ -f "$src_root/agents/basic_agent.py" ]; then
        cp "$src_root/agents/basic_agent.py" "$baseline/agents/basic_agent.py" 2>/dev/null || true
    elif [ -f "$src_root/basic_agent.py" ]; then
        cp "$src_root/basic_agent.py" "$baseline/agents/basic_agent.py" 2>/dev/null || true
    fi
    # Mark when the baseline was set so the user can tell how old it is.
    {
        echo "Created: $(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date)"
        [ -f "$src_root/VERSION" ] && echo "Version: $(cat "$src_root/VERSION" | tr -d '[:space:]')"
        echo ""
        echo "Static emergency baseline. Boots via: brainstem safe-mode"
        echo "Refresh via: brainstem doctor refresh-emergency"
    } > "$baseline/README.txt"
}

# Opt-in gate for upgrades. The kernel + user state are non-trivial to
# rebuild from scratch — the install one-liner must never silently
# overwrite an existing organism. Returns 0 to proceed, 1 to skip.
#
# Env var BRAINSTEM_UPGRADE=1 → confirmed, skip prompt.
# Interactive (TTY)           → prompt, default No.
# Piped without env var       → refuse, print exact opt-in command.
_confirm_upgrade() {
    local from="$1"
    local to="$2"

    if [ "${BRAINSTEM_UPGRADE:-}" = "1" ] || [ "${BRAINSTEM_UPGRADE:-}" = "yes" ] || [ "${BRAINSTEM_UPGRADE:-}" = "y" ]; then
        echo -e "  ${GREEN}✓${NC} BRAINSTEM_UPGRADE=1 — proceeding without prompt"
        return 0
    fi

    echo ""
    echo -e "  ${YELLOW}⬆${NC}  Upgrade available: v${from} → v${to}"
    echo ""
    echo "    The new framework will overlay your existing install."
    echo "    Custom agents, soul.md, .env, and state are preserved."
    echo "    A timestamped backup is saved to ~/.brainstem/.bond/backups/"
    echo "    so you can revert if anything breaks."
    echo ""

    if [ -t 0 ] && [ -t 1 ]; then
        # Interactive — prompt with default No
        local reply
        printf "  Proceed with upgrade? [y/N]: "
        read -r reply
        case "$reply" in
            y|Y|yes|YES) return 0 ;;
            *) echo -e "  ${GREEN}✓${NC} Keeping v${from} — no changes made"; return 1 ;;
        esac
    fi

    # Piped (curl | bash) — no TTY for read. Refuse to wipe silently.
    echo "  Re-run with BRAINSTEM_UPGRADE=1 to confirm:"
    echo ""
    echo "    BRAINSTEM_UPGRADE=1 curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash"
    echo ""
    echo -e "  ${GREEN}✓${NC} Keeping v${from} — no changes made"
    return 1
}

install_brainstem() {
    echo ""
    echo "Installing RAPP Brainstem..."
    mkdir -p "$BRAINSTEM_HOME"

    local SRC_ROOT="$BRAINSTEM_HOME/src/rapp_brainstem"
    local LOCAL_VERSION_FILE="$SRC_ROOT/VERSION"
    local STAGE="$BRAINSTEM_HOME/.framework_stage"
    local EGG_PATH="$BRAINSTEM_HOME/.bond/last-pre-bond.egg"

    # Detect prior install via the VERSION file rather than .git — the
    # installed copy is plain files. Pre-decoupling installs had a .git
    # inside src/; treat them as legacy and migrate on the way in.
    if [ -f "$LOCAL_VERSION_FILE" ] || [ -d "$BRAINSTEM_HOME/src/.git" ]; then
        # ── EXISTING ORGANISM: bond cycle (egg → overlay → hatch) ──
        local LOCAL_VER="0.0.0"
        [ -f "$LOCAL_VERSION_FILE" ] && LOCAL_VER=$(cat "$LOCAL_VERSION_FILE" 2>/dev/null || echo "0.0.0")
        local REMOTE_VER
        REMOTE_VER=$(curl -sf "$REMOTE_VERSION_URL" 2>/dev/null || echo "0.0.0")

        # Honest messaging: distinguish a user-explicit pin (BRAINSTEM_VERSION
        # env var) from the default "latest release tag" resolution. The old
        # code conflated the two and printed "Pin requested" every time the
        # default flow picked up a tag, even when the user passed nothing.
        if [ "$PIN_EXPLICIT" = "1" ]; then
            echo "  ⚑ Pin requested: v${PIN_VERSION} (will check out tag ${PIN_TAG})"
            REMOTE_VER="$PIN_VERSION"
        elif [ -n "$PIN_VERSION" ]; then
            echo "  Latest release: v${PIN_VERSION} (tag ${PIN_TAG})"
            REMOTE_VER="$PIN_VERSION"
        fi

        echo "  Local:  v${LOCAL_VER}"
        echo "  Target: v${REMOTE_VER}"

        local legacy_git=0
        [ -d "$BRAINSTEM_HOME/src/.git" ] && legacy_git=1

        if [ "$LOCAL_VER" = "$REMOTE_VER" ] && [ $legacy_git -eq 0 ]; then
            echo -e "  ${GREEN}✓${NC} Already up to date (v${LOCAL_VER})"
            # Even an up-to-date organism gets adopted into the lineage
            # system if it predates the rappid layer.
            if [ ! -f "$BRAINSTEM_HOME/rappid.json" ] && _bond_available; then
                _run_bond mint-rappid "$BRAINSTEM_HOME" >/dev/null 2>&1 || true
                _run_bond record-bond "$BRAINSTEM_HOME" adoption \
                    --to-version "$LOCAL_VER" \
                    --note "Existing organism adopted into lineage system" \
                    >/dev/null 2>&1 || true
                [ -f "$BRAINSTEM_HOME/rappid.json" ] && \
                    echo -e "  ${GREEN}🧬${NC} Adopted into lineage (rappid minted)"
            fi
            return 0
        fi

        # Refuse to bond *backward* unless the user explicitly asked for it
        # via BRAINSTEM_VERSION=. The default-latest flow would otherwise
        # downgrade users when their local is ahead of the latest tag (e.g.
        # they're tracking main HEAD or running an unreleased build).
        if [ "$PIN_EXPLICIT" != "1" ] && _version_gt "$LOCAL_VER" "$REMOTE_VER"; then
            echo -e "  ${GREEN}✓${NC} Local v${LOCAL_VER} is ahead of latest release v${REMOTE_VER} — staying put"
            echo -e "  ${YELLOW}!${NC} To force a downgrade: BRAINSTEM_VERSION=${REMOTE_VER} curl ... | bash"
            return 0
        fi

        # OPT-IN GATE — never wipe an existing organism without consent.
        # PIN_EXPLICIT=1 means the user passed BRAINSTEM_VERSION explicitly,
        # which is itself an opt-in (they asked for that exact version), so
        # skip the prompt in that case. Otherwise default behaviour: ask
        # (interactive) or refuse and print the BRAINSTEM_UPGRADE=1 command
        # (piped).
        if [ "$PIN_EXPLICIT" != "1" ]; then
            if ! _confirm_upgrade "$LOCAL_VER" "$REMOTE_VER"; then
                return 0
            fi
        fi

        if [ $legacy_git -eq 1 ]; then
            echo "  Detaching from upstream RAPP repo (no longer a git clone)..."
        fi
        echo "  Bonding v${LOCAL_VER} → v${REMOTE_VER}..."

        # 1. Stage the new framework. bond.py from the stage drives every
        # step below — same code on both sides of the upgrade.
        rm -rf "$STAGE"
        if ! stage_brainstem_framework "$STAGE"; then
            echo -e "  ${RED}✗${NC} Failed to fetch framework — keeping existing install"
            rm -rf "$STAGE"
            return 1
        fi
        local TO_COMMIT
        TO_COMMIT=$(git -C "$STAGE" rev-parse HEAD 2>/dev/null || echo "")

        # 2. PERSISTENT BACKUP — always-on safety net, kept *across* the
        # bond so users can revert if anything breaks (or if a hatched
        # state surfaces a regression a week later). Even if the bond.py
        # egg step fails (older pinned kernel without bond.py support,
        # python missing, disk full, anything), this backup of soul +
        # .env + custom agents survives the overlay AND survives the
        # whole install. Located at:
        #
        #   ~/.brainstem/.bond/backups/v<from>-to-v<to>-<utc-stamp>/
        #
        # Contains: soul.md, .env, agents/*.py, optionally pre-bond.egg.
        # Cleanup is the user's job — keep them or rm them by hand.
        local BACKUP_STAMP
        BACKUP_STAMP=$(date -u +"%Y%m%dT%H%M%SZ" 2>/dev/null || date +"%Y%m%dT%H%M%S")
        local BACKUP="$BRAINSTEM_HOME/.bond/backups/v${LOCAL_VER}-to-v${REMOTE_VER}-${BACKUP_STAMP}"
        # Ensure the backups dir is a local git repo before laying anything
        # down. _init_backup_git is idempotent + silent on failure.
        _init_backup_git
        mkdir -p "$BACKUP/agents"
        [ -f "$SOUL_FILE" ] && cp "$SOUL_FILE" "$BACKUP/soul.md" 2>/dev/null || true
        [ -f "$ENV_FILE" ] && cp "$ENV_FILE" "$BACKUP/.env" 2>/dev/null || true
        if [ -d "$AGENTS_DIR" ]; then
            cp "$AGENTS_DIR"/*.py "$BACKUP/agents/" 2>/dev/null || true
        fi
        # rappid + bonds log: identity files that should ride along with
        # any backup so a manual revert restores the same organism, not
        # a freshly-minted one.
        [ -f "$BRAINSTEM_HOME/rappid.json" ] && cp "$BRAINSTEM_HOME/rappid.json" "$BACKUP/rappid.json" 2>/dev/null || true
        [ -f "$BRAINSTEM_HOME/bonds.json" ]  && cp "$BRAINSTEM_HOME/bonds.json"  "$BACKUP/bonds.json"  2>/dev/null || true
        echo -e "  ${GREEN}💾${NC} Backup: ${BACKUP/$HOME/~}"

        # 3. Mint rappid if missing — needs bond.py from the stage.
        # Tolerated failure if bond.py isn't available (older pin).
        if [ ! -f "$BRAINSTEM_HOME/rappid.json" ] && _bond_available; then
            _run_bond mint-rappid "$BRAINSTEM_HOME" --parent-commit "$TO_COMMIT" >/dev/null 2>&1 || true
            _run_bond record-bond "$BRAINSTEM_HOME" adoption \
                --from-version "$LOCAL_VER" \
                --note "Adopted at first bond" >/dev/null 2>&1 || true
            [ -f "$BRAINSTEM_HOME/rappid.json" ] && \
                echo -e "  ${GREEN}🧬${NC} Minted rappid for legacy organism"
        fi

        # 4. 🥚 Egg the current organism — full cartridge if bond.py is
        # available, skip cleanly otherwise (the persistent backup at
        # step 2 is the safety net regardless). On success, the egg is
        # also copied into the per-bond backup folder so each upgrade
        # owns its own egg slot — last-pre-bond.egg only ever holds the
        # most recent one and would be overwritten by the next upgrade.
        EGG_PATH="$BRAINSTEM_HOME/.bond/last-pre-bond.egg"
        mkdir -p "$BRAINSTEM_HOME/.bond"
        local egg_ok=0
        if _bond_available; then
            if _run_bond egg "$BRAINSTEM_HOME" "$EGG_PATH" \
                    --kernel-version "$LOCAL_VER" --src "$SRC_ROOT" >/dev/null 2>&1; then
                egg_ok=1
                local egg_kb
                egg_kb=$(du -k "$EGG_PATH" 2>/dev/null | awk '{print $1}')
                echo -e "  ${GREEN}🥚${NC} Egged organism (${egg_kb:-?} KB) → ${EGG_PATH/$HOME/~}"
                # Tuck a per-bond copy into the persistent backup folder
                cp "$EGG_PATH" "$BACKUP/pre-bond.egg" 2>/dev/null || true
            fi
        fi
        if [ $egg_ok -eq 0 ]; then
            echo -e "  ${YELLOW}!${NC} bond.py egg unavailable — using legacy backup safety net"
            EGG_PATH=""
        fi

        # 5. Scrub legacy .git so the new src/ is unambiguously plain files.
        [ $legacy_git -eq 1 ] && rm -rf "$BRAINSTEM_HOME/src/.git"

        # 6. 🌐 Overlay new kernel. cp -R "$STAGE/rapp_brainstem/." dest/
        # copies contents in place — framework files refreshed, user-only
        # files (custom agents, .brainstem_data) stay put. The persistent
        # backup at $BACKUP is never deleted so a manual revert is always
        # possible.
        mkdir -p "$SRC_ROOT"
        if ! cp -R "$STAGE/rapp_brainstem/." "$SRC_ROOT/" 2>/dev/null; then
            echo -e "  ${RED}✗${NC} Overlay failed — restoring from backup"
            [ -f "$BACKUP/soul.md" ] && cp "$BACKUP/soul.md" "$SOUL_FILE" || true
            [ -f "$BACKUP/.env" ] && cp "$BACKUP/.env" "$ENV_FILE" || true
            rm -rf "$STAGE"
            return 1
        fi
        rm -rf "$STAGE"
        echo -e "  ${GREEN}🌐${NC} Overlayed new kernel onto src/rapp_brainstem"

        # 7. 🐣 Hatch the egg back if we have one. soul/agents/organs/
        # senses/services/data flow back over the new kernel.
        local hatched=0
        if [ -n "$EGG_PATH" ] && [ -f "$EGG_PATH" ] && _bond_available; then
            if _run_bond hatch "$BRAINSTEM_HOME" "$EGG_PATH" >/dev/null 2>&1; then
                echo -e "  ${GREEN}🐣${NC} Hatched egg back over new kernel"
                hatched=1
            else
                echo -e "  ${YELLOW}!${NC} Hatch reported errors — falling back to legacy restore"
            fi
        fi

        # 8. LEGACY RESTORE — runs whenever the bond hatch didn't.
        # Restores soul.md + .env + custom agents from the backup at step 2.
        # If the new framework already ships an agent of the same name, the
        # framework version wins (a true overlap, not a custom).
        if [ $hatched -eq 0 ]; then
            [ -f "$BACKUP/soul.md" ] && cp "$BACKUP/soul.md" "$SOUL_FILE" || true
            [ -f "$BACKUP/.env" ] && cp "$BACKUP/.env" "$ENV_FILE" || true
            local restored=0
            for agent_file in "$BACKUP/agents"/*.py; do
                [ -f "$agent_file" ] || continue
                local fname
                fname=$(basename "$agent_file")
                case "$fname" in
                    basic_agent.py|__init__.py) continue ;;
                esac
                [ -f "$AGENTS_DIR/$fname" ] && continue
                cp "$agent_file" "$AGENTS_DIR/$fname"
                restored=$((restored + 1))
            done
            echo -e "  ${GREEN}🧷${NC} Legacy restore: soul + .env + ${restored} custom agent(s)"
        fi

        # Backup is intentionally retained — it lives at $BACKUP for manual
        # revert. No `rm -rf "$BACKUP"` here.

        # 9. Record the bond + bump incarnations (best-effort).
        if _bond_available; then
            _run_bond bump-incarnations "$BRAINSTEM_HOME" >/dev/null 2>&1 || true
            _run_bond record-bond "$BRAINSTEM_HOME" bond \
                --from-version "$LOCAL_VER" --to-version "$REMOTE_VER" \
                --to-commit "$TO_COMMIT" >/dev/null 2>&1 || true
        fi

        # Commit the new backup to the local git repo BEFORE pruning
        # so the on-disk dirs we're about to drop still survive in
        # `git log`. Each bond becomes one commit on the backups repo.
        _commit_backup_to_git "$BACKUP"

        # Sliding window — drop old backups beyond the keep limit so the
        # backups dir doesn't grow without bound. The static emergency
        # baseline is separate and never pruned. Pruned backups still
        # survive in the local git history committed above.
        _prune_backups

        # Seed the emergency baseline if it hasn't been set yet (legacy
        # organisms that predate this safety net get one on their first
        # post-upgrade bond).
        _seed_emergency_baseline "$SRC_ROOT"

        echo -e "  ${GREEN}✓${NC} Bond complete: v${LOCAL_VER} → v${REMOTE_VER}"
        echo -e "  ${CYAN}↩${NC}  Revert: cp -R \"${BACKUP/$HOME/~}/.\" pieces back into place,"
        echo -e "      or hatch \"${BACKUP/$HOME/~}/pre-bond.egg\" with: brainstem hatch <egg>"
        echo -e "      or git: cd ~/.brainstem/.bond/backups && git log"
        echo -e "  ${CYAN}🛟${NC} If anything breaks: brainstem safe-mode  (emergency baseline)"
    else
        # ── FRESH INSTALL: birth event, no egg yet (nothing to pack) ──
        echo "  Fresh install — fetching framework..."
        rm -rf "$BRAINSTEM_HOME/src" 2>/dev/null || true
        rm -rf "$STAGE"
        if ! stage_brainstem_framework "$STAGE"; then
            echo -e "  ${RED}✗${NC} Failed to fetch framework"
            rm -rf "$STAGE"
            return 1
        fi
        local TO_COMMIT
        TO_COMMIT=$(git -C "$STAGE" rev-parse HEAD 2>/dev/null || echo "")
        local REMOTE_VER
        REMOTE_VER=$(cat "$STAGE/rapp_brainstem/VERSION" 2>/dev/null | tr -d '[:space:]')

        mkdir -p "$BRAINSTEM_HOME/src"
        cp -R "$STAGE/rapp_brainstem" "$BRAINSTEM_HOME/src/"
        rm -rf "$STAGE"

        # Mint identity & record birth — rappid is set ONCE per machine
        # and survives every future bond. Tolerated: an older pinned
        # framework without bond.py support won't mint, that's fine —
        # the next upgrade-to-current will adopt the install retroactively.
        if _bond_available; then
            _run_bond mint-rappid "$BRAINSTEM_HOME" --parent-commit "$TO_COMMIT" >/dev/null 2>&1 || true
            _run_bond record-bond "$BRAINSTEM_HOME" birth \
                --to-version "$REMOTE_VER" --to-commit "$TO_COMMIT" >/dev/null 2>&1 || true
            [ -f "$BRAINSTEM_HOME/rappid.json" ] && \
                echo -e "  ${GREEN}🥚${NC} Organism born — rappid minted, framework v${REMOTE_VER} hatched" || \
                echo -e "  ${GREEN}✓${NC} Framework v${REMOTE_VER} installed"
        else
            echo -e "  ${GREEN}✓${NC} Framework v${REMOTE_VER} installed (older release; rappid will mint on next upgrade)"
        fi

        # Seed the immutable emergency baseline. Static — only set on
        # first install. Future bonds never touch it. `brainstem safe-mode`
        # boots from this snapshot if the live install gets corrupted.
        _seed_emergency_baseline "$BRAINSTEM_HOME/src/rapp_brainstem"
    fi
    echo -e "  ${GREEN}✓${NC} Source code ready"
}

setup_venv() {
    local venv_python="$VENV_DIR/bin/python"

    # Check if venv exists and is healthy
    if [ -x "$venv_python" ]; then
        if "$venv_python" -c "import sys; sys.exit(0)" 2>/dev/null; then
            # Happy path — venv was already there and works. Stay silent;
            # the user doesn't need a line confirming the default state.
            return 0
        fi
        echo -e "  ${YELLOW}⚠${NC} Virtual environment broken — recreating..."
        rm -rf "$VENV_DIR"
    fi

    echo "  Creating virtual environment..."
    "$PYTHON_CMD" -m venv "$VENV_DIR" 2>/dev/null || {
        # Some systems need ensurepip first
        "$PYTHON_CMD" -m ensurepip 2>/dev/null || true
        "$PYTHON_CMD" -m venv "$VENV_DIR" || {
            echo -e "  ${RED}✗${NC} Failed to create virtual environment"
            echo "    Try: $PYTHON_CMD -m pip install virtualenv"
            exit 1
        }
    }
    # Ensure pip is up to date inside the venv
    "$VENV_DIR/bin/python" -m pip install --upgrade pip --quiet 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} Virtual environment ready"
}

setup_deps() {
    echo ""
    echo "Installing dependencies..."
    local req_file="$BRAINSTEM_HOME/src/rapp_brainstem/requirements.txt"
    "$VENV_DIR/bin/pip" install -r "$req_file" --quiet 2>/dev/null || \
        "$VENV_DIR/bin/pip" install -r "$req_file"

    # Verify the critical imports actually work
    if ! "$VENV_DIR/bin/python" -c "import flask, requests, dotenv" 2>/dev/null; then
        echo -e "  ${RED}✗${NC} Dependencies failed to install"
        echo "    Try: $VENV_DIR/bin/pip install -r $req_file"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} Dependencies installed"
}

ensure_deps() {
    # Quick import check — only install if something is missing.
    # Happy path stays silent; the user doesn't need a line confirming
    # the default state. The "missing — installing" branch below still
    # prints because the user should know we're touching pip.
    if "$VENV_DIR/bin/python" -c "import flask, requests, dotenv" 2>/dev/null; then
        return 0
    fi

    echo -e "  ${YELLOW}⚠${NC} Missing dependencies — installing..."
    local req_file="$BRAINSTEM_HOME/src/rapp_brainstem/requirements.txt"
    "$VENV_DIR/bin/pip" install -r "$req_file" --quiet 2>/dev/null || \
        "$VENV_DIR/bin/pip" install -r "$req_file"

    if ! "$VENV_DIR/bin/python" -c "import flask, requests, dotenv" 2>/dev/null; then
        echo -e "  ${RED}✗${NC} Dependencies failed — try: $VENV_DIR/bin/pip install -r $req_file"
        exit 1
    fi
    echo -e "  ${GREEN}✓${NC} Dependencies installed"
}

install_cli() {
    echo ""
    echo "Installing CLI..."
    mkdir -p "$BRAINSTEM_BIN"
    mkdir -p "$BRAINSTEM_HOME/logs"

    # Subcommand dispatcher: `brainstem` by itself starts the background
    # service (if installed) and opens the browser. `brainstem start|stop|
    # restart|status|logs|doctor|run|open` manages the service or fetches
    # diagnostics — the "doctor" output is what a user pastes back for
    # troubleshooting. All commands work whether the service is installed
    # (launchd on macOS, systemd --user on Linux) or not (falls back to
    # foreground run).
    cat > "$BRAINSTEM_BIN/brainstem" << 'WRAPPER'
#!/bin/bash
BRAINSTEM_HOME="$HOME/.brainstem"
SRC="$BRAINSTEM_HOME/src/rapp_brainstem"
VENV_PYTHON="$BRAINSTEM_HOME/venv/bin/python"
LOG="$BRAINSTEM_HOME/logs/brainstem.log"
URL="http://localhost:7071"
PLIST_ID="io.github.kodyw.rapp-brainstem"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_ID}.plist"
SYSTEMD_UNIT="rapp-brainstem.service"

is_macos() { [[ "$OSTYPE" == "darwin"* ]]; }
is_linux() { [[ "$OSTYPE" == "linux-gnu"* ]] || [[ "$OSTYPE" == "linux" ]]; }

_ensure_venv() {
    if [ ! -x "$VENV_PYTHON" ]; then
        echo "Setting up environment…"
        local PY
        PY=$(command -v python3.11 || command -v python3.12 || command -v python3.13 || command -v python3)
        "$PY" -m venv "$BRAINSTEM_HOME/venv"
    fi
    if ! "$VENV_PYTHON" -c "import flask, requests, dotenv" 2>/dev/null; then
        "$BRAINSTEM_HOME/venv/bin/pip" install -q -r "$SRC/requirements.txt" || \
            "$BRAINSTEM_HOME/venv/bin/pip" install -r "$SRC/requirements.txt"
    fi
}

_service_installed() {
    if is_macos; then [ -f "$PLIST_PATH" ]; return
    elif is_linux; then systemctl --user cat "$SYSTEMD_UNIT" &>/dev/null; return
    else return 1; fi
}

cmd_start() {
    _ensure_venv
    if is_macos && [ -f "$PLIST_PATH" ]; then
        launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null || \
            launchctl kickstart -k "gui/$(id -u)/$PLIST_ID" 2>/dev/null || true
        echo "✓ Service started (launchd: $PLIST_ID)"
    elif is_linux && _service_installed; then
        systemctl --user start "$SYSTEMD_UNIT"
        echo "✓ Service started (systemd --user: $SYSTEMD_UNIT)"
    else
        echo "⚠ No service installed — running in foreground (Ctrl-C to stop)."
        cmd_run
    fi
}

cmd_stop() {
    if is_macos && [ -f "$PLIST_PATH" ]; then
        launchctl bootout "gui/$(id -u)/$PLIST_ID" 2>/dev/null || true
        echo "✓ Service stopped"
    elif is_linux && _service_installed; then
        systemctl --user stop "$SYSTEMD_UNIT" && echo "✓ Service stopped"
    else
        echo "⚠ No service installed."
    fi
}

cmd_restart() { cmd_stop; sleep 1; cmd_start; }

cmd_status() {
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$URL/health" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then
        echo "✓ Brainstem is UP at $URL (HTTP 200)"
        curl -s --max-time 3 "$URL/health" | head -c 400 ; echo
    else
        echo "✗ Brainstem not responding at $URL (HTTP $code)"
    fi
    echo ""
    if is_macos && [ -f "$PLIST_PATH" ]; then
        echo "Service (launchd):"
        launchctl print "gui/$(id -u)/$PLIST_ID" 2>/dev/null \
            | awk '/state =|pid =|last exit code/' | sed 's/^/  /'
    elif is_linux && _service_installed; then
        echo "Service (systemd --user):"
        systemctl --user status "$SYSTEMD_UNIT" --no-pager --lines=0 2>/dev/null \
            | head -5 | sed 's/^/  /'
    else
        echo "Service: (not installed — foreground-only)"
    fi
}

cmd_logs() {
    if [ -f "$LOG" ]; then tail -f "$LOG"; else echo "no log at $LOG"; fi
}

cmd_run() {
    _ensure_venv
    cd "$SRC"
    exec "$VENV_PYTHON" brainstem.py "$@"
}

cmd_open() {
    if is_macos; then open "$URL" 2>/dev/null
    elif is_linux; then xdg-open "$URL" 2>/dev/null
    else echo "Open $URL in your browser"; fi
}

cmd_ls() {
    # List the global brainstem and every project-local brainstem registered
    # in $HOME/.brainstem/projects.json. Probes each port for liveness so the
    # output reflects what's actually responding right now, not just what was
    # ever installed. Safe to run from anywhere — read-only.
    local registry="$HOME/.brainstem/projects.json"
    printf "%-7s  %-50s  %-7s  %s\n" "PORT" "PATH" "STATE" "VERSION"
    printf "%-7s  %-50s  %-7s  %s\n" "----" "----" "-----" "-------"

    # Global brainstem (always at :7071 if installed)
    local g_state="—"
    if [ -d "$HOME/.brainstem" ]; then
        if curl -s --max-time 1 "http://localhost:7071/health" >/dev/null 2>&1; then
            g_state="up"
        else
            g_state="down"
        fi
        local g_version
        g_version=$(cat "$HOME/.brainstem/src/rapp_brainstem/VERSION" 2>/dev/null || echo "?")
        printf "%-7s  %-50s  %-7s  %s\n" "7071" "(global)  $HOME/.brainstem" "$g_state" "$g_version"
    fi

    # Project-local brainstems from registry
    if [ ! -f "$registry" ]; then
        return 0
    fi
    python3 - <<PYEOF "$registry"
import json, sys, urllib.request, os
try:
    data = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(0)
for entry in data.get("projects", []):
    port = entry.get("port", "?")
    path = entry.get("path", "?")
    version = entry.get("version", "?")
    state = "down"
    try:
        with urllib.request.urlopen(f"http://localhost:{port}/health", timeout=1) as r:
            if r.status == 200:
                state = "up"
    except Exception:
        pass
    if not os.path.isdir(os.path.join(path, ".brainstem")):
        state = "missing"
    print(f"{str(port):<7}  {path:<50}  {state:<7}  {version}")
PYEOF
}

cmd_doctor() {
    echo "=== RAPP Brainstem doctor ==="
    echo ""
    echo "Install path: $BRAINSTEM_HOME"
    echo "Source:       $SRC"
    echo "Venv python:  $VENV_PYTHON $([ -x "$VENV_PYTHON" ] && echo '(OK)' || echo '(MISSING)')"
    echo "Version:      $(cat "$SRC/VERSION" 2>/dev/null || echo '?')"
    echo "Log file:     $LOG"
    echo "OS:           $OSTYPE"
    echo ""
    echo "=== Service state ==="
    if is_macos; then
        if [ -f "$PLIST_PATH" ]; then
            echo "Plist:  $PLIST_PATH (present)"
            launchctl print "gui/$(id -u)/$PLIST_ID" 2>/dev/null \
                | awk '/state =|pid =|last exit code|program =/' | sed 's/^/  /' \
                || echo "  (not loaded)"
        else
            echo "Plist:  (not installed — running in foreground is the only way)"
        fi
    elif is_linux; then
        if _service_installed; then
            systemctl --user status "$SYSTEMD_UNIT" --no-pager --lines=0 2>/dev/null | head -6
        else
            echo "Unit: (not installed)"
        fi
    fi
    echo ""
    echo "=== /health ==="
    curl -s --max-time 3 "$URL/health" 2>/dev/null || echo "(unreachable)"
    echo ""
    echo ""
    echo "=== Last 40 log lines ==="
    tail -n 40 "$LOG" 2>/dev/null || echo "(no log yet)"
    echo ""
    echo "=== Safety net ==="
    local _baseline="$BRAINSTEM_HOME/.bond/emergency-baseline"
    if [ -f "$_baseline/brainstem.py" ]; then
        local _bv="?"
        [ -f "$_baseline/VERSION" ] && _bv=$(cat "$_baseline/VERSION" | tr -d '[:space:]')
        echo "Emergency baseline: v${_bv}  ($_baseline)"
        echo "  → Boot if live install is broken: brainstem safe-mode"
    else
        echo "Emergency baseline: (not seeded — run: brainstem doctor refresh-emergency)"
    fi
    local _backups_dir="$BRAINSTEM_HOME/.bond/backups"
    if [ -d "$_backups_dir" ]; then
        local _n
        _n=$(ls -1d "$_backups_dir"/*/ 2>/dev/null | wc -l | tr -d ' ')
        echo "Pre-bond backups:    ${_n} on disk  ($_backups_dir)"
        if [ -d "$_backups_dir/.git" ] && command -v git >/dev/null 2>&1; then
            local _git_n
            _git_n=$(git -C "$_backups_dir" rev-list --count HEAD 2>/dev/null || echo 0)
            echo "Local git history:   ${_git_n} commits  (cd $_backups_dir && git log)"
        else
            echo "Local git history:   not initialised (will be on first bond)"
        fi
        echo "  → List + revert: brainstem backups"
    else
        echo "Pre-bond backups:    none yet"
    fi
    echo ""
    echo "=== End doctor report ==="
}

cmd_identity() {
    # Print this organism's identity card (rappid + bond log).
    if [ ! -f "$BRAINSTEM_HOME/rappid.json" ]; then
        echo "(no identity yet — has the brainstem been installed via the one-liner?)"
        return 1
    fi
    echo "=== Organism ==="
    cat "$BRAINSTEM_HOME/rappid.json"
    echo ""
    if [ -f "$BRAINSTEM_HOME/bonds.json" ]; then
        echo "=== Bonds (lineage of evolution) ==="
        cat "$BRAINSTEM_HOME/bonds.json"
    fi
}

cmd_egg() {
    # Pack the local organism into a portable .egg cartridge.
    # Default output: ~/.brainstem/<rappid-slug>-<timestamp>.egg
    local out="${1:-}"
    local kver
    kver=$(cat "$SRC/VERSION" 2>/dev/null | tr -d '[:space:]')
    if [ -z "$out" ]; then
        local slug
        slug=$("$VENV_PYTHON" -c "import json,sys; print(json.load(open('$BRAINSTEM_HOME/rappid.json')).get('name','organism'))" 2>/dev/null || echo organism)
        local ts
        ts=$(date -u +"%Y%m%dT%H%M%SZ")
        out="$BRAINSTEM_HOME/${slug}-${ts}.egg"
    fi
    if (cd "$SRC" && "$VENV_PYTHON" -m utils.bond egg "$BRAINSTEM_HOME" "$out" \
            --kernel-version "${kver:-?}" --src "$SRC"); then
        echo "🥚 Egg written: $out"
    else
        echo "✗ Egg failed"
        return 1
    fi
}

cmd_hatch() {
    # Hatch a .egg cartridge over the local kernel. By default this
    # ADOPTS the egg's identity — useful when receiving an organism
    # from another machine. Use --preserve-rappid to keep the local
    # identity (e.g. just restoring agents/data from a backup egg).
    local egg="${1:-}"
    local preserve_flag=""
    [ "$2" = "--preserve-rappid" ] && preserve_flag="--preserve-rappid"
    if [ -z "$egg" ] || [ ! -f "$egg" ]; then
        echo "Usage: brainstem hatch <egg-file> [--preserve-rappid]"
        return 1
    fi
    if (cd "$SRC" && "$VENV_PYTHON" -m utils.bond hatch "$BRAINSTEM_HOME" "$egg" \
            --src "$SRC" $preserve_flag); then
        "$VENV_PYTHON" -m utils.bond record-bond "$BRAINSTEM_HOME" hatch \
            --note "Hatched from $(basename "$egg")" >/dev/null 2>&1 || true
        echo "🐣 Egg hatched"
    else
        echo "✗ Hatch failed"
        return 1
    fi
}

cmd_backups() {
    # List the per-bond backups under ~/.brainstem/.bond/backups/
    # plus the static emergency baseline and local git history (if any).
    # Newest-first.
    local backups_dir="$BRAINSTEM_HOME/.bond/backups"
    local baseline="$BRAINSTEM_HOME/.bond/emergency-baseline"
    echo "=== Pre-bond backups (on disk) ==="
    if [ -d "$backups_dir" ]; then
        local count=0
        for d in $(ls -1dt "$backups_dir"/*/ 2>/dev/null); do
            count=$((count + 1))
            local name=$(basename "${d%/}")
            local size=$(du -sh "$d" 2>/dev/null | awk '{print $1}')
            local egg=""
            [ -f "${d}pre-bond.egg" ] && egg="  +.egg" || egg=""
            echo "  ${count}. ${name}  (${size:-?})${egg}"
            echo "       ${d}"
        done
        if [ $count -eq 0 ]; then
            echo "  (none yet — backups are written before each upgrade bond)"
        fi
    else
        echo "  (none yet — backups are written before each upgrade bond)"
    fi
    echo ""
    echo "=== Local git history (every bond, even pruned ones) ==="
    if [ -d "$backups_dir/.git" ] && command -v git >/dev/null 2>&1; then
        local n
        n=$(git -C "$backups_dir" rev-list --count HEAD 2>/dev/null || echo 0)
        echo "  ${n} commit(s) at $backups_dir"
        echo ""
        git -C "$backups_dir" log --pretty=format:'  %h  %ad  %s' --date=short -n 10 2>/dev/null || true
        echo ""
        echo ""
        echo "  Browse:  cd $backups_dir && git log"
        echo "  Inspect: git -C $backups_dir show <sha>"
        echo "  Restore: git -C $backups_dir checkout <sha> -- <path>"
    else
        echo "  (no git repo yet — initialised on first bond)"
    fi
    echo ""
    echo "=== Emergency baseline (static) ==="
    if [ -d "$baseline" ] && [ -f "$baseline/brainstem.py" ]; then
        local bv="?"
        [ -f "$baseline/VERSION" ] && bv=$(cat "$baseline/VERSION" | tr -d '[:space:]')
        echo "  v${bv}  ${baseline}"
        echo "  (boot via: brainstem safe-mode)"
    else
        echo "  (not seeded — run: brainstem doctor refresh-emergency)"
    fi
}

cmd_safe_mode() {
    # Boot a brainstem from the emergency baseline regardless of what
    # state the live src/ tree is in. The minimum-viable kernel + soul
    # gets you a working chat surface even after a botched bond.
    #
    # Default port is BRAINSTEM_PORT (env) or 7072 — running on a
    # different port from the regular install so the user can run them
    # side-by-side and copy files over without first stopping the main
    # service.
    local baseline="$BRAINSTEM_HOME/.bond/emergency-baseline"
    if [ ! -f "$baseline/brainstem.py" ]; then
        echo "✗ No emergency baseline at $baseline"
        echo "  Re-run the installer to seed it, or:"
        echo "    brainstem doctor refresh-emergency"
        return 1
    fi
    local port="${BRAINSTEM_PORT:-7072}"
    [ "${1:-}" = "--port" ] && [ -n "${2:-}" ] && port="$2"
    echo "🛟 Safe mode — booting emergency baseline at http://localhost:${port}"
    echo "   Path: $baseline"
    echo "   (This does NOT touch your live install at $SRC.)"
    echo ""
    # Use the venv if it works; fall back to system python so safe mode
    # works even when the venv itself is the broken thing.
    local py="$VENV_PYTHON"
    if [ ! -x "$py" ] || ! "$py" -c "import flask" 2>/dev/null; then
        py=$(command -v python3 || command -v python || echo "")
        if [ -z "$py" ]; then
            echo "✗ No working python found — install python 3.11+ and retry"
            return 1
        fi
        echo "  (venv unavailable; using system $py)"
    fi
    cd "$baseline" || return 1
    PORT="$port" exec "$py" brainstem.py
}

cmd_doctor_refresh_emergency() {
    # Explicit refresh of the emergency baseline from the current live
    # install. Use after a known-good upgrade if you want safe mode to
    # carry the new kernel forward. Destructive (overwrites the baseline)
    # so it requires explicit confirmation.
    local baseline="$BRAINSTEM_HOME/.bond/emergency-baseline"
    if [ -d "$baseline" ] && [ -f "$baseline/brainstem.py" ]; then
        echo "Existing baseline at $baseline"
        if [ -t 0 ] && [ -t 1 ]; then
            local reply
            printf "Overwrite with the current live kernel? [y/N]: "
            read -r reply
            case "$reply" in y|Y|yes|YES) ;; *) echo "Aborted."; return 0 ;; esac
        else
            echo "Refusing to refresh non-interactively. Run from a terminal."
            return 1
        fi
        rm -rf "$baseline"
    fi
    mkdir -p "$baseline/agents"
    for f in brainstem.py basic_agent.py soul.md VERSION requirements.txt start.sh start.ps1 index.html; do
        [ -f "$SRC/$f" ] && cp "$SRC/$f" "$baseline/$f" 2>/dev/null || true
    done
    [ -f "$SRC/agents/basic_agent.py" ] && cp "$SRC/agents/basic_agent.py" "$baseline/agents/basic_agent.py" 2>/dev/null || true
    {
        echo "Refreshed: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
        [ -f "$SRC/VERSION" ] && echo "Version: $(cat "$SRC/VERSION" | tr -d '[:space:]')"
        echo ""
        echo "Static emergency baseline. Boots via: brainstem safe-mode"
    } > "$baseline/README.txt"
    echo "✓ Emergency baseline refreshed at $baseline"
}

cmd_help() {
    cat <<EOF
Usage: brainstem [COMMAND]

With no command, starts the service and opens the browser. All the
commands below work whether the background service is installed or not.

  start      Start the background service (or foreground if no service)
  stop       Stop the background service
  restart    Restart the background service
  status     One-line health check + service state
  ls         List the global brainstem + every registered project-local
             brainstem with their port and live state (up/down/missing)
  logs       Tail the service log
  doctor     Paste-to-support troubleshooting dump
  run        Run the brainstem in the foreground (for debugging)
  open       Open http://localhost:7071 in your browser

  identity   Print this organism's rappid + bond/lineage history
  egg [out]  Pack the organism into a portable .egg (full cartridge —
             AirDrop / send to another machine to continue the same
             organism elsewhere)
  hatch <e>  Hatch a received .egg over this kernel (adopts the egg's
             identity; --preserve-rappid keeps local identity instead)

  backups    List per-bond backups, local git history, + baseline status
  safe-mode  Boot from the emergency baseline (port 7072 by default)
             when the live install is broken. Read-only — does NOT
             touch your live install.
  doctor refresh-emergency
             Overwrite the emergency baseline with the current live
             install (use after a known-good upgrade).

  help       Show this message
EOF
}

case "${1:-default}" in
    start)    cmd_start ;;
    stop)     cmd_stop ;;
    restart)  cmd_restart ;;
    status)   cmd_status ;;
    ls)       cmd_ls ;;
    logs)     cmd_logs ;;
    doctor)
        if [ "${2:-}" = "refresh-emergency" ]; then
            cmd_doctor_refresh_emergency
        else
            cmd_doctor
        fi
        ;;
    run)      shift; cmd_run "$@" ;;
    open)     cmd_open ;;
    identity) cmd_identity ;;
    egg)      shift; cmd_egg "$@" ;;
    hatch)    shift; cmd_hatch "$@" ;;
    backups)  cmd_backups ;;
    safe-mode|safemode|safe_mode) shift; cmd_safe_mode "$@" ;;
    help|-h|--help) cmd_help ;;
    default)
        # No arg: ensure service is running, give it a second to come up,
        # then pop the browser. If no service is installed, fall through
        # to foreground run — the one-liner still leaves the user in a
        # working state.
        cmd_start &
        sleep 1
        for i in 1 2 3 4 5 6 7 8 9 10; do
            code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 1 "$URL/health" 2>/dev/null || echo 000)
            [ "$code" = "200" ] && break
            sleep 1
        done
        cmd_open
        ;;
    *) echo "Unknown command: $1"; cmd_help; exit 1 ;;
esac
WRAPPER

    chmod +x "$BRAINSTEM_BIN/brainstem"

    add_to_path() {
        local file="$1"
        # Create shell config if it doesn't exist (common on fresh macOS)
        touch "$file"
        if ! grep -q '\.local/bin' "$file" 2>/dev/null; then
            echo '' >> "$file"
            echo '# RAPP Brainstem' >> "$file"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$file"
        fi
    }
    add_to_path "$HOME/.bashrc"
    add_to_path "$HOME/.zshrc"
    add_to_path "$HOME/.bash_profile"

    echo -e "  ${GREEN}✓${NC} CLI installed to $BRAINSTEM_BIN/brainstem"
}

create_env() {
    local env_file="$BRAINSTEM_HOME/src/rapp_brainstem/.env"
    if [ ! -f "$env_file" ]; then
        cp "$BRAINSTEM_HOME/src/rapp_brainstem/.env.example" "$env_file" 2>/dev/null || true
    fi
}

# Install a user-level background service so non-technical users never
# have to think about "running a server". Service auto-starts on login
# (Constitution Article V — the one-liner is sacred, this is its
# auto-run story), auto-restarts on crash, logs to a known spot. Fall
# through silently if the OS service manager isn't available — the
# foreground-run fallback in the `brainstem` CLI still leaves users
# with a working install.
install_service() {
    local os_type
    os_type=$(detect_os)
    mkdir -p "$BRAINSTEM_HOME/logs"

    if [[ "$os_type" == "macos" ]]; then
        _install_service_macos
    elif [[ "$os_type" == "linux" ]]; then
        _install_service_linux
    else
        echo -e "  ${YELLOW}Service auto-start not supported on this OS — foreground only${NC}"
    fi
}

_install_service_macos() {
    local plist_id="io.github.kodyw.rapp-brainstem"
    local plist_dir="$HOME/Library/LaunchAgents"
    local plist_path="$plist_dir/${plist_id}.plist"
    local venv_python="$BRAINSTEM_HOME/venv/bin/python"
    local src_dir="$BRAINSTEM_HOME/src/rapp_brainstem"
    local log="$BRAINSTEM_HOME/logs/brainstem.log"

    mkdir -p "$plist_dir"

    # Bootout any previously-loaded copy so we pick up new paths/flags.
    launchctl bootout "gui/$(id -u)/$plist_id" 2>/dev/null || true

    cat > "$plist_path" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${plist_id}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${venv_python}</string>
        <string>brainstem.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${src_dir}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
    </dict>
    <key>StandardOutPath</key>
    <string>${log}</string>
    <key>StandardErrorPath</key>
    <string>${log}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
PLIST

    if launchctl bootstrap "gui/$(id -u)" "$plist_path" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Background service installed (launchd: ${plist_id})"
    else
        # Already-loaded cases: kickstart -k to restart with the new plist.
        launchctl kickstart -k "gui/$(id -u)/${plist_id}" 2>/dev/null && \
            echo -e "  ${GREEN}✓${NC} Background service refreshed" || \
            echo -e "  ${YELLOW}⚠${NC} Could not load service — will run in foreground"
    fi
}

_install_service_linux() {
    local unit_name="rapp-brainstem.service"
    local unit_dir="$HOME/.config/systemd/user"
    local unit_path="$unit_dir/$unit_name"
    local venv_python="$BRAINSTEM_HOME/venv/bin/python"
    local src_dir="$BRAINSTEM_HOME/src/rapp_brainstem"
    local log="$BRAINSTEM_HOME/logs/brainstem.log"

    if ! command -v systemctl &>/dev/null; then
        echo -e "  ${YELLOW}systemctl not found — skipping service install (foreground only)${NC}"
        return
    fi

    mkdir -p "$unit_dir"

    cat > "$unit_path" <<UNIT
[Unit]
Description=RAPP Brainstem — local-first AI agent server
After=network.target

[Service]
Type=simple
WorkingDirectory=${src_dir}
ExecStart=${venv_python} brainstem.py
Restart=always
RestartSec=3
StandardOutput=append:${log}
StandardError=append:${log}

[Install]
WantedBy=default.target
UNIT

    systemctl --user daemon-reload 2>/dev/null || true
    if systemctl --user enable --now "$unit_name" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Background service installed (systemd --user: ${unit_name})"
    else
        echo -e "  ${YELLOW}⚠${NC} Could not enable service (systemd --user may not be running) — falling back to foreground"
    fi
}

# Poll /health until it responds 200 or we give up. Used to verify the
# background service came up successfully before opening the browser.
wait_for_health() {
    local url="http://localhost:7071/health"
    local timeout="${1:-15}"  # seconds
    for ((i=0; i<timeout; i++)); do
        local code
        code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 1 "$url" 2>/dev/null || echo 000)
        if [ "$code" = "200" ]; then
            return 0
        fi
        sleep 1
    done
    return 1
}

open_browser() {
    local url="http://localhost:7071"
    if [[ "$(detect_os)" == "macos" ]]; then
        open "$url" 2>/dev/null || true
    elif [[ "$(detect_os)" == "linux" ]]; then
        xdg-open "$url" 2>/dev/null || true
    fi
}

launch_brainstem() {
    export PATH="$BRAINSTEM_BIN:/opt/homebrew/bin:/usr/local/bin:$PATH"

    # No auto-pull on launch — ~/.brainstem/src/ is plain files now,
    # not a git clone. Users upgrade by re-running the install one-liner;
    # install_brainstem() handles the framework refresh + user-file backup.

    local venv_python="$VENV_DIR/bin/python"

    # Ensure venv exists (handles edge case where only launch is called)
    if [ ! -x "$venv_python" ]; then
        if [[ -z "$PYTHON_CMD" ]]; then
            PYTHON_CMD=$(find_python) || true
        fi
        if [[ "$(detect_os)" == "macos" ]]; then
            ensure_brew_on_path
        fi
        setup_venv
        ensure_deps
    fi

    local token_file="$BRAINSTEM_HOME/src/rapp_brainstem/.copilot_token"
    local client_id="Iv1.b507a08c87ecfe98"

    # Step 1: Copilot authentication (device code flow)
    local needs_auth=true
    if [ -f "$token_file" ]; then
        # Validate existing token against Copilot API
        local saved_token
        saved_token=$("$venv_python" -c "
import json, sys
try:
    with open('$token_file') as f:
        raw = f.read().strip()
    if raw.startswith('{'):
        print(json.loads(raw).get('access_token',''))
    else:
        print(raw)
except: pass
" 2>/dev/null)
        if [[ -n "$saved_token" ]]; then
            local auth_prefix="token"
            if [[ "$saved_token" != ghu_* ]]; then auth_prefix="Bearer"; fi
            local check_status
            check_status=$(curl -s -o /dev/null -w "%{http_code}" \
                -H "Authorization: $auth_prefix $saved_token" \
                -H "Accept: application/json" \
                -H "Editor-Version: vscode/1.95.0" \
                -H "Editor-Plugin-Version: copilot/1.0.0" \
                "https://api.github.com/copilot_internal/v2/token" 2>/dev/null)
            if [[ "$check_status" == "200" ]]; then
                echo -e "  ${GREEN}✓${NC} Already authenticated with GitHub Copilot"
                needs_auth=false
            else
                echo -e "  ${YELLOW}⚠${NC} Saved token expired — re-authenticating..."
                rm -f "$token_file"
            fi
        else
            rm -f "$token_file"
        fi
    fi

    if [[ "$needs_auth" == true ]]; then
        echo ""
        echo -e "  ${CYAN}Authenticating with GitHub Copilot...${NC}"
        echo ""

        # Request device code
        local device_resp
        device_resp=$(curl -fsSL -X POST "https://github.com/login/device/code" \
            -H "Accept: application/json" \
            -H "Content-Type: application/x-www-form-urlencoded" \
            -d "client_id=${client_id}" 2>/dev/null)

        local user_code device_code interval verify_uri
        user_code=$(echo "$device_resp" | "$venv_python" -c "import sys,json; print(json.load(sys.stdin)['user_code'])" 2>/dev/null)
        device_code=$(echo "$device_resp" | "$venv_python" -c "import sys,json; print(json.load(sys.stdin)['device_code'])" 2>/dev/null)
        interval=$(echo "$device_resp" | "$venv_python" -c "import sys,json; print(json.load(sys.stdin).get('interval',5))" 2>/dev/null)
        verify_uri=$(echo "$device_resp" | "$venv_python" -c "import sys,json; print(json.load(sys.stdin)['verification_uri'])" 2>/dev/null)

        if [[ -z "$user_code" || -z "$device_code" ]]; then
            echo -e "  ${YELLOW}!${NC} Could not start auth — you can sign in at http://localhost:7071/login"
        else
            echo "  ┌─────────────────────────────────────────┐"
            echo -e "  │  Your code: ${CYAN}${user_code}${NC}                  │"
            echo "  └─────────────────────────────────────────┘"
            echo ""
            echo "  Opening browser to authorize..."

            # Open browser
            open "$verify_uri" 2>/dev/null || xdg-open "$verify_uri" 2>/dev/null || true

            echo "  Waiting for authorization..."
            echo ""

            local token_json=""
            for i in $(seq 1 60); do
                sleep "${interval:-5}"
                local poll_resp
                poll_resp=$(curl -fsSL -X POST "https://github.com/login/oauth/access_token" \
                    -H "Accept: application/json" \
                    -H "Content-Type: application/x-www-form-urlencoded" \
                    -d "client_id=${client_id}&device_code=${device_code}&grant_type=urn:ietf:params:oauth:grant-type:device_code" 2>/dev/null)

                local access_token error
                access_token=$(echo "$poll_resp" | "$venv_python" -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))" 2>/dev/null)
                error=$(echo "$poll_resp" | "$venv_python" -c "import sys,json; d=json.load(sys.stdin); print(d.get('error',''))" 2>/dev/null)

                if [[ -n "$access_token" ]]; then
                    # Save token file (same format brainstem.py expects)
                    "$venv_python" -c "
import sys, json
d = json.loads(sys.argv[1])
out = {'access_token': d['access_token']}
if d.get('refresh_token'): out['refresh_token'] = d['refresh_token']
with open(sys.argv[2], 'w') as f: json.dump(out, f)
" "$poll_resp" "$token_file"

                    # Validate Copilot access immediately
                    local copilot_check copilot_status
                    copilot_check=$(curl -s -w "\n%{http_code}" \
                        -H "Authorization: token $access_token" \
                        -H "Accept: application/json" \
                        -H "Editor-Version: vscode/1.95.0" \
                        -H "Editor-Plugin-Version: copilot/1.0.0" \
                        "https://api.github.com/copilot_internal/v2/token" 2>/dev/null)
                    copilot_status=$(echo "$copilot_check" | tail -1)

                    if [[ "$copilot_status" == "200" ]]; then
                        echo -e "  ${GREEN}✓${NC} Authenticated — Copilot access confirmed"
                    elif [[ "$copilot_status" == "403" ]]; then
                        echo ""
                        echo -e "  ${RED}✗${NC} This GitHub account does NOT have Copilot access."
                        echo ""
                        echo -e "  Either:"
                        echo -e "    1. Sign up for Copilot: ${CYAN}https://github.com/github-copilot/signup${NC}"
                        echo -e "    2. Re-run this installer and sign in with a different GitHub account"
                        echo ""
                        rm -f "$token_file"
                    else
                        echo -e "  ${GREEN}✓${NC} Authenticated with GitHub"
                    fi
                    break
                fi

                if [[ "$error" == "expired_token" ]]; then
                    echo -e "  ${YELLOW}!${NC} Auth timed out — sign in at http://localhost:7071/login"
                    break
                fi

                if [[ "$error" != "authorization_pending" && "$error" != "slow_down" && -n "$error" ]]; then
                    echo -e "  ${YELLOW}!${NC} Auth error: $error — sign in at http://localhost:7071/login"
                    break
                fi
            done
        fi
    fi

    # Step 2: Launch brainstem
    echo ""
    echo -e "  ${CYAN}Starting RAPP Brainstem...${NC}"
    # One-click tether handoff. The web UI reads ?tether=… on boot,
    # writes it into Settings.tether_url, flips the tether checkbox on,
    # then strips the param so a reload doesn't re-apply (or a shared
    # URL doesn't keep flipping someone else's tether back on).
    # Most modern terminals (iTerm2, macOS Terminal, Windows Terminal,
    # VSCode terminal, gnome-terminal) auto-detect URLs and make them
    # cmd-/ctrl-clickable — no need for explicit OSC-8 escape sequences
    # which would render as raw bytes in terminals that don't speak it.
    echo -e "  ${CYAN}Use the virtual brainstem with this machine as the tether:${NC}"
    echo -e "  https://kody-w.github.io/RAPP/rapp_brainstem/web/?tether=http://localhost:7071"
    echo ""

    cd "$BRAINSTEM_HOME/src/rapp_brainstem"

    # Port-in-use detection. Almost always a previous brainstem still running.
    if command -v lsof >/dev/null 2>&1; then
        EXISTING_PID=$(lsof -ti:7071 2>/dev/null | head -1)
        if [ -n "$EXISTING_PID" ]; then
            EXISTING_CMD=$(ps -p "$EXISTING_PID" -o comm= 2>/dev/null | head -c 60)
            echo -e "  ${YELLOW}⚠${NC} Port 7071 is already in use by PID $EXISTING_PID ($EXISTING_CMD)"
            if [ -t 0 ]; then
                printf "  Kill it and continue? [y/N] "
                read -r REPLY </dev/tty
            else
                # Piped via curl|bash — auto-kill since the user clearly wants
                # the brainstem running and the most common case is a stale
                # previous brainstem.
                REPLY="y"
                echo -e "  ${CYAN}(running via curl|bash — auto-killing previous brainstem)${NC}"
            fi
            case "$REPLY" in
                [Yy]*)
                    kill -9 "$EXISTING_PID" 2>/dev/null && \
                        echo -e "  ${GREEN}✓${NC} killed PID $EXISTING_PID"
                    sleep 0.5
                    ;;
                *)
                    echo -e "  ${YELLOW}Aborted.${NC} To launch on a different port:"
                    echo -e "    cd $BRAINSTEM_HOME/src/rapp_brainstem && PORT=7072 python brainstem.py"
                    exit 1
                    ;;
            esac
        fi
    fi

    # Final dep safety net — if somehow we got here without deps, fix it
    if ! "$venv_python" -c "import flask, requests, dotenv" 2>/dev/null; then
        echo -e "  ${YELLOW}⚠${NC} Fixing missing dependencies..."
        "$VENV_DIR/bin/pip" install -r "$BRAINSTEM_HOME/src/rapp_brainstem/requirements.txt" --quiet 2>/dev/null || \
            "$VENV_DIR/bin/pip" install -r "$BRAINSTEM_HOME/src/rapp_brainstem/requirements.txt"
    fi

    # ── User vs. Agent handshake ─────────────────────────────────────
    # Different runtimes want different lifecycle models:
    #   - HUMAN at a terminal: brainstem runs in the foreground; close
    #     the terminal (or Ctrl-C) to stop. This is what the user trains
    #     people on — "kill the terminal to stop the brainstem".
    #   - AGENT (Claude Code, Cursor, CI, etc.): brainstem runs as a
    #     background launchd/systemd service so the agent can return
    #     control to its harness and call `brainstem restart` / `stop`
    #     without TTY contortions.
    # Detection: well-known env vars set by the agent runtimes. Users
    # can force one mode or the other via BRAINSTEM_LAUNCH_MODE=fg|bg.
    local launch_mode="${BRAINSTEM_LAUNCH_MODE:-}"
    if [ -z "$launch_mode" ]; then
        if [ -n "$CLAUDECODE" ] || [ -n "$CURSOR_AGENT" ] || \
           [ "$CI" = "true" ] || [ -n "$GITHUB_ACTIONS" ] || \
           [ "$TERM_PROGRAM" = "vscode" ] && [ -n "$CLAUDE_CODE_ENTRYPOINT" ]; then
            launch_mode="bg"
        else
            launch_mode="fg"
        fi
    fi

    if [ "$launch_mode" = "bg" ]; then
        # Agent path: install the service so `brainstem start|stop|restart`
        # works from CLI invocations, return immediately so the harness
        # gets control back.
        echo -e "  ${CYAN}(agent runtime detected — installing as background service)${NC}"
        install_service
        if wait_for_health 15; then
            echo ""
            echo -e "  ${GREEN}✓${NC} Brainstem is running at http://localhost:7071"
            echo -e "  Manage with: ${CYAN}brainstem${NC} ${CYAN}start|stop|restart|status|logs|doctor${NC}"
            echo ""
            return 0
        fi
        echo -e "  ${YELLOW}⚠${NC} Service didn't come up — falling back to foreground."
    fi

    # Foreground path (humans). First unload any prior launchd service
    # so it doesn't race for :7071 with the foreground process we're
    # about to start.
    if [ -f "$HOME/Library/LaunchAgents/io.github.kodyw.rapp-brainstem.plist" ]; then
        echo -e "  ${CYAN}(unloading prior launchd service so foreground process owns :7071)${NC}"
        launchctl unload "$HOME/Library/LaunchAgents/io.github.kodyw.rapp-brainstem.plist" 2>/dev/null || true
    fi

    # Open the browser shortly after the server starts.
    (sleep 2 && (open "http://localhost:7071" 2>/dev/null || xdg-open "http://localhost:7071" 2>/dev/null)) &

    echo ""
    echo -e "  ${GREEN}✓${NC} Brainstem starting in this terminal — close the window or press Ctrl-C to stop it."
    echo ""

    # Use exec to replace this shell process — closing the terminal then
    # sends signals straight to brainstem.py. Only when stdin is a real
    # TTY though; when piped (curl | bash), exec can lose the TTY and
    # the process orphans. Direct invocation in the piped case still
    # gets killed when the terminal closes (parent pid gone).
    if [ -t 0 ]; then
        exec "$venv_python" brainstem.py
    else
        "$venv_python" brainstem.py </dev/tty
    fi
}

# ── Project-local helpers (--here mode) ──────────────────────────────

find_free_port() {
    # Pick a port free in three senses (good-neighbor pattern):
    #   1. No process currently listening (lsof)
    #   2. No TCP accept on 127.0.0.1 (covers ports without lsof permission)
    #   3. Not claimed by another brainstem in the peer registry
    #      (~/.config/rapp/peers.json — set by previous installs that
    #      haven't started yet, so two back-to-back --here installs don't
    #      both claim 7072 and crash on first start.)
    local start="${1:-7072}" p="$start" lim=$((start + 50))
    local registry_helper="$BRAINSTEM_HOME/src/rapp_brainstem/utils/peer_registry.py"
    local claimed=""
    if [ -f "$registry_helper" ]; then
        claimed=$(python3 "$registry_helper" claimed-ports 2>/dev/null || true)
    fi
    while [ "$p" -lt "$lim" ]; do
        if ! lsof -ti ":$p" >/dev/null 2>&1 && \
           ! (exec 3<>/dev/tcp/127.0.0.1/$p) 2>/dev/null && \
           ! echo " $claimed " | grep -q " $p "; then
            echo "$p"
            return 0
        fi
        p=$((p + 1))
    done
    echo "$start"
}

register_in_peers() {
    # Append this install to the local peer registry so future installs
    # see its port. The /api/peers endpoint reads the same file at runtime
    # to render the neighborhood view.
    local brainstem_dir="$1" port="$2"
    local registry_helper="$BRAINSTEM_HOME/src/rapp_brainstem/utils/peer_registry.py"
    local version=""
    [ -f "$BRAINSTEM_HOME/src/rapp_brainstem/VERSION" ] && \
        version=$(cat "$BRAINSTEM_HOME/src/rapp_brainstem/VERSION" | tr -d '[:space:]')
    if [ -f "$registry_helper" ]; then
        python3 "$registry_helper" upsert "$brainstem_dir" "$port" "$version" >/dev/null 2>&1 || true
    fi
}

write_local_launcher() {
    local port="$1"
    local launcher="$BRAINSTEM_HOME/start.sh"
    cat > "$launcher" << LAUNCHER
#!/bin/bash
# Project-local RAPP brainstem launcher.
# Auto-generated by install.sh --here. Safe to re-generate.
HERE="\$(cd "\$(dirname "\$0")" && pwd)"
SRC="\$HERE/src/rapp_brainstem"
VENV_PYTHON="\$HERE/venv/bin/python"
PORT_FILE="\$HERE/PORT"

# Good-neighbor pattern: if the install-time port is already taken at
# launch (e.g. another brainstem grabbed it first), autopick the next
# free port and persist the new value back to BRAINSTEM_HOME/PORT and
# the peer registry so siblings see the actual running port.
desired_port="${port}"
[ -f "\$PORT_FILE" ] && desired_port=\$(cat "\$PORT_FILE" | tr -d '[:space:]')
final_port="\$desired_port"
if lsof -ti ":\$desired_port" >/dev/null 2>&1; then
    p=\$((desired_port + 1))
    while [ "\$p" -lt \$((desired_port + 50)) ]; do
        if ! lsof -ti ":\$p" >/dev/null 2>&1 && \\
           ! (exec 3<>/dev/tcp/127.0.0.1/\$p) 2>/dev/null; then
            final_port="\$p"; break
        fi
        p=\$((p + 1))
    done
    echo "▶ Port \$desired_port busy; using \$final_port instead"
    echo "\$final_port" > "\$PORT_FILE"
    REGHELPER="\$SRC/utils/peer_registry.py"
    [ -f "\$REGHELPER" ] && python3 "\$REGHELPER" upsert "\$SRC" "\$final_port" "" >/dev/null 2>&1 || true
fi
cd "\$SRC"
PORT=\$final_port exec "\$VENV_PYTHON" brainstem.py "\$@"
LAUNCHER
    chmod +x "$launcher"
    echo "$port" > "$BRAINSTEM_HOME/PORT"
}

register_project() {
    # Add this project-local install to the host-wide registry at
    # ~/.brainstem/projects.json so `brainstem ls` (running from anywhere)
    # can see every project-local instance + the global at a glance. Idempotent —
    # running install.sh --here on the same project twice updates the entry
    # in place rather than duplicating it. Failure is silent: the registry is
    # purely informational and must never block the install.
    local port="$1"
    local registry_dir="$HOME/.brainstem"
    local registry="$registry_dir/projects.json"
    local project_path
    project_path="$(pwd)"
    local installed_at
    installed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    local version
    version="$(cat "$BRAINSTEM_HOME/src/rapp_brainstem/VERSION" 2>/dev/null | tr -d '[:space:]' || echo unknown)"

    mkdir -p "$registry_dir" 2>/dev/null || return 0
    python3 - "$registry" "$project_path" "$port" "$installed_at" "$version" <<'PYEOF' 2>/dev/null || true
import json, sys, os
registry_path, project_path, port, installed_at, version = sys.argv[1:6]
try:
    data = json.load(open(registry_path)) if os.path.exists(registry_path) else {}
except Exception:
    data = {}
projects = [p for p in data.get("projects", []) if p.get("path") != project_path]
projects.append({
    "path": project_path,
    "port": int(port),
    "installed_at": installed_at,
    "version": version,
})
data["projects"] = sorted(projects, key=lambda p: p.get("port", 0))
data["updated_at"] = installed_at
with open(registry_path, "w") as f:
    json.dump(data, f, indent=2)
PYEOF
}

ensure_project_gitignore() {
    # If cwd is inside a git repo, add .brainstem/ to its .gitignore
    # so the local brainstem's runtime state never ends up tracked.
    git rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
    local repo_root gi rel
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || return 0
    gi="$repo_root/.gitignore"
    rel=$(python3 -c "import os,sys; print(os.path.relpath('$BRAINSTEM_HOME','$repo_root'))" 2>/dev/null)
    [ -z "$rel" ] && rel=".brainstem"
    rel="${rel%/}/"
    if [ ! -f "$gi" ] || ! grep -qxF "$rel" "$gi" 2>/dev/null; then
        {
            echo ""
            echo "# Project-local RAPP brainstem (install.sh --here)"
            echo "$rel"
        } >> "$gi"
        echo -e "  ${GREEN}✓${NC} added ${rel} to ${gi#$repo_root/}"
    fi
}

main_local() {
    print_banner
    echo -e "  ${CYAN}Installing project-local brainstem at${NC} ${BRAINSTEM_HOME}"
    echo "  (running alongside any global brainstem on :7071 — this one picks its own port)"
    echo ""

    check_prereqs
    install_brainstem
    setup_venv
    setup_deps
    create_env

    local port
    port=$(find_free_port 7072)
    write_local_launcher "$port"
    ensure_project_gitignore
    register_in_peers "$BRAINSTEM_HOME/src/rapp_brainstem" "$port"
    register_project "$port"

    local installed_version
    installed_version=$(cat "$BRAINSTEM_HOME/src/rapp_brainstem/VERSION" 2>/dev/null | tr -d '[:space:]')

    echo ""
    echo "═══════════════════════════════════════════════════"
    echo -e "  ${GREEN}✓ RAPP Brainstem v${installed_version} installed (project-local)${NC}"
    echo "═══════════════════════════════════════════════════"
    echo ""
    echo "  To start this project's brainstem:"
    echo -e "    ${CYAN}./.brainstem/start.sh${NC}"
    echo ""
    echo "  See every brainstem on this host (global + project-locals):"
    echo -e "    ${CYAN}brainstem ls${NC}"
    echo ""
    echo -e "  It'll run at ${CYAN}http://localhost:${port}${NC}"
    echo ""
    echo "  Your global brainstem (if installed) keeps running at :7071."
    echo "  Both can run concurrently; they talk to each other as agents."
    echo ""
}

main() {
    if [ "$LOCAL_MODE" = "1" ]; then
        main_local
        return
    fi

    print_banner

    # Existing install? Run the full install_brainstem path so VERSION,
    # legacy .git scrubbing, and overlay all happen in one place. The old
    # check_for_upgrade fast-path that ran `git pull` against the user's
    # working tree is gone — there's no .git in src/ anymore.
    if [ -f "$BRAINSTEM_HOME/src/rapp_brainstem/VERSION" ] || [ -d "$BRAINSTEM_HOME/src/.git" ]; then
        echo "Checking for updates..."
    fi

    check_prereqs
    install_brainstem
    setup_venv
    setup_deps
    install_cli
    create_env
    register_in_peers "$BRAINSTEM_HOME/src/rapp_brainstem" 7071

    # Make sure brainstem and gh are on PATH for this session
    export PATH="$BRAINSTEM_BIN:/opt/homebrew/bin:/usr/local/bin:$PATH"

    local installed_version
    installed_version=$(cat "$BRAINSTEM_HOME/src/rapp_brainstem/VERSION" 2>/dev/null | tr -d '[:space:]')

    echo ""
    echo "═══════════════════════════════════════════════════"
    echo -e "  ${GREEN}✓ RAPP Brainstem v${installed_version} installed!${NC}"
    echo "═══════════════════════════════════════════════════"
    echo ""

    launch_brainstem
}

main
