# The user-correction loop

In v1.3, the project reached a clearer architectural position. The release message marks the shift plainly:

```text
Twin Stack v1.3: agent.py all the way down + .egg snapshots

The book factory, rebuilt sacred. No pipeline DSL, no orchestrator endpoint,
no special step kinds — just agent.py files that direct-import other
agent.py files. Every layer is a single sacred portable file.
```

That scene matters because it captures the pattern of the whole project. The user’s corrections were rarely “do less” in the sense of dropping capability. They were “have fewer kinds of things.” Keep the book factory. Keep the composition. Keep the snapshots. But remove the extra category: no pipeline DSL, no orchestration layer, no special step taxonomy when a plain `agent.py` can do the job.

The strongest evidence is in the commit itself. It names the things that were cut from `swarm/server.py`:

```text
Stripped: run_pipeline,
  _resolve_swarm, /api/pipeline/*
  (over-engineering — the sacred
  single-agent endpoint already
  handles composition).
```

So v1.3 returns to the older path, almost stubbornly:

```text
POST /api/swarm/{guid}/agent {"name":"BookFactory","args":{...}}
→ 8 LLM calls under the hood (Writer + Editor's 3 + CEO's 2 +
  Publisher + Reviewer)
→ final chapter returned + 6 artifacts on disk for .egg capture
→ 72 seconds end-to-end via Azure OpenAI gpt-5.4
```

That endpoint is the whole argument. One call in, many calls under the hood, artifacts on disk, snapshots preserved. The feature set did not shrink. If anything, it sharpened. The architecture just stopped inventing special containers for behavior that ordinary files could already express.

The phrase “agent.py all the way down” is not branding. It is a design settlement. The leaf agents each inline their own `_llm_call`. That is not what a framework-minded engineer usually does. Shared utilities feel cleaner. But the source explains the choice plainly: “no shared util module — true single-file portability.” The project had been corrected enough times that portability beat tidiness. A file should be able to stand on its own. A composite should be able to `direct-import` its dependencies. The unit of thought and the unit of deployment should match.

Even the snapshot feature follows the same pressure. `.egg` snapshots were added in v1.3, but they were added in the least exotic form available: `hippocampus/twin-egg.sh`, a shell script that packs `~/.rapp-twins/` into a single zipfile snapshot with a SHA-256 manifest. Not a daemon. Not a storage service. Just a portable artifact that can capture `.shared/` state and restore it byte-for-byte. More capability, fewer moving parts.

This is why “keep it SIMPLE” can be misunderstood. It did not mean refusing ambition. The source claims an eight-call book factory, six artifacts written to disk, snapshot capture, and six green test suites with 163 passing tests. That is not minimal software in the ordinary sense. It is software that has been repeatedly pushed to express itself using fewer species of mechanism.

By v1.3, the architecture had learned to stop multiplying nouns. One endpoint. One sacred file shape. Composition through import. State captured as a zip. The result is a system that expresses substantial behavior through fewer layers, fewer abstractions, and more portable units.
