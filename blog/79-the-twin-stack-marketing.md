# Marketing the Twin Stack: positioning, promise, proof

This post is the marketing lens. Every claim in here is something the technical posts back up; this is just the storytelling layer.

## The one-line positioning

**The Twin Stack is the local-first runtime for the digital twin you'll someday want your grandchildren to talk to.**

Local-first because nothing matters if the company hosting your twin disappears. Runtime because a twin is more than a chatbot — it's a process with memory, capabilities, and identity. Digital twin because that's what people understand, even if the term has been overloaded by every IoT vendor since 2015. Grandchildren because perpetuity is the customer's actual ask.

## The three audiences and what each one buys

**Operators (today's customers):**
What they buy: *a digital extension of themselves at work.* The twin handles inbound, briefs them on context, drafts in their voice, holds the institutional memory across roles and companies. Pricing: subscription, like a senior EA at 1/100th the cost.

**Families (next year's customers):**
What they buy: *a continuity instrument.* A parent's twin trained on a decade of their writing, decisions, and recorded conversations becomes a thing the kids can ask questions of after the parent is gone. Pricing: endowment-funded perpetual, billed once.

**Institutions (the legacy market):**
What they buy: *a structured-data preservation service for high-net-worth principals.* Family offices, foundations, academic institutions. The twin holds the principal's strategic knowledge alongside their wealth-transfer documentation. Pricing: enterprise, retainer + usage.

Same product, three positions. The local-first architecture is what lets the same platform serve all three without compromising any of them.

## Why "local-first" is the whole pitch

Every other AI assistant is a SaaS terminal pointed at OpenAI/Anthropic. Stop paying, lose access. Vendor decides to deprecate, lose your work. Vendor gets acquired, lose your privacy posture.

The Twin Stack inverts that:
- Your twin's swarms live in `~/.rapp-twins/<name>/` on your laptop
- The agents are `*_agent.py` files you can `cat` and read
- The conversations are JSONL on your filesystem
- The documents are files in `documents/` and `inbox/`
- The cloud deployment is *optional* — and even when used, it's *your* Azure subscription, *your* resource group, *your* keys

The LLM is the only remote dependency. And that's swappable in one env-var change: Azure OpenAI today, OpenAI/Anthropic/Ollama/Llama-on-your-RTX-4090 tomorrow. The twin doesn't change. The runtime doesn't change. Just the model.

## The proof we have today

- **Hero demo runs in 12 seconds:** `bash hippocampus/twin-sim.sh demo hero` — real git log → twin → T2T → twin → CEO decision. Verifiable on any clone of the repo.
- **148 tests passing across 3 runtimes:** stdlib server, local Azure Functions, deployed cloud Functions. Same wire format, three implementations.
- **2 deployed twins live in Azure right now:** `twin-kody-e89834.azurewebsites.net` and `twin-molly-4181ee.azurewebsites.net`, each in its own resource group, each costing ~$0/month at idle.
- **71+ field notes published:** the entire engineering thinking is open. Not "transparent" in a marketing sense — actually published, with code links.
- **Provisional patent filed.** "Patent-pending" is a literal status, not a slogan.

## The competitive frame

Every AI agent platform falls into one of three buckets:

| Bucket | Examples | What they sell |
|---|---|---|
| **SaaS chatbots** | ChatGPT teams, Claude, Copilot | A pane of glass over an LLM |
| **Agent orchestrators** | LangChain, AutoGen, CrewAI | A library you assemble agents with |
| **Twin/preservation platforms** | (basically nobody seriously) | A persistent identity layer |

The Twin Stack is in the third bucket — and the third bucket is mostly empty. The competition isn't really other AI products. It's Rolodexes, journals, biographies, family trusts, and (long-tail) the human discomfort with admitting you're going to die.

## Pricing tiers (the ladder)

The full ladder is in `blog/18-tier-ladder.md` and `blog/63-pricing-for-legacy.md`. The headline:

| Tier | One-line | Audience |
|---|---|---|
| Free | Local-first, your hardware, BYO LLM | Curious developers, students |
| Personal ($29/mo) | One twin, cloud-hosted on your Azure | Operators using the twin daily |
| Heritage ($299/mo) | Multi-twin family vault, sealing, snapshots | Families building a continuity instrument |
| Founder ($2,999/yr) | Build-in-public co-founder, unlimited swarms | Indie hackers, solo founders |
| Institutional (custom) | Family-office-grade with curator support | Family offices, foundations |
| Dynasty Trust (endowment) | Pay once, run perpetually | Multi-generational principals |
| Public Heritage (donated) | Public-figure twin, subsidized | Notable historical figures |

Every tier uses the same Twin Stack. The differences are capacity, support, and ceremony.

## What we don't say

We don't say "AGI." We don't say "your twin replaces you." We don't say "guaranteed indistinguishable from you." We don't say "you'll live forever."

We say: a twin is a useful, growing, personal tool. It gets sharper the more you use it. It belongs to you and stays with you. When you're gone, what's preserved is *the part you chose to make preservable* — your soul addendum, your conversations, your documents, the way you talk. Not your consciousness. Not your secrets unless you put them in. Not your privacy without your consent.

## The closing line

> *Your twin is the smallest workable version of you that can keep being useful after you stop showing up.*

That's the whole pitch. Everything else is implementation detail.
