"""
binder_service.py — package manager for a brainstem (kernel-baked).

Lives in rapp_brainstem/services/ so it ships with the brainstem itself —
no rapp-store install step needed. The legacy rapp_store/binder/binder_service.py
mirror is kept in sync for old install paths but the kernel copy is
canonical going forward.

Endpoints:
    GET    /api/binder                    — list installed rapplications
    GET    /api/binder/catalog            — fetch remote catalog
    POST   /api/binder/install            — install by id (body: {"id": "...", "version"?})
    DELETE /api/binder/installed/<id>     — uninstall by id
    GET    /api/binder/export/<id>        — export installed rapp as a .egg cartridge
    POST   /api/binder/import             — import a .egg cartridge (body: {"egg_b64": "..."})

Egg format (zip):
    manifest.json   {schema, type:"rapplication", id, version, exported_at,
                     agent_filename?, service_filename?}
    agent.py        the rapp's *_agent.py (if any)
    service.py      the rapp's *_service.py (if any)
    state/...       optional rapp-scoped data from .brainstem_data/<id>/
"""

import base64
import hashlib
import io
import json
import os
import time
import zipfile

name = "binder"


_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, ".brainstem_data")
_STATE_FILE = os.path.join(_DATA_DIR, "binder.json")
_AGENTS_DIR = os.path.join(_BASE_DIR, "agents")
_SERVICES_DIR = os.path.join(_BASE_DIR, "services")
# Distros and mirrors are first-class: RAPPSTORE_URL overrides the default
# catalog. A "RAPP Ubuntu" or "RAPP Arch" fork sets this to its own mirror
# and binder transparently installs from there. Sacred wire stays the same.
_CATALOG_URL = os.getenv("RAPPSTORE_URL", "https://raw.githubusercontent.com/kody-w/RAPP/main/rapp_store/index.json")


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


def _download(url, expected_sha=None):
    """Download a file and (optionally) verify its SHA256. Returns text content
    or raises with a useful message."""
    import requests
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"download failed: HTTP {resp.status_code}")
    content = resp.text
    if expected_sha:
        actual_sha = hashlib.sha256(content.encode()).hexdigest()
        if actual_sha != expected_sha:
            raise RuntimeError("SHA256 mismatch — file may be corrupted")
    return content


def _write_to_dir(directory, filename, content):
    os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath


def _remove_from_dir(directory, filename):
    if not filename:
        return
    filepath = os.path.join(directory, filename)
    if os.path.exists(filepath):
        os.remove(filepath)


# ── Egg cartridge helpers ───────────────────────────────────────────────

def _export_egg(rapp_id):
    """Bundle an installed rapplication into a .egg (zip). Returns
    (bytes, status, headers) for the service_dispatch binary path."""
    state = _read()
    entry = next((e for e in state.get("installed", []) if e.get("id") == rapp_id), None)
    if not entry:
        return {"error": f"rapp '{rapp_id}' is not installed"}, 404

    agent_fn = entry.get("agent_filename") or entry.get("filename")
    svc_fn = entry.get("service_filename")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        manifest = {
            "schema": "rapp-egg/1.0",
            "type": "rapplication",
            "id": rapp_id,
            "version": entry.get("version", "?"),
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "agent_filename": agent_fn,
            "service_filename": svc_fn,
        }
        z.writestr("manifest.json", json.dumps(manifest, indent=2))

        if agent_fn:
            agent_path = os.path.join(_AGENTS_DIR, agent_fn)
            if os.path.exists(agent_path):
                z.write(agent_path, "agent.py")

        if svc_fn:
            svc_path = os.path.join(_SERVICES_DIR, svc_fn)
            if os.path.exists(svc_path):
                z.write(svc_path, "service.py")

        # Optional: rapp-scoped state under .brainstem_data/<rapp_id>/
        rapp_state_dir = os.path.join(_DATA_DIR, rapp_id)
        if os.path.isdir(rapp_state_dir):
            for root, _dirs, files in os.walk(rapp_state_dir):
                for fname in files:
                    full = os.path.join(root, fname)
                    rel = os.path.relpath(full, rapp_state_dir)
                    z.write(full, "state/" + rel)

    blob = buf.getvalue()
    # Filename keeps both extensions: `.rapplication.egg` — `.rapplication`
    # is what the user reads; `.egg` is the internal format identifier
    # (zip-based archive). User-facing UI never mentions "egg" — only
    # "rapplication" — but the on-disk file keeps the format hint so a
    # tool inspecting the file can recognize it.
    download_filename = f"{rapp_id}.rapplication.egg"
    return blob, 200, {
        "Content-Type": "application/zip",
        "Content-Disposition": f'attachment; filename="{download_filename}"',
        "Content-Length": str(len(blob)),
    }


def _import_egg(body):
    """Unpack a .egg cartridge sent as {"egg_b64": "..."} and install
    its agent/service/state. Idempotent — overwrites an existing install
    of the same id."""
    egg_b64 = body.get("egg_b64", "")
    if not egg_b64:
        return {"error": "egg_b64 required"}, 400
    try:
        blob = base64.b64decode(egg_b64)
    except Exception as e:
        return {"error": f"invalid base64: {e}"}, 400

    files_restored = 0
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            names = z.namelist()
            if "manifest.json" not in names:
                return {"error": "egg missing manifest.json"}, 400
            manifest = json.loads(z.read("manifest.json"))
            if manifest.get("type") != "rapplication":
                return {"error": f"not a rapplication egg (type={manifest.get('type')!r})"}, 400

            rapp_id = manifest.get("id")
            if not rapp_id:
                return {"error": "manifest missing id"}, 400

            agent_fn = manifest.get("agent_filename")
            svc_fn = manifest.get("service_filename")

            installed = {"id": rapp_id, "version": manifest.get("version", "?")}

            if "agent.py" in names and agent_fn:
                os.makedirs(_AGENTS_DIR, exist_ok=True)
                with open(os.path.join(_AGENTS_DIR, agent_fn), "wb") as f:
                    f.write(z.read("agent.py"))
                installed["agent_filename"] = agent_fn
                installed["filename"] = agent_fn  # back-compat
                files_restored += 1

            if "service.py" in names and svc_fn:
                os.makedirs(_SERVICES_DIR, exist_ok=True)
                with open(os.path.join(_SERVICES_DIR, svc_fn), "wb") as f:
                    f.write(z.read("service.py"))
                installed["service_filename"] = svc_fn
                files_restored += 1

            # Restore rapp-scoped state
            rapp_state_dir = os.path.join(_DATA_DIR, rapp_id)
            for n in names:
                if not n.startswith("state/") or n.endswith("/"):
                    continue
                rel = n[len("state/"):]
                target = os.path.join(rapp_state_dir, rel)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "wb") as f:
                    f.write(z.read(n))
                files_restored += 1
    except zipfile.BadZipFile:
        return {"error": "not a valid .egg (zip) file"}, 400

    if "agent_filename" not in installed and "service_filename" not in installed:
        return {"error": "egg has neither agent nor service file"}, 400

    state = _read()
    state["installed"] = [e for e in state.get("installed", []) if e.get("id") != rapp_id]
    state["installed"].append(installed)
    _write(state)
    return {"status": "ok", "id": rapp_id, "files_restored": files_restored, "installed": installed}, 200


# ── Dispatch ────────────────────────────────────────────────────────────

def handle(method, path, body):
    # GET /api/binder — list installed rapplications
    if method == "GET" and path == "":
        return _read(), 200

    # GET /api/binder/catalog — fetch remote catalog
    if method == "GET" and path == "catalog":
        return _fetch_catalog(), 200

    # GET /api/binder/export/<id> — export installed rapp as a .egg cartridge
    if method == "GET" and path.startswith("export/"):
        rapp_id = path[len("export/"):]
        if not rapp_id:
            return {"error": "id required"}, 400
        return _export_egg(rapp_id)

    # POST /api/binder/import — import a .egg cartridge
    if method == "POST" and path == "import":
        return _import_egg(body)

    # POST /api/binder/install — install a rapplication by id, optionally pinned to a version
    if method == "POST" and path == "install":
        rapp_id = body.get("id", "")
        version = body.get("version", "")  # optional; empty = latest from catalog
        if not rapp_id:
            return {"error": "id required"}, 400

        catalog = _fetch_catalog()
        entry = next((r for r in catalog.get("rapplications", []) if r.get("id") == rapp_id), None)
        if not entry:
            return {"error": f"rapplication '{rapp_id}' not found in catalog"}, 404

        # Version pinning: if the caller asked for a specific version and the
        # catalog entry lists available_versions, swap URLs/SHAs to that version.
        # Edge clients pin to a specific version URL; everyone else gets latest.
        if version:
            available = entry.get("available_versions", [])
            if available and version not in available:
                return {"error": f"version '{version}' not available; have {available}"}, 404
            # Rewrite the URLs to point at the versioned path
            for fld in ("singleton_url", "service_url"):
                u = entry.get(fld)
                if u and "/versions/" not in u:
                    base, fname = u.rsplit("/", 1)
                    entry[fld] = f"{base}/versions/{version}/{fname}"
            # Pinned installs can't trust the catalog's SHA fields (those are
            # for latest); the caller is responsible for verifying out-of-band.
            entry.pop("singleton_sha256", None)
            entry.pop("service_sha256", None)
            entry["version"] = version

        installed = {"id": rapp_id, "version": entry.get("version", "?")}

        # Agent file (optional — pure services like binder/swarms may not have one)
        agent_url = entry.get("singleton_url")
        agent_filename = entry.get("singleton_filename")
        if agent_url and agent_filename:
            try:
                content = _download(agent_url, entry.get("singleton_sha256"))
            except Exception as e:
                return {"error": f"agent download failed: {e}"}, 502
            _write_to_dir(_AGENTS_DIR, agent_filename, content)
            installed["agent_filename"] = agent_filename
            # Backwards-compat: keep `filename` for older binder.json readers
            installed["filename"] = agent_filename

        # Service file (optional — some rapplications are agent-only)
        service_url = entry.get("service_url")
        service_filename = entry.get("service_filename")
        if service_url and service_filename:
            try:
                content = _download(service_url, entry.get("service_sha256"))
            except Exception as e:
                return {"error": f"service download failed: {e}"}, 502
            _write_to_dir(_SERVICES_DIR, service_filename, content)
            installed["service_filename"] = service_filename

        if "agent_filename" not in installed and "service_filename" not in installed:
            return {"error": "rapplication has neither agent nor service files"}, 400

        # Track installation (replace any existing entry for this id)
        state = _read()
        state["installed"] = [e for e in state["installed"] if e.get("id") != rapp_id]
        state["installed"].append(installed)
        _write(state)
        return {"status": "ok", "installed": installed}, 200

    # DELETE /api/binder/installed/<id> — uninstall a rapplication
    if method == "DELETE" and path.startswith("installed/"):
        rapp_id = path[len("installed/"):]
        state = _read()
        entry = next((e for e in state["installed"] if e.get("id") == rapp_id), None)
        if not entry:
            return {"error": "not installed"}, 404

        # Kernel-protected files: the binder is baked into the kernel and
        # cannot be self-removed even if the catalog still lists it. Same
        # principle for any future kernel-baked rapp — the uninstall just
        # forgets the entry from binder.json without touching the file.
        # Without this, uninstalling the binder rapp from the UI deletes
        # this very service as a side-effect and breaks /api/binder/*.
        KERNEL_PROTECTED = {"binder", "binder_service.py"}
        agent_fn = entry.get("agent_filename") or entry.get("filename")
        svc_fn = entry.get("service_filename")
        if rapp_id not in KERNEL_PROTECTED and (svc_fn or "") not in KERNEL_PROTECTED:
            _remove_from_dir(_AGENTS_DIR, agent_fn)
            _remove_from_dir(_SERVICES_DIR, svc_fn)

        state["installed"] = [e for e in state["installed"] if e.get("id") != rapp_id]
        _write(state)
        return {"status": "ok", "uninstalled": rapp_id}, 200

    return {"error": "not found"}, 404
