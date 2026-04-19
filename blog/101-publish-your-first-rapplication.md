# Publish your first rapplication — a 5-minute tutorial

You have a composite agent that works. It survived your test corpus, it beats a one-shot Claude on the prompts you care about, and the multi-file source under `agents/` is starting to feel like something other people would want. This post is the runway from "works on my brainstem" to "anyone in the world can `curl` it down and drop it in their own."

The path is ten steps. Each command is copy-pasteable. We will use a tiny three-file ensemble — one composite, two leaves — so you can see every move without a wall of code. The canonical reference is the BookFactory build at `tools/build-bookfactoryagent.py`; once you are done here, that file will read like a slightly larger version of what you just wrote.

## 1. Author the multi-file source

Every rapplication starts as plain RAPP agents — one composite that calls N specialists. The minimum that proves the pattern is one composite plus two leaves. Make the directory:

```bash
mkdir -p ~/my-rapp/agents && cd ~/my-rapp
```

You will end up with three files in `agents/`: `greeting_summarizer_agent.py` (the composite), `greeting_writer_agent.py` (leaf 1), and `greeting_critic_agent.py` (leaf 2). Pretend it is the BookFactory pipeline shrunk down to two personas.

## 2. Write the leaves

Each leaf extends `BasicAgent`, holds a `SOUL` constant, and inlines its own `_llm_call` helper. No shared util module — that is the whole point. Cat any one file and you have the unit of share.

```bash
cat > agents/greeting_writer_agent.py <<'PY'
from agents.basic_agent import BasicAgent
import json, os, urllib.request, urllib.error

SOUL = """You are a warm greeter. Given a name and an occasion, write
one heartfelt sentence. No filler. No emoji unless asked."""

class GreetingWriterAgent(BasicAgent):
    def __init__(self):
        self.name = "GreetingWriter"
        self.metadata = {"name": self.name, "description": "Drafts a one-line greeting.",
            "parameters": {"type": "object",
                "properties": {"who": {"type": "string"}, "occasion": {"type": "string"}},
                "required": ["who"]}}
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, who="friend", occasion="hello", **kwargs):
        return _llm_call(SOUL, f"Write one greeting line for {who}. Occasion: {occasion}.")

def _llm_call(soul, user):
    msgs = [{"role":"system","content":soul},{"role":"user","content":user}]
    if os.environ.get("OPENAI_API_KEY"):
        return _post("https://api.openai.com/v1/chat/completions",
            {"model": os.environ.get("OPENAI_MODEL","gpt-4o"), "messages": msgs},
            {"Content-Type":"application/json","Authorization":"Bearer "+os.environ["OPENAI_API_KEY"]})
    return "(no LLM configured)"

def _post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            j = json.loads(r.read().decode("utf-8"))
        return (j.get("choices") or [{}])[0].get("message",{}).get("content","")
    except Exception as e:
        return f"(LLM error: {e})"
PY
```

Now write `agents/greeting_critic_agent.py` the same way — same shape, different SOUL:

```bash
cat > agents/greeting_critic_agent.py <<'PY'
from agents.basic_agent import BasicAgent
import json, os, urllib.request, urllib.error

SOUL = """You are a kind editor. You take a greeting line and either return
it unchanged, or return one tightened version. Output ONLY the final line."""

class GreetingCriticAgent(BasicAgent):
    def __init__(self):
        self.name = "GreetingCritic"
        self.metadata = {"name": self.name, "description": "Tightens a greeting line.",
            "parameters": {"type":"object",
                "properties": {"input": {"type":"string"}},
                "required": ["input"]}}
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, input="", **kwargs):
        return _llm_call(SOUL, f"Greeting:\n{input}\n\nReturn the final line, nothing else.")

# Same _llm_call + _post — paste them verbatim. Sacred copy.
def _llm_call(soul, user):
    msgs = [{"role":"system","content":soul},{"role":"user","content":user}]
    if os.environ.get("OPENAI_API_KEY"):
        return _post("https://api.openai.com/v1/chat/completions",
            {"model": os.environ.get("OPENAI_MODEL","gpt-4o"), "messages": msgs},
            {"Content-Type":"application/json","Authorization":"Bearer "+os.environ["OPENAI_API_KEY"]})
    return "(no LLM configured)"

def _post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            j = json.loads(r.read().decode("utf-8"))
        return (j.get("choices") or [{}])[0].get("message",{}).get("content","")
    except Exception as e:
        return f"(LLM error: {e})"
PY
```

Two files, two SOULs, two inlined LLM helpers. Resist the urge to dedupe.

## 3. Write the composite

The composite direct-imports its leaves and calls each `.perform()` in sequence. It has no SOUL of its own — it orchestrates. Look at `agents/persona_editor_agent.py` for the canonical version; ours is the toy:

```bash
cat > agents/greeting_summarizer_agent.py <<'PY'
from agents.basic_agent import BasicAgent
from agents.greeting_writer_agent import GreetingWriterAgent
from agents.greeting_critic_agent import GreetingCriticAgent

class GreetingSummarizerAgent(BasicAgent):
    def __init__(self):
        self.name = "GreetingSummarizer"
        self.metadata = {"name": self.name,
            "description": "Writer + Critic in sequence. Source in, polished line out.",
            "parameters": {"type":"object",
                "properties": {"who":{"type":"string"}, "occasion":{"type":"string"}},
                "required": ["who"]}}
        super().__init__(name=self.name, metadata=self.metadata)

    def perform(self, who="friend", occasion="hello", **kwargs):
        draft = GreetingWriterAgent().perform(who=who, occasion=occasion)
        final = GreetingCriticAgent().perform(input=draft)
        return final
PY
```

## 4. Drop them in a brainstem

You already have a brainstem of some shape — local Flask, Pyodide tab, or the stdlib swarm server. The drop-in is identical for all three. From your repo root:

```bash
cp agents/greeting_*.py /path/to/your-brainstem/agents/
```

Restart whichever runtime you use. The loader globs `*_agent.py` and instantiates everything that ends in `Agent`.

## 5. Hatch a swarm and call the composite

If you are using the swarm server, deploy a bundle and call your top class:

```bash
python3 swarm/server.py --port 7080 --root /tmp/my-rapp &
GUID=$(curl -s -X POST http://127.0.0.1:7080/api/swarm/deploy \
  -H 'Content-Type: application/json' \
  -d "{\"schema\":\"rapp-swarm/1.0\",\"name\":\"greeting\",\"agents\":[
    {\"filename\":\"greeting_writer_agent.py\",\"name\":\"GreetingWriter\",\"source\":$(jq -Rs . < agents/greeting_writer_agent.py)},
    {\"filename\":\"greeting_critic_agent.py\",\"name\":\"GreetingCritic\",\"source\":$(jq -Rs . < agents/greeting_critic_agent.py)},
    {\"filename\":\"greeting_summarizer_agent.py\",\"name\":\"GreetingSummarizer\",\"source\":$(jq -Rs . < agents/greeting_summarizer_agent.py)}]}" \
  | jq -r .swarm_guid)
curl -s -X POST http://127.0.0.1:7080/api/swarm/$GUID/agent \
  -H 'Content-Type: application/json' \
  -d '{"name":"GreetingSummarizer","args":{"who":"Kody","occasion":"shipping day"}}'
```

You should see one polished line come back. End-to-end works.

## 6. Run the double-jump loop until you win

Read `blog/89-double-jump-loop.md` for the full method. The short version: take ten prompts from your test corpus, run them through your composite and through a one-shot Claude with no scaffolding, score blind. Iterate the SOULs until your composite wins or ties on at least 60% of the corpus. BookFactory took three cycles. Yours might take one. If it never converges, the composite shape is wrong — go back to step 1 and rethink the personas.

## 7. Collapse to a singleton

This is the move that turns a workspace into a rapplication. Write a tiny build script that inlines every SOUL as a constant, prefixes every leaf class with `_Internal`, and keeps your composite as the only public class. The model is `tools/build-bookfactoryagent.py` — about 200 lines that produce the converged 543-line `bookfactory_agent.py`. Yours is smaller:

```bash
mkdir -p tools && cat > tools/build-greeting-agent.py <<'PY'
#!/usr/bin/env python3
"""Collapse the greeting ensemble into one drop-in agent.py."""
from pathlib import Path
import re

REPO = Path(__file__).resolve().parent.parent
A = REPO / "agents"
OUT = A / "greetingsummarizer_agent.py"

def soul_of(stem):
    src = (A / f"{stem}_agent.py").read_text()
    return re.search(r'SOUL = """(.+?)"""', src, re.DOTALL).group(1)

writer_soul = soul_of("greeting_writer")
critic_soul = soul_of("greeting_critic")

OUT.write_text(f'''"""greetingsummarizer_agent.py — converged singleton."""
from agents.basic_agent import BasicAgent
import json, os, urllib.request, urllib.error

__manifest__ = {{
    "schema": "rapp-agent/1.0",
    "name": "@you/greeting-summarizer",
    "version": "0.1.0",
    "tags": ["singleton", "composite"],
    "example_call": {{"args": {{"who": "Kody", "occasion": "launch"}}}},
}}

_SOUL_WRITER = """{writer_soul}"""
_SOUL_CRITIC = """{critic_soul}"""

class _InternalWriter(BasicAgent):
    def __init__(self):
        super().__init__(name="W", metadata={{"name":"W","description":"x","parameters":{{"type":"object","properties":{{}}}}}})
    def perform(self, who="friend", occasion="hello", **kw):
        return _llm_call(_SOUL_WRITER, f"Write one greeting line for {{who}}. Occasion: {{occasion}}.")

class _InternalCritic(BasicAgent):
    def __init__(self):
        super().__init__(name="C", metadata={{"name":"C","description":"x","parameters":{{"type":"object","properties":{{}}}}}})
    def perform(self, input="", **kw):
        return _llm_call(_SOUL_CRITIC, f"Greeting:\\n{{input}}\\nReturn the final line.")

class GreetingSummarizerAgent(BasicAgent):
    def __init__(self):
        self.name = "GreetingSummarizer"
        self.metadata = {{"name": self.name, "description": "One-call greeting pipeline.",
            "parameters": {{"type":"object",
                "properties": {{"who":{{"type":"string"}}, "occasion":{{"type":"string"}}}},
                "required": ["who"]}}}}
        super().__init__(name=self.name, metadata=self.metadata)
    def perform(self, who="friend", occasion="hello", **kw):
        draft = _InternalWriter().perform(who=who, occasion=occasion)
        return _InternalCritic().perform(input=draft)

def _llm_call(soul, user):
    msgs = [{{"role":"system","content":soul}},{{"role":"user","content":user}}]
    if os.environ.get("OPENAI_API_KEY"):
        return _post("https://api.openai.com/v1/chat/completions",
            {{"model": os.environ.get("OPENAI_MODEL","gpt-4o"), "messages": msgs}},
            {{"Content-Type":"application/json","Authorization":"Bearer "+os.environ["OPENAI_API_KEY"]}})
    return "(no LLM configured)"

def _post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return (json.loads(r.read().decode("utf-8")).get("choices") or [{{}}])[0].get("message",{{}}).get("content","")
    except Exception as e:
        return f"(LLM error: {{e}})"
''')
print(f"wrote {{OUT}}")
PY
python3 tools/build-greeting-agent.py
```

Out drops `agents/greetingsummarizer_agent.py` — one file, no sibling imports.

## 8. Test the singleton standalone

The whole point is that the singleton is the unit of share. Prove it. Make a fresh empty brainstem dir, drop only the singleton, hatch, call:

```bash
mkdir -p /tmp/clean-brainstem/agents
cp agents/greetingsummarizer_agent.py /tmp/clean-brainstem/agents/
# Re-deploy a swarm with ONLY the singleton — agent_count should be 1.
# Call it the same way as step 5; output should match.
```

If the answer matches your multi-file ensemble within voice tolerance, you have a real rapplication.

## 9. Add an entry to `store/index.json`

This is the manifest the world reads. Compute the hash of your file, then add the entry:

```bash
sha256sum agents/greetingsummarizer_agent.py
# copy the hex digest
```

Open `store/index.json` and append to the `rapplications` array:

```json
{
  "id": "greetingsummarizer",
  "name": "GreetingSummarizer",
  "version": "0.1.0",
  "summary": "Writer + Critic pipeline. One name in, one polished greeting line out.",
  "manifest_name": "@you/greeting-summarizer",
  "singleton_filename": "greetingsummarizer_agent.py",
  "singleton_url": "https://raw.githubusercontent.com/you/your-fork/main/agents/greetingsummarizer_agent.py",
  "singleton_sha256": "<paste digest>",
  "example_call": {"endpoint": "POST /api/swarm/{guid}/agent",
                   "body": {"name": "GreetingSummarizer",
                            "args": {"who": "Kody", "occasion": "launch"}}}
}
```

The `singleton_url` can be a raw GitHub URL, a CDN, or anything that returns the file unchanged. The `singleton_sha256` lets the brainstem verify before loading.

## 10. Open a PR — or fork the store

Fork `kody-w/RAPP`, commit your singleton plus the `store/index.json` entry, open a PR. If the maintainer is slow or you want your own catalog, fork the store repo, host `store/index.json` on your own GitHub Pages, and tell users to point their brainstem at your URL. The schema is open. The store is just a JSON file with a list inside it.

You shipped a rapplication. Someone in another timezone can `curl` it tonight, drop it in their `agents/` directory, and use it. The unit of distribution is the file. The receipt is the hash. The catalog is the JSON. Now write the next one — it takes three minutes.
