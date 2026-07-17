#!/usr/bin/env bash
set -euo pipefail

# Target-owned installer for the immutable grail kernel. The upstream tag is
# transport only: all three authoritative bytes must match KERNEL_PIN.json.
KERNEL_REPOSITORY="https://github.com/kody-w/rapp-installer.git"
KERNEL_TAG="brainstem-v0.6.9"
BRAINSTEM_HOME="${BRAINSTEM_HOME:-$HOME/.brainstem}"
SRC_DIR="$BRAINSTEM_HOME/src"
KERNEL_DIR="$SRC_DIR/rapp_brainstem"
VENV_DIR="$BRAINSTEM_HOME/venv"
BIN_DIR="${BRAINSTEM_BIN:-$HOME/.local/bin}"
STAGE_DIR="$BRAINSTEM_HOME/.install-stage-$$"

retire() {
    printf '%s\n' \
        "RAPP installer: 410 Gone" \
        "$1" \
        "No pinned kernel byte was changed." >&2
    exit 78
}

hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        "$PYTHON_CMD" - "$1" <<'PY'
import hashlib
import sys

with open(sys.argv[1], "rb") as source:
    print(hashlib.sha256(source.read()).hexdigest())
PY
    fi
}

find_python() {
    local candidate
    for candidate in python3.11 python3.12 python3.13 python3; do
        command -v "$candidate" >/dev/null 2>&1 || continue
        if "$candidate" -c \
            'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
            >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

verify_kernel() {
    local root="$1"
    local expected relative actual
    while read -r expected relative; do
        [ -f "$root/$relative" ] ||
            retire "Pinned file is missing: $relative"
        actual="$(hash_file "$root/$relative")"
        [ "$actual" = "$expected" ] ||
            retire "Pinned file hash mismatch: $relative"
    done <<'PINS'
a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71 rapp_brainstem/brainstem.py
701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb rapp_brainstem/agents/basic_agent.py
13eb74b44be6e3a85a0efa0dedf56aec05e9e50140e1c8bbc0d0fbd8097b0717 rapp_brainstem/VERSION
PINS
}

cleanup() {
    [ ! -e "$STAGE_DIR" ] || rm -rf -- "$STAGE_DIR"
}
trap cleanup EXIT

case "$BRAINSTEM_HOME" in
    ""|"/") retire "Unsafe BRAINSTEM_HOME." ;;
esac
case "${1:-}" in
    ""|--verify-only) ;;
    *) retire "Unsupported installer option: $1" ;;
esac

command -v git >/dev/null 2>&1 || retire "Git is required."
PYTHON_CMD="$(find_python)" || retire "Python 3.11 or newer is required."

if [ -e "$SRC_DIR" ]; then
    [ -d "$SRC_DIR" ] || retire "Existing source path is not a directory."
    verify_kernel "$SRC_DIR"
    printf '%s\n' "Verified existing $KERNEL_TAG kernel; pinned bytes were not rewritten."
else
    [ "${1:-}" != "--verify-only" ] ||
        retire "There is no installed kernel to verify."
    mkdir -p "$BRAINSTEM_HOME"
    [ ! -L "$BRAINSTEM_HOME" ] ||
        retire "BRAINSTEM_HOME must not be a symbolic link."
    git clone --quiet --depth 1 --single-branch --branch "$KERNEL_TAG" \
        "$KERNEL_REPOSITORY" "$STAGE_DIR" ||
        retire "Could not fetch exact tag $KERNEL_TAG."
    [ "$(git -C "$STAGE_DIR" describe --tags --exact-match 2>/dev/null)" = "$KERNEL_TAG" ] ||
        retire "Fetched checkout is not exact tag $KERNEL_TAG."
    verify_kernel "$STAGE_DIR"
    mv "$STAGE_DIR" "$SRC_DIR"
    printf '%s\n' "Installed and verified immutable kernel $KERNEL_TAG."
fi

[ "${1:-}" != "--verify-only" ] || exit 0

if [ ! -d "$VENV_DIR" ]; then
    "$PYTHON_CMD" -m venv "$VENV_DIR"
fi
"$VENV_DIR/bin/python" -m pip install --quiet --disable-pip-version-check \
    -r "$KERNEL_DIR/requirements.txt"

if [ ! -f "$KERNEL_DIR/.env" ] && [ -f "$KERNEL_DIR/.env.example" ]; then
    cp "$KERNEL_DIR/.env.example" "$KERNEL_DIR/.env"
fi

mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/brainstem" <<EOF
#!/usr/bin/env bash
cd "$KERNEL_DIR"
exec "$VENV_DIR/bin/python" brainstem.py "\$@"
EOF
chmod 755 "$BIN_DIR/brainstem"

printf '%s\n' \
    "RAPP Brainstem is installed from $KERNEL_TAG." \
    "Run: $BIN_DIR/brainstem" \
    "If needed, add $BIN_DIR to PATH."
