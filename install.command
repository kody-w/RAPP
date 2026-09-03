#!/bin/bash
# RAPP_RESTORED_SOURCE_COMMIT=4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6
# RAPP_RESTORED_SOURCE_BLOB=6d444ac6e2303bc5cb694884ad9e4931be959048
# RAPP_RESTORED_TARGET=install.command
# RAPP_RESTORED_GATE_BEGIN
_RAPP_TARGET="install.command"
_RAPP_COMMIT="4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"
_RAPP_BLOB="6d444ac6e2303bc5cb694884ad9e4931be959048"
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
# RAPP Brainstem Installer for macOS
# Double-click this file in Finder to install.

clear
echo ""
echo "  🧠 RAPP Brainstem Installer"
echo "  ============================"
echo ""
echo "  Installing... (this window will become your brainstem server)"
echo ""

curl -fsSL https://kody-w.github.io/rapp-installer/install.sh | bash
