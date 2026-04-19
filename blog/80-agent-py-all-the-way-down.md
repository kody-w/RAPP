# agent.py all the way down

The request hits the old path:

```python
POST /api/swarm/{guid}/agent  {"name":"BookFactory","args":{...}}
```

On the other side of that call sits one file, `book_factory_agent.py`. No workflow engine wakes up. No pipeline DSL gets parsed. The file just imports five other `agent.py` files by name — `PersonaWriterAgent`, `PersonaEditorAgent`, `PersonaCEOAgent`, `PersonaPublisherAgent`, `PersonaReviewerAgent` — and calls them in order. A chapter comes back as a string. Along the way, the agent drops artifacts into a workspace directory so a snapshot can catch the whole assembly line mid-motion.

The top-level composite says so in plain English. In `book_factory_agent.py`, the docstring almost reads like a manifesto:

```python
"""
book_factory_agent.py — top-level composite for the digital twin book factory.

Direct-imports each persona agent.py and runs them in order. No pipeline DSL,
no orchestrator endpoint, no special step kinds. Just one agent.py whose
perform() does Python function calls on other agent.py files.
"""
```

That “just one agent.py” line matters. Many systems become harder to reason about as they become more reusable. This one tries to hold the line. A composite is still a file you can `cat`. You do not need a second mental model for orchestration. The same `BasicAgent` contract applies at every layer: top-level book factory, mid-level editor persona, low-level specialist.

The editor shows how that pattern scales down. `persona_editor_agent.py` is itself a composite, but it does not stop being a normal agent. It imports five specialists — `EditorStripScaffoldingAgent`, `EditorCutweakAgent`, `EditorRestructureAgent`, `EditorFactcheckAgent`, `EditorVoicecheckAgent` — and runs them in order. The metadata tells you what happens before you read the code: strip scaffolding, cut weak prose while preserving code, restructure repetitive middles, then run factcheck and voicecheck for the editor’s note.

The sequence starts without ceremony:

```python
def perform(self, input="", **kwargs):
    # Sequential transformations on the prose itself
    stripped     = EditorStripScaffoldingAgent().perform(input=input)
```

The other half of the thesis is even stricter: every leaf inlines its own `_llm_call`. There is no shared utility module to hide the network boundary. Open `editor_cutweak_agent.py` and the whole unit is there: its manifest, its prompt, its `perform()`, its Azure/OpenAI fallback logic, its HTTP post.

That choice is easy to mock until you read the prompt and realize why keeping it local helps. `EditorCutweakAgent` is not a generic “LLM helper.” It is a very specific editorial behavior with a very specific constraint:

```python
SOUL = """You are a 'cut the weakest 20%' editor pass. You read prose and
return the same prose with the weakest paragraphs removed. You preserve the
writer's voice. You do not add new content. You output ONLY the cut prose,
nothing else.

CRITICAL: Fenced code blocks (```...```) are EVIDENCE, not prose. Never cut
a code block. Never abbreviate one. Never replace one with a description of
what it shows. If a paragraph is weak, cut the paragraph; if a code block
sits next to weak prose, keep the code block, cut the prose around it.
Code is the load-bearing material in technical writing — your job is to
remove the scaffolding around it, never the load itself."""
```

There are tradeoffs. Inlined `_llm_call` code means repetition. Updating an API shape may require many edits. Shared fixes do not automatically propagate. The source here does not claim those problems are solved; it simply chooses which pain to prefer. In v1.3’s thesis, portability and local legibility beat DRY purity.
