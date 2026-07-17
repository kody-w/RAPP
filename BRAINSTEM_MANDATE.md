# Historical Brainstem Mandate

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](./RAPP1_STATUS.md). This mandate is product strategy; the
> exact RAPP wire and artifact contracts come only from the pinned standard.

> **Whole-document disposition:** this essay records a product ambition. Its
> “ship,” drag-and-drop, universal runtime, and carrier claims are not current
> capabilities or instructions. Today this repository establishes source-level
> RAPP/1 conformance and a loopback pre-acceptance façade only.

<!-- RAPP1-HISTORICAL-SECTION-START -->

> *A foundational note for everyone shipping intelligence under the RAPP banner.  Written in deliberate parallel to a famous 2002 internal email at another company.*

---

## The mandate

1. **All AI capabilities will henceforth be exposed through a local `brainstem.py`.**

2. **Teams must compose through the brainstem** — by shipping single-file agents the brainstem can load, not by standing up services other people must reach.

3. **There will be no other RAPP capability endpoint.** Drop the agent in
   `agents/` and use the exact RAPP/1 §8 `/chat` contract (or a verified
   asynchronous §7 frame). Application UI/admin views do not expand the wire.

4. **It doesn't matter what model the agent calls under the hood.** The host
   contract may use `BasicAgent.perform(**kwargs) → str`; the protocol wire is
   fixed separately and exactly by RAPP/1 §8.

5. **All agents, without exception, must be externalizable from day one.**  Single file.  No infrastructure dependencies.  Drag-and-drop into any brainstem on any device, on any substrate.  No hidden cluster.  No required cloud.  If your agent can't survive being copy-pasted into a fresh brainstem on someone else's laptop, it doesn't ship.

6. **The brainstem runs on the device.  Operator-owned.**  Cloud is an opt-in sync target, never a requirement.  This is what separates us from the 2002 email: APIs externalized your *service*; the brainstem externalizes the *intelligence layer itself*.  Every operator gets one.  It runs locally.  It's theirs.

7. **Anyone shipping AI capabilities through a cloud-only path will be off the platform.**

8. **Thank you; have a nice day.**

---

## What it means

The 2002 API mandate decoupled Amazon's internal teams from each other.  Every service had to be reachable, every interface had to be externalizable, every team had to plan from day one as if their work would be consumed by strangers.  That mandate is the precondition for AWS.  Without it, no `s3://` URL, no `lambda` invocation, no `dynamodb` query.

The intelligence layer needs the same mandate, with one fundamental change: **the externalization endpoint is on the operator's device, not on someone's datacenter.**

The 2002 mandate said: *if your team owns the data, expose it as a service so other teams can use it.*

This one says: *if your team owns an AI capability, ship it as a single-file agent that any operator's brainstem can load, regardless of who they are or where they run.*

The brainstem is to AI what the API was to data.  It is the universal surface.  Once everyone composes through it, every agent any team ships works in every brainstem any operator runs.  No coordination meetings.  No SDK versioning.  No "is your account approved."  No "the dashboard is down."  The capability lives in the operator's hand because the runtime that makes it real is in the operator's hand.

## What's allowed

- ✅ A single-file `*_agent.py` that subclasses `BasicAgent` and implements `perform(**kwargs) → str`.
- ✅ Calling out to any LLM provider from inside `perform()` — your choice, your secrets, your billing.
- ✅ Calling out to any web API, any database, any local file, any subprocess from inside `perform()`.
- ✅ Shipping a rapplication as the RAPP/1 §9 `rapplication` egg variant after
  complete integrity, viability, and signature checks.
- ✅ Optional cloud sync (Dataverse, D365, Azure Files, anywhere) as a target the operator can opt into.
- ✅ Publishing application discovery metadata to RAR, while recognizing that
  RAR is not the signed RAPP/1 §13 registry and cannot confer trust.
- ✅ **The brainstem as a pure controller.** Historical twin-chat adapters may
  drive isolated twins, but current protocol interaction still maps to the
  exact §8 forms.

## What's not allowed

- ❌ "Use our REST API to access intelligence X" — that's the 1995 model.  Wrap it as an agent.
- ❌ "Sign up for our cloud service and you'll get an API key" — that's vendor lock-in dressed as a platform.  Wrap it as an agent.
- ❌ "Our model only runs on our infrastructure" — fine, your agent can call your infrastructure, but the agent itself ships as a file.
- ❌ "You have to install our SDK" — the brainstem is the SDK.  There is no other SDK.
- ❌ A "platform" that requires operators to send their queries to your server before getting an answer.  The brainstem runs on their device.  Your agent runs in their brainstem.  That's the contract.

## What this enables

- **Sovereignty.**  The operator's intelligence layer is theirs.  They control the model, the agents, the memory, the conversation history.  No one else has a copy unless they choose to sync.
- **Composability.** Every agent can remain portable without a central
  application marketplace. This does not remove the required signed,
  monotonic RAPP/1 §13 protocol registry.
- **Substrate independence.**  The brainstem runs on a laptop, on a Mac Mini, in a container, in WSL, on a Raspberry Pi, in a SCIF, on a plane.  Wherever the operator is, intelligence is.  Cloud doesn't get to gate that.
- **Inversion of the platform.**  Historically, AI platforms put the intelligence in the cloud and gave operators a thin client.  RAPP puts the intelligence on the device and treats the cloud as one of many optional sync targets.  This is the actual reversal of the 2010s SaaS pattern.
- **The federation primitive.** Operators can carry verified RAPP/1 §7 frames
  and §9 eggs over LAN, GitHub, AirDrop, or sneakernet. Carrier choice never
  changes protocol structure or trust.

## The single sentence

The brainstem is the platform surface.  Build agents.

## Lineage

This document is product strategy under the Constitution. Constitution Article
LV and the pinned RAPP/1 rev-5 authority win every structural conflict.

The 2002 email this mirrors was about decoupling data ownership inside one company.  This one is about decoupling intelligence ownership across all of them.

Thank you; have a nice day.

<!-- RAPP1-HISTORICAL-SECTION-END -->
