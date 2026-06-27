"""
cave_agent.py — talk to the public RAPP Cave from inside your brainstem.

Drop this into ANY unmodified brainstem's agents/ directory and the LLM gets a
`Cave` tool that gives your brainstem the SAME super-RAR powers a batcave member
has — but PUBLIC (plain git clone over HTTPS, no auth, no collaborator gate):

  • list       — the cubbies in the cave (who parked what)
  • super_rar  — search the super-store: EVERY kind across EVERY cubby
                 (agents, organs, senses, rapplications, neighborhoods, eggs)
  • load       — stream a cubby's agents INTO this brainstem's agents/ and
                 register them in .git/info/exclude → they run but are git-
                 invisible (ZERO commit risk), verified against the RAR sha256
                 pins (refuses tampered/drifted files)
  • sync       — pull the latest cave

It mirrors the batcave god agent's load/super_rar exactly, minus the private
parts: the cave is public, so it shallow-clones https://github.com/kody-w/RAPP
to a local cache and reads cave/ from there. Self-contained, stdlib only.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import shutil
import subprocess

from agents.basic_agent import BasicAgent

CAVE_REPO = "https://github.com/kody-w/RAPP.git"
CACHE = os.path.expanduser("~/.brainstem/.cave_cache/RAPP")
SUPER_RAR_KINDS = {
    "agent": ("agents", "*_agent.py"), "organ": ("organs", "*_organ.py"),
    "sense": ("senses", "*.py"), "rapplication": ("rapplications", "*"),
    "neighborhood": ("neighborhoods", "*"), "egg": ("eggs", "*.egg"),
}
# kernel-shipped agents — load NEVER overwrites these (CONSTITUTION Art. XXXIII)
KERNEL_AGENTS = {"basic_agent.py", "context_memory_agent.py", "manage_memory_agent.py",
                 "learn_new_agent.py", "swarm_factory_agent.py", "hacker_news_agent.py"}
_HANDLE_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{0,38}[A-Za-z0-9])?$")
_AGENT_FILE_RE = re.compile(r"^[A-Za-z0-9._-]+_agent\.py$")


def _sha256_file(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _read_json(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


class CaveAgent(BasicAgent):
    def __init__(self):
        self.name = "Cave"
        self.metadata = {
            "name": self.name,
            "description": (
                "Browse and pull from the PUBLIC RAPP Cave — the open cubby-neighborhood at "
                "kody-w.github.io/RAPP/cave (the public sibling of the private batcave). Gives this "
                "brainstem super-RAR powers with no auth: list the cubbies, search the super-store "
                "(every kind across every cubby), and STREAM a cubby's agents into this brainstem "
                "git-invisibly (zero commit risk, sha256-verified). Use it to find what someone else "
                "built and run it here instantly."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "super_rar", "load", "sync"],
                        "description": (
                            "list = the cave's cubbies; super_rar = search the super-store across all "
                            "cubbies (use 'query'/'kind' to filter); load = stream a cubby's agents into "
                            "THIS brainstem (git-invisible, zero commit risk) — requires 'cubby'; "
                            "sync = pull the latest cave."
                        ),
                    },
                    "cubby": {"type": "string", "description": "for action=load: which cubby's agents to stream (a github login, e.g. 'kody-w')."},
                    "query": {"type": "string", "description": "for action=super_rar: substring to match across the super-store (name/purpose/cubby)."},
                    "kind": {"type": "string", "description": "for action=super_rar: filter to one kind: agent|organ|sense|rapplication|neighborhood|egg."},
                    "verify": {"type": "boolean", "description": "for action=load: verify each streamed file against the RAR sha256 pin and refuse drift. Default true."},
                },
                "required": ["action"],
            },
        }

    # ── cave clone management (public, no auth) ──────────────────────────────
    def _cave_root(self, refresh=False):
        """Return the local path to cave/ inside a public clone of kody-w/RAPP,
        cloning/pulling as needed. Prefers an existing neighborhood clone."""
        for cand in (os.path.expanduser("~/.brainstem/neighborhoods/RAPP"),
                     os.path.expanduser("~/.brainstem/neighborhoods/RAPP/clone")):
            if os.path.isdir(os.path.join(cand, "cave")) and os.path.isdir(os.path.join(cand, ".git")):
                if refresh:
                    subprocess.run(["git", "-C", cand, "pull", "--ff-only", "-q"], check=False)
                # only use it if cave/ is actually present on the checked-out branch
                if os.path.isdir(os.path.join(cand, "cave")):
                    return os.path.join(cand, "cave")
        # fall back to a dedicated shallow cache
        if not os.path.isdir(os.path.join(CACHE, ".git")):
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            shutil.rmtree(CACHE, ignore_errors=True)
            subprocess.run(["git", "clone", "--depth", "1", CACHE if False else CAVE_REPO, CACHE], check=False)
        elif refresh:
            subprocess.run(["git", "-C", CACHE, "pull", "--ff-only", "-q"], check=False)
        root = os.path.join(CACHE, "cave")
        return root if os.path.isdir(root) else None

    def perform(self, **kwargs):
        action = (kwargs.get("action") or "list").strip()
        cave = self._cave_root(refresh=(action == "sync"))
        if not cave:
            return json.dumps({"ok": False, "error": "could not clone the public cave (need git + network).",
                               "repo": CAVE_REPO}, indent=2)

        if action == "sync":
            return json.dumps({"ok": True, "synced": True, "cave": cave}, indent=2)

        if action == "list":
            idx = _read_json(os.path.join(cave, "cubbies", "index.json")) or {}
            cubbies = idx.get("cubbies")
            if not cubbies:
                cdir = os.path.join(cave, "cubbies")
                cubbies = [{"github_login": h} for h in sorted(os.listdir(cdir))
                           if not h.startswith((".", "_")) and os.path.isdir(os.path.join(cdir, h))]
            return json.dumps({"ok": True, "cave": "kody-w.github.io/RAPP/cave",
                               "cubbies": cubbies, "next": "super_rar to see what's inside, or load cubby=<login>"}, indent=2)

        if action == "super_rar":
            sr = _read_json(os.path.join(cave, "super-rar", "index.json")) or {}
            entries = sr.get("entries", [])
            q = (kwargs.get("query") or "").strip().lower()
            kind = (kwargs.get("kind") or "").strip().lower()
            hits = []
            for e in entries:
                if kind and e.get("kind") != kind:
                    continue
                hay = f"{e.get('name','')} {e.get('purpose','')} {e.get('cubby','')}".lower()
                if q and q not in hay:
                    continue
                hits.append(e)
            return json.dumps({"ok": True, "count": len(hits), "by_kind": sr.get("by_kind", {}),
                               "results": hits[:60],
                               "note": "streamable agents → `load cubby=<their cubby>`."}, indent=2)

        if action == "load":
            return self._load(kwargs, cave)

        return json.dumps({"ok": False, "error": f"unknown action {action!r}"}, indent=2)

    # ── stream a cubby's agents into THIS brainstem, git-invisibly ───────────
    def _load(self, kwargs, cave):
        handle = (kwargs.get("cubby") or "").strip()
        if not _HANDLE_RE.match(handle):
            return json.dumps({"ok": False, "error": "pass cubby=<a cave cubby login>"}, indent=2)
        src = os.path.join(cave, "cubbies", handle, "agents")
        if not os.path.isdir(src):
            return json.dumps({"ok": False, "error": f"no agents/ in cubbies/{handle}/"}, indent=2)
        bs = kwargs.get("_brainstem_dir") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target = os.path.join(bs, "agents")
        os.makedirs(target, exist_ok=True)

        verify = kwargs.get("verify", True)
        pins = {}
        if verify:
            ridx = _read_json(os.path.join(cave, "rar", "index.json")) or {}
            for a in ridx.get("agents", []):
                if a.get("path") and a.get("sha256"):
                    pins[os.path.basename(a["path"])] = a["sha256"]

        loaded, skipped = [], []
        for fn in sorted(os.listdir(src)):
            if not _AGENT_FILE_RE.match(fn):
                continue
            if fn in KERNEL_AGENTS:
                skipped.append({"file": fn, "why": "kernel — never overwritten"}); continue
            src_file = os.path.join(src, fn)
            if verify and fn in pins and _sha256_file(src_file) != pins[fn]:
                skipped.append({"file": fn, "why": "sha256 drift vs RAR pin — refused"}); continue
            dst = os.path.join(target, fn)
            if os.path.exists(dst) and _sha256_file(dst) != _sha256_file(src_file):
                skipped.append({"file": fn, "why": "your own differing file — won't overwrite"}); continue
            shutil.copy2(src_file, dst)
            loaded.append(fn)

        excluded = self._register_excludes(bs, loaded)
        return json.dumps({"ok": True, "from_cubby": handle, "loaded": loaded, "skipped": skipped,
                           "git_excluded": excluded,
                           "note": "streamed + git-invisible (.git/info/exclude) — zero commit risk. "
                                   "Reload the agents (next /chat turn) to use them."}, indent=2)

    @staticmethod
    def _register_excludes(bs, loaded):
        """Add streamed files to .git/info/exclude so the host repo never sees them."""
        info = os.path.join(bs, ".git", "info")
        if not os.path.isdir(os.path.join(bs, ".git")):
            return []                              # host brainstem isn't a git repo — nothing to hide
        os.makedirs(info, exist_ok=True)
        excl = os.path.join(info, "exclude")
        have = open(excl).read() if os.path.exists(excl) else ""
        added = []
        with open(excl, "a") as f:
            for fn in loaded:
                line = f"agents/{fn}"
                if line not in have:
                    f.write(line + "\n"); added.append(line)
        return added
