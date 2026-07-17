#!/usr/bin/env bash
# initialize-variant.sh — for variants spawned directly from kody-w/RAPP
# (the species root) via GitHub's "Use this template" flow.
#
# Run from inside the freshly-created repository's working tree.
#
# Single-parent rule (Constitution Article XXXIV): a variant's parent is
# the repo whose code it inherited — no exceptions. This script ALWAYS
# sets parent_rappid to rapp's species root rappid, because if you got
# here, you templated from RAPP. Variants templated from a downstream
# RAPP variant (e.g., wildhaven-ai-homes-twin) should use that
# downstream's installer, not this one.
#
# What it does:
#   1. Verifies this is an uninitialized template clone (via lineage_check)
#   2. Generates a fresh rappid (UUIDv4)
#   3. Updates the child lineage fields of rappid.json and removes inherited
#      root-only migration/re-anchor evidence
#   4. Prints next-step guidance
#
# What it does NOT do (rule: never overwrite local data):
#   - Does not touch any content files (README, CLAUDE.md, agents,
#     pages, rapp_brainstem internals, etc.). The variant inherits
#     RAPP's content as a starting point; edit it manually as the
#     variant takes its own shape.
#   - Does not delete or rewrite kind/description/private_companion or other
#     product metadata. Only lineage pointers, unattested child state, and
#     reserved root-only evidence fields are changed.

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)"

if [ ! -f rappid.json ]; then
    echo "FAIL: no rappid.json at repo root. This script must run inside a"
    echo "      repo created from the kody-w/RAPP template."
    exit 1
fi

# ── Identity (hardcoded — single-parent rule) ────────────────────────────

# Species root — the canonical §6.1 identifier for kody-w/RAPP (lowercase owner/
# slug, full 64-hex domain-separated tail; never 32-hex, never sha256(name)).
# `kind` (prototype) lives in the species-root rappid.json record, not the string.
PARENT_RAPPID="rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9"
PARENT_REPO="https://github.com/kody-w/RAPP.git"

# ── Freshness check via lineage_check.py ─────────────────────────────────

lineage_status() {
python3 - <<'PYEOF'
import json, sys
sys.path.insert(0, "rapp_brainstem/utils")
try:
    from lineage_check import check_lineage
    info = check_lineage()
    print(info["status"])
except Exception as e:
    print(f"error:{e}")
PYEOF
}

reuse_existing() {
    EXISTING_RAPPID="$(python3 - <<'PYEOF'
import json

with open("rappid.json", encoding="utf-8") as handle:
    print(json.load(handle)["rappid"])
PYEOF
)"
    echo "UNCHANGED: this variant is already initialized."
    echo "           Reusing mint-once identity: $EXISTING_RAPPID"
}

LINEAGE_STATUS="$(lineage_status)"

case "$LINEAGE_STATUS" in
    variant_uninitialized)
        : # Expected — proceed
        ;;
    self|master)
        echo "FAIL: this IS the rapp species-root repo itself. Refusing to"
        echo "      reinitialize the species root. If you meant to create a"
        echo "      variant, click 'Use this template' on GitHub first, then"
        echo "      run this script inside the new repo."
        exit 1
        ;;
    variant_initialized)
        reuse_existing
        exit 0
        ;;
    lineage_mismatch|no_rappid|error:*)
        echo "FAIL: lineage check returned: $LINEAGE_STATUS"
        echo "      Run: python3 rapp_brainstem/utils/lineage_check.py for details."
        exit 1
        ;;
    *)
        echo "FAIL: unexpected lineage status: $LINEAGE_STATUS"
        exit 1
        ;;
esac

# ── Variant name ─────────────────────────────────────────────────────────

DEFAULT_NAME="$(basename "$(git rev-parse --show-toplevel)")"
read -p "Variant name (default: $DEFAULT_NAME): " VARIANT_NAME
VARIANT_NAME="${VARIANT_NAME:-$DEFAULT_NAME}"

# ── Serialize initialization and recheck ─────────────────────────────────

GIT_DIR="$(git rev-parse --absolute-git-dir 2>/dev/null)"
LOCK_DIR="$GIT_DIR/rapp-initialize.lock"
LOCK_HELD=0

release_lock() {
    if [ "$LOCK_HELD" -eq 1 ]; then
        rmdir "$LOCK_DIR" 2>/dev/null || true
        LOCK_HELD=0
    fi
}
trap release_lock EXIT
trap 'exit 130' HUP INT TERM

LOCK_ATTEMPTS=0
until mkdir "$LOCK_DIR" 2>/dev/null; do
    LOCK_ATTEMPTS=$((LOCK_ATTEMPTS + 1))
    if [ "$LOCK_ATTEMPTS" -ge 300 ]; then
        echo "FAIL: timed out waiting for repository initialization lock."
        exit 1
    fi
    sleep 0.1
done
LOCK_HELD=1

LOCKED_LINEAGE_STATUS="$(lineage_status)"
case "$LOCKED_LINEAGE_STATUS" in
    variant_uninitialized)
        : # This process owns the only permitted mint.
        ;;
    variant_initialized)
        reuse_existing
        exit 0
        ;;
    *)
        echo "FAIL: lineage changed while waiting for the initialization lock:"
        echo "      $LOCKED_LINEAGE_STATUS"
        exit 1
        ;;
esac

# ── Generate rappid ──────────────────────────────────────────────────────

# Canonical RAPP §6.1 rappid: self-locating `rappid:@<owner>/<slug>:<64hex>`.
# owner/slug derived from this repo's git remote and validated against the grammar;
# the 64-hex tail is Hb("rapp/1:rappid", uuid4) — keyless, domain-separated, full
# 256-bit (never a 32-hex UUID, never sha256(name)). The variant `kind`/role lives
# in the rappid.json record (set below), not the string.
_REMOTE_URL="$(git config --get remote.origin.url 2>/dev/null || true)"
NEW_RAPPID="$(python3 - "$_REMOTE_URL" <<'PYEOF'
import sys
from rapp1_core import mint_keyless_rappid

url = sys.argv[1].rstrip("/").removesuffix(".git")
for prefix in (
    "https://github.com/",
    "http://github.com/",
    "git@github.com:",
    "ssh://git@github.com/",
):
    if url.startswith(prefix):
        location = url[len(prefix):]
        break
else:
    raise SystemExit("FAIL: origin is not a recognized GitHub repository URL")
parts = location.split("/")
if len(parts) != 2:
    raise SystemExit("FAIL: origin does not identify one owner/repository")
print(mint_keyless_rappid(parts[0], parts[1]))
PYEOF
)"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

PARENT_COMMIT="$(curl -fsSL "https://api.github.com/repos/kody-w/RAPP/commits/main" 2>/dev/null \
    | python3 -c "import json, sys; d=json.load(sys.stdin); print(d.get('sha',''))" 2>/dev/null || echo "")"

# ── Update child identity while preserving product metadata ─────────────

python3 - "$NEW_RAPPID" "$PARENT_RAPPID" "$PARENT_REPO" "$PARENT_COMMIT" "$NOW" "$VARIANT_NAME" <<'PYEOF'
import json
import os
import sys
from pathlib import Path

(rappid, parent_rappid, parent_repo, parent_commit, born_at, name) = sys.argv[1:7]

target = Path("rappid.json")
with target.open(encoding="utf-8") as f:
    data = json.load(f)

# Preserve description, kind, private_companion, and arbitrary product
# metadata. Reserved underscore-prefixed migration, legacy, re-anchor, and
# attestation notes describe only the template root and must not follow a
# freshly minted child.
root_only_fields = {
    "_migrated_from",
    "_parent_migrated_from",
    "_legacy_uuid",
    "_legacy_uuid_note",
    "_attestation_note",
    "_attestation",
    "_migration",
    "_migrated",
    "_legacy",
    "_provenance",
    "_root_provenance",
    "_root_attestation",
    "_attested_by",
    "_reanchor",
    "_re_anchor",
}
root_only_prefixes = (
    "_migrated_",
    "_migration_",
    "_legacy_",
    "_reanchor_",
    "_re_anchor_",
    "_attestation_",
    "_provenance_",
    "_root_provenance_",
    "_root_attestation_",
    "_attested_",
)
for key in tuple(data):
    if key in root_only_fields or key.startswith(root_only_prefixes):
        del data[key]

data["rappid"] = rappid
data["parent_rappid"] = parent_rappid
data["parent_repo"] = parent_repo
data["parent_commit"] = parent_commit or None
data["born_at"] = born_at
data["name"] = name
data["role"] = "variant"
# Eternity standard: `kind` lives in the record (not the rappid string).
data.setdefault("kind", "variant")
data["schema"] = "rapp/1"
# The fresh child has no inherited or fabricated attestation/re-anchor.
data["attestation"] = None

encoded = (json.dumps(data, indent=2) + "\n").encode("utf-8")
mode = target.stat().st_mode & 0o777
temporary = target.with_name(f".{target.name}.initialize-{os.getpid()}")
try:
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        mode,
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, target)
    directory = os.open(".", os.O_RDONLY)
    try:
        try:
            os.fsync(directory)
        except OSError:
            pass
    finally:
        os.close(directory)
finally:
    try:
        temporary.unlink()
    except FileNotFoundError:
        pass
PYEOF

echo ""
echo "✓ rappid.json updated:"
echo "    rappid:         $NEW_RAPPID"
echo "    parent_rappid:  $PARENT_RAPPID  (rapp species root)"
echo "    parent_repo:    $PARENT_REPO"
echo "    parent_commit:  ${PARENT_COMMIT:-(could not resolve from network)}"
echo "    born_at:        $NOW"
echo "    name:           $VARIANT_NAME"

# ── Print next-step guidance ─────────────────────────────────────────────

REMOTE_URL="$(git config --get remote.origin.url 2>/dev/null || echo '')"

echo ""
echo "──────────────────────────────────────────────────────────────────────"
echo " Variant initialized as a direct child of rapp."
echo "──────────────────────────────────────────────────────────────────────"
echo ""
echo " Your variant inherits the entire RAPP repo layout — kernel, brainstem,"
echo " swarm, pages, installer — as content. The installer ONLY changed the"
echo " lineage fields in rappid.json; nothing else was touched. Edit local"
echo " files as the variant takes its own shape."
echo ""
echo " Next steps:"
echo "   1. Edit README.md / CLAUDE.md / rappid.json description to reflect"
echo "      your variant (the installer left them as-is)."
echo "   2. Remove components you don't need (rapp_swarm, pages, etc.) by"
echo "      editing them locally — the installer will not delete files."
echo "   3. If you want your variant to be a template too:"
echo "        gh repo edit \$(echo \"$REMOTE_URL\" | sed 's|.*github.com[:/]||;s|\\.git\$||') --template=true"
echo "      Then add YOUR rappid + canonical owner/repo to the"
echo "      KNOWN_TEMPLATE_REPOS dict in rapp_brainstem/utils/lineage_check.py"
echo "      so descendants of YOUR variant can detect uninitialized clones."
echo "   4. Commit + push:"
echo "        git add -A && git commit -m 'init: $VARIANT_NAME' && git push"
echo ""
echo " Lineage walk: your_rappid → $PARENT_RAPPID (rapp species root)"
echo ""
