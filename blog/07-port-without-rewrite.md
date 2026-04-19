# How we ported the local brainstem to the browser without rewriting anything

The local brainstem is a Flask app. It loads `*_agent.py` files from a folder, uses Azure OpenAI or GitHub Copilot, and exposes a `/chat` endpoint. The virtual brainstem is a static HTML page on GitHub Pages. It uses GitHub Copilot via a Cloudflare Worker proxy and runs Python in Pyodide.

Two completely different architectures. Same agents.

The trick was deciding what the *unit of compatibility* would be. We picked the agent file. Specifically: a `*_agent.py` that runs against the local brainstem MUST also run, unchanged, in the virtual brainstem. No `if running_in_pyodide:` branches. No virtual-only forks. Drop a file, both surfaces use it.

Here's what that constraint forced.

**Storage shims at the top of each agent.** SaveMemory needs to persist. Locally that's a JSON file in `~/.brainstem/memory.json`. In the browser that's `window.localStorage`. The agent has both code paths, picks the available one:

```python
def _write_memory(data):
    try:
        from js import localStorage
        localStorage.setItem(_MEM_KEY, json.dumps(data))
        return
    except Exception:
        pass
    import os
    path = os.path.expanduser("~/.brainstem/memory.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
```

`from js import localStorage` raises ImportError on real Python, succeeds on Pyodide. One try/except, two backends.

**HTTP through whatever's available.** The HackerNews agent fetches from Firebase. In Pyodide, `urllib.request` can't reach the network because there's no network stack. The agent tries `pyodide.http.open_url` first, falls back to `urllib.request`:

```python
try:
    from pyodide.http import open_url
    return json.loads(open_url(url).read())
except Exception:
    pass
import urllib.request
with urllib.request.urlopen(url, timeout=10) as r:
    return json.loads(r.read().decode("utf-8"))
```

Same agent. Two networking layers. The agent decides.

**Tool schema parsed identically on both sides.** The local brainstem inspects `agent.metadata` at runtime to build the OpenAI tools array. The virtual brainstem can't import the agent (no Python), so we wrote a JS-side text parser that extracts `__manifest__` and `self.metadata = {...}` from the source code by brace-matching, then converts the Python dict literal to JSON. It handles `self.name` substitution and Python's implicit string concatenation. (Imperfect — see post #21.) Same shape comes out.

**Same system prompt structure.** Both surfaces use the OG `<identity> <agent_usage> <shared_memory_output> ...` XML format. Memory is read at chat time from the same key on both surfaces.

What we did NOT do: rewrite agents in JavaScript. Build a transpiler. Maintain two parallel agent libraries. Force users to choose a runtime upfront.

The result: the same `hacker_news_agent.py` runs on a Mac mini, in a Linux VPS, and in a phone browser. We didn't port the brainstem. We made the agent file portable, and the brainstems became implementations of the same contract.

The lesson is something like: when you have two runtimes, don't unify them, unify their inputs. Make the input file legal for both. The runtimes can stay weird.
