"""
RAPP Brainstem — minimal local AI agent endpoint.
Only dependency: a GitHub account with Copilot access.

Uses the GitHub Copilot API directly.
No API keys needed — just `gh auth login`.

Usage:
    ./start.sh
    # or: python brainstem.py

POST /chat    { user_input, conversation_history?, session_id? }
GET  /health  Status, model, loaded agents, token state
"""

import os
import sys
import json
import uuid
import glob
import time
import threading
import importlib.util
import subprocess
import traceback
import base64
import io
import hashlib
from datetime import datetime, timezone

import logging
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import flask.cli
from dotenv import load_dotenv

load_dotenv()

# Quiet the per-request `127.0.0.1 - - [date] "GET /... HTTP/1.1" 200 -`
# access spam from werkzeug. ERROR level still surfaces 5xx, which is the
# only thing worth interrupting the operator's eye for. The brainstem's
# own [brainstem] ... prints are the real telemetry — they were getting
# drowned out by the access log on every page load (rapp.js, manifest,
# icons, /version, /models, /agents/full all fire on every reload).
# Set BRAINSTEM_VERBOSE=1 to opt back in to the full werkzeug log.
if not os.getenv("BRAINSTEM_VERBOSE"):
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    # Also suppress Flask's own startup banner ("* Serving Flask app",
    # "* Debug mode: off", the production-deployment WARNING, "* Running
    # on http://...", "Press CTRL+C to quit"). The brainstem's own
    # startup banner above app.run() already says all of that.
    flask.cli.show_server_banner = lambda *a, **k: None

app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)))
# Cross-origin allowlist. Same-origin (bundled UI at /) needs no CORS.
# Allowed: localhost/127.0.0.1 on any port, the hosted vBrainstem UI, and
# anything the operator adds via RAPP_CORS_ORIGINS (comma-separated).
_cors_origins = [
    r"^https://kody-w\.github\.io$",
    r"^http://localhost(:\d+)?$",
    r"^http://127\.0\.0\.1(:\d+)?$",
]
_cors_extra = [o.strip() for o in os.getenv("RAPP_CORS_ORIGINS", "").split(",") if o.strip()]
CORS(app, origins=_cors_origins + _cors_extra)

# ── Config ────────────────────────────────────────────────────────────────────

SOUL_PATH    = os.getenv("SOUL_PATH",    os.path.join(os.path.dirname(__file__), "soul.md"))
AGENTS_PATH  = os.getenv("AGENTS_PATH",  os.path.join(os.path.dirname(__file__), "agents"))
SERVICES_PATH = os.getenv("SERVICES_PATH", os.path.join(os.path.dirname(__file__), "utils", "services"))
MODEL        = os.getenv("GITHUB_MODEL", "gpt-4o")
PORT        = int(os.getenv("PORT", 7071))
# Voice and Twin default ON — the brainstem's terminal twin (see
# _twin_emit below) is the operator's window into the agent's "world".
# Watching it pace and react across calls makes non-tech users care
# about what's happening; turning it off makes the terminal feel dead.
#
# NOTE: VOICE_MODE and TWIN_MODE are kept for the /voice and /twin
# status endpoints' backwards-compat shape, but the chat path no
# longer gates on them — the server unconditionally instructs the LLM
# to emit |||VOICE||| and |||TWIN|||, and unconditionally ships
# voice_response and twin_response when those blocks appear. Frontends
# decide whether to play the audio or render the cage.
VOICE_MODE  = os.getenv("VOICE_MODE", "true").lower() == "true"
TWIN_MODE   = os.getenv("TWIN_MODE", "true").lower() == "true"
VOICE_ZIP_PW = os.getenv("VOICE_ZIP_PASSWORD", "").encode() or None

_version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
VERSION = open(_version_file).read().strip() if os.path.exists(_version_file) else "0.0.0"

# Tier-2 / CommunityRAPP parity: every chat request can carry a `user_guid`
# identifying who's calling. Default = an INTENTIONALLY INVALID UUID — the
# 'p' and 'l' in c0p110t0 spell "copilot" while making the string un-parseable
# as a real UUID. This is a security feature, not a bug:
#   1. It can never collide with a real user's UUID
#   2. UUID-validating columns reject it loudly instead of accepting a default
#   3. It surfaces unmistakably in logs as "no real user context"
#   4. Memory shims route DEFAULT_USER_GUID to shared global memory
# On Tier 1 (local) the field is silent — the operator at the keyboard IS
# the user and the default is the norm. On Tier 2 (cloud) the field is
# how multi-tenant callers identify themselves. Same wire either way.
DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"

# RAPPstore catalog URL — overridable so distros and mirrors are first-class.
# Default points at the canonical store; forks/distros set this to their own
# mirror and binder transparently installs from there.
RAPPSTORE_URL = os.getenv("RAPPSTORE_URL", "https://raw.githubusercontent.com/kody-w/rapp_store/main/index.json")

COPILOT_TOKEN_URL = "https://api.github.com/copilot_internal/v2/token"

AVAILABLE_MODELS = [
    {"id": "gpt-4.1",         "name": "GPT-4.1"},
    {"id": "gpt-4o",          "name": "GPT-4o"},
    {"id": "gpt-4o-mini",     "name": "GPT-4o Mini"},
    {"id": "claude-sonnet-4", "name": "Claude Sonnet 4"},
    {"id": "gpt-4",           "name": "GPT-4"},
    {"id": "gpt-3.5-turbo",   "name": "GPT-3.5 Turbo"},
]

# Models that don't support OpenAI-style tool_choice parameter
_NO_TOOL_CHOICE_MODELS = set()
_models_fetched = False

def _fetch_copilot_models():
    """Fetch available models from Copilot API. Updates AVAILABLE_MODELS in place."""
    global AVAILABLE_MODELS, _models_fetched, _NO_TOOL_CHOICE_MODELS
    if _models_fetched:
        return
    try:
        copilot_token, endpoint = get_copilot_token()
        resp = requests.get(
            f"{endpoint}/models",
            headers={
                "Authorization": f"Bearer {copilot_token}",
                "Content-Type": "application/json",
                "Editor-Version": "vscode/1.95.0",
                "Copilot-Integration-Id": "vscode-chat",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            models_list = data if isinstance(data, list) else data.get("data", data.get("models", []))
            if models_list:
                new_models = []
                for m in models_list:
                    mid = m.get("id", m.get("model", ""))
                    mname = m.get("name", mid)
                    if mid:
                        new_models.append({"id": mid, "name": mname})
                        if "o1" in mid.lower():
                            _NO_TOOL_CHOICE_MODELS.add(mid)
                if new_models:
                    AVAILABLE_MODELS = new_models
                    print(f"[brainstem] Fetched {len(new_models)} models from Copilot API")
        _models_fetched = True
    except Exception as e:
        print(f"[brainstem] Could not fetch models (using defaults): {e}")
        _models_fetched = True

# ── Flight Recorder (book.json telemetry) ─────────────────────────────────────

_flight_log = []
_flight_log_lock = threading.Lock()
_FLIGHT_LOG_MAX = 2000
_flight_log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".brainstem_book.json")

def _tlog(event_type, data=None, level="info"):
    """Append an event to the flight recorder."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "level": level,
    }
    if data:
        entry["data"] = data
    with _flight_log_lock:
        _flight_log.append(entry)
        if len(_flight_log) > _FLIGHT_LOG_MAX:
            _flight_log[:] = _flight_log[-_FLIGHT_LOG_MAX:]

def _tlog_save():
    """Persist flight log to disk (called periodically and on export)."""
    try:
        with _flight_log_lock:
            snapshot = list(_flight_log)
        with open(_flight_log_file, "w") as f:
            json.dump(snapshot, f)
    except Exception:
        pass

def _tlog_load():
    """Load previous flight log from disk on startup."""
    global _flight_log
    if not os.path.exists(_flight_log_file):
        return
    try:
        with open(_flight_log_file) as f:
            data = json.load(f)
        if isinstance(data, list):
            with _flight_log_lock:
                _flight_log = data[-_FLIGHT_LOG_MAX:]
    except Exception:
        pass

def _tlog_autosave():
    """Background thread: flush flight log to disk every 30s."""
    while True:
        time.sleep(30)
        _tlog_save()

# Start autosave thread
threading.Thread(target=_tlog_autosave, daemon=True).start()

# ── Terminal twin (the operator's window into the agent's world) ─────────────
#
# Each chat round renders a small ASCII art frame in a bordered cage between
# the [brainstem] telemetry lines. The cage is a fixed canvas; the LLM draws
# whatever it wants inside via <frame>...</frame> in its |||TWIN||| output.
# No required prose, no speech bubble — the art IS the twin's voice.
#
# Why bother: telemetry alone is text wallpaper. A bug-cage with a small
# scene that changes per turn gives non-tech users a visual anchor for what
# the agent is doing — gateway drug to caring about the technical lines
# underneath. Like a Tamagotchi for the agent.
#
# The chat path always asks the LLM for a |||TWIN||| block and always
# ships twin_response. _twin_emit no-ops when the LLM didn't author a
# <frame> for that turn, so the operator's terminal stays quiet rather
# than showing a fake/canned animation.

import random as _twin_random

# Cage canvas dimensions — width and height of the drawing area inside
# the borders. Sized so a small ASCII figure or scene fits comfortably
# without dominating the terminal between [brainstem] lines.
_TWIN_CANVAS_H = 5
_TWIN_CANVAS_W = 44

_TWIN_COLORS = {
    "awake":    "\033[36m",  # cyan
    "thinking": "\033[35m",  # magenta
    "working":  "\033[33m",  # yellow
    "done":     "\033[32m",  # green
    "puzzled":  "\033[33m",  # yellow
    "error":    "\033[31m",  # red
}
_TWIN_RESET = "\033[0m"

# Pacing state — frame counter only. The previous version drifted the
# canned art horizontally per call to imply life; with canned art gone,
# the LLM controls composition entirely so no drift is needed.
_twin_state = {"frame": 0}


def _maybe_center_head(lines):
    """Stick-figure safety net — the LLM sometimes emits a single-glyph
    head at column 0 above a body indented by 1+ columns, like:

        o          → wrong: head sits to the LEFT of the spine
         /|\\
         / \\

    When the first line is 1–2 non-whitespace chars and shorter than
    the body line below it, shift the head's leading whitespace so
    its center column lands over the body's center column. Skips when
    the head is already wider (e.g. `\\o/`) or already aligned. No-op
    on non-figure art."""
    if len(lines) < 2:
        return lines
    head = lines[0]
    head_stripped = head.strip()
    if not head_stripped or len(head_stripped) > 2:
        return lines
    body_line = next((l for l in lines[1:] if l.strip()), None)
    if body_line is None:
        return lines
    body_left  = len(body_line) - len(body_line.lstrip())
    body_right = len(body_line.rstrip())
    if body_right - body_left < 2:
        return lines  # body too small to need centering
    body_center = (body_left + body_right - 1) // 2
    head_first  = len(head) - len(head.lstrip())
    target_first = body_center - (len(head_stripped) - 1) // 2
    if target_first > head_first:
        shift = target_first - head_first
        lines = [(" " * shift) + lines[0]] + lines[1:]
    return lines


def _normalize_canvas(art_lines):
    """Pad/truncate a list of strings to exactly _TWIN_CANVAS_H rows ×
    _TWIN_CANVAS_W cols. Lines longer than the canvas get clipped on
    the right; missing lines pad with blanks. Centers vertically when
    art is shorter than the canvas — feels less like a clipped box
    and more like the figure has room to breathe."""
    lines = [l.rstrip("\n").replace("\t", "    ") for l in art_lines or []]
    # Truncate horizontally
    lines = [l[:_TWIN_CANVAS_W] for l in lines]
    # Trim leading/trailing fully-empty lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    # Auto-center single-glyph heads over their body (common LLM miss)
    lines = _maybe_center_head(lines)
    # Truncate vertically
    lines = lines[:_TWIN_CANVAS_H]
    # Vertically center
    extra = _TWIN_CANVAS_H - len(lines)
    top_pad = extra // 2
    bot_pad = extra - top_pad
    lines = ([""] * top_pad) + lines + ([""] * bot_pad)
    # Pad each line to canvas width
    lines = [l.ljust(_TWIN_CANVAS_W) for l in lines]
    return lines


def _twin_emit(mood="done", figure=None):
    """Render one frame of the twin in its cage — IF the LLM actually
    shipped a <frame> in this turn's |||TWIN||| block. No <frame> =
    no cage. The twin lives in the system prompt or it doesn't live;
    drawing canned art on its behalf would lie about the twin being
    a real digital organism reacting to the turn.

    figure: REQUIRED. List of ASCII strings (the LLM's hand-authored
            cage content). When None or empty, this function no-ops
            silently — the operator just sees the [brainstem] telemetry
            for that turn, no twin frame.
    mood:   only used to color the cage border."""
    if not figure:
        return  # silent twin → silent terminal; no fake animation
    _twin_state["frame"] += 1

    canvas = _normalize_canvas(figure)
    if not any(line.strip() for line in canvas):
        return  # all-blank frame from the LLM is also silence

    label = f" twin · {mood} · #{_twin_state['frame']} "
    label_pad = label + ("─" * max(0, _TWIN_CANVAS_W + 2 - len(label)))
    bottom = "─" * (_TWIN_CANVAS_W + 2)

    use_color = sys.stdout.isatty()
    col = _TWIN_COLORS.get(mood, "") if use_color else ""
    rst = _TWIN_RESET if use_color else ""
    print(f"  {col}╭{label_pad}╮{rst}")
    for line in canvas:
        print(f"  {col}│{rst} {line} {col}│{rst}")
    print(f"  {col}╰{bottom}╯{rst}")
    sys.stdout.flush()


def _extract_twin_frame(twin_text):
    """Pull <frame>...</frame> ASCII art out of the twin block. Returns
    (art_lines_or_None, twin_text_with_frame_stripped). The art is
    returned raw — _normalize_canvas does the canvas-fitting at render
    time. Lets the LLM hand-author the cage's content per turn; the
    art IS the twin's voice for the round."""
    if not twin_text:
        return None, twin_text
    import re as _re
    m = _re.search(r"<frame>\s*\n?(.*?)\n?\s*</frame>", twin_text, _re.DOTALL | _re.IGNORECASE)
    if not m:
        return None, twin_text
    raw = m.group(1).rstrip("\n").lstrip("\n")
    raw_lines = raw.split("\n")
    cleaned = (twin_text[:m.start()] + twin_text[m.end():]).strip()
    return raw_lines, cleaned

# ── GitHub token ──────────────────────────────────────────────────────────────

# GitHub Copilot GitHub App client ID — produces ghu_ tokens that work with Copilot exchange API
# Note: Ov23ctDVkRmgkPke0Mmm is an OAuth App that produces gho_ tokens — those get 404 from Copilot
COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"
_token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".copilot_token")
_copilot_cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".copilot_session")

def _read_token_file():
    """Read the token file. Returns dict with at least 'access_token', or None."""
    if not os.path.exists(_token_file):
        return None
    try:
        with open(_token_file) as f:
            raw = f.read().strip()
        if not raw:
            return None
        # New JSON format: {"access_token": ..., "refresh_token": ...}
        if raw.startswith("{"):
            return json.loads(raw)
        # Legacy plain-text format: just the token string
        return {"access_token": raw}
    except Exception:
        return None

def get_github_token():
    """Get GitHub token from env, saved file, or gh CLI.
    
    Only returns tokens that work with the Copilot token exchange API.
    Tokens from 'gh auth token' (gho_ prefix) don't have Copilot access,
    so we skip them and only use ghu_ tokens from our device code flow.
    """
    # 1. Env var
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        return token
    # 2. Saved token from device code login (ghu_ tokens)
    data = _read_token_file()
    if data and data.get("access_token"):
        return data["access_token"]
    # 3. gh CLI — only use if it returns a Copilot-compatible token (not gho_)
    try:
        env = os.environ.copy()
        if sys.platform == "win32":
            machine = os.environ.get("Path", "")
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
                    machine = winreg.QueryValueEx(key, "Path")[0]
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                    user = winreg.QueryValueEx(key, "Path")[0]
                env["Path"] = machine + ";" + user
            except Exception:
                pass
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True, text=True, timeout=5,
            shell=(sys.platform == "win32"),
            env=env,
        )
        token = result.stdout.strip()
        if token and not token.startswith("gho_"):
            return token
    except Exception:
        pass
    return None

def save_github_token(token, refresh_token=None):
    """Persist token (and optional refresh token) for reuse across restarts."""
    # Preserve existing refresh_token if we're only updating the access_token
    existing = _read_token_file() or {}
    data = {
        "access_token": token,
        "refresh_token": refresh_token or existing.get("refresh_token"),
        "saved_at": time.time(),
    }
    with open(_token_file, "w") as f:
        json.dump(data, f)
    _tlog("auth.token_saved", {"prefix": token[:4], "has_refresh": bool(refresh_token)})
    print(f"[brainstem] GitHub token saved (prefix: {token[:4]}...)")

def refresh_github_token():
    """Try to refresh an expired GitHub token using the stored refresh_token."""
    data = _read_token_file()
    if not data or not data.get("refresh_token"):
        return None
    try:
        resp = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            data=(
                f"client_id={COPILOT_CLIENT_ID}"
                f"&grant_type=refresh_token"
                f"&refresh_token={data['refresh_token']}"
            ),
            timeout=10,
        )
        result = resp.json()
        if result.get("access_token"):
            new_token = result["access_token"]
            new_refresh = result.get("refresh_token", data.get("refresh_token"))
            save_github_token(new_token, new_refresh)
            print(f"[brainstem] GitHub token refreshed successfully")
            return new_token
        print(f"[brainstem] Token refresh failed: {result.get('error', 'unknown')}")
    except Exception as e:
        print(f"[brainstem] Token refresh error: {e}")
    return None

def _load_copilot_cache():
    """Load cached Copilot API token from disk."""
    if not os.path.exists(_copilot_cache_file):
        return None
    try:
        with open(_copilot_cache_file) as f:
            data = json.load(f)
        if data.get("token") and time.time() < data.get("expires_at", 0) - 60:
            return data
    except Exception:
        pass
    return None

def _save_copilot_cache(token, endpoint, expires_at):
    """Cache Copilot API token to disk so it survives restarts."""
    try:
        with open(_copilot_cache_file, "w") as f:
            json.dump({"token": token, "endpoint": endpoint, "expires_at": expires_at}, f)
    except Exception:
        pass

# ── Copilot token exchange ────────────────────────────────────────────────────

_copilot_token_cache = {"token": None, "endpoint": None, "expires_at": 0}

def _exchange_github_for_copilot(github_token):
    """Exchange a GitHub token for a Copilot API token. Returns (token, endpoint, expires_at) or raises."""
    auth_prefix = "token" if github_token.startswith("ghu_") else "Bearer"
    print(f"[brainstem] Exchanging token (prefix: {github_token[:8]}..., auth: {auth_prefix})")
    resp = requests.get(
        COPILOT_TOKEN_URL,
        headers={
            "Authorization": f"{auth_prefix} {github_token}",
            "Accept": "application/json",
            "Editor-Version": "vscode/1.95.0",
            "Editor-Plugin-Version": "copilot/1.0.0",
            "User-Agent": "GitHubCopilotChat/0.22.2024",
        },
        timeout=10,
    )
    print(f"[brainstem] Exchange response: HTTP {resp.status_code} — {resp.text[:300]}")
    return resp

def get_copilot_token():
    """Exchange GitHub token for a short-lived Copilot API token."""
    global _copilot_token_cache
    
    # 1. Return in-memory cached token if still valid (with 60s buffer)
    if _copilot_token_cache["token"] and time.time() < _copilot_token_cache["expires_at"] - 60:
        return _copilot_token_cache["token"], _copilot_token_cache["endpoint"]
    
    # 2. Try disk-cached Copilot session token (survives restarts)
    disk_cache = _load_copilot_cache()
    if disk_cache:
        _copilot_token_cache = disk_cache
        _tlog("auth.copilot_restored", {"expires_in": int(disk_cache['expires_at'] - time.time())})
        print(f"[brainstem] Copilot token restored from cache (expires in {int(disk_cache['expires_at'] - time.time())}s)")
        return disk_cache["token"], disk_cache["endpoint"]
    
    # 3. Exchange GitHub token for Copilot token
    github_token = get_github_token()
    if not github_token:
        _tlog("auth.no_github_token", level="warn")
        raise RuntimeError("Not authenticated. Visit /login in your browser to sign in with GitHub.")
    
    _tlog("auth.copilot_exchange", {"token_prefix": github_token[:4]})
    resp = _exchange_github_for_copilot(github_token)
    
    # 4. If error, the GitHub token may have expired — try refreshing it
    if resp.status_code in (401, 403, 404):
        _tlog("auth.copilot_exchange_failed", {"status": resp.status_code, "trying_refresh": True}, level="warn")
        refreshed = refresh_github_token()
        if refreshed:
            resp = _exchange_github_for_copilot(refreshed)
        if resp.status_code in (401, 403, 404):
            # Token exchange failed — NEVER delete the token file.
            try:
                err_body = resp.json()
                err_details = err_body.get("error_details", {})
                notification_id = err_details.get("notification_id", "")
            except Exception:
                err_details = {}
                notification_id = ""

            if notification_id == "no_copilot_access":
                # Extract username from error message
                detail_msg = err_details.get("message", "")
                username = detail_msg.split("as ")[-1].rstrip(".") if "as " in detail_msg else "this account"
                _tlog("auth.no_copilot_access", {"username": username}, level="error")
                print(f"[brainstem] No Copilot access for {username}")
                # Delete the bad token so health check shows unauthenticated
                if os.path.exists(_token_file):
                    os.remove(_token_file)
                raise RuntimeError(
                    f"NO_COPILOT_ACCESS:{username}"
                )

            try:
                err_msg = err_body.get("message", resp.text[:200])
            except Exception:
                err_msg = resp.text[:200]
            _tlog("auth.copilot_exchange_error", {"status": resp.status_code, "error": err_msg[:200]}, level="error")
            print(f"[brainstem] Copilot token exchange failed (HTTP {resp.status_code}): {err_msg}")
            raise RuntimeError(
                f"Copilot auth failed ({resp.status_code}): {err_msg}. Sign in with GitHub to retry."
            )
    resp.raise_for_status()
    
    data = resp.json()
    copilot_token = data.get("token")
    endpoint = data.get("endpoints", {}).get("api", "https://api.individual.githubcopilot.com")
    expires_at = data.get("expires_at", time.time() + 600)
    
    if not copilot_token:
        _tlog("auth.copilot_no_token", level="error")
        raise RuntimeError("Failed to get Copilot API token. Check your Copilot subscription.")
    
    _copilot_token_cache = {
        "token": copilot_token,
        "endpoint": endpoint,
        "expires_at": expires_at,
    }
    _save_copilot_cache(copilot_token, endpoint, expires_at)
    
    _tlog("auth.copilot_ready", {"expires_in": int(expires_at - time.time()), "endpoint": endpoint})
    print(f"[brainstem] Copilot token refreshed (expires in {int(expires_at - time.time())}s)")
    return copilot_token, endpoint

# ── Device code OAuth flow ────────────────────────────────────────────────────

_pending_login = {}
_login_bg_thread = None
_login_result = {}  # Written by bg poll thread, read by /login/poll endpoint
_pending_login_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".copilot_pending")

def _save_pending_login():
    """Persist pending device code to disk so it survives server restarts."""
    try:
        if _pending_login:
            with open(_pending_login_file, "w") as f:
                json.dump(_pending_login, f)
        elif os.path.exists(_pending_login_file):
            os.remove(_pending_login_file)
    except Exception:
        pass

def _load_pending_login():
    """Load pending device code from disk on startup."""
    global _pending_login
    if not os.path.exists(_pending_login_file):
        return
    try:
        with open(_pending_login_file) as f:
            data = json.load(f)
        if data.get("device_code") and time.time() < data.get("expires_at", 0):
            _pending_login = data
            print(f"[brainstem] Resumed pending device code: {data.get('user_code')} (expires in {int(data['expires_at'] - time.time())}s)")
            _start_bg_poll()
        else:
            # Expired — clean up
            os.remove(_pending_login_file)
    except Exception:
        pass

def start_device_code_login(force_new=False):
    """Start GitHub device code OAuth flow. Returns user_code and verification_uri.
    
    Reuses an existing pending code if it hasn't expired (prevents refresh-kills-auth bug).
    Set force_new=True to always request a fresh code.
    """
    global _pending_login, _login_bg_thread, _login_result, _copilot_token_cache

    # Reuse existing non-expired code (e.g. user refreshed the page)
    if not force_new and _pending_login and time.time() < _pending_login.get("expires_at", 0):
        _tlog("login.reuse_code", {"user_code": _pending_login["user_code"], "expires_in": int(_pending_login["expires_at"] - time.time())})
        print(f"[brainstem] Reusing existing device code (expires in {int(_pending_login['expires_at'] - time.time())}s)")
        return {
            "user_code": _pending_login["user_code"],
            "verification_uri": _pending_login["verification_uri"],
        }

    # Clear stale state so the new flow starts completely clean
    _login_result = {}
    _copilot_token_cache = {"token": None, "endpoint": None, "expires_at": 0}
    if os.path.exists(_copilot_cache_file):
        try:
            os.remove(_copilot_cache_file)
        except Exception:
            pass

    resp = requests.post(
        "https://github.com/login/device/code",
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        data=f"client_id={COPILOT_CLIENT_ID}",
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    _pending_login = {
        "device_code": data["device_code"],
        "user_code": data["user_code"],
        "verification_uri": data["verification_uri"],
        "interval": data.get("interval", 5),
        "expires_at": time.time() + data.get("expires_in", 900),
    }
    _save_pending_login()
    _tlog("login.device_code_started", {"user_code": data["user_code"]})
    print(f"[brainstem] Device code login started: {data['user_code']}")

    # Start background polling so token is captured even if browser disconnects
    _start_bg_poll()

    return {
        "user_code": data["user_code"],
        "verification_uri": data["verification_uri"],
    }

def _start_bg_poll():
    """Start a background thread that polls GitHub for device code completion."""
    global _login_bg_thread
    if _login_bg_thread and _login_bg_thread.is_alive():
        return  # Already running
    _login_bg_thread = threading.Thread(target=_bg_poll_loop, daemon=True)
    _login_bg_thread.start()

def _bg_poll_loop():
    """Background loop: polls GitHub for the device code token.

    This is the SOLE caller of poll_device_code(). The /login/poll endpoint
    reads _login_result instead of calling poll_device_code() directly,
    which eliminates the race condition between bg thread and client poll.
    """
    global _login_result
    while _pending_login:
        interval = _pending_login.get("interval", 5)
        time.sleep(interval)
        if not _pending_login:
            break
        try:
            token = poll_device_code()
            if token:
                print(f"[brainstem] Background poll: token acquired (prefix: {token[:4]}...)")
                # Eagerly exchange for Copilot token
                try:
                    get_copilot_token()
                    print("[brainstem] Copilot session established via background poll")
                    _login_result = {"status": "ok", "message": "Authenticated with GitHub Copilot!"}
                except Exception as e:
                    err = str(e)
                    if err.startswith("NO_COPILOT_ACCESS:"):
                        print(f"[brainstem] Background poll: no Copilot access — {err}")
                        _login_result = {"status": "error", "error": err}
                    else:
                        print(f"[brainstem] Eager Copilot exchange deferred: {e}")
                        _login_result = {"status": "ok", "message": "Authenticated with GitHub Copilot!"}
                break
        except RuntimeError as e:
            print(f"[brainstem] Background poll stopped: {e}")
            _login_result = {"status": "error", "error": str(e)}
            break
        except Exception as e:
            print(f"[brainstem] Background poll error: {e}")
            # Keep polling on transient errors

def poll_device_code():
    """Poll for completed device code authorization. Returns token or None."""
    global _pending_login
    if not _pending_login:
        return None

    if time.time() >= _pending_login.get("expires_at", 0):
        _pending_login = {}
        _save_pending_login()
        _tlog("login.code_expired", level="warn")
        raise RuntimeError("Login code expired. Please try again.")

    resp = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        data=(
            f"client_id={COPILOT_CLIENT_ID}"
            f"&device_code={_pending_login['device_code']}"
            f"&grant_type=urn:ietf:params:oauth:grant-type:device_code"
        ),
        timeout=10,
    )
    data = resp.json()

    if data.get("access_token"):
        token = data["access_token"]
        refresh = data.get("refresh_token")
        _tlog("login.authorized", {"token_prefix": token[:4], "has_refresh": bool(refresh)})
        print(f"[brainstem] Device code authorized! Token prefix: {token[:4]}...")
        save_github_token(token, refresh)
        _pending_login = {}
        _save_pending_login()
        return token

    error = data.get("error", "")
    if error == "slow_down":
        _tlog("login.slow_down", level="warn")
        _pending_login["interval"] = _pending_login.get("interval", 5) + 5
        return None
    if error == "authorization_pending":
        return None  # Keep polling
    if error == "expired_token":
        _pending_login = {}
        _save_pending_login()
        _tlog("login.expired_token", level="warn")
        raise RuntimeError("Login code expired. Please try again.")
    if error:
        _pending_login = {}
        _save_pending_login()
        raise RuntimeError(f"Login failed: {error}")

    return None

# ── Soul loader ───────────────────────────────────────────────────────────────

_soul_cache = None

def load_soul():
    global _soul_cache
    if _soul_cache is not None:
        return _soul_cache
    if not os.path.exists(SOUL_PATH):
        print(f"[brainstem] Warning: soul file not found at {SOUL_PATH}, using default.")
        _soul_cache = "You are a helpful AI assistant."
        return _soul_cache
    with open(SOUL_PATH, "r") as f:
        _soul_cache = f.read().strip()
    print(f"[brainstem] Soul loaded: {SOUL_PATH}")
    return _soul_cache

# ── Agent loader ──────────────────────────────────────────────────────────────


def _load_agent_from_file(filepath):
    """Load agent classes from a single .py file. Returns dict of name→instance.
    Auto-installs missing pip packages and shims cloud deps to local storage."""
    agents = {}
    brainstem_dir = os.path.dirname(os.path.abspath(__file__))
    if brainstem_dir not in sys.path:
        sys.path.insert(0, brainstem_dir)
    
    _register_shims()
    
    # Try loading, auto-install missing deps, retry once
    for attempt in range(2):
        try:
            mod_name = f"agent_{os.path.basename(filepath).replace('.', '_')}_{id(filepath)}_{attempt}"
            spec = importlib.util.spec_from_file_location(mod_name, filepath)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr in dir(mod):
                cls = getattr(mod, attr)
                if (
                    isinstance(cls, type)
                    and hasattr(cls, "perform")
                    and attr not in ("BasicAgent", "object")
                    and not attr.startswith("_")
                ):
                    instance = cls()
                    agents[instance.name] = instance
            break  # success
        except ModuleNotFoundError as e:
            missing = _extract_package_name(e)
            if missing and attempt == 0:
                _auto_install(missing)
                continue  # retry after install
            print(f"[brainstem] Failed to load {filepath}: {e}")
        except Exception as e:
            print(f"[brainstem] Failed to load {filepath}: {e}")
            break
    return agents


# ── Shims & auto-install ─────────────────────────────────────────────────────

_shims_registered = False

def _register_shims():
    """Register local shims for cloud dependencies so agents import them transparently."""
    global _shims_registered
    if _shims_registered:
        return
    
    import types
    brainstem_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Shim: agents.basic_agent → local basic_agent
    try:
        # Try loading from agents/ subdirectory first, then flat
        agents_dir = os.path.join(brainstem_dir, "agents")
        if agents_dir not in sys.path:
            sys.path.insert(0, agents_dir)
        from basic_agent import BasicAgent as _BA
        if "agents" not in sys.modules:
            agents_mod = types.ModuleType("agents")
            agents_mod.__path__ = [agents_dir]
            sys.modules["agents"] = agents_mod
        if "agents.basic_agent" not in sys.modules:
            ba_mod = types.ModuleType("agents.basic_agent")
            ba_mod.BasicAgent = _BA
            sys.modules["agents.basic_agent"] = ba_mod
            sys.modules["agents"].basic_agent = ba_mod
        # Shim: openrappter.agents.basic_agent → same BasicAgent
        if "openrappter" not in sys.modules:
            or_mod = types.ModuleType("openrappter")
            or_mod.__path__ = [brainstem_dir]
            sys.modules["openrappter"] = or_mod
        if "openrappter.agents" not in sys.modules:
            or_agents = types.ModuleType("openrappter.agents")
            or_agents.__path__ = [agents_dir]
            or_agents.basic_agent = sys.modules["agents.basic_agent"]
            sys.modules["openrappter.agents"] = or_agents
            sys.modules["openrappter"].agents = or_agents
        if "openrappter.agents.basic_agent" not in sys.modules:
            sys.modules["openrappter.agents.basic_agent"] = sys.modules["agents.basic_agent"]
    except ImportError as e:
        print(f"[brainstem] Warning: Could not load BasicAgent: {e}")
        pass
    
    # Shim: utils.azure_file_storage → local_storage.py
    # local_storage.py lives under rapp_brainstem/utils/ (root stays minimal
    # per Article XI). Add utils/ to sys.path so the bare import resolves.
    utils_dir = os.path.join(brainstem_dir, "utils")
    if utils_dir not in sys.path:
        sys.path.insert(0, utils_dir)
    from local_storage import AzureFileStorageManager as _LSM
    if "utils" not in sys.modules:
        utils_mod = types.ModuleType("utils")
        utils_mod.__path__ = [os.path.join(brainstem_dir, "utils")]
        sys.modules["utils"] = utils_mod
    afs_mod = types.ModuleType("utils.azure_file_storage")
    afs_mod.AzureFileStorageManager = _LSM
    sys.modules["utils.azure_file_storage"] = afs_mod
    if hasattr(sys.modules["utils"], "__path__"):
        sys.modules["utils"].azure_file_storage = afs_mod
    
    # Shim: utils.dynamics_storage → same local storage
    ds_mod = types.ModuleType("utils.dynamics_storage")
    ds_mod.DynamicsStorageManager = _LSM
    sys.modules["utils.dynamics_storage"] = ds_mod
    
    # Shim: utils.storage_factory → returns local storage manager
    sf_mod = types.ModuleType("utils.storage_factory")
    sf_mod.get_storage_manager = lambda: _LSM()
    sys.modules["utils.storage_factory"] = sf_mod
    if hasattr(sys.modules["utils"], "__path__"):
        sys.modules["utils"].storage_factory = sf_mod

    # Hand utils.llm a callable for the brainstem's live Copilot session.
    # Single-file rapps that import `call_llm` from utils.llm now route
    # through whichever LLM is powering the engine itself — no per-rapp
    # AZURE_OPENAI_* / OPENAI_API_KEY needed locally. Tier 2 vendors the
    # same utils/llm.py but never registers a provider, so it falls
    # through to env-configured Azure/OpenAI/Anthropic as before.
    try:
        from utils import llm as _llm_mod
        _llm_mod.register_copilot_provider(get_copilot_token, MODEL)
        print("[brainstem] utils.llm Copilot provider registered")
    except Exception as e:
        print(f"[brainstem] Could not register Copilot provider with utils.llm: {e}")

    _shims_registered = True
    print("[brainstem] Local storage shims registered")


# Map of import names → pip package names
_PIP_MAP = {
    "bs4": "beautifulsoup4",
    "beautifulsoup4": "beautifulsoup4",
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "dotenv": "python-dotenv",
}


def _extract_package_name(error):
    """Extract the pip-installable package name from a ModuleNotFoundError."""
    msg = str(error)
    # "No module named 'bs4'"
    match = __import__("re").search(r"No module named '([^']+)'", msg)
    if not match:
        return None
    mod = match.group(1).split(".")[0]
    return _PIP_MAP.get(mod, mod)


def _auto_install(package):
    """Auto-install a pip package."""
    print(f"[brainstem] Auto-installing dependency: {package}")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package, "-q"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            print(f"[brainstem] Installed {package}")
            # Clear import caches so retry works
            importlib.invalidate_caches()
        else:
            print(f"[brainstem] Failed to install {package}: {result.stderr[:200]}")
    except Exception as e:
        print(f"[brainstem] Failed to install {package}: {e}")

def load_agents():
    # Walk AGENTS_PATH recursively per Article XII (workspace_agents/ + nested
    # user folders). Skip reserved subdirs that never auto-load
    # (experimental_agents/, disabled_agents/) and __pycache__.
    agents = {}
    _SKIP = ("experimental_agents", "disabled_agents", "__pycache__")
    pattern = os.path.join(AGENTS_PATH, "**", "*_agent.py")
    files = [f for f in glob.glob(pattern, recursive=True)
             if not any(s in f.split(os.sep) for s in _SKIP)]

    for filepath in files:
        loaded = _load_agent_from_file(filepath)
        for name, instance in loaded.items():
            agents[name] = instance
            print(f"[brainstem] Agent loaded: {name} ({os.path.relpath(filepath, AGENTS_PATH)})")

    print(f"[brainstem] {len(agents)} agent(s) ready.")
    return agents

# ── LLM call ─────────────────────────────────────────────────────────────────

def call_copilot(messages, tools=None):
    """Call the Copilot chat completions API."""
    copilot_token, endpoint = get_copilot_token()
    
    url = f"{endpoint}/chat/completions"
    headers = {
        "Authorization": f"Bearer {copilot_token}",
        "Content-Type": "application/json",
        "Editor-Version": "vscode/1.95.0",
        "Copilot-Integration-Id": "vscode-chat",
    }
    body = {
        "model": MODEL,
        "messages": messages,
    }
    if tools:
        body["tools"] = tools
        if MODEL not in _NO_TOOL_CHOICE_MODELS:
            body["tool_choice"] = "auto"

    print(f"[brainstem] API call: model={MODEL}, tools={len(tools) if tools else 0}, tool_choice={body.get('tool_choice', 'NONE')}")
    # No twin frame mid-call — the twin only renders when the LLM
    # ships a real <frame> in its |||TWIN||| block at the end of the
    # round. Canned in-flight art would be the brainstem pretending
    # the twin is reacting when it isn't.

    resp = requests.post(url, headers=headers, json=body, timeout=60)
    if resp.status_code != 200:
        error_detail = resp.text[:500] if resp.text else "No details"
        _tlog("api.error", {"model": MODEL, "status": resp.status_code, "detail": error_detail[:300]}, level="error")
        print(f"[brainstem] API error {resp.status_code} with model '{MODEL}': {error_detail}")
        # On 400/429/5xx, cycle through other available models before giving up
        if resp.status_code in (400, 429, 500, 502, 503):
            tried = {MODEL}
            fallback_ids = [m["id"] for m in AVAILABLE_MODELS if m["id"] != MODEL]
            for fallback_model in fallback_ids:
                if fallback_model in tried:
                    continue
                tried.add(fallback_model)
                print(f"[brainstem] Retrying with {fallback_model}...")
                body["model"] = fallback_model
                if fallback_model in _NO_TOOL_CHOICE_MODELS:
                    body.pop("tool_choice", None)
                elif tools and "tool_choice" not in body:
                    body["tool_choice"] = "auto"
                resp = requests.post(url, headers=headers, json=body, timeout=60)
                if resp.status_code == 200:
                    break
                print(f"[brainstem] {fallback_model} also failed ({resp.status_code})")
    resp.raise_for_status()
    result = resp.json()

    # ── Normalize multi-choice responses ──────────────────────────────────────
    # Some models (e.g. Claude via Copilot API) split text and tool_calls into
    # separate choices.  Merge them into a single choice so the rest of the
    # codebase can treat the response uniformly.
    choices = result.get("choices", [])
    if len(choices) > 1:
        merged = {"role": "assistant", "content": None, "tool_calls": []}
        for c in choices:
            m = c.get("message", {})
            if m.get("content"):
                merged["content"] = (merged["content"] or "") + m["content"]
            if m.get("tool_calls"):
                merged["tool_calls"].extend(m["tool_calls"])
        if not merged["tool_calls"]:
            del merged["tool_calls"]
        fr = "tool_calls" if merged.get("tool_calls") else choices[0].get("finish_reason", "stop")
        result["choices"] = [{"message": merged, "finish_reason": fr}]

    # Debug logging
    choice = result.get("choices", [{}])[0]
    msg = choice.get("message", {})
    fr = choice.get("finish_reason", "")
    has_tools = bool(msg.get("tool_calls"))
    print(f"[brainstem] API response: finish_reason={fr}, has_tool_calls={has_tools}, content_len={len(msg.get('content') or '')}")
    if has_tools:
        names = [tc.get("function", {}).get("name", "?") for tc in msg["tool_calls"]]
        print(f"[brainstem]   tool_calls: {names}")
        # In-flight working frame — stock line, just a status indicator
        # while the twin is busy. The TWIN's actual voice for this turn
        # comes from the |||TWIN||| block emitted at the end of the
        # whole chat round (see /chat handler), not from per-step lines.
        # No twin frame mid-tool-call either — same rule as in-flight.
    # No 'speaking' / 'puzzled' frame here anymore — those are emitted
    # in the /chat handler AFTER parsing the |||TWIN||| block out of the
    # final reply. Doing it here would print the assistant content
    # (which may still contain |||VOICE||| / |||TWIN||| markers) instead
    # of the twin's intended voice.

    return result

# ── Agent execution ───────────────────────────────────────────────────────────


def run_tool_calls(tool_calls, agents, session_id=None, user_guid=None):
    """Returns (tool_results_for_messages, structured_logs).
    structured_logs is a list of dicts shaped {name, args, output, error?}
    — what the chat UI reads to render the "▶ AGENT CALLED <Name>" chip
    under the assistant bubble. Previously this was a list of pre-joined
    strings, which the UI couldn't pick the agent name out of cleanly."""
    results = []
    logs = []
    for tc in tool_calls:
        fn_name = tc["function"]["name"]
        try:
            args = json.loads(tc["function"].get("arguments", "{}"))
        except Exception:
            args = {}

        # Thread the caller's user_guid into every agent call (Tier 2 parity:
        # CommunityRAPP function_app.py line 693). Memory agents key by it;
        # other agents are free to ignore it. Don't overwrite if the LLM
        # explicitly passed one — the caller wins by convention.
        if user_guid and "user_guid" not in args:
            args["user_guid"] = user_guid

        print(f"[brainstem] {fn_name} args: {json.dumps(args)[:200]}")

        agent = agents.get(fn_name)
        log_entry = {"name": fn_name, "args": args, "output": ""}
        if agent:
            try:
                result = agent.perform(**args)
                log_entry["output"] = result
            except TypeError as e:
                # Agent's perform() doesn't accept user_guid kwarg — drop it and retry.
                # Backwards compat for older agents that haven't adopted the threaded identity.
                if "user_guid" in args and "user_guid" in str(e):
                    args.pop("user_guid", None)
                    try:
                        result = agent.perform(**args)
                        log_entry["args"] = args
                        log_entry["output"] = result
                    except Exception as e2:
                        result = f"Error: {e2}"
                        log_entry["output"] = result
                        log_entry["error"] = str(e2)
                else:
                    result = f"Error: {e}"
                    log_entry["output"] = result
                    log_entry["error"] = str(e)
            except Exception as e:
                result = f"Error: {e}"
                log_entry["output"] = result
                log_entry["error"] = str(e)
        else:
            result = f"Agent '{fn_name}' not found."
            log_entry["output"] = result
            log_entry["error"] = "agent not found"
        logs.append(log_entry)

        results.append({
            "tool_call_id": tc["id"],
            "role": "tool",
            "name": fn_name,
            "content": str(result)
        })
    return results, logs

# ── Senses Layer (Constitution Article XXIV) ─────────────────────────────────
#
# A sense is a TRANSLATION of the main response into a different mode of
# expression. VOICE = the response, said aloud. TWIN = the response, as a
# felt reaction. They are not new content — they are the same answer,
# re-perceived through a different channel. Monkey sees, monkey speaks,
# monkey hears.
#
# Senses are SINGLE-FILE just like agents:
#   rapp_brainstem/utils/senses/<name>_sense.py   ← bundled defaults
#   <user pulls more from the rapp_store>   ← installable
#
# Each *_sense.py defines four module-level vars:
#   name           — short id, used for splitter bookkeeping
#   delimiter      — e.g. "|||VOICE|||" (Article II — fixed forever once
#                    allocated)
#   response_key   — chat-response field name, e.g. "voice_response"
#   system_prompt  — the instruction telling the LLM to emit this slot
#
# Optional:
#   wrapper_tag    — XML tag the LLM may wrap content in (defaults to `name`)
#
# To install a sense from the store: drop the file in senses/, restart.
# To remove: delete the file. Soul is untouched. Other senses unaffected.
# (A dog that wakes up with three legs makes the best of it.)

SENSES_PATH = os.getenv("SENSES_PATH", os.path.join(os.path.dirname(__file__), "utils", "senses"))

def load_senses():
    """Discover *_sense.py files in SENSES_PATH. Each file is a tiny
    module exposing name / delimiter / response_key / system_prompt.
    Reloaded every chat request so adding/removing a sense file
    takes effect without a brainstem restart."""
    senses = []
    if not os.path.isdir(SENSES_PATH):
        return senses
    for filepath in sorted(glob.glob(os.path.join(SENSES_PATH, "*_sense.py"))):
        try:
            spec = importlib.util.spec_from_file_location(
                f"_sense_{os.path.basename(filepath)[:-3]}", filepath
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            sense = {
                "name":          getattr(mod, "name"),
                "delimiter":     getattr(mod, "delimiter"),
                "response_key":  getattr(mod, "response_key"),
                "wrapper_tag":   getattr(mod, "wrapper_tag", getattr(mod, "name")),
                "system_prompt": getattr(mod, "system_prompt", ""),
            }
            senses.append(sense)
        except Exception as e:
            print(f"[brainstem] Sense load failed: {os.path.basename(filepath)}: {e}")
    return senses

def _compose_senses_prompt(senses):
    """Concatenate every sense's system_prompt as its own paragraph
    appended to the soul. Each fragment is independent — no cross-
    references — so removing a sense doesn't dangle anything."""
    return "".join("\n\n" + s["system_prompt"] for s in senses if s.get("system_prompt"))


def _split_reply_by_senses(reply, senses):
    """Walk the reply, find each registered sense's delimiter (if present),
    extract the content between that delimiter and the next sense's
    delimiter (or end-of-reply). Return (main_text, {sense_name: content}).

    Senses absent from the reply get an empty string. This is the
    'always present, possibly empty' contract that lets frontends read
    sense fields without conditional guards.

    Order is determined by *position in the reply*, not registry order —
    the LLM is free to emit senses in any order, and the splitter follows."""
    found = []
    for s in senses:
        idx = reply.find(s["delimiter"])
        if idx >= 0:
            found.append((idx, s))
    parts = {s["name"]: "" for s in senses}
    if not found:
        return reply, parts
    found.sort()
    main_text = reply[:found[0][0]]
    for i, (idx, sense) in enumerate(found):
        start = idx + len(sense["delimiter"])
        end = found[i + 1][0] if i + 1 < len(found) else len(reply)
        parts[sense["name"]] = reply[start:end]
    return main_text, parts


# ── /chat endpoint ────────────────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    user_input = data.get("user_input", "").strip()
    history    = data.get("conversation_history", [])
    session_id = data.get("session_id") or str(uuid.uuid4())
    # Per-chat agent filter (additive, backwards compatible). When the
    # client sends `enabled_agents` as a list, the request only sees those
    # agent NAMES — both in the LLM tool definitions and in tool-call
    # dispatch. Omitted/None → all installed agents available (existing
    # behavior). The chat UI uses this to keep separate chat tabs scoped
    # to different agent subsets without unloading anything from disk.
    enabled_agents = data.get("enabled_agents")
    # Optional caller identity (additive, backwards compatible). Tier 1 callers
    # — humans at the keyboard, the local UI — typically omit it; the default
    # routes to shared global memory which IS "your" memory on a single-operator
    # machine. Peer brainstems and multi-tenant clients pass their own GUID.
    user_guid  = data.get("user_guid") or DEFAULT_USER_GUID

    if not user_input:
        return jsonify({"error": "user_input is required"}), 400

    _tlog("chat.request", {"session_id": session_id, "input_len": len(user_input), "history_len": len(history), "user_guid": user_guid})

    try:
        soul   = load_soul()
        agents = load_agents()
        # Apply per-request filter: enabled_agents is the allowlist of
        # agent NAMES. None/missing = no filter. Empty list = no agents
        # available for this turn (chat works as a pure LLM convo).
        if isinstance(enabled_agents, list):
            allow = set(enabled_agents)
            filtered_count = len(agents) - sum(1 for n in agents if n in allow)
            agents = {n: a for n, a in agents.items() if n in allow}
            if filtered_count > 0:
                _tlog("chat.agents_filtered", {"requested": len(allow), "active": len(agents), "filtered_out": filtered_count})
        tools  = [a.to_tool() for a in agents.values()] if agents else None

        # ── Collect system context from any agent that provides it ──
        extra_context = ""
        for agent in agents.values():
            try:
                ctx = agent.system_context()
                if ctx:
                    extra_context += "\n" + ctx
            except Exception as e:
                print(f"[brainstem] system_context failed for {agent.name}: {e}")

        # Soul + per-agent context + senses layer (Article XXIV). Senses
        # are auto-discovered single files from rapp_brainstem/utils/senses/ —
        # independent from the soul, so adding/losing a sense never
        # touches the agent's identity prompt. Reloaded per request so
        # dropping a new sense file takes effect with no restart.
        senses = load_senses()
        system_content = soul + extra_context + _compose_senses_prompt(senses)

        messages = [{"role": "system", "content": system_content}]
        messages += [m for m in history if m.get("role") in ("user", "assistant", "tool")]
        messages.append({"role": "user", "content": user_input})

        all_logs = []
        # Up to 3 tool-call rounds
        for _ in range(3):
            response = call_copilot(messages, tools=tools)
            choice   = response["choices"][0]
            msg      = choice["message"]
            finish   = choice.get("finish_reason", "")
            messages.append(msg)

            # Some models use finish_reason "tool_calls", others just include tool_calls in the message
            if msg.get("tool_calls"):
                print(f"[brainstem] Tool calls triggered (finish_reason={finish}): {[tc['function']['name'] for tc in msg['tool_calls']]}")
                tool_results, logs = run_tool_calls(msg["tool_calls"], agents, session_id=session_id, user_guid=user_guid)
                all_logs.extend(logs)
                messages.extend(tool_results)
            else:
                break

        reply = msg.get("content") or ""
        
        # Both response keys forever. The CA365 family (CommunityRAPP, rapp_swarm)
        # has shipped `assistant_response` since the original implementation.
        # rapp_brainstem renamed it to `response` along the way — that drift was
        # a tier-parity violation. Per Article XXV (chat is the only wire,
        # additive-only schema evolution), we emit both keys with the same value
        # so clients of either lineage land on the data they expect.
        # ── Frame recording ─────────────────────────────────────────
        # Every interaction is a frame: local virtual time + UTC + payload.
        # Frames are the unit dreamcatcher reconciles when divergent twin
        # incarnations are assimilated. The frame log lives at
        # .brainstem_data/frames.jsonl and is auto-packed in twin/snapshot
        # eggs (the per-incarnation stream_id is excluded so destination
        # brainstems mint their own).
        try:
            from utils import frames as frames_mod
            frames_mod.record_frame("chat", {
                "user_input": user_input,
                "assistant_response": reply,
                "session_id": session_id,
                "user_guid": user_guid,
                "agent_logs": all_logs,
                "model": MODEL,
                "history_len_in": len(history),
                "rounds": len([m for m in messages if m.get("role") == "assistant"]),
            })
        except Exception as e:
            print(f"[brainstem] frame record failed: {e}")

        result = {
            "response": reply,
            "assistant_response": reply,
            "session_id": session_id,
            "user_guid": user_guid,
            # Structured array — list of {name, args, output, error?}.
            # Chat UI uses this directly to render "▶ AGENT CALLED <Name>"
            # chips under the assistant bubble. Joined-string back-compat
            # for older clients lives under agent_logs_text.
            "agent_logs": all_logs,
            "agent_logs_text": "\n".join(
                f"[{e['name']}] {e['output']}" for e in all_logs
            ),
            "voice_mode": VOICE_MODE,
            "twin_mode":  TWIN_MODE,
        }

        # Per Article II, each slot's content may be wrapped in matching
        # XML tags — the wrapper is the LLM's explicit boundary marker.
        # We strip the outer wrapper so consumers receive bare content.
        def _unwrap(text, tag):
            t = (text or "").strip()
            open_tag = "<" + tag + ">"
            close_tag = "</" + tag + ">"
            if t.startswith(open_tag) and t.endswith(close_tag):
                return t[len(open_tag):-len(close_tag)].strip()
            return t

        # Senses-layer split (Article XXIV). One pass over the reply
        # extracts every registered sense's content; senses absent from
        # the reply land as empty string — but ALWAYS as a key in the
        # result, so frontends can read result[response_key] without
        # conditional guards.
        main_text, sense_parts = _split_reply_by_senses(reply, senses)
        result["response"] = _unwrap(main_text, "main")
        result["assistant_response"] = result["response"]
        for s in senses:
            raw = sense_parts.get(s["name"], "")
            result[s["response_key"]] = _unwrap(raw, s["wrapper_tag"]) if raw else ""

        # Final twin frame for this chat round. The cage's content
        # comes ENTIRELY from <frame>...</frame> inside the |||TWIN|||
        # block — the LLM hand-authors the ASCII art per turn and we
        # render it. No prose extraction, no speech bubble. The art
        # IS the twin's voice. If the LLM didn't ship a frame this
        # turn, _twin_emit no-ops silently (no fake animation).
        twin_text = (result.get("twin_response") or "").strip()
        twin_figure, _rest = _extract_twin_frame(twin_text)
        _twin_emit("done", figure=twin_figure)

        return jsonify(result)

    except requests.exceptions.HTTPError as e:
        traceback.print_exc()
        status = e.response.status_code if e.response is not None else 502
        detail = (e.response.text[:300] if e.response is not None else str(e)[:300])
        _tlog("chat.error", {"model": MODEL, "status": status, "detail": detail[:200]}, level="error")
        if status == 429 or "quota" in detail.lower():
            msg = "Copilot usage limit reached — wait a minute and try again."
        else:
            msg = f"Model '{MODEL}' returned {status}. All fallback models also failed — try again shortly or switch models."
        return jsonify({
            "error": msg,
            "model": MODEL,
            "detail": detail
        }), 502

    except Exception as e:
        traceback.print_exc()
        _tlog("chat.error", {"error": str(e)[:200]}, level="error")
        return jsonify({"error": str(e)}), 500

# ── /health endpoint ──────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def index():
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")

@app.route("/web/<path:filename>", methods=["GET"])
def web_static(filename):
    """Serve files from the web/ directory."""
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "web"), filename)

# Convenience routes for the named UI pages in web/ — so /manage works
# (not just /web/manage.html). The chat UI links to these clean paths.
@app.route("/manage", methods=["GET"])
def manage_page():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "web"), "manage.html")

@app.route("/binder", methods=["GET"])
@app.route("/binder.html", methods=["GET"])
def binder_page():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "web"), "binder.html")

@app.route("/rapplications", methods=["GET"])
def rapplications_page():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "web"), "rapplications.html")

@app.route("/login", methods=["POST"])
def login():
    """Start GitHub device code OAuth flow."""
    try:
        data = start_device_code_login()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/login/poll", methods=["POST"])
def login_poll():
    """Poll for completed device code authorization.

    Reads _login_result (written by the bg poll thread) instead of calling
    poll_device_code() directly. This eliminates the race where the bg thread
    and client poll both compete for the same device code response.
    """
    # Check if bg thread has completed (or errored)
    if _login_result:
        result = _login_result.copy()
        if result.get("status") == "error":
            return jsonify(result)
        return jsonify(result)

    # Check if code has expired
    if _pending_login and time.time() >= _pending_login.get("expires_at", 0):
        return jsonify({"status": "expired", "error": "Login code expired. Please try again."})

    # No pending login at all (e.g., server restarted, or flow was never started)
    if not _pending_login:
        return jsonify({"status": "expired", "error": "No login in progress. Please try again."})

    return jsonify({"status": "pending"})

@app.route("/login/status", methods=["GET"])
def login_status():
    """Check if a login flow is currently in progress. Returns code info for UI resume."""
    if _pending_login and time.time() < _pending_login.get("expires_at", 0):
        return jsonify({
            "pending": True,
            "user_code": _pending_login.get("user_code"),
            "verification_uri": _pending_login.get("verification_uri"),
            "expires_in": int(_pending_login["expires_at"] - time.time()),
        })
    return jsonify({"pending": False})

@app.route("/login/switch", methods=["POST"])
def login_switch():
    """Switch GitHub account — clears all cached tokens and starts fresh login."""
    global _copilot_token_cache, _pending_login, _login_result
    _tlog("auth.account_switch")

    # Clear everything: memory caches, disk caches, pending login, prior result
    _copilot_token_cache = {"token": None, "endpoint": None, "expires_at": 0}
    _pending_login = {}
    _login_result = {}
    _save_pending_login()

    for f in (_token_file, _copilot_cache_file):
        try:
            if os.path.exists(f):
                os.remove(f)
        except Exception:
            pass

    # Start a fresh device code flow immediately
    try:
        data = start_device_code_login(force_new=True)
        _tlog("auth.switch_new_code", {"user_code": data["user_code"]})
        return jsonify({"status": "ok", **data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/models", methods=["GET"])
def list_models():
    """List available models and current selection. Fetches from Copilot API on first call."""
    _fetch_copilot_models()
    return jsonify({"models": AVAILABLE_MODELS, "current": MODEL})

@app.route("/models/set", methods=["POST"])
def set_model():
    """Change the active model."""
    global MODEL
    data = request.get_json(force=True) or {}
    new_model = data.get("model", "").strip()
    _fetch_copilot_models()
    valid_ids = [m["id"] for m in AVAILABLE_MODELS]
    if new_model not in valid_ids:
        return jsonify({"error": f"Unknown model. Available: {valid_ids}"}), 400
    MODEL = new_model
    return jsonify({"model": MODEL})

@app.route("/voice", methods=["GET"])
def voice_status():
    """Get voice mode status."""
    return jsonify({"voice_mode": VOICE_MODE})

@app.route("/voice/config", methods=["GET"])
def voice_config():
    """Serve voice config from password-protected voice.zip."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    voice_zip = os.path.join(base_dir, "voice.zip")
    password = request.args.get("password", "").encode() or VOICE_ZIP_PW
    if os.path.exists(voice_zip):
        try:
            import pyzipper
            with pyzipper.AESZipFile(voice_zip, 'r') as zf:
                with zf.open("voice.json", pwd=password) as f:
                    cfg = json.load(f)
            return jsonify(cfg)
        except (RuntimeError, Exception) as e:
            err = str(e).lower()
            if "password" in err or "bad password" in err or "decrypt" in err:
                # Fallback: try standard zipfile (for unencrypted legacy zips)
                try:
                    import zipfile
                    with zipfile.ZipFile(voice_zip, 'r') as zf:
                        with zf.open("voice.json") as f:
                            cfg = json.load(f)
                    return jsonify(cfg)
                except Exception:
                    return jsonify({"error": "voice.zip password incorrect"}), 403
            return jsonify({"error": str(e)}), 500
    return jsonify({})

@app.route("/voice/config", methods=["POST"])
def voice_config_save():
    """Save voice config to AES-encrypted voice.zip for local persistence."""
    data = request.get_json(force=True) or {}
    password = data.pop("_password", None)
    if not password:
        return jsonify({"error": "Password required to export voice.zip"}), 400
    base_dir = os.path.dirname(os.path.abspath(__file__))
    voice_zip = os.path.join(base_dir, "voice.zip")
    try:
        import pyzipper
        with pyzipper.AESZipFile(voice_zip, 'w',
                                 compression=pyzipper.ZIP_DEFLATED,
                                 encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password.encode())
            zf.writestr("voice.json", json.dumps(data, indent=2))
        return jsonify({"status": "ok", "message": "voice.zip saved (AES encrypted)"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/voice/export", methods=["POST"])
def voice_export():
    """Generate and return a password-protected voice.zip for download."""
    data = request.get_json(force=True) or {}
    password = data.pop("_password", None)
    if not password:
        return jsonify({"error": "Password required"}), 400
    try:
        import pyzipper
        import io
        buf = io.BytesIO()
        with pyzipper.AESZipFile(buf, 'w',
                                 compression=pyzipper.ZIP_DEFLATED,
                                 encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password.encode())
            zf.writestr("voice.json", json.dumps(data, indent=2))
        buf.seek(0)
        from flask import send_file
        return send_file(buf, mimetype='application/zip',
                         as_attachment=True, download_name='voice.zip')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/voice/import", methods=["POST"])
def voice_import():
    """Import a password-protected voice.zip and return its config."""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    password = request.form.get("password", "").encode()
    if not password:
        return jsonify({"error": "Password required"}), 400
    f = request.files['file']
    try:
        import pyzipper
        import io
        buf = io.BytesIO(f.read())
        with pyzipper.AESZipFile(buf, 'r') as zf:
            with zf.open("voice.json", pwd=password) as jf:
                cfg = json.load(jf)
        # Also save to local voice.zip
        base_dir = os.path.dirname(os.path.abspath(__file__))
        voice_zip = os.path.join(base_dir, "voice.zip")
        buf.seek(0)
        with open(voice_zip, 'wb') as out:
            out.write(buf.read())
        return jsonify(cfg)
    except (RuntimeError, Exception) as e:
        err = str(e).lower()
        if "password" in err or "decrypt" in err:
            return jsonify({"error": "Wrong password"}), 403
        return jsonify({"error": str(e)}), 500

@app.route("/voice/toggle", methods=["POST"])
def voice_toggle():
    """Toggle voice mode on/off."""
    global VOICE_MODE
    data = request.get_json(force=True) or {}
    if "enabled" in data:
        VOICE_MODE = bool(data["enabled"])
    else:
        VOICE_MODE = not VOICE_MODE
    return jsonify({"voice_mode": VOICE_MODE})

@app.route("/twin", methods=["GET"])
def twin_status():
    """Get twin mode status."""
    return jsonify({"twin_mode": TWIN_MODE})

@app.route("/twin/toggle", methods=["POST"])
def twin_toggle():
    """Toggle twin mode on/off."""
    global TWIN_MODE
    data = request.get_json(force=True) or {}
    if "enabled" in data:
        TWIN_MODE = bool(data["enabled"])
    else:
        TWIN_MODE = not TWIN_MODE
    return jsonify({"twin_mode": TWIN_MODE})

@app.route("/version", methods=["GET"])
def version():
    """Return the current brainstem version."""
    return jsonify({"version": VERSION})

@app.route("/agents", methods=["GET"])
def list_agents_files():
    """List all agent .py files available with their loaded agent names."""
    files = glob.glob(os.path.join(AGENTS_PATH, "*.py"))
    results = []
    for f in files:
        filename = os.path.basename(f)
        if filename.startswith("__") or not filename.endswith(".py"):
            continue
        try:
            # We don't want to re-download pip packages or run arbitrary init unnecessarily,
            # but if it's already synthetically loaded or safe to parse, _load_agent_from_file is okay.
            loaded = _load_agent_from_file(f)
            agent_names = list(loaded.keys())
        except Exception:
            agent_names = []

        results.append({
            "filename": filename,
            "agents": agent_names
        })

    return jsonify({"files": results})


@app.route("/agents/full", methods=["GET"])
def list_agents_full():
    """Same as /agents but each entry also carries the file's source —
    the local UI's bootBinder() mints client-side cards from this so the
    binder grid matches what Python actually loaded. Skips basic_agent.py
    (the BasicAgent base class — not a usable agent on its own)."""
    files = glob.glob(os.path.join(AGENTS_PATH, "*.py"))
    results = []
    for f in files:
        filename = os.path.basename(f)
        if filename.startswith("__") or filename == "basic_agent.py" or not filename.endswith(".py"):
            continue
        try:
            loaded = _load_agent_from_file(f)
            agent_names = list(loaded.keys())
        except Exception:
            agent_names = []
        try:
            with open(f, "r", encoding="utf-8") as fh:
                source = fh.read()
        except Exception:
            source = ""
        results.append({
            "filename": filename,
            "agents": agent_names,
            "source": source,
        })
    return jsonify({"files": results})


# PWA / web-asset fallthrough routes — the local index.html (forked from
# web/) references rapp.js / manifest / icons / sw.js at root paths.
# Serve them from the web/ directory so the fork doesn't 404.
@app.route("/rapp.js", methods=["GET"])
def rapp_js():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "web"), "rapp.js")

@app.route("/manifest.webmanifest", methods=["GET"])
def manifest_webmanifest():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "web"), "manifest.webmanifest")

@app.route("/icon-192.svg", methods=["GET"])
def icon_192():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "web"), "icon-192.svg")

@app.route("/icon-512.svg", methods=["GET"])
def icon_512():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "web"), "icon-512.svg")

@app.route("/sw.js", methods=["GET"])
def service_worker():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "utils", "web"), "sw.js")

@app.route("/agents/export/<filename>", methods=["GET"])
def agents_export(filename):
    """Export an agent .py file."""
    from flask import send_file
    import werkzeug.utils
    safe_name = werkzeug.utils.secure_filename(filename)
    if not safe_name.endswith('.py'):
        safe_name += '.py'
    filepath = os.path.join(AGENTS_PATH, safe_name)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "Agent not found"}), 404

@app.route("/agents/<filename>", methods=["DELETE"])
def agents_delete(filename):
    """Delete an agent .py file."""
    import werkzeug.utils
    safe_name = werkzeug.utils.secure_filename(filename)
    if not safe_name.endswith('.py'):
        safe_name += '.py'
    filepath = os.path.join(AGENTS_PATH, safe_name)
    if os.path.exists(filepath):
        os.remove(filepath)
        # Reload agents so memory drops it
        try:
            load_agents()
        except Exception:
            pass
        return jsonify({"status": "ok", "message": f"Agent {safe_name} deleted."})
    return jsonify({"error": "Agent not found"}), 404

@app.route("/agents/import", methods=["POST"])
def agents_import():
    """Import an agent .py file or a brainstem-egg/2.0 cartridge.

    Auto-detects between:
      - .py file        → install as a single agent (existing behavior)
      - .egg / .zip blob → unpack via utils.egg (cartridge restore)

    The egg path is what makes the brainstem local-first: a user can drop
    their twin.egg or snapshot.egg here and the digital organism restores
    in place. No binder dependency.
    """
    import werkzeug.utils
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Sniff the upload — read once, dispatch on shape
    blob = f.read()

    # Egg cartridge path (zip with manifest.json — recognized regardless
    # of filename so .egg, .rapplication.egg, .twin.egg all work).
    try:
        from utils import egg as egg_mod
    except ImportError:
        egg_mod = None
    if egg_mod and egg_mod.is_egg_blob(blob):
        result = egg_mod.unpack(blob)
        if not result.get("ok"):
            return jsonify({"error": result.get("error", "egg unpack failed")}), 400
        # Reload agents so newly-restored ones become live for /chat
        try:
            load_agents()
        except Exception as e:
            return jsonify({
                "status": "partial",
                "egg": result,
                "warning": f"Egg unpacked but agents failed to reload: {e}",
            }), 200
        return jsonify({
            "status": "ok",
            "kind": "egg",
            "type": result.get("type"),
            "id": result.get("id"),
            "name": result.get("name"),
            "files_restored": result.get("files_restored"),
            "message": f"{result.get('type')} egg '{result.get('id')}' restored.",
        })

    # Plain .py agent path — also accepts .py.card (RAR card-shelled
    # form). A card with __card__.summon = "<egg url>" is a CARD
    # INCANTATION: dropping the card both installs the bare agent AND
    # auto-summons the embedded twin egg. Cards become summon vectors
    # (alongside QR codes and direct URLs) without any new endpoint.
    fname = f.filename
    if not (fname.endswith('.py') or fname.endswith('.py.card')):
        return jsonify({"error": "Only .py / .py.card files or .egg cartridges are supported"}), 400

    os.makedirs(AGENTS_PATH, exist_ok=True)
    safe_name = werkzeug.utils.secure_filename(fname)
    # Strip .card so the brainstem's *_agent.py glob auto-discovers it
    if safe_name.endswith('.py.card'):
        safe_name = safe_name[:-5]  # drop ".card" → "<x>.py"
    if not safe_name.endswith('_agent.py'):
        safe_name = safe_name[:-3] + '_agent.py'

    filepath = os.path.join(AGENTS_PATH, safe_name)
    with open(filepath, 'wb') as out:
        out.write(blob)

    try:
        load_agents()
    except Exception as e:
        return jsonify({"error": f"Uploaded but failed to load: {e}"}), 500

    # Card incantation: parse __card__ for a summon URL. If present,
    # fetch + unpack the egg so the card delivers the FULL TWIN, not
    # just the bare agent. RAR cards become twin-summon vectors.
    summon_result = None
    try:
        import ast
        src = blob.decode("utf-8", errors="replace")
        tree = ast.parse(src)
        card = None
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id == "__card__":
                        try:
                            card = ast.literal_eval(node.value)
                        except Exception:
                            card = None
                        break
        if isinstance(card, dict):
            summon_url = card.get("summon")
            expected_rappid = card.get("summon_rappid")
            if isinstance(summon_url, str) and summon_url.startswith(("http://", "https://")):
                import urllib.request as _ur
                from utils import egg as egg_mod
                try:
                    req = _ur.Request(summon_url, headers={"User-Agent": "rapp-brainstem-card-incant/1.0"})
                    with _ur.urlopen(req, timeout=30) as r:
                        egg_blob = r.read()
                    if egg_mod.is_egg_blob(egg_blob):
                        if expected_rappid:
                            info = egg_mod.inspect(egg_blob)
                            if info.get("ok") and info["manifest"].get("rappid") != expected_rappid:
                                summon_result = {"skipped": True, "reason": "rappid mismatch"}
                            else:
                                summon_result = egg_mod.unpack(egg_blob)
                        else:
                            summon_result = egg_mod.unpack(egg_blob)
                        # Reload agents after egg unpack so newly-restored ones go live
                        try:
                            load_agents()
                        except Exception:
                            pass
                except Exception as e:
                    summon_result = {"error": f"card summon fetch failed: {e}"}
    except Exception as e:
        print(f"[brainstem] card incantation parse skipped: {e}")

    resp = {
        "status": "ok",
        "kind": "agent" if not summon_result else "card-incantation",
        "message": f"Agent {safe_name} imported successfully.",
    }
    if summon_result:
        resp["summoned"] = summon_result
        resp["message"] = f"Card incantation: agent {safe_name} installed, twin egg summoned."
    return jsonify(resp)


# ── Egg cartridge export endpoints ──────────────────────────────────────
# Decoupled from the binder. The brainstem itself owns the cartridge spec
# (utils/egg.py) and exposes pack/unpack as core endpoints. The binder
# service may also call these for its own UI; the chat UI calls them
# directly. Three flavors:
#
#   GET /rapps/export/twin              → user's digital twin (agents + memory)
#   GET /rapps/export/snapshot          → full brainstem snapshot
#   GET /rapps/export/rapp/<id>         → one rapplication (legacy compat)
#
# All return application/zip with Content-Disposition for direct download.

@app.route("/rapps/export/twin", methods=["GET"])
def rapps_export_twin():
    from utils import egg as egg_mod
    twin_id = request.args.get("id", "twin")
    name = request.args.get("name", "Digital Twin")
    blob = egg_mod.pack_twin(twin_id, name=name)
    return blob, 200, {
        "Content-Type": "application/zip",
        "Content-Disposition": f'attachment; filename="{twin_id}.twin.egg"',
        "Content-Length": str(len(blob)),
    }


@app.route("/rapps/export/snapshot", methods=["GET"])
def rapps_export_snapshot():
    from utils import egg as egg_mod
    snap_id = request.args.get("id") or time.strftime("brainstem-%Y%m%d-%H%M%S", time.gmtime())
    name = request.args.get("name", "Brainstem Snapshot")
    blob = egg_mod.pack_snapshot(snap_id, name=name)
    return blob, 200, {
        "Content-Type": "application/zip",
        "Content-Disposition": f'attachment; filename="{snap_id}.snapshot.egg"',
        "Content-Length": str(len(blob)),
    }


@app.route("/rapps/export/rapp/<rapp_id>", methods=["GET"])
def rapps_export_rapp(rapp_id):
    from utils import egg as egg_mod
    # Pull metadata from binder.json if present, else best-effort defaults.
    binder_state_path = os.path.join(os.path.dirname(__file__), ".brainstem_data", "binder.json")
    entry = {}
    if os.path.exists(binder_state_path):
        try:
            with open(binder_state_path) as f:
                state = json.load(f)
            entry = next((e for e in state.get("installed", []) if e.get("id") == rapp_id), {}) or {}
        except Exception:
            pass
    blob = egg_mod.pack_rapplication(
        rapp_id=rapp_id,
        agent_filename=entry.get("agent_filename") or entry.get("filename") or f"{rapp_id}_agent.py",
        service_filename=entry.get("service_filename"),
        ui_filename=entry.get("ui_filename"),
        version=entry.get("version", "?"),
        name=entry.get("name", rapp_id),
    )
    return blob, 200, {
        "Content-Type": "application/zip",
        "Content-Disposition": f'attachment; filename="{rapp_id}.rapplication.egg"',
        "Content-Length": str(len(blob)),
    }


@app.route("/rapps/inspect", methods=["POST"])
def rapps_inspect():
    """Read just the manifest of an uploaded egg without unpacking it."""
    from utils import egg as egg_mod
    if 'file' not in request.files:
        return jsonify({"error": "no file uploaded"}), 400
    blob = request.files['file'].read()
    return jsonify(egg_mod.inspect(blob))


# ── Global twin summoning ───────────────────────────────────────────────
# A public egg lives at a public URL. Anyone who knows the URL can summon
# the twin / rapp / snapshot into their own local brainstem. Delivery
# vectors: clipboard paste, link share, QR scan (the brainstem index.html
# also accepts ?summon=<url> as a deep-link to trigger this flow).
#
# The brainstem is a game console; eggs are the cartridges; URLs +
# QR codes are how cartridges get distributed across the network.
# RAPPID inside the manifest is the universal identity that survives
# the trip.

@app.route("/eggs/summon", methods=["POST"])
def eggs_summon():
    """Fetch a .egg from a remote URL and unpack it locally.

    Body: {"url": "https://...egg", "expected_rappid": "..."  (optional)}

    The expected_rappid lets the caller pin a specific identity — useful
    for QR codes that publish a twin: the QR can encode both the URL
    and the expected RAPPID so a man-in-the-middle swap is detectable.
    """
    from utils import egg as egg_mod
    import urllib.request as _urlreq
    import urllib.error as _urlerr
    body = request.get_json(silent=True) or {}
    url = (body.get("url") or "").strip()
    expected_rappid = body.get("expected_rappid")
    if not url:
        return jsonify({"error": "url is required"}), 400
    if not (url.startswith("https://") or url.startswith("http://")):
        return jsonify({"error": "url must be http(s)"}), 400

    try:
        req = _urlreq.Request(url, headers={"User-Agent": "rapp-brainstem-egg-summon/1.0"})
        with _urlreq.urlopen(req, timeout=30) as r:
            blob = r.read()
    except (_urlerr.URLError, OSError) as e:
        return jsonify({"error": f"summon fetch failed: {e}"}), 502

    if not egg_mod.is_egg_blob(blob):
        return jsonify({"error": "URL did not return a valid egg"}), 400

    # Inspect first so we can verify expected_rappid before extracting
    info = egg_mod.inspect(blob)
    if not info.get("ok"):
        return jsonify({"error": info.get("error", "invalid manifest")}), 400
    manifest = info["manifest"]
    actual_rappid = manifest.get("rappid")
    if expected_rappid and actual_rappid != expected_rappid:
        return jsonify({
            "error": "rappid mismatch — refusing to unpack",
            "expected": expected_rappid,
            "actual": actual_rappid,
        }), 409

    # Unpack
    result = egg_mod.unpack(blob)
    if not result.get("ok"):
        return jsonify({"error": result.get("error", "unpack failed")}), 400

    # Reload agents so the summoned twin is live
    try:
        load_agents()
    except Exception as e:
        return jsonify({
            "status": "partial",
            "summoned": result,
            "warning": f"Egg unpacked but agents failed to reload: {e}",
        }), 200

    return jsonify({
        "status": "ok",
        "summoned": True,
        "type": result.get("type"),
        "rappid": actual_rappid,
        "id": result.get("id"),
        "name": result.get("name"),
        "files_restored": result.get("files_restored"),
        "manifest": manifest,
        "message": f"Summoned {result.get('type')} {result.get('name') or result.get('id')}.",
    })


@app.route("/identity", methods=["GET"])
def identity():
    """Return this brainstem's RAPPIDs (twin + per-rapp). Mints on first call."""
    from utils import egg as egg_mod
    twin_rappid = egg_mod.get_or_create_twin_rappid()
    ident = egg_mod._read_identity()
    return jsonify({
        "twin_rappid": twin_rappid,
        "rapps": ident.get("rapps", {}),
        "twin_incarnations": ident.get("twin_incarnations", 0),
    })


@app.route("/twin/manifest", methods=["GET"])
def twin_manifest():
    """Public-safe twin descriptor — what other twins / brainstems can know.

    Returns RAPPID, stream_id of THIS incarnation, frame log summary,
    incarnation count. NO state, NO chat history, NO secrets. Safe to
    expose if a brainstem is reachable on a network. Useful for twins
    discovering each other before deciding whether to collaborate.
    """
    from utils import egg as egg_mod
    from utils import frames as frames_mod
    twin_rappid = egg_mod.get_or_create_twin_rappid()
    ident = egg_mod._read_identity()
    return jsonify({
        "schema":            "twin-manifest/1.0",
        "twin_rappid":       twin_rappid,
        "stream_id":         frames_mod.get_or_create_stream_id(),
        "incarnations":      ident.get("twin_incarnations", 0),
        "frames":            frames_mod.stream_summary(),
        "version":           VERSION,
        # Capabilities surface — the "what can this twin do" affordances
        # other twins should know about. Just the agent name list — no
        # internals, no metadata that exposes state or strategy.
        "agent_names":       sorted(load_agents().keys()) if True else [],
        "rapps_installed":   list(ident.get("rapps", {}).keys()),
    })


@app.route("/frames/recent", methods=["GET"])
def frames_recent():
    """Diagnostic — read the last N frames from the local log."""
    from utils import frames as frames_mod
    try:
        limit = int(request.args.get("limit", "50"))
    except ValueError:
        limit = 50
    return jsonify({
        "stream": frames_mod.stream_summary(),
        "frames": frames_mod.read_recent(limit=limit),
    })


# ── Dreamcatcher seam: assimilate a divergent version egg ──────────────
# A "version" is a divergent local incarnation of the home twin: summoned
# to another brainstem (work laptop, friend's machine, edge device), it
# accumulated new memories / chats / agent installs while away. When the
# user returns home, those experiences need to be folded back into the
# core twin without trampling the home state.
#
# The proprietary Rappter dreamcatcher is the production merge engine —
# three-way merge with conflict resolution, CRDT-aware state, replay of
# unique experiences. This endpoint is the OPEN-SOURCE SEAM where
# dreamcatcher slots in. The basic behavior here is conservative: stage
# the version's contents under .brainstem_data/_versions/<entropy>/ so
# nothing in the home twin is overwritten. The user (or dreamcatcher)
# decides what to integrate.

@app.route("/eggs/assimilate", methods=["POST"])
def eggs_assimilate():
    from utils import egg as egg_mod
    import zipfile as _zf
    import urllib.request as _ur
    import urllib.error as _ue

    body = request.get_json(silent=True) or {}
    blob = None
    if body.get("egg_b64"):
        try:
            blob = base64.b64decode(body["egg_b64"])
        except Exception:
            return jsonify({"error": "invalid egg_b64"}), 400
    elif body.get("url"):
        url = (body["url"] or "").strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            return jsonify({"error": "url must be http(s)"}), 400
        try:
            req = _ur.Request(url, headers={"User-Agent": "rapp-brainstem-assimilate/1.0"})
            with _ur.urlopen(req, timeout=30) as r:
                blob = r.read()
        except (_ue.URLError, OSError) as e:
            return jsonify({"error": f"fetch failed: {e}"}), 502
    else:
        return jsonify({"error": "egg_b64 or url required"}), 400

    if not egg_mod.is_egg_blob(blob):
        return jsonify({"error": "not a valid egg"}), 400

    info = egg_mod.inspect(blob)
    if not info.get("ok"):
        return jsonify({"error": info["error"]}), 400
    incoming = info["manifest"]
    incoming_rappid = incoming.get("rappid") or "unknown"
    home_rappid = egg_mod.get_or_create_twin_rappid()

    parsed = egg_mod.parse_rappid(incoming_rappid)
    entropy = parsed["entropy"] if parsed else hashlib.sha1(incoming_rappid.encode()).hexdigest()[:16]
    stage_root = os.path.join(os.path.dirname(__file__), ".brainstem_data", "_versions", entropy)
    os.makedirs(stage_root, exist_ok=True)

    files_staged = 0
    with _zf.ZipFile(io.BytesIO(blob)) as z:
        for name in z.namelist():
            if name.endswith("/"):
                continue
            target = os.path.abspath(os.path.join(stage_root, name))
            if not target.startswith(os.path.abspath(stage_root) + os.sep):
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as fp:
                fp.write(z.read(name))
            files_staged += 1

    parent_rappid = (incoming.get("lineage") or {}).get("parent_rappid")
    if incoming_rappid == home_rappid:
        merge_kind = "same-twin"  # standard return-from-edge
    elif parent_rappid == home_rappid:
        merge_kind = "fork-back"  # forked twin merging into parent
    else:
        merge_kind = "cross-lineage"  # different twin entirely

    return jsonify({
        "ok": True,
        "staged_at": stage_root,
        "files_staged": files_staged,
        "source_rappid": incoming_rappid,
        "target_rappid": home_rappid,
        "merge_kind": merge_kind,
        "manifest": incoming,
        "next": (
            "Version staged. Use the Rappter dreamcatcher to merge into "
            "the home twin. The home twin's state is untouched; nothing "
            "was overwritten."
        ),
    })

@app.route("/health", methods=["GET"])
def health():
    agents = {}
    try:
        agents = load_agents()
    except Exception:
        pass
    soul_ok = os.path.exists(SOUL_PATH)

    # Lightweight auth check — just see if a GitHub token EXISTS.
    # Never do token exchange here; that happens lazily on first /chat call.
    github_token = get_github_token()

    # Check if we have a cached (valid) Copilot session (memory or disk)
    copilot_ok = False
    if _copilot_token_cache["token"] and time.time() < _copilot_token_cache["expires_at"] - 60:
        copilot_ok = True
    else:
        disk_cache = _load_copilot_cache()
        if disk_cache:
            copilot_ok = True

    if github_token:
        return jsonify({
            "status": "ok",
            "version": VERSION,
            "model":  MODEL,
            "voice_mode": VOICE_MODE,
            "twin_mode":  TWIN_MODE,
            "soul":   SOUL_PATH if soul_ok else "missing",
            "agents": list(agents.keys()),
            "copilot": "\u2713" if copilot_ok else "pending",
            "brainstem_dir": os.path.dirname(os.path.abspath(__file__)),
        })
    else:
        return jsonify({
            "status": "unauthenticated",
            "version": VERSION,
            "model":  MODEL,
            "soul":   SOUL_PATH if soul_ok else "missing",
            "agents": list(agents.keys()),
        })

@app.route("/debug/auth", methods=["GET"])
def debug_auth():
    """Debug endpoint — shows current auth state and tests token exchange."""
    token = get_github_token()
    token_data = _read_token_file()
    copilot_cache = _load_copilot_cache()

    result = {
        "github_token_exists": token is not None,
        "github_token_prefix": token[:10] + "..." if token else None,
        "github_token_length": len(token) if token else 0,
        "token_file_exists": os.path.exists(_token_file),
        "token_file_has_refresh": bool(token_data and token_data.get("refresh_token")),
        "copilot_cache_exists": copilot_cache is not None,
        "copilot_cache_expires_in": int(copilot_cache["expires_at"] - time.time()) if copilot_cache else None,
        "copilot_memory_cache": bool(_copilot_token_cache["token"]),
    }

    if token:
        try:
            resp = _exchange_github_for_copilot(token)
            result["exchange_http_status"] = resp.status_code
            result["exchange_ok"] = resp.ok
            if not resp.ok:
                try:
                    err = resp.json()
                    result["exchange_error_code"] = err.get("error") or err.get("message")
                except Exception:
                    result["exchange_error_code"] = "unparseable"
        except Exception as e:
            result["exchange_error"] = str(e)

    return jsonify(result)

# ── Diagnostics / Flight Recorder (book.json) ─────────────────────────────────

@app.route("/diagnostics", methods=["GET"])
def diagnostics():
    """Return the flight recorder log as JSON. Add ?tail=N for last N events."""
    tail = request.args.get("tail", type=int)
    with _flight_log_lock:
        events = list(_flight_log)
    if tail:
        events = events[-tail:]
    return jsonify({
        "version": VERSION,
        "model": MODEL,
        "uptime_events": len(events),
        "events": events,
    })

@app.route("/diagnostics/book.json", methods=["GET"])
def diagnostics_export():
    """Export full flight recorder as book.json — the brainstem's story."""
    _tlog_save()  # Flush to disk first
    with _flight_log_lock:
        events = list(_flight_log)

    # Build the book
    github_token = get_github_token()
    book = {
        "title": "RAPP Brainstem Flight Recorder",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "version": VERSION,
        "config": {
            "model": MODEL,
            "soul_path": SOUL_PATH,
            "agents_path": AGENTS_PATH,
            "port": PORT,
            "voice_mode": VOICE_MODE,
        },
        "auth_state": {
            "github_token_exists": github_token is not None,
            "github_token_prefix": github_token[:4] + "..." if github_token else None,
            "token_file_exists": os.path.exists(_token_file),
            "copilot_cache_valid": bool(_copilot_token_cache["token"] and time.time() < _copilot_token_cache["expires_at"] - 60),
            "pending_login": bool(_pending_login),
        },
        "agents_loaded": list(load_agents().keys()) if True else [],
        "events": events,
    }

    from flask import Response
    return Response(
        json.dumps(book, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=share-with-admin--this-file-tells-your-whole-story--they-can-help-you-now.json"},
    )

@app.route("/diagnostics/clear", methods=["POST"])
def diagnostics_clear():
    """Clear the flight recorder."""
    with _flight_log_lock:
        _flight_log.clear()
    _tlog_save()
    return jsonify({"status": "ok", "message": "Flight recorder cleared."})

@app.route("/diagnostics/report", methods=["POST"])
def diagnostics_report():
    """Create a GitHub issue with session diagnostics so admin can help."""
    _tlog("diagnostics.report_started")
    github_token = get_github_token()
    if not github_token:
        return jsonify({"error": "Not authenticated — sign in first to submit a report."}), 401

    data = request.get_json(force=True) or {}
    user_description = data.get("description", "").strip() or "_No description provided_"
    client_events = data.get("client_events", [])

    # Build the diagnostics snapshot
    _tlog_save()
    with _flight_log_lock:
        events = list(_flight_log)

    # Extract recent errors/warnings for summary
    err_events = [e for e in events if e.get("level") in ("error", "warn")][-10:]
    summary_lines = []
    for e in err_events:
        d = e.get("data", {})
        summary_lines.append(f"- `{e['ts']}` **{e['type']}** {json.dumps(d) if d else ''}")
    error_summary = "\n".join(summary_lines) if summary_lines else "_No errors or warnings recorded_"

    # Scrub sensitive fields from events before publishing
    _SCRUB_KEYS = {"user_code", "device_code", "session_id"}
    def _scrub_event(ev):
        ev = dict(ev)
        if ev.get("data"):
            ev["data"] = {k: v for k, v in ev["data"].items() if k not in _SCRUB_KEYS}
        return ev
    events = [_scrub_event(e) for e in events]
    client_events = [_scrub_event(e) for e in client_events]

    # Build compact book (no secrets, capped size)
    book = {
        "version": VERSION,
        "model": MODEL,
        "auth_state": {
            "github_token_exists": True,
            "token_prefix": github_token[:4] + "...",
            "copilot_cache_valid": bool(_copilot_token_cache["token"] and time.time() < _copilot_token_cache["expires_at"] - 60),
            "pending_login": bool(_pending_login),
        },
        "agents_loaded": list(load_agents().keys()),
        "server_events": events[-50:],  # Last 50 server events
        "client_events": client_events[-50:] if client_events else [],
    }
    book_json = json.dumps(book, indent=2)
    # GitHub issues have a body limit ~65536 chars; trim if needed
    if len(book_json) > 40000:
        book["server_events"] = events[-20:]
        book["client_events"] = client_events[-20:] if client_events else []
        book_json = json.dumps(book, indent=2)

    issue_body = (
        f"## User Report\n\n{user_description}\n\n"
        f"## Environment\n\n"
        f"- **Version:** {VERSION}\n"
        f"- **Model:** {MODEL}\n"
        f"- **Agents:** {', '.join(book['agents_loaded']) or 'none'}\n\n"
        f"## Recent Warnings & Errors\n\n{error_summary}\n\n"
        f"## Session Diagnostics\n\n"
        f"<details><summary>book.json (click to expand)</summary>\n\n"
        f"```json\n{book_json}\n```\n\n</details>"
    )

    try:
        resp = requests.post(
            "https://api.github.com/repos/kody-w/rapp-installer/issues",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "title": f"🆘 Help request — v{VERSION}",
                "body": issue_body,
                "labels": [],
            },
            timeout=15,
        )
        if resp.status_code in (201, 200):
            issue_data = resp.json()
            issue_url = issue_data.get("html_url", "")
            _tlog("diagnostics.report_created", {"issue_url": issue_url})
            return jsonify({"status": "ok", "issue_url": issue_url})

        # ghu_ tokens from device code don't have repo scope — try gh CLI
        if resp.status_code in (403, 404):
            _tlog("diagnostics.report_api_403_trying_cli", level="warn")
            try:
                result = subprocess.run(
                    ["gh", "issue", "create",
                     "--repo", "kody-w/rapp-installer",
                     "--title", f"🆘 Help request — v{VERSION}",
                     "--body", issue_body],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0:
                    issue_url = result.stdout.strip()
                    _tlog("diagnostics.report_created_via_cli", {"issue_url": issue_url})
                    return jsonify({"status": "ok", "issue_url": issue_url})
                _tlog("diagnostics.report_cli_failed", {"stderr": result.stderr[:200]}, level="error")
            except Exception as cli_err:
                _tlog("diagnostics.report_cli_error", {"error": str(cli_err)}, level="error")

        err = resp.text[:300]
        _tlog("diagnostics.report_failed", {"status": resp.status_code, "error": err}, level="error")
        return jsonify({"error": f"GitHub API returned {resp.status_code}: {err}"}), resp.status_code
    except Exception as e:
        _tlog("diagnostics.report_error", {"error": str(e)}, level="error")
        return jsonify({"error": str(e)}), 500

# ── Services (drop-in HTTP routes via services/*_service.py) ─────────────────

def load_services():
    """Discover services from SERVICES_PATH. Each service module exposes:
       name  — str, URL namespace (e.g. "swarms" → /api/swarms/...)
       handle(method, path, body) — returns (dict, status_code)
    Reloaded every request, same as agents.
    """
    svcs = {}
    if not os.path.isdir(SERVICES_PATH):
        return svcs
    for filepath in glob.glob(os.path.join(SERVICES_PATH, "*_service.py")):
        mod_name = os.path.splitext(os.path.basename(filepath))[0]
        try:
            spec = importlib.util.spec_from_file_location(mod_name, filepath)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            svc_name = getattr(mod, "name", mod_name.replace("_service", ""))
            if hasattr(mod, "handle"):
                svcs[svc_name] = mod
        except Exception as e:
            print(f"[brainstem] Service load error ({mod_name}): {e}")
    return svcs

@app.route("/api/<service>", methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/api/<service>/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def service_dispatch(service, path=""):
    svcs = load_services()
    svc = svcs.get(service)
    if not svc:
        return jsonify({"error": f"service '{service}' not found"}), 404
    try:
        body = request.get_json(silent=True) or {}
        result = svc.handle(request.method, path, body)
        # Services may return either:
        #   (dict, status)                       — JSON response (default)
        #   (bytes, status, headers_dict)        — binary file response
        # The 3-tuple form lets a service emit a download (e.g. .egg cartridge)
        # without bypassing the service-discovery contract.
        if isinstance(result, tuple) and len(result) == 3:
            blob, status, headers = result
            if isinstance(blob, (bytes, bytearray)):
                return bytes(blob), status, headers
            # Fall through if the 3rd element wasn't bytes — treat as JSON
            return jsonify(blob), status, headers
        result, status = result
        return jsonify(result), status
    except Exception as e:
        print(f"[brainstem] Service error ({service}/{path}): {e}")
        return jsonify({"error": str(e)}), 500

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _tlog_load()  # Restore previous flight log
    _tlog("server.starting", {"version": VERSION, "model": MODEL, "port": PORT})
    print(f"\n🧠 RAPP Brainstem v{VERSION} starting on http://localhost:{PORT}")
    print(f"   Soul:   {SOUL_PATH}")
    print(f"   Agents: {AGENTS_PATH}")
    print(f"   Model:  {MODEL}")
    print(f"   Voice:  {'on' if VOICE_MODE else 'off'} (POST /voice/toggle to change)")
    print(f"   Twin:   {'on' if TWIN_MODE else 'off'} (POST /twin/toggle to change)")
    print(f"   Auth:   GitHub Copilot API (via gh CLI)\n")
    load_soul()
    agents = load_agents()
    svcs = load_services()
    if svcs:
        print(f"[brainstem] {len(svcs)} service(s) ready: {', '.join(svcs.keys())}")
    _tlog("server.agents_loaded", {"agents": list(agents.keys()), "services": list(svcs.keys())})
    _load_pending_login()  # Resume any in-progress device code login
    _tlog("server.ready", {"url": f"http://localhost:{PORT}"})
    # First frame of the flipbook — twin awakens with the agents loaded.
    # No twin frame at boot — the LLM hasn't said anything yet, so
    # there's no twin to render. First frame will appear when the
    # first chat round produces a real <frame> in |||TWIN|||.
    app.run(host="0.0.0.0", port=PORT, debug=False)