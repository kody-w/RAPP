"""
snapshot_organ.py — one-click portable backup + restore for this organism.

Wraps utils/bond.py's pack_organism() / unpack_organism() so the chat
UI's Export button can produce a single portable `.egg` cartridge
(rappid + soul + custom agents/organs/senses/services + .brainstem_data
state, with secrets sanitized) and a drag-dropped `.egg` can restore
the full brainstem in one shot — instead of a "random book.json" that
only carries diagnostics.

Endpoints (dispatched at /api/snapshot/*):

    GET  /api/snapshot/export
        → returns the organism egg as application/zip,
          Content-Disposition: attachment with a dated filename.

    POST /api/snapshot/import
        body: { "content_b64": "<base64 of .egg bytes>",
                "filename":    "optional-display-name.egg" }
        → unpacks via bond.unpack_organism over the running kernel,
          returns the restore counts. The kernel itself does not need
          a restart — agents are reloaded from disk on every /chat
          turn — but new organs/senses come online next boot.
"""

from __future__ import annotations

import base64
import importlib
import os
import sys
from datetime import datetime, timezone

from flask import make_response

name = "snapshot"


_HERE = os.path.dirname(os.path.abspath(__file__))           # utils/organs/
_UTILS_DIR = os.path.dirname(_HERE)                          # utils/
_BRAINSTEM_DIR = os.path.dirname(_UTILS_DIR)                 # rapp_brainstem/
if _UTILS_DIR not in sys.path:
    sys.path.insert(0, _UTILS_DIR)


def _bond():
    """Lazy import of utils/bond.py — its load isn't free at boot time."""
    return importlib.import_module("bond")


def _rapp_home() -> str:
    return os.environ.get("RAPP_HOME") or os.path.join(os.path.expanduser("~"), ".brainstem")


def _kernel_version() -> str:
    vfile = os.path.join(_BRAINSTEM_DIR, "VERSION")
    try:
        with open(vfile, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"


def _now_stamp() -> str:
    # Filename-safe ISO-ish stamp: 2026-05-02T18-04-22Z
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def handle(method: str, path: str, body: dict):
    method = (method or "GET").upper()
    path = (path or "").strip("/")
    bond = _bond()
    home = _rapp_home()

    if method == "GET" and path in ("", "export"):
        try:
            blob = bond.pack_organism(home, _BRAINSTEM_DIR, _kernel_version())
        except Exception as e:
            return {"error": f"pack failed: {e}"}, 500
        # Filename favors the rappid slug if available so collected eggs
        # are easy to tell apart in a Downloads folder.
        slug = "brainstem"
        try:
            ident = bond._read_json(bond._rappid_path(home)) or {}
            rappid = ident.get("rappid") or ""
            # rappid:v2:<kind>:<owner>/<name>:<short>@... — pick the name
            if rappid:
                parts = rappid.split(":")
                if len(parts) >= 4:
                    name_part = parts[3]
                    if "/" in name_part:
                        name_part = name_part.split("/", 1)[1]
                    if name_part:
                        slug = name_part.replace(" ", "_")
        except Exception:
            pass
        filename = f"{slug}-{_now_stamp()}.egg"
        resp = make_response(blob, 200)
        resp.headers["Content-Type"] = "application/zip"
        resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        resp.headers["X-Egg-Filename"] = filename
        # Length helps the browser show progress.
        resp.headers["Content-Length"] = str(len(blob))
        return resp, 200

    if method == "POST" and path == "import":
        b64 = (body or {}).get("content_b64")
        if not isinstance(b64, str) or not b64:
            return {"error": "missing content_b64"}, 400
        try:
            blob = base64.b64decode(b64)
        except Exception as e:
            return {"error": f"invalid base64: {e}"}, 400
        try:
            counts = bond.unpack_organism(blob, home, _BRAINSTEM_DIR)
        except ValueError as e:
            return {"error": str(e)}, 400
        except Exception as e:
            return {"error": f"hatch failed: {e}"}, 500
        return {
            "status": "ok",
            "counts": counts,
            "filename": (body or {}).get("filename") or None,
        }, 200

    return {"error": f"unsupported {method} /api/snapshot/{path}"}, 405
