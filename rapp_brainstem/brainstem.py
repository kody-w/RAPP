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

SOUL_PATH   = os.getenv("SOUL_PATH",   os.path.join(os.path.dirname(__file__), "soul.md"))
AGENTS_PATH = os.getenv("AGENTS_PATH", os.path.join(os.path.dirname(__file__), "agents"))
MODEL       = os.getenv("GITHUB_MODEL", "gpt-4o")
PORT        = int(os.getenv("PORT", 7071))
VOICE_MODE  = os.getenv("VOICE_MODE", "false").lower() == "true"
# Twin mode drives the digital-twin side panel via |||TWIN|||. On by default
# (the twin is the flagship post-v1 addition). Set TWIN_MODE=false to disable
# the system-prompt instruction + the twin_response field on /chat. Toggle
# live via POST /twin/toggle.
TWIN_MODE   = os.getenv("TWIN_MODE", "true").lower() == "true"
VOICE_ZIP_PW = os.getenv("VOICE_ZIP_PASSWORD", "").encode() or None

_version_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "VERSION")
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

def load_agents():
    agents = {}
    pattern = os.path.join(AGENTS_PATH, "*_agent.py")
    files = glob.glob(pattern)
    disabled = _read_disabled()

    for filepath in files:
        filename = os.path.basename(filepath)
        if filename in disabled:
            print(f"[brainstem] Agent skipped (disabled): {filename}")
            continue
        loaded = _load_agent_from_file(filepath)
        for name, instance in loaded.items():
            agents[name] = instance
            print(f"[brainstem] Agent loaded: {name}")

    print(f"[brainstem] {len(agents)} agent(s) ready, {len(disabled)} disabled.")
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


def run_tool_calls(tool_calls, agents, session_id=None):
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
    return results, logs

# ── /chat endpoint ────────────────────────────────────────────────────────────

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    user_input = data.get("user_input", "").strip()
    history    = data.get("conversation_history", [])
    session_id = data.get("session_id") or str(uuid.uuid4())

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
                "<action kind=\"send|prompt|open|toggle|highlight\" target=\"...\" label=\"...\">body</action> "
                "offers the user a one-click UI favor (send text, prefill input, open a panel, "
                "toggle a feature like voice/cards/pills/hand-mode, or highlight a loaded card)."
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
                tool_results, logs = run_tool_calls(msg["tool_calls"], agents, session_id=session_id)
                all_logs.extend(logs)
                messages.extend(tool_results)
            else:
                break

        reply = msg.get("content") or ""
        
        result = {
            "response": reply,
            "session_id": session_id,
            "agent_logs": "\n".join(all_logs),
            "voice_mode": VOICE_MODE,
            "twin_mode":  TWIN_MODE,
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
            result["exchange_response"] = resp.text[:500]
        except Exception as e:
            result["exchange_error"] = str(e)

    return jsonify(result)

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
