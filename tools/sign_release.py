#!/usr/bin/env python3
"""sign_release.py — ed25519 signing for rapp_kernel/manifest.json.

Implements CONSTITUTION Article XXXIV.7 "Signed releases and variant
attestation". ed25519 chosen as the canonical method (acceptable per the
article's open list); deterministic, fast verify, 32-byte pubkey, 64-byte
signature.

Produces a sigstore-bundle-shaped sidecar at the path supplied by the
caller; verifier walks `manifest.signing.verification_uri` to resolve the
public key and re-checks the signature locally.

Auto-installs `cryptography` on first run via pip — same pattern the
brainstem uses for agent dependencies (CLAUDE.md "Missing pip
dependencies are auto-installed at import time").

Usage:
    # Generate a fresh signing keypair (one-time per maintainer)
    python3 tools/sign_release.py keygen --out ~/.rapp/release-keys

    # Sign a kernel manifest
    python3 tools/sign_release.py sign \\
        --in   rapp_kernel/manifest.json \\
        --out  rapp_kernel/manifest.sig \\
        --key  ~/.rapp/release-keys/private.pem

    # Verify a signed manifest
    python3 tools/sign_release.py verify \\
        --in       rapp_kernel/manifest.json \\
        --sig      rapp_kernel/manifest.sig \\
        --pubkey   ~/.rapp/release-keys/public.pem
"""

from __future__ import annotations
# RAPP_RESTORED_GATE_BEGIN
_RAPP_RESTORED_TARGET = "tools/sign_release.py"
_RAPP_RESTORED_SOURCE_COMMIT = "4f6c14bbdf5b2d43887a9c7ab9cbda8c075f0dd6"
_RAPP_RESTORED_SOURCE_BLOB = "9cad84a907496205492ee69b3cb2f3517fbeb85e"
_RAPP_KERNEL_PIN_SHA256 = "427a37cc914a279b9c32a2ab85be9a19a0046f10f9f503c088a2670b6646e21c"
_RAPP_FROZEN = {
    "rapp_brainstem/brainstem.py": "a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71",
    "rapp_brainstem/agents/basic_agent.py": "701488bc00d536a7b23295e7da99c62f24e9b00f233daa325886430c736b78eb",
    "rapp_brainstem/VERSION": "13eb74b44be6e3a85a0efa0dedf56aec05e9e50140e1c8bbc0d0fbd8097b0717",
}


def _rapp_restored_plan():
    print(
        '{"schema":"rapp-restored-distribution-source/1.0",'
        f'"target":"{_RAPP_RESTORED_TARGET}","mode":"plan",'
        f'"source_commit":"{_RAPP_RESTORED_SOURCE_COMMIT}",'
        f'"source_blob":"{_RAPP_RESTORED_SOURCE_BLOB}",'
        '"kernel":"kody-w/rapp-installer@brainstem-v0.6.9",'
        f'"kernel_pin_sha256":"{_RAPP_KERNEL_PIN_SHA256}",'
        '"apply_permitted":false,'
        '"reason":"authenticated-section-13-evidence-unavailable"}'
    )


def _rapp_restored_refuse(message):
    print(
        f"410 Gone: {_RAPP_RESTORED_TARGET}: {message} (RAPP1_STATUS.md)",
        file=__import__("sys").stderr,
    )
    return 78


def _rapp_restored_pin_matches(path):
    hashlib_module = __import__("hashlib")
    json_module = __import__("json")
    pathlib_module = __import__("pathlib")
    pin_path = pathlib_module.Path(path)
    try:
        pin_bytes = pin_path.read_bytes()
        pin = json_module.loads(pin_bytes)
    except (OSError, TypeError, ValueError):
        return False
    if hashlib_module.sha256(pin_bytes).hexdigest() != _RAPP_KERNEL_PIN_SHA256:
        return False
    kernel = pin.get("kernel", {})
    if (
        kernel.get("grail") != "kody-w/rapp-installer"
        or kernel.get("tag") != "brainstem-v0.6.9"
        or kernel.get("frozen") != _RAPP_FROZEN
    ):
        return False
    root = pathlib_module.Path(__file__).resolve().parents[1]
    try:
        return all(
            hashlib_module.sha256((root / relative).read_bytes()).hexdigest()
            == digest
            for relative, digest in _RAPP_FROZEN.items()
        )
    except OSError:
        return False


def _rapp_restored_gate(argv):
    argv = list(argv)
    mode = argv.pop(0) if argv else "plan"
    if mode in {"plan", "--plan", "inspect", "--inspect", "check", "--check", "help", "--help", "-h"}:
        _rapp_restored_plan()
        return 0
    if mode not in {"apply", "--apply", "run", "--run"}:
        return _rapp_restored_refuse(
            "explicit plan/check/inspect or gated --apply is required"
        )
    values = {}
    allow_active_effects = False
    while argv:
        option = argv.pop(0)
        if option == "--allow-active-effects":
            allow_active_effects = True
            continue
        if option not in {
            "--target",
            "--kernel-pin",
            "--reviewed-dependency-injection",
            "--owner-approval",
            "--section13-evidence",
        }:
            return _rapp_restored_refuse(
                f"unsupported activation argument: {option}"
            )
        if not argv:
            return _rapp_restored_refuse(f"missing value for {option}")
        values[option] = argv.pop(0)
    if not allow_active_effects:
        return _rapp_restored_refuse("--allow-active-effects is required")
    if values.get("--target") != _RAPP_RESTORED_TARGET:
        return _rapp_restored_refuse(
            "target-specific approval target is missing or mismatched"
        )
    if not _rapp_restored_pin_matches(values.get("--kernel-pin", "")):
        return _rapp_restored_refuse(
            "exact KERNEL_PIN.json for "
            "kody-w/rapp-installer@brainstem-v0.6.9 is required"
        )
    path_class = __import__("pathlib").Path
    for option, label in (
        ("--reviewed-dependency-injection", "reviewed dependency injection"),
        ("--owner-approval", "target-specific owner approval"),
        ("--section13-evidence", "authenticated fresh section-13 evidence"),
    ):
        if not path_class(values.get(option, "")).is_file():
            return _rapp_restored_refuse(f"{label} is required")
    return _rapp_restored_refuse(
        "authenticated fresh section-13 evidence is unavailable"
    )


if __name__ == "__main__":
    raise SystemExit(_rapp_restored_gate(__import__("sys").argv[1:]))
# RAPP_RESTORED_GATE_END

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys


def _ensure_cryptography():
    """Auto-install cryptography on first run (mirrors brainstem agent dep install)."""
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: F401
        return
    except ImportError:
        pass
    print("first-run setup: installing 'cryptography' via pip...", file=sys.stderr)
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "--user", "cryptography"],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        print(f"pip install failed: {e}", file=sys.stderr)
        print("install manually:  pip install --user cryptography", file=sys.stderr)
        sys.exit(2)
    # Ensure user-site is on path
    user_site = subprocess.check_output(
        [sys.executable, "-m", "site", "--user-site"], text=True
    ).strip()
    if user_site and user_site not in sys.path:
        sys.path.insert(0, user_site)


def _load_pem(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def cmd_keygen(args):
    _ensure_cryptography()
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization

    out_dir = os.path.expanduser(args.out)
    os.makedirs(out_dir, exist_ok=True)

    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()

    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    pub_raw = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    fp = hashlib.sha256(pub_raw).hexdigest()[:16]

    priv_path = os.path.join(out_dir, "private.pem")
    pub_path = os.path.join(out_dir, "public.pem")
    fp_path = os.path.join(out_dir, "fingerprint.txt")

    with open(priv_path, "wb") as f: f.write(priv_pem)
    os.chmod(priv_path, 0o600)
    with open(pub_path, "wb") as f: f.write(pub_pem)
    with open(fp_path, "w") as f: f.write(fp + "\n")

    print(json.dumps({
        "ok": True,
        "schema": "rapp-release-key/1.0",
        "private_key": priv_path,
        "public_key": pub_path,
        "fingerprint": fp,
        "note": "Publish public.pem at the URL referenced by manifest.signing.verification_uri",
    }, indent=2))


def cmd_sign(args):
    _ensure_cryptography()
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization

    in_path = os.path.expanduser(args.input)
    out_path = os.path.expanduser(args.out)
    key_path = os.path.expanduser(args.key)

    with open(in_path, "rb") as f:
        body = f.read()
    file_hash = hashlib.sha256(body).hexdigest()

    priv = serialization.load_pem_private_key(_load_pem(key_path), password=None)
    if not isinstance(priv, ed25519.Ed25519PrivateKey):
        print("error: key is not ed25519", file=sys.stderr)
        sys.exit(2)

    sig = priv.sign(body)
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    fp = hashlib.sha256(pub_raw).hexdigest()[:16]

    sidecar = {
        "schema": "rapp-release-signature/1.0",
        "method": "ed25519",
        "signed_file": os.path.basename(in_path),
        "signed_file_sha256": file_hash,
        "signature_b64": base64.b64encode(sig).decode("ascii"),
        "publisher_fingerprint": fp,
        "signed_at": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
    }
    with open(out_path, "w") as f:
        json.dump(sidecar, f, indent=2)
    print(json.dumps({"ok": True, "sidecar": out_path, "fingerprint": fp,
                      "signed_file_sha256": file_hash}, indent=2))


def cmd_verify(args):
    _ensure_cryptography()
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature

    in_path = os.path.expanduser(args.input)
    sig_path = os.path.expanduser(args.sig)
    pub_path = os.path.expanduser(args.pubkey)

    with open(in_path, "rb") as f:
        body = f.read()
    file_hash = hashlib.sha256(body).hexdigest()
    with open(sig_path) as f:
        sidecar = json.load(f)
    pub = serialization.load_pem_public_key(_load_pem(pub_path))
    if not isinstance(pub, ed25519.Ed25519PublicKey):
        print(json.dumps({"ok": False, "error": "pubkey is not ed25519"}))
        sys.exit(2)
    if sidecar.get("signed_file_sha256") != file_hash:
        print(json.dumps({"ok": False, "error": "signed_file_sha256 mismatch",
                          "expected": sidecar.get("signed_file_sha256"),
                          "actual": file_hash}))
        sys.exit(1)
    sig = base64.b64decode(sidecar["signature_b64"])
    try:
        pub.verify(sig, body)
    except InvalidSignature:
        print(json.dumps({"ok": False, "error": "ed25519 signature invalid"}))
        sys.exit(1)

    pub_raw = pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    fp = hashlib.sha256(pub_raw).hexdigest()[:16]
    print(json.dumps({
        "ok": True,
        "signed_file": in_path,
        "signed_file_sha256": file_hash,
        "publisher_fingerprint": fp,
        "method": "ed25519",
    }, indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(description="ed25519 signing for RAPP release manifests (Art. XXXIV.7)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pk = sub.add_parser("keygen", help="Generate a fresh ed25519 keypair")
    pk.add_argument("--out", required=True, help="Output directory for private.pem + public.pem")
    pk.set_defaults(func=cmd_keygen)

    ps = sub.add_parser("sign", help="Sign a manifest file → sidecar")
    ps.add_argument("--in", dest="input", required=True)
    ps.add_argument("--out", required=True)
    ps.add_argument("--key", required=True)
    ps.set_defaults(func=cmd_sign)

    pv = sub.add_parser("verify", help="Verify a signed manifest")
    pv.add_argument("--in", dest="input", required=True)
    pv.add_argument("--sig", required=True)
    pv.add_argument("--pubkey", required=True)
    pv.set_defaults(func=cmd_verify)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()

# RAPP_RESTORED_IMPORT_SEAL_BEGIN
if __name__ != "__main__":
    def _rapp_import_refusal(*_args, **_kwargs):
        raise RuntimeError(
            "imported historical signing entrypoints are unavailable; "
            "use the target-owned CLI plan gate"
        )

    for _rapp_name in (
        "_ensure_cryptography",
        "_load_pem",
        "cmd_keygen",
        "cmd_sign",
        "cmd_verify",
        "main",
    ):
        globals()[_rapp_name] = _rapp_import_refusal
# RAPP_RESTORED_IMPORT_SEAL_END
