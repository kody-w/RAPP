# Onboarding — start here

> **Historical application onboarding only.** For canonicalization, identity,
> frames, wire, eggs, registry, trust, and protocol evolution, follow RAPP/1
> rev-5 through [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). The cave installer and direct
> agent-download instructions are retired.

<!-- RAPP1-HISTORICAL-SECTION-START -->

Welcome to **The RAPP Cave**, the public sibling of the private
[Batcave](https://github.com/kody-w/rapp-batcave). Three steps and you're
browsing; one PR and you're a member. Everything here is reachable with plain
`curl` — no GitHub auth required to look or to pull.

## 1. Get a brainstem
The cave no longer supplies a bootstrap. Its prepared installer subtree is
inert history, not a live install or RAPP/1 acceptance path.

## 2. Get the participation agent
The former moving-branch direct download is removed. Any replacement must be a
verified RAPP/1 artifact accepted through the estate owner's §13 state; public
reachability alone is not trust.

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
- <https://kody-w.github.io/RAPP/cave/> — historical/application front door;
  not an install or acceptance surface

<!-- RAPP1-HISTORICAL-SECTION-END -->
