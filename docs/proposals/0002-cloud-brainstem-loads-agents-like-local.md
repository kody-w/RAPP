# Proposal 0002 — The cloud Brainstem loads agents like the local one

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). This proposal changes none of
> them. It only says which agent files the Tier 2 (cloud) Brainstem loads, and
> this draft changes no code.

## Status

**Draft.**

An AI assistant drafted this proposal from the owner's open question in
[proposal 0001](./0001-only-top-level-agents-are-live.md) (its Migration
step 3, "Tier 2 decision"). **The owner has not chosen yet.** He can accept the
recommended option, pick Alternative B or C, or refuse the proposal. Nothing
here governs until he merges it by hand (Article XXVIII.4, Article XXX.2).

This builds on 0001, which is still a draft on
`experimental/constitution-live-agents`. This draft lives on
`experimental/proposal-0002-tier2-parity`. The AI opens no pull request and
merges nothing. 0002 is the next number after 0001.

## Context

### The Tier 1 rule (proposal 0001)

Only the top-level `agents/*_agent.py` files are live, hot-loaded on every
request. Every folder under `agents/` is organization only and never loads.
Loading or unloading an agent is a plain file move, meaning drag and drop.
The grail's `load_agents()` (`rapp_brainstem/brainstem.py` lines 1202-1205)
globs one level, and `/chat` calls it on every request (line 1464).

### How Tier 2 differs today

Line numbers are for the files on this branch. Tier 2 is
`rapp_swarm/function_app.py` plus `rapp_swarm/build.sh`.

Both Tier 2 loader branches are already flat. `load_agents_from_folder()`
(lines 616-660) calls `os.listdir()` on `rapp_swarm/agents/` (line 619). Its
storage branch lists one level of the `agents` share (line 635), through
`list_directories_and_files()` for the Azure File Share
(`rapp_swarm/utils/azure_file_storage.py` line 573) or `os.listdir()` for the
local fallback (`rapp_swarm/utils/local_file_storage.py` line 380). So
subfolders never load in Tier 2 either. There are three differences:

1. **A 5-minute agent cache.** `AGENTS_CACHE_TTL_SECONDS = 5 * 60` (line 266).
   `_get_cached_agents()` (lines 525-542) reloads only when the cache is at
   least that old. `_reset_agents_cache()` (lines 545-551) exists, but nothing
   calls it. So a moved file takes effect within 5 minutes, or on a restart,
   rather than on the next request. One more detail: local files are imported
   with `importlib.import_module()` (line 562), and Python keeps the first
   import, so an edited local file keeps its old code until the app restarts.
   The storage branch runs each file fresh on every load (lines 589-591).
2. **It tries any top-level `.py` file.** The local filter keeps every name
   that ends in `.py` except `__init__.py` and `basic_agent.py` (line 620). A
   top-level `weather.py`, or a helper module, is imported, and it becomes an
   agent if it defines a `BasicAgent` subclass. Tier 1 looks only at
   `*_agent.py`, and so does Tier 2's own storage branch (line 637). The same
   file can therefore load in the cloud and not locally.
3. **Its build copies subfolders, although its apply step is refused.** The
   preserved `historical_build` in `rapp_swarm/build.sh` copies the
   `rapp_brainstem/agents/` tree recursively (lines 62-77, `rsync -a`, with a
   `cp -R` fallback at lines 73-75). It then copies that tree to
   `rapp_swarm/agents/` (lines 91-93). The only folders it skips are
   `experimental_agents`, `disabled_agents` and `__pycache__`, and under 0001
   those names mean nothing. The grail's real subfolder, `experimental/`, would
   be copied and then never loaded. The build does not run today: plan is the
   default mode (lines 124-127), apply is refused (lines 112-117 and 128-130),
   and `rapp_swarm/agents` is gitignored (`.gitignore` line 44).

### Why nothing is broken today

Tier 2 is contained. No active route calls the loader:

- `/api/health` returns a fixed containment status (lines 1615-1629).
- `/api/trigger/copilot-studio` refuses "before loading any agent"
  (lines 1632-1644).
- `/api/chat` forwards only through the loopback façade after authorization,
  and refuses by default (lines 1647-1658).

`_get_cached_agents()` is called only from the preserved handlers
`_historical_health_check` (line 1244), `_historical_copilot_studio_trigger`
(line 1313) and `_historical_main` (line 1388), and no route calls those.
`rapp_swarm/.funcignore` (lines 1-10) keeps `function_app.py`, `agents/`,
`_vendored/` and the rest out of any publish. `rapp_swarm/RAPP1_DEPLOYMENT_GUARD.json`
records `adapted-preacceptance` with no default effects.

So this decision sets the rule that the preserved Tier 2 code follows if it is
ever reviewed and switched back on. It changes nothing a user sees today.

## Proposed change (recommended)

**Option A: Tier 2 uses the Tier 1 file rule and keeps its cache.**

1. **Only top-level `*_agent.py` files load, the same rule as Tier 1.** This
   applies to both branches: the local `agents/` folder, which today takes any
   `.py` file, and the storage share, which already requires `*_agent.py`.
   `basic_agent.py` is still skipped as the base class.
2. **Subfolders are organization.** They never load. The build copies the
   top-level agent files and `basic_agent.py`, and copies a subfolder only if
   something else needs it. Today nothing in `rapp_swarm/` reads one.
3. **Keep the 5-minute cache as a documented cloud detail.** A moved file
   takes effect within 5 minutes. Say so in `rapp_swarm/README.md` and next to
   `AGENTS_CACHE_TTL_SECONDS`. Also write down that an edited local file keeps
   its old code until a restart. Changing that is not part of this proposal.

Why this option:

- The same file gives the same result in both tiers. Article III.3 promises
  that an agent which runs in Tier 1 runs unmodified in Tier 2, and Article XV
  says parity is "asserted per-PR, not deferred to a migration window".
- It keeps the one cloud-specific detail that saves work on every request.
- The code change is small: one filter in the local branch, and the agent-copy
  step of the build.

What stays the same: the cache length, the storage branch's rule, the routes,
the containment (`.funcignore`, the deployment guard, the refusals),
`rapp_swarm/_vendored/`, and everything under `rapp_brainstem/`.

## Alternatives

**B: Match Tier 1 exactly. Reload on every request, with no cache.** This uses
the same file rule as A and also drops the cache. A move or an edit would take
effect on the next request, exactly as in Tier 1. The cost is paid on every
request. Each chat would list `agents/`, import the local files, and, for the
storage share, list the directory and read every agent file (lines 635-645).
That means storage round trips on every call. A cold start already pays one
full load, but without the cache every warm request pays it too. For edits to
take effect, local loading would also have to switch from `import_module()`
to loading by path, as Tier 1 does. That is a larger change to
`function_app.py`.

**C: Leave Tier 2 as it is, and document the difference.** No code change.
`rapp_swarm/README.md` would say that Tier 2 caches agents for 5 minutes,
tries any top-level `.py` file, and copies subfolders in its build. The cost is
a documented exception to the portability promise: an agent named `weather.py`
would work in the cloud and not locally. This is the only option that leaves
`function_app.py` untouched, which a strict reading of Article I prefers (see
Migration).

## Migration

One PR per step.

1. **Acceptance.** The owner merges 0001 first, then this proposal with the
   option he picks. The proposal merge is his (Article XXX.2).
2. **One implementation PR in `rapp_swarm/`, with tests.** For C, the PR is
   only the README note.
   - `rapp_swarm/function_app.py`: require `*_agent.py` in the local branch
     (A and B), and drop the cache (B only).
   - `rapp_swarm/build.sh`: add a copy step that takes only the top-level agent
     files, for any future reviewed apply path. The preserved
     `historical_build` stays as evidence.
   - `rapp_swarm/README.md`, and a comment at line 266: the cache and restart
     notes (A), or the no-cache behavior (B).
   - Offline tests, in a new module that loads `function_app.py` the way
     `tests/test_restored_swarm_sim_sources.py` already does (`_load_module`,
     line 321), with storage stubbed. The cases: a top-level
     `weather_agent.py` loads; a top-level `weather.py` does not;
     `parked/weather_agent.py` does not; a subfolder in the storage share does
     not; `AGENTS_CACHE_TTL_SECONDS` is still 300 (A); the build plan copies no
     subfolder. Register the test in `tests/rapp1-test-suite-inventory.json`,
     and make sure `tests/run_rapp1_conformance.py` reaches it.
   - Receipts: after the code commit, regenerate `HISTORICAL_SOURCE_LEDGER.json`
     with `python3 tools/build_historical_source_ledger.py --write`, because
     each record pins its file's latest commit and bytes. Refresh the inventory
     and doc-scope receipts for any new file.
3. **Kernel freeze: none of this falls under it.** `check_kernel_pin.py` checks
   only the three files in `KERNEL_PIN.json`: `rapp_brainstem/brainstem.py`,
   `rapp_brainstem/agents/basic_agent.py` and `rapp_brainstem/VERSION`.
   `KERNEL_TREE.md` lists the same three as the sacred files and puts
   `rapp_swarm/` under Tier 2. The PR touches nothing under `rapp_brainstem/`.
4. **Other gates the PR must pass.** These are not the freeze, but they are
   hard gates:
   - **The source ledger leaves no room today.** `function_app.py` must keep
     99.5% of its historical lines and every historical symbol
     (`python_symbols(0.995)`, `tools/build_historical_source_ledger.py`
     lines 506-509). It is at 99.55% now: 4 of 895 historical lines already
     differ, and 4 is the limit. `build.sh` must keep 100% of its lines (lines
     488-491), and it does. So the change must be additive: leave line 620 and
     the `rsync` lines as they are, and add the new filter and copy step
     beside them.
   - `tests/test_restored_swarm_sim_sources.py` checks the provenance, the
     markers such as `def load_agents_from_folder` and `rsync -a`, and the
     symbols (line 377). It also requires `rapp_swarm/_vendored/` to stay
     unchanged (line 1443). `tests/test_rapp1_containment.py` requires
     `.funcignore` to keep excluding `function_app.py` (lines 361-362).
   - Tier 2 stays contained. No route starts calling the loader, and accepting
     this proposal does not switch Tier 2 on.
   - **Article I.** It says the only legitimate reason to modify
     `function_app.py` is a new output slot. Options A and B stay within
     Article I's own responsibility 3 ("Auto-discover `*_agent.py` files and
     hot-load them") and add no responsibility (Article XXVI), but they are
     still edits. Accepting A or B is therefore also the owner's explicit
     approval of that edit. If he reads Article I strictly, C is the choice.

## Rollback

Before a merge, refuse the proposal or delete the branch. Nothing changes.

After the implementation PR, revert it, then regenerate the source ledger and
refresh the receipts in the same revert PR, so the gates stay consistent.
Tier 2 is contained, so no deployed behavior changes in either direction.

## References

- [Proposal 0001](./0001-only-top-level-agents-are-live.md), the Tier 1 rule
  and the open Tier 2 question (Migration step 3).
- [`CONSTITUTION.md`](../../CONSTITUTION.md): Article I, Article III.3,
  Article XV, Article XVII, Article XVIII, Article XXVI, Article XXVIII (.3,
  .4) and Article XXX.2.
- Tier 2: `rapp_swarm/function_app.py` lines 266, 525-551, 562, 589-591,
  616-660, 1244, 1313, 1388 and 1615-1658; `rapp_swarm/build.sh` lines 62-93
  and 106-130; `rapp_swarm/.funcignore`;
  `rapp_swarm/RAPP1_DEPLOYMENT_GUARD.json`.
- Kernel freeze: `KERNEL_PIN.json`, `check_kernel_pin.py`, `KERNEL_TREE.md`.
- Gates: `tools/build_historical_source_ledger.py`,
  `tests/test_restored_swarm_sim_sources.py`, `tests/test_rapp1_containment.py`,
  `tests/rapp1-test-suite-inventory.json`.
