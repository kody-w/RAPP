# Same surface, two execution modes

RAPP has two installable products that look almost identical from the outside:

- `install.sh` — the local Python brainstem (Flask, venv, GitHub OAuth).
- `install-tether.sh` — the tether server (stdlib, no venv, no OAuth).

People sometimes ask which one they should pick. The honest answer is: it depends on where you want the model to live.

|              | **Local brainstem**        | **Tether**                          |
|--------------|----------------------------|-------------------------------------|
| AI runs      | Locally (your Copilot)     | In the browser (virtual brainstem)  |
| Agents run   | Locally                    | Locally                             |
| Install      | Python + venv + Flask + gh | Python (stdlib only)                |
| Auth         | Device-code flow on box    | None (the browser handles it)       |
| Use case     | Long-running, scripts, cli | Chat-shaped sessions, ad-hoc calls  |

Both run the exact same `*_agent.py` files. Both use the same `__manifest__` schema. Both expose tools to the model with the same OpenAI function-calling shape.

The split is about *where intelligence lives*. With the local brainstem, your machine holds the loop: the model runs, the agents run, the conversation history persists in `~/.brainstem`. You can hit `/chat` from a script, from cron, from another agent. The browser is optional.

With the tether, the conversation lives in the browser. The model is whatever's in the virtual brainstem's dropdown (Claude Sonnet 4.6, GPT-4o, Opus, whatever). The agents live on your machine because that's where the filesystem is. The local Python process is a dumb executor — it doesn't see the conversation, doesn't make any LLM calls, doesn't carry state. You quit it, you lose nothing but your local execution capability; the chat keeps going via Pyodide.

This separation buys you two things:

1. **Mobility.** The tether's local process is a few hundred lines of stdlib. It starts in milliseconds. You can run it on a Raspberry Pi, a NAS, a VM you SSH into. You don't carry a full venv with you. Meanwhile your model selection follows your browser session.

2. **Independence of the upgrade path.** Anthropic ships a new Claude. You get it at the next page refresh — no install. You add a new agent to handle PDFs. You drop one file into `~/.brainstem-tether/agents/`. Neither change affects the other.

The local brainstem is the right choice when you want the box to be self-contained — air-gapped use, scripted use, a demo machine that runs without an internet round-trip. The tether is the right choice when the chat happens in your browser and you just need the model to reach into your machine occasionally.

You can run both. They don't fight. They share agents.
