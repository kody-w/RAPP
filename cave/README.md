# 🦇 The RAPP Cave

> **Preserve the Cave; separate observation from acceptance.** For
> canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
> evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../RAPP1_STATUS.md). The catalogs retain historical
> entries and context as read-only observations, with verification, acceptance,
> and distribution state recorded separately. `rar_steward_agent.py` restores
> catalog analysis and issue drafting; `build_super_rar.py` restores discovery,
> hashing, rendering, and drift checks. Their defaults are analyze/check/plan
> only: no issue creation, write-back, install, stream, publication, or
> moving-branch acceptance.
>
> The prepared `cave/rapplications/rapp-installer/` bytes remain untouched and
> non-installing. The only current immutable grail reference is
> [`KERNEL_PIN.json`](../KERNEL_PIN.json), naming
> `kody-w/rapp-installer@brainstem-v0.6.9`.

<!-- RAPP1-HISTORICAL-SECTION-START -->

A **public RAPP neighborhood workspace** — the open sibling of the private
[Batcave](https://github.com/kody-w/rapp-batcave). Every member gets a **cubby**
— isolated housing for their entire rapp estate (agents, organs, senses,
rapplications, whole neighborhoods, eggs) — the same environment as their
on-device brainstem, smashed into a directory the whole world can browse, pull,
and learn from.

- **Identity:** `rappid:@kody-w/rapp-cave:ca72ca0a3cb90c357fb09e38b02f85f09935cacbf61e94740c57f1eb30a73e0a` (kind `workspace`, Eternity format, Art. XXXIV.1)
- **Parent:** `rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9` (the RAPP species root)
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

## Retired cave installer archive

The prepared `rapp-installer` subtree is preserved byte-for-byte as historical
evidence. Its bootstrap files and package listings must not be run, linked as a
download, or advertised as a catalog. There is no conformant cave bootstrap.

## Join (anyone)

```bash
# Historical membership workflow — application governance, not RAPP acceptance:
#   fork  https://github.com/kody-w/RAPP
#   add   cave/cubbies/<your-login>/    (cp -r cave/cubbies/_template cave/cubbies/<you>)
#   open  a PR → on merge, the cubby is yours and the world can already pull it
```

The historical direct participation-agent download and “stream into your
brainstem” commands remain design context only. Current safe adapters do not
execute them; any future distribution adapter must pass current RAPP/1 artifact
and registry verification.

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
| `rapplications/` | inert historical artifacts; no current hatchable catalog |
| `rar/index.json` | sha256-pinned participation kit (`rapp-rar-index/1.1`) |
| `specs/` | the god spec + workspace protocol + the cubby quirk |
| `.well-known/rapp-cave.json` | public discovery beacon (pointers, not contents) |

Lives in [`kody-w/RAPP`](https://github.com/kody-w/RAPP) at `cave/` — the public
sibling of the private [`kody-w/rapp-batcave`](https://github.com/kody-w/rapp-batcave).
Identical anatomy; the gate is the only thing that changed.

<!-- RAPP1-HISTORICAL-SECTION-END -->
