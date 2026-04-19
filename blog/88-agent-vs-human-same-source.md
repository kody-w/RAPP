# Agent vs human, same source material

We just ran an experiment on ourselves.

For the last 8 blog posts in this repo — this one being the 8th — we wrote two versions of every post in parallel. One version came from Claude (a general-purpose subagent invoked with task-specific instructions). The other came from the BookFactory pipeline: an 8-LLM-call composite running on the same Azure OpenAI gpt-5.4 backend that powers every other twin in the stack. Then we scored each pair, post by post, and decided which to publish. Sometimes ours won. Sometimes the agent's won. Sometimes we shipped a manual merge of the two.

This post is the report on that.

**The setup:**

8 posts, 2 versions each, 16 drafts total. Both pipelines got the same source material — this repo's `git log`, recent commits, file diffs, and the existing 79-post blog corpus for voice reference — and the same chapter title. Nothing was hidden from either side. The only difference was the writer.

**The Claude side:**

Parallel `Agent` tool invocations against general-purpose subagents. Each call carried: (a) the post number and title, (b) 2-3 specific source files to read for facts, (c) 2-3 existing blog posts to read for voice, and (d) the post's thesis in one sentence. The subagent did its own reading, drafted in one pass, and wrote to `/tmp/post-NN-claude.md`. Wall-clock per post: ~30-60s, depending on how much the subagent decided to read.

**The agent side:**

Sequential `POST /api/swarm/{guid}/agent {"name":"BookFactory"}` calls into a swarm hosting the BookFactory composite. The composite is 8 LLM calls in series: a Writer, an Editor with three specialists (line edits, structure, fact-check), a CEO with two specialists (strategic framing, voice match), a Publisher to assemble, and a Reviewer to gate. Wall-clock per post: ~75s, almost entirely spent in sequential model latency.

Same model. Same source material. Different orchestration shape.

**What we scored:**

Four axes per post:

- **Substance.** Does the post teach something a reader can use, or is it a vibes essay?
- **Voice match.** Does it sound like the existing 79 posts — engineer's first-person plural, methods-and-results, no marketing register?
- **Concreteness.** Specific commit hashes, file paths, line counts, command invocations — or hand-wave at "the system" and "the team"?
- **Length discipline.** Did it stop when done, or pad to hit some imagined word target?

And one negative axis: **what's missing.** For each draft, what did the *other* draft have that this one didn't?

**Per-post verdict:**

| # | Title | Winner | Notes |
|---|---|---|---|
| 80 | agent.py all the way down | **Claude** | Real code blocks (5-line orchestrator, full editor_cutweak source) + the "wait — but doesn't the composite break that?" rhetorical setup. |
| 81 | Two-pass agent loader | **Claude** | BookFactory output started with a literal `## Outline` section — editor pass left scaffolding in. Lost the verbatim three-pass code blocks. |
| 82 | .egg snapshot format | **Claude** | Real manifest JSON example, the actual EXCLUDE_NAMES code, the test diff command. BookFactory described them but didn't show them. |
| 83 | Deleting the pipeline DSL we just built | **Merge** | Claude's spine + BookFactory's *"put them together and you get a second product hidden inside the first one."* |
| 84 | Click-and-watch HTML | **Claude** | Real `fetch()` + `callAgent()` code. BookFactory had a great visual opening but stayed descriptive. |
| 85 | Tether bridge: the agent.py decides | **Claude** | Real `_needsTether()` and `__tether_unavailable` injection code. BookFactory's `~/Documents` example was nice but it shipped without the routing code. |
| 86 | Per-twin Function App = independent scaling unit | **Claude** | Comparison-to-shared-FA section, state-affinity argument, three-level hierarchy. BookFactory had cleaner arithmetic but missed the GUID-routed alternative. |
| 87 | The user-correction loop | **Merge** | Claude's full trajectory + verbatim user quotes (essential for a meta-post) + BookFactory's two sharpest compressions: *"features remained, taxonomy shrank"* and *"the biggest win wasn't what got built — it was what no longer had to exist."* |

Claude wins 6 of 8. The 2 merges took Claude's structural spine and grafted BookFactory's sharpest single-sentence compressions on top.


**Patterns we noticed across all 8:**

- **Code is substance, not padding.** BookFactory's editor pass cut code blocks because the cutweak specialist was instructed to remove the weakest 20% of prose. For an engineering blog, code IS the substance. The editor heuristic was domain-mismatched.
- **BookFactory writes shorter, sharper individual sentences.** The single best line in 5 of 8 posts came from the BookFactory side. *"A refusal to hide architecture behind abstractions that readers must learn before they can inspect behavior."* *"Registration and execution are separate moments."* *"Features remained. Taxonomy shrank."* These compressions are real craft.
- **BookFactory writes worse longer arguments.** Length surfaces structure. Across all 8 BookFactory outputs, the Reviewer flagged "middle gets samey / repetition" as the dominant criticism. The composite editor cuts but doesn't restructure.
- **BookFactory's editor is over-trusting.** Two of the 8 BookFactory outputs shipped with a literal `## Outline` section at the top — scaffolding the writer left in that the editor never noticed.
- **Claude over-uses fenced code blocks.** Claude's posts averaged 3-4 fenced blocks; BookFactory averaged 0-1. The right number for an engineering blog is closer to Claude's. The right number for general readers is closer to BookFactory's.
- **Both sides failed to surprise themselves.** Neither version, in any of the 8, produced an insight that wasn't already in the source brief.


**The lesson:**

Use a single LLM with task-specific instructions for engineering blog posts where code-density is the substance. Use BookFactory-style multi-persona pipelines when prose discipline is the substance — when you're writing for general readers and the win is tighter sentences, not richer evidence. Most importantly: the BookFactory's strongest contribution was never the whole post; it was the sharpest one or two lines that the human reviewer (me) folded into Claude's longer draft. Multi-agent pipelines as a *line forge*, not a draft forge.


**What we'd change about the BookFactory next time:**

- **Don't let the editor cut code blocks.** Add a manifest hint or a soul addendum: "In engineering content, code blocks are evidence. Cut prose, never code."
- **Add a meta-artifact-stripper agent before the editor.** Catches `## Outline` scaffolding the writer left in.
- **Add a 'one-line distillation' agent.** Capture the BookFactory's actual strength: producing memorable single sentences. Output them separately so they can be lifted into other drafts.
- **Try a different editor SOUL.** The current cutweak specialist treats all paragraphs as equally cuttable. For long argument that's right. For dense reference, it's wrong.


**What we'd change about the Claude prompts:**

- **Force one-line distillation as a separate output.** Claude's posts are good but rarely contain the *single line* that lands. The BookFactory beat us 5/8 on epigram-quality.
- **Length cap was right.** All 9 Claude posts came in within the 80-150 line target. No one ran long.
- **Voice references were essential.** Specifying 2-3 existing posts to match was the highest-impact prompt element. Without it, voice would have drifted toward generic technical-blog register.


**The honest answer to "are agents writing-ready?":**

It depends on what you're writing.

For **dense engineering reference** with code as the substance: not yet. Multi-persona pipelines like BookFactory cut the wrong things. A single-pass writer with strong instructions still beats them on substance density.

For **single sentences**: already there. BookFactory beat us on the strongest line in 5 of 8. The composite Editor's specialist passes (cutweak, voicecheck) actually do produce tighter prose than a single LLM call. The win is per-sentence, not per-post.

For **prose where the value is the argument shape, not the evidence density**: probably ready. The 2 posts where we ended up merging (83, 87) were the two most argument-shaped posts. BookFactory's contributions there weren't decorative — they were structural improvements.

For **bug stories with traceable causes**: not yet. Posts 81 (loader bug) and 83 (DSL deletion) both demanded specific code references, and BookFactory's editor pass stripped them. The Writer persona can produce them; the Editor cuts them.

**The clear next move:** rebuild BookFactory's Editor as a content-aware composite. The current Editor uses one cutweak specialist for everything. A real editor knows when to preserve code, when to cut prose, when to leave a scaffolding header alone because it's actually the structure of the document. That's three more specialist agents, not a redesign — agent.py all the way down.

---

## Epilogue: cycle 2

The 6/8 + 2 merges score wasn't the end. It was the diagnosis. We took the four specific weaknesses (editor cuts code; outline scaffolding leaks; middle stays repetitive; writer ignores source code blocks) and encoded each one as an agent.py change:

- `editor_cutweak_agent.py` — soul addendum: "Fenced code blocks are EVIDENCE, not prose. Never cut a code block."
- `editor_strip_scaffolding_agent.py` — new specialist: strips `## Outline`, TODOs, draft-state labels.
- `editor_restructure_agent.py` — new specialist: consolidates repetitive middle sections.
- `persona_writer_agent.py` — soul addendum: "When source has code, INCLUDE IT VERBATIM."
- `persona_editor_agent.py` — composite now calls 5 specialists, not 3.

Then we re-ran the same 8 source briefs. Cycle 2 results: **BookFactory v2 won or tied 8/8.** All 8 v1 published posts (which were Claude versions) got replaced with the v2 BookFactory chapters. The canonical published posts in `blog/80–87` are now BookFactory v2 outputs.

The full pattern is documented in `blog/89-double-jump-loop.md`. The named lesson: **the human side and the framework side both improve every cycle**, the diagnosis from each cycle gets encoded as agent.py edits, and the loop converges when no clear winner-direction emerges. At convergence, you collapse the multi-file framework into one deployable singleton (`agents/bookfactory_agent.py` — generated by `tools/build-bookfactoryagent.py`) and that's the shipping unit.

This post — 88 — was the only one that survived as a Claude-only version through cycle 2, because it's the meta-experiment writeup. The other 8 are now sacred BookFactory v2 outputs.
