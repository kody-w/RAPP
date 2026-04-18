# RAPP

📜 **[Read the v1 Specification → `SPEC.md`](./SPEC.md)** — the contractual digital twin of RAPP v1. The single-file `*_agent.py` is sacred.

Static digital twin of the **RAPP stack**, served from this repo via GitHub Pages at [kody-w.github.io/RAPP](https://kody-w.github.io/RAPP/).

The repo memorializes the three-tier RAPP architecture, plus a browser-only **virtual brainstem** that runs the same single-file agent contract entirely client-side.

## Layout

| Path | What it is |
|------|-----------|
| `index.html` | Landing page — animated stack diagram + tier intros |
| `SPEC.md` | The frozen v1 contract (sacred — do not break) |
| [`installer/`](./installer/) | Twin of [kody-w/RAPP](https://github.com/kody-w/RAPP) — install widget mirror |
| [`brainstem/`](./brainstem/) | **Virtual brainstem** — chat UI parity with the local Flask brainstem, plus the **card binder** |
| [`hippocampus/`](./hippocampus/) | Twin of Tier 2 — Deploy-to-Azure button + ARM template doc |
| [`agents/`](./agents/) | Starter single-file agents (`hello`, `dice`, `weather_poet`, `sloshtest`) |
| [`tests/`](./tests/) | Browser + Node test runner for the v1 contract |

## The virtual brainstem

[`brainstem/index.html`](./brainstem/index.html) is a browser-only RAPP brainstem at UI + functional parity with the real one. Bring your own OpenAI-compatible API key and it runs.

It ships with a **starter binder** of single-file agents. Multi-agent hot-loading is organized as a card game:

- **Deck** = your binder (every card you've ever loaded)
- **Hand** = agents currently loaded into the brainstem (visible to the LLM as tools)
- Tap a card → **Play to hand** to hot-load
- The hand row shows which agents will fire on the next turn
- When an agent runs, its mini-card flashes; `data_slush` propagates to the next agent in the chain (SPEC §5.4)

### Cards round-trip to/from agent.py byte-for-byte

A card is a JSON projection of a single-file agent. The full Python source is embedded in `card.source`, with a SHA-256 hash for verification. Importing a `card.json` reconstructs the exact `*_agent.py` file and hot-loads it through the same code path as a raw `.py` import. Exporting a card produces a JSON object the canonical [RAR SDK](https://github.com/kody-w/RAR) can also read (compatible card schema, same seed math, same 7-word incantation).

```
*_agent.py  ─── mintCard ──>  card.json  ─── cardToAgentSource ──>  *_agent.py
                                  │
                                  ▼
                              binder.json  (just an array of cards)
```

## Tests

```bash
node tests/run-tests.mjs        # Node, no deps
# or open tests/index.html in a browser
```

Both runners exercise the same suite: agent parsing, manifest extraction, seed/mnemonic round-trips, card↔agent.py byte equality, SHA-256 tamper detection, binder JSON round-trip, multi-agent chain via `data_slush`, and digital-twin file presence.

## Deploy

GitHub Pages → Settings → Pages → Source: `main` branch, root.

## History

The previous engine code that lived in this repo (the Rapp intelligence engine for Rappterbook) is preserved on the `archive/engine` branch — it is the "genetic twin" referenced in SPEC §16.
