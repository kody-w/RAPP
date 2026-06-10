# WORKSPACE_PROTOCOL — workspace native primitive

> **Frozen subset** bundled on 2026-06-10T00:00:13Z.

## The work-item primitive

Work happens via labeled GitHub Issues. Three labels:

| Label | Meaning |
|---|---|
| `workspace-todo`        | Open work-item; assignable to any member |
| `workspace-in-progress` | Claimed by someone; durable assignment |
| `workspace-done`        | Artifact landed; result is consumable by other members |

## Membership

- See `../members.json` for the current roster.
- Membership is gated. Non-members can READ; only members can `workspace-todo` → `in-progress` → `done`.
- To join: open a join request Issue OR contact the operator out-of-band.

## Steps to participate

1. **Confirm membership** — your `github_login` should appear in `../members.json`.
2. **Read open work** — Issues labeled `workspace-todo`.
3. **Pick one** — claim via comment + relabel to `workspace-in-progress`.
4. **Do the work** — open a PR or post the artifact as a comment, depending on the work-item type.
5. **Mark done** — relabel `workspace-done` once the artifact lands.

## Hard rules

- **Don't act on items not assigned to you** unless they're explicitly open.
- **Don't make the workspace public** — it's gated for a reason.
- **Don't bypass review** — workspace PRs need an owner-set review threshold.
- **Don't drop work for non-members** in this workspace — open a separate Issue OR redirect to a public neighborhood.

---

*Async work, named members, no spectators.*
