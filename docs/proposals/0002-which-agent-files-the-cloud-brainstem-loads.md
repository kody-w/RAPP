# Proposal 0002 — Which agent files the cloud Brainstem loads

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). This proposal changes none of
> them. It only says which agent files the Tier 2 (cloud) Brainstem loads, how,
> and when. This draft changes no code.

## Status

**Draft.**

An AI assistant drafted this proposal from the open Tier 2 question that
[proposal 0001](./0001-only-top-level-agents-are-live.md) leaves for the
owner (its Migration step 4, "Tier 2 decision"). It was requested for the
owner as a draft he can accept or refuse, and the request named Option A as
the recommendation. **As of 2026-09-25, the owner has not chosen.** He can
accept Option A, pick Alternative B or C, or refuse the proposal. Nothing
here governs until he merges it by hand (Article XXVIII.4, Article XXX.2).

Article XXXIII.4 says: "AI assistants must not propose or apply changes to
`brainstem.py`, `basic_agent.py`, or `function_app.py` as part of regular task
work." It adds: "If an AI assistant believes a kernel edit is genuinely
required — for example, a new top-level slot delimiter on the order of
`|||VOICE|||` — it must stop and ask the user to approve before any edit.
Authority to change DNA is held by the user, not by the assistant." This
draft does not claim that an edit to `function_app.py` is genuinely required;
Option C needs none. It sets out the choice for the owner, changes no code,
and leaves any edit to `function_app.py` to him (see Constraints under
Migration).

As of 2026-09-25, 0001 is under review in pull request #119 (branch
`experimental/constitution-live-agents`), and no pull request is open for this
draft, which lives on `experimental/proposal-0002-tier2-parity`. The assistant
that drafted it merges nothing.

**Numbering.** 0002 is the next number after 0001 in this repository's
`docs/proposals/`. The "Proposal 0002" in the title of RAPP pull request #25
is `kody-w/RAPP_Store`'s own proposal 0002, not this one.

## Context

Line numbers are for `main` at commit `8afc973`.

### The Tier 1 rule (proposal 0001)

The rule, from proposal 0001 and its amendment to Articles XVII, XVIII and
XX: in the local Brainstem, live agents come only from the top-level
`agents/*_agent.py` files, hot-loaded on every `/chat` request. Every folder
under `agents/` is organization only and never loads. Loading or unloading an
agent is a plain file move, meaning drag and drop. The grail's
`load_agents()` (`rapp_brainstem/brainstem.py` at `brainstem-v0.6.9`, lines
1202-1205) globs one level, `/chat` calls it on every request (line 1464),
and each file runs fresh from its own path (line 1039).

### How Tier 2 differs today

Tier 2's agent loading lives in `rapp_swarm/function_app.py` and
`rapp_swarm/build.sh`.

Both loader branches in `function_app.py` are already flat.
`load_agents_from_folder()` (lines 616-660) calls `os.listdir()` on
`rapp_swarm/agents/` (line 619). Its storage branch lists one level of the
`agents` directory in the storage share (line 635), through
`list_directories_and_files()` for the Azure File Share
(`rapp_swarm/utils/azure_file_storage.py` line 573) or `os.listdir()` for the
local fallback (`rapp_swarm/utils/local_file_storage.py` line 380). Python
imports those two modules from `rapp_swarm/_vendored/utils/`, whose copies
are identical. So subfolders never load in Tier 2 either. Four things differ:

1. **A 5-minute agent cache.** `AGENTS_CACHE_TTL_SECONDS = 5 * 60` (line 266).
   `_get_cached_agents()` (lines 525-542) reloads on the first call, when
   asked to (`force_refresh`), or once the cache is at least that old.
   `_reset_agents_cache()` (lines 545-551) exists, but nothing calls it, and
   nothing passes `force_refresh`. So a moved file takes effect within
   5 minutes, or on a restart, rather than on the next request.
2. **It tries any top-level `.py` file.** The local filter keeps every name
   that ends in `.py` except `__init__.py` and `basic_agent.py` (line 620). A
   top-level `weather.py`, or a helper module, is imported if Python can find
   it (see 4), and it becomes an agent if it defines or imports a
   `BasicAgent` subclass. Tier 1 looks only at `*_agent.py`, and so does
   Tier 2's own storage branch (line 637).
3. **Its build copies subfolders, although its apply step is refused.** The
   preserved `historical_build` in `rapp_swarm/build.sh` copies the
   `rapp_brainstem/agents/` tree recursively (lines 62-77, `rsync -a`, with a
   `cp -R` fallback at lines 73-75). It then copies that tree to
   `rapp_swarm/agents/` (lines 91-93). The `rsync` path skips
   `experimental_agents`, `disabled_agents` and `__pycache__` at any depth;
   the fallback removes them only at the top level. Under 0001 the first two
   names mean nothing. The grail's real subfolder, `experimental/`,
   would be copied and then never loaded. The build does not run today: plan
   is the default mode (lines 124-127), and apply is refused (lines 112-117
   and 128-130). `rapp_swarm/agents` is gitignored (`.gitignore` line 44), so
   no built copy is tracked.
4. **It imports local files by module name, not by path.**
   `_load_single_agent_local()` calls `importlib.import_module()` on
   `agents.<name>` (line 562). Python keeps the first import, so an edited
   local file keeps its old code until the app restarts. The storage branch,
   by contrast, runs each file fresh on every load (lines 589-591). The name is
   also looked up through every `agents/` folder on `sys.path`. Lines 25-32 put
   `rapp_brainstem/`, `rapp_swarm/_vendored/` and the repository root, in that
   order, ahead of the rest, so a file of the same name in
   `rapp_brainstem/agents/` or `rapp_swarm/_vendored/agents/` stands in for
   the one in `rapp_swarm/agents/`. A file that exists only in
   `rapp_swarm/agents/` is found only when the host has put `rapp_swarm/` on
   `sys.path`.

The loaders also differ in ways this proposal leaves alone. Tier 2 keeps only
the first `BasicAgent` subclass it finds in a file (lines 563-565), while
Tier 1 keeps every public class with a `perform` method (lines 1042-1059 of
`rapp_brainstem/brainstem.py`). Only Tier 1 quarantines invalid agents and
installs missing packages (lines 1055-1066).

### Tier 2 loads no agents today

Tier 2 is contained, and no active route calls the loader:

- `/api/health` returns a fixed containment status (lines 1615-1629).
- `/api/trigger/copilot-studio` refuses "before loading any agent"
  (lines 1632-1644).
- `/api/chat` (lines 1647-1658) calls `handle_rapp_chat()` (lines 1560-1612),
  which forwards only through the loopback façade after authorization, and
  refuses by default.

`_get_cached_agents()` is called only from the preserved handlers
`_historical_health_check` (line 1244), `_historical_copilot_studio_trigger`
(line 1313) and `_historical_main` (line 1388), and no route calls those.
`rapp_swarm/.funcignore` (lines 1-10) keeps `.venv`, `function_app.py`,
`agents/`, `services/`, `_vendored/`, `utils/`, `index.html`, `*.sh` and
`README.md` out of an Azure Functions publish.
`rapp_swarm/RAPP1_DEPLOYMENT_GUARD.json` records `adapted-preacceptance` with
no default effects, and the repository README calls `rapp_swarm/` a "Retired
Tier 2 tombstone and historical evidence" (`README.md` line 135).

So this decision sets the rule that the preserved Tier 2 code follows if it is
ever reviewed and switched back on. It changes nothing a user sees today.

## Proposed change (recommended in the request)

**Option A: Tier 2 uses the Tier 1 file rule, loads each file from its path,
and keeps its cache.** This is the option the request named. Whether to take
it, and who writes any kernel edit, is the owner's decision (Article
XXXIII.4).

1. **Only top-level `*_agent.py` files load, the same rule as Tier 1.** This
   applies to both branches: the local `agents/` folder, which today takes any
   `.py` file, and the storage share, which already requires `*_agent.py`.
   `basic_agent.py`, the base class, still yields no agent, as in Tier 1.
2. **Each local file is loaded from its own path in `rapp_swarm/agents/`,**
   as Tier 1 does. A file of the same name elsewhere on `sys.path` then cannot
   stand in for it, and every cache refresh runs the file fresh.
3. **Subfolders are organization.** They never load. The build copies the
   top-level agent files and `basic_agent.py`, and copies a subfolder only if
   something else needs it. Today nothing in `rapp_swarm/` reads one.
4. **Keep the 5-minute cache as a documented cloud detail.** A moved or
   edited file takes effect within 5 minutes. Say so in `rapp_swarm/README.md`
   and in a comment next to `AGENTS_CACHE_TTL_SECONDS` in `function_app.py`.

Why this option:

- Both tiers then use the same rule for which files load, and both read each
  file from its own path. Article III.3 promises that an agent file that runs
  in Tier 1 runs unmodified in Tier 2, and Article XV says "Contract parity is
  asserted per-PR, not deferred to a migration window". The timing difference
  (the cache) and the smaller loader differences listed above remain.
- It keeps the cache, a cloud-side detail that saves work on most requests.
- The change stays small and additive (see Migration).

What stays the same: the cache length, the storage branch's rule, the routes,
the containment (`.funcignore`, the deployment guard, the refusals),
`rapp_swarm/_vendored/`, and everything under `rapp_brainstem/`.

## Alternatives

**B: Match Tier 1's timing too. Reload on every request, with no cache.**
Everything in A, and the cache is bypassed, so a move or an edit takes effect
on the next request, as in Tier 1. The cost is paid on every request. Each
chat would list `agents/`, run every local agent file, and, for the storage
share, list the directory and read every agent file (lines 635-645). That
means storage round trips on every call. A cold start already pays one full
load, but without the cache every warm request pays it too.

**C: Leave Tier 2 as it is, and document the differences.** No code change.
`rapp_swarm/README.md` would describe the four differences above. The cost is
that Article III.3's promise is not met in Tier 2. A Tier 1 agent file copied
into `rapp_swarm/agents/` can be replaced by a file of the same name in
`rapp_brainstem/agents/` or `rapp_swarm/_vendored/agents/`, or not be found
at all, and an edit to it needs a restart. Tier 2 would also load files that
Tier 1 ignores, such as a top-level `weather.py`. This is the only option
that leaves `function_app.py` untouched, which Articles I and XXXIII favor
(see Constraints under Migration).

## Migration

Proposal 0001 goes first, in its own two PRs (pull request #119, then its
amendment PR). Those are 0001's steps, not steps of this proposal. Each step
below lands in one PR.

1. **Acceptance.** The owner merges this proposal, with the option he picks.
   The proposal merge is his (Article XXX.2). Before a pull request is opened
   for its branch, `experimental/proposal-0002-tier2-parity`, merge `main`
   into that branch. After 0001's two squash merges, that merge conflicts on
   proposal 0001 and on the receipts: keep `main`'s version of 0001 (its
   Status then says it is implemented), and recompute the receipts. Before
   merging this proposal, set its Status to `accepted`, and record the option
   the owner picked in place of "the owner has not chosen" and, for A or B,
   how he reads Article I for this change (see Constraints). Squash-merge it,
   since that branch carries proposal 0001's pre-split commits.
2. **One implementation PR.** It sets this proposal's Status to `implemented`
   and refreshes the receipts. For A and B, it also changes code in
   `rapp_swarm/` and adds tests, and the owner approves and merges it (see
   Constraints). For C, it adds only the README note.
   - `rapp_swarm/function_app.py` (A and B): require `*_agent.py` in the local
     branch, and load each local file from its path. For B, also bypass the
     cache. For A, also add a comment line just above
     `AGENTS_CACHE_TTL_SECONDS` (line 266), leaving that line as it is.
     Article XXXII.1 says agent discovery is kernel code that "must
     run inline in `brainstem.py` (or a utility it imports)"; for Tier 2 that
     means `function_app.py` or a module it imports, so a wrapper around the
     kernel does not fit, and even an added sibling module needs a new import
     line in `function_app.py`. Any edit must add lines and change none (see
     Constraints).
   - `rapp_swarm/build.sh` (A and B): add a copy step that takes only the
     top-level agent files, for any future reviewed apply path. The preserved
     `historical_build` stays as evidence.
   - `rapp_swarm/README.md`: the cache note (A), the no-cache behavior (B), or
     the four differences (C), added without changing its existing lines.
   - Offline tests, in a new module. It can load `function_app.py` the way
     `tests/test_restored_swarm_sim_sources.py` already does (`_load_module`,
     line 321), with storage stubbed, and it must control `sys.path`
     (difference 4). The cases: a top-level `weather_agent.py` loads; a
     top-level `weather.py` does not; `parked/weather_agent.py` does not; a
     subfolder in the storage share does not; a file of the same name in
     another `agents/` folder does not stand in; an edit takes effect at the
     next refresh (A) or request (B); `AGENTS_CACHE_TTL_SECONDS` is still 300
     (A); and the new copy step, run on a scratch tree, copies no subfolder.
     Register the test in `tests/rapp1-test-suite-inventory.json`, and make
     sure `tests/run_rapp1_conformance.py` reaches it.
   - Receipts: after the commit that changes `function_app.py`, `build.sh` or
     `README.md`, regenerate `HISTORICAL_SOURCE_LEDGER.json` with
     `python3 tools/build_historical_source_ledger.py --write`, because each
     record pins its file's latest commit and bytes. Refresh the byte count in
     `tests/fixtures/rapp1-doc-scope.json` for any byte change. For any new
     file, also refresh the inventory's path counts and path-set digests (the
     `snapshot`, and each path set that covers the file, such as `PS-ALL`)
     and the doc-scope path count.
   - Merge method: the ledger records the branch commit, which a squash merge
     replaces. Merge this PR with a merge commit, or regenerate the ledger on
     `main` right after a squash merge (Article XXX.1 expects squash merges).

### Constraints on the implementation PR

- **Kernel.** The byte-pin freeze does not cover `rapp_swarm/`.
  `check_kernel_pin.py` checks only the three files in `KERNEL_PIN.json`
  (`rapp_brainstem/brainstem.py`, `rapp_brainstem/agents/basic_agent.py` and
  `rapp_brainstem/VERSION`), and `KERNEL_TREE.md` lists the same three as the
  sacred files. But Article XXXIII.1 lists `rapp_swarm/function_app.py` as
  kernel "DNA" ("Sacred ... Never edited by AI assistants"), and
  Article XXXIII.4 says AI assistants must not propose or apply changes to it
  as part of regular task work. XXXIII.4's stop-and-ask path lets the user
  approve an assistant's edit, but XXXIII.1 says kernel files are "Never
  edited by AI assistants"; this draft reads the stricter rule as governing.
  So for A or B, the owner writes the `function_app.py` change himself, and
  the implementation PR is not merged by an AI under Article XXX.1's
  standing authorization. `build.sh`, `README.md` and the tests are not
  kernel files. The PR touches nothing under `rapp_brainstem/`.
- **Article I.** It says the only legitimate reason to modify
  `function_app.py` is a new output slot, and it gives no other exception.
  Options A and B stay within Article I's own responsibility 3
  ("Auto-discover `*_agent.py` files and hot-load them") and add no
  responsibility (Article XXVI), but they still edit the file, so they
  conflict with that sentence as written. Article XXXII, which the
  XXXIII.1 table points to "for what changes the kernel admits at all", says
  which code belongs in the kernel (agent discovery does); it adds no reason
  to edit it. Choosing A or B therefore also needs the owner to record how he
  reads Article I for this change. This draft does not treat amending
  Article I as a way around it, because Article XXVI says amendments must
  preserve Article I. Option C needs neither.
- **The source ledger allows no changed lines today.** The ledger's checks
  run in `tests/test_adaptation_inventory.py` (lines 151-159 and 409-423).
  They count each historical line that is 8 or more characters long once
  whitespace is collapsed, and look for it anywhere in the current file.
  `function_app.py` must keep 99.5% of those lines and every historical
  symbol (`python_symbols(0.995)`, `tools/build_historical_source_ledger.py`
  lines 506-509). It is at 99.55% now: 4 of the 895 historical lines that the
  check counts are already missing, and 4 is the most allowed. `build.sh` must
  keep all of its counted historical lines
  (`normalized_line_coverage(1.0, ...)`, same file, lines 488-491), and it
  does. So must `rapp_swarm/README.md` (record `swarm-readme`, lines
  622-638). So the change must be purely additive: change no existing counted
  line, including lines 562, 620 and 626, the cache lines and the `rsync`
  lines, and add the new code beside them.
- **Tests and evidence.** `tests/test_restored_swarm_sim_sources.py` checks
  the provenance, the markers such as `def load_agents_from_folder` and
  `rsync -a`, and the symbols (line 377). `tests/test_rapp1_containment.py`
  requires `.funcignore` to keep excluding `function_app.py` (lines 361-362).
  `tests/fixtures/rapp1-doc-scope.json` classifies `rapp_swarm/README.md` as
  `excluded`, a "current pre-acceptance safety boundary plus bounded verbatim
  historical Tier-2 guide". Leave `rapp_swarm/_vendored/` alone: it is
  preserved evidence. No gate checks the content of a committed edit there,
  though. The test at line 1443 of `tests/test_restored_swarm_sim_sources.py`
  sees only unstaged changes, and `tests/test-t2t-removal.sh` (lines 164-192)
  checks only that the build plan leaves it unchanged and that certain files
  are present or absent. A size change would still fail the byte receipt,
  and an added or removed file would fail the `PS-SWARM` and `PS-ALL` path
  sets until they are recomputed.
- **Containment.** Tier 2 stays contained. No route starts calling the loader,
  and accepting this proposal does not switch Tier 2 on.

## Rollback

- **Before a merge:** refuse the proposal or delete the branch. Nothing
  changes.
- **After the proposal, before the implementation PR:** a later proposal can
  supersede this one (Article XXVIII.3). Nothing else needs undoing.
- **After the implementation PR:** revert it. For A or B the revert changes
  `function_app.py`, so the owner makes and merges it himself (see
  Constraints). Regenerate the source ledger and refresh the receipts in the
  same revert PR. Merge that revert with a merge commit, or regenerate the
  ledger on `main` right after a squash merge, for the reason given under
  Migration.

Tier 2 is contained, so no deployed behavior changes in either direction.

## References

- [Proposal 0001](./0001-only-top-level-agents-are-live.md), the Tier 1 rule
  and the open Tier 2 question (Migration step 4); under review in pull
  request #119 as of 2026-09-25.
- [`CONSTITUTION.md`](../../CONSTITUTION.md): Article I, Article III.3,
  Article XV, Article XVII, Article XVIII, Article XX, Article XXVI,
  Article XXVIII (.3, .4), Article XXX.1, Article XXX.2, Article XXXII.1 and
  Article XXXIII (.1, .4).
- Tier 1: `rapp_brainstem/brainstem.py` lines 1039, 1042-1066, 1202-1205 and
  1464.
- Tier 2: `rapp_swarm/function_app.py` lines 25-32, 266, 525-551, 562-565,
  589-591, 616-660, 1244, 1313, 1388, 1560-1612 and 1615-1658;
  `rapp_swarm/build.sh` lines 62-93 and 106-130; `rapp_swarm/.funcignore`;
  `rapp_swarm/RAPP1_DEPLOYMENT_GUARD.json`; `README.md` line 135.
- Kernel freeze: `KERNEL_PIN.json`, `check_kernel_pin.py`, `KERNEL_TREE.md`.
- Gates: `tools/build_historical_source_ledger.py`,
  `tests/test_adaptation_inventory.py`,
  `tests/test_restored_swarm_sim_sources.py`, `tests/test-t2t-removal.sh`,
  `tests/test_rapp1_containment.py`, `tests/rapp1-test-suite-inventory.json`,
  `tests/fixtures/rapp1-doc-scope.json`.
