"""join_neighborhood_agent — minimum-viable neighborhood join.

The hero shareability use case (Article XXXVII): a brainstem operator
runs `brainstem.py` locally, says "join kody-w/<neighborhood-repo>",
and the neighborhood's workflow is immediately runnable in their own
agents/ directory. No cloud, no Azure, no auth flow — just local.

This agent composes existing primitives:

  1. mint_rappid (utils/bond.py) — ensures ~/.brainstem/rappid.json
     exists. Idempotent: returns the existing rappid if already minted
     by install.sh, mints fresh otherwise. The "rappid is generated on
     join" property falls out of this for-free.

  2. fetch neighborhood.json — verifies the URL points at a real RAPP
     gate (rapp-neighborhood/1.0 schema). Refuses non-neighborhoods.

  3. RarLoader (rar_loader_agent.py) — hot-loads the neighborhood's
     `rar/index.json` workflow into the local agents/ directory,
     sha256-verified.

  4. neighborhoods.json — records the subscription locally so future
     `list neighborhoods` / `leave` operations have something to walk.

Operator-mediated by design: default dry_run=True (shows what would
install + verify the gate); set dry_run=False to actually install +
record. Existing files in the local agents/ directory are never
clobbered — RarLoader's sha256 contract guarantees additive-only.

Schema: `rapp-neighborhood-join-result/1.0`.
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone

try:
    from agents.basic_agent import BasicAgent
except ImportError:  # standalone import (tests)
    from basic_agent import BasicAgent


def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def _brainstem_home() -> str:
    return os.path.expanduser(os.environ.get("BRAINSTEM_HOME", "~/.brainstem"))


def _local_agents_dir() -> str:
    explicit = os.environ.get("AGENTS_PATH")
    if explicit:
        return explicit
    here = os.path.dirname(os.path.abspath(__file__))
    return here  # this file IS in agents/, so its dir is the target


def _neighborhoods_path(home: str) -> str:
    return os.path.join(home, "neighborhoods.json")


def _read_subscriptions(home: str) -> list[dict]:
    path = _neighborhoods_path(home)
    if not os.path.exists(path):
        return []
    try:
        return json.load(open(path)).get("subscribed", [])
    except Exception:
        return []


def _write_subscriptions(home: str, subscribed: list[dict]) -> None:
    os.makedirs(home, exist_ok=True)
    payload = {
        "schema": "rapp-neighborhood-subscriptions/1.0",
        "updated_at": _now_iso(),
        "subscribed": subscribed,
    }
    with open(_neighborhoods_path(home), "w") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def _fetch_neighborhood_json(gate_repo: str) -> tuple[dict | None, str]:
    url = (
        f"https://raw.githubusercontent.com/{gate_repo}"
        f"/main/neighborhood.json"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "rapp-join/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode()), url
    except Exception as e:
        return None, f"fetch failed: {e}"


class JoinNeighborhoodAgent(BasicAgent):
    metadata = {
        "name": "JoinNeighborhood",
        "description": (
            "Join a planted RAPP neighborhood. Mints the operator's rappid "
            "if missing, hot-loads the neighborhood's workflow agents into "
            "the local brainstem (sha256-verified, additive-only), and "
            "records the subscription locally. The minimum-viable join "
            "flow: after this runs, every agent the neighborhood ships is "
            "callable in this brainstem with no further setup. Default "
            "dry_run=True; set dry_run=False to actually install."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "gate_repo": {
                    "type": "string",
                    "description": (
                        "GitHub repo of the neighborhood gate, e.g. "
                        "'kody-w/billwhalen-agent-team'. Owner/name only."
                    ),
                },
                "dry_run": {
                    "type": "boolean",
                    "default": True,
                    "description": (
                        "If true, fetches the gate metadata and shows what "
                        "would install without writing. Set false to commit."
                    ),
                },
            },
            "required": ["gate_repo"],
        },
    }

    def __init__(self):
        self.name = "JoinNeighborhood"

    def perform(self, **kwargs) -> str:
        gate_repo = (kwargs.get("gate_repo") or "").strip().strip("/")
        dry_run = bool(kwargs.get("dry_run", True))

        if not gate_repo or "/" not in gate_repo:
            return json.dumps({
                "schema": "rapp-neighborhood-join-result/1.0",
                "ok": False,
                "error": "gate_repo must be in 'owner/name' form",
            })

        # 1. Verify the gate is a real RAPP neighborhood.
        nb, source = _fetch_neighborhood_json(gate_repo)
        if not nb:
            return json.dumps({
                "schema": "rapp-neighborhood-join-result/1.0",
                "ok": False,
                "error": source,
                "gate_repo": gate_repo,
            })
        if nb.get("schema") != "rapp-neighborhood/1.0":
            return json.dumps({
                "schema": "rapp-neighborhood-join-result/1.0",
                "ok": False,
                "error": (
                    f"not a RAPP neighborhood (schema={nb.get('schema')!r}); "
                    f"refusing to join"
                ),
                "gate_repo": gate_repo,
            })

        nb_rappid = nb.get("neighborhood_rappid") or nb.get("rappid")
        nb_name = nb.get("display_name") or nb.get("name") or gate_repo

        # 2. Mint or read local operator rappid (idempotent).
        home = _brainstem_home()
        operator_rappid = None
        mint_note = None
        try:
            from utils.bond import mint_rappid  # type: ignore
            id_dict = mint_rappid(home)
            operator_rappid = id_dict.get("rappid")
        except Exception as e:
            mint_note = f"mint deferred: {e}"

        # 3. Hot-load the neighborhood's workflow via RarLoader.
        loader_result: dict | None = None
        try:
            from agents.rar_loader_agent import RarLoaderAgent  # type: ignore
            loader = RarLoaderAgent()
            raw = loader.perform(
                gate_repo=gate_repo,
                dry_run=dry_run,
                target_dir=_local_agents_dir(),
            )
            loader_result = json.loads(raw) if isinstance(raw, str) else raw
        except Exception as e:
            loader_result = {"ok": False, "error": f"RarLoader failed: {e}"}

        # 4. Record subscription (only on commit).
        subscription_added = False
        if not dry_run:
            subs = _read_subscriptions(home)
            if not any(s.get("gate_repo") == gate_repo for s in subs):
                subs.append({
                    "gate_repo": gate_repo,
                    "neighborhood_rappid": nb_rappid,
                    "display_name": nb_name,
                    "joined_at": _now_iso(),
                })
                _write_subscriptions(home, subs)
                subscription_added = True

        next_step = (
            f"Joined {nb_name}. Workflow agents are now in {_local_agents_dir()} "
            f"and callable from this brainstem. Subscription recorded at "
            f"{_neighborhoods_path(home)}."
            if not dry_run
            else (
                f"Dry-run for {gate_repo}. Re-run with dry_run=False to "
                f"install the workflow + record the subscription."
            )
        )

        return json.dumps({
            "schema": "rapp-neighborhood-join-result/1.0",
            "ok": True,
            "dry_run": dry_run,
            "gate_repo": gate_repo,
            "neighborhood_rappid": nb_rappid,
            "neighborhood_name": nb_name,
            "operator_rappid": operator_rappid,
            "mint_note": mint_note,
            "rar_loader": loader_result,
            "subscription_added": subscription_added,
            "next_step": next_step,
        }, indent=2)
