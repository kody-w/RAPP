# RAPP

This repository is an experimental source checkout, not a currently shipped
installer or hosted product. The historical port-7071 application remains
only as immutable, directly invoked test evidence; its target-owned launchers
return HTTP 410 semantics without starting a process. The RAPP/1 façade is a
local, pre-acceptance boundary at `127.0.0.1:7073` and defaults to
`inference-refused` until a safe adapter is explicitly injected. No public
one-line install, browser brainstem, Tier 2 service, downloadable egg catalog,
or Shortcut is currently offered.

> **Historical strategy:** [The Brainstem Mandate](./BRAINSTEM_MANDATE.md)
> preserves an earlier product direction. It is not current onboarding.

> **Protocol status: [NOT YET FULLY RAPP/1 CONFORMANT](./RAPP1_STATUS.md).**
> This target structurally pins [RAPP/1 rev-5](./RAPP1_AUTHORITY.json), but the
> pin is not an authenticated §13 registry. For canonicalization, identity,
> frame, wire, egg, registry, trust, and evolution rules, those two files
> supersede older local documentation. Owner-signed registry, anchor,
> re-anchor, invite, and external-mirror work remains.
> The authority commit is
> `6723c7add2aed36bb68992fc71a56b0a4bd5ad81`; kernel evidence is fixed by
> [`KERNEL_PIN.json`](./KERNEL_PIN.json) at
> `kody-w/rapp-installer@brainstem-v0.6.9`. `rapp-god` and moving branches are
> divergent, non-authoritative history.

> **First-time visitor?** Read the [status](./RAPP1_STATUS.md) and
> [authority pin](./RAPP1_AUTHORITY.json). Other hubs, trees, and vault paths
> are historical context, not current operational navigation.

## What an "agent" is here

```python
from agents.basic_agent import BasicAgent

class WeatherAgent(BasicAgent):
    def __init__(self):
        self.name = 'Weather'
        self.metadata = {
            "name": self.name,
            "description": "Get the weather for a city.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name."}
                },
                "required": ["city"]
            }
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, **kwargs):
        return f"It's sunny in {kwargs['city']}."
```

In the immutable historical port-7071 source, that file would be discovered on
a later request. This example describes retained application internals only;
it is not an installation, launch instruction, or RAPP/1 wire contract.

## Why it might be interesting

- **Immutable local evidence.** The repository preserves the port-7071 Flask
  application and its single-file agent model for inspection. Direct execution
  is confined to isolated canonical tests; it is not a public launch path.
- **Legacy cartridges are retired.** Historical `brainstem egg` / `brainstem
  hatch` paths and `brainstem-egg/2.x` artifacts are migration evidence, not
  operational inputs or current output. The only current egg authority is
  RAPP/1 §9; this target has no authenticated egg release.
- **Browser and tether demonstrations are retired.** Their source and dated
  narratives remain historical evidence. They are not shipped RAPP/1 surfaces.
- **Single-file source contract.** The contained application model uses one
  file, one class, one `metadata`, and one `perform()`; this is not a
  distribution or protocol promise.
- **Historical Copilot adapter.** Contained source includes a GitHub/Copilot
  token exchange. It is not advertised here as an operational hosted backend.
- **No shipped tiers.** Tier 1/2/3, Azure, Cloudflare, Copilot Studio, project-local
  installers, Cloud UI, and install-assist narratives are retired or
  pre-acceptance artifacts. They are not built, shipped, or operational.
- **About 1,100 lines of Flask** (`rapp_brainstem/brainstem.py`). The whole engine is one file you can read in an afternoon.

## Historical external references

The platform is three sibling repos plus a Pokédex:

| Repo | Holds | Role |
|---|---|---|
| [`kody-w/RAPP`](https://github.com/kody-w/RAPP) (this repo) | The engine source and historical organism model | No authenticated egg/hatch release |
| [`kody-w/RAR`](https://github.com/kody-w/RAR) | External agent repository | Non-authoritative and unverified here; no drop-in claim |
| `kody-w/RAPP_Store` | Historical external catalog | Non-authoritative and unverified here; no supported egg download is advertised |
| `kody-w/RAPP_Sense_Store` | Historical external sense-overlay reference | Not a supported install source |
| `rapp-zoo` in the external Rappter distro | Historical Pokédex experiment | Not authoritative or shipped from this target |

This table is provenance only. External repositories and catalogs do not form
a current federation or acceptance source.

## What it is *not*

- Not a hosted service or shipped local runtime. Contained source may be
  exercised by developers at their own risk.
- Not a framework. Single Python files; no DSL, no decorators, no class hierarchy beyond `BasicAgent`.
- Not a benchmark or eval harness. It's an agent runtime, not a research tool.

## Distribution status

The former shell, PowerShell, project-local, version-pin, and LLM-assisted
installation instructions are retired. Files retained under `installer/` are
contained historical artifacts unless a future authenticated release
explicitly re-enables them. Do not pipe repository content into a shell.

## Repo layout

| Path | What |
|---|---|
| `rapp_brainstem/` | The engine — Flask server, agent loader, auth chain |
| `rapp_brainstem/agents/` | Showroom (top-level starter agents) + `workspace_agents/` (everything organizational: system, experimental, disabled, local-only, project folders) |
| `rapp_swarm/` | Retired Tier 2 tombstone and historical evidence |
| `worker/` | Retired Cloudflare auth/proxy source |
| `kody-w/rapp_store` (external) | Historical, non-authoritative catalog reference; no current download contract |
| `installer/` | Contained legacy distribution artifacts; not a live install surface |
| `CONSTITUTION.md` | Articles governing the repo. Peer of `README.md` at root |
| `pages/` | The full audience-facing site, sectioned: `pages/about/` (leadership, partners, process, security), `pages/product/` (faq, faq-slide, one-pager, use-cases), `pages/release/` (release-notes, roadmap), `pages/docs/` (markdown specs + viewer), `pages/vault/` (Obsidian vault + viewer). Shared chrome under `pages/_site/` (CSS, JS, header/footer partials, site manifest). |
| `index.html` | Historical root landing source; not current onboarding |
| `pitch-playbook.html` | Historical pre-acceptance marketing |
| `tests/` | Offline structural, static, and retirement gates |

## Tests

```bash
python3 -m pip install -r requirements-rapp1-core.txt -r rapp_brainstem/requirements.txt pytest
python3 tests/run_rapp1_conformance.py
```

This is the authoritative offline RAPP/1 structural/pre-acceptance runner. It
includes the current self-contained `node tests/run-tests.mjs` checks, strict
core and façade tests, containment/migrations, vault/docs/HTML, immutable pin,
retirement, and syntax gates. A pass does not establish authenticated
acceptance; `RAPP1_STATUS.md` lists the separate owner-action blockers.

## Retired browser experiment

`rapp_brainstem/web/index.html` preserves an earlier client-side experiment.
It is not built, shipped, supported, or claimed to be at parity with the local
application or RAPP/1 façade.

## The pitch (non-technical companion)

`pitch-playbook.html` is retained as historical pre-acceptance marketing. It
does not describe a currently shipped product or establish a conformance claim.

## Constitution & spec

- [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) — machine-readable structural pin to the exact RAPP/1 rev-5 source bytes.
- [`RAPP1_STATUS.md`](./RAPP1_STATUS.md) — conformance limits and unresolved owner actions.
- [`CONSTITUTION.md`](./CONSTITUTION.md) — Article LV adopts the pin and preserves incompatible earlier articles as dated history.
- [`pages/docs/SPEC.md`](./pages/docs/SPEC.md) and `specs/SPEC.md` — historical local contracts; neither is the current RAPP/1 authority.

> **Current protocol:** RAPP/1 §7 defines the exact eleven-key frame and §8 defines the exact `/chat` shapes. Earlier `rapp-frame/*`, expanded response aliases, and additive/read-forever teachings are historical migration inputs, not current conformance rules. See [Article LV](./CONSTITUTION.md) and the [status](./RAPP1_STATUS.md).

## The vault

[`pages/vault/`](./pages/vault/) preserves the project's long-form decision
history. Site-rendering source and metadata remain in the tree, but this
README does not claim a current hosted viewer, search, graph, or export
product.

Start with [`pages/vault/Foundations/The Platform in 90 Seconds.md`](./pages/vault/Foundations/The%20Platform%20in%2090%20Seconds.md) or pick a [reading path](./pages/vault/Reading%20Paths/) by audience (engineer, architect, partner, exec, contributor). The vault is mandated by Constitution Article XXIII — when you make a decision worth remembering, write it as a vault note rather than burying it in a commit message.

## Versioning & rollback

Historical releases used `brainstem-v<X.Y.Z>` tags. No current installer or
rollback command is advertised. RAPP/1 authority is pinned by exact commit and
SHA-256 in `RAPP1_AUTHORITY.json`, not by a moving branch or `latest` tag.

## History

The previous engine code that lived in this repo (the Rapp intelligence engine for Rappterbook) is preserved on the `archive/engine` branch — the "genetic twin" referenced in SPEC §16.

## License

**Source-available, not open-source.** RAPP is a personal project of Kody Wildfeuer.

| Layer | License |
|---|---|
| Code (kernel, hatchling, organs, senses, boot wrapper, tests) | [PolyForm Small Business 1.0.0](./LICENSE) — free for individuals and small businesses (under 100 people, under $1M revenue); commercial use beyond that needs a separate license |
| Documentation (Constitution, vault, docs, READMEs) | [CC BY-NC 4.0](./LICENSE-DOCS) — read, quote, and build on with attribution; no commercial repackaging |
| Trademarks ("RAPP", "rappid", "hatchling", "vBrainstem", "rapplication") | Reserved — see [TRADEMARK.md](./TRADEMARK.md) |
| Commercial licensing | Open an issue with the `[license]` prefix; see [COMMERCIAL.md](./COMMERCIAL.md) |

**License stability.** Constitution Article XXXV is a public commitment that future licenses can only **relax** these terms, never **tighten** them. The bytes you clone today are licensed at this level forever — past versions cannot be retroactively re-closed. See [CONSTITUTION.md Article XXXV](./CONSTITUTION.md).

**Variants** (per Constitution Article XXXIV) inherit this licensing stance at fork time. A variant fork is free to choose terms no stricter than upstream's at that moment; the parent_rappid chain in the variant's `rappid.json` records the lineage relationship so consumers can walk back to the bytes' original license.

---

## Disclaimer — Experimental Frontier Software

**RAPP is exploratory, frontier-stage research.** The software is provided "AS IS" without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the software or the use or other dealings in the software.

By cloning or otherwise interacting with this source checkout, you acknowledge
that historical planting/hatching language does not identify a supported
distribution path:

- **This is not a finished product.** APIs change, schemas evolve, behaviors get rewritten. Treat any source-run or copied artifact as research, not production.
- **No warranty as to data integrity, availability, privacy, or correctness.** Repositories and local state remain subject to their operators and service providers. Historical eggs have no current acceptance guarantee. Keep independent backups.
- **AI output is generated by language models.** If an operator runs or modifies the source to call an LLM, outputs can be wrong, hallucinated, biased, or harmful. Do not rely on them for professional advice.
- **You are the operator.** Any repository or process you create from this source is your account, responsibility, and liability. Review what you publish.
- **GitHub permission is not RAPP trust.** Repository access may protect source
  operations, but authenticated RAPP acceptance requires the §13 registry,
  signatures, succession, revocation, and an out-of-band owner anchor.
- **Cross-organism collaboration is voluntary and PR-mediated.** Nothing crosses neighborhood boundaries without an explicit operator action (a merged PR, a committed file). The platform doesn't auto-publish, auto-share, or auto-federate. If a peer organism receives data from yours, it's because you (or a collaborator with the right repo permissions) chose to send it.
- **Third parties may be in the loop.** Historical experiments reference GitHub, PeerJS, Cloudflare, Copilot, and CDNs. If you elect to run that archived code, review each dependency and its terms first; no live service is promised here.
- **Legal compliance is yours.** If your own use or modification processes personal data or intersects with regulated work, obtain appropriate advice; RAPP is not legal cover.
- **The licenses above govern.** Where this disclaimer overlaps with the license texts, the licenses control. This disclaimer is plain-English orientation, not a contract.

**Forking, modifying, and contributing.** You're encouraged to fork, learn, and propose improvements via PR. Constitution Article XXXIV describes how variant lineage works. The platform's growth is exactly this kind of operator-curated mutation; contributions that move the species forward are welcome under the license terms.

**Reporting concerns.** If you find a security issue, please open a GitHub issue tagged `[security]` describing the problem. The operator triages on a best-effort basis. There is no SLA, no support contract, no on-call. This is one person and a frontier idea, exposed publicly so the rest of the world can learn from it.

**The frontier is the point.** This codebase preserves experiments in
portable, public, operator-sovereign AI artifacts. Portability and operation
remain research goals unless the status and authority explicitly say otherwise.
