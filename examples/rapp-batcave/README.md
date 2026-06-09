# 🦇 The Batcave

A **private RAPP neighborhood workspace**. Every member gets a **cubby** —
isolated housing for their entire rapp estate (agents, organs, senses,
rapplications, whole neighborhoods, eggs) — the same environment as their
on-device brainstem, smashed into a directory the rest of the crew can
browse and learn from.

- **Identity:** `rappid:@kody-w/rapp-batcave:72c739f277aade85ceb863c031b6c2998d577c7aa86f72652edae7e9c19eb100` (kind `workspace`, Eternity format, Art. XXXIV.1)
- **Visibility:** private, standalone — the repo IS the workspace
  (the `private-workspace` pattern; membership = collaborator status)
- **Front door:** none, by design. Outsiders 404; kited vTwins dial the
  rappid at the [payphone](https://kody-w.github.io/RAPP/pages/payphone.html) with their own GitHub auth.
- **Quirk:** `specs/CUBBY_PROTOCOL.md` — cubbies, streaming, show & tell
- **Specs hub:** https://kody-w.github.io/RAPP-Bible/#specs

## Why it exists

> "I have a private repo for my customer facing agents and then I use rar
> for ones that I want to share." — the common central resource problem.

The batcave is the shared private middle: store agents here instead of
committing them to any brainstem grail repo, stream them into a local
brainstem on demand (`batcave load` → `.git/info/exclude`, zero commit
risk), and show the crew what you're cooking (`batcave show_and_tell`).
Kited vTwins join with the same GitHub account that holds their
collaborator access — same contract on every substrate.

## Join (collaborators)

```bash
gh repo clone kody-w/rapp-batcave
cp agents/batcave_agent.py <your-brainstem>/agents/   # the participation agent
# then from your brainstem chat:
#   "batcave join"                      → creates cubbies/<you>/
#   "batcave browse"                    → see everyone's cubbies
#   "batcave load cubby=kody-w"         → stream agents into your brainstem
#   "batcave show_and_tell title=..."   → post to the room
```

Not a collaborator yet? Ask the operator (@kody-w) — out-of-band by design.

## The map

| Path | What |
|---|---|
| `cubbies/<handle>/` | one member's estate housing (isolated; owner-only writes) |
| `cubbies/_template/` | copy me to join by hand |
| `events/` | append-only signed show-and-tell stream |
| `agents/batcave_agent.py` | the participation agent (`@kody-w/batcave`) |
| `rar/index.json` | sha256-pinned participation kit (`rapp-rar-index/1.1`) |
| `specs/` | the god spec + workspace protocol + the cubby quirk |
| `.well-known/batcave.egg` | tiny invite egg (pointers, not contents) |

Planted from [`kody-w/RAPP`](https://github.com/kody-w/RAPP) `examples/rapp-batcave/` by
`tools/plant_batcave.py`.
