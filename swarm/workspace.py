#!/usr/bin/env python3
"""
swarm/workspace.py — per-twin workspace docs + T2T file sharing.

Each local twin gets its own filesystem workspace:

    ~/.rapp-twins/<name>/
      swarms/<guid>/...           (existing per-swarm storage)
      t2t/...                     (existing T2T identity, peers, conversations)
      documents/                  (THIS twin's documents)
      inbox/                      (docs received from other twins)
      outbox/                     (docs sent to other twins, copied for audit)
      workspace.json              (name, port, created_at, …)

Documents are arbitrary files (text, JSON, markdown, binary up to 10 MB).
They live in `documents/` until explicitly shared. Sharing routes through
the existing T2T HMAC channel — same trust model as messages.

Wire surface (mounted by swarm/server.py):

    GET    /api/workspace                       Workspace metadata
    GET    /api/workspace/documents             List documents (mine + inbox)
    GET    /api/workspace/documents/<name>      Read one document
    POST   /api/workspace/documents/<name>      Save / overwrite
    DELETE /api/workspace/documents/<name>      Remove

    POST   /api/t2t/send-document               Encode + sign + push to peer
    POST   /api/t2t/receive-document            Verify sig, save to inbox
"""

from __future__ import annotations
import base64
import json
import os
from pathlib import Path
from datetime import datetime, timezone


MAX_DOC_BYTES = 10 * 1024 * 1024  # 10 MB safety cap


def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_name(name: str) -> str:
    """Sandbox a document name to a single basename — no path traversal."""
    n = os.path.basename(name or "").strip()
    # Strip control chars + any remaining path separators
    n = "".join(c for c in n if c.isprintable() and c not in "/\\")
    return n[:255]


class Workspace:
    """Per-twin workspace. Lives at the same root as SwarmStore."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.docs_dir = self.root / "documents"
        self.inbox_dir = self.root / "inbox"
        self.outbox_dir = self.root / "outbox"
        for d in (self.docs_dir, self.inbox_dir, self.outbox_dir):
            d.mkdir(parents=True, exist_ok=True)
        self.meta_path = self.root / "workspace.json"

    # ── metadata ──

    def info(self) -> dict:
        meta = {}
        if self.meta_path.exists():
            try:
                meta = json.loads(self.meta_path.read_text())
            except Exception:
                meta = {}
        meta.setdefault("name", self.root.name)
        meta.setdefault("created_at", _now_iso())
        meta["root"] = str(self.root)
        meta["doc_count"] = sum(1 for _ in self.docs_dir.iterdir() if _.is_file())
        meta["inbox_count"] = sum(1 for _ in self.inbox_dir.iterdir() if _.is_file())
        return meta

    def ensure_meta(self, name: str = None, port: int = None):
        meta = {}
        if self.meta_path.exists():
            try:
                meta = json.loads(self.meta_path.read_text())
            except Exception:
                pass
        meta.setdefault("name", name or self.root.name)
        meta.setdefault("created_at", _now_iso())
        if port is not None:
            meta["port"] = port
        self.meta_path.write_text(json.dumps(meta, indent=2))
        return meta

    # ── documents ──

    def list_documents(self) -> dict:
        def stat_dir(d: Path):
            out = []
            for p in sorted(d.iterdir()):
                if not p.is_file(): continue
                out.append({
                    "name": p.name,
                    "bytes": p.stat().st_size,
                    "modified_at": datetime.fromtimestamp(
                        p.stat().st_mtime, tz=timezone.utc
                    ).isoformat().replace("+00:00", "Z"),
                })
            return out
        return {
            "documents": stat_dir(self.docs_dir),
            "inbox":     stat_dir(self.inbox_dir),
            "outbox":    stat_dir(self.outbox_dir),
        }

    def read_document(self, name: str, location: str = "documents") -> dict | None:
        """Returns {name, bytes, content_b64, modified_at} or None if missing."""
        n = _safe_name(name)
        if not n: return None
        d = self._loc_dir(location)
        p = d / n
        if not p.is_file(): return None
        data = p.read_bytes()
        return {
            "name": n,
            "location": location,
            "bytes": len(data),
            "content_b64": base64.b64encode(data).decode("ascii"),
            "modified_at": datetime.fromtimestamp(
                p.stat().st_mtime, tz=timezone.utc
            ).isoformat().replace("+00:00", "Z"),
        }

    def write_document(self, name: str, content: bytes,
                       location: str = "documents") -> dict:
        n = _safe_name(name)
        if not n:
            raise ValueError("invalid document name")
        if len(content) > MAX_DOC_BYTES:
            raise ValueError(f"document exceeds {MAX_DOC_BYTES // 1024 // 1024} MB cap")
        d = self._loc_dir(location)
        p = d / n
        p.write_bytes(content)
        return {"name": n, "location": location, "bytes": len(content),
                "saved_at": _now_iso()}

    def delete_document(self, name: str, location: str = "documents") -> bool:
        n = _safe_name(name)
        if not n: return False
        p = self._loc_dir(location) / n
        if p.is_file():
            p.unlink()
            return True
        return False

    def _loc_dir(self, location: str) -> Path:
        loc = (location or "documents").lower()
        if loc == "inbox":  return self.inbox_dir
        if loc == "outbox": return self.outbox_dir
        return self.docs_dir
