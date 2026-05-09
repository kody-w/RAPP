"""rar_loader_agent — universal RAR-style hot-loader.

Per the planted-rules pattern: every neighborhood / twin / place repo
ships a `rar/index.json` (`rapp-rar-index/1.0`) declaring the agents,
organs, senses, and cards required to participate. Joining brainstems
hot-load these into their local agents/ (or organs/ / senses/) directory,
sha256-verified against the published manifest.

Same RAR shape as kody-w/RAR + kody-w/RAPP_Store, but scoped to one
planted repo — making the seed self-sufficient and portable. Any AI that
clones the repo can boot a brainstem from inside it; any AI elsewhere
can hot-load just the participation kit.

Schema: `rapp-rar-loadout/1.0` (the install-result envelope).

Usage:
    # Inspect what would install (default — safe)
    RarLoader.perform(rar_url="https://raw.githubusercontent.com/kody-w/ant-farm/main/rar/index.json")

    # Actually install
    RarLoader.perform(
        rar_url="...",
        dry_run=False,
        target_dir="/path/to/agents",
    )

    # Shortcut form: pass gate_repo
    RarLoader.perform(gate_repo="kody-w/ant-farm")
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request

try:
    from agents.basic_agent import BasicAgent
except ImportError:
    from basic_agent import BasicAgent


_USER_AGENT = "rapp-rar-loader/1.0"
_HTTP_TIMEOUT = 12.0
_DEFAULT_TARGET_DIRS = {
    "agent":        "agents",
    "organ":        "utils/organs",
    "sense":        "utils/senses",
    "card":         "rar/cards",
    "rapplication": "rapps",
}


def _gh_get_text(url: str, timeout: float = _HTTP_TIMEOUT) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return None


def _gh_get_bytes(url: str, timeout: float = _HTTP_TIMEOUT) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _resolve_brainstem_target(kind: str, override: str | None = None) -> str:
    if override:
        return os.path.expanduser(override)
    sub = _DEFAULT_TARGET_DIRS.get(kind, "agents")
    # Walk up from this file's location to the brainstem root.
    here = os.path.dirname(os.path.abspath(__file__))
    bs_root = os.path.dirname(here)  # rapp_brainstem/
    return os.path.join(bs_root, sub)


def _local_cache_path() -> str:
    """Where to cache fetched rar/index.json bodies for offline replay."""
    p = os.path.expanduser("~/.brainstem/rar_cache")
    os.makedirs(p, exist_ok=True)
    return p


def _cache_key(rar_url: str) -> str:
    return os.path.join(_local_cache_path(), _sha256(rar_url.encode())[:16] + ".json")


def fetch_rar_index(rar_url: str, allow_cache: bool = True) -> tuple[dict | None, str]:
    """Fetch rar/index.json. Local-first: if network fails, fall back to cache.

    Returns (index_dict, source) where source ∈ {"network", "cache", "missing"}.
    """
    txt = _gh_get_text(rar_url)
    if txt:
        try:
            d = json.loads(txt)
            try:
                with open(_cache_key(rar_url), "w") as f:
                    f.write(txt)
            except OSError:
                pass
            return d, "network"
        except (ValueError, json.JSONDecodeError):
            pass
    if allow_cache:
        cache = _cache_key(rar_url)
        if os.path.exists(cache):
            try:
                with open(cache) as f:
                    return json.load(f), "cache"
            except (OSError, ValueError):
                pass
    return None, "missing"


def _fetch_and_verify(item: dict) -> tuple[bytes | None, str]:
    """Fetch one item; verify sha256. Returns (bytes, status)."""
    raw_url = item.get("raw_url")
    expected = (item.get("sha256") or "").lower()
    if not raw_url:
        return None, "no_raw_url"
    if not expected:
        return None, "no_sha256_in_manifest"
    body = _gh_get_bytes(raw_url)
    if body is None:
        return None, "fetch_failed"
    actual = _sha256(body)
    if actual != expected:
        return None, f"sha256_mismatch (expected {expected[:12]}…, got {actual[:12]}…)"
    return body, "verified"


def _install_one(item: dict, body: bytes, target_dir: str, dry_run: bool) -> dict:
    file_rel = item.get("file") or os.path.basename(item.get("raw_url", "") or "unknown")
    base_name = os.path.basename(file_rel)
    install_path = os.path.join(target_dir, base_name)
    result = {
        "name": item.get("name"),
        "kind": item.get("kind"),
        "file": file_rel,
        "install_path": install_path,
        "bytes": len(body),
        "sha256": _sha256(body),
        "status": "would_install" if dry_run else "installed",
    }
    if dry_run:
        return result
    try:
        os.makedirs(target_dir, exist_ok=True)
        with open(install_path, "wb") as f:
            f.write(body)
    except OSError as e:
        result["status"] = f"install_error: {e}"
    return result


class RarLoaderAgent(BasicAgent):
    metadata = {
        "name": "RarLoader",
        "description": (
            "Hot-load a planted repo's required participation kit (agents, "
            "organs, senses, cards) from its rar/index.json. sha256-verified "
            "against the published manifest. Local-first: caches fetched "
            "manifests at ~/.brainstem/rar_cache so offline replay works."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "rar_url": {"type": "string",
                            "description": "URL of the rar/index.json to load."},
                "gate_repo": {"type": "string",
                              "description": "Shortcut: <owner>/<repo> → builds the URL automatically."},
                "include_optional": {"type": "boolean", "default": False,
                                     "description": "Also install optional_for_participation entries."},
                "include_kernel_base": {"type": "boolean", "default": False,
                                        "description": "Re-install kernel_base_included entries (usually skip — every brainstem already has them)."},
                "include_cards": {"type": "boolean", "default": True,
                                  "description": "Install rar/cards/* JSON."},
                "include_rapplications": {"type": "boolean", "default": True,
                                          "description": "Install rar/rapplications/* (rapp-application/1.0)."},
                "include_federated": {"type": "boolean", "default": False,
                                      "description": "Also fetch from `federation.federates_with` upstream stores (kody-w/RAR, RAPP_Store, RAPP_Sense_Store). Default off — neighborhood RARs are scope-local by design."},
                "dry_run": {"type": "boolean", "default": True,
                            "description": "If true, return what WOULD install without writing files."},
                "target_dir": {"type": "string",
                               "description": "Override install directory for agents. Defaults to the running brainstem's agents/."},
            },
            "required": [],
        },
    }

    def __init__(self):
        self.name = "RarLoader"

    def perform(self, **kwargs) -> str:
        rar_url = kwargs.get("rar_url")
        gate_repo = kwargs.get("gate_repo")
        if not rar_url and gate_repo:
            rar_url = f"https://raw.githubusercontent.com/{gate_repo}/main/rar/index.json"
        if not rar_url:
            return json.dumps({"ok": False, "error": "rar_url or gate_repo required"})

        # Test-injection: pass _index_override to skip network entirely.
        index = kwargs.get("_index_override")
        source = "injected" if index is not None else None
        if index is None:
            index, source = fetch_rar_index(rar_url)
        if not index:
            return json.dumps({
                "ok": False, "error": "rar/index.json unreachable + no cache",
                "rar_url": rar_url,
            })

        if index.get("schema") != "rapp-rar-index/1.0":
            return json.dumps({
                "ok": False,
                "error": f"unexpected rar index schema: {index.get('schema')!r}",
                "rar_url": rar_url, "source": source,
            })

        dry_run = kwargs.get("dry_run", True)
        include_optional = bool(kwargs.get("include_optional"))
        include_kernel_base = bool(kwargs.get("include_kernel_base"))
        include_cards = kwargs.get("include_cards", True)
        include_rapplications = kwargs.get("include_rapplications", True)
        include_federated = bool(kwargs.get("include_federated"))
        target_override = kwargs.get("target_dir")
        federation_block = index.get("federation") or {}
        federated_pointers = federation_block.get("federates_with") or [] if include_federated else []

        # Aggregate items by kind. Rapplications follow the rapp-application/1.0
        # contract from kody-w/RAPP_Store — each planted seed can bundle its own.
        by_kind = {
            "agent":        list(index.get("required_for_participation") or []),
            "card":         list(index.get("cards") or []) if include_cards else [],
            "organ":        list(index.get("organs") or []),
            "sense":        list(index.get("senses") or []),
            "rapplication": list(index.get("rapplications") or []) if include_rapplications else [],
        }
        if include_optional:
            for opt in index.get("optional_for_participation") or []:
                by_kind.setdefault(opt.get("kind", "agent"), []).append(opt)
        if include_kernel_base:
            for kb in index.get("kernel_base_included") or []:
                by_kind["agent"].append(kb)

        installed = []
        skipped = []
        errors = []
        for kind, items in by_kind.items():
            for item in items:
                # Filter to declared kind in case mixed (cards may not need verify)
                item_kind = item.get("kind") or kind
                target_dir = target_override if (target_override and item_kind == "agent") else _resolve_brainstem_target(item_kind)
                # Test-injection: pass _content_override to skip network
                content = kwargs.get(f"_content_override:{item.get('name')}")
                status = "verified"
                if content is None:
                    body, status = _fetch_and_verify(item)
                else:
                    body = content
                    actual = _sha256(body)
                    expected = (item.get("sha256") or "").lower()
                    if expected and actual != expected:
                        body = None
                        status = f"sha256_mismatch (expected {expected[:12]}…, got {actual[:12]}…)"
                if body is None:
                    errors.append({"name": item.get("name"), "kind": item_kind,
                                   "status": status, "raw_url": item.get("raw_url")})
                    continue
                # Cards may have no sha256 — skip integrity for non-required if missing
                installed.append(_install_one(item, body, target_dir, dry_run))

        result = {
            "schema": "rapp-rar-loadout/1.0",
            "rar_url": rar_url,
            "source": source,
            "rar_name": index.get("name"),
            "rar_for": index.get("rar_for"),
            "dry_run": dry_run,
            "installed": installed,
            "skipped": skipped,
            "errors": errors,
            "summary": {
                "installed_count": sum(1 for i in installed if i["status"] in ("installed", "would_install")),
                "error_count": len(errors),
                "by_kind": {
                    k: sum(1 for i in installed if i.get("kind") == k)
                    for k in ("agent", "organ", "sense", "card", "rapplication")
                },
                "include_optional": include_optional,
                "include_kernel_base": include_kernel_base,
                "include_cards": include_cards,
                "include_rapplications": include_rapplications,
                "include_federated": include_federated,
            },
            "federation": {
                "default_mode": federation_block.get("default_mode", "separate"),
                "walked": federated_pointers,
                "_note": ("Neighborhood RAR is scope-local by default. Pass include_federated=true "
                          "to walk federation.federates_with (kody-w/RAR / RAPP_Store / RAPP_Sense_Store)."),
            },
        }
        return json.dumps(result, indent=2)
