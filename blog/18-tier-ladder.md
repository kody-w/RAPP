# The Tier ladder explained

The brainstem's system prompt mentions three tiers:

> The user may be at any stage of the RAPP journey:
> - **Tier 1 — Brainstem**: local Python or this browser-only twin (where they are now)
> - **Tier 2 — Hippocampus**: Azure Functions with persistent memory, runs locally first
> - **Tier 3 — Nervous System**: Copilot Studio + M365/Teams

The tiers are a deliberate ladder, not a feature matrix. Each one builds on the previous. You climb when you need to, not before.

**Tier 1 — Brainstem.** This is where everyone starts. A local-first AI assistant that runs on your machine (or in your browser, via the virtual brainstem twin). It chats. It calls agents. It remembers things to localStorage or a JSON file. It does not need Azure, does not need API keys, does not need a backend. The brain metaphor: this is the brainstem — core reflexes, the part of the brain that runs whether you're paying attention or not.

For most users, Tier 1 is the whole product. Most workflows are: chat with my AI, have it call a few agents, get an answer, move on. You don't need cloud infrastructure for that. You don't need persistent multi-user memory. You don't need to expose your AI in Teams. You need a local AI that can do work.

**Tier 2 — Hippocampus.** When you're ready for memory that survives more than a single machine — when you want your AI to remember things across devices, share state with teammates, or access files in cloud storage — you graduate to Tier 2. This is Azure Functions with persistent memory. The brain metaphor: the hippocampus is where short-term memory consolidates into long-term memory.

You install Tier 2 with one line. The brainstem's soul prompt knows this and offers it when users ask for "the cloud" or "Azure" or "memory that persists":

```bash
curl -fsSL https://raw.githubusercontent.com/kody-w/rapp-installer/main/community_rapp/install.sh | bash
```

It scaffolds a project at `~/rapp-projects/{name}/` with its own venv, runs locally first, can deploy to Azure later when you actually want shared state.

**Tier 3 — Nervous System.** When you need your AI to be reachable from inside your organization — Microsoft Teams, M365, Copilot Studio agents — you go to Tier 3. The brain metaphor: the nervous system reaches out from the brain to the rest of the body.

This tier is heavyweight. It's where you stop being a single user with a personal AI and start being an organization that's *deploying* AI to its workforce. There's identity, there's RBAC, there's compliance, there's deployment pipelines. The brainstem helps you get here, but it doesn't pretend the climb is one curl command. Tier 3 is real engineering work.

The point of the ladder is that **each tier is whole on its own**. You can stop at Tier 1 forever. Many users will. The brainstem doesn't push you up. The system prompt explicitly says: *don't push users to Azure or Copilot Studio — let them ask when they're ready*.

This matters because most "AI platform" products try to sell you the cloud version on day one. RAPP's bet is the opposite: start local, prove value, climb when you have a reason. Most personal AI users never need to leave the brainstem. The ones who do, do because their use case actually requires it — multi-device, multi-user, enterprise reach. Not because we made them.

The ladder is also the upgrade path. Your Tier 1 agents work in Tier 2 unchanged (same `__manifest__`, same `perform()`). Your Tier 2 agents are reachable from Tier 3 via Copilot Studio's agent action surface. You don't rewrite as you climb. You just add.
