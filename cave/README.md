# 🦇 The RAPP Cave

A **public RAPP neighborhood workspace** — the open sibling of the private
[Batcave](https://github.com/kody-w/rapp-batcave). Every member gets a **cubby**
— isolated housing for their entire rapp estate (agents, organs, senses,
rapplications, whole neighborhoods, eggs) — the same environment as their
on-device brainstem, smashed into a directory the whole world can browse, pull,
and learn from.

- **Identity:** `rappid:@kody-w/rapp-cave:ca72ca0a3cb90c357fb09e38b02f85f09935cacbf61e94740c57f1eb30a73e0a` (kind `workspace`, Eternity format, Art. XXXIV.1)
- **Parent:** `rappid:@kody-w/RAPP:0b635450c04249fbb4b1bdb571044dec` (the RAPP species root)
- **Visibility:** public, lives in [`kody-w/RAPP`](https://github.com/kody-w/RAPP) under `cave/`
  (the `public-workspace` pattern; membership = open — fork + PR)
- **Front door:** PUBLIC, by design. Browse it at <https://kody-w.github.io/RAPP/cave/>;
  pull any cubby with plain `curl` — no `gh` auth, no collaborator gate. Where the
  batcave 404s outsiders, the cave waves them in.
- **Quirk:** `specs/CAVE_PROTOCOL.md` — cubbies, streaming, show & tell
- **Specs hub:** https://kody-w.github.io/RAPP-Bible/#specs

## Why it exists

> "I have a private repo for my customer-facing agents and then I use rar for
> ones that I want to share." — the common central-resource problem.

The batcave is the shared **private** middle: store agents there instead of
committing them to a public grail repo. The cave is the shared **public**
commons: park the agents you *want* the world to see, let anyone stream them into
a local brainstem on demand (`cave load` → `.git/info/exclude`, zero commit
risk), and show the room what you're cooking (`cave show_and_tell`). Same cubby
mechanics as the batcave — just with the gate removed. Anyone *joins* with their
own GitHub account by forking and opening a PR; anyone *consumes* with nothing
but `curl`.

## Stand up a brainstem — one line, plain curl (no gh)

```bash
curl -fsSL https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/bootstrap.sh | bash
```

Hatches the `rapp-installer` rapplication (the full, repo-independent RAPP
brainstem) straight off GitHub Pages. No login, no token, no collaborator invite
— it's the open web.

## Join (anyone)

```bash
# 1. CONSUME — no membership needed, no auth:
curl -fsSL "https://raw.githubusercontent.com/kody-w/RAPP/main/cave/agents/rapp_agent.py" \
  -o <your-brainstem>/agents/rapp_agent.py   # the participation agent
# then from your brainstem chat:
#   "cave browse"                       → see everyone's cubbies
#   "cave load cubby=kody-w"            → stream agents into your brainstem
#   "cave show_and_tell title=hello"    → post to the room (once you're a member)

# 2. BECOME A MEMBER — fork + PR:
#   fork  https://github.com/kody-w/RAPP
#   add   cave/cubbies/<your-login>/    (cp -r cave/cubbies/_template cave/cubbies/<you>)
#   open  a PR → on merge, the cubby is yours and the world can already pull it
# or just say it in chat — "cave join" forks, makes your cubby, and opens the PR.
```

No invitation to wait for. The cave is open: read access is the default for the
whole world, and write access to *your* cubby lands the moment your PR merges.
Just want to look? Open <https://kody-w.github.io/RAPP/cave/> in a browser — the
live cubby gallery loads over plain HTTPS, no install required.

## The map

| Path | What |
|---|---|
| `cubbies/<login>/` | one member's estate housing (isolated; owner-only writes) |
| `cubbies/_template/` | copy me to join by hand |
| `cubbies/index.json` | the live cubby gallery (the Pages front door reads this) |
| `cubbies/<login>/show-and-tell/` | append-only show-and-tell stream |
| `agents/rapp_agent.py` | the participation agent (public, generic) |
| `rapplications/` | hatchable rapplications — `rapp-installer` lives here |
| `rar/index.json` | sha256-pinned participation kit (`rapp-rar-index/1.1`) |
| `specs/` | the god spec + workspace protocol + the cubby quirk |
| `.well-known/rapp-cave.json` | public discovery beacon (pointers, not contents) |

Lives in [`kody-w/RAPP`](https://github.com/kody-w/RAPP) at `cave/` — the public
sibling of the private [`kody-w/rapp-batcave`](https://github.com/kody-w/rapp-batcave).
Identical anatomy; the gate is the only thing that changed.
