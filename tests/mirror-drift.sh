#!/usr/bin/env bash
#
# Read-only immutable-grail verification.
#
# KERNEL_PIN.json is the authority for the repository, tag, paths, and hashes.
# This check compares local bytes and the exact pinned remote tag. It never
# follows a moving branch and never recommends overwriting immutable files.
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PIN_PATH="$REPO_ROOT/KERNEL_PIN.json"

pin_meta="$(
    python3 - "$PIN_PATH" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    pin = json.load(handle)
kernel = pin["kernel"]
print(f"{kernel['grail']}\t{kernel['tag']}")
PY
)"
IFS=$'\t' read -r GRAIL_REPO GRAIL_TAG <<<"$pin_meta"

if [[ "$GRAIL_TAG" != "brainstem-v0.6.9" ]]; then
    echo "ERROR KERNEL_PIN.json no longer names brainstem-v0.6.9" >&2
    exit 1
fi

pin_files="$(
    python3 - "$PIN_PATH" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    frozen = json.load(handle)["kernel"]["frozen"]
if not isinstance(frozen, dict) or not frozen:
    raise SystemExit("kernel.frozen must be a non-empty object")
for path, digest in frozen.items():
    print(f"{path}\t{digest}")
PY
)"

GRAIL_RAW="https://raw.githubusercontent.com/$GRAIL_REPO/$GRAIL_TAG"
failed=0

while IFS=$'\t' read -r path expected_sha; do
    [[ -n "$path" ]] || continue
    local_path="$REPO_ROOT/$path"
    if [[ ! -f "$local_path" ]]; then
        echo "MISSING local pinned file: $path"
        failed=1
        continue
    fi

    local_sha="$(shasum -a 256 "$local_path" | awk '{print $1}')"
    if [[ "$local_sha" == "$expected_sha" ]]; then
        echo "OK    local  $path"
    else
        echo "DRIFT local  $path (expected $expected_sha, got $local_sha)"
        failed=1
    fi

    remote_url="$GRAIL_RAW/$path"
    if remote_sha="$(curl -fsSL "$remote_url" | shasum -a 256 | awk '{print $1}')"; then
        if [[ "$remote_sha" == "$expected_sha" ]]; then
            echo "OK    pinned $path"
        else
            echo "DRIFT pinned $path (expected $expected_sha, got $remote_sha)"
            failed=1
        fi
    else
        echo "UNAVAILABLE pinned source: $remote_url"
        failed=1
    fi
done <<<"$pin_files"

if [[ "$failed" -ne 0 ]]; then
    echo
    echo "Read-only grail verification failed."
    echo "Do not overwrite immutable bytes; investigate KERNEL_PIN authority or source availability."
    exit 1
fi

echo
echo "Pinned grail bytes match KERNEL_PIN.json and $GRAIL_REPO@$GRAIL_TAG."
