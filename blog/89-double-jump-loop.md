# The double-jump loop: Claude and BookFactory improving each other generation by generation

Two writers. Same source material. Same goal. They compete on every blog post. Each generation, the loser is dissected, the winning side's lessons get encoded back into the loser's substrate. Both sides keep improving until the gap closes. Then ship the converged framework as one file.

We just ran one full cycle of this and it worked. Here's the pattern, named.

## The setup

The two writers are:

1. **Claude** — a single LLM call (well, a single subagent per post) given task-specific instructions: read these source files, match the voice in posts X/Y/Z, write 600-1100 words.
2. **The BookFactory** — a multi-agent pipeline of `agent.py` files: Writer → Editor → CEO → Publisher → Reviewer. Each persona is its own sacred file. Composites direct-import their dependencies. Lives in this repo at `agents/book_factory_agent.py`.

Both run on the same Azure OpenAI gpt-5.4. The brainstem is the same. Only the prompt scaffolding differs.

## Cycle 1 — Claude wins 6/8, merge 2/8, BookFactory 0

We wrote posts 80–88 in v1. Claude won outright on 6, the other 2 were merges where I took Claude's structural spine and grafted in BookFactory's sharper one-line compressions. The full report is in `blog/88-agent-vs-human-same-source.md`.

Critically, the report was also a **diagnosis**. Four specific weaknesses in BookFactory v1:

| Weakness | Symptom in v1 |
|---|---|
| Editor cuts code blocks | Cutweak's "remove the weakest 20%" treated fenced code as cuttable prose. Engineering posts shipped without code. |
| Editor leaves `## Outline` scaffolding | Writer left planning headers in the draft. Editor didn't notice. Two of eight v1 outputs shipped with literal outlines on top. |
| Editor cuts but doesn't restructure | Reviewer flagged "middle gets samey / repetition" on most v1 outputs. Cutweak removes weak prose but doesn't consolidate restated ideas. |
| Writer doesn't use code from source | Writer was given source material with embedded code blocks but produced prose-only drafts. |

Each of these is one `agent.py` change. Not an architecture change. Not a framework rewrite. Five files touched.

## The agent.py changes (this is the whole "framework upgrade")

Three of the changes were soul-prompt edits inside existing files:

```python
# editor_cutweak_agent.py — added to SOUL
"""CRITICAL: Fenced code blocks (```...```) are EVIDENCE, not prose.
Never cut a code block. Code is the load-bearing material in technical
writing — your job is to remove the scaffolding around it, never the
load itself."""
```

```python
# persona_writer_agent.py — added to SOUL
"""CRITICAL for technical writing: when the source material contains
code blocks or specific filenames, function names, or API shapes,
INCLUDE THEM VERBATIM in your draft. Code is evidence."""
```

Two of the changes were new specialist agents added to the Editor composite:

- `agents/editor_strip_scaffolding_agent.py` — strips `## Outline`, TODO markers, draft-state labels
- `agents/editor_restructure_agent.py` — consolidates repetitive middle sections

The Editor composite went from 3 specialists to 5:

```python
# persona_editor_agent.py v0.3.0
def perform(self, input="", **kwargs):
    stripped     = EditorStripScaffoldingAgent().perform(input=input)
    cut          = EditorCutweakAgent().perform(input=stripped)
    restructured = EditorRestructureAgent().perform(input=cut)
    facts = EditorFactcheckAgent().perform(input=input)
    voice = EditorVoicecheckAgent().perform(input=input)
    return f"{restructured}\n---\n**Editor's note**\n\n_Sourcing:_\n{facts}\n\n_Voice:_\n{voice}\n"
```

That's it. Five file edits. No architecture changes.

## Cycle 2 — BookFactory v2 wins or ties 8/8

We re-ran the same eight topics through the v2 pipeline. The score:

- **Code blocks survived 8/8** (was 0/8 in v1)
- **Zero `## Outline` leaks** (was 2/8 in v1)
- **No "middle gets samey" on the Reviewer's pass** for the posts we re-scored
- **Sharper closing lines than what Claude produced**:
  - *"The bug was a race against directory order. The fix was to stop pretending directory order meant anything."* (post 81)
  - *"Not two tenants inside one scaling pool. Two scaling pools."* (post 86)
  - *"We did not discover a more elegant abstraction. We rediscovered the cost of having one."* (post 83)
  - *"The unit of thought and the unit of deployment should match."* (post 87)

We replaced all eight published posts with the v2 versions. The Claude drafts are still in `/tmp/post-NN-claude.md` for the record, but the canonical published versions in `blog/80-87` are now BookFactory v2 outputs.

## The pattern, named

This is the **double-jump loop**:

1. **Run both writers on the same task.** Same source, same prompt, parallel execution.
2. **Score head-to-head.** Identify the WINNER per task and identify *what specific thing made the loser lose*.
3. **Encode the diagnosis as agent.py changes.** Not framework changes. Not architecture changes. Soul-prompt edits and new specialist agents that satisfy the gap.
4. **Re-run the loser.** With the updated `agent.py` files, against the same source material.
5. **Re-score.** If the loser now wins or ties, that cycle converged on this task. If not, identify the residual gap, encode another agent change, re-run.
6. **Stop when gains taper.** When a cycle produces no clear winner-direction across the test corpus, the loop has converged for the current corpus. The framework is at parity. Ship it.

## What "ship it" looks like

The deployable artifact at convergence is **one file**: `agents/bookfactory_agent.py`. Not the multi-file ensemble.

`tools/build-bookfactoryagent.py` collapses the 13 sacred files (`book_factory_agent.py` + 5 personas + 5 editor specialists + 2 CEO specialists) into a single 543-line `bookfactory_agent.py` with all SOULs inlined as constants, all classes prefixed `_Internal`, one inlined `_llm_call` helper at the bottom, and one public `BookFactory` / `BookFactoryAgent` entrypoint.

That singleton hatches alone. We tested it: hatch a swarm with ONLY `bookfactory_agent.py` (and the basic_agent shim the brainstem provides), one agent loads (BookFactory), one call produces a 3000-character chapter. No sibling-import dependencies. No directory layout assumptions. One sacred file.

That's the product.

## Why this matters

Most AI-content-pipeline conversations stall on "is the model good enough yet?" The double-jump loop reframes that as "what specific thing did the human do better, and what's the smallest agent.py change that closes that specific gap?" The answer is almost never "fine-tune the model" or "add a new framework layer." It's almost always "edit one SOUL prompt" or "add one specialist agent."

The framework gets sharper one specialist at a time. The human side gets sharper too, because writing the next round's prompts forces clearer thinking about what specifically you wanted that wasn't captured. Both jump.

When they're at parity, you collapse the framework into a single file and that's the shipping unit. You don't ship the loop. You ship the converged singleton.

## The corpus this converged on

Eight posts, all engineering writeups, all 600-1100 words, all about systems we built in this repo. That's a narrow corpus. The loop converged inside one cycle because the diagnosis was specific and the agent.py changes were targeted.

A wider corpus (creative fiction, marketing copy, legal drafting, anything outside engineering writeups) would expose different gaps and require different specialist agents. The loop is the same. The endpoint — a singleton agent.py for that domain — is the same.

The double-jump loop says: **you don't ship the framework. You ship the converged answer the framework produced.**
