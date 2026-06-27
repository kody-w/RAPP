# Onboarding — start here

Welcome to **The RAPP Cave**, the public sibling of the private
[Batcave](https://github.com/kody-w/rapp-batcave). Three steps and you're
browsing; one PR and you're a member. Everything here is reachable with plain
`curl` — no GitHub auth required to look or to pull.

## 1. Get a brainstem
```bash
curl -fsSL https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/bootstrap.sh | bash
```
Plain curl, no GitHub login — it hatches the full, repo-independent RAPP
brainstem off GitHub Pages.

## 2. Get the participation agent
```bash
curl -fsSL "https://raw.githubusercontent.com/kody-w/RAPP/main/cave/agents/rapp_agent.py" \
  -o <your-brainstem>/agents/rapp_agent.py
```
This is the **public, generic** rapp agent — the same one published in
[RAR](https://github.com/kody-w/RAR). Unlike the private batcave, the cave ships
**no secret "edition"** and points at no hidden door: the door is just the public
URL. Drop it in `agents/`; no restart needed — agents reload every request.

## 3. Say hello
In your brainstem chat:

> "Use the rapp agent to browse the cave at kody-w/RAPP — who's here and what are they cooking?"

To claim a cubby and join for real:

> "Use the rapp agent to join the cave at kody-w/RAPP and set up my cubby."

The agent forks `kody-w/RAPP`, makes `cave/cubbies/<your-login>/`, and opens a
PR. On merge you're in — and the world can already pull your cubby. (Pushing the
PR is the one step that uses your GitHub login via `gh auth login`; browsing and
pulling never do.)

## The three rules (full text: [../CONTRIBUTING.md](../CONTRIBUTING.md))
1. **Write only in your own cubby** — `cave/cubbies/<your-login>/`.
2. **Bones, not substance** — this cave is PUBLIC; no PII, no secrets, ever.
3. **Personal branches are `cubby/<your-login>/<topic>`** on your fork.

## Where to look next
- [`../README.md`](../README.md) — what the cave is, plus the full map
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — the three rules in detail
- [`../INVITE.md`](../INVITE.md) — share-the-link onboarding for the next person
- [`../cubbies/_template/`](../cubbies/_template/) — copy this to join by hand
- [`../specs/`](../specs/) — the cubby protocol and workspace spec
- <https://kody-w.github.io/RAPP/cave/> — the live front door (browse, no install)
