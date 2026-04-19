# The hero demo: real git history → twin → twin → CEO decision in 12 seconds

If you build a digital-twin system and you can't show somebody it works in under a minute, the system isn't real.

Here's the hero demo, exactly as it runs:

```bash
bash hippocampus/twin-sim.sh demo hero
```

That single command:
1. Spins up Kody's twin and Molly's twin if they're not already running (each on its own port + workspace)
2. Mutually peers them for T2T
3. Auto-hatches their clouds from the registry if either is empty
4. Captures *this repo's actual* `git log -5`, file-changed stats, and blog count into `/tmp/this-week.md`
5. Saves that file into `kody/documents/`
6. Asks Kody's twin (live Azure OpenAI gpt-5.4) to draft a 4-bullet brief for Molly using that document
7. Saves the brief as `kody/documents/brief-for-molly.md`
8. HMAC-signs and sends via T2T to Molly's twin → `molly/inbox/`
9. Asks Molly's twin (also live gpt-5.4) to read the brief and return a CEO decision in 3 bullets
10. Prints both the brief and the response side-by-side

End to end: ~12 seconds. Two LLM calls. One signed file transfer. Two isolated workspaces. Real production gpt-5.4. **No staging.** The git data is real (the actual commit `223fd1e` of this repo). The roles are real (the actual soul addendums in `brainstem/onboard/registry.json`). The intelligence is real (Azure OpenAI — same backend a Fortune 500 uses).

**What you see in the output:**

Kody's brief (verbatim from a real run):

> Subject: This week's RAPP brief
> Molly —
> - Strategic headline: we now have the public primitives for preservation in place — swarm sealing + snapshot shipped, plus Twin Stack v1 tying hatch, T2T, and hippocampus together.
> - We shipped a major code drop in the last commit: 20 files, 4,084 insertions, including hippocampus cloud functions, T2T wiring, chat/LLM paths, onboarding flow, and deploy/test coverage.
> - Build-in-public moved hard: the blog is now at 71 field notes…
> - Live infra is stable and simple: local twins are Kody and Molly; provider is Azure OpenAI on gpt-5.4.
> Kody

Molly's reply:

> - **Decision owed by tomorrow:** whether we treat this as the first **partner-ready preservation demo window** now, or keep it in founder-safe testing for one more cycle.
> - **Partner conversation unlocked:** a first serious **estate-attorney / family-office briefing** — not the full vision, but the practical story: capture, continuity, custody.
> - **Pushback:** yes — "patent-pending" and "public primitives" need tighter message discipline. We should not let shipping velocity outrun claims, custody language, or readiness framing.

Note the *pushback*. Molly's twin didn't just summarize Kody's brief — it returned a sharp strategic correction in her CEO voice. That's not a summarization model; that's role-aware reasoning grounded in a soul addendum that includes "you operate from a position of long-term stewardship" and "you are the relationship layer with partners (estate attorneys, family offices, investors, press)."

**Why this is the right hero demo:**

Most AI demos are *generative* — they produce content. They impress because the output is novel. This demo is *operational* — it produces a *decision*. The output is something a human can act on tomorrow morning.

It also touches every novel piece of the Twin Stack at once:
- The local-first runtime (twin-sim.sh)
- Per-twin workspaces (isolated state)
- Cloud-from-registry hatching (the bundle pattern)
- Hot-loaded agents (per-swarm tool sets)
- LLM dispatch with tool-calling (chat.py)
- Soul-shaped role reasoning (each twin behaves like its principal)
- Document save (workspace.py)
- HMAC-signed T2T document share (the protocol)
- Cross-twin processing (Molly reads Kody's brief, not a system message)

Anyone can verify it. Anyone can clone the repo and run the command. The data is their own git log. There's no canned demo content.

**This is the bar:**

When someone asks "what does the Twin Stack do?" — you don't open slides. You open a terminal and type `bash hippocampus/twin-sim.sh demo hero`. Twelve seconds later, you've shown them a co-founder pair using their digital twins to brief each other on real work and produce a real decision. End of demo, start of conversation.
