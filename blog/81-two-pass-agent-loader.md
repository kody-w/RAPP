# The two-pass agent loader

A composite agent lands in a swarm directory. Its filename is ordinary enough: `persona_editor_agent.py`. Open it, though, and you can see the trap immediately. Before anything runs, while Python is still defining the module, it reaches sideways for five sibling agents:

```python
from agents.basic_agent import BasicAgent
from agents.editor_strip_scaffolding_agent import EditorStripScaffoldingAgent
from agents.editor_cutweak_agent           import EditorCutweakAgent
from agents.editor_restructure_agent       import EditorRestructureAgent
from agents.editor_factcheck_agent         import EditorFactcheckAgent
from agents.editor_voicecheck_agent        import EditorVoicecheckAgent
```

That is not a runtime dependency tucked safely inside a method. It is a class-definition-time dependency. If `editor_cutweak_agent.py` has not been imported yet, `persona_editor_agent.py` does not merely limp along. It blows up on import.

That was the bug.

The fix starts by making the import path real. The loader injects an `agents` package into `sys.modules`, then loads a vendored `agents.basic_agent` shim so every per-swarm file can import the same base class.

Then comes the key move. The loader imports each file under two names at once: a swarm-unique module name, and a shared `agents.<stem>` name for sibling imports. The code says exactly what it is doing:

```python
# Two-pass load:
#   Pass 1 — import every module and register it under both
#            `swarm_<guid>_<stem>` (per-swarm unique) AND
#            `agents.<stem>`     (so composite agents can do
#                                  `from agents.editor_cutweak_agent
#                                   import EditorCutweakAgent`)
#   Pass 2 — instantiate the *Agent classes. Defers instantiation
#            so a composite's dependencies are all in sys.modules
#            before its class body executes. Some composites import
#            specialists at class-definition time; passing twice
#            avoids glob-order accidents.
```

For each file, the loader creates a module object, places it in `sys.modules` as both `swarm_<guid>_<stem>` and `agents.<stem>`, and only then calls `spec.loader.exec_module(mod)`.

The retry logic is the real second pass. On the first sweep, any exception gets recorded as “import deferred.” Then the loader loops back over the misses and re-executes them after the rest of the directory has had a chance to populate `sys.modules`. This is how a bad glob order stops mattering. The first pass builds the map; the second pass takes another shot at the modules that arrived too early.

Only after that does the loader instantiate classes:

```python
# Pass 3: instantiate every *Agent class
for path, mod in loaded_mods:
    if mod is None: continue
    for attr in dir(mod):
        cls = getattr(mod, attr)
        if not isinstance(cls, type):
            continue
        if attr.endswith("Agent") and attr != "BasicAgent":
            try:
                inst = cls()
```

So despite the chapter title, the finished design is really three stages: seed the import namespace, retry deferred imports, then instantiate agent classes. The “two-pass” idea survives because the core bug was about loading modules in a dependency-tolerant way before object construction began.

The failure here was specific. The composite was not abstractly “coupled.” It imported real siblings by real names — `EditorCutweakAgent`, `EditorRestructureAgent`, `EditorFactcheckAgent`. The loader fix met that reality head-on. It did not ask authors to rewrite composites or move imports into functions. It taught the loader to honor the shape of the code already being written.

The bug was a race against directory order. The fix was to stop pretending directory order meant anything.
