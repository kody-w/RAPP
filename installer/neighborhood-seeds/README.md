# RAPP Neighborhood seeds

This directory holds the canonical **public-gate / private-companion** seed pair for the first cross-device, GitHub-collaborator-gated RAPP neighborhood. Two repos, one identity. The pattern is reusable — copy this layout to plant any new neighborhood.

```
microsoft-se-team-neighborhood/          ← public gate (anonymous-friendly)
microsoft-se-team-neighborhood-private/  ← private workflow (auth-gated)
```

Both seeds carry the same `neighborhood_rappid` (`869ea057-4755-47ec-80df-54551ecf8581`) — they are two faces of one neighborhood, cross-referenced via `private_companion` (in the gate) and `gate_repo` (in the companion).

## The bigger picture — estate × metropolis

A user's brainstem subscribes to **many** neighborhoods. Their **estate** is the union of all those subscriptions — local on-device, cross-device, public, private. Estates mesh through shared neighborhoods, and an **AI metropolis** is the emergent topology of all those meshes — exactly like physical urban zoning is emergent rather than declared.

Operator identity (the operator's personal `rappid`) is the spine. Work products in any neighborhood attribute back to the operator. Users are in the loop **async** — agents do work in zones across the metropolis; results land in the operator's estate inbox; the user checks back when ready.

The endpoint that synthesizes this lens is `GET /api/neighborhoods/estate`. See `pages/vault/Decisions/2026-05-08 — Estate is the operator's union of neighborhoods.md`.

## Why public gate + private companion

Bill's workflow at Microsoft (and most enterprise team workflows) **must not** be visible publicly, but the team also wants the discovery surface so people can find them and request access. The split solves this:

- **Public gate** carries identity, card, lineage, and a join-Issue path. Anyone can read it.
- **Private companion** carries the roster, agents, decisions, runbooks, twin chat. Only GitHub collaborators can read it.

The trust anchor is GitHub collaborator status on the private companion — no separate identity service, no key registry. The gate's `neighborhood.json` has a `private_companion` block (existing schema, see `ECOSYSTEM.md` §3) advertising where the workflow lives.

## Stand it up — first time, by hand

These are the exact commands kody-w runs to push both repos and invite rappter1. Once verified, the same flow extends to Bill.

### 1. Push the public gate

```bash
cd installer/neighborhood-seeds/microsoft-se-team-neighborhood
git init -b main
git add .
git commit -m "Plant Microsoft SE Team neighborhood — public gate"

gh repo create kody-w/microsoft-se-team-neighborhood \
    --public \
    --description "Microsoft SE Team — RAPP neighborhood (public gate). Workflow is gated to authenticated members." \
    --homepage "https://kody-w.github.io/microsoft-se-team-neighborhood/" \
    --source . --push

# Turn on Pages (root, main branch)
gh api -X POST /repos/kody-w/microsoft-se-team-neighborhood/pages \
    -f source.branch=main -f source.path=/
```

### 2. Push the private companion

```bash
cd ../microsoft-se-team-neighborhood-private
git init -b main
git add .
git commit -m "Plant Microsoft SE Team neighborhood — private workflow"

gh repo create kody-w/microsoft-se-team-neighborhood-private \
    --private \
    --description "Microsoft SE Team — RAPP neighborhood private workflow. Auth-gated to GitHub collaborators." \
    --source . --push
```

### 3. Add rappter1 as a collaborator on the private companion

Once `rappter1`'s GitHub account exists:

```bash
gh api -X PUT /repos/kody-w/microsoft-se-team-neighborhood-private/collaborators/rappter1 \
    -f permission=push
```

`rappter1` accepts the invite via email or `gh repo accept-invitation`. They are now a member of the SE Team neighborhood.

### 4. (Later) Invite Bill the same way

```bash
gh api -X PUT /repos/kody-w/microsoft-se-team-neighborhood-private/collaborators/<bill-gh-login> \
    -f permission=push
```

## Verify the keystone — `kody-w` + `rappter1` loop

Run **before** inviting Bill so you know the plumbing works.

### A. Schema + seed coherence (no GitHub needed)

```bash
node tests/neighborhood-membership.mjs
python3 tests/test_neighborhood_membership_organ.py
```

Expected: 15 + 15 passing. These verify both seeds are well-formed, cross-references match, and the membership organ's routing/dispatch logic works.

### B. End-to-end subscription (kody-w seat)

After both repos are pushed and rappter1 is added as a collaborator:

```bash
# Start the brainstem
cd rapp_brainstem && ./start.sh   # Terminal 1

# In another terminal, subscribe to the gate
curl -s -X POST http://localhost:7071/api/neighborhoods/join \
     -H 'content-type: application/json' \
     -d '{"gate_url":"https://github.com/kody-w/microsoft-se-team-neighborhood"}' \
     | jq

# Confirm subscription landed
curl -s http://localhost:7071/api/neighborhoods | jq

# Roster (should show kody-w + rappter1)
curl -s http://localhost:7071/api/neighborhoods/kody-w/microsoft-se-team-neighborhood-private/members | jq

# Estate view (synthesized — your full RAPP city as one operator sees it)
curl -s http://localhost:7071/api/neighborhoods/estate | jq
```

Expected:

- `joined: true` from `/join`
- `role_inferred: "founder"` (because kody-w has admin on the private companion)
- Member list shows two seats
- Estate view shows one subscription, kind=neighborhood, kody-w bridges (trivially) to itself

### C. End-to-end subscription (rappter1 seat)

From a separate machine — or the same machine with a separate `gh` profile:

```bash
gh auth switch --user rappter1   # or use a separate GH_TOKEN env var
brainstem identity                # confirm rappter1's brainstem rappid

# Subscribe
curl -s -X POST http://localhost:7071/api/neighborhoods/join \
     -H 'content-type: application/json' \
     -d '{"gate_url":"https://github.com/kody-w/microsoft-se-team-neighborhood"}' \
     | jq
```

Expected:

- `joined: true`
- `role_inferred: "member"` (rappter1 has push but not admin)
- Member list reachable, identical content to kody-w's view (modulo cache-time)

### D. Negative test — non-collaborator

From a `gh` profile that is **not** a collaborator on the private companion:

```bash
curl -s -X POST http://localhost:7071/api/neighborhoods/join \
     -H 'content-type: application/json' \
     -d '{"gate_url":"https://github.com/kody-w/microsoft-se-team-neighborhood"}' \
     | jq
```

Expected:

- HTTP 403
- `joined: false`
- `next_step.action: "open_join_issue"` with a pre-filled GitHub Issue URL on the public gate

## What's working today (Phase 1)

- ✅ Two-repo split with shared identity
- ✅ Subscription via `brainstem join` (organ endpoint)
- ✅ Collaborator-gate verification
- ✅ Roster sync (cached + reconciled against live API)
- ✅ Estate view with zones + bridges
- ✅ Neighborhood agents staged on the private companion (introduce / ask / federate / subscribe)
- ✅ Async loop-back primitive (Issues + subscribe agent)

## What's still to land for the full metropolis vision (Phase 2+)

Tracked candidates, in the order the operator would feel the value:

1. **Operator inbox** — single async queue across all subscriptions. "While you were away, your agents did X in zone A, Y in zone B." Aggregator on top of the subscribe agents.
2. **Estate-level personal memory** — facts you learn in one zone follow you to others. (Per-neighborhood facts stay scoped.)
3. **Cross-neighborhood agent invocation** — call a capability in zone B from zone A while preserving operator-identity attribution.
4. **Hot-mount on subscribe** — neighborhood agents land in the running brainstem's tool palette automatically (with `neigh_<slug>_` prefix to namespace).
5. **Inter-estate meshing protocol implementation** — the wire-level rules for when your estate brushes mine through a shared neighborhood.
6. **Topology view** — the visual "map of the city" rendered from `/estate` data + bridge cross-references.

## The agent vocabulary rule still applies

Per `ANTIPATTERNS.md` §1: every plug-in unit is an **agent**. The shared agents in the private companion are agents — never "skills", "plugins", "routines", or "loops" in code, copy, or commit messages.

## Schemas

- `rapp-neighborhood/1.0` — `neighborhood.json`
- `rapp-neighborhood-members/1.0` — `members.json`
- `rapp-public-facets/1.0` — `facets.json`
- `rapp-neighborhoods-cache/1.0` — `~/.brainstem/neighborhoods.json` (organ-owned)
- `rapp-neighborhood-subscription/1.0` — single subscription record
- `rapp-estate/1.0` — synthesized estate view
- `rapp-twin-chat/1.0` — message envelope (federate / ask / introduce)
- `rapp-neighborhood-subscribe-report/1.0` — subscribe agent's reconciliation report

Per `ANTIPATTERNS.md` §3: bump the schema version when changing fields. Shims for half-released features are forbidden.

## Cross-references

- [`NEIGHBORHOOD_PROTOCOL.md`](../../NEIGHBORHOOD_PROTOCOL.md) — wire-level rules: trust scopes, channel types, knowledge-exchange primitives
- [`HERO_USECASE.md`](../../HERO_USECASE.md) — the canonical scenarios this work serves; needs §6 "Cross-Estate Metropolis" once Phase 2 lands
- [`ECOSYSTEM.md`](../../ECOSYSTEM.md) — single-organism layout (where `private_companion` originated)
- [`ANTIPATTERNS.md`](../../ANTIPATTERNS.md) — what we will never do; rules locked
