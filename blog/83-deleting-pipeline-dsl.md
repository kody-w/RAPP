# Deleting the pipeline DSL we just built

The route was already there.

You could `POST /api/pipeline/run`. You could describe work as step kinds in a JSON DSL. There was a resolver to figure out dependencies, transcripts to explain what happened, and a coherent story about orchestration.

Then we deleted it.

What survived is much more direct. In `book_factory_agent.py`, the top-level composite says exactly what it does:

```python
"""
book_factory_agent.py — top-level composite for the digital twin book factory.

Direct-imports each persona agent.py and runs them in order. No pipeline DSL,
no orchestrator endpoint, no special step kinds. Just one agent.py whose
perform() does Python function calls on other agent.py files.

Run via the existing path:
    POST /api/swarm/{guid}/agent  {"name":"BookFactory","args":{...}}
"""
from agents.persona_writer_agent    import PersonaWriterAgent
from agents.persona_editor_agent    import PersonaEditorAgent
from agents.persona_ceo_agent       import PersonaCEOAgent
from agents.persona_publisher_agent import PersonaPublisherAgent
from agents.persona_reviewer_agent  import PersonaReviewerAgent
```

Each of those features had introduced a second thing to understand. Not just the writer persona, but the writer persona as a pipeline step. Not just sequencing, but sequencing expressed through JSON. Not just calling code, but resolving code through an abstraction layer. We had built machinery around the work, and over time the machinery started competing with the work for attention.

The commit history tells the story in reverse. We kept adding layers:

- `223fd1e` — Twin Stack v1: hatch page, T2T, hippocampus brainstem-in-the-cloud
- `f423108` — Twin Stack v1.1: simulator, workspaces, doc share, mobile PWA
- `60cb9ff` — Twin Stack v1.2: tether bridge, book factory, one-command launcher
- `25dc659` — Twin Stack v1.3: agent.py all the way down + .egg snapshots
- `412ece4` — Book factory click-and-watch HTML — one-page demo

What replaced it was smaller, and therefore easier to inspect and maintain. Each persona became its own `agent.py`. Composite agents stopped declaring dependencies and started importing them. The BookFactory orchestrator became a normal Python function call chain. If you wanted to know what ran first, you opened one file. If you wanted to change the order, you edited one file. If it broke, the stack trace pointed to code you owned.

The surviving `perform()` method is plain about its priorities:

```python
def perform(self, source="", chapter_title="Untitled chapter",
            author="@rapp", workspace=None, **kwargs):
    ws = workspace or os.environ.get("TWIN_WORKSPACE") or "/tmp/book-factory"
    os.makedirs(ws, exist_ok=True)

    def save(name, content):
        path = os.path.join(ws, name)
        with open(path, "w") as f:
            f.write(content if isinstance(content, str) else str(content))
        return path

    save("00-source.md", source)
```

The important thing we did not lose was composability. We changed where composability lives. Instead of a general-purpose orchestration layer, we put it in Python itself: imports, function calls, files, arguments. The system still composes; it just does so in a medium every engineer on the project can already read.

This was not a reversal for its own sake. It was a simplification in service of reliability. The user request stayed the same. The path to fulfilling it got shorter, clearer, and easier to debug.

The user’s request was more reliable than our guesses: less moving parts.

That is the whole postmortem, really. We did not discover a more elegant abstraction. We rediscovered the cost of having one.
