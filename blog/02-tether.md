# Browser AI + local hardware via tether

The virtual brainstem at `kody-w.github.io/RAPP/brainstem/` is a complete chat surface — GitHub Copilot models, agent calling, memory, holo cards, registries — and it runs entirely in the browser. Pyodide does the Python execution in-page.

Pyodide is great at one thing and bad at another. It can run agent code that's pure Python — math, string parsing, schema validation, prompt assembly. It can't touch the local filesystem, spawn subprocesses, hit the LAN, talk to a database, or read from a USB device. The browser sandbox isn't going to grant any of that, ever, for very good reasons.

The tether closes the gap with about 200 lines of stdlib Python:

```bash
curl -fsSL https://kody-w.github.io/RAPP/install-tether.sh | bash
# or
python tether/server.py
```

The server loads every `*_agent.py` from `./agents`, exposes two endpoints:

- `GET /tether/healthz` → `{agents: [names], count, host}`
- `POST /tether/agent` → `{name, args}` runs `agent.perform(**args)`, returns the output

CORS is whitelisted for `https://kody-w.github.io` and localhost. Crucially, it sets `Access-Control-Allow-Private-Network: true` — a Chrome-specific header required since 2022 for `https://` pages to call `http://localhost`.

In the virtual brainstem's Settings panel, you flip on "Tether to local brainstem" and paste the URL. The header lights up with a `⚡ Tethered · N local agents` pill and the agent dispatch order becomes:

1. **Tether** (if connected and the agent name is exported)
2. **Live** (Pyodide in-browser)
3. **Stub** (synthesized output for offline)

Tether failures fall through silently — a 404 or timeout doesn't surface as a chat error, it just routes to the next executor. The user gets an answer either way.

Why this matters: the AI lives in the browser (your Copilot subscription, no API keys, no install). The agents live on your machine (real Python, real OS access). Two separate concerns, separately upgraded, sharing one chat surface. You can change which model you're using by clicking a dropdown. You can change what your agents can do by editing a file in `~/.brainstem-tether/agents/`. Neither breaks the other.

The local brainstem (full Flask + venv stack) is one mental model: AI runs locally, agents run locally. Tether is the other: AI runs in the browser, agents run locally. You install whichever fits your situation. Same agents work in both.

The smallest meaningful bridge between a sandboxed AI and the host machine is HTTP + JSON + CORS. We didn't need WebSockets, message queues, native messaging extensions, or a VPN. We needed one stdlib server and the right preflight header.
