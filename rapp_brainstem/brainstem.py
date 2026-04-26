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
SERVICES_PATH = os.getenv("SERVICES_PATH", os.path.join(os.path.dirname(__file__), "services"))
MODEL        = os.getenv("GITHUB_MODEL", "gpt-4o")
PORT        = int(os.getenv("PORT", 7071))
# Voice and Twin default ON — the brainstem's terminal twin (see
# _twin_emit below) is the operator's window into the agent's "world".
# Watching it pace and react across calls makes non-tech users care
# about what's happening; turning it off makes the terminal feel dead.
# Operators who want pure telemetry can set TWIN_MODE=false.
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
RAPPSTORE_URL = os.getenv("RAPPSTORE_URL", "https://raw.githubusercontent.com/kody-w/RAPP/main/rapp_store/index.json")

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
# Each LLM round emits a small ASCII portrait of the digital twin between
# the [brainstem] telemetry lines. Static per-call (no animation inside a
# frame), but state persists across calls — the twin paces left↔right
# inside its bordered "cage" with a frame counter, so as the chat goes on
# you see a continuous flipbook of the twin reacting to what's happening.
# Like a Tamagotchi for the agent.
#
# Why bother: telemetry alone is text wallpaper. A bug-cage frame with a
# face in it gives non-tech users a visual anchor for "the agent is
# thinking now / working now / done now" — gateway drug to caring about
# the technical lines underneath. Operators who want pure telemetry set
# TWIN_MODE=false.

import random as _twin_random

_TWIN_FACES = {
    "awake":    [r"|^_^|", r"(o.o)", r"|*.*|", r"(O.O)", r"[^v^]"],
    "thinking": [r"|?_?|", r"(@.@)", r"|...|", r"(o.O)", r"|<.>|"],
    "working":  [r"|>_<|", r"(>.<)", r"|^.^|", r"(=_=)", r"[*-*]"],
    "done":     [r"|^_^|", r"(:^))", r"|+_+|", r"(^o^)", r"[\o/]"],
    "puzzled":  [r"|?.?|", r"(0.0)", r"|x.x|", r"(O_o)", r"[?_?]"],
    "error":    [r"|x_x|", r"(T_T)", r"|>.<|", r"(@_@)", r"[X_X]"],
}
_TWIN_COLORS = {
    "awake":    "\033[36m",  # cyan
    "thinking": "\033[35m",  # magenta
    "working":  "\033[33m",  # yellow
    "done":     "\033[32m",  # green
    "puzzled":  "\033[33m",  # yellow
    "error":    "\033[31m",  # red
}
_TWIN_RESET = "\033[0m"
_TWIN_DIM = "\033[2m"

# Persistent state — pacing position + direction + frame count. Builds
# the flipbook continuity: pos drifts left/right per call, bouncing off
# the walls so the twin never escapes the cage. Mood + face are fresh
# per call but the position carries.
_twin_state = {"pos": 0, "dir": 1, "frame": 0}
_TWIN_CAGE_W = 8  # 0..7 horizontal positions

def _twin_emit(message="", mood="working"):
    """Render one frame of the twin in its cage."""
    if not TWIN_MODE:
        return
    _twin_state["frame"] += 1
    # Bounce position off the cage walls so the twin paces back and
    # forth instead of stacking against an edge or wrapping unpredictably.
    _twin_state["pos"] += _twin_state["dir"]
    if _twin_state["pos"] >= _TWIN_CAGE_W - 1:
        _twin_state["dir"] = -1
    elif _twin_state["pos"] <= 0:
        _twin_state["dir"] = 1
    pos = max(0, min(_TWIN_CAGE_W - 1, _twin_state["pos"]))

    pool = _TWIN_FACES.get(mood, _TWIN_FACES["working"])
    face = _twin_random.choice(pool)
    msg = (message or "").strip().replace("\n", " ")[:48]

    width = 55  # internal width of the cage
    indent_face = (" " * (pos * 6)) + face
    line_face = indent_face.ljust(width)[:width]
    line_msg = ("  " + msg).ljust(width)[:width]

    label = f" twin · {mood} · #{_twin_state['frame']} "
    label_pad = label + ("─" * max(0, width - len(label)))
    bottom = "─" * width

    use_color = sys.stdout.isatty()
    col = _TWIN_COLORS.get(mood, "") if use_color else ""
    rst = _TWIN_RESET if use_color else ""
    print(f"  {col}╭{label_pad}╮{rst}")
    print(f"  {col}│{rst}{line_face}{col}│{rst}")
    print(f"  {col}│{rst}{line_msg}{col}│{rst}")
    print(f"  {col}╰{bottom}╯{rst}")
    sys.stdout.flush()


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
    # Twin frame: thinking. Try to surface what's actually being thought
    # about — last user message in the conversation. Falls back to a
    # mood-only frame if we can't derive a snippet.
    _twin_hint = ""
    try:
        for _m in reversed(messages or []):
            if _m.get("role") == "user":
                _twin_hint = (_m.get("content") or "").strip().split("\n")[0][:40]
                break
    except Exception:
        pass
    _twin_emit(f"thinking · {_twin_hint}" if _twin_hint else "thinking…", "thinking")

    resp = requests.post(url, headers=headers, json=body, timeout=60)
    if resp.status_code != 200:
        error_detail = resp.text[:500] if resp.text else "No details"
        _tlog("api.error", {"model": MODEL, "status": resp.status_code, "detail": error_detail[:300]}, level="error")
        print(f"[brainstem] API error {resp.status_code} with model '{MODEL}': {error_detail}")
        _twin_emit(f"oops · HTTP {resp.status_code}", "error")
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
        _twin_emit(f"calling · {', '.join(names)[:36]}", "working")
    else:
        # Plain text response — twin "speaks" a brief excerpt of what
        # it just said, if anything came back. Empty response → puzzled.
        _content = (msg.get("content") or "").strip()
        if _content:
            _excerpt = _content.split("\n")[0][:42]
            _twin_emit(f"speaking · {_excerpt}", "done")
        else:
            _twin_emit("hmm · empty response", "puzzled")

    return result

# ── Agent execution ───────────────────────────────────────────────────────────


def run_tool_calls(tool_calls, agents, session_id=None, user_guid=None):
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
        if agent:
            try:
                result = agent.perform(**args)
                logs.append(f"[{fn_name}] {result}")
            except TypeError as e:
                # Agent's perform() doesn't accept user_guid kwarg — drop it and retry.
                # Backwards compat for older agents that haven't adopted the threaded identity.
                if "user_guid" in args and "user_guid" in str(e):
                    args.pop("user_guid", None)
                    try:
                        result = agent.perform(**args)
                        logs.append(f"[{fn_name}] {result}")
                    except Exception as e2:
                        result = f"Error: {e2}"
                        logs.append(f"[{fn_name}] ERROR: {e2}")
                else:
                    result = f"Error: {e}"
                    logs.append(f"[{fn_name}] ERROR: {e}")
            except Exception as e:
                result = f"Error: {e}"
                logs.append(f"[{fn_name}] ERROR: {e}")
        else:
            result = f"Agent '{fn_name}' not found."
            logs.append(result)

        results.append({
            "tool_call_id": tc["id"],
            "role": "tool",
            "name": fn_name,
            "content": str(result)
        })
    return results, logs

# ── /chat endpoint ────────────────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    user_input = data.get("user_input", "").strip()
    history    = data.get("conversation_history", [])
    session_id = data.get("session_id") or str(uuid.uuid4())
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

        system_content = soul + extra_context
        if VOICE_MODE:
            system_content += "\n\nIMPORTANT: End every response with |||VOICE||| followed by a concise, conversational version of your answer suitable for text-to-speech. Keep the voice version under 2-3 sentences. The part before |||VOICE||| should be the full formatted response."
        if TWIN_MODE:
            system_content += (
                "\n\nTWIN: After the VOICE section (or after the main reply if VOICE is off), "
                "append |||TWIN||| followed by the user's digital twin reacting to this turn. "
                "Speak FIRST-PERSON as the user, TO the user — one or two short observations, "
                "hints, risks, or questions about what was just said. Short is a feature. "
                "Silent is allowed — leave empty if there's nothing worth saying. "
                "Do NOT re-answer the question. The twin comments ON the turn, it does not "
                "replace any part of it. Bold tags like **Hint:** / **Risk:** / **Question:** "
                "work well. Inside |||TWIN|||, you may also emit these optional tags (all are "
                "stripped before the user sees the panel): "
                "<probe id=\"t-<uniq>\" kind=\"<slug>\" subject=\"...\" confidence=\"0.0-1.0\"/> "
                "tags a claim you could be right or wrong about. "
                "<calibration id=\"<probe id>\" outcome=\"validated|contradicted|silent\" note=\"...\"/> "
                "judges a prior probe against what the user just did. "
                "<telemetry>one fact per line</telemetry> is server-log-only debug signal. "
                "<action kind=\"send|prompt|open|toggle|highlight|rapp\" target=\"...\" label=\"...\">body</action> "
                "offers the user a one-click UI favor (send text, prefill input, open a panel, "
                "toggle a feature like voice/cards/pills/hand-mode, highlight a loaded card, "
                "or invoke a rapplication tool on their behalf via kind=\"rapp\")."
            )

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
        result = {
            "response": reply,
            "assistant_response": reply,
            "session_id": session_id,
            "user_guid": user_guid,
            "agent_logs": "\n".join(all_logs),
            "voice_mode": VOICE_MODE,
            "twin_mode":  TWIN_MODE,
        }

        # Three-way split: main |||VOICE||| voice |||TWIN||| twin.
        # Both delimiters optional. Left-to-right so twin never
        # pollutes voice and voice never pollutes main.
        # Per Article II, each slot's content may be wrapped in matching
        # XML tags (<main>, <voice>, <twin>) — the wrapper is the LLM's
        # explicit boundary marker. We strip the outer wrapper here so
        # consumers receive the bare content. Wrapping is optional input;
        # legacy emitters without it parse the same way.
        def _unwrap(text, tag):
            t = text.strip()
            open_tag = "<" + tag + ">"
            close_tag = "</" + tag + ">"
            if t.startswith(open_tag) and t.endswith(close_tag):
                return t[len(open_tag):-len(close_tag)].strip()
            return t

        remainder = reply
        if "|||VOICE|||" in remainder:
            main, _, remainder = remainder.partition("|||VOICE|||")
            result["response"] = _unwrap(main, "main")
            result["assistant_response"] = result["response"]
        if "|||TWIN|||" in remainder:
            voice_or_main, _, twin_text = remainder.partition("|||TWIN|||")
            if VOICE_MODE and "|||VOICE|||" in reply:
                result["voice_response"] = _unwrap(voice_or_main, "voice")
            elif "|||VOICE|||" not in reply:
                # No VOICE delimiter — the part before |||TWIN||| is the
                # main reply. Without this branch, response/assistant_response
                # would still contain the unsplit reply (with |||TWIN||| and
                # the twin text embedded), which is wrong for programmatic
                # clients reading those fields.
                result["response"] = _unwrap(voice_or_main, "main")
                result["assistant_response"] = result["response"]
            result["twin_response"] = _unwrap(twin_text, "twin") if TWIN_MODE else ""
        elif VOICE_MODE and "|||VOICE|||" in reply:
            result["voice_response"] = _unwrap(remainder, "voice")

        # If the response had no slot delimiters at all but the LLM still
        # wrapped the whole reply in <main>...</main>, unwrap that too.
        if "|||VOICE|||" not in reply and "|||TWIN|||" not in reply:
            unwrapped = _unwrap(reply, "main")
            if unwrapped != reply.strip():
                result["response"] = unwrapped
                result["assistant_response"] = unwrapped

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
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"), filename)

# Convenience routes for the named UI pages in web/ — so /manage works
# (not just /web/manage.html). The chat UI links to these clean paths.
@app.route("/manage", methods=["GET"])
def manage_page():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"), "manage.html")

@app.route("/binder", methods=["GET"])
@app.route("/binder.html", methods=["GET"])
def binder_page():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"), "binder.html")

@app.route("/rapplications", methods=["GET"])
def rapplications_page():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"), "rapplications.html")

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
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"), "rapp.js")

@app.route("/manifest.webmanifest", methods=["GET"])
def manifest_webmanifest():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"), "manifest.webmanifest")

@app.route("/icon-192.svg", methods=["GET"])
def icon_192():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"), "icon-192.svg")

@app.route("/icon-512.svg", methods=["GET"])
def icon_512():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"), "icon-512.svg")

@app.route("/sw.js", methods=["GET"])
def service_worker():
    return send_from_directory(os.path.join(os.path.dirname(os.path.abspath(__file__)), "web"), "sw.js")

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
    """Import an agent .py file via drag & drop."""
    import werkzeug.utils
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files['file']
    if f.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not f.filename.endswith('.py'):
        return jsonify({"error": "Only .py files are supported"}), 400
    
    os.makedirs(AGENTS_PATH, exist_ok=True)
    safe_name = werkzeug.utils.secure_filename(f.filename)
    # Ensure it matches the glob pattern *_agent.py
    if not safe_name.endswith('_agent.py'):
        safe_name = safe_name[:-3] + '_agent.py'
        
    filepath = os.path.join(AGENTS_PATH, safe_name)
    f.save(filepath)
    
    # Reload agents to include the new one
    try:
        load_agents()
    except Exception as e:
        return jsonify({"error": f"Uploaded but failed to load: {e}"}), 500
        
    return jsonify({"status": "ok", "message": f"Agent {safe_name} imported successfully."})

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
    _twin_emit(f"awake · {len(agents)} agents · listening on :{PORT}", "awake")
    app.run(host="0.0.0.0", port=PORT, debug=False)