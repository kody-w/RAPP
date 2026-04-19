# The rapplication — the unit of converged AI workflow

For months we shipped agents. Then swarms. Then clouds. Then twins. Each layer earned its name by being the smallest thing that could carry that scale of intent. We had a hierarchy and we had a stack — what we did not have was a word for *the thing a user actually pulls down and runs*.

Now we do. We call it a **rapplication**: a RAPP application. One file. One drop-in. The converged output of the double-jump loop, sitting in `store/index.json` waiting to be installed.

This post names it, points at the first one, and explains why the singleton form matters more than the elegant multi-file form it came from.

**What a rapplication is:**

A rapplication is a single-file `agent.py` that contains an entire converged ensemble inlined into itself. It implements the same `BasicAgent` contract as any leaf agent, exposes the same `__manifest__`, hot-loads via the same brainstem mechanism. From the runtime's point of view, it is just an agent. From the author's point of view, it is the published form of a multi-file pipeline that has stopped iterating.

The first one lives at `agents/bookfactory_agent.py`. 543 lines. 24,779 bytes. SHA-256 `e4cc1cd9...`. Its catalog entry in `store/index.json` looks like this:

```json
{
  "id": "bookfactoryagent",
  "name": "BookFactory",
  "version": "0.3.0",
  "manifest_name": "@rapp/book-factory-singleton",
  "singleton_filename": "bookfactory_agent.py",
  "singleton_lines": 543,
  "singleton_bytes": 24779,
  "produced_by": {
    "method": "double-jump-loop",
    "cycles": 3,
    "source_files_collapsed": 13
  }
}
```

Thirteen files collapsed to one. That collapse is what makes it a rapplication.

**The unit hierarchy, named end-to-end:**

| Tier | Unit | What it is |
|---|---|---|
| L0 | `agent.py` | A sacred single file with one `BasicAgent` subclass and a SOUL |
| L1 | swarm | A hatched ensemble of agents inside one workspace, mid-flight |
| L2 | cloud | A tenant-scoped runtime hosting multiple swarms |
| L3 | twin | A persisted identity that occupies one or more clouds |

A rapplication is a special L0. It looks like an agent. It registers like an agent. It hot-loads like an agent. But internally it carries a hatched ensemble that has been frozen into its body. The `BookFactory` class at the bottom of `bookfactory_agent.py` is the public face. Above it sit ten `_Internal*` classes — `_InternalPersonaWriter`, `_InternalEditorCutweak`, `_InternalCEORisk`, the rest — prefixed specifically to hide them from the brainstem's `*Agent` discovery rule. Only `BookFactoryAgent` (the alias on line 500) is visible to the runtime. The other ten are private organs.

That is the trick. A rapplication is an agent whose body happens to be a swarm.

**Why a singleton — portability beats elegance:**

The multi-file source form is the right shape for *building*. The double-jump loop iterates against it. Each persona is editable as one file. Each SOUL is a string at the top of the file you opened. Composites direct-import their dependencies. That ensemble is how `BookFactory` got from cycle 1 to cycle 3 — by us editing five files, not by us refactoring an architecture (see `blog/89-double-jump-loop.md` for the cycle-by-cycle).

The multi-file form is the wrong shape for *shipping*. A user who wants to install BookFactory does not want to clone thirteen files into the right relative directory layout, satisfy the `from agents.editor_strip_scaffolding_agent import EditorStripScaffoldingAgent` imports, hope no helper module is missing. They want one file. They want to `cat` it, `scp` it, drop it into their brainstem's `agents/` folder, and call it.

The store entry says it plainly:

> "drop the singleton .py file into your local brainstem's `agents/` dir... The file is everything — no install script, no pip, no native deps."

Portability beats elegance. The collapse pays for itself the first time someone installs a rapplication on an air-gapped server with no source tree behind it.

**The collapse tool — `tools/build-bookfactoryagent.py`:**

The collapse is mechanical, not magical. The build script (149 lines, parses the source ensemble with `ast`) does six things in order:

1. Extract every `SOUL = """..."""` constant from each leaf and rename it `_SOUL_PERSONA_WRITER`, `_SOUL_EDITOR_CUTWEAK`, etc.
2. Extract every leaf class body, rename `class FooAgent` to `class _InternalFoo`, rewrite the SOUL reference inside `perform()`.
3. Extract every composite class body, rewrite every cross-agent instantiation (`EditorCutweakAgent()` → `_InternalEditorCutweak()`).
4. Take the top-level composite (`BookFactoryAgent`) and lift it as the public `BookFactory` class — the only one without an `_Internal` prefix.
5. Inline ONE `_llm_call` + `_post` helper at the bottom (the ten leaves had identical copies; the singleton needs one).
6. Append a `class BookFactoryAgent(BookFactory): pass` alias so the brainstem's "name ends in Agent" rule still finds it.

Net delete > net add. Thirteen files of source, one file out, all the per-file LLM helper duplication gone. The output is regeneratable: edit a SOUL in the source, re-run `python3 tools/build-bookfactoryagent.py`, get a new singleton.

**Naming distinction that matters:**

There were three words floating around for the same shape and we kept conflating them. Now they have edges:

- **agent** — the sacred single-file unit. Could be a leaf (one persona, one SOUL) or a composite (one file that references its siblings via direct import). The thing the brainstem hot-loads.
- **swarm** — a hatched ensemble of agents inside a workspace, mid-flight. The form a multi-file pipeline takes while it is being iterated against by the double-jump loop. Editable, distributed across files, alive.
- **rapplication** — a converged, ship-ready singleton. The public artifact a user installs from the store. A rapplication IS an agent (same contract), but specifically one whose internal multi-file ensemble has been hidden behind a single collapsed file.

Every rapplication is an agent. Not every agent is a rapplication. A leaf `editor_cutweak_agent.py` is an agent — but it has nothing to collapse, so it is not a rapplication. `bookfactory_agent.py` is a rapplication because something multi-file got collapsed into it.

**The first published one:**

`bookfactoryagent` is rapplication #1. Five-persona content pipeline (Writer → Editor [3 specialists] → CEO [2 specialists] → Publisher → Reviewer). 8 LLM calls per invocation, 75-second p50 wall time, 3 double-jump cycles to converge. The catalog entry lists 13 source files collapsed and a 0.625 cycle-3 corpus win rate against single-LLM baselines. One call, one chapter back.

**The doctrine, in two lines:**

The double-jump loop is how you BUILD a rapplication. The RAPPstore is how you SHIP one.

Author the multi-file source. Iterate it cycle by cycle until the loser stops losing. Run the collapse tool. Add an entry to `store/index.json`. The singleton sitting at the URL in that entry is now installable by anyone with a brainstem and a file copy command. That is the unit of converged AI workflow — the smallest object that carries *a finished pipeline* across the wire.

We did not invent the agent. We did not invent the bundle. We named the in-between thing — the converged singleton that an agent author hands to an agent user — and that name is *rapplication*.

One file. Same contract. Whole pipeline inside.
