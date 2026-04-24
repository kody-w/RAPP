"""
binder_service.py — Install/uninstall rapplications from the RAPPstore catalog.

Fetches the catalog from the public rapp_store index, downloads singleton
agent files into agents/, and tracks what's installed in .brainstem_data/binder.json.
"""

import json
import os
import hashlib

name = "binder"

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, ".brainstem_data")
_STATE_FILE = os.path.join(_DATA_DIR, "binder.json")
_AGENTS_DIR = os.path.join(_BASE_DIR, "agents")
_CATALOG_URL = "https://raw.githubusercontent.com/kody-w/RAPP/main/rapp_store/index.json"


def _read():
    if os.path.exists(_STATE_FILE):
        with open(_STATE_FILE) as f:
            return json.load(f)
    return {"installed": []}


def _write(data):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _fetch_catalog():
    try:
        import requests
        resp = requests.get(_CATALOG_URL, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {"rapplications": []}


def handle(method, path, body):
    # GET /api/binder — list installed rapplications
    if method == "GET" and path == "":
        return _read(), 200

    # GET /api/binder/catalog — fetch remote catalog
    if method == "GET" and path == "catalog":
        return _fetch_catalog(), 200

    # POST /api/binder/install — install a rapplication by id
    if method == "POST" and path == "install":
        rapp_id = body.get("id", "")
        if not rapp_id:
            return {"error": "id required"}, 400

        catalog = _fetch_catalog()
        entry = None
        for r in catalog.get("rapplications", []):
            if r.get("id") == rapp_id:
                entry = r
                break
        if not entry:
            return {"error": f"rapplication '{rapp_id}' not found in catalog"}, 404

        singleton_url = entry.get("singleton_url")
        singleton_filename = entry.get("singleton_filename")
        if not singleton_url or not singleton_filename:
            return {"error": "rapplication has no singleton file"}, 400

        # Download the agent file
        try:
            import requests
            resp = requests.get(singleton_url, timeout=30)
            if resp.status_code != 200:
                return {"error": f"download failed: HTTP {resp.status_code}"}, 502
            content = resp.text
        except Exception as e:
            return {"error": f"download failed: {e}"}, 502

        # Verify hash if provided
        expected_sha = entry.get("singleton_sha256")
        if expected_sha:
            actual_sha = hashlib.sha256(content.encode()).hexdigest()
            if actual_sha != expected_sha:
                return {"error": "SHA256 mismatch — file may be corrupted"}, 400

        # Write to agents/
        os.makedirs(_AGENTS_DIR, exist_ok=True)
        filepath = os.path.join(_AGENTS_DIR, singleton_filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        # Track installation
        state = _read()
        state["installed"] = [e for e in state["installed"] if e.get("id") != rapp_id]
        state["installed"].append({
            "id": rapp_id,
            "filename": singleton_filename,
            "version": entry.get("version", "?"),
        })
        _write(state)
        return {"status": "ok", "installed": rapp_id}, 200

    # DELETE /api/binder/installed/<id> — uninstall a rapplication
    if method == "DELETE" and path.startswith("installed/"):
        rapp_id = path[len("installed/"):]
        state = _read()
        entry = None
        for e in state["installed"]:
            if e.get("id") == rapp_id:
                entry = e
                break
        if not entry:
            return {"error": "not installed"}, 404

        # Remove the agent file
        filename = entry.get("filename")
        if filename:
            filepath = os.path.join(_AGENTS_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)

        state["installed"] = [e for e in state["installed"] if e.get("id") != rapp_id]
        _write(state)
        return {"status": "ok", "uninstalled": rapp_id}, 200

    return {"error": "not found"}, 404
