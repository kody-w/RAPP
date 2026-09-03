#!/bin/bash
# RAPP_RESTORED_SOURCE_COMMIT=925dee4a211965f2582e71a6d2ad75f60a54ea7d
# RAPP_RESTORED_SOURCE_BLOB=2c746543ee4a949adfa991d9bdc0fbd85a7f56ba
# RAPP_RESTORED_TARGET=installer/install-swarm.sh
# RAPP_RESTORED_GATE_BEGIN
_RAPP_TARGET="installer/install-swarm.sh"
_RAPP_COMMIT="925dee4a211965f2582e71a6d2ad75f60a54ea7d"
_RAPP_BLOB="2c746543ee4a949adfa991d9bdc0fbd85a7f56ba"
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
set -e

# RAPP Swarm Server Installer
# Usage: curl -fsSL https://kody-w.github.io/RAPP/installer/install-swarm.sh | bash
#
# Hosts many RAPP swarms behind one local endpoint, routed by swarm_guid +
# user_guid. Stdlib-only Python; no venv, no pip, no Azure runtime needed
# locally. Deploy from the brainstem's "Deploy as Swarm" action.

SWARM_HOME="$HOME/.rapp-swarm"
SWARM_BIN="$HOME/.local/bin"
REPO_URL="https://github.com/kody-w/RAPP.git"

GREEN='\033[0;32m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'

print_banner() {
    echo ""
    echo -e "${CYAN}  🐝 RAPP Swarm Server${NC}"
    echo "  Host many RAPP swarms behind one endpoint, routed by GUID."
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
    SRC="$SWARM_HOME/_repo"
    if [ -d "$SRC/.git" ]; then
        echo "  Updating $SRC..."
        git -C "$SRC" fetch --quiet origin main 2>/dev/null || true
        git -C "$SRC" reset --hard --quiet origin/main 2>/dev/null || true
    else
        echo "  Cloning $REPO_URL → $SRC..."
        rm -rf "$SRC"
        git clone --quiet --depth 1 "$REPO_URL" "$SRC"
    fi
}

install_cli() {
    mkdir -p "$SWARM_BIN"
    local python_cmd="$1"
    cat > "$SWARM_BIN/brainstem-swarm" << WRAPPER
#!/bin/bash
# RAPP Swarm Server launcher.
# Persists swarms to ~/.rapp-swarm/swarms/{guid}/.
exec "$python_cmd" "$SWARM_HOME/_repo/rapp_brainstem/brainstem.py" \\
    --root "$SWARM_HOME" \\
    "\$@"
WRAPPER
    chmod +x "$SWARM_BIN/brainstem-swarm"

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

    command -v git &>/dev/null || {
        echo -e "  ${RED}git is required.${NC} https://git-scm.com/"
        exit 1
    }
    PYTHON_CMD=$(find_python) || {
        echo -e "  ${RED}Python 3.8+ required.${NC} https://python.org"
        exit 1
    }
    echo "  Python: $PYTHON_CMD ($($PYTHON_CMD --version 2>&1))"

    mkdir -p "$SWARM_HOME"
    ensure_repo
    install_cli "$PYTHON_CMD"
    export PATH="$SWARM_BIN:$PATH"

    echo ""
    echo "═══════════════════════════════════════════════════"
    echo -e "  ${GREEN}✓ RAPP Swarm Server installed!${NC}"
    echo "═══════════════════════════════════════════════════"
    echo ""
    echo "  CLI:    brainstem-swarm"
    echo "  Repo:   $SWARM_HOME/_repo"
    echo "  Swarms: $SWARM_HOME/swarms/"
    echo ""
    echo -e "  ${CYAN}Launching swarm server now…${NC}"
    echo ""
    exec "$SWARM_BIN/brainstem-swarm"
}

main
