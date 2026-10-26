# Why a Brainstem

> Updated October 2026. This page is the reason, not the spec. The exact wire and file contracts live in
> [RAPP/1](https://rapp1.si); what ships today is on the installer's
> [Start here](https://github.com/kody-w/rapp-installer#start-here) page.

## The short version

**The AI you use will keep changing. Your Brainstem is the part that doesn't.**

A Brainstem is a small AI home that runs on a computer you own. It keeps your memory, your agents and the way you
like things done, and it lends them to whichever AI you are using this month: Claude, ChatGPT, GitHub Copilot, a free
local model, or whatever comes next. Swap the model and you keep everything you built.

## Two things happened in 2026

**The gap got wider.** Andrej Karpathy describes AI understanding as a funnel. Roughly six billion people have barely
touched these systems. One to two billion use a free chatbot now and then. About twenty million use frontier models
every day for code and math and watch weeks of work get done from one prompt. About five thousand people inside the
labs watch swarms of agents work for weeks. Each layer doesn't see a better AI. It sees a different one.

**The horse question got real.** David Shapiro's argument: machines replaced horses one job at a time because they
were better, faster, cheaper and safer, and "learn to use the AI" is the horse learning to drive the tractor. It buys
time. His way out is ownership. Horses could never own a share of the tractor. People can.

A Brainstem is our answer to both. It brings the bottom of the funnel up to everyone, and it's an engine you own.

## Why, at the frontier

For people already deep in the funnel, the Brainstem is the part your tools don't give you:

- **It stays on.** A coding session ends when you close the terminal. A Brainstem keeps running on the laptop in the
  closet, so long jobs keep going while you sleep.
- **Your work is files, not settings.** Every ability is one `agent.py` file. You can read it, copy it to another
  computer, share it, or keep it private. It runs the same on every Brainstem.
- **Any model, one setting.** Use the strongest model for the hard job and the cheapest one for the routine one. The
  agents don't care.
- **Checkable work.** Models are sharpest where the work can be checked: code that runs, a test that passes. A
  Brainstem is built around receipts (what ran, what changed, the proof), so more of your work lands in the zone
  where AI is strongest.
- **Many computers, one AI.** Several Brainstems can act as one, so the work isn't tied to the one machine you happen
  to be sitting at.
- **A core that doesn't move under you.** The kernel is small and kept backward compatible on purpose, like Linux.
  What worked last month works the same way today.

## Why, every day

For everyone else, which is most people, the Brainstem is how you skip the funnel:

- **It learns you once.** Tell it about yourself, your work and your preferences one time and it keeps that memory on
  your machine. Connect Claude, ChatGPT or Copilot through [brainstem-mcp](https://github.com/kody-w/brainstem-mcp)
  and they share it, so you stop re-explaining yourself to each new app.
- **It learns as you go.** Everything you teach it stays, so it needs less from you every week, not more.
- **You talk; it works.** No prompts to master, no models to compare, no tools to wire together. You say what you
  want in plain words, it does the work, and it shows you what it did.
- **It's yours.** Memory stays on your machine. Nothing you teach it is locked inside someone else's product.
- **It's a teacher, too.** Because every ability is a small readable file, anyone curious can open one and see exactly
  how it works. Learning AI stops being a lecture and becomes looking under the hood of something you already use.

## Regardless of AI stack

The Brainstem doesn't compete with the AI you already use. It gives it a home.

| You use | What the Brainstem adds |
|---|---|
| Claude | A memory and set of agents that outlive the chat, and keep working when the session ends |
| ChatGPT | The same memory and agents, shared with everything else you use |
| GitHub Copilot | A place for your agents to live outside one editor, signed in once |
| Free or local models | The same agents and memory, on hardware you already own |
| Whatever ships next year | Nothing to migrate. Point the Brainstem at it and keep going |

Others do some things better. Claude Code is the stronger coding agent, ChatGPT is the more polished app, and MCP has
the biggest catalog of tools. They connect to your Brainstem, and your Brainstem runs where they can't.

## What we learned from the people who came before

Every lasting computing idea promised the person something that outlived the vendor: POSIX promised the interface,
not the machine; SQL promised the query, not the database; the web promised the link, not the browser. The Brainstem
promises the same thing for AI: **your agents, your memory and one plain `/chat` door, whatever model is behind it.**

## Read next

- [The Personless Harness](https://kodyw.com/the-personless-harness/): the engine, the carriage and the horse.
- [BRAINSTEM_MANDATE.md](BRAINSTEM_MANDATE.md): the original mandate (historical).
- [PHILOSOPHY.md](PHILOSOPHY.md) and [ZEN.md](ZEN.md): how the platform thinks.
- [RAPP/1](https://rapp1.si): the protocol.
