from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VAULT = ROOT / "pages" / "vault"


def test_vault_bundle_is_current_and_byte_exact():
    result = subprocess.run(
        [sys.executable, "tools/build_vault_bundle.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    manifest = json.loads((VAULT / "manifest.json").read_text(encoding="utf-8"))
    bundle = json.loads(
        (VAULT / "content-bundle.json").read_text(encoding="utf-8")
    )
    assert bundle["schema"] == "rapp-vault-content-bundle/1.0"
    assert manifest["runtime_content"] == {
        "bundle": "content-bundle.json",
        "renderer": "marked.min.js",
        "renderer_package": "marked@12.0.2",
        "renderer_sha256": (
            "15fabce5b65898b32b03f5ed25e9f891"
            "a729ad4c0d6d877110a7744aa847a894"
        ),
        "renderer_license": "vendor/marked-LICENSE.txt",
        "network_fallback": False,
        "hash_required": True,
    }
    assert bundle["network_fallback"] is False
    assert bundle["note_count"] == len(manifest["notes"]) == 110
    assert set(bundle["notes"]) == {note["path"] for note in manifest["notes"]}
    for note in manifest["notes"]:
        raw = (VAULT / note["path"]).read_bytes()
        record = bundle["notes"][note["path"]]
        assert record["content"].encode("utf-8") == raw
        assert record["bytes"] == note["bytes"] == len(raw)
        assert (
            record["sha256"]
            == note["sha256"]
            == hashlib.sha256(raw).hexdigest()
        )


def test_vault_and_docs_render_without_remote_runtime_dependencies():
    vault_index = (VAULT / "index.html").read_text(encoding="utf-8")
    vault_runtime = (VAULT / "vault.js").read_text(encoding="utf-8")
    docs_runtime = (
        ROOT / "pages/_site/js/doc-viewer.js"
    ).read_text(encoding="utf-8")
    docs_viewer = (
        ROOT / "pages/docs/viewer.html"
    ).read_text(encoding="utf-8")

    for source in (vault_runtime, docs_runtime, docs_viewer):
        assert "cdn.jsdelivr.net" not in source
        assert "raw.githubusercontent.com" not in source
    assert '<script src="https://cdn.jsdelivr.net' not in vault_index
    assert "raw.githubusercontent.com" not in vault_index
    assert "./marked.min.js" in vault_index
    assert "../vault/marked.min.js" in docs_runtime
    assert "./content-bundle.json" in vault_runtime
    assert "sanitizeHtml" in vault_runtime
    assert "sanitizeHtml" in docs_runtime
    assert "localStorage.removeItem(LS_KEY)" not in vault_runtime
    assert "discardLegacyLocalOverride" not in vault_runtime
    assert "if (local && local.manifest)" not in vault_runtime
    assert "connect-src 'self'" in vault_index
    assert "connect-src 'self'" in docs_viewer
