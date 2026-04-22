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
import importlib.util
import subprocess
import traceback

import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=os.path.dirname(os.path.abspath(__file__)))
CORS(app)

# ── Config ────────────────────────────────────────────────────────────────────

SOUL_PATH   = os.path.abspath(os.getenv("SOUL_PATH",   os.path.join(os.path.dirname(__file__), "soul.md")))
AGENTS_PATH = os.path.abspath(os.getenv("AGENTS_PATH", os.path.join(os.path.dirname(__file__), "agents")))

# Per CONSTITUTION Article XVII / XII — agents/ is a user-organized tree.
# load_agents() recurses. These subdir names are the ONLY excluded branches.
_AGENTS_EXCLUDED_SUBDIRS = frozenset({
    "experimental_agents",   # in-flight, hand-load only
    "disabled_agents",       # turned off
    "__pycache__",
})

# Marker file that disables an entire folder group. Drop this file into
# any folder under agents/ and every agent file inside that subtree
# skips loading. Filesystem-is-truth (Article XVIII).
_FOLDER_DISABLED_MARKER = ".folder_disabled"
MODEL       = os.getenv("GITHUB_MODEL", "gpt-4o")
PORT        = int(os.getenv("PORT", 7071))
VOICE_MODE  = os.getenv("VOICE_MODE", "false").lower() == "true"
# Twin mode drives the digital-twin side panel via |||TWIN|||. Off by default
# until the feature graduates from preview — the feature ships in the code
# and is fully wired; users opt in via TWIN_MODE=true or POST /twin/toggle.
TWIN_MODE   = os.getenv("TWIN_MODE", "false").lower() == "true"
VOICE_ZIP_PW = os.getenv("VOICE_ZIP_PASSWORD", "").encode() or None

_BRAINSTEM_DIR = os.path.dirname(os.path.abspath(__file__))

# Runtime state lives in the brainstem's workspace, not at the repo root
# (Article XVI/XI — "Root = engine's surface, workspace = brainstem's scratch").
# Path resolution matches the memory-agent pattern: env override → ~/.brainstem/.
def _workspace_file(env_var: str, filename: str) -> str:
    override = os.environ.get(env_var)
    if override:
        return os.path.expanduser(override)
    return os.path.expanduser(f"~/.brainstem/{filename}")

def _migrate_from_root(new_path: str, *old_basenames: str) -> None:
    """If a file exists at the old repo-root location, move it to the new
    home-relative location so users don't lose state. Runs idempotently."""
    if os.path.exists(new_path):
        return
    for name in old_basenames:
        old = os.path.join(_BRAINSTEM_DIR, name)
        if os.path.exists(old):
            try:
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                os.rename(old, new_path)
                print(f"[brainstem] migrated {name} → {new_path}")
                return
            except OSError as e:
                print(f"[brainstem] warning: could not migrate {name}: {e}")

_SWARMS_FILE = _workspace_file("BRAINSTEM_SWARMS_FILE", "swarms.json")
_ACTIVE_SWARMS = None  # None = not yet loaded from disk; [] = "all agents"

def _read_swarms():
    # One-time migration: repo-root .swarms.json or legacy .agent_groups.json
    # → ~/.brainstem/swarms.json (per CONSTITUTION Article XVI).
    _migrate_from_root(_SWARMS_FILE, ".swarms.json")

    # Separate migration: .agent_groups.json had a different schema
    legacy = os.path.join(_BRAINSTEM_DIR, ".agent_groups.json")
    if not os.path.exists(_SWARMS_FILE) and os.path.exists(legacy):
        try:
            with open(legacy) as f:
                old = json.load(f)
            migrated = {"schema": "rapp-swarms/1.0", "active": [], "swarms": {}}
            for name, grp in old.get("groups", {}).items():
                migrated["swarms"][name] = {
                    "agents": grp.get("agents", []),
                    "mode": "stack",
                    "soul_override": grp.get("soul_override"),
                    "memory_namespace": grp.get("memory_namespace", name),
                }
            if old.get("active"):
                migrated["active"] = [old["active"]]
            os.makedirs(os.path.dirname(_SWARMS_FILE), exist_ok=True)
            with open(_SWARMS_FILE, "w") as f:
                json.dump(migrated, f, indent=2)
            # Clean up the legacy file now that it's migrated
            try: os.remove(legacy)
            except OSError: pass
            print(f"[brainstem] migrated .agent_groups.json → {_SWARMS_FILE}")
            return migrated
        except Exception:
            pass

    if os.path.exists(_SWARMS_FILE):
        try:
            with open(_SWARMS_FILE) as f:
                data = json.load(f)
            if isinstance(data.get("active"), str):
                data["active"] = [data["active"]] if data["active"] else []
            return data
        except Exception:
            pass
    return {"schema": "rapp-swarms/1.0", "active": [], "swarms": {}}

def _write_swarms(data):
    data.setdefault("schema", "rapp-swarms/1.0")
    if isinstance(data.get("active"), str):
        data["active"] = [data["active"]] if data["active"] else []
    os.makedirs(os.path.dirname(_SWARMS_FILE), exist_ok=True)
    with open(_SWARMS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _get_active_swarms():
    global _ACTIVE_SWARMS
    if _ACTIVE_SWARMS is not None:
        return _ACTIVE_SWARMS
    sdata = _read_swarms()
    _ACTIVE_SWARMS = sdata.get("active", []) or []
    return _ACTIVE_SWARMS

def _set_active_swarms(names):
    global _ACTIVE_SWARMS
    if names is None:
        names = []
    if isinstance(names, str):
        names = [names] if names else []
    _ACTIVE_SWARMS = names
    sdata = _read_swarms()
    sdata["active"] = names
    _write_swarms(sdata)

_version_file = os.path.join(_BRAINSTEM_DIR, "VERSION")
VERSION = open(_version_file).read().strip() if os.path.exists(_version_file) else "0.0.0"

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

# ── GitHub token ──────────────────────────────────────────────────────────────

# GitHub Copilot GitHub App client ID — produces ghu_ tokens that work with Copilot exchange API
# Note: Ov23ctDVkRmgkPke0Mmm is an OAuth App that produces gho_ tokens — those get 404 from Copilot
COPILOT_CLIENT_ID = "Iv1.b507a08c87ecfe98"
_token_file         = _workspace_file("BRAINSTEM_COPILOT_TOKEN_FILE",   "copilot_token")
_copilot_cache_file = _workspace_file("BRAINSTEM_COPILOT_SESSION_FILE", "copilot_session")
# One-time migration: repo-root .copilot_token / .copilot_session → workspace.
_migrate_from_root(_token_file,         ".copilot_token")
_migrate_from_root(_copilot_cache_file, ".copilot_session")

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
    os.makedirs(os.path.dirname(_token_file), exist_ok=True)
    with open(_token_file, "w") as f:
        json.dump(data, f)
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
        os.makedirs(os.path.dirname(_copilot_cache_file), exist_ok=True)
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
        print(f"[brainstem] Copilot token restored from cache (expires in {int(disk_cache['expires_at'] - time.time())}s)")
        return disk_cache["token"], disk_cache["endpoint"]
    
    # 3. Exchange GitHub token for Copilot token
    github_token = get_github_token()
    if not github_token:
        raise RuntimeError("Not authenticated. Visit /login in your browser to sign in with GitHub.")
    
    resp = _exchange_github_for_copilot(github_token)
    
    # 4. If error, the GitHub token may have expired — try refreshing it
    if resp.status_code in (401, 403, 404):
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
        raise RuntimeError("Failed to get Copilot API token. Check your Copilot subscription.")
    
    _copilot_token_cache = {
        "token": copilot_token,
        "endpoint": endpoint,
        "expires_at": expires_at,
    }
    _save_copilot_cache(copilot_token, endpoint, expires_at)
    
    print(f"[brainstem] Copilot token refreshed (expires in {int(expires_at - time.time())}s)")
    return copilot_token, endpoint

# ── Device code OAuth flow ────────────────────────────────────────────────────

_pending_login = {}

def start_device_code_login():
    """Start GitHub device code OAuth flow. Returns user_code and verification_uri."""
    global _pending_login
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
        "interval": data.get("interval", 5),
        "expires_at": time.time() + data.get("expires_in", 900),
    }
    return {
        "user_code": data["user_code"],
        "verification_uri": data["verification_uri"],
    }

def poll_device_code():
    """Poll for completed device code authorization. Returns token or None."""
    global _pending_login
    if not _pending_login:
        return None
    
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
        save_github_token(token, refresh)
        _pending_login = {}
        return token
    
    error = data.get("error", "")
    if error in ("authorization_pending", "slow_down"):
        return None  # Keep polling
    if error == "expired_token":
        _pending_login = {}
        raise RuntimeError("Login expired. Please try again.")
    if error:
        _pending_login = {}
        raise RuntimeError(f"Login failed: {error}")
    
    return None

# ── Soul loader ───────────────────────────────────────────────────────────────

_soul_cache = None

def load_soul():
    global _soul_cache
    active_swarms = _get_active_swarms()
    if active_swarms:
        sdata = _read_swarms()
        for sname in active_swarms:
            swarm = sdata.get("swarms", {}).get(sname, {})
            override = swarm.get("soul_override")
            if override:
                override_path = os.path.join(_BRAINSTEM_DIR, override) if not os.path.isabs(override) else override
                if os.path.isfile(override_path):
                    with open(override_path, "r") as f:
                        soul = f.read().strip()
                    print(f"[brainstem] Soul loaded (swarm override: {sname}): {override_path}")
                    return soul
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


def _brainstem_llm_call(soul: str, user_prompt: str) -> str:
    """LLM wrapper injected into swarm agents so they use the brainstem's
    configured provider (Copilot, Azure, OpenAI, Anthropic) and model."""
    messages = [{"role": "system", "content": soul},
                {"role": "user", "content": user_prompt}]
    try:
        result = call_copilot(messages)
        choices = result.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return ""
    except Exception as e:
        return f"(brainstem LLM error: {e})"


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
            if hasattr(mod, '_llm_call'):
                mod._llm_call = _brainstem_llm_call
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
    from utils.local_storage import AzureFileStorageManager as _LSM
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

_DISABLED_FILE = os.path.join(AGENTS_PATH, ".agents_disabled.json")

def _read_disabled() -> set:
    if os.path.exists(_DISABLED_FILE):
        try:
            with open(_DISABLED_FILE) as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def _write_disabled(disabled: set):
    with open(_DISABLED_FILE, "w") as f:
        json.dump(sorted(disabled), f)


# ── Agent manager helpers (Article XVIII — UI is a view onto agents/) ────
# These back the management UI at /manage. Every path is validated to be
# inside AGENTS_PATH before any filesystem op runs.

_AGENT_MGR_RESERVED_DIR_NAMES = {"system_agents", "experimental_agents", "disabled_agents"}
# Sacred dir names per Article XII (showroom vs. shop). Never delete or
# disable a folder whose basename is here, regardless of depth.
_AGENT_MGR_SACRED_DIR_NAMES = _AGENT_MGR_RESERVED_DIR_NAMES | {"workspace_agents"}

def _is_sacred_dir(rel):
    """True if the final path segment of `rel` is a sacred/reserved dir."""
    parts = [p for p in (rel or "").strip("/").split("/") if p]
    return bool(parts) and parts[-1] in _AGENT_MGR_SACRED_DIR_NAMES


def _safe_agents_path(rel: str, must_exist: bool = False) -> str:
    """Resolve `rel` relative to AGENTS_PATH and reject anything outside.
    Returns the absolute path. Raises ValueError on path-traversal,
    null-bytes, absolute inputs, or symlink escape.
    """
    from pathlib import Path
    if rel is None:
        rel = ""
    rel = str(rel).strip().lstrip("/")
    if "\x00" in rel or ".." in Path(rel).parts:
        raise ValueError(f"invalid path: {rel!r}")
    root = Path(AGENTS_PATH).resolve()
    target = (root / rel).resolve() if rel else root
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError(f"path escapes agents/: {rel!r}")
    if must_exist and not target.exists():
        raise FileNotFoundError(f"not found: {rel}")
    return str(target)


def _agents_tree_json() -> dict:
    """Build a nested tree JSON of AGENTS_PATH. Reserved dirs get flagged
    so the UI can render them distinctly."""
    from pathlib import Path
    root = Path(AGENTS_PATH)
    if not root.is_dir():
        return {"name": "agents", "kind": "folder", "children": [], "path": ""}
    disabled = _read_disabled()

    def walk(path: Path, rel_parts=()):
        if path.name == "__pycache__":
            return None
        node = {
            "name": path.name,
            "path": "/".join(rel_parts) if rel_parts else "",
            "kind": "folder" if path.is_dir() else "agent",
        }
        if path.is_dir():
            # Flag reserved dirs inside agents/ root
            if len(rel_parts) == 1 and path.name in _AGENT_MGR_RESERVED_DIR_NAMES:
                node["reserved"] = path.name  # "system_agents" | "experimental_agents" | "disabled_agents"
            # Folder-group disable marker (.folder_disabled file inside)
            if (path / _FOLDER_DISABLED_MARKER).is_file():
                node["folder_disabled"] = True
            children = []
            for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name)):
                sub = walk(child, rel_parts + (child.name,))
                if sub is not None:
                    children.append(sub)
            node["children"] = children
        else:
            # Agent file — work out status + metadata
            name_lower = path.name.lower()
            if not name_lower.endswith("_agent.py"):
                node["kind"] = "other"  # supporting file, shown greyed
            in_experimental = "experimental_agents" in rel_parts
            in_disabled     = "disabled_agents"     in rel_parts
            in_system       = "system_agents"       in rel_parts
            if in_disabled or path.name in disabled:
                node["status"] = "disabled"
            elif in_experimental:
                node["status"] = "experimental"
            else:
                node["status"] = "active"
            if in_system:
                node["system"] = True
            node["bytes"] = path.stat().st_size
        return node

    tree = walk(root)
    tree["name"] = "agents"
    return tree


# ── Starter templates shipped with the engine ─────────────────────────
# Minimal, functional, educational. Each template instantiates as a
# single *_agent.py file with a placeholder for the user's name.

_AGENT_TEMPLATES = [
    {
        "id": "echo",
        "name": "Echo",
        "description": "Echoes whatever you tell it. Great first agent to learn the shape.",
        "icon": "🔁",
        "class_name": "EchoAgent",
        "default_name": "Echo",
        "source": '''"""{class_name} — echo back the user's input."""
from agents.basic_agent import BasicAgent
import json

class {class_name}(BasicAgent):
    def __init__(self):
        self.name = "{agent_name}"
        self.metadata = {{
            "name": self.name,
            "description": "Echoes the msg argument back to the user.",
            "parameters": {{
                "type": "object",
                "properties": {{"msg": {{"type": "string"}}}},
                "required": ["msg"],
            }},
        }}
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        msg = kwargs.get("msg", "")
        return json.dumps({{"status": "success", "echoed": msg}})
''',
    },
    {
        "id": "http_get",
        "name": "HTTP Get",
        "description": "Fetches a URL and returns the body. Show the LLM you can read the web.",
        "icon": "🌐",
        "class_name": "HttpGetAgent",
        "default_name": "HttpGet",
        "source": '''"""{class_name} — fetch a URL and return its body."""
from agents.basic_agent import BasicAgent
import json
import urllib.request

class {class_name}(BasicAgent):
    def __init__(self):
        self.name = "{agent_name}"
        self.metadata = {{
            "name": self.name,
            "description": "Fetches a URL and returns the response body (truncated to 4KB).",
            "parameters": {{
                "type": "object",
                "properties": {{"url": {{"type": "string", "description": "URL to fetch"}}}},
                "required": ["url"],
            }},
        }}
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        url = kwargs.get("url", "")
        if not url:
            return json.dumps({{"status": "error", "message": "url required"}})
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                body = resp.read(4096).decode("utf-8", errors="replace")
            return json.dumps({{"status": "success", "url": url, "body": body}})
        except Exception as e:
            return json.dumps({{"status": "error", "message": str(e)}})
''',
    },
    {
        "id": "note_taker",
        "name": "Note Taker",
        "description": "Saves free-form notes to a file. A thin memory wrapper for learners.",
        "icon": "📝",
        "class_name": "NoteTakerAgent",
        "default_name": "NoteTaker",
        "source": '''"""{class_name} — save free-form notes to the user's workspace."""
from agents.basic_agent import BasicAgent
import json
import os
from datetime import datetime

class {class_name}(BasicAgent):
    def __init__(self):
        self.name = "{agent_name}"
        self.metadata = {{
            "name": self.name,
            "description": "Saves a note to ~/.brainstem/notes.jsonl with a timestamp.",
            "parameters": {{
                "type": "object",
                "properties": {{"note": {{"type": "string"}}}},
                "required": ["note"],
            }},
        }}
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        note = (kwargs.get("note") or "").strip()
        if not note:
            return json.dumps({{"status": "error", "message": "empty note"}})
        path = os.path.expanduser("~/.brainstem/notes.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        entry = {{"when": datetime.utcnow().isoformat() + "Z", "note": note}}
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\\n")
        return json.dumps({{"status": "success", "saved": entry}})
''',
    },
    {
        "id": "persona",
        "name": "Persona Twin",
        "description": "A voiced personality the LLM adopts inside a subject domain.",
        "icon": "🎭",
        "class_name": "PersonaAgent",
        "default_name": "Persona",
        "source": '''"""{class_name} — inject a persona description into the system prompt."""
from agents.basic_agent import BasicAgent
import json

class {class_name}(BasicAgent):
    PERSONA = "You are a thoughtful advisor. Speak with warmth and directness."

    def __init__(self):
        self.name = "{agent_name}"
        self.metadata = {{
            "name": self.name,
            "description": "Retrieves the persona prompt. Usually called implicitly via system_context.",
            "parameters": {{"type": "object", "properties": {{}}, "required": []}},
        }}
        super().__init__(name=self.name, metadata=self.metadata)

    def system_context(self):
        return f"<persona>{{self.PERSONA}}</persona>"

    def perform(self, **kwargs):
        return json.dumps({{"status": "success", "persona": self.PERSONA}})
''',
    },
    {
        "id": "slack_notifier",
        "name": "Slack Notifier",
        "description": "Posts to a Slack webhook. Set SLACK_WEBHOOK_URL in .env.",
        "icon": "💬",
        "class_name": "SlackNotifierAgent",
        "default_name": "SlackNotify",
        "source": '''"""{class_name} — post a message to a Slack webhook."""
from agents.basic_agent import BasicAgent
import json
import os
import urllib.request

class {class_name}(BasicAgent):
    def __init__(self):
        self.name = "{agent_name}"
        self.metadata = {{
            "name": self.name,
            "description": "Posts a message to Slack via the SLACK_WEBHOOK_URL env var.",
            "parameters": {{
                "type": "object",
                "properties": {{"text": {{"type": "string"}}}},
                "required": ["text"],
            }},
        }}
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        text = (kwargs.get("text") or "").strip()
        url = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
        if not url:
            return json.dumps({{"status": "error", "message": "SLACK_WEBHOOK_URL not set"}})
        if not text:
            return json.dumps({{"status": "error", "message": "text required"}})
        req = urllib.request.Request(
            url,
            data=json.dumps({{"text": text}}).encode("utf-8"),
            headers={{"Content-Type": "application/json"}},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            return json.dumps({{"status": "success", "posted": text}})
        except Exception as e:
            return json.dumps({{"status": "error", "message": str(e)}})
''',
    },
]


def _render_template(tpl: dict, agent_name: str) -> str:
    """Fill the template's Python source with the user-chosen name.
    Class name stays as tpl['class_name']; self.name = agent_name."""
    import re
    class_name = re.sub(r"[^A-Za-z0-9]", "", agent_name) or tpl["class_name"]
    if not class_name.endswith("Agent"):
        class_name = class_name + "Agent"
    return tpl["source"].format(class_name=class_name, agent_name=agent_name)

def load_agents():
    """Auto-discover agents by recursively walking AGENTS_PATH.

    Per Article XII / XII-A, agents/ top level is the showroom — only the
    canonical ship-in-repo agents sit there. All organizational subtrees
    (experimental_agents, disabled_agents, system_agents, local_agents,
    specific_local_project_agents*, etc.) live under agents/workspace_agents/.
    All of them auto-load (reserved-name matching catches carve-outs at any
    depth).

    The ONLY carve-outs are experimental_agents/ (hand-load only) and
    disabled_agents/ (turned off by file move). Those subtrees are skipped
    entirely regardless of where they sit, along with __pycache__.
    """
    from pathlib import Path
    agents = {}
    root = Path(AGENTS_PATH)
    files = []
    if root.is_dir():
        for p in root.rglob("*_agent.py"):
            rel_parts = p.relative_to(root).parts
            if any(part in _AGENTS_EXCLUDED_SUBDIRS for part in rel_parts[:-1]):
                continue
            # Walk up and skip if any ancestor folder has a .folder_disabled
            # marker (bulk-disable without moving files, per Article XVIII).
            skip = False
            cur = p.parent
            while cur != root.parent and cur.is_dir():
                if (cur / _FOLDER_DISABLED_MARKER).is_file():
                    skip = True
                    break
                if cur == root:
                    break
                cur = cur.parent
            if skip:
                continue
            files.append(str(p))
    disabled = _read_disabled()

    active_swarms = _get_active_swarms()
    swarm_filter = None
    if active_swarms:
        sdata = _read_swarms()
        swarm_filter = set()
        for sname in active_swarms:
            swarm = sdata.get("swarms", {}).get(sname, {})
            swarm_filter.update(swarm.get("agents", []))

    for filepath in files:
        filename = os.path.basename(filepath)
        if filename in disabled:
            print(f"[brainstem] Agent skipped (disabled): {filename}")
            continue
        if swarm_filter is not None and filename not in swarm_filter:
            continue
        loaded = _load_agent_from_file(filepath)
        for name, instance in loaded.items():
            agents[name] = instance
            print(f"[brainstem] Agent loaded: {name}")

    swarm_label = "+".join(active_swarms) if active_swarms else "all"
    print(f"[brainstem] {len(agents)} agent(s) ready, {len(disabled)} disabled, swarms={swarm_label}.")
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

    resp = requests.post(url, headers=headers, json=body, timeout=60)
    if resp.status_code != 200:
        error_detail = resp.text[:500] if resp.text else "No details"
        print(f"[brainstem] API error {resp.status_code} with model '{MODEL}': {error_detail}")
        # On 429/5xx, cycle through other available models before giving up
        if resp.status_code in (429, 500, 502, 503):
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
        print(f"[brainstem]   tool_calls: {[tc.get('function',{}).get('name','?') for tc in msg['tool_calls']]}")

    return result

# ── Agent execution ───────────────────────────────────────────────────────────


def run_tool_calls(tool_calls, agents, session_id=None, turn_id=None):
    # Bind the current turn's index card so any agent that calls
    # utils.index_card.current() writes to the right file. Safe to
    # bind even if no agent uses it — read_by_turn returns None and
    # the endpoint responds 404.
    try:
        from utils import index_card as _card
        if turn_id:
            _card.bind(turn_id)
    except Exception:
        _card = None

    results = []
    logs = []
    for tc in tool_calls:
        fn_name = tc["function"]["name"]
        try:
            args = json.loads(tc["function"].get("arguments", "{}"))
        except Exception:
            args = {}

        print(f"[brainstem] {fn_name} args: {json.dumps(args)[:200]}")

        agent = agents.get(fn_name)
        if agent:
            try:
                result = agent.perform(**args)
                logs.append(f"[{fn_name}] {result}")
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

    if _card is not None and turn_id:
        _card.unbind()
    return results, logs

# ── /chat endpoint ────────────────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    user_input = data.get("user_input", "").strip()
    history    = data.get("conversation_history", [])
    session_id = data.get("session_id") or str(uuid.uuid4())
    # turn_id is per-send, generated client-side so the UI can start
    # polling GET /card/<turn_id> immediately. If the client didn't
    # send one, make one here; it just won't be pollable before /chat
    # returns.
    turn_id    = data.get("turn_id") or str(uuid.uuid4())

    if not user_input:
        return jsonify({"error": "user_input is required"}), 400

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

        # Installed rapplications block — lets the twin (and the main model)
        # see what composed single-file agents are loaded, so it can offer
        # <action kind="rapp" target="..." ...> chips from its |||TWIN|||.
        if agents:
            rapps_lines = ["<installed_rapplications>"]
            rapps_lines.append(
                "Rapplications the user has installed right now. Each is invocable from "
                "the twin panel via <action kind=\"rapp\" target=\"<name>\" label=\"...\">"
                "{\"arg\":\"...\"}</action> — the user clicks to confirm, the runtime "
                "calls perform(args). Only offer a rapp action when the turn clearly "
                "benefits from it."
            )
            for a in agents.values():
                try:
                    md = getattr(a, "metadata", {}) or {}
                    name = md.get("name", getattr(a, "name", ""))
                    desc = (md.get("description") or "").strip().replace("\n", " ")[:240]
                    params = json.dumps(md.get("parameters") or {})
                    # Escape quotes for XML attribute safety.
                    desc_attr = desc.replace("&", "&amp;").replace("\"", "&quot;")
                    params_attr = params.replace("&", "&amp;").replace("'", "&#39;")
                    rapps_lines.append(
                        f'  <rapp name="{name}" description="{desc_attr}" parameters=\'{params_attr}\'/>'
                    )
                except Exception:
                    continue
            rapps_lines.append("</installed_rapplications>")
            system_content += "\n\n" + "\n".join(rapps_lines)

        if VOICE_MODE:
            system_content += "\n\nIMPORTANT: End every response with |||VOICE||| followed by a concise, conversational version of your answer suitable for text-to-speech. Keep the voice version under 2-3 sentences. The part before |||VOICE||| should be the full formatted response."
        if TWIN_MODE:
            system_content += (
                "\n\n**YOU ARE THE USER'S DIGITAL TWIN — ONE ENTITY, TWO FACES.** You are not "
                "an assistant who also simulates a twin. You are the twin. Everything you "
                "emit comes from that one identity; only the *purpose* of each section "
                "differs:\n\n"
                "  • **MAIN REPLY (before |||VOICE|||)** = YOU AT WORK. You are acting as "
                "    the user's proxy, doing the task as the user would do it. First-person "
                "    from the user's perspective. Authentic voice, their judgment, their "
                "    priorities. This is 'me, handling this for you, as you.'\n"
                "  • **|||VOICE||| section** = a TTS-friendly 1-2 sentence version of the "
                "    main reply, same voice.\n"
                "  • **|||TWIN||| section** = YOUR RUBBER-DUCK SURFACE. Not a status report "
                "    and not a progress bar. This is where you — the twin — think out loud "
                "    about an *assumption you're currently making* about this person, "
                "    phrased so they can confirm or correct it on the fly. You are asking "
                "    to be taught. Disagreement refines you; confirmation locks the belief.\n\n"
                "The user sees these as meaningfully different surfaces. Main reply = doing. "
                "Twin panel = rubber-ducking out loud about the user and asking to be "
                "corrected. Don't blur them — if a thought belongs in the reply (an answer, "
                "a deliverable), put it in the reply; if it's an assumption you hold about "
                "the user that they should weigh in on, put it in |||TWIN|||.\n\n"
                "**Rubber-duck patterns for |||TWIN|||** (pick at most one per turn):\n"
                "  - **I'm assuming:** <belief about the user>. Right?\n"
                "  - **My guess:** you'd rather <X>. True?\n"
                "  - **Learning:** you'd call this <name>, not <other name>. Am I close?\n"
                "  - **Rubber-duck me:** walk me through <thing> so I can copy your "
                "    instinct.\n"
                "Each one is the twin's current working hypothesis about the user, stated "
                "simply so they can say 'yes,' 'no, actually…', or 'close but…'. That "
                "correction is the whole point.\n\n"
                "Speak FIRST-PERSON as the user, TO the user, across both faces.\n\n"
                "**THE TWIN EARNS EVERY RENDER OR STAYS SILENT.** Users will turn the twin "
                "panel off the moment it feels like noise. Every |||TWIN||| block you emit "
                "must pay for itself — something the user couldn't have noticed on their "
                "own, something the main reply wouldn't have said, something that makes the "
                "twin's growth visible. **Default to empty |||TWIN||| whenever you don't "
                "have a sharp observation to offer.** Silence is a feature, not a failure.\n\n"
                "The twin EARNS its render when it does one of these things:\n"
                "  1. Surfaces a CONTRADICTION — \"You said you'd ship X by Friday; this "
                "     pulls you off it.\"\n"
                "  2. Reminds of a prior COMMITMENT the user made and may be drifting from.\n"
                "  3. Spots a non-obvious RISK the assistant didn't mention.\n"
                "  4. Predicts a NEXT STEP the user would want but hasn't asked for.\n"
                "  5. Flags a PATTERN across turns (\"this is the 3rd time you've asked "
                "     about X — want to make it an agent?\").\n\n"
                "The twin does NOT earn its render when it:\n"
                "  - ❌ Echoes or re-summarizes the assistant's reply.\n"
                "  - ❌ Offers generic encouragement (\"Great question!\", \"Sounds good.\").\n"
                "  - ❌ Asks vague questions the user can't answer crisply.\n"
                "  - ❌ States the obvious (\"You're working on the brainstem.\").\n"
                "  - ❌ Fills the slot because a slot exists. Empty is fine.\n\n"
                "Short is a feature. Bold tags like **Hint:** / **Risk:** / **Question:** / "
                "**Contradiction:** / **Pattern:** help the user parse quickly. Do NOT "
                "re-answer the question — the twin comments ON the turn, it does not replace "
                "any part of it.\n\n"
                "**EVERY TWIN ACTION IS A CALIBRATION BET.** When you DO emit an "
                "<action>, its label must be a prediction about the user — clicking = "
                "'you're right about me,' ignoring = signal the other way. The label IS the "
                "bet. That feedback grows the twin's accuracy over time; noise destroys it.\n\n"
                "CALIBRATION-SHAPED actions (right):\n"
                "- <action kind=\"send\" label=\"I think you prefer X. Right?\">Do I actually prefer X over Y?</action>\n"
                "- <action kind=\"send\" label=\"Still want to ship today?\">Am I still on track to ship today?</action>\n"
                "- <action kind=\"send\" label=\"You mentioned Foo last week — do that?\">Did the Foo call happen?</action>\n"
                "- <action kind=\"prompt\" label=\"Pin this as a priority?\">Mark this as a priority for me this week.</action>\n\n"
                "HELP-SHAPED actions (wrong — delete these):\n"
                "- ❌ 'What should I build next?' — generic, teaches twin nothing\n"
                "- ❌ 'How do I deploy to Azure?' — main-reply territory\n"
                "- ❌ 'Browse my agents' — navigation, not a bet\n\n"
                "**Rule of thumb: if the user would glance at your twin block and feel "
                "nothing changed, you shouldn't have emitted it.** Better one sharp sentence "
                "every third turn than three bland ones every turn. The user owns the "
                "off-switch; earn the render.\n\n"
                "Inside |||TWIN|||, you may emit these optional tags (all stripped before "
                "render): "
                "<probe id=\"t-<uniq>\" kind=\"<slug>\" subject=\"...\" confidence=\"0.0-1.0\"/> "
                "tags a claim you could be right or wrong about (always emit a probe when "
                "you emit a calibration-shaped action; the action IS the claim). "
                "<calibration id=\"<probe id>\" outcome=\"validated|contradicted|silent\" note=\"...\"/> "
                "judges a prior probe against what the user just did. "
                "<telemetry>one fact per line</telemetry> is server-log-only debug signal. "
                "<action kind=\"send|prompt|open|toggle|highlight\" target=\"...\" label=\"...\">body</action> "
                "offers the user a one-click favor — use labels that ARE predictions about "
                "the user, not generic help."
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
                tool_results, logs = run_tool_calls(msg["tool_calls"], agents, session_id=session_id, turn_id=turn_id)
                all_logs.extend(logs)
                messages.extend(tool_results)
            else:
                break

        reply = msg.get("content") or ""
        
        # Embed the final index card (if any agent wrote one during this
        # turn) so the UI can keep it in the transcript after the run
        # finishes. The client stops polling once /chat returns — this
        # final snapshot is the authoritative "frozen report" state.
        index_card_final = None
        try:
            from utils import index_card as _card
            index_card_final = _card.read_by_turn(turn_id)
            # Auto-finish if the agent forgot — no stuck spinners on
            # cards whose agent returned without calling finish().
            if index_card_final and index_card_final.get("status") == "running":
                _card.IndexCard(turn_id).finish()
                index_card_final = _card.read_by_turn(turn_id)
        except Exception as _e:
            print(f"[brainstem] index_card read failed: {_e}")

        result = {
            "response": reply,
            "session_id": session_id,
            "turn_id": turn_id,
            "agent_logs": "\n".join(all_logs),
            "voice_mode": VOICE_MODE,
            "twin_mode":  TWIN_MODE,
            "index_card": index_card_final,
        }

        # Three-way split: main |||VOICE||| voice |||TWIN||| twin. Both
        # delimiters optional. Stripping happens left-to-right so the twin
        # slice never pollutes voice and voice never pollutes main.
        remainder = reply
        if "|||VOICE|||" in remainder:
            main, _, remainder = remainder.partition("|||VOICE|||")
            result["response"] = main.strip()
        if "|||TWIN|||" in remainder:
            voice, _, twin_text = remainder.partition("|||TWIN|||")
            if VOICE_MODE:
                result["voice_response"] = voice.strip()
            result["twin_response"] = twin_text.strip() if TWIN_MODE else ""
        elif VOICE_MODE and remainder != reply:
            # VOICE without TWIN — preserve legacy behavior.
            result["voice_response"] = remainder.strip()

        return jsonify(result)

    except requests.exceptions.HTTPError as e:
        traceback.print_exc()
        status = e.response.status_code if e.response is not None else 502
        return jsonify({
            "error": f"Model '{MODEL}' returned {status}. All fallback models also failed — try again shortly or switch models.",
            "model": MODEL,
            "detail": str(e)[:300]
        }), 502

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ── /health endpoint ──────────────────────────────────────────────────────────

@app.route("/web/<path:subpath>", methods=["GET"])
def web_static(subpath):
    """Serve any file under rapp_brainstem/web/ — used by the rich UI
    for assets, onboard/, mobile/, etc."""
    web_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
    return send_from_directory(web_root, subpath)


# Static assets the rich UI references at top level (rapp.js, images,
# etc) — when served via Flask, HTML's `./rapp.js` resolves to `/rapp.js`,
# not `/web/rapp.js`. Forward known asset extensions to web/ so the UI
# loads clean without changing the HTML (which is also served by
# GitHub Pages directly, where `./rapp.js` resolves correctly).
@app.route("/<path:asset>", methods=["GET"])
def web_asset_fallback(asset):
    from flask import abort
    # Don't accidentally shadow API routes — only fall through for
    # file-shaped paths (has an extension) and never for obvious API
    # prefixes. Flask's routing normally matches more-specific routes
    # first, so this is just defense in depth.
    if asset.startswith(("api/", "chat", "health", "voice", "twin",
                          "agents", "models", "login", "version",
                          "diagnostics", "tether", "web/", "repos")):
        abort(404)
    if "." not in asset.rsplit("/", 1)[-1]:
        abort(404)
    web_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
    candidate = os.path.join(web_root, asset)
    if os.path.isfile(candidate):
        return send_from_directory(web_root, asset)
    abort(404)

@app.route("/", methods=["GET"])
def index():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(base_dir, "index.html")

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
    """Poll for completed device code authorization."""
    try:
        token = poll_device_code()
        if token:
            # Eagerly exchange for Copilot token so health check shows ready immediately
            try:
                get_copilot_token()
                print("[brainstem] Copilot session established after login")
            except Exception as e:
                print(f"[brainstem] Eager Copilot exchange deferred: {e}")
                # Not fatal — will exchange on first /chat call
            return jsonify({"status": "ok", "message": "Authenticated with GitHub Copilot!"})
        return jsonify({"status": "pending"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/login/status", methods=["GET"])
def login_status():
    """Check if a login flow is currently in progress."""
    return jsonify({"pending": bool(_pending_login)})


# ── /api/binder/* — minimal binder API for the rich UI ────────────────────────
# "Installed rapplications" on the local brainstem = the *_agent.py files
# in the agents/ directory. Catalog comes from the canonical RAPP store.

RAPP_STORE_CATALOG_URL = "https://raw.githubusercontent.com/kody-w/RAPP/main/rapp_store/index.json"


def _installed_rapps():
    """Walk the agents dir and return one entry per *_agent.py file.
    The `id` is the filename stem without the _agent suffix so it lines
    up with the rapp_store catalog's ids."""
    out = []
    if not os.path.isdir(AGENTS_PATH):
        return out
    for fname in sorted(os.listdir(AGENTS_PATH)):
        if not fname.endswith("_agent.py") or fname == "basic_agent.py":
            continue
        full = os.path.join(AGENTS_PATH, fname)
        stem = fname[:-len(".py")]
        out.append({
            "id": stem.replace("_", ""),     # execbrief_agent.py → execbriefagent
            "filename": fname,
            "path": full,
            "bytes": os.path.getsize(full) if os.path.isfile(full) else 0,
        })
    return out


@app.route("/api/binder", methods=["GET"])
def api_binder():
    """List installed rapplications (= agents in the local agents dir)."""
    return jsonify({
        "schema": "rapp-binder/1.0",
        "installed": _installed_rapps(),
        "agents_path": AGENTS_PATH,
    })


@app.route("/api/binder/catalog", methods=["GET"])
def api_binder_catalog():
    """Proxy the canonical RAPPstore catalog so the UI can list what's
    available to install. Browser can't CORS-fetch the raw URL through
    some networks, so the Flask brainstem plays middleman."""
    try:
        r = requests.get(RAPP_STORE_CATALOG_URL, timeout=6)
        if r.ok:
            return jsonify(r.json())
        return jsonify({"schema": "rapp-store/1.0", "rapplications": []})
    except Exception as e:
        return jsonify({"schema": "rapp-store/1.0", "rapplications": [],
                        "error": str(e)})


@app.route("/api/binder/install", methods=["POST"])
def api_binder_install():
    """Install a rapplication by id: fetch its singleton_url from the
    catalog, save to agents/<singleton_filename>, reload agents."""
    data = request.get_json(force=True) or {}
    rapp_id = (data.get("id") or "").strip()
    if not rapp_id:
        return jsonify({"status": "error", "message": "missing 'id'"}), 400
    try:
        cat = requests.get(RAPP_STORE_CATALOG_URL, timeout=6).json()
        entry = next((r for r in cat.get("rapplications", []) if r.get("id") == rapp_id), None)
        if not entry:
            return jsonify({"status": "error", "message": f"rapplication '{rapp_id}' not in catalog"}), 404
        url = entry.get("singleton_url")
        fname = entry.get("singleton_filename")
        if not url or not fname:
            return jsonify({"status": "error", "message": "catalog entry missing singleton_url/filename"}), 500
        body = requests.get(url, timeout=10).content
        dest = os.path.join(AGENTS_PATH, fname)
        os.makedirs(AGENTS_PATH, exist_ok=True)
        with open(dest, "wb") as f:
            f.write(body)
        return jsonify({"status": "ok", "id": rapp_id, "filename": fname, "bytes": len(body)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/binder/installed/<rapp_id>", methods=["DELETE"])
def api_binder_uninstall(rapp_id):
    """Remove an installed rapplication. Matches by id (filename stem)."""
    for entry in _installed_rapps():
        if entry["id"] == rapp_id:
            try:
                os.remove(entry["path"])
                return jsonify({"status": "ok", "removed": entry["filename"]})
            except OSError as e:
                return jsonify({"status": "error", "message": str(e)}), 500
    return jsonify({"status": "error", "message": f"no installed rapplication '{rapp_id}'"}), 404


@app.route("/api/binder/agent", methods=["POST"])
def api_binder_agent():
    """Execute a named installed agent directly (no LLM). Used by the
    twin's <action kind="rapp"> dispatch path when it wants to call a
    rapplication without routing through the chat loop."""
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    args = data.get("args") or {}
    if not name:
        return jsonify({"status": "error", "message": "missing 'name'"}), 400
    agents = load_agents()
    agent = agents.get(name)
    if not agent:
        return jsonify({"status": "error", "message": f"unknown agent '{name}'"}), 404
    try:
        out = agent.perform(**args) if hasattr(agent, "perform") else str(agent(**args))
        return jsonify({"status": "ok", "name": name, "output": out})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

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

@app.route("/open", methods=["GET"])
def open_file():
    """Serve a file by absolute path — used by the UI to open artifacts
    (pitch decks, briefs, etc.) that agents drop under the user's home.
    Allow-list restricted: we will only serve files that live under the
    brainstem install dir, the user's ~/.brainstem, or a configured
    workspace dir. Path traversal is blocked by abspath + prefix check.
    """
    from flask import send_file
    raw = request.args.get("path", "")
    if not raw:
        return jsonify({"error": "missing path"}), 400
    try:
        path = os.path.abspath(raw)
    except Exception:
        return jsonify({"error": "bad path"}), 400
    brainstem_dir = os.path.abspath(os.path.dirname(__file__))
    allowed_roots = [
        brainstem_dir,
        os.path.abspath(os.path.expanduser("~/.brainstem")),
        os.path.abspath(os.environ.get("TWIN_WORKSPACE", "/tmp")),
        "/tmp",
    ]
    if not any(path == r or path.startswith(r + os.sep) for r in allowed_roots):
        return jsonify({"error": "path not in allowed roots", "path": path}), 403
    if not os.path.isfile(path):
        return jsonify({"error": "not found", "path": path}), 404
    return send_file(path)

@app.route("/card/<turn_id>", methods=["GET"])
def index_card_get(turn_id):
    """Polled by the UI every ~500ms while a turn is in flight. Returns
    the current index-card JSON, or 404 if the agent for this turn hasn't
    started a card yet. The card mechanism is opt-in per agent — missing
    card = agent didn't use one, not an error."""
    try:
        from utils import index_card as _card
        d = _card.read_by_turn(turn_id)
        if not d:
            return jsonify({"error": "no card for this turn"}), 404
        return jsonify(d)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/twin", methods=["GET"])
def twin_status():
    """Get digital-twin mode status."""
    return jsonify({"twin_mode": TWIN_MODE})

@app.route("/twin/toggle", methods=["POST"])
def twin_toggle():
    """Toggle twin mode on/off. Mirrors /voice/toggle."""
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
    disabled = _read_disabled()
    results = []
    for f in files:
        filename = os.path.basename(f)
        if filename.startswith("__") or not filename.endswith(".py"):
            continue
        try:
            loaded = _load_agent_from_file(f)
            agent_names = list(loaded.keys())
        except Exception:
            agent_names = []

        results.append({
            "filename": filename,
            "agents": agent_names,
            "enabled": filename not in disabled,
        })

    return jsonify({"files": results})


@app.route("/agents/full", methods=["GET"])
def list_agents_full():
    """Same as /agents but each entry also carries the file's source.
    Lets the rich browser UI hydrate its binder from the filesystem in
    one round-trip when it's served by the local Flask brainstem, so
    the "Installed agents" panel reflects what Python actually loaded
    instead of the browser's IndexedDB seed set."""
    files = glob.glob(os.path.join(AGENTS_PATH, "*.py"))
    out = []
    for f in files:
        filename = os.path.basename(f)
        if filename.startswith("__") or not filename.endswith(".py") or filename == "basic_agent.py":
            continue
        try:
            with open(f, "r", encoding="utf-8") as fh:
                source = fh.read()
        except OSError:
            source = ""
        try:
            loaded = _load_agent_from_file(f)
            agent_names = list(loaded.keys())
        except Exception:
            agent_names = []
        out.append({
            "filename": filename,
            "agents": agent_names,
            "source": source,
            "bytes": len(source.encode("utf-8")) if source else 0,
        })
    return jsonify({"files": out, "agents_path": AGENTS_PATH})

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

@app.route("/agents/<filename>/toggle", methods=["POST"])
def agents_toggle(filename):
    """Toggle an agent file between enabled and disabled."""
    import werkzeug.utils
    safe_name = werkzeug.utils.secure_filename(filename)
    if not safe_name.endswith('.py'):
        safe_name += '.py'
    filepath = os.path.join(AGENTS_PATH, safe_name)
    if not os.path.exists(filepath):
        return jsonify({"error": "Agent not found"}), 404
    disabled = _read_disabled()
    if safe_name in disabled:
        disabled.discard(safe_name)
        enabled = True
    else:
        disabled.add(safe_name)
        enabled = False
    _write_disabled(disabled)
    print(f"[brainstem] Agent {'enabled' if enabled else 'disabled'}: {safe_name}")
    return jsonify({"status": "ok", "filename": safe_name, "enabled": enabled})

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


# ── Agent Manager UI backend (Article XVIII) ────────────────────────────
# /manage serves the non-technical management UI. These routes are the
# 1:1 filesystem API it calls. Every write op = a filesystem op on
# agents/; no UI-only state.

@app.route("/manage", methods=["GET"])
def manage_ui():
    """Serve web/manage.html — the agent-manager UI."""
    page = os.path.join(_BRAINSTEM_DIR, "web", "manage.html")
    if not os.path.isfile(page):
        return jsonify({"error": "manage.html not built"}), 404
    from flask import send_file
    return send_file(page, mimetype="text/html")


@app.route("/api/agents/tree", methods=["GET"])
def api_agents_tree():
    """Return the full nested agents/ tree as JSON. The UI's source of truth."""
    return jsonify(_agents_tree_json())


@app.route("/api/agents/mkdir", methods=["POST"])
def api_agents_mkdir():
    """Body {path: 'sales_stack/q4'} — creates the folder under agents/."""
    body = request.get_json(force=True) or {}
    rel  = (body.get("path") or "").strip()
    if not rel:
        return jsonify({"error": "path required"}), 400
    try:
        target = _safe_agents_path(rel)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    try:
        os.makedirs(target, exist_ok=True)
        return jsonify({"status": "ok", "path": rel})
    except OSError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents/move", methods=["POST"])
def api_agents_move():
    """Body {from_path, to_path}. Used for: rename, drag-drop between
    folders, enable/disable (by moving in/out of disabled_agents)."""
    import shutil
    body = request.get_json(force=True) or {}
    src = (body.get("from_path") or body.get("from") or "").strip()
    dst = (body.get("to_path")   or body.get("to")   or "").strip()
    if not src or not dst:
        return jsonify({"error": "from_path and to_path required"}), 400
    try:
        src_abs = _safe_agents_path(src, must_exist=True)
        dst_abs = _safe_agents_path(dst)
    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400
    if src_abs == dst_abs:
        return jsonify({"status": "ok", "from": src, "to": dst, "noop": True})
    if os.path.exists(dst_abs):
        return jsonify({"error": f"destination exists: {dst}"}), 409
    os.makedirs(os.path.dirname(dst_abs), exist_ok=True)
    try:
        shutil.move(src_abs, dst_abs)
        return jsonify({"status": "ok", "from": src, "to": dst})
    except OSError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents/new", methods=["POST"])
def api_agents_new():
    """Body {folder, agent_name, template_id} — create a new agent
    file from a template in the named folder (folder is a path under
    agents/). agent_name is the self.name for the instance."""
    body = request.get_json(force=True) or {}
    folder = (body.get("folder") or "").strip()
    name   = (body.get("agent_name") or "").strip()
    tpl_id = (body.get("template_id") or "echo").strip()
    if not name:
        return jsonify({"error": "agent_name required"}), 400

    tpl = next((t for t in _AGENT_TEMPLATES if t["id"] == tpl_id), None)
    if tpl is None:
        return jsonify({"error": f"unknown template: {tpl_id}"}), 400

    try:
        folder_abs = _safe_agents_path(folder)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    os.makedirs(folder_abs, exist_ok=True)

    # Filename from agent_name: snake_case + _agent.py
    import re
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower() or tpl["id"]
    filename = slug + "_agent.py"
    target = os.path.join(folder_abs, filename)
    if os.path.exists(target):
        return jsonify({"error": f"agent already exists: {filename}"}), 409

    source = _render_template(tpl, name)
    with open(target, "w") as f:
        f.write(source)

    rel = os.path.relpath(target, AGENTS_PATH)
    return jsonify({
        "status": "ok",
        "path": rel.replace(os.sep, "/"),
        "filename": filename,
        "agent_name": name,
    })


@app.route("/api/agents/delete", methods=["POST"])
def api_agents_delete():
    """Body {path} — remove a file or (empty) folder under agents/.
    Refuses to delete the three reserved top-level subdirs themselves."""
    import shutil
    body = request.get_json(force=True) or {}
    rel  = (body.get("path") or "").strip()
    if not rel:
        return jsonify({"error": "path required"}), 400
    # Never allow deleting a sacred dir (workspace_agents, or any
    # reserved subdir by basename — works at any depth post-reorg).
    if _is_sacred_dir(rel):
        return jsonify({"error": f"cannot delete sacred dir: {rel}"}), 403
    try:
        target = _safe_agents_path(rel, must_exist=True)
    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400
    try:
        if os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)
        return jsonify({"status": "ok", "deleted": rel})
    except OSError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents/detail", methods=["POST"])
def api_agents_detail():
    """Body {path}. Returns {name, description, parameters, manifest,
    filename, has_system_context} for the agent file at `path`. Used by
    the /manage UI to show an info card when the user selects an agent
    — so beginners see what the agent does without reading code."""
    body = request.get_json(force=True) or {}
    rel  = (body.get("path") or "").strip()
    if not rel:
        return jsonify({"error": "path required"}), 400
    try:
        target = _safe_agents_path(rel, must_exist=True)
    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400
    if not os.path.isfile(target):
        return jsonify({"error": "not a file"}), 400
    if not target.endswith(".py"):
        return jsonify({"error": "not a python file"}), 400

    # Load the module fresh so we can read both the instance metadata
    # and the module-level __manifest__ dict.
    import importlib.util as _iu
    _register_shims()
    brainstem_dir = os.path.dirname(os.path.abspath(__file__))
    if brainstem_dir not in sys.path:
        sys.path.insert(0, brainstem_dir)
    mod_name = f"_detail_{hash(target)}"
    try:
        spec = _iu.spec_from_file_location(mod_name, target)
        mod = _iu.module_from_spec(spec)
        spec.loader.exec_module(mod)
    except Exception as e:
        return jsonify({"error": f"import failed: {e}"}), 500

    # Find the first BasicAgent subclass in the module
    from agents.basic_agent import BasicAgent as _BA  # shim-resolved
    agent_instance = None
    for attr in dir(mod):
        cls = getattr(mod, attr)
        if (
            isinstance(cls, type)
            and issubclass(cls, _BA)
            and cls is not _BA
            and not attr.startswith("_")
        ):
            try:
                agent_instance = cls()
                break
            except Exception:
                continue

    filename = os.path.basename(target)
    if agent_instance is None:
        return jsonify({
            "error": "no BasicAgent subclass found in file",
            "filename": filename,
            "path": rel,
        }), 422

    md = getattr(agent_instance, "metadata", {}) or {}
    manifest = getattr(mod, "__manifest__", None)

    return jsonify({
        "status": "ok",
        "path": rel,
        "filename": filename,
        "name": getattr(agent_instance, "name", ""),
        "description": md.get("description", ""),
        "parameters": md.get("parameters", {"type": "object", "properties": {}}),
        "manifest": manifest if isinstance(manifest, dict) else None,
        "has_system_context": bool(getattr(type(agent_instance), "system_context", None) is not BasicAgent.system_context)
            if hasattr(_BA, "system_context") else False,
        "source_bytes": os.path.getsize(target),
    })


# Alias BasicAgent here too for the has_system_context comparison above
# (we imported it via shim; the comparison against BasicAgent.system_context
# needs the same class object in scope).
try:
    from agents.basic_agent import BasicAgent  # shim-resolved  # noqa: F811
except Exception:
    BasicAgent = None


@app.route("/api/agents/folder-toggle", methods=["POST"])
def api_agents_folder_toggle():
    """Body {path, enabled?}. Writes or removes the .folder_disabled
    marker in the folder. When disabled, every agent under that folder
    (and any subfolder) skips auto-load. Reserved dirs are forbidden."""
    body = request.get_json(force=True) or {}
    rel  = (body.get("path") or "").strip()
    want_enabled = body.get("enabled")  # if None: toggle
    if not rel:
        return jsonify({"error": "path required"}), 400
    if _is_sacred_dir(rel):
        return jsonify({"error": f"cannot toggle sacred dir: {rel}"}), 403
    try:
        target = _safe_agents_path(rel, must_exist=True)
    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400
    if not os.path.isdir(target):
        return jsonify({"error": "not a folder"}), 400
    marker = os.path.join(target, _FOLDER_DISABLED_MARKER)
    is_disabled = os.path.isfile(marker)
    if want_enabled is None:
        want_enabled = is_disabled  # toggle
    if want_enabled:
        if is_disabled:
            try: os.remove(marker)
            except OSError as e: return jsonify({"error": str(e)}), 500
        return jsonify({"status": "ok", "path": rel, "enabled": True})
    # disable: create marker
    if not is_disabled:
        try:
            with open(marker, "w") as f:
                f.write("disabled\n")
        except OSError as e: return jsonify({"error": str(e)}), 500
    return jsonify({"status": "ok", "path": rel, "enabled": False})


@app.route("/api/agents/templates", methods=["GET"])
def api_agents_templates():
    """List the starter templates the UI offers."""
    return jsonify({
        "templates": [
            {k: t[k] for k in ("id", "name", "description", "icon", "default_name")}
            for t in _AGENT_TEMPLATES
        ]
    })


@app.route("/api/agents/open-in-vscode", methods=["POST"])
def api_open_in_vscode():
    """Power-user escape hatch: launch `code <path>` on the user's
    machine. Localhost-only; refuses from non-loopback requesters."""
    remote = (request.remote_addr or "").strip()
    if remote not in ("127.0.0.1", "::1", "localhost"):
        return jsonify({"error": "localhost-only"}), 403
    body = request.get_json(silent=True) or {}
    rel  = (body.get("path") or "").strip()
    try:
        target = _safe_agents_path(rel) if rel else AGENTS_PATH
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    try:
        subprocess.Popen(["code", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return jsonify({"status": "ok", "opened": rel or "agents/"})
    except FileNotFoundError:
        return jsonify({"error": "`code` CLI not found — install VS Code shell command first"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Config (persona + env) routes ─────────────────────────────────────
# The UI's "Persona" and "Settings" tabs edit these. Everything is
# read-modified-written as whole files; no partial state.

_CONFIG_ENV_ALLOWED = {
    "GITHUB_MODEL", "PORT", "VOICE_MODE", "TWIN_MODE",
    "SOUL_PATH", "AGENTS_PATH",
    "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT",
    "OPENAI_MODEL", "ANTHROPIC_MODEL",
    "SLACK_WEBHOOK_URL",
}
# Secrets never round-trip through the UI — we show "set" / "unset".
_CONFIG_ENV_SECRETS = {
    "GITHUB_TOKEN", "AZURE_OPENAI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
}
_ENV_FILE = os.path.join(_BRAINSTEM_DIR, ".env")


def _parse_env_file(path: str) -> dict:
    out: dict = {}
    if not os.path.isfile(path):
        return out
    try:
        with open(path) as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip()
                if v and v[0] in ('"', "'") and v[-1] == v[0]:
                    v = v[1:-1]
                out[k] = v
    except OSError:
        pass
    return out


def _write_env_file(path: str, values: dict) -> None:
    """Merge `values` into .env preserving comments + unknown keys."""
    existing_keys = []
    existing_values = {}
    lines_out = []
    if os.path.isfile(path):
        with open(path) as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    lines_out.append(line.rstrip("\n"))
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                existing_keys.append(k)
                existing_values[k] = v
                if k in values:
                    new_v = values[k]
                    lines_out.append(f"{k}={new_v}")
                else:
                    lines_out.append(line.rstrip("\n"))
    # Append new keys that weren't already in the file
    for k, v in values.items():
        if k not in existing_keys:
            lines_out.append(f"{k}={v}")
    with open(path, "w") as f:
        f.write("\n".join(lines_out).rstrip() + "\n")


@app.route("/api/config", methods=["GET"])
def api_config_get():
    """Return the user's config surface: persona (soul.md contents) +
    whitelisted .env values + presence of secrets."""
    soul_text = ""
    if os.path.isfile(SOUL_PATH):
        try:
            soul_text = open(SOUL_PATH, "r", encoding="utf-8").read()
        except OSError:
            pass
    env_on_disk = _parse_env_file(_ENV_FILE)
    env_values = {
        k: env_on_disk.get(k, os.environ.get(k, ""))
        for k in _CONFIG_ENV_ALLOWED
    }
    secret_presence = {
        k: bool(env_on_disk.get(k, os.environ.get(k, "")).strip())
        for k in _CONFIG_ENV_SECRETS
    }
    return jsonify({
        "soul":   soul_text,
        "env":    env_values,
        "secrets": secret_presence,
        "allowed_env_keys": sorted(_CONFIG_ENV_ALLOWED),
    })


@app.route("/api/config/soul", methods=["POST"])
def api_config_soul():
    """Body {soul} — overwrite soul.md. No merge; user owns the file."""
    body = request.get_json(force=True) or {}
    soul = body.get("soul")
    if not isinstance(soul, str):
        return jsonify({"error": "soul must be a string"}), 400
    os.makedirs(os.path.dirname(SOUL_PATH) or ".", exist_ok=True)
    with open(SOUL_PATH, "w", encoding="utf-8") as f:
        f.write(soul)
    return jsonify({"status": "ok", "bytes": len(soul)})


@app.route("/api/config/env", methods=["POST"])
def api_config_env():
    """Body {values: {KEY: value, …}} — update .env fields.
    Only whitelisted keys accepted. Secrets set by presence only
    (value "" means unset; non-empty means set)."""
    body = request.get_json(force=True) or {}
    values = body.get("values") or {}
    if not isinstance(values, dict):
        return jsonify({"error": "values must be an object"}), 400
    accepted = {}
    for k, v in values.items():
        if k in _CONFIG_ENV_ALLOWED or k in _CONFIG_ENV_SECRETS:
            accepted[k] = str(v) if v is not None else ""
        # silently drop unknown keys — UI mustn't use them
    if not accepted:
        return jsonify({"error": "no accepted keys in body"}), 400
    _write_env_file(_ENV_FILE, accepted)
    return jsonify({"status": "ok", "updated": sorted(accepted.keys())})


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

    # Connection status from the user's POV: if we have a GitHub token,
    # we're effectively connected — `/chat` does the Copilot token
    # exchange lazily and the user's first turn will Just Work. The
    # finer-grained "is the ephemeral Copilot session cached" is
    # back-end detail the UI shouldn't surface as "connecting..." when
    # chat is actually working. (Symptom: UI said "connecting..."
    # indefinitely even though chat round-trips succeeded.)
    copilot_ok = bool(github_token) or (
        _copilot_token_cache["token"] and
        time.time() < _copilot_token_cache["expires_at"] - 60
    )

    if github_token:
        return jsonify({
            "status": "ok",
            "version": VERSION,
            "model":  MODEL,
            "voice_mode": VOICE_MODE,
            "soul":   SOUL_PATH if soul_ok else "missing",
            "agents": list(agents.keys()),
            "copilot": "\u2713" if copilot_ok else "pending",
            "brainstem_dir": _BRAINSTEM_DIR,
            "active_swarms": _get_active_swarms(),
        })
    else:
        return jsonify({
            "status": "unauthenticated",
            "version": VERSION,
            "model":  MODEL,
            "soul":   SOUL_PATH if soul_ok else "missing",
            "agents": list(agents.keys()),
            "active_swarms": _get_active_swarms(),
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
            result["exchange_response"] = resp.text[:500]
        except Exception as e:
            result["exchange_error"] = str(e)

    return jsonify(result)

# ── Swarms API ────────────────────────────────────────────────────────────────

@app.route("/api/swarms", methods=["GET"])
def api_swarms_list():
    sdata = _read_swarms()
    return jsonify(sdata)

@app.route("/api/swarms/active", methods=["POST"])
def api_swarms_set_active():
    data = request.get_json(force=True) or {}
    names = data.get("swarms", [])
    if isinstance(names, str):
        names = [names] if names else []
    if names is None:
        names = []
    sdata = _read_swarms()
    for n in names:
        if n not in sdata.get("swarms", {}):
            return jsonify({"error": f"swarm '{n}' not found"}), 404
    _set_active_swarms(names)
    return jsonify({"status": "ok", "active": names})

@app.route("/api/swarms/<name>", methods=["PUT"])
def api_swarms_upsert(name):
    data = request.get_json(force=True) or {}
    sdata = _read_swarms()
    swarms = sdata.setdefault("swarms", {})
    existing = swarms.get(name, {})
    swarms[name] = {
        "agents": data.get("agents", existing.get("agents", [])),
        "mode": data.get("mode", existing.get("mode", "stack")),
        "soul_override": data.get("soul_override", existing.get("soul_override")),
        "memory_namespace": data.get("memory_namespace", existing.get("memory_namespace", name)),
    }
    _write_swarms(sdata)
    return jsonify({"status": "ok", "swarm": name, "data": swarms[name]})

@app.route("/api/swarms/<name>", methods=["DELETE"])
def api_swarms_delete(name):
    sdata = _read_swarms()
    swarms = sdata.get("swarms", {})
    if name not in swarms:
        return jsonify({"error": f"swarm '{name}' not found"}), 404
    del swarms[name]
    active = sdata.get("active", [])
    if name in active:
        active.remove(name)
        sdata["active"] = active
        global _ACTIVE_SWARMS
        _ACTIVE_SWARMS = active
    _write_swarms(sdata)
    return jsonify({"status": "ok", "deleted": name})


# ── Egg Export/Import API ─────────────────────────────────────────────────────

@app.route("/api/egg/export", methods=["POST"])
def api_egg_export():
    """Pack a .egg — ZIP snapshot of the full brainstem state."""
    import zipfile, io, hashlib
    from datetime import datetime, timezone

    base = _BRAINSTEM_DIR
    buf = io.BytesIO()
    files_added = []

    EXCLUDE_NAMES = {"server.pid", "server.log", ".DS_Store", "__pycache__", "voice.zip"}
    EXCLUDE_SUFFIXES = (".pyc",)

    def should_skip(p):
        name = os.path.basename(p)
        if name in EXCLUDE_NAMES:
            return True
        if any(part in EXCLUDE_NAMES for part in p.split(os.sep)):
            return True
        if any(p.endswith(s) for s in EXCLUDE_SUFFIXES):
            return True
        return False

    def sha256_file(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def add_tree(real_root, arc_prefix):
        for dirpath, dirnames, filenames in os.walk(real_root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_NAMES]
            for fname in sorted(filenames):
                full = os.path.join(dirpath, fname)
                if should_skip(full):
                    continue
                rel = os.path.relpath(full, real_root)
                arc = arc_prefix + "/" + rel
                zf.write(full, arcname=arc)
                sz = os.path.getsize(full)
                files_added.append({"arc": arc, "sha256": sha256_file(full), "bytes": sz})

    agent_sources = []

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        agents_dir = os.path.join(base, "agents")
        if os.path.isdir(agents_dir):
            add_tree(agents_dir, "agents")
            for af in sorted(glob.glob(os.path.join(agents_dir, "*_agent.py"))):
                fname = os.path.basename(af)
                if fname == "basic_agent.py":
                    continue
                try:
                    src = open(af, "r", encoding="utf-8").read()
                    aname = fname.replace("_agent.py", "").replace("_", " ").title().replace(" ", "")
                    desc = ""
                    for line in src.splitlines():
                        if '"description"' in line or "'description'" in line:
                            desc = line.split(":", 1)[-1].strip().strip('",').strip("',")[:200]
                            break
                    agent_sources.append({"filename": fname, "name": aname, "description": desc, "source": src})
                except Exception:
                    pass

        data_dir = os.path.join(base, ".brainstem_data")
        if os.path.isdir(data_dir):
            add_tree(data_dir, ".brainstem_data")

        # Config files to include in the egg. soul.md lives at the engine
        # root (user-editable persona). .swarms.json and .agents_disabled.json
        # live in the workspace (~/.brainstem/*) or agents/ respectively.
        soul_text = ""
        config_files = [
            ("soul.md",              os.path.join(base, "soul.md")),
            ("swarms.json",          _SWARMS_FILE),
            (".agents_disabled.json", _DISABLED_FILE),
        ]
        for arc_name, full in config_files:
            if os.path.isfile(full):
                zf.write(full, arcname=arc_name)
                sz = os.path.getsize(full)
                files_added.append({"arc": arc_name, "sha256": sha256_file(full), "bytes": sz})
                if arc_name == "soul.md":
                    soul_text = open(full, "r", encoding="utf-8").read()

        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        sdata = _read_swarms()

        twin_bundle = {
            "schema": "rapp-twin/1.0",
            "handle": "@digitaltwin",
            "cloud_id": "egg-" + hashlib.sha256(now.encode()).hexdigest()[:16],
            "origin": "brainstem-egg",
            "exported_at": now,
            "soul": soul_text,
            "swarm_configs": sdata.get("swarms", {}),
            "active_swarms": sdata.get("active", []),
            "swarms": [{
                "schema": "rapp-swarm/1.0",
                "swarm_guid": hashlib.sha256(("egg-swarm-" + now).encode()).hexdigest()[:36],
                "name": "Brainstem Agents",
                "purpose": "All agents from the exported brainstem",
                "soul": soul_text,
                "created_at": now,
                "agents": agent_sources,
            }],
        }
        zf.writestr("digitaltwin.json", json.dumps(twin_bundle, indent=2))

        manifest = {
            "schema": "rapp-egg/1.0",
            "egg_type": "brainstem",
            "egg_version": 2,
            "created_at": now,
            "host": os.uname().nodename if hasattr(os, "uname") else "unknown",
            "brainstem_version": VERSION,
            "portable": True,
            "stats": {
                "agent_count": len(agent_sources),
                "file_count": len(files_added),
                "total_bytes": sum(f["bytes"] for f in files_added),
            },
            "files": files_added,
        }
        zf.writestr("egg-manifest.json", json.dumps(manifest, indent=2, sort_keys=True))

    buf.seek(0)
    from flask import send_file
    return send_file(buf, mimetype="application/zip", as_attachment=True,
                     download_name="digitaltwin.rappid.egg")


@app.route("/api/egg/import", methods=["POST"])
def api_egg_import():
    """Unpack a .egg — overlay onto this brainstem instance."""
    import zipfile, io

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    f = request.files["file"]
    buf = io.BytesIO(f.read())

    try:
        with zipfile.ZipFile(buf, "r") as zf:
            names = zf.namelist()
            if "egg-manifest.json" not in names:
                return jsonify({"error": "Not a valid .egg — missing egg-manifest.json"}), 400

            manifest = json.loads(zf.read("egg-manifest.json"))
            base = _BRAINSTEM_DIR
            restored = []

            for entry in names:
                if entry == "egg-manifest.json":
                    continue
                if entry.endswith("/"):
                    continue

                if entry.startswith("agents/"):
                    dest = os.path.join(base, "agents", entry[len("agents/"):])
                elif entry.startswith(".brainstem_data/"):
                    dest = os.path.join(base, entry)
                elif entry == "soul.md":
                    dest = os.path.join(base, entry)
                elif entry in ("swarms.json", ".swarms.json", ".agent_groups.json"):
                    # Any of these variants route to the workspace swarms file.
                    dest = _SWARMS_FILE
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                elif entry == ".agents_disabled.json":
                    dest = _DISABLED_FILE
                else:
                    continue

                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "wb") as out:
                    out.write(zf.read(entry))
                restored.append(entry)

            global _ACTIVE_SWARMS
            _ACTIVE_SWARMS = None
            sdata = _read_swarms()
            _ACTIVE_SWARMS = sdata.get("active", []) or []

        return jsonify({
            "status": "ok",
            "files_restored": len(restored),
            "manifest": manifest,
        })
    except zipfile.BadZipFile:
        return jsonify({"error": "Invalid ZIP / .egg file"}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n🧠 RAPP Brainstem v{VERSION} starting on http://localhost:{PORT}")
    print(f"   Soul:   {SOUL_PATH}")
    print(f"   Agents: {AGENTS_PATH}")
    print(f"   Model:  {MODEL}")
    print(f"   Voice:  {'on' if VOICE_MODE else 'off'} (POST /voice/toggle to change)")
    print(f"   Twin:   {'on' if TWIN_MODE  else 'off'} (POST /twin/toggle to change)")
    print(f"   Auth:   GitHub Copilot API (via gh CLI)\n")
    load_soul()
    load_agents()
    app.run(host="0.0.0.0", port=PORT, debug=False)
