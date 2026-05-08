# Microsoft SE Team — Neighborhood (private workflow)

This is the **private companion** of the Microsoft SE Team RAPP neighborhood. The workflow lives here. The public-facing gate is at <https://github.com/kody-w/microsoft-se-team-neighborhood>.

```
public gate    →  github.com/kody-w/microsoft-se-team-neighborhood
private (here) →  github.com/kody-w/microsoft-se-team-neighborhood-private
```

## Membership = GitHub collaborator status on THIS repo

If you can read this file, you are a member. The trust anchor is GitHub push permission (no separate identity service, no key registry — see `NEIGHBORHOOD_PROTOCOL.md` §2 in the RAPP species root).

## What's in here

| Path | Purpose |
|---|---|
| `neighborhood.json` | Identity. Shares the same `neighborhood_rappid` as the public gate — two repos, one neighborhood. |
| `members.json` | Roster cache. Authoritative source is `GET /repos/<owner>/<repo>/collaborators`. |
| `facets.json` | What's exposed at which scope (member-only vs personal). |
| `agents/` | Neighborhood-shared agents. Every member's brainstem mounts these on subscribe. |
| `state/decisions/` | Shared decision narratives. |
| `state/runbooks/` | Shared operational runbooks. |
| `state/snapshots/` | Knowledge snapshots — point-in-time captures of shared state. |

## Shared agents (auto-mounted on subscribe)

| Agent | Purpose |
|---|---|
| `neighborhood_introduce_agent.py` | Member-aware introduction — names members + capabilities. |
| `neighborhood_ask_agent.py` | Pull a fact from a specific named neighbor's twin. |
| `neighborhood_federate_agent.py` | Fan-out twin-chat across all online members; falls back to async Issues for offline. |
| `neighborhood_subscribe_agent.py` | Long-poll listener for `neighborhood-message` Issues + members.json reconciliation. |

## How to join (operator workflow)

1. A new prospect opens a join Issue on the public gate
2. Existing member runs: `gh api -X PUT /repos/kody-w/microsoft-se-team-neighborhood-private/collaborators/<login>`
3. Prospect accepts the invite via email / GitHub notification
4. Prospect's brainstem runs `brainstem join https://github.com/kody-w/microsoft-se-team-neighborhood`
5. Prospect's brainstem detects collaborator access on this private repo, mounts neighborhood agents, and opens a PR adding their `github_login` + `rappid` + `seed_url` to `members.json`

## How to leave (operator workflow)

1. Member's brainstem runs `brainstem leave microsoft-se-team-neighborhood` (local unsubscribe)
2. Existing member runs: `gh api -X DELETE /repos/kody-w/microsoft-se-team-neighborhood-private/collaborators/<login>`
3. Next reconciliation removes the entry from `members.json`

## Self-healing properties

| Failure | Recovery |
|---|---|
| One member's brainstem offline | Federation skips them; Issue queued for async reply on reconnect |
| Half the members offline | Quorum agent answers from cached state + remaining online peers |
| All members offline except me | I answer from the last-synced cache (with a stale-pill in the response) |
| GitHub itself down | WebRTC tether to peers I have cached peer-IDs for; otherwise cache-only |
| My brainstem offline | Other members continue — neighborhood is online if ≥1 brainstem is online |

## Schema versioning

- `rapp-neighborhood/1.0` — `neighborhood.json`
- `rapp-neighborhood-members/1.0` — `members.json`
- `rapp-public-facets/1.0` — `facets.json`

Bump the schema version when changing fields. Shims for half-released features are forbidden (see `ANTIPATTERNS.md` §3).
