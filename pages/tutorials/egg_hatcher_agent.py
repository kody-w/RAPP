"""
egg_hatcher_agent.py — universal hatcher for the .egg cartridge family.

Current behavior is deterministic local inspection only. The complete legacy
router remains below, while URL reads, extraction, installation, estate writes,
and browser mounting require reviewed dependency injection, an exact target
receipt, and fresh authenticated RAPP/1 section-13 evidence.

The kernel-level agent that introspects ANY .egg cartridge and routes it
to the right destination based on what's inside. Drop into a brainstem,
restart, and the LLM gets a `HatchEgg` tool that does the right thing
without the operator having to know which kind of cartridge they're
holding.

The .egg cartridge family (per kody-w/rappterbox/carts/SCHEMA.md):

  brainstem-egg/2.2-organism       → hatch into ~/.rapp/twins/<rappid>/
  brainstem-egg/2.2-rapplication   → install as a planted rapp
  brainstem-egg/2.3-session        → mount in rappterbox console iframe
  brainstem-egg/2.3-neighborhood   → mint a new GitHub repo (planned)
  brainstem-egg/2.3-estate         → re-anchor estate on substrate (planned)

Routing is BY INTROSPECTION — the hatcher reads the cartridge's manifest
and dispatches by `schema` / `type`. Never guesses. Unknown kinds get a
clear "I don't know how to hatch this" reply, never a destructive
fallback.

How the routing works:
  1. Open file (or fetch URL) → bytes
  2. Try JSON parse first (session cartridges are bare JSON)
  3. If not JSON → try ZIP, read manifest.json
  4. Read manifest['schema'] and manifest['type']
  5. Switch and route

Sneakernet portable: the docstring IS the readme. Drop the .py into
~/.brainstem/agents/, restart, ask in chat: "hatch /path/to/file.egg"
or "hatch https://example.com/foo.egg". The LLM tool-routes to HatchEgg.

For session cartridges specifically: the hatcher CAN'T mount them itself
(no iframe in a Python brainstem) — instead it returns the URL to the
rappterbox console and a one-line instruction. The console drag-drops
the .egg in and mounts the embedded runtime.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import pathlib
import stat
import sys
import urllib.request
import zipfile
from collections.abc import Callable, Mapping
from pathlib import Path

try:
    from agents.basic_agent import BasicAgent
except ModuleNotFoundError:
    _REPO_ROOT = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(_REPO_ROOT / "rapp_brainstem"))
    from agents.basic_agent import BasicAgent


__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/egg_hatcher",
    "version": "1.1.0",
    "display_name": "EggHatcher",
    "description": "Historical .egg cartridge router restored for deterministic local inspection. URL reads and every hatch/write route are default-off behind reviewed dependency injection, exact target receipts, and fresh authenticated section-13 evidence.",
    "author": "RAPP",
    "tags": ["egg", "cartridge", "hatch", "organism", "rapplication", "lifecycle"],
    "category": "core",
    "quality_tier": "official",
    "requires_env": [],
    "dependencies": ["@rapp/basic_agent"],
    "example_call": {"args": {"egg_path": "~/Downloads/dad.egg"}},
}


RAPPTERBOX_CONSOLE_URL = "https://kody-w.github.io/rappterbox/console.html"
VBRAINSTEM_URL = "https://kody-w.github.io/RAPP/pages/vbrainstem.html"
HISTORICAL_SOURCE = {
    "path": "pages/tutorials/egg_hatcher_agent.py",
    "commit": "f715eb3e6d4b473bbc34c472d3ad60cf6a2e144f",
    "blob": "be409f4f5c7d821e6573d182a34a663442177961",
    "sha256": "bdd2b796aeac17d01a8c675acf8dfcf717aaa29601451aefccf7feffe6b8cf04",
    "bytes": 14962,
}
TARGET_RECEIPT_SCHEMA = "rapp-effect-target-receipt/1.0"
MAX_EGG_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024


class EggEffectRefused(RuntimeError):
    def __init__(self, code: str, step: str):
        super().__init__(f"{code}: {step}")
        self.code = code
        self.step = step


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


def network_read_target(egg_url: str) -> dict[str, object]:
    return {
        "url": egg_url,
        "maximum_bytes": MAX_EGG_BYTES,
        "purpose": "legacy-egg-inspection",
    }


def _strict_json_loads(text: str | bytes):
    def reject_constant(value):
        raise ValueError(f"non-finite JSON number: {value}")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON member: {key}")
            result[key] = value
        return result

    return json.loads(
        text,
        parse_constant=reject_constant,
        object_pairs_hook=unique_object,
    )


def _optional_string(manifest: dict, name: str) -> None:
    if name in manifest and type(manifest[name]) is not str:
        raise ValueError(f"manifest.{name} must be a string")


def _validate_manifest(manifest: dict) -> None:
    if type(manifest) is not dict:
        raise ValueError("egg manifest must be a JSON object")
    _optional_string(manifest, "schema")
    _optional_string(manifest, "type")
    for name in (
        "name",
        "title",
        "rappid",
        "display_name",
        "neighborhood_url",
        "neighborhood_json",
        "tether_url",
        "soul_summary",
    ):
        _optional_string(manifest, name)

    kind = _route_kind(manifest)
    if kind == "session":
        runtime = manifest.get("runtime", {})
        if type(runtime) is not dict:
            raise ValueError("manifest.runtime must be an object")
        for name in ("type", "sha256", "payload"):
            if name in runtime and type(runtime[name]) is not str:
                raise ValueError(f"manifest.runtime.{name} must be a string")
        transcript = manifest.get("transcript", [])
        if type(transcript) is not list:
            raise ValueError("manifest.transcript must be an array")
        participants = manifest.get("participants", [])
        if type(participants) is not list:
            raise ValueError("manifest.participants must be an array")
        for participant in participants:
            if type(participant) is not dict:
                raise ValueError("every participant must be an object")
            if "name" in participant and type(participant["name"]) is not str:
                raise ValueError("participant.name must be a string")


def _historical_read_bytes(egg_path: str) -> bytes:
    """Load egg bytes from a local path or URL. Hatcher accepts both."""
    if egg_path.startswith(("http://", "https://")):
        with urllib.request.urlopen(egg_path, timeout=30) as r:
            return r.read()
    p = pathlib.Path(os.path.expanduser(egg_path))
    if not p.exists():
        raise FileNotFoundError(f"egg not found: {egg_path}")
    return p.read_bytes()


def _read_bytes(
    egg_path: str,
    *,
    dependencies: Mapping[str, object] | None = None,
    target_receipt: Mapping[str, object] | None = None,
    authority_evidence: Mapping[str, object] | None = None,
) -> bytes:
    """Read a regular local file, or a receipt-bound injected URL reader."""
    if egg_path.startswith(("http://", "https://")):
        target = network_read_target(egg_path)
        refusal = authorize_effect(
            operation="legacy-egg-network-read",
            target=target,
            dependencies=dependencies,
            target_receipt=target_receipt,
            authority_evidence=authority_evidence,
        )
        if refusal is not None:
            raise EggEffectRefused(refusal["code"], refusal["step"])
        reader = dependencies.get("network_reader")
        if not isinstance(reader, Callable):
            raise EggEffectRefused(
                "reviewed-dependency-injection-required",
                "network-reader",
            )
        blob = reader(egg_path, MAX_EGG_BYTES)
        if not isinstance(blob, bytes) or len(blob) > MAX_EGG_BYTES:
            raise ValueError("injected network reader returned invalid egg bytes")
        return blob

    path = pathlib.Path(os.path.expanduser(egg_path))
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise FileNotFoundError(
                f"egg is not a regular local file: {egg_path}"
            )
        if metadata.st_size > MAX_EGG_BYTES:
            raise ValueError(f"egg exceeds {MAX_EGG_BYTES} bytes")
        chunks = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, MAX_EGG_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_EGG_BYTES:
                raise ValueError(f"egg exceeds {MAX_EGG_BYTES} bytes")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _introspect(blob: bytes) -> dict:
    """Sniff the egg shape: JSON-only (session) vs ZIP (organism/rapplication/etc)."""
    if not isinstance(blob, bytes) or len(blob) > MAX_EGG_BYTES:
        raise ValueError("egg bytes are missing or exceed the inspection limit")
    # Try JSON first — session cartridges are bare JSON
    try:
        text = blob.decode("utf-8")
        manifest = _strict_json_loads(text)
        if isinstance(manifest, dict) and (
            manifest.get("schema", "").startswith("brainstem-egg/")
            or manifest.get("schema") == "rappterbox-cart/0.1"
        ):
            _validate_manifest(manifest)
            return {"container": "json", "manifest": manifest}
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    # Else try ZIP
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            info = z.getinfo("manifest.json")
            if info.flag_bits & 0x1:
                raise ValueError("encrypted egg manifests are not inspectable")
            if info.file_size > MAX_MANIFEST_BYTES:
                raise ValueError("egg manifest exceeds the inspection limit")
            with z.open("manifest.json") as f:
                manifest_bytes = f.read(MAX_MANIFEST_BYTES + 1)
            if len(manifest_bytes) > MAX_MANIFEST_BYTES:
                raise ValueError("egg manifest exceeds the inspection limit")
            manifest = _strict_json_loads(manifest_bytes)
            _validate_manifest(manifest)
            return {"container": "zip", "manifest": manifest, "zip_bytes": blob}
    except (zipfile.BadZipFile, KeyError) as e:
        raise ValueError(f"egg has no recognizable manifest (not JSON, not a ZIP with manifest.json): {e}")


def _route_session(manifest: dict) -> str:
    """Session cartridges mount in rappterbox console — Python brainstem can't iframe."""
    name = manifest.get("name") or "session"
    title = manifest.get("title") or name
    rappid = manifest.get("rappid", "(no rappid)")
    runtime = manifest.get("runtime") or {}
    sha = runtime.get("sha256", "(no sha)")[:16]
    runtime_size = len(runtime.get("payload", ""))
    transcript_n = len(manifest.get("transcript") or [])
    parts = manifest.get("participants") or []
    parts_str = ", ".join(p.get("name", "?") for p in parts) or "(none)"
    return (
        f"Session cartridge identified: '{title}' ({name})\n"
        f"  rappid: {rappid}\n"
        f"  runtime: {runtime.get('type','?')} · sha256={sha}… · {runtime_size:,} bytes\n"
        f"  transcript: {transcript_n} events\n"
        f"  participants: {parts_str}\n"
        f"\n"
        f"Session cartridges run in a console (browser iframe), not in the Python brainstem.\n"
        f"To mount this cartridge:\n"
        f"  1. Open {RAPPTERBOX_CONSOLE_URL} (or {VBRAINSTEM_URL})\n"
        f"  2. Go to the 'Tether Carts' blade (rappterbox) or just drag the file onto the page\n"
        f"  3. Click 'Load .cart.json' / drop the .egg file in\n"
        f"  4. The runtime mounts in a sandboxed iframe; sha256 is verified against the manifest\n"
    )


def _historical_route_organism(manifest: dict, blob: bytes) -> str:
    """Organism cartridges hatch into ~/.rapp/twins/<rappid>/ via utils.bond."""
    rappid = manifest.get("rappid", "(no rappid)")
    try:
        from utils.bond import hatch_organism  # type: ignore
    except ImportError:
        return (
            f"Organism cartridge identified: rappid={rappid}\n"
            f"This brainstem doesn't have utils.bond.hatch_organism available. "
            f"Run a kernel that does (rapp_brainstem v0.4+) or extract the ZIP manually:\n"
            f"  unzip the .egg into ~/.rapp/twins/<rappid>/\n"
            f"  then: bash ~/.brainstem/start.sh --port <free-port> with SOUL_PATH/AGENTS_PATH "
            f"pointed at that twin dir."
        )
    try:
        out = hatch_organism(blob)
        return f"Organism cartridge hatched. rappid={rappid}\n{out}"
    except Exception as e:
        return f"Organism hatch failed: {e}"


def _historical_route_rapplication(manifest: dict, blob: bytes) -> str:
    """Rapplication cartridges install as a planted rapp under host brainstem."""
    rappid = manifest.get("rappid", "(no rappid)")
    try:
        from utils.bond import hatch_rapplication  # type: ignore
    except ImportError:
        return (
            f"Rapplication cartridge identified: rappid={rappid}\n"
            f"This brainstem doesn't have utils.bond.hatch_rapplication available. "
            f"Run a kernel that does (rapp_brainstem v0.4+) or extract the ZIP into "
            f"~/.brainstem/rapps/<name>/ manually."
        )
    try:
        out = hatch_rapplication(blob)
        return f"Rapplication cartridge installed. rappid={rappid}\n{out}"
    except Exception as e:
        return f"Rapplication hatch failed: {e}"


def _historical_route_neighborhood(manifest: dict) -> str:
    """Neighborhood eggs are JOIN invites — they append the operator's two-tier
    estate's `member[]` with `{rappid, added_at, via: "egg"}` per Article XLVI.
    The egg carries the neighborhood's canonical URLs; the operator's brainstem
    fetches the full neighborhood.json from there going forward.
    """
    import datetime as _dt
    rappid = manifest.get("rappid")
    if not rappid:
        return "Neighborhood egg invalid: no rappid in manifest. Refusing to join."
    # Light format check — Article XLVI forbids fallback parsers, but the
    # real parser is in the RAPP-side tools/door_address.py; if available we
    # use it, otherwise we accept any non-empty string and let the brainstem's
    # own validator reject malformed entries on next estate rebuild.
    try:
        from door_address import door_from_rappid, InvalidRappidError  # type: ignore
        try:
            door_from_rappid(rappid)
        except InvalidRappidError as e:
            return f"Neighborhood egg invalid: malformed rappid '{rappid}' — {e}"
    except ImportError:
        pass

    name = manifest.get("display_name") or manifest.get("name") or rappid
    url = manifest.get("neighborhood_url") or ""
    nbhd_json = manifest.get("neighborhood_json") or ""
    tether = manifest.get("tether_url") or ""
    soul_summary = manifest.get("soul_summary") or ""

    # Locate the operator's two-tier estate file.
    estate_path = os.path.expanduser("~/.brainstem/estate.json")
    estate_dir = os.path.dirname(estate_path)
    try:
        os.makedirs(estate_dir, exist_ok=True)
    except Exception as e:
        return f"Could not create {estate_dir}: {e}"

    # Load existing estate or seed a minimal skeleton. The skeleton is
    # incomplete (no owner.rappid until the operator's identity is known),
    # so we don't write a skeleton unilaterally — instead we ask the operator
    # to bootstrap their estate first via `tools/rebuild_estate.py`.
    if not os.path.exists(estate_path):
        return (
            f"No estate file at {estate_path}. Bootstrap yours first:\n"
            f"  python3 tools/rebuild_estate.py --handle <your-gh> --apply\n"
            f"Then re-hatch this neighborhood egg to join {name}.\n"
        )

    try:
        estate = json.loads(pathlib.Path(estate_path).read_text())
    except Exception as e:
        return f"Couldn't read {estate_path}: {e}"

    member = estate.get("member") or []
    if not isinstance(member, list):
        return f"Estate file shape unexpected: 'member' is {type(member).__name__}, expected list."

    # Idempotent: already joined?
    if any(isinstance(m, dict) and m.get("rappid") == rappid for m in member):
        msg = f"Already a member of {name} (rappid={rappid})."
        if tether:
            msg += f"\nTether: {tether}"
        return msg

    # Append per Article XLVI: ONLY rappid + added_at + via.
    member.append({
        "rappid":   rappid,
        "added_at": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "via":      "egg",
    })
    estate["member"] = member
    estate["updated_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")

    try:
        pathlib.Path(estate_path).write_text(json.dumps(estate, indent=2) + "\n")
    except Exception as e:
        return f"Joined in-memory but could not write {estate_path}: {e}"

    lines = [
        f"Joined neighborhood: {name}",
        f"  rappid:    {rappid}",
    ]
    if url:
        lines.append(f"  homepage:  {url}")
    if nbhd_json:
        lines.append(f"  manifest:  {nbhd_json}")
    if tether:
        lines.append(f"  tether:    {tether}  ← go here to chat with the neighborhood")
    if soul_summary:
        lines.append("")
        lines.append(f"  {soul_summary}")
    lines.append("")
    lines.append(f"Wrote {estate_path}. Total memberships: {len(member)}.")
    return "\n".join(lines)


def _route_organism(manifest: dict, blob: bytes) -> str:
    del blob
    return (
        f"Organism cartridge identified: rappid={manifest.get('rappid', '(no rappid)')}\n"
        "Plan only: preserve the legacy utils.bond hatch algorithm, but do not "
        "extract, install, start, or write without authenticated apply injection."
    )


def _route_rapplication(manifest: dict, blob: bytes) -> str:
    del blob
    return (
        f"Rapplication cartridge identified: rappid={manifest.get('rappid', '(no rappid)')}\n"
        "Plan only: preserve the planted-rapp installation algorithm, but do not "
        "extract or write into a host brainstem without authenticated apply injection."
    )


def _route_neighborhood(manifest: dict) -> str:
    name = (
        manifest.get("display_name")
        or manifest.get("name")
        or manifest.get("rappid")
        or "(unnamed)"
    )
    return (
        f"Neighborhood cartridge identified: {name}\n"
        "Plan only: the Article XLVI estate-membership algorithm is preserved, "
        "but no directory or estate.json mutation occurs during inspection."
    )


def _route_estate(manifest: dict) -> str:
    """Estate cartridges re-anchor on a new substrate. Planned — not yet wired."""
    rappid = manifest.get("rappid", "(no rappid)")
    return (
        f"Estate cartridge identified: rappid={rappid}\n"
        f"Estate hatching is on the v0.4 roadmap (kody-w/rappterbox/carts/SCHEMA.md).\n"
        f"Estate eggs carry the operator's whole multi-tier identity (public discovery + "
        f"private bones pointer + sealed PII pointer) for substrate migration "
        f"(GitHub → GitLab, GitHub → Codeberg, etc.).\n"
        f"For now, manual migration: see PUBLIC_PRIVATE_BOUNDARY.md §1.6 override paths."
    )


def _route_unknown(manifest: dict) -> str:
    schema = manifest.get("schema", "(unknown)")
    kind = manifest.get("type", "(no type)")
    return (
        f"Unknown egg cartridge: schema='{schema}' type='{kind}'.\n"
        f"This hatcher knows: organism, rapplication, session, neighborhood.\n"
        f"Planned: estate.\n"
        f"See kody-w/rappterbox/carts/SCHEMA.md for the cartridge family.\n"
        f"NOT routing — refusing to guess. Operator action required."
    )


def _route_kind(manifest: dict) -> str:
    schema = manifest.get("schema", "")
    kind = manifest.get("type", "")
    if schema in ("brainstem-egg/2.3-session", "rappterbox-cart/0.1") or kind == "session":
        return "session"
    if "organism" in schema or kind == "organism":
        return "organism"
    if "rapplication" in schema or kind == "rapplication":
        return "rapplication"
    if "neighborhood" in schema or kind == "neighborhood":
        return "neighborhood"
    if "estate" in schema or kind == "estate":
        return "estate"
    return "unknown"


def _route_plan(kind: str, manifest: dict, blob: bytes) -> str:
    if kind == "session":
        return _route_session(manifest)
    if kind == "organism":
        return _route_organism(manifest, blob)
    if kind == "rapplication":
        return _route_rapplication(manifest, blob)
    if kind == "neighborhood":
        return _route_neighborhood(manifest)
    if kind == "estate":
        return _route_estate(manifest)
    return _route_unknown(manifest)


def inspection_result(info: dict, blob: bytes) -> dict:
    manifest = info["manifest"]
    _validate_manifest(manifest)
    kind = _route_kind(manifest)
    return {
        "schema": "rapp-legacy-egg-inspection/1.0",
        "mode": "inspect",
        "container": info["container"],
        "egg_sha256": hashlib.sha256(blob).hexdigest(),
        "egg_bytes": len(blob),
        "manifest": manifest,
        "route": kind,
        "plan": _route_plan(kind, manifest, blob),
        "accepted": False,
        "effects": [],
        "historical_source": HISTORICAL_SOURCE,
    }


def _normalized_destination(
    route: str,
    destination: Mapping[str, object],
) -> dict[str, str]:
    if route not in {"organism", "rapplication", "neighborhood"}:
        raise ValueError(f"route {route!r} has no Python apply operation")
    if set(destination) != {"kind", "path"}:
        raise ValueError("destination must contain exactly kind and path")
    kind = destination.get("kind")
    path = destination.get("path")
    expected_kind = (
        "neighborhood-membership"
        if route == "neighborhood"
        else route
    )
    if kind != expected_kind or type(path) is not str or not path:
        raise ValueError(
            f"destination must name kind={expected_kind!r} and a path"
        )
    normalized_path = str(Path(path).expanduser().resolve())
    if route == "neighborhood":
        expected_path = str(
            (Path.home() / ".brainstem" / "estate.json").resolve()
        )
        if normalized_path != expected_path:
            raise ValueError(
                "neighborhood apply target must be the exact estate.json path"
            )
    return {"kind": expected_kind, "path": normalized_path}


def hatch_target(info: dict, blob: bytes, destination: Mapping[str, object]) -> dict:
    manifest = info["manifest"]
    _validate_manifest(manifest)
    route = _route_kind(manifest)
    normalized_destination = _normalized_destination(route, destination)
    manifest_bytes = json.dumps(
        manifest,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return {
        "route": route,
        "container": info["container"],
        "egg_sha256": hashlib.sha256(blob).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "destination": normalized_destination,
    }


def apply_hatch(
    info: dict,
    blob: bytes,
    *,
    destination: Mapping[str, object] | None,
    dependencies: Mapping[str, object] | None,
    target_receipt: Mapping[str, object] | None,
    authority_evidence: Mapping[str, object] | None,
) -> dict:
    if not isinstance(destination, Mapping) or not destination:
        return {
            "schema": "rapp-legacy-egg-apply/1.0",
            "ok": False,
            "applied": False,
            "effects_started": False,
            "error": {
                "code": "exact-target-receipt-required",
                "step": "destination",
            },
        }
    try:
        target = hatch_target(info, blob, destination)
    except (TypeError, ValueError) as exc:
        return {
            "schema": "rapp-legacy-egg-apply/1.0",
            "ok": False,
            "applied": False,
            "effects_started": False,
            "error": {
                "code": "exact-target-receipt-required",
                "step": str(exc),
            },
        }
    refusal = authorize_effect(
        operation="legacy-egg-hatch",
        target=target,
        dependencies=dependencies,
        target_receipt=target_receipt,
        authority_evidence=authority_evidence,
    )
    if refusal is not None:
        return {
            "schema": "rapp-legacy-egg-apply/1.0",
            "ok": False,
            "applied": False,
            "effects_started": False,
            "error": refusal,
            "target": target,
        }
    executor = dependencies.get("hatch_executor")
    if not isinstance(executor, Callable):
        return {
            "schema": "rapp-legacy-egg-apply/1.0",
            "ok": False,
            "applied": False,
            "effects_started": False,
            "error": {
                "code": "reviewed-dependency-injection-required",
                "step": "hatch-executor",
            },
            "target": target,
        }
    manifest_snapshot = json.dumps(
        info["manifest"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    target_snapshot = json.dumps(
        target,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return executor(
        target["route"],
        manifest_snapshot,
        bytes(blob),
        target_snapshot,
    )


class EggHatcherAgent(BasicAgent):
    def __init__(self):
        self.name = "HatchEgg"
        self.metadata = {
            "name": self.name,
            "description": (
                "Inspect a local historical .egg cartridge and produce a deterministic "
                "route plan. URL reads and apply mode require reviewed dependency injection, "
                "an exact target receipt, and fresh authenticated section-13 evidence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "egg_path": {
                        "type": "string",
                        "description": (
                            "Local file path (e.g. /Volumes/usb/dad.egg, ~/Downloads/foo.egg) "
                            "or a gated HTTP/HTTPS URL to a .egg cartridge."
                        ),
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["inspect", "plan", "apply"],
                        "description": "Default inspect is local and inert; apply is gated.",
                    },
                    "destination": {
                        "type": "object",
                        "description": "Exact reviewed destination object required for apply.",
                    },
                },
                "required": ["egg_path"],
            },
        }
        super().__init__(self.name, self.metadata)

    def perform(self, **kwargs) -> str:
        egg_path_value = kwargs.get("egg_path", "")
        egg_path = egg_path_value.strip() if isinstance(egg_path_value, str) else ""
        if not egg_path:
            return json.dumps({
                "schema": "rapp-legacy-egg-inspection/1.0",
                "ok": False,
                "error": {
                    "code": "egg-path-required",
                    "step": "input",
                },
                "effects": [],
            }, indent=2, sort_keys=True)
        mode = kwargs.get("mode") or "inspect"
        if mode not in {"inspect", "plan", "apply"}:
            return json.dumps({
                "schema": "rapp-legacy-egg-inspection/1.0",
                "ok": False,
                "error": {
                    "code": "invalid-mode",
                    "step": "input",
                },
                "effects": [],
            }, indent=2, sort_keys=True)
        dependencies = kwargs.get("_dependencies")
        network_receipts = (
            dependencies.get("network_target_receipts")
            if isinstance(dependencies, Mapping)
            else None
        )
        network_receipt = kwargs.get("_network_target_receipt")
        if (
            network_receipt is None
            and isinstance(network_receipts, Mapping)
        ):
            network_receipt = network_receipts.get(egg_path)
        network_evidence = (
            dependencies.get("network_authority_evidence")
            if isinstance(dependencies, Mapping)
            else None
        )
        try:
            blob = _read_bytes(
                egg_path,
                dependencies=dependencies,
                target_receipt=network_receipt,
                authority_evidence=network_evidence,
            )
        except EggEffectRefused as exc:
            return json.dumps({
                "schema": "rapp-legacy-egg-inspection/1.0",
                "ok": False,
                "read": False,
                "effects_started": False,
                "error": {"code": exc.code, "step": exc.step},
            }, indent=2, sort_keys=True)
        except Exception as e:
            return json.dumps({
                "schema": "rapp-legacy-egg-inspection/1.0",
                "ok": False,
                "read": False,
                "effects_started": False,
                "error": {
                    "code": "egg-read-failed",
                    "step": str(e),
                },
            }, indent=2, sort_keys=True)
        try:
            info = _introspect(blob)
        except Exception as e:
            return json.dumps({
                "schema": "rapp-legacy-egg-inspection/1.0",
                "ok": False,
                "read": True,
                "effects_started": False,
                "error": {
                    "code": "egg-introspection-failed",
                    "step": str(e),
                },
            }, indent=2, sort_keys=True)

        if mode in {"inspect", "plan"}:
            try:
                result = inspection_result(info, blob)
            except (AttributeError, TypeError, ValueError) as exc:
                return json.dumps({
                    "schema": "rapp-legacy-egg-inspection/1.0",
                    "ok": False,
                    "read": True,
                    "effects_started": False,
                    "error": {
                        "code": "egg-introspection-failed",
                        "step": str(exc),
                    },
                }, indent=2, sort_keys=True)
            result["mode"] = mode
            result["ok"] = True
            return json.dumps(result, indent=2, sort_keys=True)

        result = apply_hatch(
            info,
            blob,
            destination=kwargs.get("destination"),
            dependencies=dependencies,
            target_receipt=kwargs.get("_target_receipt"),
            authority_evidence=kwargs.get("_authority_evidence"),
        )
        return json.dumps(result, indent=2, sort_keys=True)


def inspection_report() -> dict:
    return {
        "schema": "rapp-legacy-egg-hatcher-inspection/1.0",
        "mode": "inspect",
        "local_file_inspection": True,
        "network_read": False,
        "hatch_apply": False,
        "historical_source": HISTORICAL_SOURCE,
        "effects": [],
        "accepted": False,
    }


if __name__ == "__main__":
    print(json.dumps(inspection_report(), indent=2, sort_keys=True))
