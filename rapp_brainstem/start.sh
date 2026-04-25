#!/bin/bash
set -e
cd "$(dirname "$0")"

BRAINSTEM_HOME="$HOME/.brainstem"
VENV_PYTHON="$BRAINSTEM_HOME/venv/bin/python"

# Use venv if available; create it if missing
if [ ! -x "$VENV_PYTHON" ]; then
    echo "Setting up virtual environment..."
    PYTHON_CMD=$(command -v python3.11 || command -v python3.12 || command -v python3.13 || command -v python3)
    "$PYTHON_CMD" -m venv "$BRAINSTEM_HOME/venv" 2>/dev/null || {
        echo "Failed to create venv — run the installer: curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash"
        exit 1
    }
fi

# Install deps if needed
if ! "$VENV_PYTHON" -c "import flask, requests, dotenv" 2>/dev/null; then
    echo "Installing dependencies..."
    "$BRAINSTEM_HOME/venv/bin/pip" install -r requirements.txt -q
fi

# Create .env from example if missing
if [ ! -f .env ]; then
    cp .env.example .env 2>/dev/null || true
fi

# Bootstrap binder from RAPPstore on first launch.
#
# Brainstem ships clean (no pre-installed services). Binder is the
# package manager — it installs everything else, but it can't install
# itself, so start.sh fetches it once on first run. The result is also
# the canary for whether RAPPstore is reachable from this machine; we
# write the outcome to .brainstem_data/bootstrap.json so /health (and
# the chat UI) can surface "RAPPstore offline" instead of a silent
# degradation.
BINDER_PATH="services/binder_service.py"
BINDER_URL="https://raw.githubusercontent.com/kody-w/RAPP/main/rapp_store/binder/binder_service.py"
BINDER_SHA="d393fbf17c9daa2887cadb035a20c4ee5862f660c8816750af5fc75e3db6d1f3"
BOOTSTRAP_FILE=".brainstem_data/bootstrap.json"
mkdir -p .brainstem_data services

write_bootstrap() {
    # $1 = reachable (true|false), $2 = installed (true|false), $3 = error (or empty)
    cat > "$BOOTSTRAP_FILE" <<EOF
{
  "rapp_store_reachable": $1,
  "binder_installed": $2,
  "checked_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "error": $(if [ -z "$3" ]; then echo "null"; else echo "\"$3\""; fi)
}
EOF
}

if [ -f "$BINDER_PATH" ]; then
    # Already installed (from a prior bootstrap). Don't re-check the network on every launch.
    [ -f "$BOOTSTRAP_FILE" ] || write_bootstrap "true" "true" ""
else
    echo "Bootstrapping binder from RAPPstore..."
    if curl -fsSL "$BINDER_URL" -o "$BINDER_PATH.tmp" 2>/dev/null; then
        ACTUAL_SHA=$(shasum -a 256 "$BINDER_PATH.tmp" | cut -d' ' -f1)
        if [ "$ACTUAL_SHA" = "$BINDER_SHA" ]; then
            mv "$BINDER_PATH.tmp" "$BINDER_PATH"
            write_bootstrap "true" "true" ""
            echo "  binder installed."
        else
            rm -f "$BINDER_PATH.tmp"
            write_bootstrap "true" "false" "sha256 mismatch (expected $BINDER_SHA, got $ACTUAL_SHA)"
            echo "  WARNING: binder SHA256 mismatch — install skipped. UI will run without package management."
        fi
    else
        rm -f "$BINDER_PATH.tmp"
        write_bootstrap "false" "false" "rapp_store unreachable"
        echo "  WARNING: RAPPstore unreachable — binder not installed. UI will run without package management."
    fi
fi

exec "$VENV_PYTHON" brainstem.py
