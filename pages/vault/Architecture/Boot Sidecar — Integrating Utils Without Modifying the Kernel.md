---
title: Boot Sidecar — Integrating Utils Without Modifying the Kernel
status: published
section: Architecture
hook: The kernel is sacred DNA. Body_functions, /web mount, and future utils/ integrations attach to its Flask app via boot.py — a kernel-sibling launcher that runs the kernel verbatim and monkey-patches Flask.run to inject additions just before serving.
---

# Boot Sidecar — Integrating Utils Without Modifying the Kernel

> **Hook.** The kernel is sacred DNA. Body_functions, /web mount, and future utils/ integrations attach to its Flask app via boot.py — a kernel-sibling launcher that runs the kernel verbatim and monkey-patches Flask.run to inject additions just before serving.

## The constraint

Per **Constitution Article XXXIII §4**, AI assistants — and contributors generally — must not edit `brainstem.py`. The kernel is universal DNA, drop-in replaceable across all installs. Yet the kernel as canonically shipped does very little: it serves `/chat`, `/agents`, `/health`, `/version`, voice slot splitting, and Copilot auth. It does **not** dispatch body_functions (`/api/<name>/<path>` routes), does **not** mount static `/web/<path>` assets, and does **not** know about senses, twin frames, index_card, or any other module under `utils/`.

The question this note answers: **how does the rest of the platform get wired in without ever touching brainstem.py?**

## The pattern: a kernel-sibling launcher

`rapp_brainstem/boot.py` is a sibling of the kernel — DNA-adjacent, not part of the mutation surface. It does three things:

1. **Monkey-patches `flask.Flask.run`** before the kernel runs. The patched version installs body_function routes (and any other late-bound integrations) on the Flask app, then hands control to the original `run`.
2. **Executes the canonical kernel verbatim** via `runpy.run_path("brainstem.py", run_name="__main__")`. The kernel's `if __name__ == "__main__":` block runs unchanged — banner, soul load, agent load, the works.
3. **Discovers and registers** body_functions via `body_functions_loader.install(app)` at the moment Flask is about to serve. Same for `/web/<path>` static handling.

```python
# rapp_brainstem/boot.py (essence)
import flask, runpy
_real_run = flask.Flask.run
def _wrapped_run(self, *args, **kwargs):
    body_functions_loader.install(self)   # /api/<name>/...
    _mount_web_static(self)               # /web/<path>
    return _real_run(self, *args, **kwargs)
flask.Flask.run = _wrapped_run
runpy.run_path("brainstem.py", run_name="__main__")
```

That's the whole mechanism. The kernel never imports boot.py. The kernel never knows boot.py exists.

## What this earns us

| Capability | Where it lives | How the kernel knows |
|---|---|---|
| `/chat`, `/agents`, `/health`, `/version` | `brainstem.py` | Kernel ships these. |
| Voice slot splitting (`|||VOICE|||`) | `brainstem.py` | Kernel ships this. |
| Body_function dispatch (`/api/<name>/<path>`) | `body_functions_loader.py` + `utils/body_functions/*_body_function.py` | Doesn't. Boot sidecar attaches. |
| Static `/web/<path>` mount | `boot.py` + `utils/web/*` | Doesn't. Boot sidecar attaches. |
| Senses, twin probes, index_card, frames | `utils/{twin,frames,index_card}.py` + agents that consume them | Future — boot sidecar can attach more. |

The kernel stays exactly as small as Article XXXII demands ("kernel is what /chat requires"). The body grows around it.

## What `python brainstem.py` still does

The canonical kernel can be launched directly without boot.py:

```bash
python brainstem.py        # bare DNA — chat, agents, voice, no body_functions
python boot.py              # full organism — DNA + body_functions + /web
```

This is **load-bearing**. The drop-in fixture (Fixture 01, Article XXXIII §3) tests that the canonical kernel boots from a fresh checkout with nothing else. Body_functions and /web are additive — present when the launcher arranges for them, absent when the kernel runs alone. Either path is valid; they're the bare and full forms of the same organism.

`start.sh` and `start.ps1` invoke `boot.py` (with a fallback to `brainstem.py` for older organism layouts), so users who run via the launcher always get the full organism. Power users who launch the kernel directly are deliberately opting into the bare form.

## Why a launcher and not a phantom agent

An earlier draft of this design considered putting the integration code in a `*_agent.py` file under `agents/` — leveraging the kernel's existing agent-discovery mechanism. The agent's import side effects would register body_function routes on the kernel's app.

Rejected because:

- **`agents/` is the user's workspace** (Article XVII). Engine plumbing doesn't belong there.
- A phantom agent has to walk `sys.modules` to find the kernel's Flask app, which is fragile.
- The phantom agent runs once during `load_agents()`, but the discovery / registration ordering is implicit. The boot sidecar is explicit: "right before `app.run`, install the additions."

The launcher pattern keeps engine plumbing out of the user's workspace and makes the integration timing explicit.

## Why a monkey-patch and not a wrapper script

An earlier draft of this design considered replicating the kernel's `if __name__ == "__main__":` block in boot.py — calling `brainstem.load_soul()`, `brainstem.load_agents()`, etc. by hand, then calling `brainstem.app.run(...)`.

Rejected because:

- The kernel's startup is detailed (telemetry hooks, banner, pending-login resume). Replicating it in boot.py creates **drift risk**: when the kernel adds a new startup step, boot.py becomes silently stale.
- `runpy.run_path(kernel, run_name="__main__")` runs the kernel's startup verbatim, every line, every time. If the kernel adds a step, boot.py picks it up automatically because boot.py doesn't replicate — it delegates.

The monkey-patch is the smallest possible interception: one Flask method, exactly one extra step, no other duplication.

## Future integrations

The boot sidecar is the natural attachment point for everything else under `utils/` that needs to wire into the kernel's HTTP surface or request lifecycle:

- **Index card** — a body_function that exposes `/api/card/<turn_id>` polling the per-turn artifact.
- **Twin / frames** — a `before_request` / `after_request` hook in boot.py that records frames; or a body_function for the dreamcatcher reconciliation API.
- **Senses** — sense modules contribute to the system prompt every chat turn. The kernel doesn't compose senses today; if it gains a `before_chat` hook in some future canonical update, boot.py will wire senses through it.
- **Egg packing** — a body_function `/api/egg/pack` that produces a `.egg` of the running organism.

Each of these adds zero kernel lines.

## See also

- Constitution Article XXXII (Kernel is what chat requires) — the litmus test that says the kernel doesn't do this.
- Constitution Article XXXIII §4 (AI assistants do not edit DNA) — the rule that produced this pattern.
- [[Local Storage Shim via sys.modules]] — a different additive integration: agents transparently get the local backend without knowing.
- [[Fixture 01 — Canonical Kernel local_storage Drop-In]] — the architectural promise this pattern serves: drop-in compatibility.
