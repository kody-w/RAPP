# 🦇 Joining the RAPP Cave — the public way

No invitation, no token, no waiting. The cave is **public** — you can pull
everything in it with plain `curl`, and you become a member by forking
[`kody-w/RAPP`](https://github.com/kody-w/RAPP) and opening a PR. (Its private
sibling, the Batcave, hands you one secret file person-to-person; the cave hands
you nothing — it's already open.)

## What you need
1. A running brainstem — install with the one-liner if you don't have one:
   ```bash
   curl -fsSL https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/bootstrap.sh | bash
   ```
   (or the classic installer: `curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash`)
2. The one agent — the **public, generic** participation agent. There is no
   private "edition" and no hidden door; the door is just the public URL:
   ```bash
   curl -fsSL "https://raw.githubusercontent.com/kody-w/RAPP/main/cave/agents/rapp_agent.py" \
     -o <your-brainstem>/agents/rapp_agent.py
   ```
   Drop it in your brainstem's `agents/` dir as `rapp_agent.py`. No restart
   needed — agents reload every request.

   *(GitHub CLI signed in as you — `gh auth login` — is only needed to **push** a
   PR, not to browse or pull. Consuming the cave needs no auth at all.)*

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

## Once you're in — five moves
| Say | What it does |
|---|---|
| "browse the cave — who's here and what are they cooking?" | lists every cubby |
| "search the super-rar for X" | content-aware search across EVERYTHING in all cubbies |
| "load <member>'s agents into my brainstem" | streams them in **git-invisibly** (never committable to your grail) |
| "stash this file in my cubby" / "show and tell" | share your work (secrets auto-refused) |
| "egg my cubby" / "hatch this egg into my cubby" | round-trip organisms local ↔ cave |

## Inviting the next person
There's nothing to hand over — **just share the link.** Anyone can browse and
pull, no auth:

> https://kody-w.github.io/RAPP/cave/

To contribute, they fork `kody-w/RAPP` and open a PR (the rapp agent does it for
them: *"join the cave at kody-w/RAPP and set up my cubby"*). The door is the
public URL; there is no secret to leak, because the cave keeps none.

---
### Browse without installing anything
The cave is a normal GitHub Pages site. Hand anyone the URL —
<https://kody-w.github.io/RAPP/cave/> — and they get the live cubby gallery in a
browser, the hatch one-liner, and every rapplication, over plain HTTPS. For
scripts, the public raw base is
`https://raw.githubusercontent.com/kody-w/RAPP/main/cave`. No QR, no payphone, no
dial tone — the address *is* the access, because the cave is open.
