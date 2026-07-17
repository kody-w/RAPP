"""Product-local checks for the legacy ecosystem offspring inventory.

This module is not RAPP/1 protocol authority. It is imported by
`tools/ecosystem_audit.py` to compare repository-product conventions.

Stdlib-only. Safe to read from the audit script which itself runs before
any venv exists.

The Bond Pulse audit walks every offspring listed in
`pages/metropolis/index.json`, looks up the offspring's `kind`, fetches
the product-local expectations here, and reports drift. These checks are data,
not protocol law — a future fix-bot can read this same dict and propose
corrections per the same rules.
"""

from __future__ import annotations

# ── kernel base + seed-required base ──────────────────────────────────────
#
# KERNEL_BASE_FILES is the full kernel-tier set (per CONSTITUTION Art. XXXIII);
# these live in a running brainstem install. SEED_REQUIRED_AGENTS is what a
# PLANTED seed's agents/ directory must ship for portability — only the base
# class. The other two kernel agents are brainstem-internal (manage_memory
# and context_memory are loaded by the joining brainstem itself, not by the
# seed). The audit's `kernel_base_check` validates SEED_REQUIRED_AGENTS — the
# minimum a seed needs to be self-sufficient when cloned.

KERNEL_BASE_FILES = (
    "basic_agent.py",
    "manage_memory_agent.py",
    "context_memory_agent.py",
)

SEED_REQUIRED_AGENTS = (
    "basic_agent.py",
)

# ── per-kind contract ──────────────────────────────────────────────────────

# Each KindContract dict carries:
#   required_files          paths that MUST exist at offspring root
#                           (or in the named subdir for path-prefixed entries)
#   expected_product_schemas path → product-local schema string to compare
#   rappid_kind             the `kind` the offspring's rappid.json RECORD must
#                           declare. Per the consolidated rappid form
#                           (rappid:@<owner>/<slug>:<64hex>), kind lives in the
#                           rappid.json record FIELD, never as a string prefix —
#                           so the audit reads d["kind"], not a "rappid:v2:<kind>:"
#                           string prefix. The rappid STRING must match exact
#                           RAPP/1 section 6.1; legacy forms are always drift.
#                           (None = kind not enforced, e.g. catalog/template/twin)
#   identity_block_required soul.md must contain the spec-compliant Identity sentinel
#   rar_required            rar/index.json must exist + sha256-validate against agents/
#   kernel_base_check       must ship the three KERNEL_BASE_FILES under agents/
#   optional_files          tolerated-if-absent (no drift)
#   notes                   human-readable description; surfaces in the audit report

CONTRACTS: dict = {

    # ── neighborhoods (the canonical multi-participant unit) ────────────────
    "neighborhood": {
        "required_files": [
            "rappid.json",
            "neighborhood.json",
            "soul.md",
            "card.json",
            "members.json",
            "rar/index.json",
            ".nojekyll",
        ],
        "expected_product_schemas": {
            "rappid.json":       "rapp/1",
            "neighborhood.json": "rapp-neighborhood/1.0",
            "card.json":         "rapp-card/1.0",
            "members.json":      "rapp-neighborhood-members/1.0",
            "rar/index.json":    "rapp-rar-index/1.0",
        },
        "rappid_kind":             "neighborhood",
        "identity_block_required": True,
        "rar_required":            True,
        "kernel_base_check":       True,
        "optional_files":          ["index.html", "holo.md", "data/colony.json"],
        "notes": "Standard collaborator-gated neighborhood. Public gate + optional private companion.",
    },

    # ── ant-farm: same as neighborhood + holo.md is REQUIRED ────────────────
    "ant-farm": {
        "required_files": [
            "rappid.json",
            "neighborhood.json",
            "soul.md",
            "card.json",
            "members.json",
            "rar/index.json",
            "holo.md",
            ".nojekyll",
        ],
        "expected_product_schemas": {
            "rappid.json":       "rapp/1",
            "neighborhood.json": "rapp-neighborhood/1.0",
            "card.json":         "rapp-card/1.0",
            "members.json":      "rapp-neighborhood-members/1.0",
            "rar/index.json":    "rapp-rar-index/1.0",
        },
        "rappid_kind":             "ant-farm",
        "identity_block_required": True,
        "rar_required":            True,
        "kernel_base_check":       True,
        "optional_files":          ["index.html", "data/colony.json"],
        "notes": "Autonomous distributed swarm. holo.md is the any-AI-ingestable contract — required, not optional.",
    },

    # ── twin: a single planted organism (e.g. heimdall) ────────────────────
    "twin": {
        "required_files": [
            "rappid.json",
            "soul.md",
            "card.json",
            "index.html",  # the gate / front door
        ],
        "expected_product_schemas": {
            "rappid.json": "rapp/1",
            "card.json":   "rapp-card/1.0",
        },
        "rappid_kind":             None,  # twin rappids may use various kinds (personal/place/experiment/etc.)
        "identity_block_required": True,
        "rar_required":            False,  # twins MAY ship rar/ but it's not required
        "kernel_base_check":       False,
        "optional_files":          ["agents/", "rar/index.json", "doorman/index.html",
                                    "data/frames.json", ".brainstem_data/memory.json"],
        "notes": "Single planted organism with public gate (front door). The canonical example: kody-w/heimdall.",
    },

    # ── workspace: private-pattern (gate + private companion) ──────────────
    "workspace": {
        "required_files": [
            "rappid.json",
            "neighborhood.json",
            "members.json",
        ],
        "expected_product_schemas": {
            "rappid.json":       "rapp/1",
            "neighborhood.json": "rapp-neighborhood/1.0",
            "members.json":      "rapp-neighborhood-members/1.0",
        },
        "rappid_kind":             "workspace",
        "identity_block_required": False,  # workspaces are private; gate may be terse
        "rar_required":            False,
        "kernel_base_check":       False,
        "optional_files":          ["soul.md", "card.json", "rar/index.json", ".nojekyll", "index.html"],
        "notes": "Private workspace pattern (gate + private companion). Less ceremonial than neighborhood; soul/card optional.",
    },

    # ── braintrust: research/contribution-collection pattern ────────────────
    "braintrust": {
        "required_files": [
            "rappid.json",
            "neighborhood.json",
            "card.json",
            "rar/index.json",
        ],
        "expected_product_schemas": {
            "rappid.json":       "rapp/1",
            "neighborhood.json": "rapp-neighborhood/1.0",
            "card.json":         "rapp-card/1.0",
            "rar/index.json":    "rapp-rar-index/1.0",
        },
        "rappid_kind":             "braintrust",
        "identity_block_required": True,
        "rar_required":            True,
        "kernel_base_check":       True,
        "optional_files":          ["soul.md", "members.json", ".nojekyll", "index.html"],
        "notes": "Project braintrust — collaborative research pattern. Requires rar/ for participation kit.",
    },

    # ── catalog: rapp-zoo, rapp-store, RAR (directory surfaces, not neighborhoods) ─
    "catalog": {
        "required_files": [
            "index.html",  # the only required surface
        ],
        "expected_product_schemas": {},
        "rappid_kind":             None,
        "identity_block_required": False,
        "rar_required":            False,
        "kernel_base_check":       False,
        "optional_files":          ["rappid.json", "card.json", "soul.md"],
        "notes": "Directory / catalog surface (rapp-zoo, RAPP_Store, RAPP_Sense_Store, RAR). gate_url is what matters; deeper structure varies per catalog.",
    },

    # ── template: forkable-as-template repos (no live state required) ──────
    "template": {
        "required_files": [
            "rappid.json",
        ],
        "expected_product_schemas": {
            "rappid.json": "rapp/1",
        },
        "rappid_kind":             None,  # templates may carry the kind they spawn (workspace/braintrust)
        "identity_block_required": False,
        "rar_required":            False,
        "kernel_base_check":       False,
        "optional_files":          ["soul.md", "card.json", "neighborhood.json", "README.md",
                                    "rar/index.json", ".nojekyll"],
        "notes": "Template repo — exists for forking. May carry partial scaffolding; only rappid.json is mandatory so fork lineage is recoverable.",
    },

    # ── installer: special tooling repo (kody-w/rapp-installer) ────────────
    "installer": {
        "required_files": [
            "install.sh",
        ],
        "expected_product_schemas": {},
        "rappid_kind":             None,
        "identity_block_required": False,
        "rar_required":            False,
        "kernel_base_check":       False,
        "optional_files":          ["install.ps1", "install.cmd", "README.md"],
        "notes": "The install one-liner host. Sacred URL shape per CONSTITUTION Article V; only checks the entry point exists.",
    },

    # ── egg-hub: the public catalog of .egg cartridges ─────────────────────
    "egg-hub": {
        "required_files": [
            "index.json",
        ],
        "expected_product_schemas": {},
        "rappid_kind":             None,
        "identity_block_required": False,
        "rar_required":            False,
        "kernel_base_check":       False,
        "optional_files":          ["README.md", "eggs/"],
        "notes": "Public egg-cartridge catalog (kody-w/rapp-egg-hub). Mostly content-addressed eggs in a curated list.",
    },
}


# ── kind resolution ────────────────────────────────────────────────────────

# Map metropolis-index `kind` strings to contract keys. Some entries declare
# their kind explicitly (kind="ant-farm"); others (rapp-zoo, rapp-store, RAR)
# need to be inferred from name/role/tags.

_KIND_ALIASES: dict = {
    # entry["kind"] value     → contract key
    "ant-farm":      "ant-farm",
    "neighborhood":  "neighborhood",
    "workspace":     "workspace",
    "braintrust":    "braintrust",
    "twin":          "twin",
    "directory":     "catalog",
    "catalog":       "catalog",
    "template":      "template",
    "installer":     "installer",
    "egg-hub":       "egg-hub",
}


def kind_for_entry(entry: dict) -> str:
    """Map a metropolis index entry's `kind` field to a contract key.

    Resolution order:
      1. If `entry_role == "template"` regardless of declared kind → "template".
      2. If declared `kind` is in _KIND_ALIASES → use that.
      3. Catch known-by-name catalog repos (rapp-zoo, rapp-store, rapp-sense-store, rar) → "catalog".
      4. Catch installer + egg-hub by name.
      5. Default: "neighborhood" (the most common shape).
    """
    if (entry.get("entry_role") or "").lower() == "template":
        return "template"

    declared_kind = (entry.get("kind") or "").lower()
    if declared_kind in _KIND_ALIASES:
        return _KIND_ALIASES[declared_kind]

    name = (entry.get("name") or "").lower()
    if name in ("rapp-zoo", "rapp-store", "rapp_store", "rapp-sense-store", "rapp_sense_store", "rar"):
        return "catalog"
    if name in ("rapp-installer",):
        return "installer"
    if name in ("rapp-egg-hub",):
        return "egg-hub"

    return "neighborhood"


def all_kinds() -> list:
    """Sorted list of every contract key. Used by the audit to validate
    that every kind declared in the metropolis index has a contract."""
    return sorted(CONTRACTS.keys())


def contract_for_kind(kind: str) -> dict:
    """Look up a contract by key. Returns the neighborhood contract if
    the kind is unknown (audit will flag the unknown kind separately)."""
    return CONTRACTS.get(kind) or CONTRACTS["neighborhood"]


# ── self-check (importable) ────────────────────────────────────────────────

def _self_check() -> dict:
    """Verify the contract is internally consistent. Useful for tests."""
    issues = []
    for kind, c in CONTRACTS.items():
        for required_field in ("required_files", "expected_product_schemas", "rappid_kind",
                               "identity_block_required", "rar_required", "kernel_base_check",
                               "optional_files", "notes"):
            if required_field not in c:
                issues.append(f"{kind}: missing field {required_field}")
        # Every product schema key must name a required or optional file.
        all_paths = set(c.get("required_files", [])) | set(c.get("optional_files", []))
        for sch_path in (c.get("expected_product_schemas") or {}):
            if sch_path not in all_paths:
                issues.append(
                    f"{kind}: expected_product_schemas references {sch_path} "
                    "but it is not in required/optional files"
                )
    return {
        "kinds": all_kinds(),
        "kind_count": len(CONTRACTS),
        "issues": issues,
        "ok": not issues,
        "authority_state": "product-local-observation",
        "rapp_protocol_authority": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(_self_check(), indent=2))
