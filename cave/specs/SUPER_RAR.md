# The Cave super-RAR — the public super-store

The RAPP Cave has the **same super-RAR capability as the private batcave**, just
public (plain git/HTTPS, no auth, no collaborator gate).

- **RAR** (`rar/index.json`) — the agent + rapplication registry, every entry
  sha256-pinned. `cave load` verifies a streamed file against its pin and
  **refuses drift** (a tampered cubby file never lands in your brainstem).
- **super-RAR** (`super-rar/index.json`) — the *super-store*: **every kind across
  every cubby** (agents · organs · senses · rapplications · neighborhoods · eggs),
  one registry over the whole open neighborhood. Find what a neighbor already
  built and stream it in.

## The capability (three parts)

| Part | File | What it does |
|---|---|---|
| **Builder** | `tools/build_super_rar.py` | (Re)builds both indexes from the cubbies on disk. The standalone, pure-stdlib equivalent of the batcave god agent's `super_rar rebuild`. `--check` mode is the CI gate. |
| **Agent** | `agents/cave_agent.py` (`@kody-w/cave`) | Drop into any brainstem → a `Cave` tool: `list` cubbies · `super_rar` (search the super-store) · `load cubby=<login>` (stream that cubby's agents into your brainstem, **git-invisible** via `.git/info/exclude`, sha-verified — zero commit risk) · `sync`. |
| **Steward** | `agents/rar_steward_agent.py` (`@rapp/rar_steward`) | Registry hygiene — dedup/assess agents in the RAR. |

## Get the capability into your brainstem (public, no auth)

```bash
# drop the Cave agent (and the steward) into your brainstem, then just ask it
curl -fsSL https://kody-w.github.io/RAPP/cave/agents/cave_agent.py    -o ~/.brainstem/src/rapp_brainstem/agents/cave_agent.py
curl -fsSL https://kody-w.github.io/RAPP/cave/agents/rar_steward_agent.py -o ~/.brainstem/src/rapp_brainstem/agents/rar_steward_agent.py
```
Then in chat: *"list the cave cubbies"*, *"search the cave super-rar for X"*,
*"load kody-w's agents from the cave"*.

## Freshness

The super-RAR is **living**, not hand-maintained: `tools/build_super_rar.py`
regenerates it from the cubbies, and `.github/workflows/cave-super-rar.yml`
**gates every PR** — if you change a cubby and don't rebuild, CI fails. Rebuild
locally with:

```bash
python3 cave/tools/build_super_rar.py
```

## Difference from the batcave

Identical mechanism (build + sha-pin + stream + `.git/info/exclude` zero-commit-risk).
The only delta is **trust/access**: the batcave streams from a private,
collaborator-gated clone; the cave streams from the **public** `kody-w/RAPP`
clone — anyone, no auth.
