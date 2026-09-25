# Proposal 0001 — Only top-level agents are live

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). This proposal changes none of
> them. It only says which Brainstem agent files are live, and it changes no
> code, no agent file, and no grail byte.

## Status

**Draft.**

The maintainer (@kody-w) approved the substance in conversation on
2026-09-24. It had been pointed out to him that the constitution says agents
load recursively, while the grail loads only the top level of `agents/`. He
confirmed that the grail is right:

> "yes that is correct only agents/ is the true live brainstem agents...
> everything else is just organization"

> "then its just drag and drop for agents hotloaded in and out"

That approval is not a merge. A constitutional amendment still needs the
maintainer's deliberate human merge (Article XXVIII.4, Article XXX.2). An AI
agent drafted this proposal and pushed it to the experimental branch
`experimental/constitution-live-agents` only. It opens no pull request and
merges nothing.

**Numbering.** `docs/proposals/` does not exist on `main`, and no numbered
proposal appears anywhere in the repository history. The only earlier
proposal file, `docs/proposals/2026-07-25-kernel-minimality-enforcement.md`,
is an unmerged draft with a date for a name on branch `law/kernel-minimality`.
It has no number. This proposal is therefore 0001.

## Context

### What the grail does (Tier 1)

`rapp_brainstem/brainstem.py` is byte-identical to the grail,
`kody-w/rapp-installer@brainstem-v0.6.9` (see `KERNEL_PIN.json`;
`python3 check_kernel_pin.py` passes). Its loader is flat:

```python
# rapp_brainstem/brainstem.py, VERSION 0.6.9, lines 1202-1205
def load_agents():
    agents = {}
    pattern = os.path.join(AGENTS_PATH, "*_agent.py")
    files = glob.glob(pattern)
```

- `glob.glob()` with no `**` and no `recursive=True` matches one directory
  level. The loader never looks inside a folder under `agents/`.
- `/chat` calls `load_agents()` on every request (line 1464), and
  `_load_agent_from_file()` runs each file fresh from disk (lines 1021-1073).
  So top-level files are hot-loaded on every request. Adding or removing one
  takes effect on the next message.
- `basic_agent.py` matches the pattern but gives no agent, because the loader
  skips the `BasicAgent` class (line 1047).
- `GET /agents` lists only top-level `*.py` files (line 1787).
  `POST /agents/import`, which the code describes as "Import an agent .py file
  via drag & drop", saves the file at the top level (lines 1843-1862), so a
  dropped file is live on the next request. `DELETE /agents/<filename>` also
  acts only on the top level (lines 1821-1841).
- The grail's latest public tag, `brainstem-v0.6.16`, keeps the same flat
  loader: `load_agents()` at lines 1832-1835 does
  `files = sorted(glob.glob(pattern))`, and `/chat` calls it at line 2271.
- This repository's own test pins the live default set with the same flat
  glob (`rapp_brainstem/test_reserved_agents.py`, lines 21-29).

### What the constitution says instead

Line numbers are for `CONSTITUTION.md` at `8afc973`, before this amendment.

| Where | Stale claim |
|---|---|
| Art. XVII, lines 909-916 | `agents/` is a "recursive tree", and a nested file "auto-loads exactly like `agents/outbound_agent.py`" |
| Art. XVII, lines 918-921 | `experimental_agents/` and `disabled_agents/` are reserved by the engine and never auto-load; "Everything else under `agents/` loads" |
| Art. XVII, lines 936-947 | `agents/workspace_agents/` "Auto-loads recursively", and its reserved subfolders never auto-load |
| Art. XVII, lines 949-959 | "Anything else the user creates under `agents/` auto-loads" |
| Art. XVII, lines 973-975 and 985-986 | subfolder names reserved by the engine; no depth limit on `agents/` recursion |
| Art. XVII, lines 988-999 | `load_agents()` "walks `agents/` recursively via `rglob("*_agent.py")`", and `rapp_swarm/build.sh` makes Tier 2 mirror Tier 1's shape |
| Art. XVIII, lines 1024-1026 | "Disable", "Enable" and "Mark experimental" map to moves into and out of reserved folders |
| Art. XVIII, lines 1029-1032 and 1059-1061 | the reserved subfolders are shown "with their semantics (experimental won't auto-load, disabled is off)" |
| Art. XX, lines 1143-1144 (also 1154-1155 and 1167-1168) | the beginner view hides "reserved folders", and "The three reserved names are engine-internal" |

None of this matches the grail. It has no `rglob`, no reserved folder names,
and no subfolder that loads. The constitution even contradicts itself:
Article III.7 (line 301) correctly says `rapp_brainstem/agents/experimental/`
holds agents "the auto-loader ignores". The historical guides agree with the
grail too: `CLAUDE.md` line 130 says "flat only", and
`.github/copilot-instructions.md` line 166 says subfolders "are not
auto-discovered".

Why it matters: a person who follows Article XVII puts `weather_agent.py` in
`agents/my_project/` and expects it to load, and it never does. A person who
wants to turn an agent off looks for a special folder, when any folder already
does the job.

### The ruling

- **Live** means exactly the top-level `agents/*_agent.py` files, hot-loaded
  on every request.
- **Every subfolder** of `agents/` is organization only and never loads,
  whatever its name.
- **Loading or unloading** an agent is a plain file move, meaning drag and
  drop: move it to the top of `agents/` to load it, or into any folder to
  unload it.

### What this means for the agents that ship

- The grail's `rapp_brainstem/agents/` has the same files at
  `brainstem-v0.6.9` and `brainstem-v0.6.16`:
  - **Live (top level):** `context_memory_agent.py`, `hacker_news_agent.py`
    and `manage_memory_agent.py`. `basic_agent.py` also sits there, but it is
    the base class, not an agent.
  - **Not live (subfolder):** `experimental/copilot_research_agent.py`. It
    stays parked until someone moves it to the top level.
- The grail ships no `workspace_agents/` folder and no
  `swarm_factory_agent.py`, at either tag. Article XVII says to keep "the one engine tool
  (`swarm_factory_agent.py`)" under `workspace_agents/` (lines 930-934,
  938-941 and 979-982). With a flat loader, that would leave the tool not
  live. The only copy in this repository,
  `rapp_swarm/_vendored/agents/workspace_agents/swarm_factory_agent.py`, is in
  a subfolder, so neither tier's loader loads it.
- Article XVII's starter set (lines 923-928: `learn_new_agent.py`,
  `save_memory_agent.py`, `recall_memory_agent.py`) does not match the grail's
  top level either. That is a separate drift. This proposal does not amend it
  and lists it as a follow-up.

### Tier 2 (`rapp_swarm/`)

This is what the code does today. This proposal changes no Tier 2 code. Tier 2
is pre-acceptance, and its effects are refused by default
(`rapp_swarm/RAPP1_DEPLOYMENT_GUARD.json`).

- **Its loader is flat too.** `rapp_swarm/function_app.py`
  `load_agents_from_folder()` (lines 616-660) calls `os.listdir()` on
  `rapp_swarm/agents/`, which lists the top level only (lines 618-620). It
  also lists one level of the storage `agents` directory (lines 634-637),
  whether that is the Azure File Share (`list_directories_and_files()`,
  `rapp_swarm/utils/azure_file_storage.py` line 573) or the local fallback
  (`os.listdir()`, `rapp_swarm/utils/local_file_storage.py` line 380).
  Nothing recurses.
- **It differs from Tier 1 in three ways:**
  1. *It caches.* Agents are cached for five minutes
     (`AGENTS_CACHE_TTL_SECONDS = 5 * 60` at line 266, `_get_cached_agents()`
     at lines 525-542), and nothing in the file forces a refresh. A file move
     shows up when the cache expires or the app restarts, not on the next
     request.
  2. *Its local filter is looser.* The local folder tries to load any
     top-level `.py` file except `__init__.py` and `basic_agent.py`
     (line 620), not only `*_agent.py`. The storage branch does require
     `_agent.py` (line 637).
  3. *Its build copies folders.* The preserved historical build in
     `rapp_swarm/build.sh` (lines 62-77) copies the `agents/` tree
     recursively, skipping `experimental_agents` and `disabled_agents`, and
     then copies it to `rapp_swarm/agents/` (lines 91-93). Subfolders get
     deployed but never load. The build's apply mode is refused (lines
     112-117 and 128-130), and `rapp_swarm/agents` is gitignored
     (`.gitignore` line 44).
- So Article XVII's line "Tier 2 mirrors Tier 1's user-organized shape
  exactly" is true of copying, not of loading. Whether Tier 2 should load on
  every request and only `*_agent.py` files, like Tier 1, is an **open
  follow-up for the owner** (Migration step 3).

## Proposed change

The change is additive only. It follows the "Amendment (2026-07-08)"
precedent in Articles XLVI and XLVII: add a governing blockquote note, keep
the stale wording, and state "this note governs".

1. **`CONSTITUTION.md`, Article XVII.** A governing note at the top of the
   article, titled "Amendment (2026-09-24) — only top-level agents are live;
   additive per Article XXVI". It cites the grail's `load_agents()` and this
   proposal.
2. **`CONSTITUTION.md`, Article XVIII.** A short note at "The mapping":
   **Load** = move the file to the top level of `agents/`; **Unload** = move
   it into any folder. Drag and drop is the whole interaction. Reserved
   folder names are conventions with no engine meaning.
3. **`CONSTITUTION.md`, Article XX.** A short note under the beginner-view
   bullet "Reserved folders hidden": the engine reserves no folder names.
4. **`pages/docs/SPEC.md`, §18.5.** A short note under the "Workshop" bullet
   (lines 786-788). The bullet says a workshop under
   `agents/workspace_agents/<my_swarm>/` iterates "against the hotload loop".
   Under the ruling it does not.
5. **Receipts for the new tracked file.** `RAPP1_ADAPTATION_INVENTORY.json`
   (path count and path-set digest) and `tests/fixtures/rapp1-doc-scope.json`
   (path, byte and document counts, and this proposal's `current`
   disposition). They are recomputed with the digest rules in
   `tests/test_adaptation_inventory.py` and `tools/check_rapp1_docs.py`.

What does not change:

- No code, no agent file, and nothing under `rapp_brainstem/`. The three grail
  files pinned by `KERNEL_PIN.json` are untouched (Article LV.4).
- No stale sentence is deleted or rewritten (Article XXVI).
- `README.md` line 134 is left as it is, because it is not wrong under the
  ruling. It calls the top level the "Showroom (top-level starter agents)"
  and `workspace_agents/` "everything organizational". (It names a
  `workspace_agents/` folder that the grail does not ship; that is listed as
  a follow-up.)

### Article XXVI check

- **Article I (the brainstem stays light):** preserved. Nothing is added to
  `brainstem.py` or `function_app.py`. The amendment describes the loader as
  it already is.
- **Article XXV (chat is the only wire):** preserved. No request, response,
  slot or schema changes, and nothing is removed or renamed; the notes are
  additive. RAPP/1 §8, which governs the wire under Article LV, is untouched
  too.

## Migration

One PR per step.

1. **This change (docs only).** The proposal, the three constitutional notes,
   the SPEC.md note and the receipt refresh, on
   `experimental/constitution-live-agents`. The maintainer accepts the
   proposal and merges the amendment by hand (Articles XXVIII.4 and XXX.2).
   Until then, nothing here governs.
2. **Follow-up docs (optional, the owner's call).** Additive notes or
   corrections, each in its own PR:
   - `rapp_brainstem/CONSTITUTION.md`, the historical application
     constitution. Article IX, lines 497-499 and 544, says workshop folders
     iterate "against the hotload loop". Article XII, lines 723-734, 747-770,
     791 and 797-805, repeats the recursive tree, the reserved names, `rglob`
     and Tier 2 mirroring. Article XIII, lines 828-834 and 851, and
     Article XIV, lines 877-878, repeat the reserved-folder rows and rules.
     The file is outside the kernel freeze, but it is left untouched here.
   - `rapp_brainstem/.gitignore`, lines 26-28: the comment says
     `agents/workspace_agents/local_agents/` is "auto-loaded by brainstem".
   - The vault drafts, left alone here:
     `pages/vault/Blog Drafts/the-experimental-graveyard.md` (lines 6, 19,
     23, 25, 36, 49 and 75 describe `experimental_agents/` as a folder the
     loader filters out) and `pages/vault/Plans & Ledgers/Blog Roadmap.md`
     line 120 (the same hook).
   - `README.md` line 134 and Article XVII lines 923-934: folder and file
     names (`workspace_agents/`, the starter set) that differ from what the
     grail ships.
3. **Tier 2 decision (the owner's).** Decide whether
   `rapp_swarm/function_app.py` should load on every request and only
   `*_agent.py` files, like Tier 1, and whether `rapp_swarm/build.sh` should
   stop copying subfolders. Any code change needs its own proposal and review.
   Until then, Tier 2 stays refused by default.

## Rollback

Revert the amendment commit. Every change is an additive note, and the
receipts are in the same commit, so a revert restores the earlier bytes
exactly and leaves the receipts consistent. No runtime behavior changes, so
nothing outside the repository needs rolling back. Before a merge, deleting
the experimental branch is enough.

## References

- [`CONSTITUTION.md`](../../CONSTITUTION.md): Article I, Article III.7,
  Article XVII, Article XVIII, Article XX, Article XXV, Article XXVI,
  Article XXVIII (.3, .4, .6), Article XXX.2 and Article LV.4.
- Precedent: the "Amendment (2026-07-08)" notes in Articles XLVI and XLVII.
- Grail loader: `rapp_brainstem/brainstem.py` lines 1202-1205, pinned by
  `KERNEL_PIN.json` and checked by `check_kernel_pin.py` (see also
  `KERNEL_TREE.md`).
- Tier 2: `rapp_swarm/function_app.py` lines 266, 525-542 and 616-660;
  `rapp_swarm/build.sh` lines 62-93 and 112-130.
