#!/bin/bash
# RAPP_RESTORED_SOURCE_COMMIT=4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6
# RAPP_RESTORED_SOURCE_BLOB=d35d686d3a7f60de4c99cc41bd16a7e0225d7a23
# RAPP_RESTORED_TARGET=community_rapp/install.sh
# RAPP_RESTORED_GATE_BEGIN
_RAPP_TARGET="community_rapp/install.sh"
_RAPP_COMMIT="4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"
_RAPP_BLOB="d35d686d3a7f60de4c99cc41bd16a7e0225d7a23"
_RAPP_PIN_SHA256="427a37cc914a279b9c32a2ab85be9a19a0046f10f9f503c088a2670b6646e21c"
_rapp_plan() {
    printf '{"schema":"rapp-restored-distribution-source/1.0","target":"%s","mode":"plan","source_commit":"%s","source_blob":"%s","kernel":"kody-w/rapp-installer@brainstem-v0.6.9","kernel_pin_sha256":"%s","apply_permitted":false,"reason":"authenticated-section-13-evidence-unavailable"}\n' \
        "$_RAPP_TARGET" "$_RAPP_COMMIT" "$_RAPP_BLOB" "$_RAPP_PIN_SHA256"
}
_rapp_refuse() {
    printf '410 Gone: %s: %s (RAPP1_STATUS.md)\n' "$_RAPP_TARGET" "$1" >&2
    exit 78
}
_rapp_expect_line() {
    IFS= read -r _rapp_actual || return 1
    [ "$_rapp_actual" = "$1" ]
}
_rapp_expect_last_line() {
    _rapp_actual=""
    IFS= read -r _rapp_actual
    _rapp_status=$?
    [ "$_rapp_status" -ne 0 ] && [ "$_rapp_actual" = "$1" ]
}
_rapp_pin_matches() {
    [ -f "$1" ] || return 1
    {
        _rapp_expect_line '{' &&
        _rapp_expect_line '  "spec": "rapp-distro/1.0",' &&
        _rapp_expect_line '  "distro": "RAPP (the reference distro)",' &&
        _rapp_expect_line '  "kernel": {' &&
        _rapp_expect_line '    "grail": "kody-w/rapp-installer",' &&
        _rapp_expect_line '    "tag": "brainstem-v0.6.9",' &&
        _rapp_expect_line '    "frozen": {' &&
        _rapp_expect_line '      "rapp_brainstem/brainstem.py": "a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71",' &&
        _rapp_expect_line '      "rapp_brainstem/agents/basic_agent.py": "701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb",' &&
        _rapp_expect_line '      "rapp_brainstem/VERSION": "13eb74b44be6e3a85a0efa0dedf56aec05e9e50140e1c8bbc0d0fbd8097b0717"' &&
        _rapp_expect_line '    }' &&
        _rapp_expect_line '  },' &&
        _rapp_expect_line '  "channel": "lts",' &&
        _rapp_expect_line "  \"note\": \"RAPP tracks the grail (kody-w/rapp-installer). Pinned at brainstem-v0.6.9, the grail's current kernel release — a deliberate distro bump from v0.6.0 ordered in kody-w/RAPP#83 (the grail feeds RAPP; RAPP's vendored copy tracks it). Verified byte-identical to the grail tag.\"" &&
        _rapp_expect_last_line '}' &&
        ! IFS= read -r _rapp_extra
    } < "$1"
}
_RAPP_MODE=${1:-plan}
[ "$#" -eq 0 ] || shift
case "$_RAPP_MODE" in
    plan|--plan|inspect|--inspect|check|--check|help|--help|-h)
        _rapp_plan
        exit 0
        ;;
    apply|--apply|run|--run) ;;
    *) _rapp_refuse "explicit plan/check/inspect or gated --apply is required" ;;
esac
_RAPP_ALLOW=0
_RAPP_REQUESTED_TARGET=""
_RAPP_PIN=""
_RAPP_INJECTION=""
_RAPP_APPROVAL=""
_RAPP_EVIDENCE=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --allow-active-effects) _RAPP_ALLOW=1; shift ;;
        --target|--kernel-pin|--reviewed-dependency-injection|--owner-approval|--section13-evidence)
            [ "$#" -ge 2 ] || _rapp_refuse "missing value for $1"
            _rapp_option=$1
            _rapp_value=$2
            shift 2
            case "$_rapp_option" in
                --target) _RAPP_REQUESTED_TARGET=$_rapp_value ;;
                --kernel-pin) _RAPP_PIN=$_rapp_value ;;
                --reviewed-dependency-injection) _RAPP_INJECTION=$_rapp_value ;;
                --owner-approval) _RAPP_APPROVAL=$_rapp_value ;;
                --section13-evidence) _RAPP_EVIDENCE=$_rapp_value ;;
            esac
            ;;
        *) _rapp_refuse "unsupported activation argument: $1" ;;
    esac
done
[ "$_RAPP_ALLOW" -eq 1 ] || _rapp_refuse "--allow-active-effects is required"
[ "$_RAPP_REQUESTED_TARGET" = "$_RAPP_TARGET" ] || _rapp_refuse "target-specific approval target is missing or mismatched"
_rapp_pin_matches "$_RAPP_PIN" || _rapp_refuse "exact KERNEL_PIN.json for kody-w/rapp-installer@brainstem-v0.6.9 is required"
[ -f "$_RAPP_INJECTION" ] || _rapp_refuse "reviewed dependency injection evidence is required"
[ -f "$_RAPP_APPROVAL" ] || _rapp_refuse "target-specific owner approval is required"
[ -f "$_RAPP_EVIDENCE" ] || _rapp_refuse "authenticated fresh section-13 evidence is required"
_rapp_refuse "authenticated fresh section-13 evidence is unavailable"
# RAPP_RESTORED_GATE_END
# RAPP_RESTORED_HISTORICAL_SOURCE_BEGIN
#!/bin/bash
# CommunityRAPP — One-line installer (Hippocampus / Tier 2)
# Usage: curl -fsSL https://raw.githubusercontent.com/kody-w/rapp-installer/main/community_rapp/install.sh | bash
#
# Creates a ready-to-run CommunityRAPP project with persistent memory,
# auto-discovered agents, and GitHub Copilot device-code auth through the UI.
# No API keys, no Azure account, no cloud services needed to start.

set -e

RED="\033[0;31m" GREEN="\033[0;32m" YELLOW="\033[1;33m" BLUE="\033[0;34m" NC="\033[0m"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  RAPP Hippocampus — Local Setup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ── Helpers ─────────────────────────────────────────────────

die() { echo -e "${RED}ERROR: $1${NC}" >&2; exit 1; }

find_python() {
    for cmd in python3.11 python3.12 python3; do
        if command -v "$cmd" &>/dev/null; then
            local ver
            ver=$("$cmd" --version 2>&1 | awk '{print $2}')
            local major minor
            major=$(echo "$ver" | cut -d. -f1)
            minor=$(echo "$ver" | cut -d. -f2)
            if [ "$major" = "3" ] && [ "$minor" -ge 11 ] && [ "$minor" -le 12 ]; then
                echo "$cmd"
                return 0
            fi
        fi
    done
    return 1
}

# ── Prerequisites ───────────────────────────────────────────
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Git
command -v git &>/dev/null || die "Git is required. Install from https://git-scm.com"
echo -e "${GREEN}[OK] Git${NC}"

# Python
PYTHON_CMD=$(find_python) || {
    echo -e "${YELLOW}Python 3.11+ required (3.13+ not supported). Attempting install...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install python@3.11 2>/dev/null || die "Install Python 3.11 via Homebrew: brew install python@3.11"
    else
        sudo apt-get update -qq && sudo apt-get install -y -qq python3.11 python3.11-venv 2>/dev/null || \
        die "Install Python 3.11: https://python.org/downloads/"
    fi
    PYTHON_CMD=$(find_python) || die "Python 3.11-3.12 required. Install from https://python.org"
}
echo -e "${GREEN}[OK] $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))${NC}"

# Azure Functions Core Tools
if ! command -v func &>/dev/null; then
    echo -e "${YELLOW}Installing Azure Functions Core Tools...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew tap azure/functions 2>/dev/null && brew install azure-functions-core-tools@4 2>/dev/null || \
        die "Install Azure Functions Core Tools: brew tap azure/functions && brew install azure-functions-core-tools@4"
    else
        if command -v npm &>/dev/null; then
            npm install -g azure-functions-core-tools@4 2>/dev/null || \
            die "Install Azure Functions Core Tools: npm install -g azure-functions-core-tools@4"
        else
            die "Install Node.js and Azure Functions Core Tools: https://learn.microsoft.com/azure/azure-functions/functions-run-local"
        fi
    fi
fi
echo -e "${GREEN}[OK] Azure Functions Core Tools${NC}"

# ── Project name ────────────────────────────────────────────

PROJECT_NAME="${1:-}"
if [ -z "$PROJECT_NAME" ]; then
    echo ""
    printf "Project name (e.g. my-project): "
    read -r PROJECT_NAME
    [ -z "$PROJECT_NAME" ] && die "Project name is required."
fi

if ! echo "$PROJECT_NAME" | grep -qE '^[a-z0-9][a-z0-9-]*$'; then
    die "Invalid name '$PROJECT_NAME'. Use lowercase letters, numbers, and hyphens."
fi

PROJECTS_DIR="${RAPP_PROJECTS_DIR:-$HOME/rapp-projects}"
PROJECT_DIR="$PROJECTS_DIR/$PROJECT_NAME"

[ -d "$PROJECT_DIR" ] && die "Project '$PROJECT_NAME' already exists at $PROJECT_DIR"

# ── Clone ───────────────────────────────────────────────────
echo ""
echo -e "${YELLOW}Creating project '$PROJECT_NAME'...${NC}"

mkdir -p "$PROJECTS_DIR"

echo -e "${YELLOW}Cloning CommunityRAPP...${NC}"
git clone --depth 1 --quiet https://github.com/kody-w/CommunityRAPP.git "$PROJECT_DIR"
echo -e "${GREEN}[OK] Cloned${NC}"

# ── Venv + deps ─────────────────────────────────────────────
echo -e "${YELLOW}Creating virtual environment...${NC}"
"$PYTHON_CMD" -m venv "$PROJECT_DIR/.venv"

echo -e "${YELLOW}Installing dependencies...${NC}"
"$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt" --quiet 2>/dev/null
echo -e "${GREEN}[OK] Dependencies installed${NC}"

# ── Settings ────────────────────────────────────────────────
if [ -f "$PROJECT_DIR/local.settings.template.json" ]; then
    cp "$PROJECT_DIR/local.settings.template.json" "$PROJECT_DIR/local.settings.json"
fi

# ── Port + start script ────────────────────────────────────
BASE_PORT=7072
PORT=$BASE_PORT

if [ -f "$PROJECTS_DIR/.hatchery.json" ]; then
    max=$(grep -o '"port": [0-9]*' "$PROJECTS_DIR/.hatchery.json" 2>/dev/null | awk '{print $2}' | sort -n | tail -1)
    if [ -n "$max" ] && [ "$max" -ge "$PORT" ]; then
        PORT=$((max + 1))
    fi
fi

cat > "$PROJECT_DIR/start.sh" << EOF
#!/usr/bin/env bash
cd "\$(dirname "\$0")"
source .venv/bin/activate
func start --port $PORT
EOF
chmod +x "$PROJECT_DIR/start.sh"

cat > "$PROJECT_DIR/start.ps1" << EOF
\$ErrorActionPreference = 'Stop'
Set-Location \$PSScriptRoot
.venv\\Scripts\\Activate.ps1
func start --port $PORT
EOF

# Inject port into chat UI
if [ -f "$PROJECT_DIR/index.html" ]; then
    sed -i '' "s|</head>|<script>window.__RAPP_PORT__='${PORT}';</script></head>|" "$PROJECT_DIR/index.html" 2>/dev/null || \
    sed -i "s|</head>|<script>window.__RAPP_PORT__='${PORT}';</script></head>|" "$PROJECT_DIR/index.html" 2>/dev/null || true
fi

# Remove hatchery/ (it's for brainstem distribution, not the running project)
rm -rf "$PROJECT_DIR/hatchery" 2>/dev/null || true

# ── Business Mode UI (first hatch deploys it) ──────────────
BIZ_HTML="$PROJECTS_DIR/business.html"
if [ ! -f "$BIZ_HTML" ]; then
    curl -fsSL "https://raw.githubusercontent.com/kody-w/CommunityRAPP/main/business.html" -o "$BIZ_HTML" 2>/dev/null || true
fi

# ── Update manifest ─────────────────────────────────────────
MANIFEST="$PROJECTS_DIR/.hatchery.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ -f "$MANIFEST" ]; then
    "$PYTHON_CMD" -c "
import json
with open('$MANIFEST', 'r') as f:
    data = json.load(f)
data.setdefault('projects', {})['$PROJECT_NAME'] = {
    'path': '$PROJECT_DIR',
    'port': $PORT,
    'created_at': '$TIMESTAMP',
    'python': '$PYTHON_CMD'
}
with open('$MANIFEST', 'w') as f:
    json.dump(data, f, indent=2)
"
else
    cat > "$MANIFEST" << EOF
{
  "projects": {
    "$PROJECT_NAME": {
      "path": "$PROJECT_DIR",
      "port": $PORT,
      "created_at": "$TIMESTAMP",
      "python": "$PYTHON_CMD"
    }
  }
}
EOF
fi

# ── Done ────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Project '$PROJECT_NAME' is ready!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "  Location:  $PROJECT_DIR"
echo "  Port:      $PORT"
echo "  Python:    $PYTHON_CMD"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start it:"
echo "     cd $PROJECT_DIR && ./start.sh"
echo ""
echo "  2. Open the chat UI:"
echo "     open $PROJECT_DIR/index.html"
echo ""
echo "  3. Send a message — the UI walks you through GitHub auth."
echo "     No API keys needed."
echo ""
if [ -f "$BIZ_HTML" ]; then
echo "  4. Business Mode (multi-instance side-by-side):"
echo "     open $BIZ_HTML"
echo ""
fi
echo "  When you're ready for Azure:"
echo "     Edit $PROJECT_DIR/local.settings.json"
echo "     Then: func azure functionapp publish YOUR_APP --build remote"
echo ""
