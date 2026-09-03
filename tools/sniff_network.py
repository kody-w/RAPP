"""Collect complete, source-labelled RAPP network publication observations.

Publication does not establish identity, membership, compliance, or RAPP/1
acceptance. Every record carries the parsed publication payload and retrieval
provenance separately from ``accepted: false``. This repository has no
implementation that authenticates fresh section-13 registry evidence, so this
tool observes fully while refusing acceptance.

PURE-RAW DISCOVERY (default — no GitHub API rate limits):
    1. Fetch the well-known seed at
       https://raw.githubusercontent.com/kody-w/RAPP/main/.well-known/rapp-network-seed.json
    2. For each operator listed there, fetch their `.well-known/rapp-network.json`
       beacon at <handle>/rapp-estate/main/.well-known/rapp-network.json
    3. Each beacon's `discovery.federation_hints[]` adds more handles to the queue
    4. BFS until no new nodes
    5. Optionally fetch each estate.json for a full inventory

ALL raw.githubusercontent.com URLs. No `gh search`. No API token. No rate limit
concerns at our scale (raw is CDN-fronted; topic search would lag minutes-to-hours).

OPTIONAL TOPIC FALLBACK (--via topic):
    Uses `gh search repos topic:rapp-estate` to catch operators who aren't
    in any federation hint chain. Eventually-consistent; useful as a sweep.

USAGE:
    python3 tools/sniff_network.py                       # raw BFS, print summary
    python3 tools/sniff_network.py --json                # full envelope
    python3 tools/sniff_network.py --out observations.json \
        --owner-approval /path/to/approval.json
    python3 tools/sniff_network.py --seed-url <url>      # start from a different seed
    python3 tools/sniff_network.py --max-hops 5          # cap BFS depth (default 10)
    python3 tools/sniff_network.py --via topic           # use gh search instead (slower, lags)
    python3 tools/sniff_network.py --include-private     # ignore beacon opt-out flag

Stdlib only for --via raw (the default). gh CLI only for --via topic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "tools"))

from door_address import door_from_rappid, InvalidRappidError, estate_url  # noqa: E402
from rapp1_core import strict_loads  # noqa: E402


_TOPIC = "rapp-estate"
_BEACON_PATH = ".well-known/rapp-network.json"
_BEACON_SCHEMA_VERSIONS = {"rapp-network-beacon/1.0", "rapp-network-beacon/1.1"}
_SEED_SCHEMA = "rapp-network-seed/1.0"
_DEFAULT_SEED_URL = "https://raw.githubusercontent.com/kody-w/RAPP/main/.well-known/rapp-network-seed.json"
_FETCH_TIMEOUT = 8
_SNIFF_SCHEMA = "rapp-network-sniff/1.0"
_APPROVAL_SCHEMA = "rapp-tool-owner-approval/1.0"
_ACCEPTANCE_REASON = (
    "Authenticated, fresh RAPP/1 section-13 registry evidence verification "
    "is not implemented; publication observations cannot be accepted."
)


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _parsed_payload_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _provenance(
    *,
    url: str,
    source: str,
    discovered_via: str,
    status: str = "observed",
    **extra,
) -> dict:
    return {
        "url": url,
        "source": source,
        "discovered_via": discovered_via,
        "status": status,
        "observed_at": _now_iso(),
        **extra,
    }


def _unavailable(via: str, detail: str, **extra) -> dict:
    return {
        "schema": _SNIFF_SCHEMA,
        "authority_state": "unverified-observation",
        "rapp_protocol_authority": False,
        "via": via,
        "ok": False,
        "accepted": False,
        "status": "UNAVAILABLE",
        "observation_complete": False,
        "error": {
            "code": "observation-unavailable",
            "detail": detail,
        },
        "acceptance_error": {
            "code": "authenticated-registry-unavailable",
            "detail": _ACCEPTANCE_REASON,
        },
        **extra,
    }


def _unverified_record(**published_observation) -> dict:
    return {
        **published_observation,
        "accepted": False,
        "status": "UNVERIFIED",
        "verification": {
            "section_13_authenticated": False,
            "freshness_verified": False,
            "reason": _ACCEPTANCE_REASON,
        },
    }


def _unverified_envelope(
    via: str,
    observations: list[dict],
    skipped: list[dict],
    **extra,
) -> dict:
    published_door_claim_count = sum(
        observation.get("published_created_claim_count", 0)
        + observation.get("published_member_claim_count", 0)
        for observation in observations
    )
    return {
        "schema": _SNIFF_SCHEMA,
        "authority_state": "unverified-observation",
        "rapp_protocol_authority": False,
        "via": via,
        "ok": True,
        "accepted": False,
        "status": "OBSERVED_UNVERIFIED",
        "observation_complete": True,
        "acceptance_error": {
            "code": "authenticated-registry-unavailable",
            "detail": _ACCEPTANCE_REASON,
        },
        "observations_count": len(observations),
        "observations_skipped": len(skipped),
        "published_door_claim_count": published_door_claim_count,
        "observations": observations,
        "skipped": skipped,
        "sniffed_at": _now_iso(),
        **extra,
    }


def _raw_get_json(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "rapp-network-sniffer/1.0"})
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as r:
            return json.loads(r.read())
    except Exception:
        return None


def fetch_seed(seed_url: str) -> dict | None:
    d = _raw_get_json(seed_url)
    if not isinstance(d, dict):
        return None
    if d.get("schema") != _SEED_SCHEMA:
        return None
    return d


def _substrate_label(url: str) -> str:
    """Short human-readable label for the substrate a URL serves on.
    Used in sniff progress + record fields so operators see which substrate
    each node was reached through (Article XLVII.5)."""
    if not url:
        return "?"
    if url.startswith("https://raw.githubusercontent.com/"):
        return "github-raw"
    if url.startswith("file://"):
        return "file"
    if url.startswith(("http://192.168.", "http://10.", "http://172.16.",
                       "http://172.17.", "http://172.18.", "http://172.19.",
                       "http://172.2", "http://172.30.", "http://172.31.",
                       "http://localhost", "http://127.")):
        return "lan-http"
    if url.startswith("http://"):
        return "http"
    if url.startswith("https://"):
        return "https"
    return "other"


def github_beacon_url(handle: str) -> str:
    """The canonical GitHub-substrate beacon URL for a handle (Article XLVII)."""
    return f"https://raw.githubusercontent.com/{handle}/rapp-estate/main/{_BEACON_PATH}"


def github_estate_url(handle: str) -> str:
    """The canonical GitHub-substrate estate URL for a handle (Article XLVII)."""
    return f"https://raw.githubusercontent.com/{handle}/rapp-estate/main/estate.json"


def fetch_beacon_at_url(url: str) -> dict | None:
    """Fetch a beacon from ANY URL (Article XLVII.5 substrate-agnostic).

    Same JSON contract whether it's served from raw.githubusercontent.com,
    a LAN HTTP server (http://192.168.x.x:8080/...), a file:// URL, or any
    other substrate that serves the canonical beacon JSON.
    """
    d = _raw_get_json(url)
    if not isinstance(d, dict):
        return None
    if d.get("schema") not in _BEACON_SCHEMA_VERSIONS:
        return None
    return d


def fetch_estate_at_url(url: str) -> dict | None:
    """Fetch an estate from ANY URL (Article XLVII.5 substrate-agnostic)."""
    d = _raw_get_json(url)
    return d if isinstance(d, dict) else None


# Backward-compatible aliases for the github-substrate path
def fetch_beacon_for_handle(handle: str) -> dict | None:
    return fetch_beacon_at_url(github_beacon_url(handle))


def fetch_estate_for_handle(handle: str) -> dict | None:
    return fetch_estate_at_url(github_estate_url(handle))


def _resolve_node(entry) -> tuple[str, str, str]:
    """Normalize a seed/hint entry into (handle, beacon_url, estate_url).

    Entry can be:
      - "<handle>" (string) → uses canonical github raw URLs
      - {"github": "<handle>"} (dict) → uses canonical github raw URLs
      - {"github": "<handle>", "beacon_url": "<url>", "estate_url": "<url>"}
        (dict) → uses provided URLs (Article XLVII.5 substrate override)
      - {"beacon_url": "<url>", "estate_url": "<url>"} (dict, no handle) →
        anonymous LAN/local node; handle defaults to first part of URL host

    Substrate-agnostic: same JSON shapes wherever they're served.
    """
    if isinstance(entry, str):
        h = entry
        return h, github_beacon_url(h), github_estate_url(h)
    if isinstance(entry, dict):
        handle = entry.get("github") or entry.get("handle") or ""
        beacon_url = entry.get("beacon_url") or (github_beacon_url(handle) if handle else "")
        estate_url = entry.get("estate_url") or (github_estate_url(handle) if handle else "")
        if not handle and beacon_url:
            # Derive a label from the URL host so the queue/visited set works
            try:
                from urllib.parse import urlparse
                handle = f"@{urlparse(beacon_url).netloc}"
            except Exception:
                handle = beacon_url
        return handle, beacon_url, estate_url
    return "", "", ""


# ─── Pure-raw BFS sniffer ──────────────────────────────────────────────────

def sniff_via_raw(seed_url: str = _DEFAULT_SEED_URL,
                   max_hops: int = 10,
                   include_private: bool = False,
                   fetch_estates: bool = True,
                   on_progress=None) -> dict:
    """BFS from a seed across operator beacons. All raw URLs."""
    seed = fetch_seed(seed_url)
    if not seed:
        return _unavailable(
            "raw",
            f"could not fetch seed publication at {seed_url}",
            seed_url=seed_url,
        )

    if on_progress:
        on_progress(f"seed loaded: {len(seed.get('operators', []))} initial operators")

    # BFS state — each queued node carries its OWN beacon_url + estate_url so
    # the substrate (github raw, LAN HTTP, file://, etc.) can vary per-node
    # (Article XLVII.5 substrate-agnostic federation).
    queue: deque[tuple[str, str, str, int, str]] = deque()  # (handle, beacon_url, estate_url, hop, source)
    visited: set[str] = set()
    operators: list[dict] = []
    skipped: list[dict] = []

    # Seed operators — accept either bare strings or {github, beacon_url, estate_url} dicts
    for op in seed.get("operators", []):
        handle, b_url, e_url = _resolve_node(op)
        if handle and b_url:
            queue.append((handle, b_url, e_url, 0, "seed"))

    while queue:
        handle, beacon_url, estate_url, hop, source = queue.popleft()
        if handle in visited:
            continue
        visited.add(handle)
        if hop > max_hops:
            skipped.append(
                {
                    "handle": handle,
                    "reason": f"max_hops={max_hops} exceeded",
                    "accepted": False,
                    "provenance": _provenance(
                        url=beacon_url,
                        source=_substrate_label(beacon_url),
                        discovered_via=source,
                        status="not-fetched",
                        hop=hop,
                    ),
                }
            )
            continue

        if on_progress:
            on_progress(f"hop {hop}: {handle} (via {source}, substrate: {_substrate_label(beacon_url)})")

        beacon = fetch_beacon_at_url(beacon_url)
        if not beacon:
            skipped.append(
                {
                    "handle": handle,
                    "reason": f"no valid beacon at {beacon_url}",
                    "accepted": False,
                    "provenance": _provenance(
                        url=beacon_url,
                        source=_substrate_label(beacon_url),
                        discovered_via=source,
                        status="missing-or-invalid",
                        hop=hop,
                    ),
                }
            )
            continue

        indexable = bool(beacon.get("discovery", {}).get("indexable", True))
        if not indexable and not include_private:
            skipped.append(
                {
                    "handle": handle,
                    "reason": (
                        "discovery.indexable=false (opt-out honored)"
                    ),
                    "accepted": False,
                    "observed": {"beacon": beacon},
                    "provenance": _provenance(
                        url=beacon_url,
                        source=_substrate_label(beacon_url),
                        discovered_via=source,
                        hop=hop,
                        parsed_payload_sha256=_parsed_payload_sha256(beacon),
                    ),
                }
            )
            continue

        op_rappid = beacon.get("operator_rappid", "")
        try:
            door_from_rappid(op_rappid)
        except InvalidRappidError as e:
            skipped.append(
                {
                    "handle": handle,
                    "reason": (
                        f"operator_rappid invalid: {str(e)[:120]}"
                    ),
                    "accepted": False,
                    "observed": {"beacon": beacon},
                    "provenance": _provenance(
                        url=beacon_url,
                        source=_substrate_label(beacon_url),
                        discovered_via=source,
                        hop=hop,
                        parsed_payload_sha256=_parsed_payload_sha256(beacon),
                    ),
                }
            )
            continue

        effective_estate_url = beacon.get("estate_url") or estate_url
        record = _unverified_record(
            published_github=handle,
            published_operator_rappid=op_rappid,
            beacon_url=beacon_url,
            substrate=_substrate_label(beacon_url),
            published_estate_url=effective_estate_url,
            published_grail_url=beacon.get("grail_url", ""),
            published_protocol_claims=beacon.get("protocol", {}).get(
                "implements", []
            ),
            published_minted_at=beacon.get("minted_at"),
            published_indexable=indexable,
            discovered_via=source,
            hop=hop,
            observed={"beacon": beacon, "estate": None},
            provenance={
                "beacon": _provenance(
                    url=beacon_url,
                    source=_substrate_label(beacon_url),
                    discovered_via=source,
                    hop=hop,
                    parsed_payload_sha256=_parsed_payload_sha256(beacon),
                ),
                "estate": {
                    "url": effective_estate_url,
                    "status": "not-requested",
                    "observed_at": None,
                },
            },
        )

        # Article XLVIII: surface private extension presence WITHOUT fetching.
        # The beacon's private_estate_pointer + private_estate_commitment are
        # the only signals we report. The CONTENT of the private repo is never
        # touched — that's receiver-controls (XLVIII.4) + URL-opacity (XLVIII.6).
        priv_pointer = beacon.get("private_estate_pointer", "") or ""
        priv_commit  = beacon.get("private_estate_commitment", "") or ""
        priv_count   = beacon.get("private_door_count", 0)
        record["published_private_extension_pointer_present"] = bool(
            priv_pointer
        )
        record["published_private_estate_pointer"] = priv_pointer
        record["published_private_estate_commitment"] = priv_commit
        record["published_private_door_claim_count"] = priv_count

        if fetch_estates:
            est = (
                fetch_estate_at_url(effective_estate_url)
                if effective_estate_url
                else None
            )
            if est:
                record["published_created_claim_count"] = len(
                    est.get("created", []) or []
                )
                record["published_member_claim_count"] = len(
                    est.get("member", []) or []
                )
                record["observed"]["estate"] = est
                record["provenance"]["estate"] = _provenance(
                    url=effective_estate_url,
                    source=_substrate_label(effective_estate_url),
                    discovered_via=f"estate:{handle}",
                    parsed_payload_sha256=_parsed_payload_sha256(est),
                )
            else:
                record["provenance"]["estate"] = _provenance(
                    url=effective_estate_url,
                    source=_substrate_label(effective_estate_url),
                    discovered_via=f"estate:{handle}",
                    status="missing-or-invalid",
                )

        operators.append(record)

        # Enqueue this beacon's federation hints (substrate-agnostic per XLVII.5).
        # Hints can be bare handles OR {github, beacon_url, estate_url} dicts.
        hints = beacon.get("discovery", {}).get("federation_hints", []) or []
        for hint in hints:
            h_handle, h_beacon, h_estate = _resolve_node(hint)
            if h_handle and h_handle not in visited and h_beacon:
                queue.append((h_handle, h_beacon, h_estate, hop + 1, f"hint:{handle}"))

    return _unverified_envelope(
        "raw",
        operators,
        skipped,
        seed_url=seed_url,
        max_hops=max_hops,
        observed_seed=seed,
        seed_provenance=_provenance(
            url=seed_url,
            source=_substrate_label(seed_url),
            discovered_via="seed",
            parsed_payload_sha256=_parsed_payload_sha256(seed),
        ),
    )


# ─── Topic-search fallback (gh search repos) ──────────────────────────────

def _gh(args: list[str]) -> tuple[int, str, str]:
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True)
    except FileNotFoundError:
        return 127, "", "gh CLI is not installed"
    return p.returncode, p.stdout, p.stderr


def sniff_via_bonjour(browse_seconds: int = 3, include_private: bool = False,
                       fetch_estates: bool = True, on_progress=None) -> dict:
    """LAN-substrate discovery via Bonjour/mDNS (Article XLVII.5).

    The LAN equivalent of `topic:rapp-estate` is the Bonjour service type
    `_rapp-estate._tcp.local`. Brainstems advertise themselves via
    `tools/lan_advertise.py` (which calls `dns-sd -R`); sniffers discover via
    `dns-sd -B _rapp-estate._tcp local.`.

    For each discovered service, resolve its host:port + TXT records via
    `dns-sd -L`, derive the LAN HTTP beacon URL, then walk it through the
    same substrate-agnostic BFS as github-substrate (substrate label = "lan-http").
    """
    if not shutil.which("dns-sd"):
        return _unavailable(
            "bonjour",
            "dns-sd CLI not found (required for Bonjour observation)",
        )

    if on_progress:
        on_progress(f"browsing _rapp-estate._tcp.local for {browse_seconds}s…")

    # Step 1: Browse for service instances
    browse = subprocess.Popen(
        ["dns-sd", "-B", "_rapp-estate._tcp", "local."],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
    )
    time.sleep(browse_seconds)
    try:
        browse.terminate()
        browse_out, _ = browse.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        browse.kill()
        browse_out, _ = browse.communicate()

    # Parse out service instance names. dns-sd -B output lines look like:
    #   23:03:39.723  Add        3  14 local.               _http._tcp.          NAS8C4560
    # Columns: timestamp, A/R, flags, interface, domain, service_type, instance_name
    instance_names: list[str] = []
    for line in browse_out.splitlines():
        parts = line.split()
        # Match the "Add" rows for our service type. Service type is parts[5]
        # (after timestamp, A/R, flags, interface, domain). Name is parts[6:].
        if (len(parts) >= 7
                and parts[1] in ("Add", "Adding")
                and parts[5].startswith("_rapp-estate._tcp")):
            name = " ".join(parts[6:])
            if name and name not in instance_names:
                instance_names.append(name)

    if on_progress:
        on_progress(f"found {len(instance_names)} Bonjour service(s): {', '.join(instance_names) or '(none)'}")

    operators: list[dict] = []
    skipped: list[dict] = []

    # Step 2: For each instance, resolve to host:port + TXT records
    for name in instance_names:
        if on_progress:
            on_progress(f"resolving {name}…")
        resolve = subprocess.Popen(
            ["dns-sd", "-L", name, "_rapp-estate._tcp", "local."],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        )
        time.sleep(1.5)
        try:
            resolve.terminate()
            resolve_out, _ = resolve.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            resolve.kill()
            resolve_out, _ = resolve.communicate()

        # Parse the resolve output for "can be reached at <host>.local.:<port>" + TXT records
        host = ""
        port = 0
        txt_records: dict[str, str] = {}
        for line in resolve_out.splitlines():
            line = line.strip()
            if "can be reached at" in line:
                # "kody-w-brainstem._rapp-estate._tcp.local. can be reached at mac.local.:8080 (interface 4)"
                try:
                    chunk = line.split("can be reached at", 1)[1].strip()
                    hostport = chunk.split(" ")[0].rstrip(".")
                    host, port_s = hostport.rsplit(":", 1)
                    port = int(port_s)
                except Exception:
                    pass
            # TXT records appear as " key=value" lines (one per line, indented)
            if "=" in line and not line.startswith(("16:", "17:", "18:", "19:", "20:", "21:", "22:", "23:", "00:", "01:", "02:", "03:", "04:", "05:", "06:", "07:", "08:", "09:", "10:", "11:", "12:", "13:", "14:", "15:")):
                # Could be a TXT record line. dns-sd shows them as quoted "key=value"
                stripped = line.strip().strip('"')
                if "=" in stripped and " " not in stripped.split("=", 1)[0]:
                    k, v = stripped.split("=", 1)
                    if k and v and not k.startswith(("DATE", "Browse", "Lookup", "STARTING", "Timestamp", "Add", "Rmv", "Domain")):
                        txt_records[k] = v

        if not host or not port:
            skipped.append(
                {
                    "service": name,
                    "reason": "could not resolve host:port",
                    "accepted": False,
                    "observed": {
                        "resolve_output": resolve_out,
                        "txt_records": txt_records,
                    },
                    "provenance": _provenance(
                        url=f"mdns://{name}._rapp-estate._tcp.local",
                        source="dns-sd",
                        discovered_via="bonjour",
                        status="resolve-incomplete",
                    ),
                }
            )
            continue

        beacon_path = txt_records.get("beacon_path", f"/{_BEACON_PATH}").lstrip("/")
        estate_path = txt_records.get("estate_path", "/estate.json").lstrip("/")
        beacon_url = f"http://{host}:{port}/{beacon_path}"
        estate_url_lan = f"http://{host}:{port}/{estate_path}"
        github_hint = txt_records.get("github", "") or f"@{host}"

        beacon = fetch_beacon_at_url(beacon_url)
        if not beacon:
            skipped.append(
                {
                    "service": name,
                    "host": host,
                    "port": port,
                    "reason": f"no valid beacon at {beacon_url}",
                    "accepted": False,
                    "observed": {
                        "resolve_output": resolve_out,
                        "txt_records": txt_records,
                    },
                    "provenance": _provenance(
                        url=beacon_url,
                        source="lan-http",
                        discovered_via="bonjour",
                        status="missing-or-invalid",
                    ),
                }
            )
            continue

        indexable = bool(beacon.get("discovery", {}).get("indexable", True))
        if not indexable and not include_private:
            skipped.append(
                {
                    "service": name,
                    "reason": "indexable=false (opt-out honored)",
                    "accepted": False,
                    "observed": {
                        "resolve_output": resolve_out,
                        "txt_records": txt_records,
                        "beacon": beacon,
                    },
                    "provenance": _provenance(
                        url=beacon_url,
                        source="lan-http",
                        discovered_via="bonjour",
                        parsed_payload_sha256=_parsed_payload_sha256(beacon),
                    ),
                }
            )
            continue

        op_rappid = beacon.get("operator_rappid", "")
        try:
            door_from_rappid(op_rappid)
        except InvalidRappidError as e:
            skipped.append(
                {
                    "service": name,
                    "reason": (
                        f"operator_rappid invalid: {str(e)[:120]}"
                    ),
                    "accepted": False,
                    "observed": {
                        "resolve_output": resolve_out,
                        "txt_records": txt_records,
                        "beacon": beacon,
                    },
                    "provenance": _provenance(
                        url=beacon_url,
                        source="lan-http",
                        discovered_via="bonjour",
                        parsed_payload_sha256=_parsed_payload_sha256(beacon),
                    ),
                }
            )
            continue

        effective_estate_url = beacon.get("estate_url") or estate_url_lan
        record = _unverified_record(
            published_github=github_hint,
            service_name=name,
            published_operator_rappid=op_rappid,
            beacon_url=beacon_url,
            substrate="lan-http",
            published_estate_url=effective_estate_url,
            published_minted_at=beacon.get("minted_at"),
            published_indexable=indexable,
            discovered_via="bonjour",
            published_txt_records=txt_records,
            observed={
                "resolve_output": resolve_out,
                "txt_records": txt_records,
                "beacon": beacon,
                "estate": None,
            },
            provenance={
                "service": _provenance(
                    url=f"mdns://{name}._rapp-estate._tcp.local",
                    source="dns-sd",
                    discovered_via="bonjour",
                    host=host,
                    port=port,
                ),
                "beacon": _provenance(
                    url=beacon_url,
                    source="lan-http",
                    discovered_via="bonjour",
                    parsed_payload_sha256=_parsed_payload_sha256(beacon),
                ),
                "estate": {
                    "url": effective_estate_url,
                    "status": "not-requested",
                    "observed_at": None,
                },
            },
        )

        if fetch_estates:
            est = fetch_estate_at_url(effective_estate_url)
            if est:
                record["published_created_claim_count"] = len(
                    est.get("created", []) or []
                )
                record["published_member_claim_count"] = len(
                    est.get("member", []) or []
                )
                record["observed"]["estate"] = est
                record["provenance"]["estate"] = _provenance(
                    url=effective_estate_url,
                    source="lan-http",
                    discovered_via=f"estate:{name}",
                    parsed_payload_sha256=_parsed_payload_sha256(est),
                )
            else:
                record["provenance"]["estate"] = _provenance(
                    url=effective_estate_url,
                    source="lan-http",
                    discovered_via=f"estate:{name}",
                    status="missing-or-invalid",
                )

        operators.append(record)

    return _unverified_envelope(
        "bonjour",
        operators,
        skipped,
        service_type="_rapp-estate._tcp.local",
        browsed_seconds=browse_seconds,
        services_found=len(instance_names),
        observed_browse_output=browse_out,
        browse_provenance=_provenance(
            url="mdns://_rapp-estate._tcp.local",
            source="dns-sd",
            discovered_via="bonjour",
            browse_seconds=browse_seconds,
        ),
    )


def sniff_via_topic(limit: int = 100, include_private: bool = False,
                     fetch_estates: bool = True, on_progress=None) -> dict:
    """Use `gh search repos topic:rapp-estate`. Eventually-consistent (lags
    indexing by minutes-to-hours); use as a periodic sweep, not a primary."""
    rc, out, err = _gh([
        "search", "repos", f"topic:{_TOPIC}",
        "--json", "owner,name,topics,stargazerCount,updatedAt",
        "--limit", str(limit),
    ])
    if rc != 0:
        return _unavailable(
            "topic",
            f"GitHub topic observation failed: {err.strip()[:200]}",
        )
    try:
        repos = json.loads(out) or []
    except Exception:
        repos = []

    operators: list[dict] = []
    skipped: list[dict] = []
    for r in repos:
        if not isinstance(r, dict):
            skipped.append(
                {
                    "reason": "topic result is not an object",
                    "accepted": False,
                    "observed": {"search_result": r},
                }
            )
            continue
        owner = (r.get("owner") or {}).get("login", "")
        name = r.get("name", "")
        if name != "rapp-estate":
            skipped.append(
                {
                    "repo": f"{owner}/{name}",
                    "reason": "topic match but not <handle>/rapp-estate",
                    "accepted": False,
                    "observed": {"search_result": r},
                    "provenance": _provenance(
                        url=f"https://github.com/{owner}/{name}",
                        source="gh-search",
                        discovered_via="topic",
                    ),
                }
            )
            continue
        if on_progress:
            on_progress(f"validating: {owner}/rapp-estate")
        beacon = fetch_beacon_for_handle(owner)
        if not beacon:
            skipped.append(
                {
                    "repo": f"{owner}/{name}",
                    "reason": "no valid beacon",
                    "accepted": False,
                    "observed": {"search_result": r},
                    "provenance": _provenance(
                        url=github_beacon_url(owner),
                        source="github-raw",
                        discovered_via="topic",
                        status="missing-or-invalid",
                    ),
                }
            )
            continue
        indexable = bool(beacon.get("discovery", {}).get("indexable", True))
        if not indexable and not include_private:
            skipped.append(
                {
                    "repo": f"{owner}/{name}",
                    "reason": "indexable=false",
                    "accepted": False,
                    "observed": {
                        "search_result": r,
                        "beacon": beacon,
                    },
                    "provenance": _provenance(
                        url=github_beacon_url(owner),
                        source="github-raw",
                        discovered_via="topic",
                        parsed_payload_sha256=_parsed_payload_sha256(beacon),
                    ),
                }
            )
            continue
        op_rappid = beacon.get("operator_rappid", "")
        try:
            door_from_rappid(op_rappid)
        except InvalidRappidError as e:
            skipped.append(
                {
                    "repo": f"{owner}/{name}",
                    "reason": f"bad rappid: {e}",
                    "accepted": False,
                    "observed": {
                        "search_result": r,
                        "beacon": beacon,
                    },
                    "provenance": _provenance(
                        url=github_beacon_url(owner),
                        source="github-raw",
                        discovered_via="topic",
                        parsed_payload_sha256=_parsed_payload_sha256(beacon),
                    ),
                }
            )
            continue
        effective_estate_url = (
            beacon.get("estate_url") or github_estate_url(owner)
        )
        record = _unverified_record(
            published_github=owner,
            published_operator_rappid=op_rappid,
            published_estate_url=effective_estate_url,
            published_grail_url=beacon.get("grail_url", ""),
            published_minted_at=beacon.get("minted_at"),
            published_indexable=indexable,
            discovered_via="topic",
            observed={
                "search_result": r,
                "beacon": beacon,
                "estate": None,
            },
            provenance={
                "search": _provenance(
                    url=f"https://github.com/{owner}/{name}",
                    source="gh-search",
                    discovered_via="topic",
                    parsed_payload_sha256=_parsed_payload_sha256(r),
                ),
                "beacon": _provenance(
                    url=github_beacon_url(owner),
                    source="github-raw",
                    discovered_via="topic",
                    parsed_payload_sha256=_parsed_payload_sha256(beacon),
                ),
                "estate": {
                    "url": effective_estate_url,
                    "status": "not-requested",
                    "observed_at": None,
                },
            },
        )
        if fetch_estates:
            est = fetch_estate_at_url(effective_estate_url)
            if est:
                record["published_created_claim_count"] = len(
                    est.get("created", []) or []
                )
                record["published_member_claim_count"] = len(
                    est.get("member", []) or []
                )
                record["observed"]["estate"] = est
                record["provenance"]["estate"] = _provenance(
                    url=effective_estate_url,
                    source=_substrate_label(effective_estate_url),
                    discovered_via=f"estate:{owner}",
                    parsed_payload_sha256=_parsed_payload_sha256(est),
                )
            else:
                record["provenance"]["estate"] = _provenance(
                    url=effective_estate_url,
                    source=_substrate_label(effective_estate_url),
                    discovered_via=f"estate:{owner}",
                    status="missing-or-invalid",
                )
        operators.append(record)

    return _unverified_envelope(
        "topic",
        operators,
        skipped,
        topic=_TOPIC,
        repos_found=len(repos),
        observed_search_results=repos,
        search_provenance=_provenance(
            url=f"gh-search://repos?topic={_TOPIC}&limit={limit}",
            source="gh-search",
            discovered_via="topic",
            parsed_payload_sha256=_parsed_payload_sha256(repos),
        ),
    )


# ─── CLI ──────────────────────────────────────────────────────────────────

def _print_summary(out: dict) -> None:
    print(f"=== {_SNIFF_SCHEMA} (via {out.get('via','?')}) ===")
    if not out.get("observation_complete"):
        error = out.get("error") or {}
        print(f"  ERROR: {error.get('detail', 'unknown')}")
        return
    print("  acceptance:        REFUSED (unverified publication observations)")
    if out["via"] == "raw":
        print(f"  seed:              {out['seed_url']}")
        print(f"  max hops:          {out['max_hops']}")
    elif out["via"] == "bonjour":
        print(f"  service type:      {out.get('service_type', '_rapp-estate._tcp.local')}")
        print(f"  browse window:     {out.get('browsed_seconds', '?')}s")
        print(f"  services found:    {out.get('services_found', '?')}")
    else:
        print(f"  topic:             {out.get('topic', '?')}")
        print(f"  repos found:       {out.get('repos_found', '?')}")
    print(f"  observations:      {out['observations_count']}")
    print(f"  published claims:  {out['published_door_claim_count']} doors")
    print(f"  skipped:           {out['observations_skipped']}")
    print()
    for op in out["observations"]:
        marker = "★" if op.get("hop") == 0 else "·"
        cc = op.get("published_created_claim_count", "?")
        mc = op.get("published_member_claim_count", "?")
        hop_info = f"hop={op.get('hop')}" if "hop" in op else "topic"
        substrate = op.get("substrate", "?")
        label = op.get("published_github", "(anonymous)")
        print(
            f"  {marker} {label:24s}  published claims: {cc!s:>3} created · "
            f"{mc!s:>3} member  ({hop_info}, via "
            f"{op.get('discovered_via','?')}, substrate: {substrate}) "
            "[UNVERIFIED; accepted=false]"
        )
        print(f"    published estate: {op.get('published_estate_url','')}")
        if op.get("published_grail_url"):
            print(f"    published grail:  {op['published_grail_url']}")
        if op.get("published_private_extension_pointer_present"):
            commit = (
                op.get("published_private_estate_commitment") or ""
            )[:16]
            count = op.get("published_private_door_claim_count", 0)
            print(
                "    published private pointer: "
                f"{op['published_private_estate_pointer']}  "
                f"(claimed commit: {commit}…, claimed doors: {count})"
            )
    if out["skipped"]:
        print()
        print(f"  Skipped ({out['observations_skipped']}):")
        for s in out["skipped"][:10]:
            label = s.get("handle") or s.get("repo") or "?"
            print(f"    - {label}: {s['reason']}")


def _write_target(path: str, via: str) -> dict[str, str]:
    return {
        "path": os.path.abspath(os.path.expanduser(path)),
        "via": via,
        "operation": "network-sniff-write",
    }


def _inspect_owner_approval(
    approval_path: str,
    *,
    operation: str,
    target: dict[str, str],
) -> dict:
    if not approval_path:
        return {
            "supplied": False,
            "structurally_matching": False,
            "authenticated": False,
            "fresh": False,
            "status": "MISSING",
            "detail": "an explicit owner-approval artifact is required",
        }
    path = Path(os.path.expanduser(approval_path))
    try:
        raw = path.read_bytes()
        value = strict_loads(raw)
    except (OSError, TypeError, ValueError) as exc:
        return {
            "supplied": True,
            "path": str(path),
            "structurally_matching": False,
            "authenticated": False,
            "fresh": False,
            "status": "INVALID",
            "detail": f"owner-approval artifact could not be inspected: {exc}",
        }
    structurally_matching = (
        type(value) is dict
        and value.get("schema") == _APPROVAL_SCHEMA
        and value.get("operation") == operation
        and value.get("target") == target
    )
    return {
        "supplied": True,
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "byte_length": len(raw),
        "schema": value.get("schema") if type(value) is dict else None,
        "operation": value.get("operation") if type(value) is dict else None,
        "target": value.get("target") if type(value) is dict else None,
        "structurally_matching": structurally_matching,
        "authenticated": False,
        "fresh": False,
        "status": "STRUCTURAL_ONLY" if structurally_matching else "MISMATCH",
        "detail": (
            _ACCEPTANCE_REASON
            if structurally_matching
            else "artifact schema, operation, or target does not exactly match"
        ),
    }


def _write_gate(path: str, via: str, approval_path: str) -> dict:
    target = _write_target(path, via)
    approval = _inspect_owner_approval(
        approval_path,
        operation="network-sniff-write",
        target=target,
    )
    if not approval["supplied"]:
        code = "owner-approval-artifact-required"
    elif not approval["structurally_matching"]:
        code = "owner-approval-artifact-invalid"
    else:
        code = "authenticated-registry-unavailable"
    return {
        "permitted": False,
        "code": code,
        "detail": approval["detail"],
        "target": target,
        "approval": approval,
        "prerequisites": {
            "explicit_write_flag": True,
            "owner_approval_artifact_supplied": approval["supplied"],
            "owner_approval_artifact_matches": approval[
                "structurally_matching"
            ],
            "section_13_registry_authenticated": False,
            "registry_freshness_verified": False,
            "out_of_band_estate_owner_anchor_verified": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--via", choices=["raw", "topic", "bonjour"], default="raw",
                    help="discovery method (raw=pure URL fetches; topic=gh search; bonjour=LAN mDNS)")
    ap.add_argument("--bonjour-seconds", type=int, default=3,
                    help="for --via bonjour: how long to browse for services (default 3s)")
    ap.add_argument("--seed-url", default=_DEFAULT_SEED_URL,
                    help="raw URL to start the BFS (default: kody-w/RAPP seed)")
    ap.add_argument("--max-hops", type=int, default=10,
                    help="BFS depth cap (default 10)")
    ap.add_argument("--limit", type=int, default=100,
                    help="for --via topic: max repos to search (default 100)")
    ap.add_argument("--include-private", action="store_true",
                    help="ignore discovery.indexable=false (audit only)")
    ap.add_argument("--no-estates", action="store_true",
                    help="skip fetching each estate.json (faster)")
    ap.add_argument("--apply", action="store_true",
                    help="request a gated write to ~/.brainstem/network-sniff.json")
    ap.add_argument("--out", default="", help="request a gated write to this path")
    ap.add_argument(
        "--owner-approval",
        default="",
        help="target-owned approval artifact required by --apply or --out",
    )
    ap.add_argument("--json", action="store_true",
                    help="emit full JSON envelope (default: human summary)")
    args = ap.parse_args(argv)

    def _progress(msg: str) -> None:
        print(f"  · {msg}", file=sys.stderr)

    if args.via == "raw":
        out = sniff_via_raw(seed_url=args.seed_url, max_hops=args.max_hops,
                             include_private=args.include_private,
                             fetch_estates=not args.no_estates,
                             on_progress=_progress)
    elif args.via == "bonjour":
        out = sniff_via_bonjour(browse_seconds=args.bonjour_seconds,
                                 include_private=args.include_private,
                                 fetch_estates=not args.no_estates,
                                 on_progress=_progress)
    else:
        out = sniff_via_topic(limit=args.limit,
                               include_private=args.include_private,
                               fetch_estates=not args.no_estates,
                               on_progress=_progress)

    write_requested = bool(args.apply or args.out)
    if write_requested:
        path = (
            os.path.expanduser("~/.brainstem/network-sniff.json")
            if args.apply
            else os.path.expanduser(args.out)
        )
        gate = _write_gate(path, args.via, args.owner_approval)
        out["write_gate"] = gate
        out["write_requested"] = True
        out["write_permitted"] = gate["permitted"]
        if gate["permitted"]:
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            Path(path).write_text(json.dumps(out, indent=2) + "\n")
            out["wrote_to"] = path

    if args.json:
        print(json.dumps(out, indent=2))
    else:
        _print_summary(out)
    if write_requested and not out.get("write_permitted"):
        return 2
    return 0 if out.get("observation_complete") else 1


if __name__ == "__main__":
    sys.exit(main())
