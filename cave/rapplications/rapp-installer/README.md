# RAPP Installer — the brainstem, ported out of the grail

**Public home:** <https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/>
· public raw base: `https://raw.githubusercontent.com/kody-w/RAPP/main/cave/rapplications/rapp-installer`

**Public one-liner (anybody, anywhere — no GitHub auth):**

```bash
curl -fsSL https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/bootstrap.sh | bash
```

This is the **whole RAPP brainstem** (the engine behind the `rapp-installer`
one-liner) carved **out** of its git repo (`kody-w/rapp-installer`, a.k.a. *the
grail*) and packaged as a **self-contained, egged rapplication**. You get every
capability the rapp installer has — run the server, build agents, the web UI,
GitHub-Copilot auth, memory, model switching, the Tier-2 Azure deploy, the
Tier-3 M365 solution — but **nothing here is tied to the grail repo**, so you
can hack on it in VS Code and there is *no way to accidentally commit to the
sacred grail.*

> The cubby it lives in (`~/.brainstem/cubbies/rapp-installer/`) is **not a git
> repo**. The Source Control panel stays empty. That is the whole point.

## Why this exists

Working directly in `~/.brainstem/src/rapp_brainstem` means every stray file —
a `.pptx`, a scratch agent, a zip — shows up in the **grail's** Source Control,
one slip from being committed to production `main`. This rapplication is the
escape hatch: the same engine, in a place where commits to the grail are
impossible.

## What's inside

```
rapplications/rapp-installer/
  serve.py            launcher → boots the BUNDLED kernel (never the grail)
  hatch.py            pure-stdlib self-bootstrapper (egg → running brainstem)
  bootstrap.sh/.ps1   the one-liner (plain-curl pull from the PUBLIC RAPP Cave)
  manifest.json       rapp-rapplication/1.0
  rappid.json         this organism's identity
  soul.md             system prompt
  web/index.html      the brainstem web UI
  agents/             default agents (drop your own here — never touches grail)
  kernel/             a COMPLETE standalone brainstem, byte-identical to grail
    brainstem.py  local_storage.py  index.html  requirements.txt  VERSION
    agents/basic_agent.py
  installer/          the installer payload across tiers (see installer/README.md)
    start.sh/.ps1                               (Tier 1 — run the brainstem)
    azuredeploy.json  deploy.sh/.ps1            (Tier 2 — Azure)
    MSFTAIBASMultiAgentCopilot_*.zip            (Tier 3 — M365 / Copilot Studio)
    community_rapp/  skill.md                   (Hippocampus path + onboarding)
```

> The Tier-1 **standup** here is `bootstrap.sh` / `serve.py` — repo-independent,
> no grail. The grail-cloning public `install.sh` is intentionally **omitted**
> (it would re-create `~/.brainstem/src`, the very thing this rapplication
> exists to avoid). See `installer/README.md`.

`kernel/brainstem.py` is verified byte-identical to the grail's — full parity,
no fork.

## Run it

```bash
# from this directory (after hatch.py built the venv, or just use python3):
python3 serve.py                 # → http://localhost:7077   (coexists with a :7071 grail)
PORT=7071 python3 serve.py       # pick your own port

# or run the bare kernel directly (true parity — it's a complete brainstem).
# the bare kernel defaults to PORT 7071, so set 7077 to coexist with a grail:
PORT=7077 AGENTS_PATH="$PWD/agents" SOUL_PATH="$PWD/soul.md" python3 kernel/brainstem.py
```

Health check: `curl -s localhost:7077/health | python3 -m json.tool`

## Get it on a fresh machine (from the public cave)

The RAPP Cave is a **public front door** — no GitHub auth, no collaborator gate.
Anyone can pull with plain curl:

```bash
curl -fsSL https://kody-w.github.io/RAPP/cave/rapplications/rapp-installer/bootstrap.sh | bash
```

That pulls `cubby-rapp-installer.egg` (plain HTTPS from the public raw base, with
a Pages mirror fallback), extracts `hatch.py` from it, hatches into
`~/.brainstem/cubbies/rapp-installer/`, builds the venv, and launches `serve.py`
— all without ever cloning or touching the grail.

> **Note for maintainers:** `cubby-rapp-installer.egg` is **not** committed in
> this public tree — it is **repacked by the integrator** from these source
> files (the `cubby/` tree → a `brainstem-egg/2.3-cubby` zip) and published to
> the public raw base above. The bootstrap one-liner always pulls the freshly
> repacked public egg.

## Join in / contribute

The cave is open. To add or improve a rapplication, **fork** `kody-w/RAPP` and
open a **PR** — or just pull and run. No invite required.

## The guarantee

`serve.py` hard-refuses to boot against `~/.brainstem/src/rapp_brainstem`.
`hatch.py` hard-refuses to hatch into it. Everything — code, agents, runtime
tokens, telemetry — lives inside the cubby. The grail is read-from at build
time only, never written to.
