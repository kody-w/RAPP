# Private Workspace (template)

A standalone private RAPP workspace. No public gate. The repo IS the workspace. Membership is GitHub collaborator status on this repo. Solo at start; founder grants access one-by-one when ready.

This is the template for the **fourth visibility pattern** in RAPP:

- `public-gate` — public face of a split (Microsoft SE Team gate)
- `private` — private companion of a split
- `public` — standalone public neighborhood (Public Art Collective)
- **`private-workspace` — standalone private workspace (this template)**

## How to use this template

1. Clone this directory; rename the slug; update the `neighborhood.json` `name` + `display_name` + `github` fields.
2. Create a private GitHub repo with that name.
3. Push this content to it.
4. **You're the only member**. Use it solo.
5. When you want to add a collaborator: `gh api -X PUT /repos/<owner>/<repo>/collaborators/<login>` — that's the entire admission gate.
6. Their brainstem subscribes via `brainstem join https://github.com/<owner>/<repo>`. They mount the workspace agents.

## Workspace agents

| Agent | Purpose |
|---|---|
| `workspace_init_agent.py` | Bootstrap a fresh workspace — write the founder's first decision. |
| `workspace_decision_agent.py` | Log a decision narrative to `state/decisions/`. |
| `workspace_invite_agent.py` | Compose the exact `gh api` command to add a new collaborator. |
| `workspace_inbox_agent.py` | Surface async work products from federated agents — attributed to whichever operator's rappid did the work. |

## How federation flows back here

The workspace inbox is the operator-side aggregator described in the master plan ("the user is in the loop async"). When agents in OTHER neighborhoods (or this one's automated runs) finish work for a member, the result lands in `state/inbox/<utc>-<from-rappid>.json`. The `workspace_inbox_agent` surfaces those to the operator on next chat.

## Schema

- `rapp-neighborhood/1.0` (visibility: `private-workspace`)
- `rapp-neighborhood-members/1.0`
- `rapp-public-facets/1.0`
- `rapp-workspace-decision/1.0` (per `state/decisions/<n>-<slug>.md` frontmatter)
- `rapp-workspace-inbox-item/1.0` (per `state/inbox/<utc>-<from-rappid>.json`)

## Why this template exists

Bill described this in the design conversation: *"you can make the rapplication private."* For an SE solo working on something that's not yet ready to share — or for any operator who wants a private ai-driven workspace — this is the smallest possible neighborhood-pattern unit. It composes with everything else (subscribe to many; the union is your estate).
