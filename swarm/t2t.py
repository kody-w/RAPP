#!/usr/bin/env python3
"""
t2t.py — Daemon-to-Daemon protocol v0 for the RAPP swarm server.

Two sovereign swarm clouds talk to each other via HMAC-authenticated message
envelopes. v0 is plaintext-over-HTTPS (relay-trusted) with HMAC for sender
identity. v1 will add Ed25519 + X25519 for full end-to-end encryption.

See blog/66-t2t-protocol-v0.md for the full protocol spec.

Wire surface (mounted by swarm/server.py):

    GET  /api/t2t/identity                     My daemon's pubkey + capabilities
    POST /api/t2t/peers                        Add a peer (cloud_id + shared_secret)
    GET  /api/t2t/peers                        List my whitelisted peers
    POST /api/t2t/handshake                    Initiate / accept a conversation
    POST /api/t2t/message                      Send / receive a message
    POST /api/t2t/invoke                       Cross-cloud capability invocation

Storage layout (under {root}/t2t/):

    t2t/
      identity.json              { cloud_id, secret, handle, capabilities[] }
      peers.json                 { peers: [{cloud_id, secret, handle, allowed_caps[]}] }
      conversations/<conv_id>/   message log per conversation
"""

from __future__ import annotations
import hashlib
import hmac
import json
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


# ─── Constants ──────────────────────────────────────────────────────────

T2T_SCHEMA = "rapp-t2t/1.0"


# ─── Identity store ─────────────────────────────────────────────────────

class IdentityStore:
    """Per-cloud identity. Generates on first access."""

    def __init__(self, root: Path):
        self.path = root / "t2t" / "identity.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def get_or_create(self, handle: str = None, capabilities: list = None) -> dict:
        with self._lock:
            if self.path.exists():
                ident = json.loads(self.path.read_text())
                # Keep handle / capabilities up to date if provided
                if handle and ident.get("handle") != handle:
                    ident["handle"] = handle
                if capabilities is not None:
                    ident["capabilities"] = capabilities
                self.path.write_text(json.dumps(ident, indent=2))
                return ident

            ident = {
                "schema": T2T_SCHEMA,
                "cloud_id": secrets.token_hex(16),
                "secret": secrets.token_hex(32),
                "handle": handle or "@unnamed.cloud",
                "capabilities": capabilities or [],
                "created_at": _now_iso(),
            }
            self.path.write_text(json.dumps(ident, indent=2))
            return ident

    def get_public(self) -> dict:
        """Returns the publishable identity (no secret)."""
        ident = self.get_or_create()
        return {
            "schema": ident["schema"],
            "cloud_id": ident["cloud_id"],
            "handle": ident["handle"],
            "capabilities": ident["capabilities"],
        }

    def get_secret(self) -> str:
        return self.get_or_create()["secret"]


# ─── Peer store ─────────────────────────────────────────────────────────

class PeerStore:
    """Whitelisted peers. Each peer's shared_secret is exchanged out-of-band."""

    def __init__(self, root: Path):
        self.path = root / "t2t" / "peers.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def list_peers(self) -> list:
        if not self.path.exists():
            return []
        return json.loads(self.path.read_text()).get("peers", [])

    def add_peer(self, cloud_id: str, secret: str, handle: str = "",
                 url: str = "", allowed_caps: list = None) -> dict:
        peer = {
            "cloud_id": cloud_id,
            "secret": secret,
            "handle": handle,
            "url": url,
            "allowed_caps": allowed_caps or ["*"],
            "added_at": _now_iso(),
        }
        with self._lock:
            data = json.loads(self.path.read_text()) if self.path.exists() else {"peers": []}
            # Replace existing peer with same cloud_id
            data["peers"] = [p for p in data["peers"] if p.get("cloud_id") != cloud_id]
            data["peers"].append(peer)
            self.path.write_text(json.dumps(data, indent=2))
        return peer

    def get_peer(self, cloud_id: str) -> dict | None:
        for p in self.list_peers():
            if p.get("cloud_id") == cloud_id:
                return p
        return None

    def remove_peer(self, cloud_id: str) -> bool:
        with self._lock:
            data = json.loads(self.path.read_text()) if self.path.exists() else {"peers": []}
            before = len(data["peers"])
            data["peers"] = [p for p in data["peers"] if p.get("cloud_id") != cloud_id]
            self.path.write_text(json.dumps(data, indent=2))
            return len(data["peers"]) < before


# ─── Conversation store ─────────────────────────────────────────────────

class ConversationStore:
    def __init__(self, root: Path):
        self.dir = root / "t2t" / "conversations"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def append_message(self, conv_id: str, message: dict) -> None:
        with self._lock:
            cdir = self.dir / conv_id
            cdir.mkdir(parents=True, exist_ok=True)
            log = cdir / "log.jsonl"
            with log.open("a") as f:
                f.write(json.dumps(message) + "\n")

    def get_log(self, conv_id: str) -> list:
        log = self.dir / conv_id / "log.jsonl"
        if not log.exists():
            return []
        out = []
        for line in log.read_text().splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
        return out


# ─── Signing / verification ────────────────────────────────────────────

def sign(payload: str, secret: str) -> str:
    """HMAC-SHA256 of payload with shared secret. Hex-encoded."""
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def verify(payload: str, signature: str, peer_secret: str) -> bool:
    """Constant-time verify. False on mismatch (doesn't raise)."""
    try:
        expected = sign(payload, peer_secret)
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


def envelope_payload(conv_id: str, seq: int, body: dict) -> str:
    """Canonical string for HMAC. Order matters for verification."""
    return json.dumps({"conv_id": conv_id, "seq": seq, "body": body},
                      sort_keys=True, separators=(",", ":"))


# ─── T2T Manager (the orchestrator) ─────────────────────────────────────

class T2TManager:
    """Top-level facade for all T2T operations."""

    def __init__(self, root: Path):
        self.identity = IdentityStore(root)
        self.peers = PeerStore(root)
        self.conversations = ConversationStore(root)

    # ── Identity ──

    def get_identity_public(self, handle: str = None, capabilities: list = None) -> dict:
        if handle or capabilities is not None:
            self.identity.get_or_create(handle=handle, capabilities=capabilities)
        return self.identity.get_public()

    # ── Peers ──

    def add_peer(self, cloud_id: str, secret: str, handle: str = "",
                 url: str = "", allowed_caps: list = None) -> dict:
        return self.peers.add_peer(cloud_id, secret, handle, url, allowed_caps)

    def list_peers(self) -> list:
        # Return without secrets
        return [{k: v for k, v in p.items() if k != "secret"}
                for p in self.peers.list_peers()]

    # ── Handshake ──

    def handshake(self, from_cloud_id: str, conv_id: str, intro: dict, sig: str) -> dict:
        """Receive an incoming handshake. Verify the peer's signature; accept or reject."""
        peer = self.peers.get_peer(from_cloud_id)
        if not peer:
            return {"accepted": False, "reason": "peer not whitelisted"}

        payload = envelope_payload(conv_id, 0, intro)
        if not verify(payload, sig, peer["secret"]):
            return {"accepted": False, "reason": "signature verification failed"}

        # Record the handshake
        self.conversations.append_message(conv_id, {
            "type": "handshake_in",
            "from": from_cloud_id,
            "intro": intro,
            "received_at": _now_iso(),
        })

        # Build acknowledgment
        my_secret = self.identity.get_secret()
        my_id = self.identity.get_or_create()["cloud_id"]
        ack_body = {"accepted": True, "by": my_id, "at": _now_iso()}
        ack_payload = envelope_payload(conv_id, 0, ack_body)
        ack_sig = sign(ack_payload, my_secret)

        return {
            "accepted": True,
            "conversation_token": conv_id,
            "ack": ack_body,
            "ack_sig": ack_sig,
        }

    # ── Message ──

    def receive_message(self, from_cloud_id: str, conv_id: str, seq: int,
                        body: dict, sig: str) -> dict:
        peer = self.peers.get_peer(from_cloud_id)
        if not peer:
            return {"received": False, "reason": "peer not whitelisted"}

        payload = envelope_payload(conv_id, seq, body)
        if not verify(payload, sig, peer["secret"]):
            return {"received": False, "reason": "signature verification failed"}

        self.conversations.append_message(conv_id, {
            "type": "message_in",
            "from": from_cloud_id,
            "seq": seq,
            "body": body,
            "received_at": _now_iso(),
        })
        return {"received": True}

    def sign_outgoing(self, conv_id: str, seq: int, body: dict) -> dict:
        """Sign an outgoing message with my own secret."""
        secret = self.identity.get_secret()
        payload = envelope_payload(conv_id, seq, body)
        return {
            "from": self.identity.get_or_create()["cloud_id"],
            "conv_id": conv_id,
            "seq": seq,
            "body": body,
            "sig": sign(payload, secret),
        }

    # ── Invocation ──

    def can_peer_invoke(self, from_cloud_id: str, capability: str) -> bool:
        peer = self.peers.get_peer(from_cloud_id)
        if not peer:
            return False
        allowed = peer.get("allowed_caps", [])
        return "*" in allowed or capability in allowed


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ─── CLI for ops / debugging ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="T2T operations.")
    parser.add_argument("--root", default="~/.rapp-swarm")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_id = sub.add_parser("identity", help="Show my T2T identity")
    p_id.add_argument("--handle", help="Set my handle")

    p_peer_add = sub.add_parser("peer-add", help="Whitelist a peer")
    p_peer_add.add_argument("cloud_id")
    p_peer_add.add_argument("secret")
    p_peer_add.add_argument("--handle", default="")
    p_peer_add.add_argument("--url", default="")

    p_peer_ls = sub.add_parser("peer-list", help="List whitelisted peers")

    p_secret = sub.add_parser("show-secret", help="Print my shared secret (for OOB exchange)")

    args = parser.parse_args()
    root = Path(os.path.expanduser(args.root))
    mgr = T2TManager(root)

    if args.cmd == "identity":
        ident = mgr.get_identity_public(handle=args.handle)
        print(json.dumps(ident, indent=2))
    elif args.cmd == "peer-add":
        peer = mgr.add_peer(args.cloud_id, args.secret, args.handle, args.url)
        peer = {k: v for k, v in peer.items() if k != "secret"}
        print(json.dumps(peer, indent=2))
    elif args.cmd == "peer-list":
        print(json.dumps(mgr.list_peers(), indent=2))
    elif args.cmd == "show-secret":
        print(mgr.identity.get_secret())
