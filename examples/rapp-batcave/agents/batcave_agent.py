"""BatcaveAgent — participate in the RAPP Batcave (the private cubby neighborhood).

The batcave (`kody-w/rapp-batcave`, PRIVATE) is a standalone collaborator-gated
neighborhood in the private-workspace pattern. Its planted quirk is the
**cubby**: each member's isolated housing for their FULL rapp estate — agents
(incl. factory agents / industries), organs, senses, rapplications, whole
neighborhoods, eggs — the same environment as their on-device brainstem,
smashed into a directory the crew can browse and learn from. Contract:
`specs/CUBBY_PROTOCOL.md` in the batcave repo.

What this single file gives the LLM:

  mount          clone/refresh the batcave at ~/.brainstem/neighborhoods/rapp-batcave/clone
  join           create cubbies/<you>/ (+ roster entries) — idempotent
  browse         list everyone's cubbies + what they're cooking (offline from cache)
  stash          put a file (agent / egg / note) in YOUR cubby (secrets refused)
  load           stream a cubby's agents/ into a local brainstem's agents/ —
                 registered in the host repo's .git/info/exclude so they run
                 like any agent but can NEVER be committed to the grail repo
  unload         remove streamed agents cleanly (loadout-tracked)
  show_and_tell  post a signed rapp-batcave-event/1.0 + a markdown artifact
  sync           pull + report what's new since your last look
  branch         start a personal branch cubby/<you>/<topic> (never must merge)
  invite         emit (dry-run) or run the gh command adding a collaborator
  status         identity + mount + loadout summary
  protocol/help  the rules

Auth rides the operator's gh CLI (the same GitHub account that holds
collaborator access — local brainstems and kited vTwins alike, Art. XLVII).
Local-first per ANTIPATTERNS §5: everything except mount/sync/push works from
the cached clone; offline degrades to cache, never crashes.

MIT © Kody Wildfeuer
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone

try:
    from agents.basic_agent import BasicAgent  # type: ignore
except ImportError:
    try:
        from basic_agent import BasicAgent  # type: ignore
    except ImportError:
        class BasicAgent:  # minimal shim so the file runs standalone
            def __init__(self, name="Agent", metadata=None):
                self.name = name
                self.metadata = metadata or {}

__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@kody-w/batcave",
    "version": "1.0.0",
    "display_name": "BatcaveAgent",
    "description": ("Participate in the RAPP Batcave private cubby "
                    "neighborhood: join, browse cubbies, stash files, stream "
                    "agents into a local brainstem with zero grail-repo "
                    "commit risk, post signed show-and-tell events."),
    "author": "Kody Wildfeuer",
    "tags": ["batcave", "cubby", "neighborhood", "private", "workspace",
             "streaming", "show-and-tell"],
    "category": "integrations",
    "quality_tier": "community",
    "requires_env": [],
    "dependencies": ["@rapp/basic_agent"],
}

DEFAULT_REPO = os.environ.get("BATCAVE_REPO", "kody-w/rapp-batcave")
NEIGHBORHOOD_RAPPID = ("rappid:@kody-w/rapp-batcave:"
                       + hashlib.sha256(b"kody-w/rapp-batcave").hexdigest())
CACHE_SLUG = "rapp-batcave"
EVENT_SCHEMA = "rapp-batcave-event/1.0"
EVENT_KINDS = ("hello", "show-and-tell", "ask", "reply", "fyi", "leave")
CUBBY_ANATOMY = ("agents", "organs", "senses", "rapplications",
                 "neighborhoods", "eggs", "show-and-tell")

# Kernel-shipped agents (rapp_brainstem/CLAUDE.md) — `load` NEVER touches these.
KERNEL_AGENTS = {
    "basic_agent.py", "context_memory_agent.py", "manage_memory_agent.py",
    "learn_new_agent.py", "swarm_factory_agent.py", "hacker_news_agent.py",
}

# Secret-shaped names `stash` refuses outright (PUBLIC_PRIVATE_BOUNDARY §1.8.2).
_SECRET_NAME_RE = re.compile(
    r"(^\.env($|\.)|token|secret|credential|password|apikey|api_key|"
    r"\.pem$|\.key$|\.p12$|\.pfx$|\.ppk$|\.keystore$|\.jks$|"
    r"^id_rsa|^id_dsa|^id_ecdsa|^id_ed25519|"
    r"^\.lineage_key$|^\.copilot|^\.npmrc$|^\.netrc$|private-estate-secret)",
    re.IGNORECASE)

# GitHub login shape — gate any handle used to build a filesystem path.
_HANDLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$")
# Single-file agent filename shape — gate anything load/unload touches.
_AGENT_FILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*_agent\.py$")

try:
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric.utils import (
        decode_dss_signature, encode_dss_signature)
    _HAS_CRYPTO = True
except Exception:
    _HAS_CRYPTO = False


# ---------------------------------------------------------------- helpers

def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _ub64u(s: str) -> bytes:
    s = s.replace("-", "+").replace("_", "/")
    return base64.b64decode(s + "=" * (-len(s) % 4))


def _canonical(obj) -> bytes:
    # recursively key-sorted, compact, UTF-8 — the commons' stableStringify
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _read_json(path: str, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return default


def _write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=120)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timed out"


def _slugify(text: str, fallback: str = "post") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s[:48] or fallback)


# ---------------------------------------------------------------- identity + signing

def _load_or_mint_keys(keys_dir: str):
    """ECDSA P-256 keypair under <home>/.brainstem/keys/ (plant_household
    pattern). Returns (priv, jwk) or (None, None) without `cryptography`."""
    if not _HAS_CRYPTO:
        return None, None
    pem_path = os.path.join(keys_dir, "ecdsa-p256-private.pem")
    jwk_path = os.path.join(keys_dir, "ecdsa-p256-public.jwk")
    if os.path.exists(pem_path):
        try:
            with open(pem_path, "rb") as f:
                priv = serialization.load_pem_private_key(f.read(), password=None)
            jwk = _read_json(jwk_path) or _jwk_from_priv(priv)
            return priv, jwk
        except Exception:
            pass
    priv = ec.generate_private_key(ec.SECP256R1())
    os.makedirs(keys_dir, exist_ok=True)
    pem = priv.private_bytes(serialization.Encoding.PEM,
                             serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption())
    with open(pem_path, "wb") as f:
        f.write(pem)
    os.chmod(pem_path, 0o600)
    jwk = _jwk_from_priv(priv)
    _write_json(jwk_path, jwk)
    return priv, jwk


def _jwk_from_priv(priv) -> dict:
    nums = priv.public_key().public_numbers()
    return {"kty": "EC", "crv": "P-256",
            "x": _b64u(nums.x.to_bytes(32, "big")),
            "y": _b64u(nums.y.to_bytes(32, "big"))}


def _fingerprint(jwk: dict) -> str:
    return hashlib.sha256(_canonical(jwk)).hexdigest()


def _sign(priv, data: bytes) -> str:
    der = priv.sign(data, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    return _b64u(r.to_bytes(32, "big") + s.to_bytes(32, "big"))  # IEEE-P1363


def _verify_event(ev: dict) -> bool:
    """Verify a rapp-batcave-event/1.0 signature against its embedded JWK."""
    if not _HAS_CRYPTO:
        raise RuntimeError("verification needs the `cryptography` package")
    try:
        jwk = ev["pub"]
        x = int.from_bytes(_ub64u(jwk["x"]), "big")
        y = int.from_bytes(_ub64u(jwk["y"]), "big")
        pub = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
        sig = _ub64u(ev["sig"])
        der = encode_dss_signature(int.from_bytes(sig[:32], "big"),
                                   int.from_bytes(sig[32:], "big"))
        no_sig = {k: v for k, v in ev.items() if k != "sig"}
        pub.verify(der, _canonical(no_sig), ec.ECDSA(hashes.SHA256()))
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- the agent

class BatcaveAgent(BasicAgent):
    def __init__(self):
        self.name = "BatcaveAgent"
        self.metadata = {
            "name": self.name,
            "description": (
                "Talk to the RAPP Batcave — the private cubby neighborhood "
                "(kody-w/rapp-batcave). Join to get your own cubby (housing "
                "for your full rapp estate), browse everyone's cubbies, "
                "stash agents/eggs in yours, STREAM agents from any cubby "
                "into the local brainstem with zero commit risk "
                "(.git/info/exclude), post signed show-and-tell events, and "
                "sync what's new."),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["protocol", "help", "status", "mount",
                                 "join", "browse", "stash", "show_and_tell",
                                 "load", "unload", "sync", "branch",
                                 "invite"],
                        "description": "what to do (see help)",
                    },
                    "cubby": {"type": "string",
                              "description": "target cubby's GitHub handle (default: your own; load defaults to kody-w when you have no cubby)"},
                    "path": {"type": "string",
                             "description": "stash: local file to put in your cubby"},
                    "title": {"type": "string",
                              "description": "show_and_tell: post title"},
                    "text": {"type": "string",
                             "description": "show_and_tell: post body"},
                    "kind": {"type": "string",
                             "description": "show_and_tell event kind (default show-and-tell)"},
                    "in_reply_to": {"type": "string",
                                    "description": "show_and_tell: event filename this replies to"},
                    "topic": {"type": "string",
                              "description": "branch: topic suffix for cubby/<you>/<topic>"},
                    "github_login": {"type": "string",
                                     "description": "invite: collaborator to add"},
                    "what_im_cooking": {"type": "string",
                                        "description": "join: one-liner for the gallery"},
                    "confirm": {"type": "boolean",
                                "description": "invite: actually run it (default dry-run)"},
                    "push": {"type": "boolean",
                             "description": "join/stash/show_and_tell: commit+push to the batcave (default true in real mode)"},
                },
                "required": ["action"],
            },
        }
        super().__init__(self.name, self.metadata)

    # ---- context resolution -------------------------------------------
    def _ctx(self, kwargs: dict) -> dict:
        home = kwargs.get("_home_dir") or os.path.expanduser("~")
        cache = os.path.join(home, ".brainstem", "neighborhoods", CACHE_SLUG)
        repo_dir = kwargs.get("_repo_dir") or os.path.join(cache, "clone")
        offline = bool(kwargs.get("_repo_dir"))  # test hook ⇒ no git/gh network
        rec = _read_json(os.path.join(home, ".brainstem", "rappid.json")) or {}
        rappid = rec.get("rappid") or "rappid:unregistered"
        handle = kwargs.get("_handle")
        if not handle and not offline:
            rc, out, _ = _run(["gh", "api", "user", "--jq", ".login"])
            handle = out if rc == 0 and out else None
        return {"home": home, "cache": cache, "repo_dir": repo_dir,
                "offline": offline, "rappid": rappid, "handle": handle,
                "keys_dir": os.path.join(home, ".brainstem", "keys"),
                "loadout_path": os.path.join(cache, "loadout.json"),
                "sync_path": os.path.join(cache, "last-sync.json"),
                "repo": kwargs.get("repo") or DEFAULT_REPO}

    def _env(self, action: str, status: str, **fields) -> str:
        return json.dumps({"schema": "rapp-batcave-result/1.0",
                           "action": action, "status": status, **fields},
                          indent=2, ensure_ascii=False)

    def _commit_push(self, ctx: dict, message: str, do_push: bool) -> dict:
        """Commit + push the clone in real mode; report planned commands in
        offline/test mode. Never raises."""
        if ctx["offline"] or not do_push:
            return {"pushed": False,
                    "planned_commands": [
                        f"git -C {ctx['repo_dir']} add -A",
                        f"git -C {ctx['repo_dir']} commit -m '{message}'",
                        f"git -C {ctx['repo_dir']} push"]}
        rd = ctx["repo_dir"]
        _run(["git", "-C", rd, "add", "-A"])
        rc_c, _, err_c = _run(["git", "-C", rd, "commit", "-m", message])
        if rc_c != 0 and "nothing to commit" not in err_c.lower():
            return {"pushed": False, "error": f"commit failed: {err_c[:200]}"}
        rc_p, _, err_p = _run(["git", "-C", rd, "push"])
        if rc_p != 0:
            return {"pushed": False,
                    "error": (f"push failed ({err_p[:200]}). Are you a "
                              f"collaborator on {ctx['repo']}? Ask the "
                              "operator for access (out-of-band).")}
        return {"pushed": True}

    # ---- perform -------------------------------------------------------
    def perform(self, **kwargs) -> str:
        action = (kwargs.get("action") or "help").lower()

        if action == "protocol":
            return (
                "The RAPP Batcave — private cubby neighborhood\n"
                f"  identity : {NEIGHBORHOOD_RAPPID}\n"
                f"  door     : https://github.com/{DEFAULT_REPO} (PRIVATE — "
                "membership is collaborator status; kited vTwins ride the "
                "same signed-in GitHub account)\n"
                "  quirk    : the cubby — isolated housing for one member's "
                "FULL rapp estate (agents, organs, senses, rapplications, "
                "whole neighborhoods, eggs). specs/CUBBY_PROTOCOL.md\n"
                "  rules    : 1) write only in your own cubby (+ append-only "
                "zones)  2) bones, not substance — no PII/secrets in the "
                "repo  3) personal branches are cubby/<you>/<topic> and "
                "never must merge  4) sign your events  5) show the crew "
                "what you're cooking\n"
                "  streaming: `load` copies cubby agents into your "
                "brainstem's agents/ and registers them in .git/info/exclude "
                "— they run like any agent but can never be committed to "
                "the grail repo.\n"
                "  payphone : no public front door — outsiders 404. Kited "
                "vTwins dial the rappid at "
                "https://kody-w.github.io/RAPP/pages/payphone.html with "
                "their own GitHub auth (collaborator access = dial tone).\n"
                "  join     : out-of-band — ask the operator for "
                "collaborator access, then action=join."
            )

        if action == "help" or action not in (
                "status", "mount", "join", "browse", "stash", "show_and_tell",
                "load", "unload", "sync", "branch", "invite"):
            return (
                "BatcaveAgent — your cubby in the private batcave neighborhood.\n"
                "  action=status                       identity + mount + loadout\n"
                "  action=mount                        clone/refresh the batcave locally\n"
                "  action=join  what_im_cooking='...'  create your cubby (idempotent)\n"
                "  action=browse                       everyone's cubbies + what's cooking\n"
                "  action=stash path=/file             put a file in YOUR cubby\n"
                "  action=load [cubby=kody-w]          stream cubby agents into this brainstem\n"
                "                                      (git-invisible via .git/info/exclude)\n"
                "  action=unload                       remove streamed agents cleanly\n"
                "  action=show_and_tell title='...' text='...'   post to the room (signed)\n"
                "  action=sync                         pull + what's new since last look\n"
                "  action=branch topic=wip             start cubby/<you>/<topic>\n"
                "  action=invite github_login=bob      add a collaborator (dry-run default)\n"
                "  action=protocol                     the rules\n"
                "Contract: specs/CUBBY_PROTOCOL.md in the batcave repo."
            )

        ctx = self._ctx(kwargs)
        mounted = os.path.isdir(ctx["repo_dir"]) and \
            os.path.exists(os.path.join(ctx["repo_dir"], "neighborhood.json"))

        # ---- status ----
        if action == "status":
            loadout = _read_json(ctx["loadout_path"]) or {}
            cubby_path = (os.path.join(ctx["repo_dir"], "cubbies", ctx["handle"])
                          if ctx["handle"] else None)
            return self._env(action, "success",
                             rappid=ctx["rappid"],
                             github_handle=ctx["handle"],
                             repo=ctx["repo"],
                             mounted=mounted,
                             clone=ctx["repo_dir"],
                             has_cubby=bool(cubby_path and os.path.isdir(cubby_path)),
                             streamed_agents=[e["file"] for e in
                                              loadout.get("loaded", [])])

        # ---- mount ----
        if action == "mount":
            if ctx["offline"]:
                return self._env(action, "success", mounted=mounted,
                                 clone=ctx["repo_dir"], note="test/offline mode")
            if mounted:
                rc, out, err = _run(["git", "-C", ctx["repo_dir"], "pull",
                                     "--ff-only"])
                if rc != 0:
                    return self._env(action, "degraded", mounted=True,
                                     clone=ctx["repo_dir"],
                                     note=(f"pull failed ({err[:160]}) — "
                                           "serving the cached clone "
                                           "(local-first; reconnect later)"))
                return self._env(action, "success", mounted=True,
                                 clone=ctx["repo_dir"], refreshed=True)
            os.makedirs(os.path.dirname(ctx["repo_dir"]), exist_ok=True)
            rc, out, err = _run(["gh", "repo", "clone", ctx["repo"],
                                 ctx["repo_dir"]])
            if rc != 0:
                return self._env(action, "error",
                                 error=(f"clone failed: {err[:240]}. Need "
                                        f"collaborator access on {ctx['repo']} "
                                        "+ gh auth login."))
            return self._env(action, "success", mounted=True,
                             clone=ctx["repo_dir"])

        if not mounted:
            return self._env(action, "error",
                             error=("batcave not mounted — run action=mount "
                                    "first (clones the private repo via your "
                                    "gh auth)."))
        rd = ctx["repo_dir"]

        # ---- browse ----
        if action == "browse":
            cubbies = []
            cubby_root = os.path.join(rd, "cubbies")
            for entry in sorted(os.listdir(cubby_root) if os.path.isdir(cubby_root) else []):
                if entry.startswith(("_", ".")):
                    continue
                c = _read_json(os.path.join(cubby_root, entry, "cubby.json")) or {}
                tells = sorted((os.listdir(os.path.join(cubby_root, entry, "show-and-tell"))
                                if os.path.isdir(os.path.join(cubby_root, entry, "show-and-tell"))
                                else []))
                agents = sorted(f for f in
                                (os.listdir(os.path.join(cubby_root, entry, "agents"))
                                 if os.path.isdir(os.path.join(cubby_root, entry, "agents"))
                                 else []) if f.endswith("_agent.py"))
                cubbies.append({"github_login": c.get("github_login", entry),
                                "what_im_cooking": c.get("what_im_cooking", ""),
                                "agents": agents,
                                "latest_show_and_tell": tells[-1] if tells else None})
            return self._env(action, "success", cubbies=cubbies,
                             count=len(cubbies))

        # Everything below needs to know who you are.
        if not ctx["handle"]:
            return self._env(action, "error",
                             error=("could not resolve your GitHub handle — "
                                    "run `gh auth login` (the batcave is "
                                    "collaborator-gated) or pass _handle."))
        me = ctx["handle"]
        if not _HANDLE_RE.match(me):
            return self._env(action, "error",
                             error=f"refusing unsafe handle: {me!r}")
        my_cubby = os.path.join(rd, "cubbies", me)

        # ---- join ----
        if action == "join":
            existed = os.path.isfile(os.path.join(my_cubby, "cubby.json"))
            for d in CUBBY_ANATOMY:
                os.makedirs(os.path.join(my_cubby, d), exist_ok=True)
            if not existed:
                cooking = kwargs.get("what_im_cooking", "just moved in")
                _write_json(os.path.join(my_cubby, "cubby.json"), {
                    "schema": "rapp-batcave-cubby/1.0",
                    "github_login": me,
                    "rappid": ctx["rappid"],
                    "display_name": me,
                    "what_im_cooking": cooking,
                    "created_at": _now(),
                    "estate": {"anatomy": list(CUBBY_ANATOMY)},
                    "streamable": {"agents": True},
                })
                tmpl = os.path.join(rd, "cubbies", "_template", "front_door.md")
                fd = os.path.join(my_cubby, "front_door.md")
                if os.path.exists(tmpl):
                    shutil.copy2(tmpl, fd)
                else:
                    with open(fd, "w") as f:
                        f.write(f"# {me} — front door\n\n## What I'm cooking\n\n- {cooking}\n")
            # roster entries — additive, (github_login)-keyed, idempotent
            members = _read_json(os.path.join(rd, "members.json")) or \
                {"schema": "rapp-neighborhood-members/1.0", "members": []}
            if not any(m.get("github_login") == me for m in members["members"]):
                members["members"].append({
                    "github_login": me, "rappid": ctx["rappid"],
                    "role": "member", "capabilities": ["cubby"],
                    "joined_at": _now(), "via": "cubby-join"})
                members["synced_at"] = _now()
                _write_json(os.path.join(rd, "members.json"), members)
            idx = _read_json(os.path.join(rd, "cubbies", "index.json")) or \
                {"schema": "rapp-batcave-cubbies/1.0", "cubbies": []}
            if not any(c.get("github_login") == me for c in idx["cubbies"]):
                cj = _read_json(os.path.join(my_cubby, "cubby.json")) or {}
                idx["cubbies"].append({"github_login": me,
                                       "what_im_cooking": cj.get("what_im_cooking", ""),
                                       "rappid": ctx["rappid"]})
                idx["updated_at"] = _now()
                _write_json(os.path.join(rd, "cubbies", "index.json"), idx)
            git = self._commit_push(ctx, f"cubby: {me} joins the batcave",
                                    kwargs.get("push", True))
            return self._env(action,
                             "already_joined" if existed else "success",
                             cubby=f"cubbies/{me}/", **git)

        # ---- stash ----
        if action == "stash":
            src = kwargs.get("path")
            if not src or not os.path.isfile(src):
                return self._env(action, "error",
                                 error="pass path=<existing local file>")
            target_cubby = kwargs.get("cubby") or me
            if target_cubby != me:
                return self._env(action, "refused",
                                 error=(f"cubbies are isolated — you write "
                                        f"only in cubbies/{me}/. To offer "
                                        f"something to @{target_cubby}, open "
                                        "a PR they merge."))
            base = os.path.basename(src)  # strip any path components
            if _SECRET_NAME_RE.search(base):
                return self._env(action, "refused",
                                 error=(f"'{base}' is secret-shaped — bones, "
                                        "not substance (PUBLIC_PRIVATE_"
                                        "BOUNDARY §1.8.2). Secrets stay on "
                                        "your device."))
            if os.path.getsize(src) > 5 * 1024 * 1024:
                return self._env(action, "refused",
                                 error="5 MB cap — the batcave stays lean; "
                                       "big artifacts ride eggs or releases.")
            if base.endswith("_agent.py"):
                sub = "agents"
            elif base.endswith("_organ.py"):
                sub = "organs"
            elif base.endswith(".egg"):
                sub = "eggs"
            else:
                sub = "show-and-tell"
            dst = os.path.join(my_cubby, sub, base)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            git = self._commit_push(ctx, f"cubby({me}): stash {sub}/{base}",
                                    kwargs.get("push", True))
            return self._env(action, "success",
                             stashed=f"cubbies/{me}/{sub}/{base}",
                             sha256=_sha256_file(dst), **git)

        # ---- show_and_tell ----
        if action == "show_and_tell":
            title = kwargs.get("title") or "show and tell"
            text = kwargs.get("text") or ""
            kind = kwargs.get("kind") or "show-and-tell"
            if kind not in EVENT_KINDS:
                kind = "show-and-tell"
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            slug = _slugify(title)
            artifact_rel = f"cubbies/{me}/show-and-tell/{date}-{slug}.md"
            artifact = os.path.join(rd, artifact_rel)
            os.makedirs(os.path.dirname(artifact), exist_ok=True)
            with open(artifact, "w") as f:
                f.write(f"# {title}\n\n*{_now()} — @{me}*\n\n{text}\n")
            ev = {"schema": EVENT_SCHEMA, "kind": kind, "from": ctx["rappid"],
                  "ts": _now(), "cubby": me,
                  "body": {"title": title, "text": text[:4096],
                           "artifact": artifact_rel},
                  "in_reply_to": kwargs.get("in_reply_to")}
            extra = {}
            # Filename prefix = sha256(from-rappid)[:16] — deterministic in
            # both the signed and signing-intent paths (events/SCHEMA.md §2).
            fp = hashlib.sha256(ctx["rappid"].encode()).hexdigest()[:16]
            if _HAS_CRYPTO:
                priv, jwk = _load_or_mint_keys(ctx["keys_dir"])
                ev["pub"] = jwk
                ev["sig"] = _sign(priv, _canonical(ev))
            else:
                extra["signing_intent"] = {
                    "alg": "ecdsa-p256",
                    "canonical_fields_order": "sorted",
                    "note": ("`cryptography` not installed — a WebCrypto "
                             "host (vBrainstem) fills pub/sig; unsigned "
                             "drafts never federate beyond the repo."),
                }
            ts_compact = ev["ts"].replace("-", "").replace(":", "")
            ev_rel = f"events/{fp}-{ts_compact}.json"
            _write_json(os.path.join(rd, ev_rel), ev)
            git = self._commit_push(ctx, f"show-and-tell({me}): {title[:50]}",
                                    kwargs.get("push", True))
            return self._env(action, "success", artifact=artifact_rel,
                             event=ev_rel, signed=_HAS_CRYPTO, **extra, **git)

        # ---- load ----
        if action == "load":
            def _has_agents(handle):
                d = os.path.join(rd, "cubbies", handle, "agents")
                return os.path.isdir(d) and any(
                    f.endswith("_agent.py") for f in os.listdir(d))

            src_cubby = kwargs.get("cubby")
            if not src_cubby:
                # default to your own cubby if it has agents; else the founder's
                src_cubby = me if _has_agents(me) else "kody-w"
            if not _HANDLE_RE.match(src_cubby):
                return self._env(action, "error",
                                 error=f"refusing unsafe cubby name: {src_cubby!r}")
            src_agents = os.path.join(rd, "cubbies", src_cubby, "agents")
            if not os.path.isdir(src_agents):
                return self._env(action, "error",
                                 error=f"no agents/ in cubbies/{src_cubby}/")
            bs_dir = kwargs.get("_brainstem_dir") or os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))
            target = os.path.join(bs_dir, "agents")
            os.makedirs(target, exist_ok=True)
            loadout = _read_json(ctx["loadout_path"]) or \
                {"schema": "rapp-batcave-loadout/1.0", "loaded": []}
            known = {e["file"] for e in loadout["loaded"]}
            loaded, skipped = [], []
            for fn in sorted(os.listdir(src_agents)):
                if not _AGENT_FILE_RE.match(fn):
                    continue
                if fn in KERNEL_AGENTS:
                    skipped.append({"file": fn, "why": "kernel agent — sacred, never overwritten"})
                    continue
                dst = os.path.join(target, fn)
                if os.path.exists(dst) and fn not in known and \
                        _sha256_file(dst) != _sha256_file(os.path.join(src_agents, fn)):
                    skipped.append({"file": fn,
                                    "why": "exists locally and isn't batcave-streamed — won't overwrite your copy"})
                    continue
                shutil.copy2(os.path.join(src_agents, fn), dst)
                sha = _sha256_file(dst)
                loadout["loaded"] = [e for e in loadout["loaded"]
                                     if e["file"] != fn] + [{
                    "file": fn, "sha256": sha, "from_cubby": src_cubby,
                    "loaded_at": _now(), "target": target}]
                loaded.append(fn)
            # git-invisibility: register streamed files in .git/info/exclude
            excluded = self._register_excludes(bs_dir, target, loaded)
            loadout["updated_at"] = _now()
            _write_json(ctx["loadout_path"], loadout)
            return self._env(action, "success", from_cubby=src_cubby,
                             loaded=loaded, skipped=skipped,
                             git_excluded=excluded, target=target,
                             loadout=ctx["loadout_path"],
                             note=("streamed agents are live in agents/ but "
                                   "invisible to git — zero grail-repo "
                                   "commit risk. Brainstem reloads agents "
                                   "every request; no restart needed."))

        # ---- unload ----
        if action == "unload":
            loadout = _read_json(ctx["loadout_path"]) or {"loaded": []}
            bs_dir = kwargs.get("_brainstem_dir")
            removed, kept = [], []
            remaining = []
            for e in loadout.get("loaded", []):
                target = e.get("target", "")
                fn = e.get("file", "")
                # Never delete a kernel agent or anything not agent-shaped,
                # even if loadout.json was hand-edited or corrupted.
                if fn in KERNEL_AGENTS or not _AGENT_FILE_RE.match(fn):
                    remaining.append(e)
                    kept.append(f"{fn} (refused — sacred/invalid)")
                    continue
                if bs_dir and os.path.normpath(target) != \
                        os.path.normpath(os.path.join(bs_dir, "agents")):
                    remaining.append(e)
                    kept.append(e["file"])
                    continue
                p = os.path.join(target, fn)
                if os.path.basename(p) == fn and os.path.exists(p):
                    os.remove(p)
                removed.append(fn)
                self._unregister_exclude(os.path.dirname(target), target, fn)
            loadout["loaded"] = remaining
            loadout["updated_at"] = _now()
            _write_json(ctx["loadout_path"], loadout)
            return self._env(action, "success", removed=removed, kept=kept)

        # ---- sync ----
        if action == "sync":
            pulled = {}
            if not ctx["offline"]:
                rc, _, err = _run(["git", "-C", rd, "pull", "--ff-only"])
                pulled = {"pulled": rc == 0}
                if rc != 0:
                    pulled["note"] = (f"pull failed ({err[:120]}) — comparing "
                                      "against the cached clone (local-first)")
            snapshot = self._snapshot(rd)
            prev = _read_json(ctx["sync_path"]) or {}
            news = {
                "new_cubbies": sorted(set(snapshot["cubbies"]) -
                                      set(prev.get("cubbies", []))),
                "new_show_and_tells": sorted(set(snapshot["show_and_tells"]) -
                                             set(prev.get("show_and_tells", []))),
                "new_events": sorted(set(snapshot["events"]) -
                                     set(prev.get("events", []))),
                "new_agents": sorted(set(snapshot["agents"]) -
                                     set(prev.get("agents", []))),
            }
            _write_json(ctx["sync_path"], snapshot)
            return self._env(action, "success", **pulled, **news,
                             first_sync=not bool(prev))

        # ---- branch ----
        if action == "branch":
            topic = _slugify(kwargs.get("topic") or "wip", "wip")
            branch = f"cubby/{me}/{topic}"
            if ctx["offline"]:
                return self._env(action, "dry_run", branch=branch,
                                 planned_commands=[
                                     f"git -C {rd} checkout -b {branch}",
                                     f"git -C {rd} push -u origin {branch}"])
            rc, _, err = _run(["git", "-C", rd, "checkout", "-b", branch])
            if rc != 0:
                return self._env(action, "error", error=err[:200])
            _run(["git", "-C", rd, "push", "-u", "origin", branch])
            return self._env(action, "success", branch=branch,
                             note=("yours — never required to merge to "
                                   "main. `git checkout main` to get back "
                                   "to the shared truth."))

        # ---- invite ----
        if action == "invite":
            login = kwargs.get("github_login")
            if not login:
                return self._env(action, "error",
                                 error="pass github_login=<who to invite>")
            cmd = ["gh", "api", "-X", "PUT",
                   f"repos/{ctx['repo']}/collaborators/{login}",
                   "--field", "permission=push"]
            if not kwargs.get("confirm"):
                return self._env(action, "dry_run",
                                 command=" ".join(cmd),
                                 note=("operator-mediated: re-run with "
                                       "confirm=true to actually invite "
                                       f"@{login}. They accept the email, "
                                       "clone, and action=join."))
            rc, out, err = _run(cmd)
            if rc != 0:
                return self._env(action, "error", error=err[:240])
            return self._env(action, "success", invited=login,
                             note=f"@{login} can now clone {ctx['repo']} and join.")

        return self._env(action, "error", error="unreachable")

    # ---- git-invisibility helpers --------------------------------------
    @staticmethod
    def _git_toplevel(start_dir: str) -> str | None:
        rc, out, _ = _run(["git", "-C", start_dir, "rev-parse",
                           "--show-toplevel"])
        return out if rc == 0 and out else None

    def _register_excludes(self, bs_dir: str, target: str,
                           files: list[str]) -> list[str]:
        top = self._git_toplevel(bs_dir)
        if not top:
            return []
        exclude_path = os.path.join(top, ".git", "info", "exclude")
        os.makedirs(os.path.dirname(exclude_path), exist_ok=True)
        existing = ""
        if os.path.exists(exclude_path):
            with open(exclude_path) as f:
                existing = f.read()
        lines = []
        for fn in files:
            rel = os.path.relpath(os.path.join(target, fn), top)
            if rel not in existing.splitlines():
                lines.append(rel)
        if lines:
            with open(exclude_path, "a") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write("# streamed from the batcave (batcave load) — "
                        "git-invisible by design\n")
                f.write("\n".join(lines) + "\n")
        return lines

    def _unregister_exclude(self, bs_dir: str, target: str, fn: str) -> None:
        top = self._git_toplevel(bs_dir)
        if not top:
            return
        exclude_path = os.path.join(top, ".git", "info", "exclude")
        if not os.path.exists(exclude_path):
            return
        rel = os.path.relpath(os.path.join(target, fn), top)
        with open(exclude_path) as f:
            lines = f.read().splitlines()
        kept = [l for l in lines if l.strip() != rel]
        with open(exclude_path, "w") as f:
            f.write("\n".join(kept) + ("\n" if kept else ""))

    @staticmethod
    def _snapshot(rd: str) -> dict:
        cubbies, tells, agents = [], [], []
        root = os.path.join(rd, "cubbies")
        if os.path.isdir(root):
            for entry in sorted(os.listdir(root)):
                if entry.startswith(("_", ".")):
                    continue
                cubbies.append(entry)
                st = os.path.join(root, entry, "show-and-tell")
                if os.path.isdir(st):
                    tells += [f"{entry}/{f}" for f in sorted(os.listdir(st))
                              if f.endswith(".md")]
                ag = os.path.join(root, entry, "agents")
                if os.path.isdir(ag):
                    agents += [f"{entry}/{f}" for f in sorted(os.listdir(ag))
                               if f.endswith("_agent.py")]
        ev_dir = os.path.join(rd, "events")
        events = [f for f in sorted(os.listdir(ev_dir))
                  if f.endswith(".json")] if os.path.isdir(ev_dir) else []
        return {"cubbies": cubbies, "show_and_tells": tells,
                "agents": agents, "events": events, "taken_at": _now()}


if __name__ == "__main__":
    a = BatcaveAgent()
    print(a.perform(action="protocol"))
    print("\n---\n")
    print(a.perform(action="help"))
