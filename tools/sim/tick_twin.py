"""tick_twin.py — single autonomous tick for one twin.

Current no-flag behavior is a deterministic in-memory sandbox tick. Historical
model and filesystem execution remains below, reachable only through reviewed
injected runners after exact target-receipt and section-13 verification.

Invokes the `claude` CLI in a fresh, isolated session pinned to the
twin's identity. Claude reads the twin's soul.md + the neighborhood's
state, decides ONE action, and emits a strict JSON action envelope.
This script validates + executes the action (writes file, appends bond
event). Operator-mediated by design: the AI proposes, this script
disposes (within sandboxed local writes only).

Usage:
    python3 tick_twin.py --twin bill-brainstem [--neighborhood local-art-collective] [--dry-run] [--mode auto|fake]

Modes:
    auto  — invoke `claude` CLI (real LLM tick). Default.
    fake  — deterministic action picker (no LLM call; useful for CI / smoke tests).

Exit codes:
    0 — action executed cleanly
    1 — Claude response invalid / action rejected / I/O error
    2 — twin or neighborhood missing
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Mapping

SIM_ROOT = os.path.expanduser("~/RAPP-sim")
HISTORICAL_SOURCE = {
    "path": "tools/sim/tick_twin.py",
    "commit": "05f75bd40dd37f4590da6ebab28110d9a4b4094a",
    "blob": "70e1e36890238745729117d6d029640f06262d66",
    "sha256": "2e1016a842336d7b5e2eff50d6d05b5ad6da33fd1590936ac18d24f6ee6d5405",
    "bytes": 16102,
}
TARGET_RECEIPT_SCHEMA = "rapp-effect-target-receipt/1.0"
SAFE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
ALLOWED_PIECE_KINDS = {"text", "ascii", "svg", "prompt", "json"}
MAX_PIECE_BYTES = 4 * 1024


def exact_target_receipt(operation: str, target: Mapping[str, object]) -> dict:
    return {
        "schema": TARGET_RECEIPT_SCHEMA,
        "operation": operation,
        "target": dict(target),
    }


def authorize_effect(
    *,
    operation: str,
    target: Mapping[str, object],
    dependencies: Mapping[str, object] | None,
    target_receipt: Mapping[str, object] | None,
    authority_evidence: Mapping[str, object] | None,
) -> dict | None:
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


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_json(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def _write_json(path: str, doc: dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    temporary = f"{path}.rapp-tick.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, "w") as stream:
            descriptor = -1
            json.dump(doc, stream, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.remove(temporary)
        except FileNotFoundError:
            pass
        raise


def _append_bond_event(twin_dir: str, event: dict) -> None:
    bonds_path = os.path.join(twin_dir, "bonds.json")
    bonds = _read_json(bonds_path) if os.path.exists(bonds_path) else {"events": []}
    bonds["events"].append(event)
    _write_json(bonds_path, bonds)


def _scan_neighborhood(nb_dir: str) -> dict:
    """Pure-filesystem read of the neighborhood's current state."""
    sub_dir = os.path.join(nb_dir, "submissions")
    vote_dir = os.path.join(nb_dir, "votes")

    submissions = []
    if os.path.isdir(sub_dir):
        for slug in sorted(os.listdir(sub_dir)):
            slug_path = os.path.join(sub_dir, slug)
            if os.path.isdir(slug_path):
                meta_p = os.path.join(slug_path, "meta.json")
                if os.path.exists(meta_p):
                    submissions.append(_read_json(meta_p))

    votes = []
    if os.path.isdir(vote_dir):
        for vote_file in sorted(os.listdir(vote_dir)):
            if vote_file.endswith(".json"):
                votes.append(_read_json(os.path.join(vote_dir, vote_file)))

    return {"submissions": submissions, "votes": votes,
            "neighborhood": _read_json(os.path.join(nb_dir, "neighborhood.json"))}


def build_prompt(twin: dict, nb_dir: str, nb_state: dict) -> str:
    """Build the prompt fed to Claude CLI. Single-shot, action-constrained."""
    soul = open(os.path.join(twin["dir"], "soul.md")).read()
    nb_holo_path = os.path.join(nb_dir, "holo.md")
    nb_holo = open(nb_holo_path).read() if os.path.exists(nb_holo_path) else ""
    nb_specs_path = os.path.join(nb_dir, "specs", "SUBMISSION_PROTOCOL.md")
    nb_specs = open(nb_specs_path).read() if os.path.exists(nb_specs_path) else ""

    summary_lines = []
    for s in nb_state["submissions"]:
        rmx = f" (remix of {s['remix_of']})" if s.get("remix_of") else ""
        summary_lines.append(f"  - slug={s['slug']!r} title={s['title']!r} by {s['contributor']}{rmx}")
    sub_summary = "\n".join(summary_lines) if summary_lines else "  (canvas is empty)"

    vote_lines = []
    for v in nb_state["votes"]:
        vote_lines.append(f"  - {v['voter_display']} → {v['slug']}: {v['reaction']}")
    vote_summary = "\n".join(vote_lines) if vote_lines else "  (no votes yet)"

    own_subs = [s for s in nb_state["submissions"] if s.get("contributor") == twin["display_name"]]
    others_subs = [s for s in nb_state["submissions"] if s.get("contributor") != twin["display_name"]]

    return f"""You are participating as **{twin['display_name']}** in a local-first art collective.

YOUR SOUL (read every turn — anchors your voice):
---
{soul}
---

THE NEIGHBORHOOD'S HOLO CARD (your entry doc):
---
{nb_holo[:3000]}
---

THE SUBMISSION PROTOCOL (the formal contract):
---
{nb_specs[:3000]}
---

CURRENT CANVAS STATE:
Submissions ({len(nb_state['submissions'])}):
{sub_summary}

Votes ({len(nb_state['votes'])}):
{vote_summary}

Your own submissions so far: {len(own_subs)}
Others' submissions so far:  {len(others_subs)}

YOUR TASK: Take EXACTLY ONE action this tick. Choose from:

  1. submit       — add a new piece
  2. vote         — react to an existing submission (you may NOT vote on your own)
  3. remix        — submit a new piece tagged remix_of: <other-slug>
  4. observe-only — do nothing this tick (returns rationale)

Respond with ONE JSON object inside a single ```json fenced block. Schema:

```json
{{
  "action": "submit" | "vote" | "remix" | "observe-only",
  "reason": "<1-2 sentences in your own voice>",
  "submit": {{
    "slug":  "<unique-lowercase-slug ≤ 48 chars>",
    "title": "<title>",
    "kind":  "text",
    "content": "<the piece itself, ≤ 4 KB>"
  }},
  "vote": {{
    "slug":     "<existing-slug-not-yours>",
    "reaction": "🩵 | 👎"
  }},
  "remix": {{
    "slug":     "<unique-new-slug>",
    "title":    "<title>",
    "kind":     "text",
    "content":  "<the remix piece>",
    "remix_of": "<existing-slug-not-yours>"
  }}
}}
```

Constraints (per ANTIPATTERNS):
- Stay in your voice (per soul.md). NEVER fall back to "I am an AI assistant" or "I am Claude".
- Don't clobber: never use a slug that's already in the canvas.
- If the canvas has at least one piece by another contributor and you've never voted on it, voting is a strong default.
- Cite if remixing — set `remix_of` to the source slug.
- License is always CC0-1.0.

Respond with ONLY the JSON block. No prose around it.
"""


def _historical_call_claude(prompt: str, timeout_s: int = 60) -> str:
    """Invoke claude CLI in a fresh subprocess (isolated session)."""
    cmd = ["claude", "--print", prompt]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
    if p.returncode != 0:
        raise RuntimeError(f"claude CLI exit {p.returncode}: {p.stderr[:500]}")
    return p.stdout


def call_claude(
    prompt: str,
    timeout_s: int = 60,
    *,
    dependencies: Mapping[str, object] | None = None,
    target_receipt: Mapping[str, object] | None = None,
    authority_evidence: Mapping[str, object] | None = None,
) -> str:
    """Invoke only an explicitly injected model runner."""
    target = {"model_boundary": "simulation-tick", "timeout_seconds": timeout_s}
    refusal = authorize_effect(
        operation="simulation-model-call",
        target=target,
        dependencies=dependencies,
        target_receipt=target_receipt,
        authority_evidence=authority_evidence,
    )
    if refusal is not None:
        raise RuntimeError(
            f"model execution refused at {refusal['step']}: {refusal['code']}"
        )
    runner = dependencies.get("model_runner")
    if not isinstance(runner, Callable):
        raise RuntimeError("model execution refused: injected model_runner missing")
    return runner(prompt, timeout_s)


def parse_action(claude_response: str) -> dict:
    """Extract the JSON action from Claude's response."""
    m = re.search(r"```json\s*(\{.*?\})\s*```", claude_response, re.DOTALL)
    if not m:
        # Fall back: try to parse as raw JSON
        try:
            return json.loads(claude_response.strip())
        except json.JSONDecodeError:
            raise ValueError(f"no JSON found in claude response (first 500 chars): {claude_response[:500]}")
    return json.loads(m.group(1))


def _validate_piece_payload(spec: object, *, remix: bool) -> tuple[bool, str]:
    label = "remix" if remix else "submit"
    if type(spec) is not dict:
        return False, f"{label}: payload must be an object"
    slug = spec.get("slug")
    if type(slug) is not str or not SAFE_SLUG_RE.fullmatch(slug):
        return False, f"{label}: slug {slug!r} invalid"
    title = spec.get("title")
    if type(title) is not str or not title.strip():
        return False, f"{label}: missing nonempty title"
    content = spec.get("content")
    if type(content) is not str:
        return False, f"{label}: missing string content"
    if len(content.encode("utf-8")) > MAX_PIECE_BYTES:
        return False, f"{label}: content exceeds {MAX_PIECE_BYTES} bytes"
    if spec.get("kind", "text") not in ALLOWED_PIECE_KINDS:
        return False, f"{label}: bad kind"
    if remix:
        remix_of = spec.get("remix_of")
        if type(remix_of) is not str or not SAFE_SLUG_RE.fullmatch(remix_of):
            return False, f"remix: remix_of {remix_of!r} invalid"
    return True, "ok"


def _validate_action_structure(action: object) -> tuple[bool, str]:
    if type(action) is not dict:
        return False, "action must be an object"
    kind = action.get("action")
    if kind not in ("submit", "vote", "remix", "observe-only"):
        return False, f"unknown action {kind!r}"
    if kind == "submit":
        return _validate_piece_payload(action.get("submit"), remix=False)
    if kind == "remix":
        return _validate_piece_payload(action.get("remix"), remix=True)
    if kind == "vote":
        vote_spec = action.get("vote")
        if type(vote_spec) is not dict:
            return False, "vote: payload must be an object"
        slug = vote_spec.get("slug")
        if type(slug) is not str or not SAFE_SLUG_RE.fullmatch(slug):
            return False, f"vote: slug {slug!r} invalid"
        if vote_spec.get("reaction") not in ("🩵", "👎", "heart", "thumbs_down"):
            return False, "vote: reaction must be 🩵 or 👎"
    return True, "ok"


def _historical_fake_action(twin: dict, nb_state: dict) -> dict:
    """Deterministic action picker for tests / smoke runs without LLM."""
    own_count = sum(1 for s in nb_state["submissions"] if s["contributor"] == twin["display_name"])
    others = [s for s in nb_state["submissions"] if s["contributor"] != twin["display_name"]]
    voted_slugs = {v["slug"] for v in nb_state["votes"] if v["voter_display"] == twin["display_name"]}
    unvoted_others = [s for s in others if s["slug"] not in voted_slugs]

    # Heuristic: if there's an unvoted other, vote. If we have 0 submissions, submit. Otherwise observe.
    if unvoted_others:
        return {"action": "vote", "reason": "fake mode — voting on unvoted other",
                "vote": {"slug": unvoted_others[0]["slug"], "reaction": "🩵"}}
    if own_count == 0:
        slug = f"{twin['name'].split('-')[0]}-fake-piece-{int(time.time())}"
        return {"action": "submit",
                "reason": "fake mode — first submission",
                "submit": {"slug": slug, "title": f"{twin['display_name']}'s first piece (fake mode)",
                           "kind": "text", "content": f"# Fake piece\n\nGenerated by tick_twin.py in fake mode.\nTimestamp: {_now_iso()}\n"}}
    return {"action": "observe-only", "reason": "fake mode — nothing to do this tick"}


def fake_action(twin: dict, nb_state: dict) -> dict:
    """Deterministic sandbox action picker with a stable clock and slug."""
    own_count = sum(
        1
        for submission in nb_state["submissions"]
        if submission["contributor"] == twin["display_name"]
    )
    others = [
        submission
        for submission in nb_state["submissions"]
        if submission["contributor"] != twin["display_name"]
    ]
    voted_slugs = {
        vote["slug"]
        for vote in nb_state["votes"]
        if vote["voter_display"] == twin["display_name"]
    }
    unvoted_others = [
        submission
        for submission in others
        if submission["slug"] not in voted_slugs
    ]
    if unvoted_others:
        return {
            "action": "vote",
            "reason": "sandbox mode - voting on first unvoted other",
            "vote": {"slug": unvoted_others[0]["slug"], "reaction": "🩵"},
        }
    if own_count == 0:
        stem = re.sub(r"[^a-z0-9-]", "-", twin["name"].lower()).strip("-")
        return {
            "action": "submit",
            "reason": "sandbox mode - first deterministic submission",
            "submit": {
                "slug": f"{stem[:30]}-sandbox-piece",
                "title": f"{twin['display_name']}'s sandbox piece",
                "kind": "text",
                "content": "# Sandbox piece\n\nDeterministic local replay.\n",
            },
        }
    return {
        "action": "observe-only",
        "reason": "sandbox mode - nothing to do this tick",
    }


def validate_action(action: dict, twin: dict, nb_state: dict) -> tuple[bool, str]:
    """Sanity-check the action before executing."""
    valid, detail = _validate_action_structure(action)
    if not valid:
        return valid, detail
    kind = action["action"]

    existing_slugs = {s["slug"] for s in nb_state["submissions"]}

    if kind == "submit":
        s = action["submit"]
        if s["slug"] in existing_slugs: return False, f"submit: slug {s['slug']!r} already exists"

    if kind == "vote":
        v = action["vote"]
        if v["slug"] not in existing_slugs: return False, f"vote: slug {v['slug']!r} doesn't exist"
        target = next(s for s in nb_state["submissions"] if s["slug"] == v["slug"])
        if target["contributor"] == twin["display_name"]:
            return False, f"vote: cannot vote on own submission {v['slug']!r}"

    if kind == "remix":
        r = action["remix"]
        if r["slug"] in existing_slugs: return False, f"remix: slug {r['slug']!r} already exists"
        if r["remix_of"] not in existing_slugs: return False, f"remix: remix_of {r['remix_of']!r} doesn't exist"
        source = next(s for s in nb_state["submissions"] if s["slug"] == r["remix_of"])
        if source["contributor"] == twin["display_name"]:
            return False, f"remix: cannot remix own submission"

    return True, "ok"


def _safe_output_path(root: str, *parts: str) -> str:
    canonical_root = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(canonical_root, *parts))
    if os.path.commonpath((canonical_root, candidate)) != canonical_root:
        raise ValueError(f"output escapes authorized root: {candidate}")
    return candidate


def action_effect_target(
    action: dict,
    twin: dict,
    nb_dir: str,
    nb_state: dict,
) -> dict:
    valid, detail = validate_action(action, twin, nb_state)
    if not valid:
        raise ValueError(detail)
    twin_dir = os.path.realpath(twin["dir"])
    neighborhood_dir = os.path.realpath(nb_dir)
    kind = action["action"]
    outputs = [_safe_output_path(twin_dir, "bonds.json")]
    if kind in {"submit", "remix"}:
        spec = action[kind]
        extension = {
            "text": "md",
            "ascii": "txt",
            "svg": "svg",
            "prompt": "md",
            "json": "json",
        }[spec.get("kind", "text")]
        submission_root = _safe_output_path(
            neighborhood_dir, "submissions", spec["slug"]
        )
        outputs.extend(
            (
                _safe_output_path(submission_root, "meta.json"),
                _safe_output_path(submission_root, f"piece.{extension}"),
                _safe_output_path(neighborhood_dir, "submissions", "index.json"),
            )
        )
    elif kind == "vote":
        twin_name = twin.get("name")
        if type(twin_name) is not str or not SAFE_SLUG_RE.fullmatch(twin_name):
            raise ValueError(f"unsafe twin name: {twin_name!r}")
        outputs.append(
            _safe_output_path(
                neighborhood_dir,
                "votes",
                f"{twin_name}-on-{action['vote']['slug']}.json",
            )
        )
    action_bytes = json.dumps(
        action,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    state_bytes = json.dumps(
        nb_state,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    identity = {
        "name": twin.get("name"),
        "display_name": twin.get("display_name"),
        "rappid": twin.get("rappid"),
    }
    if not all(type(value) is str and value for value in identity.values()):
        raise ValueError("twin identity fields must be nonempty strings")
    return {
        "twin_dir": twin_dir,
        "neighborhood_dir": neighborhood_dir,
        "twin": identity,
        "action": kind,
        "action_sha256": hashlib.sha256(action_bytes).hexdigest(),
        "neighborhood_state_sha256": hashlib.sha256(state_bytes).hexdigest(),
        "output_paths": sorted(outputs),
    }


def _historical_execute_action(
    action: dict,
    twin: dict,
    nb_dir: str,
    dry_run: bool = False,
    nb_state: dict | None = None,
) -> dict:
    """Apply the action to the neighborhood + log to twin's bonds.json."""
    valid, detail = (
        validate_action(action, twin, nb_state)
        if nb_state is not None
        else _validate_action_structure(action)
    )
    if not valid:
        raise ValueError(detail)
    kind = action["action"]
    result = {"action": kind, "reason": action.get("reason", ""), "applied": not dry_run, "at": _now_iso()}

    if kind == "observe-only":
        if not dry_run:
            _append_bond_event(twin["dir"], {
                "at": result["at"], "kind": "tick", "action": "observe-only",
                "reason": action.get("reason", ""), "neighborhood": nb_dir,
            })
        return result

    if kind == "submit" or kind == "remix":
        spec = action[kind]
        slug = spec["slug"]
        sub_dir = _safe_output_path(nb_dir, "submissions", slug)
        meta = {
            "schema": "rapp-art-submission/1.0",
            "title": spec["title"], "slug": slug,
            "contributor": twin["display_name"],
            "contributor_rappid": twin["rappid"],
            "kind": spec.get("kind", "text"),
            "submitted_at": result["at"],
            "remix_of": spec.get("remix_of") if kind == "remix" else None,
            "license": "CC0-1.0",
        }
        ext_map = {"text": "md", "ascii": "txt", "svg": "svg", "prompt": "md", "json": "json"}
        piece_path = f"piece.{ext_map.get(meta['kind'], 'txt')}"
        if not dry_run:
            submissions_dir = _safe_output_path(nb_dir, "submissions")
            os.makedirs(submissions_dir, exist_ok=True)
            os.mkdir(sub_dir)
            idx_path = os.path.join(nb_dir, "submissions", "index.json")
            idx = _read_json(idx_path) if os.path.exists(idx_path) else {"schema": "rapp-art-submissions-index/1.0", "submissions": []}
            original_idx = json.loads(json.dumps(idx, ensure_ascii=False))
            try:
                _write_json(os.path.join(sub_dir, "meta.json"), meta)
                piece = os.path.join(sub_dir, piece_path)
                descriptor = os.open(
                    piece,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0),
                    0o600,
                )
                with os.fdopen(descriptor, "w") as stream:
                    stream.write(spec["content"])
                    stream.flush()
                    os.fsync(stream.fileno())
                idx["submissions"].append({k: meta[k] for k in ("slug", "title", "contributor", "kind", "submitted_at", "license", "remix_of")})
                _write_json(idx_path, idx)
                try:
                    _append_bond_event(twin["dir"], {
                        "at": result["at"], "kind": kind, "slug": slug, "title": spec["title"],
                        "remix_of": meta["remix_of"], "neighborhood": nb_dir,
                    })
                except Exception:
                    _write_json(idx_path, original_idx)
                    raise
            except Exception:
                shutil.rmtree(sub_dir, ignore_errors=True)
                raise
        result["slug"] = slug
        return result

    if kind == "vote":
        v = action["vote"]
        reaction = v["reaction"] if v["reaction"] in ("🩵", "👎") else ("🩵" if v["reaction"] == "heart" else "👎")
        twin_name = twin.get("name")
        if type(twin_name) is not str or not SAFE_SLUG_RE.fullmatch(twin_name):
            raise ValueError(f"unsafe twin name: {twin_name!r}")
        vote_path = _safe_output_path(
            nb_dir, "votes", f"{twin_name}-on-{v['slug']}.json"
        )
        if not dry_run:
            _write_json(vote_path, {
                "voter": twin["name"], "voter_display": twin["display_name"],
                "voter_rappid": twin["rappid"],
                "slug": v["slug"], "reaction": reaction, "at": result["at"],
            })
            _append_bond_event(twin["dir"], {
                "at": result["at"], "kind": "vote", "slug": v["slug"], "reaction": reaction,
                "neighborhood": nb_dir,
            })
        result["slug"] = v["slug"]
        result["reaction"] = reaction
        return result

    return result


def execute_action(
    action: dict,
    twin: dict,
    nb_dir: str,
    dry_run: bool = True,
    *,
    dependencies: Mapping[str, object] | None = None,
    target_receipt: Mapping[str, object] | None = None,
    authority_evidence: Mapping[str, object] | None = None,
    nb_state: dict | None = None,
) -> dict:
    if dry_run:
        if nb_state is not None:
            valid, detail = validate_action(action, twin, nb_state)
            if not valid:
                return {
                    "action": action.get("action"),
                    "applied": False,
                    "effects_started": False,
                    "error": {"code": "invalid-action", "step": detail},
                }
        result = _historical_execute_action(action, twin, nb_dir, dry_run=True)
        result["at"] = "2000-01-01T00:00:00Z"
        return result

    if nb_state is None:
        return {
            "action": action.get("action"),
            "applied": False,
            "effects_started": False,
            "error": {
                "code": "invalid-action",
                "step": "current neighborhood state is required",
            },
        }
    try:
        target = action_effect_target(action, twin, nb_dir, nb_state)
    except ValueError as exc:
        return {
            "action": action.get("action"),
            "applied": False,
            "effects_started": False,
            "error": {"code": "invalid-action", "step": str(exc)},
        }
    refusal = authorize_effect(
        operation="simulation-tick-apply",
        target=target,
        dependencies=dependencies,
        target_receipt=target_receipt,
        authority_evidence=authority_evidence,
    )
    if refusal is not None:
        return {
            "action": action.get("action"),
            "applied": False,
            "effects_started": False,
            "error": refusal,
        }
    executor = dependencies.get("action_executor")
    lock_factory = dependencies.get("action_lock")
    state_reader = dependencies.get("read_neighborhood_state")
    if not all(
        isinstance(candidate, Callable)
        for candidate in (executor, lock_factory, state_reader)
    ):
        return {
            "action": action.get("action"),
            "applied": False,
            "effects_started": False,
            "error": {
                "code": "reviewed-dependency-injection-required",
                "step": "action-lock-state-executor",
            },
        }
    bound_action = json.loads(json.dumps(action, ensure_ascii=False))
    bound_twin = {
        "name": target["twin"]["name"],
        "display_name": target["twin"]["display_name"],
        "rappid": target["twin"]["rappid"],
        "dir": target["twin_dir"],
    }
    lock = lock_factory(target)
    if not hasattr(lock, "__enter__") or not hasattr(lock, "__exit__"):
        return {
            "action": action.get("action"),
            "applied": False,
            "effects_started": False,
            "error": {
                "code": "reviewed-dependency-injection-required",
                "step": "action-lock",
            },
        }
    with lock:
        current_state = state_reader(target["neighborhood_dir"])
        try:
            current_target = action_effect_target(
                bound_action,
                bound_twin,
                target["neighborhood_dir"],
                current_state,
            )
        except ValueError as exc:
            return {
                "action": action.get("action"),
                "applied": False,
                "effects_started": False,
                "error": {"code": "state-changed", "step": str(exc)},
            }
        if current_target != target:
            return {
                "action": action.get("action"),
                "applied": False,
                "effects_started": False,
                "error": {
                    "code": "state-changed",
                    "step": "receipt-bound neighborhood state changed",
                },
            }
        bound_state = json.loads(json.dumps(current_state, ensure_ascii=False))
        return executor(
            _historical_execute_action,
            bound_action,
            bound_twin,
            target["neighborhood_dir"],
            bound_state,
        )


def load_twin(twin_name: str) -> dict:
    twin_dir = os.path.join(SIM_ROOT, twin_name)
    if not os.path.isdir(twin_dir):
        print(f"ERROR: twin {twin_name!r} not found at {twin_dir}", file=sys.stderr)
        sys.exit(2)
    rj = _read_json(os.path.join(twin_dir, "rappid.json"))
    return {
        "name": rj.get("name", twin_name),
        "display_name": rj.get("display_name", twin_name),
        "rappid": rj["rappid"],
        "dir": twin_dir,
    }


def _historical_main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--twin", required=True, help="e.g. bill-brainstem")
    ap.add_argument("--neighborhood", default="local-art-collective")
    ap.add_argument("--mode", choices=["auto", "fake"], default="auto",
                    help="auto = call claude CLI; fake = deterministic action picker (no LLM)")
    ap.add_argument("--dry-run", action="store_true", help="propose but don't apply")
    ap.add_argument("--timeout", type=int, default=60)
    args = ap.parse_args(argv)

    twin = load_twin(args.twin)
    nb_dir = os.path.join(SIM_ROOT, args.neighborhood)
    if not os.path.isdir(nb_dir):
        print(f"ERROR: neighborhood {args.neighborhood!r} not found at {nb_dir}", file=sys.stderr)
        sys.exit(2)

    print(f"[tick] {twin['display_name']} → {args.neighborhood} | mode={args.mode} | dry_run={args.dry_run}")

    nb_state = _scan_neighborhood(nb_dir)

    if args.mode == "fake":
        action = fake_action(twin, nb_state)
        print(f"[fake] proposed action: {action['action']} | reason: {action.get('reason','')[:80]}")
    else:
        prompt = build_prompt(twin, nb_dir, nb_state)
        print(f"[claude] prompt size: {len(prompt)} chars")
        try:
            response = call_claude(prompt, timeout_s=args.timeout)
        except subprocess.TimeoutExpired:
            print("[claude] TIMEOUT", file=sys.stderr)
            sys.exit(1)
        try:
            action = parse_action(response)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"[parse] FAILED: {e}", file=sys.stderr)
            print(f"[claude] raw response: {response[:1000]}", file=sys.stderr)
            sys.exit(1)
        print(f"[claude] proposed action: {action.get('action')} | reason: {action.get('reason','')[:80]}")

    ok, msg = validate_action(action, twin, nb_state)
    if not ok:
        print(f"[validate] REJECTED: {msg}", file=sys.stderr)
        if not args.dry_run:
            _append_bond_event(twin["dir"], {
                "at": _now_iso(), "kind": "tick-rejected",
                "proposed_action": action.get("action"), "reason": msg,
            })
        sys.exit(1)

    result = execute_action(
        action,
        twin,
        nb_dir,
        dry_run=args.dry_run,
        nb_state=nb_state,
    )
    print(f"[exec] {result}")


def sandbox_replay() -> dict:
    twin = {
        "name": "bill-brainstem",
        "display_name": "Bill",
        "rappid": "candidate-unminted",
        "dir": "<in-memory>",
    }
    state = {
        "submissions": [
            {
                "slug": "alice-opening",
                "title": "Alice Opening",
                "contributor": "Alice",
            }
        ],
        "votes": [],
        "neighborhood": {"name": "local-art-collective"},
    }
    action = fake_action(twin, state)
    ok, message = validate_action(action, twin, state)
    result = execute_action(
        action,
        twin,
        "<in-memory>",
        dry_run=True,
        nb_state=state,
    )
    return {
        "schema": "rapp-simulation-tick/1.0",
        "mode": "sandbox",
        "clock": "2000-01-01T00:00:00Z",
        "twin": twin,
        "action": action,
        "validation": {"ok": ok, "message": message},
        "result": result,
        "model_calls": [],
        "writes": [],
        "subprocesses": [],
        "historical_source": HISTORICAL_SOURCE,
        "accepted": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Run a deterministic simulation tick or request a gated effect."
    )
    parser.add_argument("--twin", help="e.g. bill-brainstem")
    parser.add_argument("--neighborhood", default="local-art-collective")
    parser.add_argument(
        "--mode",
        choices=["sandbox", "inspect", "fake", "auto"],
        default="sandbox",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args(argv)

    if args.apply and (not args.twin or args.mode in {"sandbox", "inspect"}):
        print(json.dumps({
            "schema": "rapp-simulation-tick-result/1.0",
            "ok": False,
            "effects_started": False,
            "error": {
                "code": "reviewed-dependency-injection-required",
                "step": "apply-mode",
            },
            "requirements": [
                "reviewed-dependency-injection",
                "exact-target-receipt",
                "authenticated-fresh-section-13-evidence",
            ],
        }, indent=2, sort_keys=True))
        return 78

    if args.mode in {"sandbox", "inspect"} and not args.twin:
        print(json.dumps(sandbox_replay(), indent=2, sort_keys=True))
        return 0

    if args.mode == "auto":
        result = {
            "schema": "rapp-simulation-tick-result/1.0",
            "ok": False,
            "effects_started": False,
            "error": {
                "code": "authenticated-registry-unavailable",
                "step": "model-runner",
            },
            "requirements": [
                "reviewed-dependency-injection",
                "exact-target-receipt",
                "authenticated-fresh-section-13-evidence",
            ],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 78

    if not args.twin:
        parser.error("--twin is required for filesystem-backed fake/inspect modes")

    twin = load_twin(args.twin)
    nb_dir = os.path.join(SIM_ROOT, args.neighborhood)
    if not os.path.isdir(nb_dir):
        print(
            f"ERROR: neighborhood {args.neighborhood!r} not found at {nb_dir}",
            file=sys.stderr,
        )
        return 2
    state = _scan_neighborhood(nb_dir)
    action = fake_action(twin, state)
    ok, message = validate_action(action, twin, state)
    if not ok:
        print(json.dumps({"ok": False, "error": message}, indent=2, sort_keys=True))
        return 1
    result = execute_action(
        action,
        twin,
        nb_dir,
        dry_run=not args.apply,
        nb_state=state,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("applied") is not False or not args.apply else 78


if __name__ == "__main__":
    raise SystemExit(main())
