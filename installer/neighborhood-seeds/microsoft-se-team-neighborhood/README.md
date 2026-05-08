# Microsoft SE Team — Neighborhood (public gate)

This is the **public gate** of the Microsoft SE Team RAPP neighborhood. The gate is the only thing visible to the world. The workflow — shared agents, member roster, twin chat, decisions — lives in a private companion repo and is gated by GitHub collaborator membership.

```
public  →  github.com/kody-w/microsoft-se-team-neighborhood          ← you are here
private →  github.com/kody-w/microsoft-se-team-neighborhood-private  ← workflow + members
```

## What you can see from outside

- **Identity** — name, sigil, purpose, lineage
- **Card** — `card.json` (the trade card)
- **Public-safe agents** — `agents/neighborhood_introduce_agent.py` only
- **Join path** — open an Issue requesting access; a current member can grant it

## What you can NOT see from outside

- The member roster (`members.json` is in the private companion)
- The neighborhood-shared agents (federate, ask, subscribe)
- Decisions, runbooks, snapshots
- Any twin-chat traffic

## How a brainstem subscribes

```bash
brainstem join https://github.com/kody-w/microsoft-se-team-neighborhood
```

The brainstem will:

1. Read this gate's `neighborhood.json` to find the private companion URL
2. Try to fetch the private companion (using your GitHub token from `gh auth`)
3. If you're a collaborator → mount neighborhood agents, sync members, you're in
4. If you're not → offer to open a join Issue on this gate repo

## Schema

Identity: `rapp-neighborhood/1.0`
Trade card: `rapp-card/1.0`
Facets: `rapp-public-facets/1.0`

## Lineage

Planted from the RAPP species root: <https://github.com/kody-w/RAPP>.

This is the first canonical demonstration of the **public gate / private workflow** pattern (RAPP Neighborhood Protocol §2 trust scopes; `private_companion` block in `rappid.json`).
