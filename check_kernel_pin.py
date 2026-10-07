#!/usr/bin/env python3
"""Verify RAPP's canonical kernel.json against the live grail. Stdlib only."""

import hashlib
import json
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


REQUIRED = {"kernel", "sha", "version", "path", "kernel_blob"}
OPTIONAL = {
    "pinned",
    "ui_path",
    "ui_blob",
    "soul_path",
    "soul_blob",
    "contract",
    "rule",
    "vendored",
}
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")


class PinError(Exception):
    pass


def get(url):
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "RAPP-kernel-check"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except (OSError, urllib.error.HTTPError) as exc:
        raise PinError(f"cannot read {url}: {exc}") from exc


def raw(pin, path):
    path = urllib.parse.quote(path, safe="/")
    return get(f"https://raw.githubusercontent.com/{pin['kernel']}/{pin['sha']}/{path}")


def blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def safe_path(value, field):
    if not isinstance(value, str) or not value or value.startswith("/"):
        raise PinError(f"{field} must be a relative repository path")
    path = pathlib.PurePosixPath(value)
    if ".." in path.parts:
        raise PinError(f"{field} must not contain '..'")
    return value


def blob_pair(pin, path_key, blob_key):
    if (path_key in pin) != (blob_key in pin):
        raise PinError(f"{path_key} and {blob_key} must be present together")
    if path_key not in pin:
        return None
    path = safe_path(pin[path_key], path_key)
    expected = pin[blob_key]
    if not isinstance(expected, str) or not HEX40.fullmatch(expected):
        raise PinError(f"{blob_key} must be a 40-hex git blob")
    actual = blob(raw(pin, path))
    if actual != expected:
        raise PinError(f"{blob_key} mismatch for {path}: expected {expected}, got {actual}")
    return path


def verify():
    try:
        pin = json.loads(pathlib.Path("kernel.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PinError(f"cannot load kernel.json: {exc}") from exc
    if not isinstance(pin, dict):
        raise PinError("kernel.json must be a JSON object")
    missing = sorted(REQUIRED - set(pin))
    extra = sorted(set(pin) - REQUIRED - OPTIONAL)
    if missing:
        raise PinError(f"missing required keys: {', '.join(missing)}")
    if extra:
        raise PinError(f"unsupported keys: {', '.join(extra)}")
    if pin["kernel"] != "kody-w/rapp-installer":
        raise PinError("kernel must be kody-w/rapp-installer")
    if not isinstance(pin["sha"], str) or not HEX40.fullmatch(pin["sha"]):
        raise PinError("sha must be a 40-hex commit")
    if not isinstance(pin["version"], str) or not pin["version"]:
        raise PinError("version must be a non-empty string")
    kernel_path = safe_path(pin["path"], "path")
    if not isinstance(pin["kernel_blob"], str) or not HEX40.fullmatch(pin["kernel_blob"]):
        raise PinError("kernel_blob must be a 40-hex git blob")

    commit_url = (
        f"https://api.github.com/repos/{pin['kernel']}/commits/"
        f"{urllib.parse.quote(pin['sha'], safe='')}"
    )
    commit = json.loads(get(commit_url))
    if commit.get("sha") != pin["sha"]:
        raise PinError(f"sha did not resolve exactly: {commit.get('sha')}")
    if blob(raw(pin, kernel_path)) != pin["kernel_blob"]:
        raise PinError("kernel_blob does not match the grail")
    version_path = str(pathlib.PurePosixPath(kernel_path).parent / "VERSION")
    actual_version = raw(pin, version_path).decode().strip()
    if actual_version != pin["version"]:
        raise PinError(f"version mismatch: expected {pin['version']}, got {actual_version}")

    checked = [
        value
        for value in (
            blob_pair(pin, "ui_path", "ui_blob"),
            blob_pair(pin, "soul_path", "soul_blob"),
        )
        if value
    ]
    vendored = pin.get("vendored", {})
    if not isinstance(vendored, dict):
        raise PinError("vendored must be an object")
    for path, expected in sorted(vendored.items()):
        path = safe_path(path, "vendored path")
        if not isinstance(expected, str) or not HEX64.fullmatch(expected):
            raise PinError(f"vendored hash for {path} must be 64-hex sha256")
        upstream = hashlib.sha256(raw(pin, path)).hexdigest()
        if upstream != expected:
            raise PinError(f"vendored pin mismatch for {path}: expected {expected}, got {upstream}")
        local = pathlib.Path(path)
        if not local.is_file() or local.is_symlink():
            raise PinError(f"vendored copy missing: {path}")
        actual = hashlib.sha256(local.read_bytes()).hexdigest()
        if actual != expected:
            raise PinError(f"vendored copy drifted for {path}: expected {expected}, got {actual}")

    print(f"PASS commit {pin['kernel']}@{pin['sha']}")
    print(f"PASS kernel {kernel_path} blob {pin['kernel_blob']}")
    print(f"PASS version {pin['version']} from {version_path}")
    for path in checked:
        print(f"PASS pinned blob {path}")
    for path in sorted(vendored):
        print(f"PASS vendored {path}")
    print("PASS kernel.json")


def main():
    try:
        verify()
    except (PinError, json.JSONDecodeError) as exc:
        print(f"FAIL {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
