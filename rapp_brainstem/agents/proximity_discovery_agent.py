"""proximity_discovery_agent — Pizza Place / Pokémon-Go layer.

Per HERO_USECASE.md §4 — location-tied seeds (`kind: "place"`) discover
each other by sharing geohash prefixes. Pure-stdlib geohash encode/decode;
matches against the metropolis tracker `pages/metropolis/index.json`.

Closes ECOSYSTEM §15 row "Location-aware proximity swarm (Pizza Place /
Pokémon-Go layer)". Single-file agent per ANTIPATTERNS §1.

Geohash precision (chars → ~box size):
  4 chars  ≈ 39 km × 19 km    (regional)
  5 chars  ≈ 4.9 km × 4.9 km  (city neighborhood — default)
  6 chars  ≈ 1.2 km × 0.6 km  (block)
  7 chars  ≈ 153 m × 153 m    (building)

Usage from /chat (LLM tool-call):
    Proximity.discover(lat=47.6062, lng=-122.3321, precision=5)
    Proximity.encode(lat=47.6062, lng=-122.3321, precision=7)
    Proximity.match(geohash="c23nb", radius_chars=1)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

try:
    from agents.basic_agent import BasicAgent
except ImportError:
    from basic_agent import BasicAgent


_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"
_USER_AGENT = "rapp-proximity/1.0"
_HTTP_TIMEOUT = 8.0
_DEFAULT_PRECISION = 5
_DEFAULT_TRACKER_URL = "https://kody-w.github.io/RAPP/metropolis/index.json"


# ── Geohash codec (pure stdlib, ~30 lines) ──────────────────────────────

def geohash_encode(lat: float, lng: float, precision: int = _DEFAULT_PRECISION) -> str:
    """Encode (lat, lng) → geohash. Reference impl: same algorithm everyone uses."""
    if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
        raise ValueError(f"lat/lng out of range: ({lat}, {lng})")
    lat_lo, lat_hi = -90.0, 90.0
    lng_lo, lng_hi = -180.0, 180.0
    bits, bit, ch = [], 0, 0
    even = True
    while len(bits) < precision:
        if even:
            mid = (lng_lo + lng_hi) / 2
            if lng >= mid: ch |= 1 << (4 - bit); lng_lo = mid
            else:                                    lng_hi = mid
        else:
            mid = (lat_lo + lat_hi) / 2
            if lat >= mid: ch |= 1 << (4 - bit); lat_lo = mid
            else:                                    lat_hi = mid
        even = not even
        bit += 1
        if bit == 5:
            bits.append(_BASE32[ch])
            bit, ch = 0, 0
    return "".join(bits)


def geohash_decode(geohash: str) -> tuple[float, float]:
    """Decode geohash → (lat, lng) at the cell center."""
    lat_lo, lat_hi = -90.0, 90.0
    lng_lo, lng_hi = -180.0, 180.0
    even = True
    for ch in geohash.lower():
        if ch not in _BASE32:
            raise ValueError(f"invalid geohash char: {ch!r}")
        bits = _BASE32.index(ch)
        for i in range(5):
            mask = 1 << (4 - i)
            if even:
                mid = (lng_lo + lng_hi) / 2
                if bits & mask: lng_lo = mid
                else:           lng_hi = mid
            else:
                mid = (lat_lo + lat_hi) / 2
                if bits & mask: lat_lo = mid
                else:           lat_hi = mid
            even = not even
    return ((lat_lo + lat_hi) / 2, (lng_lo + lng_hi) / 2)


# ── Tracker fetch ────────────────────────────────────────────────────────

def _fetch_tracker(url: str) -> dict | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError):
        return None


def _local_tracker_path() -> str:
    return os.path.expanduser("~/.brainstem/metropolis_index.json")


def _read_local_tracker() -> dict | None:
    """Offline fallback — reads cached metropolis index."""
    p = _local_tracker_path()
    if not os.path.exists(p):
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _entries_with_geohash(tracker: dict) -> list[dict]:
    """Filter tracker entries that declare a location_geohash."""
    if not isinstance(tracker, dict):
        return []
    entries = tracker.get("entries", [])
    if not isinstance(entries, list):
        return []
    return [e for e in entries if isinstance(e, dict) and e.get("location_geohash")]


# ── Matching ─────────────────────────────────────────────────────────────

def _match_by_prefix(entries: list[dict], prefix: str) -> list[dict]:
    """Entries whose geohash starts with `prefix` (or vice versa)."""
    out = []
    for e in entries:
        gh = (e.get("location_geohash") or "").lower()
        p = prefix.lower()
        if gh.startswith(p) or p.startswith(gh):
            out.append(e)
    return out


class ProximityDiscoveryAgent(BasicAgent):
    metadata = {
        "name": "Proximity",
        "description": (
            "Location-aware proximity discovery for kind=place organisms. "
            "Encodes lat/lng to geohash; matches the metropolis tracker against "
            "a geohash prefix to find nearby planted places. Pure stdlib; "
            "works offline against ~/.brainstem/metropolis_index.json cache."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["discover", "encode", "decode", "match"],
                           "default": "discover"},
                "lat": {"type": "number", "description": "Latitude (-90..90)."},
                "lng": {"type": "number", "description": "Longitude (-180..180)."},
                "precision": {"type": "integer", "default": _DEFAULT_PRECISION,
                              "description": "Geohash precision (1..12)."},
                "geohash": {"type": "string", "description": "Geohash to match (action=match) or decode."},
                "radius_chars": {"type": "integer", "default": 0,
                                 "description": "Truncate geohash by N chars to widen search radius."},
                "tracker_url": {"type": "string", "default": _DEFAULT_TRACKER_URL},
            },
            "required": [],
        },
    }

    def __init__(self):
        self.name = "Proximity"

    def perform(self, **kwargs) -> str:
        action = (kwargs.get("action") or "discover").lower()

        if action == "encode":
            lat = float(kwargs.get("lat", 0)); lng = float(kwargs.get("lng", 0))
            precision = int(kwargs.get("precision") or _DEFAULT_PRECISION)
            try:
                gh = geohash_encode(lat, lng, precision)
                return json.dumps({"ok": True, "geohash": gh,
                                   "lat": lat, "lng": lng, "precision": precision})
            except ValueError as e:
                return json.dumps({"ok": False, "error": str(e)})

        if action == "decode":
            gh = (kwargs.get("geohash") or "").strip()
            if not gh:
                return json.dumps({"ok": False, "error": "geohash required"})
            try:
                lat, lng = geohash_decode(gh)
                return json.dumps({"ok": True, "geohash": gh, "lat": lat, "lng": lng})
            except ValueError as e:
                return json.dumps({"ok": False, "error": str(e)})

        # action = discover or match — both need the tracker
        tracker_url = kwargs.get("tracker_url") or _DEFAULT_TRACKER_URL
        tracker = _fetch_tracker(tracker_url) or _read_local_tracker()
        if not tracker:
            return json.dumps({"ok": False, "error": "tracker unreachable + no local cache"})

        if action == "match":
            gh = (kwargs.get("geohash") or "").strip().lower()
            if not gh:
                return json.dumps({"ok": False, "error": "geohash required for match"})
            radius = int(kwargs.get("radius_chars") or 0)
            search_prefix = gh[:max(1, len(gh) - radius)]
            entries = _entries_with_geohash(tracker)
            matches = _match_by_prefix(entries, search_prefix)
            return json.dumps({
                "schema": "rapp-proximity-match/1.0",
                "ok": True, "geohash": gh, "search_prefix": search_prefix,
                "tracker_url": tracker_url,
                "matched": matches, "matched_count": len(matches),
                "tracker_entry_count": len(entries),
            }, indent=2)

        # action = discover — encode lat/lng, then match
        if "lat" not in kwargs or "lng" not in kwargs:
            return json.dumps({"ok": False, "error": "discover requires lat + lng"})
        lat = float(kwargs.get("lat")); lng = float(kwargs.get("lng"))
        precision = int(kwargs.get("precision") or _DEFAULT_PRECISION)
        radius = int(kwargs.get("radius_chars") or 0)
        try:
            gh = geohash_encode(lat, lng, precision)
        except ValueError as e:
            return json.dumps({"ok": False, "error": str(e)})
        search_prefix = gh[:max(1, len(gh) - radius)]
        entries = _entries_with_geohash(tracker)
        matches = _match_by_prefix(entries, search_prefix)
        return json.dumps({
            "schema": "rapp-proximity-match/1.0",
            "ok": True,
            "lat": lat, "lng": lng, "precision": precision,
            "geohash": gh, "search_prefix": search_prefix,
            "tracker_url": tracker_url,
            "matched": matches, "matched_count": len(matches),
            "tracker_entry_count": len(entries),
        }, indent=2)
