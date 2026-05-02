"""
senses_organ.py — install / list / remove sense modules.

Senses live under utils/senses/<id>_sense.py and are auto-composed by
utils/senses/__init__.py at request time. The kernel doesn't ship an
install endpoint for them (Article XXXIII: kernel stays light), so this
organ is the install surface the chat UI's RAPP_Store tab calls into.

Endpoints (dispatched at /api/senses/*):

    GET    /api/senses              — list installed sense files
    POST   /api/senses/install      — body: { filename, content }
                                       writes utils/senses/<filename>
    DELETE /api/senses/<filename>   — remove utils/senses/<filename>
"""

from __future__ import annotations

import os

name = "senses"


_HERE = os.path.dirname(os.path.abspath(__file__))                  # utils/organs/
_UTILS_DIR = os.path.dirname(_HERE)                                 # utils/
_SENSES_DIR = os.path.join(_UTILS_DIR, "senses")


def _safe_filename(filename: str) -> str | None:
    if not isinstance(filename, str) or not filename:
        return None
    if "/" in filename or "\\" in filename or filename.startswith("."):
        return None
    if not filename.endswith("_sense.py"):
        return None
    return filename


def _list_files() -> list[dict]:
    if not os.path.isdir(_SENSES_DIR):
        return []
    out: list[dict] = []
    for name_ in sorted(os.listdir(_SENSES_DIR)):
        if not name_.endswith("_sense.py"):
            continue
        full = os.path.join(_SENSES_DIR, name_)
        try:
            st = os.stat(full)
            out.append({
                "filename": name_,
                "id": name_[:-len("_sense.py")],
                "bytes": st.st_size,
                "mtime": int(st.st_mtime),
            })
        except OSError:
            continue
    return out


def handle(method: str, path: str, body: dict):
    method = (method or "GET").upper()
    path = (path or "").strip("/")

    if method == "GET" and path in ("", "list"):
        return {"senses": _list_files(), "dir": _SENSES_DIR}, 200

    if method == "POST" and path == "install":
        filename = _safe_filename((body or {}).get("filename"))
        content = (body or {}).get("content")
        if not filename:
            return {"error": "invalid filename — must be <id>_sense.py"}, 400
        if not isinstance(content, str) or not content.strip():
            return {"error": "missing content"}, 400
        os.makedirs(_SENSES_DIR, exist_ok=True)
        target = os.path.join(_SENSES_DIR, filename)
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            return {"error": f"write failed: {e}"}, 500
        return {"status": "ok", "filename": filename, "path": target}, 200

    if method == "DELETE" and path:
        filename = _safe_filename(path)
        if not filename:
            return {"error": "invalid filename"}, 400
        target = os.path.join(_SENSES_DIR, filename)
        if not os.path.isfile(target):
            return {"error": "not found"}, 404
        try:
            os.remove(target)
        except OSError as e:
            return {"error": f"delete failed: {e}"}, 500
        return {"status": "ok", "filename": filename}, 200

    return {"error": f"unsupported {method} /api/senses/{path}"}, 405
