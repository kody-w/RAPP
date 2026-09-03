"""
cave_agent.py — talk to the public RAPP Cave from inside your brainstem.

Current behavior defaults to inspection of a caller-supplied local Cave
snapshot. The clone, pull, agent-copy, and git-exclude algorithms remain
preserved below but require reviewed injected execution, an exact target
receipt, and fresh authenticated section-13 evidence.

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
import stat
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    from agents.basic_agent import BasicAgent
except ModuleNotFoundError:
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(_REPO_ROOT / "rapp_brainstem"))
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
HISTORICAL_SOURCE = {
    "path": "cave/agents/cave_agent.py",
    "commit": "cdf1aba25ba39c373ba4c738e7c6d421fff0cf86",
    "blob": "a3fdc75afccce81e16eda5c5e7e5f5963495eb96",
    "sha256": "c8480ab51c661939d74b91e78f0c33c121034da114d5956494e3cf192db3c45b",
    "bytes": 10977,
}
TARGET_RECEIPT_SCHEMA = "rapp-effect-target-receipt/1.0"


def exact_target_receipt(operation, target):
    return {
        "schema": TARGET_RECEIPT_SCHEMA,
        "operation": operation,
        "target": dict(target),
    }


def authorize_effect(
    *,
    operation,
    target,
    dependencies,
    target_receipt,
    authority_evidence,
):
    if not isinstance(dependencies, Mapping):
        return {"code": "reviewed-dependency-injection-required", "step": "dependency-injection"}
    review = dependencies.get("review")
    if not isinstance(review, Callable) or review(dependencies, operation, target) is not True:
        return {"code": "reviewed-dependency-injection-required", "step": "dependency-review"}
    if target_receipt != exact_target_receipt(operation, target):
        return {"code": "exact-target-receipt-required", "step": "target-receipt"}
    authenticate = dependencies.get("authenticate_section13")
    if not isinstance(authenticate, Callable):
        return {"code": "authenticated-registry-unavailable", "step": "section-13-authentication"}
    verdict = authenticate(authority_evidence, operation, target)
    if (
        not isinstance(verdict, Mapping)
        or verdict.get("authenticated") is not True
        or verdict.get("fresh") is not True
        or verdict.get("owner_anchor_verified") is not True
    ):
        return {"code": "authenticated-registry-unavailable", "step": "section-13-authentication"}
    return None


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
                "Inspect a caller-supplied local snapshot of the historical PUBLIC RAPP Cave. "
                "list and super_rar are read-only. load and sync preserve the original algorithms "
                "but require reviewed dependency injection, an exact target receipt, and fresh "
                "authenticated RAPP/1 section-13 evidence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["inspect", "list", "super_rar", "load", "sync"],
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
    def _historical_cave_root(self, refresh=False):
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

    def _cave_root(self, refresh=False, dependencies=None):
        """Resolve only an injected local snapshot; never clone or pull."""
        if refresh:
            return None
        if isinstance(dependencies, Mapping):
            root = dependencies.get("cave_root")
            if isinstance(root, str) and os.path.isdir(root):
                return root
        return None

    def perform(self, **kwargs):
        action = (kwargs.get("action") or "inspect").strip()
        dependencies = kwargs.get("_dependencies")
        cave = kwargs.get("_cave_root")
        if cave is None and isinstance(dependencies, Mapping):
            cave = dependencies.get("cave_root")

        if action == "inspect":
            return json.dumps({
                "ok": True,
                "mode": "inspect",
                "historical_source": HISTORICAL_SOURCE,
                "available_actions": ["list", "super_rar", "load", "sync"],
                "local_cave_root_supplied": bool(cave),
                "default_effects": [],
                "accepted": False,
            }, indent=2, sort_keys=True)

        if action == "sync":
            target = {"repository": CAVE_REPO, "cache": CACHE}
            refusal = authorize_effect(
                operation="cave-sync",
                target=target,
                dependencies=dependencies,
                target_receipt=kwargs.get("_target_receipt"),
                authority_evidence=kwargs.get("_authority_evidence"),
            )
            if refusal is not None:
                return json.dumps({
                    "ok": False,
                    "synced": False,
                    "effects_started": False,
                    "error": refusal,
                    "target": target,
                }, indent=2, sort_keys=True)
            executor = dependencies.get("cave_executor")
            if not isinstance(executor, Callable):
                return json.dumps({
                    "ok": False,
                    "synced": False,
                    "effects_started": False,
                    "error": {
                        "code": "reviewed-dependency-injection-required",
                        "step": "cave-executor",
                    },
                    "target": target,
                }, indent=2, sort_keys=True)
            result = executor(self._historical_cave_root, True, target)
            return json.dumps({
                "ok": bool(result),
                "synced": bool(result),
                "cave": result,
            }, indent=2, sort_keys=True)

        if not cave or not os.path.isdir(cave):
            return json.dumps({
                "ok": False,
                "error": {
                    "code": "local-cave-snapshot-required",
                    "step": "local-inspection",
                },
                "repo": CAVE_REPO,
                "effects_started": False,
            }, indent=2, sort_keys=True)

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
    @staticmethod
    def _load_source_snapshot(cave, src, verify):
        pins = {}
        if verify:
            ridx = _read_json(os.path.join(cave, "rar", "index.json")) or {}
            for agent in ridx.get("agents", []):
                path = agent.get("path")
                digest = agent.get("sha256")
                if path and digest:
                    filename = os.path.basename(path)
                    if filename in pins and pins[filename] != digest:
                        pins[filename] = None
                    else:
                        pins[filename] = digest

        source_root = os.path.realpath(src)
        entries = []
        for filename in sorted(os.listdir(src)):
            if not _AGENT_FILE_RE.match(filename):
                continue
            source_file = os.path.join(src, filename)
            resolved = os.path.realpath(source_file)
            record = {"file": filename}
            if filename in KERNEL_AGENTS:
                record["status"] = "kernel-refused"
            elif os.path.islink(source_file):
                record["status"] = "symlink-refused"
            elif not os.path.isfile(source_file):
                record["status"] = "non-regular-refused"
            elif os.path.commonpath((source_root, resolved)) != source_root:
                record["status"] = "source-escape-refused"
            else:
                digest = _sha256_file(source_file)
                record.update({
                    "sha256": digest,
                    "bytes": os.path.getsize(source_file),
                })
                expected = pins.get(filename)
                if verify and expected is None:
                    record["status"] = "pin-required"
                elif verify and digest != expected:
                    record["status"] = "pin-mismatch"
                    record["expected_sha256"] = expected
                else:
                    record["status"] = "loadable"
                    if expected:
                        record["expected_sha256"] = expected
            entries.append(record)
        encoded = json.dumps(
            entries,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return {
            "verify": bool(verify),
            "entries": entries,
            "sha256": hashlib.sha256(encoded).hexdigest(),
        }

    @staticmethod
    def _git_exclude_path(bs):
        marker = os.path.join(bs, ".git")
        if os.path.isdir(marker):
            git_dir = os.path.realpath(marker)
        elif os.path.isfile(marker):
            try:
                line = open(marker, encoding="utf-8").readline().strip()
            except OSError:
                return None
            prefix = "gitdir:"
            if not line.lower().startswith(prefix):
                return None
            raw = line[len(prefix):].strip()
            git_dir = os.path.realpath(
                raw if os.path.isabs(raw) else os.path.join(bs, raw)
            )
        else:
            return None

        common = os.path.join(git_dir, "commondir")
        if os.path.isfile(common):
            try:
                raw = open(common, encoding="utf-8").readline().strip()
            except OSError:
                return None
            git_dir = os.path.realpath(
                raw if os.path.isabs(raw) else os.path.join(git_dir, raw)
            )
        return os.path.join(git_dir, "info", "exclude")

    def _load(self, kwargs, cave):
        handle = (kwargs.get("cubby") or "").strip()
        if not _HANDLE_RE.match(handle):
            return json.dumps({"ok": False, "error": "pass cubby=<a cave cubby login>"}, indent=2)
        src = os.path.join(cave, "cubbies", handle, "agents")
        if not os.path.isdir(src):
            return json.dumps({"ok": False, "error": f"no agents/ in cubbies/{handle}/"}, indent=2)
        bs = kwargs.get("_brainstem_dir") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        verify = kwargs.get("verify", True)
        snapshot = self._load_source_snapshot(cave, src, verify)
        exclude_path = self._git_exclude_path(bs)
        target = {
            "cubby": handle,
            "source": os.path.realpath(src),
            "brainstem": os.path.realpath(bs),
            "verify": bool(verify),
            "source_snapshot_sha256": snapshot["sha256"],
            "source_entries": snapshot["entries"],
            "git_exclude": exclude_path,
        }
        if exclude_path is None:
            return json.dumps({
                "ok": False,
                "loaded": [],
                "effects_started": False,
                "error": {
                    "code": "git-exclusion-unavailable",
                    "step": "git-exclude-preflight",
                },
                "target": target,
            }, indent=2, sort_keys=True)
        dependencies = kwargs.get("_dependencies")
        refusal = authorize_effect(
            operation="cave-load-agents",
            target=target,
            dependencies=dependencies,
            target_receipt=kwargs.get("_target_receipt"),
            authority_evidence=kwargs.get("_authority_evidence"),
        )
        if refusal is not None:
            return json.dumps({
                "ok": False,
                "loaded": [],
                "effects_started": False,
                "error": refusal,
                "target": target,
            }, indent=2, sort_keys=True)
        executor = dependencies.get("cave_executor")
        if not isinstance(executor, Callable):
            return json.dumps({
                "ok": False,
                "loaded": [],
                "effects_started": False,
                "error": {
                    "code": "reviewed-dependency-injection-required",
                    "step": "cave-executor",
                },
                "target": target,
            }, indent=2, sort_keys=True)
        return executor(
            self._historical_load,
            kwargs,
            cave,
            target,
            snapshot,
        )

    def _historical_load(self, kwargs, cave, expected_target=None, expected_snapshot=None):
        handle = (kwargs.get("cubby") or "").strip()
        src = os.path.join(cave, "cubbies", handle, "agents")
        bs = kwargs.get("_brainstem_dir") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        target = os.path.join(os.path.realpath(bs), "agents")
        verify = kwargs.get("verify", True)
        current_snapshot = self._load_source_snapshot(cave, src, verify)
        current_target = {
            "cubby": handle,
            "source": os.path.realpath(src),
            "brainstem": os.path.realpath(bs),
            "verify": bool(verify),
            "source_snapshot_sha256": current_snapshot["sha256"],
            "source_entries": current_snapshot["entries"],
            "git_exclude": self._git_exclude_path(bs),
        }
        if (
            expected_target != current_target
            or expected_snapshot is None
            or current_snapshot["sha256"] != expected_snapshot.get("sha256")
        ):
            return json.dumps({
                "ok": False,
                "loaded": [],
                "error": "source snapshot changed after authorization",
            }, indent=2)

        loadable = [
            entry
            for entry in current_snapshot["entries"]
            if entry["status"] == "loadable"
        ]
        skipped = [
            {"file": entry["file"], "why": entry["status"]}
            for entry in current_snapshot["entries"]
            if entry["status"] != "loadable"
        ]
        to_copy = []
        for entry in loadable:
            filename = entry["file"]
            source_file = os.path.join(src, filename)
            destination = os.path.join(target, filename)
            if os.path.lexists(destination):
                skipped.append({
                    "file": filename,
                    "why": "destination already exists — won't overwrite",
                })
                continue
            to_copy.append((filename, source_file, destination))

        if not to_copy:
            return json.dumps({
                "ok": True,
                "from_cubby": handle,
                "loaded": [],
                "skipped": skipped,
                "git_excluded": [],
                "git_invisible": True,
                "note": "no eligible new agents to stream",
            }, indent=2)

        names = [filename for filename, _, _ in to_copy]
        excluded = self._register_excludes(bs, names)
        expected_excludes = [f"agents/{filename}" for filename in names]
        if excluded != expected_excludes:
            return json.dumps({
                "ok": False,
                "loaded": [],
                "skipped": skipped,
                "git_excluded": excluded,
                "error": "could not guarantee git exclusion before copying",
            }, indent=2)

        nofollow = getattr(os, "O_NOFOLLOW", 0)
        directory_flag = getattr(os, "O_DIRECTORY", 0)
        if not nofollow or not directory_flag:
            return json.dumps({
                "ok": False,
                "loaded": [],
                "skipped": skipped,
                "git_excluded": excluded,
                "error": "no-follow descriptor operations are unavailable",
            }, indent=2)

        target_created = False
        try:
            os.mkdir(target)
            target_created = True
        except FileExistsError:
            pass
        if os.path.islink(target) or not os.path.isdir(target):
            return json.dumps({
                "ok": False,
                "loaded": [],
                "skipped": skipped,
                "git_excluded": excluded,
                "error": "agents destination is not a real directory",
            }, indent=2)

        source_fd = os.open(
            os.path.realpath(src),
            os.O_RDONLY | directory_flag | nofollow,
        )
        try:
            target_fd = os.open(
                target,
                os.O_RDONLY | directory_flag | nofollow,
            )
        except Exception:
            os.close(source_fd)
            raise
        expected_by_name = {
            entry["file"]: entry
            for entry in current_snapshot["entries"]
            if entry["status"] == "loadable"
        }
        created = []
        try:
            for filename, _, _ in to_copy:
                try:
                    os.stat(
                        filename,
                        dir_fd=target_fd,
                        follow_symlinks=False,
                    )
                except FileNotFoundError:
                    pass
                else:
                    raise FileExistsError(
                        f"destination appeared after authorization: {filename}"
                    )

                source_file_fd = os.open(
                    filename,
                    os.O_RDONLY | nofollow,
                    dir_fd=source_fd,
                )
                try:
                    source_stat = os.fstat(source_file_fd)
                    if not stat.S_ISREG(source_stat.st_mode):
                        raise OSError(
                            f"source is no longer a regular file: {filename}"
                        )
                    destination_fd = os.open(
                        filename,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
                        0o600,
                        dir_fd=target_fd,
                    )
                    created.append(filename)
                    digest = hashlib.sha256()
                    try:
                        while True:
                            chunk = os.read(source_file_fd, 1024 * 1024)
                            if not chunk:
                                break
                            digest.update(chunk)
                            offset = 0
                            while offset < len(chunk):
                                written = os.write(
                                    destination_fd, chunk[offset:]
                                )
                                if written <= 0:
                                    raise OSError(
                                        f"short write while copying {filename}"
                                    )
                                offset += written
                        os.fchmod(
                            destination_fd,
                            stat.S_IMODE(source_stat.st_mode),
                        )
                        os.fsync(destination_fd)
                    finally:
                        os.close(destination_fd)
                    if digest.hexdigest() != expected_by_name[filename]["sha256"]:
                        raise OSError(
                            f"source changed during copy: {filename}"
                        )
                finally:
                    os.close(source_file_fd)
        except Exception:
            for filename in created:
                try:
                    os.unlink(filename, dir_fd=target_fd)
                except OSError:
                    pass
            if target_created:
                try:
                    os.rmdir(target)
                except OSError:
                    pass
            raise
        finally:
            os.close(target_fd)
            os.close(source_fd)

        loaded = list(created)
        return json.dumps({
            "ok": True,
            "from_cubby": handle,
            "loaded": loaded,
            "skipped": skipped,
            "git_excluded": excluded,
            "git_invisible": len(excluded) == len(loaded),
            "note": (
                "streamed only after git exclusion was installed; reload the "
                "agents on the next /chat turn to use them"
            ),
        }, indent=2)

    @staticmethod
    def _register_excludes(bs, loaded):
        """Add streamed files to .git/info/exclude so the host repo never sees them."""
        exclude_path = CaveAgent._git_exclude_path(bs)
        if exclude_path is None or fcntl is None:
            return []
        info = os.path.dirname(exclude_path)
        os.makedirs(info, exist_ok=True)
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        lock_path = os.path.join(info, "rapp-cave-exclude.lock")
        lock_fd = os.open(
            lock_path,
            os.O_RDWR | os.O_CREAT | nofollow,
            0o600,
        )
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            if os.path.islink(exclude_path):
                return []
            if os.path.exists(exclude_path):
                read_fd = os.open(exclude_path, os.O_RDONLY | nofollow)
                try:
                    chunks = []
                    while True:
                        chunk = os.read(read_fd, 1024 * 1024)
                        if not chunk:
                            break
                        chunks.append(chunk)
                    have = b"".join(chunks).decode("utf-8")
                finally:
                    os.close(read_fd)
            else:
                have = ""
            lines = [f"agents/{filename}" for filename in loaded]
            missing = [line for line in lines if line not in have.splitlines()]
            if missing:
                suffix = "" if not have or have.endswith("\n") else "\n"
                updated = have + suffix + "".join(
                    f"{line}\n" for line in missing
                )
                temporary = (
                    f"{exclude_path}.rapp-cave-{os.getpid()}.tmp"
                )
                try:
                    write_fd = os.open(
                        temporary,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
                        0o600,
                    )
                    try:
                        encoded = updated.encode("utf-8")
                        offset = 0
                        while offset < len(encoded):
                            written = os.write(write_fd, encoded[offset:])
                            if written <= 0:
                                raise OSError(
                                    "short write updating git exclude"
                                )
                            offset += written
                        os.fsync(write_fd)
                    finally:
                        os.close(write_fd)
                    os.replace(temporary, exclude_path)
                finally:
                    try:
                        os.remove(temporary)
                    except FileNotFoundError:
                        pass
            read_fd = os.open(exclude_path, os.O_RDONLY | nofollow)
            try:
                chunks = []
                while True:
                    chunk = os.read(read_fd, 1024 * 1024)
                    if not chunk:
                        break
                    chunks.append(chunk)
                final_lines = set(b"".join(chunks).decode("utf-8").splitlines())
            finally:
                os.close(read_fd)
            return lines if all(line in final_lines for line in lines) else []
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
