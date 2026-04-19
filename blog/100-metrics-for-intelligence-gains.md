# Metrics for intelligence gains in the double-jump loop

We get one version of this question, repeatedly, from the kind of reader who has read the rest of the blog: *"OK, but how does it fit the metrics? What are you actually measuring?"* This post is the answer. It is the most numerically rigorous post in this directory. The numbers are read verbatim from `metrics/double-jump.json` (schema `rapp-metrics/1.0`). Where the framework loses, we say so. Where the framework's edge is real, we name the size of the edge and the population it was measured against.

The whole point of writing the loop down as a metrics file is so the claims can be checked. So let's check them.

**What we measure (definitions):**

These are the eleven metrics tracked across cycles. One sentence each.

- **Win rate** — the fraction of head-to-head matchups where this side won outright (excluding ties).
- **Tie rate** — the fraction of matchups scored as ties (both sides comparable, or merge-publish was the call).
- **Best-line win rate** — the fraction of matchups where this side's strongest single sentence (per the BookFactory's Reviewer agent) was sharper than the opposing side's.
- **Code-block survival** — the fraction of source-material code blocks that appear verbatim in the published draft (engineering-shaped corpus only).
- **Scaffolding-leak rate** — the fraction of outputs containing meta-artifacts (`## Outline`, `TODO`, draft-state labels) that should have been stripped.
- **Structural completeness** — shape-specific: for tutorials, the fraction of required runnable steps; for FAQs, the fraction of required Qs; for READMEs, the fraction of required sections.
- **Specialist count** — the number of `agent.py` files that compose the framework's pipeline at this version.
- **SOUL byte count** — total bytes across all SOUL constants in the framework's specialists; a proxy for crystalized prompt knowledge.
- **Wall-time p50** — median wall time per BookFactory invocation, in seconds.
- **LLM call count** — number of LLM calls under one `/api/swarm/{guid}/agent` BookFactory call.
- **Convergence iterations per shape** — the number of double-jump iterations required for the framework to win or tie on a given content shape.

**What we don't claim:**

We are not claiming the model got smarter. The model is unchanged across all three cycles — the same Azure OpenAI gpt-5.4 brainstem powers both sides of every matchup. What changed is the framework around the model. Across cycles 1 → 3 we added two specialist agents and edited five SOUL prompts. The improvement we measure is the improvement that comes from encoding reusable distillation in `agent.py` files. Nothing in this post should be read as a general AI capability claim. The metrics describe THIS framework on THIS corpus.

**Cycle-by-cycle table:**

The numbers below come straight out of `metrics/double-jump.json`. No rounding, no smoothing.

| Metric | Cycle 1 | Cycle 2 | Cycle 3 |
|---|---|---|---|
| Framework version | 0.1.0 | 0.2.0 | 0.3.0 |
| Specialist count | 9 | 11 | 11 |
| SOUL byte count | 2,840 | 4,920 | 4,920 |
| Corpus size | 8 | 8 | 8 |
| Corpus shapes | engineering × 8 | engineering × 8 | mixed (6 shapes) |
| Framework wins | 0 | 8 | 3 |
| Human wins | 6 | 0 | 3 |
| Ties / merges | 2 | 0 | 2 |
| **Framework win rate** | **0.000** | **1.000** | **0.375** |
| Human win rate | 0.750 | 0.000 | 0.375 |
| Tie rate | 0.250 | 0.000 | 0.250 |
| Framework best-line win rate | 0.625 | 0.625 | 0.500 |
| Code-block survival | 0.000 | 1.000 | 1.000 |
| Scaffolding-leak rate | 0.250 | 0.000 | 0.000 |
| Wall-time p50 (sec) | 75 | 75 | 95 |
| LLM calls / invocation | 6 | 8 | 10 |

Three observations from this table. First, the framework went from losing every engineering matchup in cycle 1 to winning every engineering matchup in cycle 2, on the same corpus, with five file edits between them. Second, when we widened the corpus in cycle 3 to include five new shapes (tutorial, FAQ, investor-pager, README, personal-essay), the framework's overall win rate dropped from 1.000 to 0.375 — exactly the regression you'd expect when a tool tuned for one shape encounters five new ones. Third, two metrics held flat across the regression: code-block survival stayed at 1.000 and scaffolding-leak rate stayed at 0.000. The cycle-1 lessons stuck.

**The headline finding:**

Across all 24 head-to-head matchups in cycles 1, 2, and 3, the framework's strongest single sentence (per the Reviewer) beat the one-shot LLM's strongest single sentence in 14 of 24. That is 58.3%. It is the metric that held its sign across every cycle: 0.625 in cycle 1, 0.625 in cycle 2, 0.500 in cycle 3. Even when the framework lost the overall draft (cycle 1), it produced sharper individual sentences. This is the framework's most stable and reproducible advantage. The composite Editor's specialist passes (cutweak + voicecheck) produce sentence-level distillation that single-pass writing does not reproduce.

**What converged:**

Three content shapes converged in one cycle. From the `convergence_status_per_shape` field:

| Shape | Convergence iterations | Cycle-3 result |
|---|---|---|
| engineering-writeup | 1 | 3 framework wins, 0 human wins |
| investor-pager | 1 | 1 framework win, 0 human wins |
| personal-essay | 1 | 1 framework win, 0 human wins |

These are the **narrative shapes** — argument-shaped or evidence-shaped writing where the value is the prose, not the document scaffolding. The framework wins or ties on every matchup in this category.

**What hasn't converged:**

Three content shapes did not converge. Each one is a structurally-demanding shape where the literal structure of the document is part of the value.

| Shape | Convergence | Diagnosis |
|---|---|---|
| tutorial | not yet | cutweak treats numbered runnable steps as cuttable prose |
| FAQ | not yet | cutweak compresses toward "less padding"; FAQs need MORE Qs |
| README | not yet | writer doesn't recognize README as a fixed-shape document |

The diagnosis IS the prediction. Each row above maps to one new specialist agent for cycle 4: `editor_preserve_structure_agent.py` (never cut numbered lists, Q&A pairs, README sections, runnable command code blocks) and `writer_shape_recognizer_agent.py` (detects the requested shape and adjusts the Writer's prompt). If we run cycle 4 with those two agents added, the prediction (testable, recorded in the metrics file under `predicted_cycle_4_outcome`) is that the framework wins or ties 8/8 — including the three currently-losing structurally-demanding shapes. If that prediction fails, the loop didn't converge for those shapes and we add another specialist. The audit trail forces honesty.

**Cost per intelligence gain:**

Here is the unit economics, calculated from the aggregate fields.

| Quantity | Cycle 1 | Cycle 3 | Δ |
|---|---|---|---|
| Specialist count | 9 | 11 | +2 |
| SOUL bytes | 2,840 | 4,920 | +2,080 (1.73×) |
| Framework win rate on engineering | 0.000 | 1.000 | +1.000 |

Two new specialist files. Five SOUL edits. SOUL byte count grew by a factor of 1.73. In return, the framework's win rate on engineering writeups went from 0% to 100%. That ratio — two specialists plus five SOUL edits, in exchange for closing the engineering-writeup quality gap completely — is the unit economics of the double-jump loop. The denominator is "human design work, measured in `agent.py` diffs." The numerator is "measurable framework capability, measured in head-to-head win rate." Both are auditable. Both are reproducible.

A note on the SOUL-byte proxy: growing SOULs is not the same as a smarter framework. Quality came from PRECISE soul edits and shape-specific specialists, not from text volume. We track byte count because it's the cheapest proxy available, not because it's the underlying signal.

**Caveats:**

We list these because every honest metrics post lists them.

- **Corpus is small.** 24 head-to-head matchups across 3 cycles. With this n, a 58% best-line win rate is a directional signal, not a statistically rigorous claim. We would want n > 100 before defending the rate to two decimal places.
- **The reviewer is the BookFactory's own Reviewer agent.** This is a known potential bias. The Reviewer was not trained against ground truth; it was instructed via SOUL prompt to score per-axis. We have not yet introduced a third-party reviewer to check the Reviewer.
- **Wall-time and LLM-call counts vary with model latency.** The 75s → 95s wall-time bump from cycle 2 to cycle 3 partly reflects the additional specialists in the pipeline and partly reflects Azure-side latency on the day we ran. Don't read these as a clean cost curve.
- **The metrics describe THIS framework on THIS corpus.** Not a general AI capability claim. Not a multi-tenant claim. Not a claim that any framework tuned this way would behave the same.

**What this means for the skeptic:**

The double-jump loop produces measurable, reproducible quality gains per unit of human design work. The audit trail is in two places: the `agent.py` diffs (what changed in the framework) and the metric deltas (what improved in the output). Both are inspectable. Both are reproducible. Run the loop yourself against your corpus; record your numbers in the same `rapp-metrics/1.0` schema; compare. If your framework's win rate doesn't move with your specialist edits, that is a finding too. The point of the metrics file is not to claim victory. The point is to make the claim falsifiable.

The framework is not smarter than the model. The framework is a structured way of encoding the specific things the model leaves on the table, one specialist at a time, until the gap closes for a given shape. We measured that closure. The numbers are above. The methodology is in `metrics/double-jump.json`. The remaining gaps are named, and the next two `agent.py` files that should close them are named too.

That's the unit. That's the whole instrument.
