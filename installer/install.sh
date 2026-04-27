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

# Optional pin: BRAINSTEM_VERSION=X.Y.Z env var → install that tagged
# version instead of the tip of main. Empty means "latest main".
PIN_VERSION="${BRAINSTEM_VERSION:-}"
PIN_TAG=""
[ -n "$PIN_VERSION" ] && PIN_TAG="brainstem-v${PIN_VERSION}"

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

install_brainstem() {
    echo ""
    echo "Installing RAPP Brainstem..."
    mkdir -p "$BRAINSTEM_HOME"

    local AGENTS_DIR="$BRAINSTEM_HOME/src/rapp_brainstem/agents"
    local SOUL_FILE="$BRAINSTEM_HOME/src/rapp_brainstem/soul.md"
    local ENV_FILE="$BRAINSTEM_HOME/src/rapp_brainstem/.env"
    local LOCAL_VERSION_FILE="$BRAINSTEM_HOME/src/rapp_brainstem/VERSION"

    if [ -d "$BRAINSTEM_HOME/src/.git" ]; then
        # ── SMART UPDATE: preserve local files, upgrade framework ──
        local LOCAL_VER="0.0.0"
        [ -f "$LOCAL_VERSION_FILE" ] && LOCAL_VER=$(cat "$LOCAL_VERSION_FILE" 2>/dev/null || echo "0.0.0")
        local REMOTE_VER=$(curl -sf "$REMOTE_VERSION_URL" 2>/dev/null || echo "0.0.0")

        # Pinned-version override: users can fall back to an older released
        # version if a newer one broke something for them.
        if [ -n "$PIN_VERSION" ]; then
            echo "  ⚑ Pin requested: v${PIN_VERSION} (will check out tag ${PIN_TAG})"
            REMOTE_VER="$PIN_VERSION"
        fi

        echo "  Local:  v${LOCAL_VER}"
        echo "  Target: v${REMOTE_VER}"

        if [ "$LOCAL_VER" = "$REMOTE_VER" ]; then
            echo -e "  ${GREEN}✓${NC} Already up to date (v${LOCAL_VER})"
        else
            echo "  Upgrading v${LOCAL_VER} → v${REMOTE_VER}..."

            # 1. Backup user's local files (soul, custom agents, .env)
            local BACKUP="/tmp/brainstem-upgrade-$$"
            mkdir -p "$BACKUP"
            [ -f "$SOUL_FILE" ] && cp "$SOUL_FILE" "$BACKUP/soul.md"
            [ -f "$ENV_FILE" ] && cp "$ENV_FILE" "$BACKUP/.env"
            if [ -d "$AGENTS_DIR" ]; then
                mkdir -p "$BACKUP/agents"
                # Backup ALL agents — user-created ones will be restored
                cp "$AGENTS_DIR"/*.py "$BACKUP/agents/" 2>/dev/null || true
            fi
            echo -e "  ${GREEN}✓${NC} Backed up soul, agents, config"

            # 2. Hard-sync framework files to origin/main. User files (soul,
            # agents, .env) are already backed up above — we restore them at
            # step 3. `git pull` was getting wedged on untracked files or
            # merge conflicts and silently failing, leaving users pinned to
            # old VERSIONs. Hard reset always wins the race.
            cd "$BRAINSTEM_HOME/src"
            # Make sure the origin URL is the canonical repo — users can end
            # up on forks/mirrors or old HTTPS→SSH migrations where fetch
            # pulls from somewhere stale.
            git remote set-url origin "$REPO_URL" 2>/dev/null || true
            git stash --quiet --include-untracked 2>/dev/null || true
            # Ensure we're on main — clones can drift to other branches
            git checkout main --quiet 2>/dev/null || true
            # Fetch main + tags so both "latest" and "pin" flows work.
            git fetch --quiet --tags origin main 2>/dev/null || true
            # Choose reset target: a pinned tag if requested, else origin/main.
            local reset_target="origin/main"
            if [ -n "$PIN_TAG" ]; then
                if git rev-parse --verify "$PIN_TAG" >/dev/null 2>&1; then
                    reset_target="$PIN_TAG"
                else
                    echo -e "  ${YELLOW}⚠${NC} Pin tag ${PIN_TAG} not found on remote — falling back to origin/main"
                fi
            fi
            if git reset --hard --quiet "$reset_target" 2>/dev/null; then
                git clean -fdq 2>/dev/null || true
                echo -e "  ${GREEN}✓${NC} Framework hard-synced to ${reset_target}"
            else
                echo -e "  ${YELLOW}Warning: git reset failed — falling back to pull${NC}"
                git pull --quiet 2>/dev/null || echo -e "  ${YELLOW}Warning: Could not pull${NC}"
            fi

            # 2b. Verify the sync actually landed. If VERSION still doesn't
            # match the remote, something deeper is wrong with the user's
            # local clone (detached HEAD, wrong branch, broken origin, a
            # stale object cache) — nuke and re-clone. Backup is safe.
            local post_sync_ver="0.0.0"
            [ -f "$LOCAL_VERSION_FILE" ] && post_sync_ver=$(cat "$LOCAL_VERSION_FILE" 2>/dev/null | tr -d '[:space:]')
            if [ "$post_sync_ver" != "$REMOTE_VER" ]; then
                echo -e "  ${YELLOW}⚠${NC} Post-sync VERSION is v${post_sync_ver} (expected v${REMOTE_VER})"
                echo "  Re-cloning from scratch to recover..."
                cd "$BRAINSTEM_HOME"
                rm -rf "$BRAINSTEM_HOME/src"
                # Full clone — users typically deploy the swarm tier and worker
                # later, and the install one-liner is the path everyone takes.
                # The catalog (rapp_store) is the only repo that's been split out;
                # everything else (rapp_brainstem, rapp_swarm, worker, installer,
                # pages, tests) ships as a single tree.
                if git clone --quiet "$REPO_URL" "$BRAINSTEM_HOME/src"; then
                    if [ -n "$PIN_TAG" ]; then
                        cd "$BRAINSTEM_HOME/src"
                        git checkout --quiet "$PIN_TAG" 2>/dev/null || \
                            echo -e "  ${YELLOW}Warning: Could not check out tag ${PIN_TAG}; staying on main${NC}"
                    fi
                    echo -e "  ${GREEN}✓${NC} Fresh clone successful"
                else
                    echo -e "  ${RED}✗${NC} Fresh clone failed — please check connectivity and retry"
                    return 1
                fi
            fi

            # 3. Restore user's local files (merge, don't overwrite)
            [ -f "$BACKUP/soul.md" ] && cp "$BACKUP/soul.md" "$SOUL_FILE"
            [ -f "$BACKUP/.env" ] && cp "$BACKUP/.env" "$ENV_FILE"
            if [ -d "$BACKUP/agents" ]; then
                # Only restore truly custom agents — ones the user created
                # that don't exist in the repo after reset. Agents the repo
                # deleted must stay deleted.
                local restored=0
                for agent_file in "$BACKUP/agents"/*.py; do
                    local fname=$(basename "$agent_file")
                    case "$fname" in
                        basic_agent.py|__init__.py) continue ;;
                    esac
                    # If the repo already has this file after reset, skip —
                    # the repo version wins (updated or still present).
                    # If the repo DOESN'T have it, it's either a custom agent
                    # or one the repo deleted. Check git to distinguish.
                    if [ -f "$AGENTS_DIR/$fname" ]; then
                        continue
                    fi
                    # File not in repo after reset — was it ever tracked?
                    # If git knows about it, the repo intentionally deleted it.
                    if git -C "$BRAINSTEM_HOME/src" log --oneline -1 -- "rapp_brainstem/agents/$fname" >/dev/null 2>&1 && \
                       [ -n "$(git -C "$BRAINSTEM_HOME/src" log --oneline -1 -- "rapp_brainstem/agents/$fname" 2>/dev/null)" ]; then
                        echo -e "  ${YELLOW}⚠${NC} Skipping deleted repo agent: $fname"
                        continue
                    fi
                    cp "$agent_file" "$AGENTS_DIR/$fname"
                    restored=$((restored + 1))
                done
                if [ $restored -gt 0 ]; then
                    echo -e "  ${GREEN}✓${NC} Restored $restored custom agent(s) + soul + config"
                else
                    echo -e "  ${GREEN}✓${NC} Restored soul + config"
                fi
            fi

            # 4. Clean up backup
            rm -rf "$BACKUP"
            echo -e "  ${GREEN}✓${NC} Upgrade complete: v${LOCAL_VER} → v${REMOTE_VER}"
        fi
    else
        echo "  Fresh install — cloning repository..."
        rm -rf "$BRAINSTEM_HOME/src" 2>/dev/null || true
        # Full clone of kody-w/RAPP — engine, swarm, worker, installer, pages,
        # tests. The rapp_store catalog is in a separate repo, fetched at
        # runtime via RAPPSTORE_URL.
        git clone --quiet "$REPO_URL" "$BRAINSTEM_HOME/src"
        if [ -n "$PIN_TAG" ]; then
            cd "$BRAINSTEM_HOME/src"
            if git checkout --quiet "$PIN_TAG" 2>/dev/null; then
                echo -e "  ${GREEN}✓${NC} Checked out tag ${PIN_TAG}"
            else
                echo -e "  ${YELLOW}Warning: Tag ${PIN_TAG} not found — staying on main${NC}"
            fi
        fi
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

install_binder_locally() {
    # Binder is baked into the kernel — rapp_brainstem/utils/services/binder_service.py
    # ships with the brainstem itself. If it's missing (e.g. user uninstalled
    # the binder rapp via the UI, which deleted its own service file as a
    # rapp side-effect), restore from git HEAD so /api/binder/* keeps
    # working. This is non-destructive — it only writes if the file is gone.
    local src_dir="$BRAINSTEM_HOME/src/rapp_brainstem"
    local services="$src_dir/utils/services"
    local kernel_binder="$services/binder_service.py"
    mkdir -p "$services"
    if [ -f "$kernel_binder" ]; then
        # Happy path — binder file shipped with the kernel and is still
        # there. The user doesn't need to know about a default that
        # behaved as expected; this branch stays silent so the install
        # output only mentions the binder when something was actually
        # done (restore, copy, or warn).
        :
    elif [ -d "$BRAINSTEM_HOME/src/.git" ] && \
         git -C "$BRAINSTEM_HOME/src" cat-file -e HEAD:rapp_brainstem/utils/services/binder_service.py 2>/dev/null; then
        # File is in git HEAD but missing on disk — restore it. Most common
        # cause: user uninstalled the binder rapp from the catalog, which
        # nuked the kernel-baked file as a side-effect. Works with sparse
        # checkout too — git keeps the blob in the object DB.
        git -C "$BRAINSTEM_HOME/src" checkout HEAD -- rapp_brainstem/utils/services/binder_service.py 2>/dev/null
        echo -e "  ${GREEN}OK${NC} Binder restored from git HEAD"
    else
        echo -e "  ${YELLOW}!${NC} binder_service.py missing - package manager unavailable"
    fi
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
    echo "=== End doctor report ==="
}

cmd_help() {
    cat <<EOF
Usage: brainstem [COMMAND]

With no command, starts the service and opens the browser. All the
commands below work whether the background service is installed or not.

  start     Start the background service (or foreground if no service)
  stop      Stop the background service
  restart   Restart the background service
  status    One-line health check + service state
  logs      Tail the service log
  doctor    Paste-to-support troubleshooting dump
  run       Run the brainstem in the foreground (for debugging)
  open      Open http://localhost:7071 in your browser
  help      Show this message
EOF
}

case "${1:-default}" in
    start)   cmd_start ;;
    stop)    cmd_stop ;;
    restart) cmd_restart ;;
    status)  cmd_status ;;
    logs)    cmd_logs ;;
    doctor)  cmd_doctor ;;
    run)     shift; cmd_run "$@" ;;
    open)    cmd_open ;;
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

    # Always pull latest code before launching — ensure we're on main
    if [ -d "$BRAINSTEM_HOME/src/.git" ]; then
        cd "$BRAINSTEM_HOME/src"
        local current_branch
        current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
        if [ "$current_branch" != "main" ]; then
            git stash --quiet --include-untracked 2>/dev/null || true
            git checkout main --quiet 2>/dev/null || true
        fi
        git fetch --quiet origin main 2>/dev/null || true
        git reset --hard origin/main --quiet 2>/dev/null || true
        # NEVER `git clean rapp_brainstem/agents/` — that directory is the
        # user's workspace (Article XVII) and contains rapplications they
        # installed via binder. git clean would wipe them on every upgrade.
        # The git reset above already restores any tracked files in agents/;
        # untracked files (the user's installed agents) stay put.
    fi

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

    # Check if this is an upgrade of an existing install
    if [ -d "$BRAINSTEM_HOME/src/.git" ]; then
        echo "Checking for updates..."
        if ! check_for_upgrade; then
            # VERSION matches, but UI changes and kernel-service updates
            # ship without version bumps — pull latest origin/main anyway
            # so a curl|bash always lands on the freshest files. Fast-
            # forward only: we never clobber locally modified files
            # (.env, runtime-installed agents, user data).
            if cd "$BRAINSTEM_HOME/src" 2>/dev/null; then
                git remote set-url origin "$REPO_URL" 2>/dev/null || true
                git fetch --quiet origin main 2>/dev/null || true
                local before_sha after_sha
                before_sha=$(git rev-parse HEAD 2>/dev/null)
                if git merge --ff-only --quiet origin/main 2>/dev/null; then
                    after_sha=$(git rev-parse HEAD 2>/dev/null)
                    if [ "$before_sha" != "$after_sha" ]; then
                        echo -e "  ${GREEN}✓${NC} Pulled latest UI / kernel files (${before_sha:0:7} → ${after_sha:0:7})"
                    fi
                else
                    echo -e "  ${YELLOW}⚠${NC} Could not fast-forward — local changes blocking. Run 'git -C $BRAINSTEM_HOME/src status' to inspect."
                fi
                cd - >/dev/null
            fi
            check_prereqs
            setup_venv
            ensure_deps
            install_cli
            create_env
            install_binder_locally
            export PATH="$BRAINSTEM_BIN:/opt/homebrew/bin:/usr/local/bin:$PATH"
            launch_brainstem
            exit $?  # launch uses exec, but guard against fall-through
        fi
        # Upgrade available — fall through to full install path
    fi

    check_prereqs
    install_brainstem
    setup_venv
    setup_deps
    install_cli
    create_env
    install_binder_locally
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
