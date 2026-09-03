"""Historical holocard derivation helpers with a fail-closed generator.

The former generator claimed to emit a conformant RAPPcards document while
using an interim mnemonic registry that the claimed registry rejects. It is
therefore tombstoned. ``generate_holo_card`` now returns only an explicit
historical/nonconformant refusal envelope and never emits a ``card.json``
schema claim.

The deterministic seed and SVG helpers remain available solely for inspecting
historical material. They are not registry acceptance, RAPP/1 authority, or a
current publication path.

Public API:
    derive_seed(rappid_str) -> int                  # 64-bit unsigned, BLAKE2b-64
    seed_to_words(seed) -> str                      # historical preview only
    generate_holo_card(...) -> dict                 # nonconformant refusal
    generate_avatar_svg(seed, kind) -> str          # historical visual helper
    generate_summon_qr_svg(seed, gate_url) -> str   # historical placeholder
    available_kinds() -> list[str]
"""

from __future__ import annotations

import hashlib
import json

HISTORICAL_OUTPUT_SCHEMA = "rapp-holocard-historical-observation/1.0"
TOMBSTONE_STATUS = "RETIRED_NONCONFORMANT"


# ─── Historical seed derivation ───────────────────────────────────────────

def derive_seed(rappid_str: str) -> int:
    """BLAKE2b-64 of the rappid string → unsigned 64-bit integer.

    The retired implementation derived its seed as:
        int.from_bytes(blake2b(source_bytes, digest_size=8).digest(), 'big')
    For historical neighborhood material, the source was the rappid string.
    """
    h = hashlib.blake2b(rappid_str.encode("utf-8"), digest_size=8)
    return int.from_bytes(h.digest(), "big")


# ─── Historical mnemonic preview (not registry-compatible) ────────────────
# The retired implementation embedded only 20 words instead of the registry
# vocabulary. Its previews are intentionally labelled nonconformant.

_INTERIM_WORDS = (
    "FORGE ANVIL BLADE RUNE SHARD SMELT TEMPER QUENCH HAMMER BELLOW "
    "TONGS COAL EMBER ASHES IRON STEEL COPPER BRONZE SILVER GOLD"
).split()


def seed_to_words(seed: int) -> str:
    """Return the retired interim-wordlist preview; never a registry token."""
    s = seed & ((1 << 64) - 1)
    idxs = []
    for _ in range(7):
        idxs.append(s & (len(_INTERIM_WORDS) - 1))
        s >>= max(1, (len(_INTERIM_WORDS) - 1).bit_length())
    return " ".join(_INTERIM_WORDS[i] for i in reversed(idxs))


# ─── Mulberry32 PRNG (matches RAR/scripts/generate_holo_cards.py) ─────────

def _mulberry32(seed: int):
    state = [seed & 0xFFFFFFFF]

    def _next() -> float:
        state[0] = (state[0] + 0x6D2B79F5) & 0xFFFFFFFF
        t = state[0] ^ (state[0] >> 15)
        t = (t * (1 | state[0])) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t) & 0xFFFFFFFF)) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    return _next


# ─── Historical per-kind attributes ──────────────────────────────────────

# Retired type-system data retained only to inspect historical visuals.
#   LOGIC → WEALTH → HEAL → CRAFT → SHIELD → SOCIAL → DATA → LOGIC

_KIND_PROFILE = {
    "ant-farm": {
        "agent_types": ["SOCIAL", "DATA"],
        "weakness":    "WEALTH",   # SOCIAL is weak to WEALTH (per cycle: WEALTH→HEAL→CRAFT→SHIELD→SOCIAL — SHIELD attacks SOCIAL; SOCIAL beats DATA)
        "resistance":  "DATA",
        "rarity_tier": "core",
        "type_line":   "Distributed Swarm — Self-Coordinating",
        "flavor_text": "Many ants, one trail. The colony writes the story.",
        "abilities_template": [
            {"name": "Drop Pheromone",  "cost": 1, "damage": 30,
             "text": "Post a content-addressed pheromone Issue. Chain to prev_hash. The colony detects tampering automatically.",
             "type": "SOCIAL"},
            {"name": "Synthesize",      "cost": 2, "damage": 0,
             "text": "Aggregate the colony's pheromone chain into a rapp-colony-observation/1.0. No new pheromones created.",
             "type": "DATA"},
        ],
    },
    "neighborhood": {
        "agent_types": ["CRAFT", "SOCIAL"],
        "weakness":    "DATA",
        "resistance":  "SHIELD",
        "rarity_tier": "core",
        "type_line":   "Public Neighborhood — Submission-Driven",
        "flavor_text": "The canvas IS the union of contributions.",
        "abilities_template": [
            {"name": "Submit",  "cost": 1, "damage": 40,
             "text": "Open a PR adding submissions/<slug>/{meta.json, piece.<ext>}. License travels with the piece.",
             "type": "CRAFT"},
            {"name": "Vote",    "cost": 0, "damage": 0,
             "text": "React on the announcement Issue. 🩵 = belongs in the canvas; 👎 = doesn't fit.",
             "type": "SOCIAL"},
            {"name": "Remix",   "cost": 2, "damage": 50,
             "text": "Open a new submission with remix_of: <other-slug>. The lineage is permanent.",
             "type": "CRAFT"},
        ],
    },
    "braintrust": {
        "agent_types": ["LOGIC", "DATA"],
        "weakness":    "SHIELD",
        "resistance":  "WEALTH",
        "rarity_tier": "rare",
        "type_line":   "Federated Research — Citation-Bound",
        "flavor_text": "Multiple libraries, one synthesized truth.",
        "abilities_template": [
            {"name": "Request",     "cost": 1, "damage": 0,
             "text": "Open a research request Issue (label: braintrust-request). Defines topic, scope, deadline, quorum.",
             "type": "LOGIC"},
            {"name": "Contribute",  "cost": 2, "damage": 60,
             "text": "Comment on the request Issue with rapp-braintrust-contribution/1.0. Every claim cited or labeled as opinion.",
             "type": "DATA"},
            {"name": "Synthesize",  "cost": 3, "damage": 80,
             "text": "Aggregate contributions into reports/<request_id>.md (rapp-braintrust-report/1.0) via PR. Consensus = review.",
             "type": "LOGIC"},
        ],
    },
    "workspace": {
        "agent_types": ["CRAFT", "LOGIC"],
        "weakness":    "SOCIAL",
        "resistance":  "WEALTH",
        "rarity_tier": "core",
        "type_line":   "Private Workspace — Membership-Gated",
        "flavor_text": "Async work, named members, no spectators.",
        "abilities_template": [
            {"name": "Drop Work-Item", "cost": 1, "damage": 30,
             "text": "Open a workspace-todo Issue with the work payload. Assignable to members.",
             "type": "CRAFT"},
            {"name": "Pick Up",        "cost": 0, "damage": 0,
             "text": "Claim a workspace-todo. Relabel to workspace-in-progress; the assignment is durable.",
             "type": "LOGIC"},
            {"name": "Mark Done",      "cost": 1, "damage": 0,
             "text": "Relabel workspace-done after the artifact lands. Members consume the result.",
             "type": "CRAFT"},
        ],
    },
    # ── twin: an AI / brainstem planting (heimdall, kody-twin, etc.) ────────
    # Twins ARE the AIs. When a neighborhood encounters a twin (or vice versa),
    # both sides ship their own self-describing front door so they can
    # negotiate participation without prior knowledge of each other.
    "twin": {
        "agent_types": ["LOGIC", "DATA"],
        "weakness":    "WEALTH",
        "resistance":  "HEAL",
        "rarity_tier": "rare",
        "type_line":   "Brainstem — AI / Twin",
        "flavor_text": "An AI with a permanent address and persistent memory. Visits neighborhoods.",
        "abilities_template": [
            {"name": "Chat",        "cost": 1, "damage": 30,
             "text": "Operator interacts via /chat. Tool calls dispatch agents; soul.md anchors voice.",
             "type": "LOGIC"},
            {"name": "Recall",      "cost": 0, "damage": 0,
             "text": "Persistent memory across sessions via the kernel's memory agents + bonds.json.",
             "type": "DATA"},
            {"name": "Twin-Chat",   "cost": 2, "damage": 0,
             "text": "Reach another twin over rapp-twin-chat/1.0 envelope (NEIGHBORHOOD_PROTOCOL §6).",
             "type": "DATA"},
            {"name": "Join",        "cost": 1, "damage": 0,
             "text": "Visit a neighborhood, read its holo.md + specs/, contribute within contract.",
             "type": "LOGIC"},
        ],
    },
}

# Historical aliases used by the retired visual profiles.
_KIND_ALIASES = {
    "personal":          "twin",     # heimdall, kody-twin (legacy "personal" → twin)
    "place":             "twin",     # pkstop-* (planted places ARE twins of a location)
    "swarm":             "ant-farm", # legacy swarm → ant-farm
    "pre-founder-twin":  "twin",     # wildhaven-ai-homes-twin
    "mirror":            "twin",     # rapp-test-neighbor (mirror is a twin variant)
}


def normalize_kind(kind: str) -> str:
    """Map a historical alias to its retained visual profile."""
    return _KIND_ALIASES.get(kind, kind)


def available_kinds() -> list[str]:
    return sorted(_KIND_PROFILE.keys())


# ─── Stat derivation (deterministic from seed) ────────────────────────────

def _derive_stats(seed: int) -> dict:
    """Derive historical visual stats deterministically from a seed."""
    rng = _mulberry32(seed ^ 0xCAFEBABE)
    return {
        "hp":  int(60 + rng() * 240),       # 60–300
        "atk": int(40 + rng() * 215),       # 40–255
        "def": int(40 + rng() * 215),
        "spd": int(40 + rng() * 215),
        "int": int(40 + rng() * 215),
    }


# ─── Procedural avatar SVG (~3 KB, deterministic from seed) ──────────────

# Curated palettes — chosen for high contrast on dark organism-night
_AVATAR_PALETTES = [
    ("#ff6b6b", "#c94646", "#ffd166"),
    ("#118ab2", "#0a5d7a", "#06d6a0"),
    ("#7209b7", "#480475", "#3a86ff"),
    ("#fb5607", "#b03c00", "#ffbe0b"),
    ("#06d6a0", "#048967", "#118ab2"),
    ("#3a86ff", "#1f5cc4", "#06d6a0"),
    ("#9b5de5", "#6c2eb5", "#f15bb5"),
    ("#00bbf9", "#0085bb", "#fee440"),
]


def generate_avatar_svg(seed: int, kind: str = "neighborhood") -> str:
    """Procedural heraldic-badge avatar SVG, ≤4 KB, deterministic from seed."""
    rng = _mulberry32(seed ^ 0xA5A5A5A5)
    pal = _AVATAR_PALETTES[seed % len(_AVATAR_PALETTES)]
    body, shadow, accent = pal

    # Background hue derived from seed
    bg_hue = int((seed >> 16) % 360)
    bg_inner = f"hsl({bg_hue},45%,12%)"
    bg_outer = f"hsl({bg_hue},55%,4%)"

    # Center shape: 5–8 sided polygon, rotated by seed
    sides = 5 + (seed >> 24) % 4
    rot = (seed >> 8) % 360
    polygon_pts = []
    import math
    for i in range(sides):
        angle = math.radians(rot + i * 360.0 / sides - 90)
        polygon_pts.append(f"{100 + 55 * math.cos(angle):.1f},{100 + 55 * math.sin(angle):.1f}")

    # Concentric rings (3–5)
    ring_count = 3 + int(rng() * 3)
    rings = ""
    for i in range(ring_count):
        r = 30 + i * 18
        rings += f'<circle cx="100" cy="100" r="{r}" fill="none" stroke="{accent}" stroke-width="0.6" opacity="{0.55 - i*0.1:.2f}"/>'

    # Orbital dots (representing the 4D evolution — different positions per "moment")
    dots = ""
    for i in range(7):
        ang = math.radians((rot * 2 + i * 51) % 360)
        rad = 60 + (i * 7 % 30)
        cx = 100 + rad * math.cos(ang)
        cy = 100 + rad * math.sin(ang)
        dots += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2" fill="{accent}" opacity="0.7"/>'

    # Center glyph: small shape based on kind
    kind = normalize_kind(kind)
    kind_glyph = {
        "ant-farm":     '<circle cx="100" cy="100" r="10" fill="' + accent + '"/>',
        "neighborhood": '<rect x="90" y="90" width="20" height="20" fill="' + accent + '" transform="rotate(45 100 100)"/>',
        "braintrust":   '<polygon points="100,88 112,108 88,108" fill="' + accent + '"/>',
        "workspace":    '<rect x="88" y="92" width="24" height="16" fill="' + accent + '"/>',
        "twin":         '<circle cx="100" cy="100" r="6" fill="' + accent + '"/><circle cx="100" cy="100" r="14" fill="none" stroke="' + accent + '" stroke-width="1.2" opacity="0.8"/>',
    }.get(kind, '<circle cx="100" cy="100" r="8" fill="' + accent + '"/>')

    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" role="img">\n'
        f'  <defs>\n'
        f'    <radialGradient id="bg" cx="50%" cy="50%" r="55%">\n'
        f'      <stop offset="0%" stop-color="{bg_inner}"/>\n'
        f'      <stop offset="100%" stop-color="{bg_outer}"/>\n'
        f'    </radialGradient>\n'
        f'    <filter id="glow"><feGaussianBlur stdDeviation="2"/></filter>\n'
        f'  </defs>\n'
        f'  <rect width="200" height="200" fill="url(#bg)"/>\n'
        f'  <g filter="url(#glow)" opacity="0.55">{rings}</g>\n'
        f'  <polygon points="{" ".join(polygon_pts)}" fill="none" stroke="{body}" stroke-width="2.2" opacity="0.85"/>\n'
        f'  <polygon points="{" ".join(polygon_pts)}" fill="{shadow}" opacity="0.18"/>\n'
        f'  {kind_glyph}\n'
        f'  <g>{dots}</g>\n'
        f'</svg>\n'
    )


# ─── Summon QR placeholder (V2 will replace with real scannable QR) ──────

def generate_summon_qr_svg(seed: int, gate_url: str) -> str:
    """Decorative QR-style SVG. V1: NOT a real scannable QR. V2 will lift
    a pure-Python QR encoder. The summon URL is embedded as a clickable
    link beneath the visual + as text inside the SVG so consumers can
    extract it without QR scanning."""
    rng = _mulberry32(seed)
    # Build a 21x21 random-looking matrix (deterministic from seed).
    # Reserve corners for "finder patterns" (cosmetic — not real QR finders).
    matrix = []
    for r in range(21):
        row = []
        for c in range(21):
            in_finder = ((r < 7 and c < 7) or (r < 7 and c >= 14) or (r >= 14 and c < 7))
            if in_finder:
                # Cosmetic finder: outer 7x7 ring + 3x3 center
                if r in (0, 6) or c in (0, 6) or (r >= 14 and c >= 14):
                    row.append(1)
                elif 2 <= r <= 4 and 2 <= c <= 4:
                    row.append(1)
                elif r >= 14 and 14 <= c <= 18:
                    row.append(1 if rng() > 0.5 else 0)
                else:
                    row.append(0)
            else:
                row.append(1 if rng() > 0.5 else 0)
        matrix.append(row)

    # Render
    cells = []
    cell = 8
    for r, row in enumerate(matrix):
        for c, v in enumerate(row):
            if v:
                cells.append(f'<rect x="{c*cell}" y="{r*cell}" width="{cell}" height="{cell}" fill="#0a0a0a"/>')

    summon_url = f"{gate_url.rstrip('/')}/#summon&seed={seed}"

    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 240" role="img" aria-label="Summon QR for seed {seed}">\n'
        f'  <title>Summon QR — {summon_url}</title>\n'
        f'  <desc>V1 placeholder QR-style visual. The actual summon URL is in the title attribute and the text below. Real scannable QR coming in V2.</desc>\n'
        f'  <rect width="220" height="240" fill="#fff"/>\n'
        f'  <g transform="translate(26 14)">{"".join(cells)}</g>\n'
        f'  <text x="110" y="200" text-anchor="middle" font-family="monospace" font-size="9" fill="#0a0a0a">seed={seed}</text>\n'
        f'  <text x="110" y="218" text-anchor="middle" font-family="monospace" font-size="8" fill="#555">#summon&amp;seed=...</text>\n'
        f'  <text x="110" y="232" text-anchor="middle" font-family="Georgia,serif" font-size="9" fill="#222" font-style="italic">V1 placeholder — see title for full URL</text>\n'
        f'</svg>\n'
    )


# ─── Tombstoned generator ─────────────────────────────────────────────────

def generate_holo_card(rappid: str, kind: str, owner: str, name: str,
                       display_name: str, *,
                       version: str = "1.0.0",
                       category: str = None,
                       license: str = "PolyForm-Small-Business",
                       embed_avatar_svg: bool = True,
                       gate_url: str = None) -> dict:
    """Return an explicit historical/nonconformant refusal envelope."""
    kind = normalize_kind(kind)
    seed = derive_seed(rappid)
    return {
        "schema": HISTORICAL_OUTPUT_SCHEMA,
        "ok": False,
        "accepted": False,
        "conformant": False,
        "status": TOMBSTONE_STATUS,
        "output_permitted": False,
        "error": {
            "code": "generator-retired",
            "detail": (
                "The historical generator cannot emit a registry-acceptable "
                "holocard. Its interim mnemonic vocabulary is not the claimed "
                "registry vocabulary."
            ),
        },
        "historical_observation": {
            "rappid": rappid,
            "kind": kind,
            "owner": owner,
            "name": name,
            "display_name": display_name,
            "derived_seed": str(seed),
            "interim_mnemonic_preview": seed_to_words(seed),
            "requested_version": version,
            "requested_category": category,
            "requested_license": license,
            "requested_embed_avatar_svg": bool(embed_avatar_svg),
            "requested_gate_url": gate_url,
        },
        "owner_review_required": True,
        "replacement_requirement": (
            "Use a separately reviewed generator whose exact schema and "
            "registry vocabulary are authenticated and whose output validates "
            "before publication."
        ),
    }


# ─── Self-check ───────────────────────────────────────────────────────────

def _self_check() -> dict:
    issues = []
    test_rappid = "rappid:@test/example:abc123def456"
    seed_a = derive_seed(test_rappid)
    seed_b = derive_seed(test_rappid)
    if seed_a != seed_b:
        issues.append("seed not deterministic")
    if not (0 <= seed_a < (1 << 64)):
        issues.append("seed out of unsigned-64 range")

    refusal = generate_holo_card(
        test_rappid, "neighborhood", "test", "example", "Example"
    )
    if refusal.get("schema") != HISTORICAL_OUTPUT_SCHEMA:
        issues.append("tombstone emitted the wrong historical schema")
    if refusal.get("ok") is not False or refusal.get("accepted") is not False:
        issues.append("tombstone became success-shaped")
    if refusal.get("conformant") is not False:
        issues.append("tombstone claimed conformance")

    # Avatar bounds
    avatar = generate_avatar_svg(seed_a, "neighborhood")
    if len(avatar) > 64 * 1024:
        issues.append(f"avatar exceeds spec limit 64 KB ({len(avatar)} bytes)")

    qr = generate_summon_qr_svg(seed_a, "https://test.example.com/")
    if "summon" not in qr.lower():
        issues.append("summon QR missing summon URL reference")

    return {
        "ok": False,
        "accepted": False,
        "conformant": False,
        "status": TOMBSTONE_STATUS,
        "self_check_passed": len(issues) == 0,
        "issues": issues,
        "kinds":  available_kinds(),
        "sample_seed":        seed_a,
        "sample_incantation": seed_to_words(seed_a),
    }


if __name__ == "__main__":
    import sys
    chk = _self_check()
    print(json.dumps(chk, indent=2))
    sys.exit(1)
