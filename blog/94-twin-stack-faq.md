# A Twin Stack FAQ

This is the question pile that's been accumulating in DMs, demos, and the back of the room. Answered straight, no marketing. Where the answer is "not yet," it says not yet.

**What is the Twin Stack?**

The Twin Stack is the local-first, cloud-portable runtime for digital twins built out of single-file agents. It's an identity layer (`cloud_id` + `secret`), a per-twin workspace (`~/.rapp-twins/<name>/`), a brainstem that runs the same wire surface locally or in Azure, and a peer protocol called T2T that lets twins talk to each other. You occupy it; you don't import it.

**Is this open source?**

Yes. The reference implementation is at [kody-w/RAPP](https://github.com/kody-w/RAPP), the cloud backend is at [kody-w/CommunityRAPP](https://github.com/kody-w/CommunityRAPP), and the agent registry is at [kody-w/RAR](https://github.com/kody-w/RAR). The v1 spec at `SPEC.md` is frozen and contractual — anything that conforms to §5 is a valid RAPP agent, regardless of who built the runtime.

**Do I need an Azure account?**

No, not for Tier 1. The local brainstem runs on your laptop with `curl -fsSL https://kody-w.github.io/RAPP/install.sh | bash` followed by `brainstem`, and authenticates to GitHub Models with `gh auth login`. You only need Azure if you want Tier 2 — a Function App per twin, deployed via `bash hippocampus/provision-twin-lite.sh <name>`.

**Can I use OpenAI / Anthropic instead?**

Yes. `swarm/llm.py` dispatches to Azure OpenAI, OpenAI, Anthropic, or a fake provider for tests. Pick whichever has keys in your environment; the agent contract doesn't care which model is on the other end of the function call. The orchestrator picks tools probabilistically and the agent runs deterministically — that split is the same regardless of provider.

**Will it work offline?**

The brainstem boots offline, the binder reads from IndexedDB offline, and `card resolve` works against a local clone of RAR with no network. `git clone` the registry once and you have everything — it works from `file://`, in a cabin, with no internet. The LLM call itself obviously needs whoever you pointed `swarm/llm.py` at — unless that's a local model, in which case yes, fully offline.

**Where does my twin's state live?**

In `~/.rapp-twins/<name>/` on your filesystem, or in the equivalent `BRAINSTEM_HOME` directory inside your Function App's storage account. That directory contains `workspace.json`, `swarms/`, `t2t/`, `documents/`, `inbox/`, `outbox/`, `server.log`, `server.pid`. Move the directory, move the twin.

**What's the difference between a twin, a swarm, and an agent?**

An agent is one `*_agent.py` file with a `BasicAgent` subclass and a `perform()` method. A swarm is a hatched bundle of agents (plus a soul) loaded into a workspace under `~/.rapp-twins/<name>/swarms/<guid>/`. A twin is the whole identity — one `cloud_id`, one secret, one workspace, however many swarms you've hatched into it.

**Can two twins talk to each other?**

Yes, that's T2T (twin-to-twin). `bash hippocampus/twin-sim.sh peer kody molly` performs a mutual peering by reading both `identity.json` files and posting to each twin's `/api/t2t/peers` endpoint. Once peered, twins can chat, share documents, and invoke each other's swarms.

**Is T2T encrypted?**

T2T envelopes are HMAC-SHA256 signed for authenticity, not encrypted for confidentiality. Run T2T over HTTPS (the cloud Function Apps already do); the HMAC proves the sender, the transport protects the contents. End-to-end encryption between twins is a v2 item — not yet.

**Can my twin run on my phone?**

The browser-only virtual brainstem at `brainstem/index.html` is a PWA and runs on a phone — bring an OpenAI-compatible key and you have a hand of agents in your pocket. The full Python stack (the one that hosts T2T peers and accepts inbound calls) doesn't run on iOS/Android — not yet. v2's "phone-anchored cloud" pattern handles that with a relay.

**What's an .egg file?**

An egg is a compact serialization of a set of agents into a shareable string. `python rapp_sdk.py egg forge @a/foo @b/bar @c/baz` produces one; `python rapp_sdk.py egg hatch <STRING>` reconstructs the agents on another device. It's the side-channel format for moving a swarm without a registry round-trip.

**What's the difference between hatching a swarm and importing a twin?**

Hatching a swarm drops a bundle of agents into an existing twin's workspace — the soul, identity, and history stay yours. Importing a twin (via snapshot or workspace move) brings in someone else's whole identity: their soul addendum, their conversation history, their peers. Hatching is "learn this skill"; importing is "this is now me."

**How do I install the tether?**

On macOS/Linux: `curl -fsSL https://kody-w.github.io/RAPP/install-tether.sh | bash`. On Windows: `irm https://kody-w.github.io/RAPP/install-tether.ps1 | iex`. The tether is the thin local helper that lets a browser brainstem reach files and shells on your machine through a single agreed-upon port. The browser stays the UI; the tether is the hands.

**Can someone else's twin use my computer?**

Only through capabilities you've explicitly granted in `t2t/peers.json`, and only via signed T2T envelopes for endpoints your brainstem exposes. There's no implicit trust — peering is mutual and out-of-band, and capability invocation is logged in `t2t/conversations/`. Revoke by deleting the peer entry.

**What happens to my twin if I stop paying?**

Tier 1 is free forever — it's `python` and your GitHub auth. Tier 2 on Consumption Y1 costs roughly $0 at idle plus ~2¢/GB/month for storage; if you stop paying Azure, the resource group eventually goes away, but `az group export` or a workspace dir copy gets the bytes off first. The twin is a directory; the directory is portable.

**How is this different from ChatGPT / Claude / a plugin store?**

ChatGPT and Claude are services you talk to. The Twin Stack is a runtime you own — your soul file, your agents directory, your storage, your URL, your keys. Plugin stores are a marketplace of capabilities for someone else's chatbot; RAR is a registry of single-file agents that drop into *your* brainstem (or any v1-compliant runtime, including ones nobody's written yet).

**Do I lose my data if the company disappears?**

No. The spec is frozen and public, the reference implementations are MIT, and the data layout is filesystem-native. If every server kody-w runs vanishes tomorrow, your `~/.rapp-twins/<name>/` directory is still a working twin — clone the repo, run `brainstem`, point at the directory, you're back.

**Can my kids inherit my twin?**

Mechanically, yes — a twin is a directory plus a `cloud_id`/`secret` pair. Hand over the workspace, hand over the secret, they own it. The legal/estate side (sealing a twin to make it immutable but queryable, the endowment-funded perpetual hosting model) is sketched in `blog/53-smallest-workable-seal.md` and `blog/64-endowment-funded-perpetual.md` but is not turn-key — not yet.

**How do I delete a twin completely?**

Locally: `rm -rf ~/.rapp-twins/<name>/`. In Azure: `az group delete --name rg-twin-<name> --yes --no-wait`. Both are guaranteed clean removals because the per-twin isolation (one resource group, one storage account, one Function App) means there's nothing shared to clean up. If the twin had peers, notify them out-of-band — the protocol doesn't broadcast deletions.

**What's the smallest workable use case?**

Install the brainstem, drop a `weather_agent.py` in `agents/`, ask it about the weather. That's the whole thing — one file, one tenant, one soul, one machine. Everything else (swarms, T2T, the cloud tier, RAR, eggs, sealing) is optional surface area you grow into when you have a reason to.

**Do I have to publish my agents to RAR?**

No. §12.0 of the spec is explicit: a `weather_agent.py` with `BasicAgent`, `name`, `metadata`, and `perform()` is a fully valid RAPP v1 agent and runs anywhere. The `__manifest__` block is the cost of admission to the registry, not the cost of being a RAPP agent. Run private agents forever; publish only when you want others to install them with `rapp_sdk.py install`.

**How do I move a twin between machines?**

Copy `~/.rapp-twins/<name>/` to the new machine (rsync, USB, syncthing, whatever). Install the brainstem on the new side, point it at the directory, start it. The `cloud_id` and `secret` come along in `t2t/identity.json`, so existing peers still recognize the twin without re-pairing.

**Can I run two twins on the same laptop?**

Yes — that's what `hippocampus/twin-sim.sh` is for. Each twin gets a deterministic port (`7090 + hash(name) % 100`) and an isolated workspace under `~/.rapp-twins/`. Two `start` calls and a `peer` call gives you a synthetic multi-twin scenario without spending a cent on cloud.

**What models are supported?**

Anything OpenAI-function-calling-compatible. Tier 1 defaults to GitHub Models `gpt-4o`; Tier 2 expects an Azure OpenAI deployment of GPT-4o. The dispatcher in `swarm/llm.py` also handles raw OpenAI, Anthropic, and a fake provider for tests — adding a new provider is editing one file.

**Is there a UI or is this all command line?**

There's a UI. The brainstem ships a chat interface, and `brainstem/index.html` runs the same UI entirely in the browser with a card binder for hot-loading agents. The CLI commands in this FAQ are for installing, provisioning, and peering — once a twin is up, you talk to it in chat like anything else.

**What if I find a bug or want a feature?**

File an issue on [kody-w/RAPP](https://github.com/kody-w/RAPP) for the runtime, [kody-w/RAR](https://github.com/kody-w/RAR) for the registry, or [kody-w/CommunityRAPP](https://github.com/kody-w/CommunityRAPP) for the cloud backend. The spec at `SPEC.md` is frozen for v1 — feature requests that would change §5 (the agent contract), §8 (the HTTP surface), or §5.4 (data slush) are v2 conversations, not v1 patches.

**Can I snapshot a twin and roll back?**

Yes. A snapshot is a frozen copy of the `agents/` directory and the memory store at a point in time, written under the workspace. Restore by pointing the brainstem at the snapshot or by copying it back over the live directory. Useful before a risky soul edit, a `LearnNew` agent generation that might go sideways, or any change you might want to undo cleanly.

**What if I want to seal a twin?**

Sealing mutates the manifest and `chmod 444`s the agent files — the twin becomes immutable but still queryable. Used for memorialization (a twin you want to preserve as it was at a moment) or for shipping a frozen reference twin to peers. The smallest workable seal is documented in `blog/53-smallest-workable-seal.md`; the v1 primitive is intentionally crude because the social/legal surrounding it isn't.

That's the pile cleared. New questions land in the issue tracker; the next FAQ post happens when the answers settle into something stable enough to write down.
