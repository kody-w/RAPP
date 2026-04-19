# Your first agent.py — a tutorial

You are going to write an agent, drop it into a brainstem, hatch a swarm, and call it over HTTP. About five minutes, end to end.

The contract fits in your head: one Python file that extends `BasicAgent`, sets a `name`, sets a `metadata` dict, and implements `perform(**kwargs)`. That is all the runtime asks. Everything else here is plumbing you learn once.

## 1. The fifteen-line skeleton

Every agent has the same four pieces:

- `from agents.basic_agent import BasicAgent` — the only framework import.
- `self.name` — the OpenAI tool name. The model calls it by exactly this string.
- `self.metadata` — `{name, description, parameters}`. `parameters` is a JSON Schema the model reads to know what arguments to pass.
- `perform(**kwargs)` — does the work, returns a string. Plain text or JSON-as-text. The brainstem does not care.

Read `agents/basic_agent.py` if you want — it is six lines and a default `perform` that returns `"Not implemented."`. You override that. Here it is, ready to paste in the next step:

## 2. Save it as `agents/hello_agent.py`

From the repo root, write the skeleton to disk:

```bash
cat > agents/hello_agent.py <<'PY'
from agents.basic_agent import BasicAgent


class HelloAgent(BasicAgent):
    def __init__(self):
        self.name = "Hello"
        self.metadata = {
            "name": self.name,
            "description": "Says hello to whoever you point it at.",
            "parameters": {
                "type": "object",
                "properties": {"who": {"type": "string"}},
                "required": ["who"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, who="world", **kwargs):
        return f"Hello, {who}."
PY
```

The filename must end in `_agent.py`. The loader globs for `*_agent.py` and skips anything else. That is the only naming rule.

## 3. Drop it into a brainstem

Start the swarm server. Stdlib only:

```bash
python3 swarm/server.py --port 7080 --root /tmp/my-rapp
```

You should see:

```
  RAPP Swarm Server
  ────────────────────────────────────
  Root: /tmp/my-rapp
  Swarms loaded: 0

  Listening on  http://127.0.0.1:7080
```

Leave it running. Open a new terminal for the rest.

## 4. Hatch a swarm via `curl`

A swarm is a bundle of agents posted as JSON to `/api/swarm/deploy`. Build one with your hello agent and post it:

```bash
python3 - <<'PY' | curl -s -X POST http://127.0.0.1:7080/api/swarm/deploy \
    -H 'Content-Type: application/json' --data-binary @-
import json
source = open("agents/hello_agent.py").read()
print(json.dumps({
    "schema": "rapp-swarm/1.0",
    "name": "Hello Swarm",
    "purpose": "Demo swarm with one agent.",
    "agents": [{
        "filename": "hello_agent.py",
        "name": "Hello",
        "description": "Says hello.",
        "source": source,
    }],
}))
PY
```

The server replies with `{"status": "ok", "swarm_guid": "f3a1...", "swarm_url": "...", "agent_count": 1}`. Save the GUID:

```bash
export GUID=f3a1...c0   # paste the swarm_guid from the response
```

## 5. Call your agent

`POST /api/swarm/{guid}/agent` is the wire. Body is `{"name": <agent name>, "args": <kwargs>}`:

```bash
curl -s -X POST http://127.0.0.1:7080/api/swarm/$GUID/agent \
    -H 'Content-Type: application/json' \
    -d '{"name": "Hello", "args": {"who": "Kody"}}'
```

## 6. Read the response

You get back exactly what `perform` returned, wrapped in an envelope:

```json
{
  "status": "ok",
  "output": "Hello, Kody.",
  "agent": "Hello"
}
```

That is the round trip. HTTP → Python → your agent → string → HTTP. No build step. No registration. The server hot-loaded `hello_agent.py` on the first call and cached the instance.

## 7. Add an LLM call

Most real agents ask a model. The RAPP pattern: inline the LLM call into the agent file. No shared client, no DI container. The same helper goes in every leaf agent that needs a model.

This `_llm_call` helper is sacred. It is copied verbatim from `agents/editor_cutweak_agent.py`. Do not refactor it. Do not import it. Paste it.

```python
from agents.basic_agent import BasicAgent
import json, os, urllib.request, urllib.error


SOUL = "You are a friendly greeter. Reply with a one-sentence hello in the style of the requested vibe."


class HelloAgent(BasicAgent):
    def __init__(self):
        self.name = "Hello"
        self.metadata = {
            "name": self.name,
            "description": "Says hello in a requested style.",
            "parameters": {
                "type": "object",
                "properties": {
                    "who": {"type": "string"},
                    "vibe": {"type": "string", "description": "e.g. pirate, formal, haiku"},
                },
                "required": ["who"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, who="world", vibe="warm", **kwargs):
        return _llm_call(SOUL, f"Greet {who}. Vibe: {vibe}.")


def _llm_call(soul, user_prompt):
    msgs = [{"role": "system", "content": soul}, {"role": "user", "content": user_prompt}]
    ep, key = os.environ.get("AZURE_OPENAI_ENDPOINT", ""), os.environ.get("AZURE_OPENAI_API_KEY", "")
    dep = os.environ.get("AZURE_OPENAI_DEPLOYMENT") or os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "")
    if ep and key:
        url = ep if "/chat/completions" in ep else ep.rstrip("/") + f"/openai/deployments/{dep}/chat/completions?api-version=2025-01-01-preview"
        if "/chat/completions" in ep and "/openai/v1/" not in ep and "?" not in url:
            url += "?api-version=2025-01-01-preview"
        return _post(url, {"messages": msgs, "model": dep},
                      {"Content-Type": "application/json", "api-key": key})
    if os.environ.get("OPENAI_API_KEY"):
        return _post("https://api.openai.com/v1/chat/completions",
                      {"model": os.environ.get("OPENAI_MODEL", "gpt-4o"), "messages": msgs},
                      {"Content-Type": "application/json",
                       "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
    return "(no LLM configured)"


def _post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            j = json.loads(r.read().decode("utf-8"))
        c = j.get("choices") or []
        return (c[0]["message"].get("content") or "") if c else ""
    except urllib.error.HTTPError as e:
        return f"(LLM HTTP {e.code}: {e.read().decode('utf-8')[:200]})"
    except urllib.error.URLError as e:
        return f"(LLM network error: {e})"
```

Save this over your existing `agents/hello_agent.py`. The agent now reads `AZURE_OPENAI_*` or `OPENAI_API_KEY` from the environment and falls back to the literal string `"(no LLM configured)"` if neither is set. Your dev environment never crashes for lack of a model.

## 8. Test it

The server caches loaded agents per swarm. To pick up the new code, restart the server or re-deploy with the `curl` from step 4. Then:

```bash
curl -s -X POST http://127.0.0.1:7080/api/swarm/$GUID/agent \
    -H 'Content-Type: application/json' \
    -d '{"name": "Hello", "args": {"who": "Kody", "vibe": "pirate"}}'
```

With keys exported, you get a pirate greeting. Without, you get `"(no LLM configured)"`. Both are correct outputs.

## 9. Add `tether_required` if you need OS access

Pyodide-hosted brainstems cannot read your disk, spawn subprocesses, or hit the LAN. If your agent needs any of that, add one flag to its manifest:

```python
__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@you/hello",
    "tier": "core",
    "trust": "community",
    "version": "0.1.0",
    "tether_required": True,
}
```

That single boolean flips the routing path. Calls go to the local tether process instead of the in-browser Pyodide runtime, and the user must opt in separately by running the tether. Capability becomes visible before the call leaves the browser. Full trust model in post 85 (`tether bridge: the agent.py decides`).

You do not need this flag for the hello agent. Reach for it the first time you call `os.listdir` or `subprocess.run`.

## 10. You shipped an agent

Recap:

- One Python file that extends `BasicAgent`.
- Hot-loaded by the swarm server, no build step.
- Hatched, called over HTTP, returned a string.
- LLM call inlined by pasting six lines verbatim.
- One flag, `tether_required`, gates real OS access.

The unit of distribution is the file. You can paste `hello_agent.py` into a Slack DM, email it, drop it on a webpage. It runs unchanged in three runtimes: this stdlib swarm server, the Pyodide brainstem in a browser tab, and the local tether process. The contract is the file. Everything else is a reader.

Now write the second one. It takes two minutes.
