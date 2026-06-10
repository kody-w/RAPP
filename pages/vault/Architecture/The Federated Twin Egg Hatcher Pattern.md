---
title: The Federated Twin Egg Hatcher Pattern
status: published
section: Architecture
hook: One single-file hatcher hatches any RAPP twin into ~/.rapp/twins/<hash>/ from cwd auto-detect, a public/private GitHub repo, or a local .egg file. The global brainstem's built-in Twin agent then federates list, boot, and chat across every twin under that folder — no kernel patches, no second installer, no per-twin code duplication.
---

# The Federated Twin Egg Hatcher Pattern

> **Hook.** One single-file hatcher (`twin_egg_hatcher_agent.py`) hatches any RAPP twin into `~/.rapp/twins/<hash>/` from cwd auto-detect, a public/private GitHub repo, or a local `.egg` zip. The global brainstem's built-in `Twin` agent then federates `list`, `boot`, and `chat` across every twin under that folder — no kernel patches, no second installer, no per-twin code duplication.

[[The Distro Hatcher Agent Pattern]] describes how to *extend the kernel* with a distro via an in-process hatcher.  This doc describes the sibling pattern that *adds twins to the federation* without touching the kernel at all.  The distro hatcher writes into a target brainstem folder; the twin hatcher writes into `~/.rapp/twins/`, where the kernel's built-in [[The Twin Agent|Twin]] tool already knows to look.

## The shape

Three properties make a twin egg distribution work:

1. **One generic hatcher, every twin uses it.** The hatcher carries no twin-specific identity. It loads identity from one of three sources at runtime:
   - **cwd auto-detect** — inside a cloned twin repo with `rappid.json` + `soul.md`
   - **`--source REPO`** — public/private GitHub twin repo (raw fetch + Contents API for `agents/`); set `GH_TOKEN` for private
   - **`--egg PATH`** — fully-exported `.egg` zip (brainstem-egg/2.1 layout: files under `repo/`)
2. **Twin repos hold *only* identity.** No hatcher in-repo.  Each twin repo is just:
   - `rappid.json` — schema `rapp-rappid/2.0` or legacy bare-UUID, with `name`, `kind`, `parent_rappid`, lineage back to [[The Species DNA Archive — rapp_kernel|kody-w/RAPP]]
   - `soul.md` — read by the brainstem every turn so the twin stays in voice
   - `agents/*.py` — optional, twin-specific tools
3. **No kernel patches.** The hatched workspace at `~/.rapp/twins/<hash>/` is read by the global brainstem's `start.sh` via `SOUL_PATH` / `AGENTS_PATH` / `PORT` env vars. The kernel sees a child brainstem; the user sees a twin. The kernel itself never changes.

The hash extraction handles every shape: the `<hash>` segment from an Eternity rappid (`rappid:@OWNER/SLUG:HASH`), the same from a legacy v2 rappid (`rappid:v2:KIND:@OWNER/SLUG:HASH@...`, canonicalized on read), and bare UUIDs from legacy v1.x front doors. Same workspace dir convention either way.

## Why one hatcher, many twins

The earlier approach was to bundle a hardcoded `hatch_<twin>_agent.py` in every twin repo. That works for one or two twins but multiplies failure surface:

- Every twin repo carries a copy of the same Python file. When the hatcher logic changes (better error messages, new loaders, a security fix), every repo has to be updated.
- The class names + tool names collide if you drop more than one of those files into the same brainstem's `agents/` folder.
- The egg payload (organ stubs, sense markers, hello agents) gets re-stated in every hatcher's `EGG_PAYLOAD` dict — same drift problem.

The federated pattern flips it: **one hatcher repo**, many **identity-only twin repos**.  Updates to the hatcher don't touch any twin.  Updates to a twin's persona don't touch the hatcher.  Each repo has one clear job.

## The repo set

| Repo | Role | Visibility |
|---|---|---|
| [`kody-w/twin-egg-hatcher`](https://github.com/kody-w/twin-egg-hatcher) | Public mirror of the generic hatcher — curl-friendly, no auth | PUBLIC |
| [`kody-w/aibast-twin`](https://github.com/kody-w/aibast-twin) | Canonical home of the hatcher *and* the AIBAST team twin identity | PRIVATE |
| [`kody-w/heimdall`](https://github.com/kody-w/heimdall) | Heimdall — the gatekeeper / front-door twin | PUBLIC |
| [`kody-w/kody-w-twin`](https://github.com/kody-w/kody-w-twin) | @kody-w operator twin (also Article-XLVI front door) | PUBLIC |
| [`kody-w/bots-in-blazers-twin`](https://github.com/kody-w/bots-in-blazers-twin) | Bots in Blazers — Mfg CoE project twin (Bill Whalen's team) | PRIVATE |

The same hatcher file is published as `agents/@kody/twin_egg_hatcher_agent.py` in the [[Federation via RAR|RAR]] registry:

- **RAR submission:** [`kody-w/RAR PR #98`](https://github.com/kody-w/RAR/pull/98)
- **Manifest:** `@kody/twin_egg_hatcher v1.0.0`, category `core`, tags `twin, egg, hatcher, organism, federation, single-file, rapp`
- **Raw agent file:** [twin_egg_hatcher_agent.py](https://raw.githubusercontent.com/kody-w/twin-egg-hatcher/main/twin_egg_hatcher_agent.py)

Once merged into RAR's `registry.json`, any brainstem can install it via `RARRemote(action="install", agent="@kody/twin_egg_hatcher")`.

## Bring it up locally with just a brainstem

You need a brainstem and nothing else.

```bash
# 1. Install the kernel if you haven't.
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash

# 2. Drop the generic hatcher into the brainstem's agents folder.
curl -fsSL https://raw.githubusercontent.com/kody-w/twin-egg-hatcher/main/install.sh | bash
cp ./twin_egg_hatcher_agent.py ~/.brainstem/src/rapp_brainstem/agents/

# 3. Pull the kernel's built-in Twin federation agent (CommunityRAPP source).
#    This file makes the brainstem aware of every workspace under ~/.rapp/twins/.
cp /path/to/twin_agent.py ~/.brainstem/src/rapp_brainstem/agents/

# 4. Hatch any twin you want — by repo (public), by repo (private + token), or by .egg.
python ~/.brainstem/src/rapp_brainstem/agents/twin_egg_hatcher_agent.py hatch --source kody-w/heimdall
python ~/.brainstem/src/rapp_brainstem/agents/twin_egg_hatcher_agent.py hatch --source kody-w/kody-w-twin
GH_TOKEN=ghp_… python ~/.brainstem/src/rapp_brainstem/agents/twin_egg_hatcher_agent.py hatch --source kody-w/aibast-twin
GH_TOKEN=ghp_… python ~/.brainstem/src/rapp_brainstem/agents/twin_egg_hatcher_agent.py hatch --source kody-w/bots-in-blazers-twin

# 5. Boot each twin as a child brainstem on its own port (the Twin agent will do
#    this automatically too, but you can do it manually):
SOUL_PATH=~/.rapp/twins/<hash>/soul.md \
AGENTS_PATH=~/.rapp/twins/<hash>/agents \
PORT=7081 \
bash ~/.brainstem/src/rapp_brainstem/start.sh
```

The brainstem's next `/chat` call picks up the dropped agents — no restart required (`load_agents()` runs per request).

## Federate through the global brainstem in plain English

Now you talk to *one* endpoint and the brainstem routes:

```
> Twin(action="list")
> Twin(action="boot",  rappid_uuid="<rappid>")
> Twin(action="chat",  rappid_uuid="<rappid>", message="hello")
```

The LLM handles the dispatch when you ask in natural language:

> *Ask Heimdall who he is.*
> *Have @kody-w and Bots in Blazers debate whether to ship to Copilot Studio or MCP App first.*
> *Hatch the Northwind Pharmacy sub-twin from this egg I have on disk.*

The global brainstem is the only port your user sees.  Every child twin runs on its own port (7081, 7082, …) under its own `soul.md`, but federation makes them look like one chat partner.

## The four-twin worked example

The first federation deployment runs four twins simultaneously on one machine:

| Port | Twin | Voice | rappid kind |
|---|---|---|---|
| 7081 | 🌈 Heimdall | *"I am Heimdall, watcher of the Bifrost…"* | `personal` (bare UUID) |
| 7082 | 🧬 @kody-w | *"Patching is lazy. Reissue, don't patch."* | `operator` (v2) |
| 7083 | 🏭 Bots in Blazers | *"Hi, I'm Bots in Blazers — the Mfg CoE twin…"* | `project` (v2) |
| 7084 | ⚡ AIBAST | *"AI Base team — transcript in, prototype out."* | `project` (v2) |

All four were hatched from the same single-file `twin_egg_hatcher_agent.py`, each from a different source (public repo, private repo, or `.egg`).  The global brainstem at `localhost:7071` federates all four through one `Twin` tool.  Federation primitives verified: simultaneous identity reveal, cross-twin handoff, two-twin debates, twin-teaches-twin, four-voice co-authored essay.

## Constraints worth knowing

- **v2 rappids contain `/` characters.** The Twin agent's filesystem-key transform was originally just `replace(":", "_").replace("@", "")`, which left `/` intact and shredded into subdirectories.  Patch: extract the 32-hex `HASH` portion for any rappid that starts with `rappid:`; fall back to `replace("/", "_")` only as a defensive escape.  Upstream the fix in `twin_agent.py`'s `_pid_file` / `_port_file` / `ws_name` resolution.
- **`load_agents()` reload cadence.** The brainstem re-scans `AGENTS_PATH/*_agent.py` on every `/chat` request, so a dropped file is live on the next call — no restart needed.  But the agent's `__init__()` is re-run each time too; keep it fast and side-effect-free.
- **Soul granularity.** Personality lives in `soul.md`, not the runtime.  Change one word in a soul and the twin behaves differently.  Useful for sandbox copies (e.g. `kody-w-evil-twin` with `reissue` → `patch`); dangerous for drift.

## Related

- [[The Distro Hatcher Agent Pattern]] — sibling pattern for kernel extensions vs twin spawning
- [[Federation via RAR]] — how the hatcher itself is distributed
- [[Distros as a Pattern]] — what a distro is and why this isn't one
- [[Rappid]] — v2 schema details + Article XLVI lineage
- [[The Twin Agent]] — the federation primitive in the kernel
- [[Mirror Spec]] — why the kernel stays untouched in the default `mode=twin`
