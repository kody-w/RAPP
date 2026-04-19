#!/bin/bash
set -e

# RAPP Tether Installer
# Usage: curl -fsSL https://kody-w.github.io/RAPP/install-tether.sh | bash
#
# Companion to the brainstem installer. Sets up tether/server.py — a
# stdlib-only Python HTTP server that exposes your local *_agent.py files
# to the virtual brainstem at https://kody-w.github.io/RAPP/brainstem/.
# No venv, no pip, no GitHub OAuth — the AI lives in the browser, this
# process just runs your agents.

TETHER_HOME="$HOME/.brainstem-tether"
TETHER_BIN="$HOME/.local/bin"
REPO_URL="https://github.com/kody-w/RAPP.git"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

print_banner() {
    echo ""
    echo -e "${CYAN}"
    echo "  🔗 RAPP Tether"
    echo -e "${NC}"
    echo "  Local agents, browser AI."
    echo "  Routes virtual-brainstem agent calls to this machine."
    echo ""
}

find_python() {
    for cmd in python3 python3.13 python3.12 python3.11 python3.10 python3.9 python3.8; do
        if command -v "$cmd" &> /dev/null; then
            ver=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor:02d}")' 2>/dev/null) || continue
            if [ -n "$ver" ] && [ "$ver" -ge 308 ] 2>/dev/null; then
                echo "$cmd"; return 0
            fi
        fi
    done
    return 1
}

ensure_repo() {
    if [ -d "$TETHER_HOME/.git" ]; then
        echo "  Updating $TETHER_HOME..."
        git -C "$TETHER_HOME" fetch --quiet origin main 2>/dev/null || true
        git -C "$TETHER_HOME" reset --hard --quiet origin/main 2>/dev/null || true
    else
        echo "  Cloning $REPO_URL → $TETHER_HOME..."
        rm -rf "$TETHER_HOME"
        git clone --quiet --depth 1 "$REPO_URL" "$TETHER_HOME"
    fi
}

install_cli() {
    mkdir -p "$TETHER_BIN"
    local python_cmd="$1"
    cat > "$TETHER_BIN/brainstem-tether" << WRAPPER
#!/bin/bash
# RAPP Tether launcher — runs tether/server.py with the bundled agents.
# Edit ~/.brainstem-tether/agents/ to add your own *_agent.py files,
# then re-run \`brainstem-tether\` to pick them up.
exec "$python_cmd" "$TETHER_HOME/tether/server.py" \\
    --agents "$TETHER_HOME/agents" \\
    "\$@"
WRAPPER
    chmod +x "$TETHER_BIN/brainstem-tether"

    # Add to PATH in common shell rcs (only if missing — same idempotent
    # pattern the brainstem installer uses).
    add_to_path() {
        local f="$1"; touch "$f"
        if ! grep -q '\.local/bin' "$f" 2>/dev/null; then
            echo '' >> "$f"
            echo '# RAPP' >> "$f"
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$f"
        fi
    }
    add_to_path "$HOME/.bashrc"
    add_to_path "$HOME/.zshrc"
    add_to_path "$HOME/.bash_profile"
}

main() {
    print_banner

    if ! command -v git &> /dev/null; then
        echo -e "  ${RED}git is required but not installed.${NC}"
        echo "  Install git from https://git-scm.com/ and re-run."
        exit 1
    fi

    PYTHON_CMD=$(find_python) || {
        echo -e "  ${RED}Python 3.8+ is required but not found.${NC}"
        echo "  Install Python from https://python.org and re-run."
        exit 1
    }
    echo "  Python: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"

    ensure_repo
    install_cli "$PYTHON_CMD"

    export PATH="$TETHER_BIN:$PATH"

    echo ""
    echo "═══════════════════════════════════════════════════"
    echo -e "  ${GREEN}✓ RAPP Tether installed!${NC}"
    echo "═══════════════════════════════════════════════════"
    echo ""
    echo "  CLI:    brainstem-tether"
    echo "  Repo:   $TETHER_HOME"
    echo "  Agents: $TETHER_HOME/agents/"
    echo ""
    echo -e "  ${CYAN}Launching tether server now…${NC}"
    echo ""
    exec "$TETHER_BIN/brainstem-tether"
}

main
