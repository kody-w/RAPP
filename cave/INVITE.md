# 🦇 Joining the RAPP Cave — the public way

> **No cave bootstrap or installer download is current.** For
> canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
> evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../RAPP1_STATUS.md). The prepared installer subtree is
> inert history and is not an acceptance path.

<!-- RAPP1-HISTORICAL-SECTION-START -->

No invitation, no token, no waiting. The cave is **public** — you can pull
everything in it with plain `curl`, and you become a member by forking
[`kody-w/RAPP`](https://github.com/kody-w/RAPP) and opening a PR. (Its private
sibling, the Batcave, hands you one secret file person-to-person; the cave hands
you nothing — it's already open.)

## What you need
1. A separately obtained, explicitly evaluated host. This document does not
   provide an installer; the former cave and classic one-liners are retired.
2. A participation adapter accepted through current trust policy. The former
   moving-branch `rapp_agent.py` download is removed; a public URL or hash in an
   unsigned cave catalog is not sufficient acceptance.

   *(GitHub CLI signed in as you — `gh auth login` — is only needed to **push** a
   PR, not to browse historical public content. Public read access is not
   protocol trust.)*

## Join (natural language — the agent guides you)
Open your brainstem chat and say:

> **"Use the rapp agent to join the cave at kody-w/RAPP and set up my cubby."**

What happens:
- The agent **forks** `kody-w/RAPP` under *your* GitHub account (or reuses your
  existing fork).
- It creates `cave/cubbies/<your-login>/` (your isolated full-estate housing),
  adds your row to `cubbies/index.json`, commits on a personal branch, and
  **opens a PR**.
- On merge, you're in — and the world can already `curl` your cubby. No gate to
  clear, no collaborator invite to accept, no operator to ask.

Just want to *browse*? Skip all of it:

> **"Use the rapp agent to browse the cave at kody-w/RAPP — who's here and what are they cooking?"**

## Retired command vocabulary
The following phrases are historical UX notes. No current cave agent, loader,
stashing, egg, or hatch action is offered.

| Former phrase | Historical intent |
|---|---|
| "browse the cave — who's here and what are they cooking?" | inspected static historical files |
| "search the super-rar for X" | searched an unauthenticated generated index |
| "load <member>'s agents into my brainstem" | retired direct loading |
| "stash this file in my cubby" / "show and tell" | retired write workflow |
| "egg my cubby" / "hatch this egg into my cubby" | retired legacy cartridge round trip |

## Inviting the next person
The public link exposes static historical/application content only. It is not
an invite, catalog, pull, install, or acceptance endpoint:

> https://kody-w.github.io/RAPP/cave/

Repository contributions use ordinary fork-and-PR review. No agent-driven join
or cubby-creation action is currently offered.

---
### Browse without installing anything
The cave is a normal GitHub Pages site. Hand anyone the URL —
<https://kody-w.github.io/RAPP/cave/> — and they get the live cubby gallery in a
browser as historical/application content over plain HTTPS. It does not expose
a hatch one-liner or current rapplication download catalog. No QR, payphone, or
raw moving-branch URL establishes RAPP/1 acceptance.

<!-- RAPP1-HISTORICAL-SECTION-END -->
