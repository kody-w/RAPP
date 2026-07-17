---
title: The Distro Hatcher Agent Pattern
status: historical
section: Architecture
hook: A single Python file you drop into ~/.brainstem/agents/ that, on its first tool-call, pulls a full distro down from raw.githubusercontent.com and hatches it into its own folder beside the grail kernel — no shell installer, no kernel modification, no second brainstem to manage.
---

# The Distro Hatcher Agent Pattern

> **HISTORICAL VAULT NOTE — superseded current guidance.** The bounded body
> describes a retired hatcher pattern; it is not current egg or installer
> instruction. For canonicalization, identity, frames, wire, eggs, registry,
> trust, and protocol evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../../RAPP1_STATUS.md).

<!-- RAPP1-HISTORICAL-SECTION-START -->

> **Hook.** A single Python file you drop into `~/.brainstem/agents/` that, on its first tool-call, pulls a full distro down from `raw.githubusercontent.com` and hatches it into its own folder beside the grail kernel — no shell installer, no kernel modification, no second brainstem to manage.

[[Distros as a Pattern]] explains *what* a distro is and the byte-identical-to-grail contract it must respect. This doc describes a specific *delivery vehicle* for distros: a brainstem-loaded agent that does the install in-process.

The [[The Federated Twin Egg Hatcher Pattern|twin-egg-hatcher]] is the sibling. It distributes *twins* into `~/.rapp/twins/<hash>/` instead of distros into a brainstem-source folder. Same single-file mechanics — `__manifest__`, `BasicAgent` subclass, always-confirm gate, stdlib only — but the scope flips: distro hatcher = *extend the kernel*; twin hatcher = *add to the federation without touching the kernel*. If you're authoring something that lays a hatched organism beside the grail kernel, this doc is the right one; if you're shipping a twin identity that plugs into the existing brainstem's federation, see [[The Federated Twin Egg Hatcher Pattern]].

## The shape

A distro hatcher is one `*_agent.py` file with five properties:

1. **`__manifest__` dict at the top** — `rapp-agent/1.0` schema, so the file is also a valid [[Federation via RAR|RAR]] submission (one artifact, two channels: drop-in install + community registry).
2. **A `BasicAgent` subclass with a tool-call surface** — `check`, `status`, `dry-run`, `hatch`. Always-confirm gate before any write. The kernel's agent loader picks it up on the next `/chat` without restart.
3. **Two-phase hatch**:
   - Phase 1 — *kernel copy.* Auto-discover the grail kernel under `source_home` (handles both the flat `~/.brainstem/brainstem.py` layout and the nested `~/.brainstem/src/rapp_brainstem/brainstem.py` layout `rapp-installer` actually produces). Copy its source tree into `target_home`, skipping `__pycache__/`, `venv/`, runtime state, and identity files (`rappid.json`, `keys/`, `peers/`, etc).
   - Phase 2 — *distro lay.* Fetch `MANIFEST.json` from `raw.githubusercontent.com/<distro-repo>/<branch>/MANIFEST.json`, then GET each listed file and write it to its declared destination under `target_home`. **sha256-verify every fetched file** against the manifest entry before writing.
4. **Stdlib only** — `urllib`, `json`, `hashlib`, `os`. No third-party dependencies; the brainstem's venv is enough.
5. **Sacred-path refusal** — any manifest entry whose destination resolves to `brainstem.py`, `VERSION`, or `agents/basic_agent.py` is rejected before write. Encodes the [[Mirror Spec|kernel-untouched contract]] into the data layer, not just the install script.

## Why side-by-side beats overlay

The earlier `install.sh` story for `kody-w/rappter-distro` was overlay: rsync the distro on top of `~/.brainstem/`. That works but has costs:

- The grail kernel install is no longer a clean reference for `git diff` against [[The Species DNA Archive — rapp_kernel|rapp_kernel/latest/]].
- A user who wants the bare kernel back has to reinstall.
- Two distros can't coexist on one machine without conflict.

The hatcher pattern lays the distro into a sibling folder (default `~/.brainstem-rappter/`). The source kernel at `~/.brainstem/` is *read*, never *written*. Both organisms — bare grail and hatched rappter — can run simultaneously on different ports. The drift-check one-liner against `rapp_kernel/latest/` still passes against either install.

## Why a Python agent beats a curl|bash installer

A distro could ship an `install.sh` instead. The hatcher pattern picks Python for three reasons:

- **No second shell ritual.** The user already runs the brainstem. They drop one file in, then ask in chat — same surface as every other RAPP capability.
- **The LLM gates the install.** `confirm=true` is required to write; the LLM previews the dry-run manifest first. The user reads a structured plan instead of an opaque bash trace.
- **The same file is the canonical implementation.** Walks `LAYOUT`, generates `MANIFEST.json` with `--build-manifest`, then *consumes* that manifest at install time. The agent is both the installer and the installer's source of truth.

curl|bash still works for the bootstrap (you need *something* to write the agent file into `~/.brainstem/agents/`). After that one-liner, the agent owns the install.

## Wire shape

The manifest is `rappter-distro-install-manifest/1.0`:

```json
{
  "schema": "rappter-distro-install-manifest/1.0",
  "repo": "kody-w/rappter-distro",
  "branch": "main",
  "files": [
    { "src": "lib/bond.py", "dst": "utils/bond.py", "size": 30188, "sha256": "..." },
    { "src": "lib/boot.py", "dst": "utils/boot.py", "size": 23117, "sha256": "..." },
    ...
  ]
}
```

`src` is the path inside the distro repo (under any branch). `dst` is the path relative to `target_home`. The agent walks files in order, GETs each from `https://raw.githubusercontent.com/<repo>/<branch>/<src>`, hashes the bytes, and only writes if the hash matches the manifest entry.

Failure modes are first-class:
- `fetch-failed` — network error or 404.
- `sha-mismatch` — bytes don't match the recorded hash. Almost always means the manifest is stale; treat as a hard stop.
- `write-failed` — disk error.

Each per-file outcome surfaces in the agent's response so the LLM can summarize.

## Tool-call surface

The agent exposes four actions:

| action | side effect | confirm? |
|---|---|---|
| `check` | none — reports whether a grail kernel is reachable under `source_home` and where the hatch would land | no |
| `status` | none — reports installed-distro state at *both* `source_home` and `target_home` | no |
| `dry-run` | fetches manifest, fetches every file, verifies every hash, but writes nothing | no |
| `hatch` | full two-phase install. Without `confirm=true`, refuses and returns a dry-run preview | **yes** |

`dry-run` is intentionally as expensive as a real install except for the final write. The whole point is that the user (and the LLM) sees the same fetch + verify report they'd get from `hatch`, and only flips `confirm=true` once that report looks right.

## The bootstrap one-liner

You can't tool-call an agent that isn't loaded yet, so the hatcher itself needs a curl entry. The pattern is:

```bash
curl -fsSL https://raw.githubusercontent.com/<owner>/<distro-repo>/main/agents/install_<distro>_agent.py \
  > ~/.brainstem/agents/install_<distro>_agent.py
```

After that single line, the brainstem hot-loads the agent on the next `/chat`. The user asks in plain English ("hatch the <distro> distro"); the LLM tool-calls the agent; the agent does the rest.

## Reference implementation

The canonical hatcher today is **[@kody/install_rappter_distro_agent](https://kody-w.github.io/RAR/grail.html#@kody/install_rappter_distro_agent)**, which hatches [`kody-w/rappter-distro`](https://github.com/kody-w/rappter-distro) into `~/.brainstem-rappter/`. Card forged: *The Catalyst · {2}{B} · 2/4 uncommon · HOLO set*.

Source (single file, ~37 KB, stdlib-only):

```
https://raw.githubusercontent.com/kody-w/rappter-distro/main/agents/install_distro_agent.py
```

It's also the **manifest generator** for its own distro:

```bash
python install_distro_agent.py --build-manifest --src . --out MANIFEST.json
```

That's the same `LAYOUT` walk a CI step uses to refresh `MANIFEST.json` on every distro commit. The agent installs *against* the manifest it can also build — one source of truth.

## Authoring your own distro hatcher

If you maintain a distro (or want to ship one), the recipe:

1. Define a `LAYOUT` for your distro — list the source dirs / files in your repo and where each one lands relative to `target_home`. Mirrors what your `install.sh` does today.
2. Vendor the reference agent. Copy `install_distro_agent.py` from `kody-w/rappter-distro/agents/`, rename it to `install_<your-distro>_agent.py`, update the `DISTRO_REPO`, `__manifest__.name` (`@yourname/install_<distro>`), and `LAYOUT`. Keep the rest verbatim — it's the load-bearing part.
3. Generate `MANIFEST.json` in CI (or on every push) so the published manifest is always a function of the published source. Commit it.
4. Document the curl one-liner in your distro's README.
5. (Optional but recommended) Submit the hatcher agent to [[Federation via RAR|RAR]] so the wider ecosystem can discover it — it's already in the right `rapp-agent/1.0` schema.

## Open questions

- **Manifest signing.** Today the trust chain is "raw.githubusercontent.com URLs are authoritative for `<owner>/<repo>/<branch>`". A signed manifest would let a hatcher verify provenance without trusting GitHub Pages. Cross-references [[Signed Releases and Variant Attestation]].
- **Cross-distro hatch.** Can a hatcher for distro A also hatch distro B into a third folder? Today each hatcher is hardcoded to its distro. A generic "hatcher driver" agent that takes a manifest URL as input is straightforward but unproven.
- **Hatched-organism identity.** The hatched target needs its own `rappid.json` (the source's was deliberately not copied). Today the user runs `initialize-variant.sh` or lets the boot wrapper mint a fresh identity on first start. A cleaner story is on the [[Rappid]] roadmap.

## See also

- [[Distros as a Pattern]] — the framing this pattern slots into
- [[Boot Sidecar — Integrating Utils Without Modifying the Kernel]] — the runtime mechanism the hatched organism uses after install
- [[Mirror Spec]] — the byte-identical-to-grail discipline the hatcher enforces via sacred-path refusal
- [[Federation via RAR]] — the registry the hatcher manifest doubles as a submission to
- [[The Species DNA Archive — rapp_kernel]] — what the hatcher copies in phase 1 and never modifies

<!-- RAPP1-HISTORICAL-SECTION-END -->
