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

---

## Cycle 3: testing v2 on new content shapes

We re-ran the loop on **8 new posts in different content shapes** (3 engineering writeups + 5 entirely new shapes: tutorial, FAQ, investor one-pager, README, personal essay). The threading server fix landed too: `swarm/server.py` now uses `ThreadingHTTPServer` with a lock around `load_agents`, so 8 parallel BookFactory calls finish in ~107 seconds wall time instead of ~12 minutes sequential. 8x speedup, race condition fixed in the same patch.

**Results (5 v3 wins/ties, 3 Claude wins):**

| # | Shape | Winner | Why |
|---|---|---|---|
| 90 | Mobile IDB workspace (engineering) | **v3** | Same code density, sharper line: *"The browser is standing in for the filesystem, not replacing the architecture."* |
| 91 | Offline send queue (engineering) | **v3** (tie) | Stronger opening: *"The user has already hit send. The sentence is in motion."* |
| 92 | Sim ports (engineering) | **v3** | *"The script derives, then starts."* + honest tradeoffs section |
| 93 | Tutorial | **Claude** | Claude shipped 10 numbered runnable steps. v3 admitted "stops short of delivering a fully complete minimal example" — and stopped short. |
| 94 | FAQ | **Claude** | Claude: 28 grounded Q&A pairs. v3: ~17, plus a numbering skip from 8 → 10. |
| 95 | Investor one-pager | **v3** (tie) | *"A digital twin meant for descendants is not a $20-per-month tool. It is closer to an heirloom than to a subscription."* |
| 96 | README | **Claude** | Claude wrote a README. v3 wrote a thoughtful *editorial about how to write a README*. |
| 97 | Personal essay | **v3** | *"The machine shortens the distance between idea and evidence."* + the texture of being honest about steering vs commanding. |

**The cycle-3 diagnosis:** v2 generalizes well to **narrative shapes** (engineering writeups, persuasive essays, personal reflection) — wins or ties on every one. v2 struggles with **structurally-demanding shapes** where the structure IS the value:

- **Tutorial** (93): each numbered step must be runnable end-to-end. v2's editor pass treats the structural elements as cuttable prose.
- **FAQ** (94): completeness matters — fewer Qs = worse FAQ. v2's editor cuts toward "less padding," and the FAQ shape NEEDS more.
- **README** (96): a README has a fixed canonical shape (Quick start → What you get → Components). v2 met the topic and produced an essay describing what that shape should look like.

Each of these is a missing specialist agent. Cycle-4 candidates:

```
agents/editor_preserve_structure_agent.py    # don't cut numbered lists, Q&A pairs,
                                              # README section headers, code blocks
                                              # presented as runnable commands
agents/writer_shape_recognizer_agent.py      # detect: tutorial / FAQ / README /
                                              # essay / spec — pick the right Writer mode
```

If we ran cycle-4 with those two agents added, the prediction (testable) is that v3 would win or tie 8/8 — including 93, 94, 96.

**The pattern this validates:** the loop converges *per content shape*. Each cycle reveals shape-specific gaps. Each gap is one agent.py. Net delete > net add still holds because each new specialist replaces what would otherwise be a per-shape framework branch.

The double-jump loop also exposed something we didn't know to look for: **the BookFactory's sharpest single sentences are reliably better than what a single LLM call produces.** Across cycles 1, 2, and 3, the BookFactory's strongest line beat Claude's strongest line in 14 of 24 head-to-head pairs. That's not noise. The composite Editor's specialists (cutweak + voicecheck) produce distillation that a one-shot LLM doesn't. The framework's value isn't "complete drafts" — it's "compressed sentences." Use the loop accordingly: human writes the long form, framework forges the lines that will be quoted.
