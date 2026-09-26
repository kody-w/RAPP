# Proposal 0003 — Bring the three non-conformant eggs to RAPP/1

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). This proposal changes none of
> them. It re-frames two retired egg copies without changing their identity,
> and it retires one placeholder invite. It changes no egg address, no rappid,
> no grail byte, no owner-authorized record and no owner value, and it does
> not make this repository fully conformant.

## Status

**Draft** until the maintainer merges pull request #121. That merge accepts
this proposal (Articles XXVIII.4 and XXX.2). The same pull request also
carries both parts, so the same merge implements them.

Once it is merged, this Status should read **Implemented: Part A and Part B,
pull request #121**. If the maintainer takes only one part, it should read
**Implemented in part: Part A, pull request #121; Part B withdrawn** (or the
same with the parts swapped). A pull request cannot record its own merge, so
a one-line documentation follow-up (Article XXVIII.2) sets that line.

The maintainer (@kody-w) is asked to authorize two separate parts:

- **Part A.** A one-time, identity-preserving re-framing of the two retired
  `cubby-rapp-installer.egg` copies. It asks the maintainer to **waive**, for
  this framing change only, the rules that keep those copies immutable,
  including the "Issue-ready immutable Cave residual" in
  `RAPP1_OWNER_ACTIONS.md`. It is not the independently authorized
  replacement artifact that the residual waits for, and it closes nothing.
- **Part B.** Retiring the placeholder Commons invite
  `pages/tutorials/commons.egg` now, before the owner-signed reissue. This
  re-sequences section 3 of `RAPP1_OWNER_ACTIONS.md` (retire first, reissue
  later). The reissue itself stays an open owner-only action.

The owner asked for the parts of RAPP/1 that are already in force to pass the
RAPP/1 checker without drift, through each repository's own change process.
Several repository rules forbid these edits unless the maintainer relaxes or
waives them (see "Rules this proposal asks the maintainer to relax or
waive"). This proposal is that request. It grants nothing by itself. It uses
this repository's front door for a material change (Article XXIX): a written
proposal and an ordinary pull request. An AI agent drafted it on the branch
`experimental/rapp1-drift-eggs` and opened that pull request. It merges
nothing. Merging is the maintainer's decision (Article XXVIII.4, Article
XXX.2).

**One pull request, three separable commits.** Article XXVIII.3 asks for a
migration with one pull request per step. This pull request instead carries
the proposal and its two steps as three separate commits. Each part is small
(two files re-framed; one file removed), the evidence for each part is checked
against the bytes of its own commit, every commit passes every gate on its
own, and the maintainer can judge the whole change, with its evidence, in one
review. If the maintainer prefers one pull request per step, Migration says
how to split it.

**Numbering.** Proposal 0001 (pull request #119) is merged on `main`, and
proposal 0002 (branch `experimental/proposal-0002-tier2-parity`) is a draft
from another workstream. This proposal is therefore 0003.

## Context

### The finding

The RAPP/1 checker `rapp_check.py` at
`kody-w/rapp-1@591e014ad39e223b00ab343ae26e5d9a867ebeee` reports **DRIFT** for
`main` at `8afc9733e20ccf7e579a58028c29ab9c207087fa`. It has exactly three
findings, all under rule "§9 egg":

| Artifact | Finding |
|---|---|
| `cave/cubbies/kody-w/eggs/cubby-rapp-installer.egg` (retired copy) | `parse: ZIP local and central UTF-8 flags must match exactly` |
| `cave/rapplications/rapp-installer/cubby-rapp-installer.egg` (retired copy) | the same |
| `pages/tutorials/commons.egg` (retired placeholder) | `§10: invite verification requires estate_owner_rappid` |

Everything else it checks passes: five `rappid.json` records (one is a plant
template that the checker exempts from §6.1) and
`pages/tutorials/sample-session.egg`.

### The two cubby egg copies (Part A)

The two retired copies are byte-identical:

- 526,007 bytes, SHA-256
  `38ce5e8f1236b584eb3c6d4a6663ce46a0ff73c06599628d87fe610e035fb18b`;
- an unsigned `rapp/1-egg` (`sig: null`), variant `rapplication`, rappid
  `rappid:@kody-w/rapp-installer:7d9a33a14ef9fbe2ec8d74aca65ba8de7536aaffe4ec1761ff5b1562f1b26d63`;
- egg address
  `21289721de93122c5ad504175de75aa27052e253b521470dd0461252bc4f86c2`;
- 44 members plus `manifest.json`, so 45 ZIP entries.

The manifest and every member are correct. Every member hashes to its
manifest entry. The only defect is the ZIP framing. In all 45 local headers and
all 45 central-directory headers, bit 11 of the general-purpose flag (the
UTF-8 name flag) is 0. RAPP/1 §9.1 requires "UTF-8 filename flag set".

Both copies come from commit `b824965a0297b133d04bd556f6d9726de9a2fefa`
(2026-07-15, "§9: re-pack cartridges to rapp/1-egg"). An older rapp-1
`pack_egg` produced them. It set bit 11 on the entry before writing it, but
CPython's `zipfile` clears the flag field when it starts writing an entry, so
the bit never reached the archive. rapp-1 fixed its packer in commit
`67673cbd71d5ab999016215943824fafa724886e` (2026-08-29): it now sets the bit
while it encodes the headers.

**Why not `egg_repack.py`.** rapp-1's `egg_repack.py` is a migration tool for
legacy cartridges. It is not identity-preserving for an egg that is already
`rapp/1-egg`: it re-mints it. Run on this egg at `591e014`, it turns the
`rapplication` into an `organism`, rewrites `rappid.json`, adds `soul.md`,
grows the file to 526,209 bytes, and changes the egg address from
`21289721…` to `ad72766c…`. So Part A calls rapp-1's reference packer
`rapp.pack_egg` directly, with the egg's own manifest values and member bytes.

**Re-framing with the reference packer** (rapp-1 `rapp.py` at `591e014` on a
POSIX host; CPython 3.9, 3.11, 3.13 and 3.14 on macOS give the same bytes):

| Check | Result |
|---|---|
| Length | 526,007 bytes, unchanged |
| Changed bytes | exactly 90 per copy: the high byte of the flag field in each of the 45 local and 45 central headers, `0x00` to `0x08` |
| Manifest | value-equal, and its `manifest.json` bytes are identical |
| Members | all 44 byte-identical, same order |
| Egg address | `21289721de93122c5ad504175de75aa27052e253b521470dd0461252bc4f86c2`, unchanged |
| rapp-1 `verify_egg` at `591e014` | passes (it failed at `parse` before) |
| Fixed point | packing the result again gives the same bytes |
| New SHA-256 | `01468b160d6b96f92fe05f98169498db47592385ce7a6dd4930fd0ba016aa105` |

**What RAPP's own consumer says.** `rapp1_core.egg.inspect_egg` is this
repository's own RAPP/1 egg inspector. It is stricter than rapp-1 at
`591e014`, and it does not accept these eggs before or after re-framing:

| Framing | `rapp1_core` result |
|---|---|
| Current bytes | `invalid-zip-metadata`: "central entry is not stored/epoch/UTF-8/no-extras" (the flag defect) |
| rapp-1 reference framing (this proposal) | `invalid-zip-metadata`: "ZIP bytes differ from the deterministic RAPP encoding" |
| `rapp1_core`'s own ZIP encoding of the same entries | `inviable-rapplication`: "rapplication contains a path outside its ratified layout" |

The re-framing removes the defect that both implementations detect. The two
refusals that remain come from two places where the implementations read the
standard differently. Neither can be closed by re-framing:

1. **Container header fields.** §9.1 lists stored entries, `contents` order,
   the 1980 timestamps, no extra fields and the UTF-8 flag, and concludes that
   two conformant packers emit byte-identical eggs. It does not fix the
   central directory's "version made by" or the external file attributes.
   rapp-1's `pack_egg` uses CPython's `zipfile`. On a POSIX host it writes
   "version made by" `0x0314` and the file mode `0o600` in the external
   attributes; on Windows it writes `0x0014`, so its own bytes depend on the
   host. `rapp1_core` writes `0x0014` and `0`, and refuses any other bytes.
2. **The `rapplication` layout.** §9.2 says a `rapplication` "MUST include
   `rappid.json` and exactly one `agent.py` at the root", and "MAY include one
   `ui.html` and files under `state/`". rapp-1 at `591e014` reads the MAY list
   as open. `rapp1_core` reads it as closed. These eggs also carry `HATCH.md`
   and the whole `cubby/` tree, so only a re-mint (a new address) could satisfy
   the closed reading.

Closing either one needs a change to a validation rule or to the standard. That
is outside this proposal. Both are reported for a standard decision. Until
then, `rapp1_core` keeps refusing these retired copies. That fits their state:
they are unsigned, unpublished and not distributable, and no authenticated
acceptance is possible for them.

### What changes for consumers (Part A)

Part A changes the verdict of one kind of consumer: one that relies on
rapp-1's structural check. Measured on both copies, with the before bytes read
from commit `b824965a0297b133d04bd556f6d9726de9a2fefa`:

| Consumer | Before | After |
|---|---|---|
| rapp-1 `verify_egg` at `591e014` (structural §9.3 checks; no signature, no registry) | refused at `parse` | **accepted**: `(True, None, "ok")` |
| `rapp_check.py` at `591e014` | a "§9 egg" finding on each path | no finding |
| `rapp1_core.inspect_egg` | refused: `invalid-zip-metadata` | refused: `invalid-zip-metadata` (see the table above) |
| `tools/import_peer_egg.py` | inspect `INVALID`; import `INVALID`, nothing imported | the same |
| `pages/tutorials/egg_hatcher_agent.py` | route `unknown`, not accepted, no effects | the same |
| `cave/rapplications/rapp-installer/hatch.py` | exits 1, because schema `rapp/1-egg` is not `brainstem-egg/2.3-cubby`; writes no file | the same |
| generic ZIP readers (`unzip -t`, CPython `zipfile`) | read all 45 entries | the same |

In plain terms:

- rapp-1's structural `verify_egg` now **accepts an unsigned egg**. It checks
  integrity and viability (§9.3). It authenticates nothing: an unsigned egg
  has no signature to check (§10), and Article LV.3 requires consumers to
  keep "structurally valid" apart from "authenticated and accepted".
- RAPP's own consumer, `rapp1_core`, **still refuses** both copies.
- Both copies stay **unsigned** (`sig: null`), **unpublished** and **not
  distributable**. `_config.yml` keeps both paths out of GitHub Pages (their
  Pages URLs return 404). `cave/super-rar/index.json` keeps the egg
  `accepted: false`, with fetch, install, execute, stream and publish all
  `false`. `installer/RETIRED_ARTIFACTS.json` keeps
  `publication_allowed: false`. Like every tracked file, the bytes stay
  readable through GitHub's raw transport, before and after; raw URLs are
  transport, not authority.
- **Authenticated acceptance still needs** an owner signature and the
  authenticated §13 registry. Neither exists, and this proposal creates
  neither.
- **The residual is untouched.** The egg still carries
  `cubby/rapplications/rapp-installer/hatch.py` (SHA-256
  `bc8a70b3bb8f168d55f97620a3cd477744fd374546338b52e9cbdf01369142af`, the
  same bytes as the prepared copy) and a root `agent.py` (SHA-256
  `acdccb947f9001bcff4f3e1b8bf84bb6b831522a2c7df0d6cffa3cbdae5bfc80`). That
  `agent.py` is byte-identical to the Cave `rapp_installer_agent.py` that
  commit `f6bf5ed` added and commit `d3d2623` retired; it hands out a
  `curl … | bash` one-liner. Part A changes neither file. The external-owner
  fix that the ledger asks for is still needed.

**Would anything fetch or hatch it?** No RAPP code path, page, bootstrap or
one-liner fetches or hatches either copy, before or after. The search covered
the egg's name, both paths, Pages and raw URLs into the Cave, file names built
as `cubby-<slug>.egg`, and every egg reader in the tree:

- The prepared `bootstrap.sh`, `bootstrap.ps1` and `serve.py` are
  410/exit-78 tombstones. The Pages one-liner quoted by the egg's `agent.py`,
  the prepared `manifest.json` and `HATCH.md`, and
  `cave/.well-known/rapp-cave.json` returns 404.
- In the tree, the original `bootstrap.sh` survives only inside the egg. Run
  by hand, it would fetch the raw copy from `main` and run the embedded
  `hatch.py`, which exits on the schema before it writes anything.
- `cave/agents/cave_agent.py` loads only `*_agent.py` files from a cubby's
  `agents/` folder, behind injected, authenticated effects, and otherwise
  reads only the Cave index. It never reads egg bytes.
- The grail's `/agents/import` accepts only `.py` files.
- rapp-1's only hatcher, `hatch_and_prove.py`, takes a pinned `estate` egg
  and hatches only the `organism` eggs inside it; it refuses a
  `rapplication`. rapp-1's `open_sealed_egg` is for `sealed` eggs only.

One route remains, and it is the residual's own: extract the archive with a
generic ZIP tool and run the extracted `hatch.py` in place. It worked before
Part A and works the same after it. That is why the residual stays open.

### The Commons invite (Part B)

`pages/tutorials/commons.egg` is a 443-byte JSON `invite`:

- SHA-256
  `2731c02f187701c1d07b3a7f5eed5e2073c203ffb4f6c08d00292894e3319a5d`;
- egg address
  `a03fa90289eaefcf1a6521cdc10ee17bc706a0bb353e688ad84135d684380fb7`;
- its `sig` member is a non-JWS migration placeholder, so it can never verify;
- its `target_url` is `https://kody-w.github.io/commons/`, which returns 404.

The ledger's audit-baseline table in `RAPP1_OWNER_ACTIONS.md` already calls it
the "Retired invite". Section 3's rule is: "Preserve the retired target
artifact only by path, SHA-256, and git history." Today section 3 retires it
only after the owner has issued a signed replacement.

The file is not live. GitHub Pages does not publish it (`_config.yml` excludes
it), and the retired hatch tutorial already points its download control at
`KERNEL_PIN.json`. What is left is a tracked blob that no verifier accepts:
rapp-1 at `591e014` refuses it, and `rapp1_core` refuses it as
`invalid-jws`.

**Checker gap.** No invite can pass `rapp_check.py` at `591e014`. Its command
line calls `rapp.verify_egg` without `estate_owner_rappid` and without a
signature verifier, and `verify_egg` refuses every invite without both (§10).
So even the owner-signed replacement would be reported as DRIFT by that
checker. This is a gap in the checker, not in the invite. It is reported for a
checker decision. It matters here because it decides where the future signed
invite should live (see Part B, step 5).

### Rules this proposal asks the maintainer to relax or waive

Each row is the maintainer's call. This pull request grants none of them.

| Rule | What it says | Part | What is asked |
|---|---|---|---|
| `CLAUDE.md` rule 2, `.github/copilot-instructions.md` ("Current instructions"), `llms.txt` (AI clients "must not … modify the immutable grail, prepared Cave installer, archives"), and the agent prompts `.github/prompts/test-agent.prompt.md` ("never edit … the prepared `cave/rapplications/rapp-installer/**` snapshot"; "Never … modify prepared Cave installer bytes") and `.github/prompts/write-agent.prompt.md` ("the prepared … snapshot are read-only") | never edit the prepared `cave/rapplications/rapp-installer/**` subtree | A | change one file there, the egg copy, in its ZIP framing bytes only |
| the same rules' "archives" clause | never edit archives | A | re-frame both egg copies. `cave/cubbies/kody-w/eggs/cubby-rapp-installer.egg` is outside the prepared subtree, but it is one of the five ZIP-compatible archives that `RAPP1_STATUS.md` counts (the two egg copies and the three Power archive copies). The Power archives are not touched |
| `installer/RETIRED_ARTIFACTS.json` | `repacking_allowed: false`; both copies are `immutable_eggs`; the prepared snapshot has `modification_allowed: false` | A | one dated exception, `proposal-0003-part-a` in `repacking_exceptions`, also named in `prepared_snapshot.modification_exceptions`. Both flags stay `false`. The two `immutable_eggs` hashes move to the new bytes |
| `RAPP1_ADAPTATION_INVENTORY.json`: `HISTORY-001` ("Legacy archives and eggs remain exact and unaccepted"; acceptance test "All archive and retired-test bytes remain exact"; "without altering archived bytes"; `exact-bytes` data exhaust), `CAVE-001` ("the prepared Cave snapshot remains immutable and non-distributable"), and the `exact-bytes` data exhaust of `EGG-001`'s historical egg corpus | the historical archives and eggs, the prepared snapshot included, keep their exact bytes | A | the one ZIP-framing exception. Part A qualifies those four sentences with it; the earlier exact bytes stay in git history at `b824965` |
| `RAPP1_OWNER_ACTIONS.md`, "Issue-ready immutable Cave residual" | this target must not patch the prepared clone or any egg or archive containing it; a replacement payload goes only through the owner's authenticated artifact process; the immutable copies stay byte-identical until an independently authorized replacement artifact is adopted | A | an explicit **waiver** for this framing-only change, which only the maintainer can grant. It is not the owner's authenticated artifact process and not a replacement artifact: nothing is signed, adopted or published, and the residual stays open. A dated note in that section records the waiver. `RAPP1_OWNER_ACTIONS.json` has no record for this residual, so nothing is added there |
| `CLAUDE.md` rule 5 and `.github/copilot-instructions.md` "Adapt, do not kill"; in `RAPP1_ADAPTATION_INVENTORY.json`, `policies.adapt_dont_kill.preserve_data_exhaust`, the exact-bytes `data_exhaust` of `EGG-001`, and `OA-INVITE` ("preserve invalid predecessor"; "the predecessor remains visible but never accepted"), and `EGG-001`'s acceptance test "Legacy eggs remain visible and accepted=false" | Commons samples are data exhaust: preserve the complete artifact, disable only the exact unsafe edge, and never replace useful content with a blank refusal or a tombstone | B | remove the Commons sample from the tree. Section 3's own retirement rule ("path, SHA-256, and git history") is the adaptation here: it is the ledger's more specific rule for this exact artifact. The exact 443 bytes stay in git history at `b824965` (exact-bytes fidelity), and its path, SHA-256, size and address stay visible in the records. Its substantive facts stay recorded in `known_evidence.commons_invite`: the Commons rappid it names, its wrong 404 target URL, and the reason its signature member can never verify. Nothing replaces it with a refusal or a tombstone, and it had no unsafe edge left to disable: Pages already excluded it, and no verifier accepts it |
| `installer/RETIRED_ARTIFACTS.json` `immutable_eggs` | `pages/tutorials/commons.egg` is one of the immutable eggs | B | move its record from `immutable_eggs` to `removed_eggs` |
| `RAPP1_OWNER_ACTIONS.md` section 3, and `when` in `owner-reissue-commons-invite` | retire the placeholder only after the signed reissue, together with the link switch | B | re-sequence it: retire first, reissue later |

Two further rules are followed, not relaxed. Constitution Article XXVIII.1 is
why this proposal exists: Part A changes the bytes behind two raw paths, and
Part B deletes an egg and its raw path. `tools/check_rapp1_docs.py` refuses
*uncommitted* edits to its protected paths, which include both egg copies. The
committed state passes it, and that state is what is up for approval.

Every current statement that the prepared snapshot or the historical eggs
keep their exact bytes, and what happens to it:

- `cave/specs/SUPER_RAR.md` ("remains untouched and non-installing"): Part A
  adds "apart from the one ZIP-framing exception `proposal-0003-part-a`
  recorded in `installer/RETIRED_ARTIFACTS.json`".
- `RAPP1_ADAPTATION_INVENTORY.json`: the `CAVE-001` sentence and the three
  `HISTORY-001` sentences in the table above. Part A qualifies each with the
  same exception.
- `cave/README.md`, twice: "The prepared `cave/rapplications/rapp-installer/`
  bytes remain untouched and non-installing" in its current banner, and "The
  prepared `rapp-installer` subtree is preserved byte-for-byte as historical
  evidence" in its historical section. This pull request does not edit
  READMEs. If Part A is accepted, that README's owner should add the same
  qualification to both.
- The instruction files (`CLAUDE.md`, `.github/copilot-instructions.md`,
  `llms.txt` and the two agent prompts) state the rule itself. They stay as
  they are: the waiver is for this one change only.
- The dated audit guidance `POST-CONTAIN-CAVE` ("do not edit embedded/pinned
  archive bytes"), pinned in `tests/fixtures/rapp1-doc-scope.json` and
  `tools/check_rapp1_docs.py`, is a definition in the dated 691-row final
  `verify-rapp-files` report. It is not edited; it is covered by the same
  waiver.
- `immutable_prepared_snapshot: true` in `cave/rar/index.json` (written by
  `cave/tools/build_super_rar.py` and required by `tools/check_rapp1_docs.py`)
  classifies the snapshot. It stays true: the snapshot stays immutable, and
  this one exception is recorded in `installer/RETIRED_ARTIFACTS.json`.

**Nothing else is relaxed.** The grail bytes pinned by `KERNEL_PIN.json` stay
read-only (Article LV.4). No other file in the prepared subtree changes, and
no other archive or egg: the three Power archive copies and
`pages/tutorials/sample-session.egg` keep their bytes. No generated external
mirror changes, and no owner-authorized identity or trust record: no key,
signature, anchor, registry entry or re-anchor is created. No egg is signed
or published. No owner action is closed, no owner value is set, and the
residual's external-owner fix stays open. The pins and receipts that move
(the `cave/super-rar/index.json` pin in `tools/check_rapp1_docs.py` and
`tests/fixtures/rapp1-doc-scope.json`, and the path and byte receipts) are
recomputed from the new tree; no validation rule changes.

## Proposed change

### Part A — re-frame the two cubby egg copies

1. Replace the bytes of both copies with the rapp-1 reference-packer output
   described above: SHA-256
   `01468b160d6b96f92fe05f98169498db47592385ce7a6dd4930fd0ba016aa105`,
   526,007 bytes, egg address unchanged, all 44 members byte-identical.
2. In `installer/RETIRED_ARTIFACTS.json`, keep `repacking_allowed: false`.
   Record one dated exception in `repacking_exceptions`: this proposal, both
   paths, the before and after SHA-256 values, the length, the address, the
   member count, the 90 changed flag bytes, the packer pin, and the commit
   `b824965a0297b133d04bd556f6d9726de9a2fefa` whose tree holds the before
   bytes. Name the same exception, `proposal-0003-part-a`, in a new
   `prepared_snapshot.modification_exceptions` list;
   `modification_allowed` stays `false`. Update the two `immutable_eggs`
   hashes. The exception covers no other artifact.
3. Add a dated note, linked to this proposal, to the "Issue-ready immutable
   Cave residual" section of `RAPP1_OWNER_ACTIONS.md`. It records the waiver
   and its limits: the copies stay unsigned, unpublished and not
   distributable; the members, including `hatch.py`, are unchanged; the
   external-owner fix and its acceptance still apply; and from then on the
   copies stay byte-identical to the re-framed bytes until an independently
   authorized replacement artifact is adopted. `RAPP1_OWNER_ACTIONS.json` has
   no record for this residual, so it is not changed.
4. Regenerate `cave/super-rar/index.json` with
   `python3 cave/tools/build_super_rar.py --render super-rar`. The builder
   already keeps the old SHA-256 `38ce5e8f…` as a historical observation.
   Update the pinned SHA-256 of that index in
   `tests/fixtures/rapp1-doc-scope.json` and `tools/check_rapp1_docs.py`, as
   commit `d5ed57c` did.
5. Add a test to `tests/test_distribution_containment.py`. It reads the old
   bytes from git history and proves that they hash to the recorded "before"
   value, that only the 90 flag bytes differ, that the manifest and every
   member are identical, and that the address is unchanged. It also checks
   that `prepared_snapshot` and the ledger note name the exception.
6. Refresh the byte receipt in `tests/fixtures/rapp1-doc-scope.json`.

No other file under `cave/rapplications/rapp-installer/` changes. The retired
`hatch.py` residual is unchanged: it is still an external-owner fix, and the
members that carry it are byte-identical.

**Why not use `rapp1_core`'s encoder instead.** Its `pack_egg` refuses to pack
this egg (closed `rapplication` layout). Its ZIP encoder would change 135 more
header bytes per copy, and `rapp1_core` would still refuse the result, now on
layout. It would also stop being a fixed point of rapp-1's reference packer.
The reference packer is the smallest change that removes the only defect the
checker reports.

### Part B — retire the placeholder Commons invite now

1. Remove `pages/tutorials/commons.egg` from the tree (`git rm`).
2. Preserve it only by path, SHA-256 and git history, as section 3 requires:
   - `installer/RETIRED_ARTIFACTS.json` moves its record from
     `immutable_eggs` to `removed_eggs`, with the path, SHA-256, length,
     address, the commit `b824965a0297b133d04bd556f6d9726de9a2fefa` whose tree
     holds the bytes, and a link to this proposal;
   - `RAPP1_OWNER_ACTIONS.json` adds the same commit and link to
     `known_evidence.commons_invite`, keeps every `retired_*` value, and drops
     the path from `current_evidence.current_path_hashes`, because it is no
     longer a current path.
3. Update every live reference: the `EGG-001` surface and the primary egg rule
   in `RAPP1_ADAPTATION_INVENTORY.json`; the owner-action tests, which now read
   the retired bytes from git history; and the record counts in
   `tests/test_distribution_containment.py` and `tests/run-tests.mjs`. Two new
   tests in `tests/test_distribution_containment.py` prove that the bytes
   survive only in git history and that nothing live names the file. The
   second one reads every tracked text file (UTF-16 with a byte-order mark
   is decoded; other binary files, such as archives, eggs and images, are
   skipped). HTML goes through Python's `html.parser`, so it sees what a
   browser may follow or run, quoted or not: the URL attributes `action`,
   `background`, `cite`, `data`, `formaction`, `href`, `imagesrcset`,
   `longdesc`, `manifest`, `ping`, `poster`, `src`, `srcdoc`, `srcset`,
   `style` and `xlink:href`, `<param>` values, every event handler (`on*`),
   every `<meta>` `content` (so a refresh redirect counts), and inline
   scripts and styles. Every other text file, Python and extensionless
   scripts included, is checked line by line, and each file once more as a
   whole with its line breaks removed. Each value and line is checked as
   written, after HTML entities and percent-encoding are decoded, and with
   tabs and line breaks removed (browsers drop them from URLs), so
   `commons&#46;egg`, `commons%2Eegg`, `comm&#10;ons.egg` and a name split
   across two lines all count. What it cannot see:
   a name built at run time (string concatenation or escapes in code), and
   mentions inside the exempt files. It exempts only the four retirement records (this
   proposal, `installer/RETIRED_ARTIFACTS.json` and both owner-action
   ledgers), the two tests that name the retired path on purpose
   (`tests/test_distribution_containment.py` and
   `tests/test_rapp1_owner_actions.py`), and the `_config.yml` exclude line.
   These mentions stay on purpose:
   - `_config.yml` keeps excluding the retired path from Pages. It is a guard
     that stops the path from being published again, not a reference.
   - `pages/tutorials/hatch-egg.html` keeps `data-historical-href="commons.egg"`,
     the download label and the `hatch` command example. They are inert
     history in the retired tutorial (text, not a link or a script), and its
     live link already goes to `KERNEL_PIN.json`.
   - `tests/rapp1_core/test_eggs.py` uses the name `kody-w--commons.egg` for a
     synthetic test member, not this file, and the test's name rule does not
     match it.
4. Keep the owner action `owner-reissue-commons-invite` open and unchanged in
   substance. It stays `owner-action-required`, every owner input stays
   `null`, and its acceptance tests are unchanged. Only sentences made stale by
   the retirement change: tense, and the order "retire after reissue" becomes
   "retire first, reissue later". The audit-baseline table, which describes
   the `f71810d` baseline, is not changed. Blocker 3 in `RAPP1_STATUS.md`, the
   signed replacement invite, stays open.
5. The future signed invite is a new artifact with a new address. It goes to
   the owner-approved path (the ledger's candidate is
   `pages/tutorials/artifacts/commons-invite.egg`) and the Commons well-known
   path, never back to the retired path. Because of the checker gap above,
   `rapp_check.py` at `591e014` will report any invite in this tree as DRIFT
   until the checker can take the owner anchor and a signature verifier. Place
   it knowing that.
6. Refresh the path and byte receipts in `RAPP1_ADAPTATION_INVENTORY.json` and
   `tests/fixtures/rapp1-doc-scope.json`.

### What does not change

- No egg address, rappid, manifest, member or signature changes.
- No grail byte, no README, and no file under `rapp_brainstem/`.
- `RAPP1_STATUS.md` is unchanged. The repository stays **NOT YET FULLY RAPP/1
  CONFORMANT**, and its three owner blockers stay open. Its audit counts (such
  as "5 ZIP-compatible archives … and 2 JSON eggs") are dated snapshots and
  stay as they are.
- No key, signature, anchor, registry entry, re-anchor or owner value is
  created or filled in.
- The "Issue-ready immutable Cave residual" stays open, and its
  external-owner fix is still needed.
- `rapp1_core`'s validation rules are unchanged.

## Migration

The pull request has three commits, one per step. Each commit passes every gate
on its own:

1. **Proposal.** This file and the receipts for one new tracked document.
2. **Part A.** The re-framing, its exception record and prepared-snapshot
   reference, the dated waiver note in the residual section of
   `RAPP1_OWNER_ACTIONS.md`, the regenerated Cave index and its pins, the
   test, and the byte receipt.
3. **Part B.** The retirement, the ledger and inventory facts, the tests, and
   the receipts.

**Taking one part only.** To take Part A without Part B, merge only the first
two commits; nothing else changes. To take Part B without Part A, drop the
Part A commit and re-apply the Part B commit on the proposal commit. That
re-application stops on the two adjacent receipt lines `tracked_paths` and
`stable_tracked_bytes` (see Rollback): take either side, then refresh the
receipts.

**One pull request per step (Article XXVIII.3).** If the maintainer wants the
steps split, this pull request keeps only the proposal commit. After it
merges, Part A and Part B each become their own pull request: a branch from
the new `main` that cherry-picks the matching commit and refreshes the
receipts. The Part A pull request then sets Status to "Implemented in part",
and the Part B pull request sets it to "Implemented".

**Receipts.** The receipts are recomputed, never hand-picked:

- `cave/super-rar/index.json`:
  `python3 cave/tools/build_super_rar.py --render super-rar`, then
  `--check`. Its SHA-256 is pinned in `tests/fixtures/rapp1-doc-scope.json`
  and `tools/check_rapp1_docs.py`.
- `RAPP1_ADAPTATION_INVENTORY.json`: the path counts and path-set digests use
  the helpers in `tests/test_adaptation_inventory.py`.
- `tests/fixtures/rapp1-doc-scope.json`: the tracked-path, byte and document
  counts use the rules in `tools/check_rapp1_docs.py`.

**Re-derive Part A.** Anyone can recompute the new bytes from a public
checkout of `kody-w/rapp-1` at `591e014ad39e223b00ab343ae26e5d9a867ebeee`,
without other tooling. Save this as `reframe.py` and run
`python3 reframe.py <rapp-1 checkout> <old egg>` on a POSIX host, with the old
bytes taken from `b824965a0297b133d04bd556f6d9726de9a2fefa`. It prints the
unchanged address and the new SHA-256. On a Windows host CPython writes a
different "version made by" byte, and the 90-byte assertion fails closed.

```python
import hashlib, io, json, sys, zipfile
sys.path.insert(0, sys.argv[1])  # a kody-w/rapp-1 checkout at 591e014
import rapp
old = open(sys.argv[2], "rb").read()
with zipfile.ZipFile(io.BytesIO(old)) as z:  # tolerant read of the old bytes
    names = z.namelist()
    manifest = json.loads(z.read("manifest.json"))
    files = {name: z.read(name) for name in names[1:]}
assert names == ["manifest.json"] + [c["path"] for c in manifest["contents"]]
assert all(rapp.Hb("rapp/1:egg", files[c["path"]]) == c["hash"] for c in manifest["contents"])
new = rapp.pack_egg(manifest["variant"], manifest["rappid"], manifest["created_utc"],
                    files=files, payload=manifest["payload"], sig=manifest["sig"])
assert rapp.verify_egg(new)[0] and rapp.read_egg(new) == (manifest, files)
changed = [i for i in range(len(old)) if old[i] != new[i]]
assert len(new) == len(old) and len(changed) == 90
assert all(old[i] == 0x00 and new[i] == 0x08 for i in changed)
print(rapp.egg_address(manifest), hashlib.sha256(new).hexdigest())
```

**Validation.** On each commit: `python3 tests/run_restoration_acceptance.py`
(which runs `tests/run_rapp1_conformance.py`), `python3 check_kernel_pin.py`,
`python3 tools/check_rapp1_docs.py`,
`python3 cave/tools/build_super_rar.py --check`,
`python3 cave/tests/test_catalog_containment.py`, `node tests/run-tests.mjs`,
`node tests/vault-check.mjs`, `bash tests/e2e/08-html-pages.sh`, and the pull
request's CI, which also runs rapp-drift-lint. After Part B, `rapp_check.py`
at `591e014` reports **COMPLIANT** for the tree.

## Rollback

- **Part B.** Revert its commit. The 443 bytes come back exactly from git
  history, and the ledger returns to the original order of section 3. This
  does not turn joining on: the placeholder never verified.
- **Part A.** Revert its commit. The old bytes come back exactly from git
  history, and the exception record, the prepared-snapshot reference and the
  ledger note go away. The eggs are not published, so nothing outside the
  repository needs rolling back.
- **Order and receipts.** Reverting the newest commit restores the tree before
  it exactly, so its receipts stay valid. Reverting Part A while Part B stays
  (like taking Part B without Part A) is not clean: both parts change the byte
  receipt `stable_tracked_bytes` in `tests/fixtures/rapp1-doc-scope.json`, and
  git stops on it and the adjacent `tracked_paths` line, which Part B also
  changes. Take either side, refresh the receipts as described
  under Migration, and run the validation again. The other files merge
  cleanly, because each part keeps its own tests and records and their hunks
  do not touch.
- **Before a merge.** Close the pull request or delete the branch.

## References

- [`CONSTITUTION.md`](../../CONSTITUTION.md): Article XXVIII (.1, .2, .3,
  .4), Article XXIX, Article XXX.2, and Article LV (.2 item 4, .3, .4, .5).
- [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
  [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md) ("Audit coverage and checker
  limitation", for the archive count, and "Structural validation is not
  authenticated acceptance").
- [`RAPP1_OWNER_ACTIONS.md`](../../RAPP1_OWNER_ACTIONS.md): section 3 and
  "Issue-ready immutable Cave residual";
  [`RAPP1_OWNER_ACTIONS.json`](../../RAPP1_OWNER_ACTIONS.json):
  `known_evidence.commons_invite` and `owner-reissue-commons-invite`.
- [`installer/RETIRED_ARTIFACTS.json`](../../installer/RETIRED_ARTIFACTS.json),
  [`CLAUDE.md`](../../CLAUDE.md) rules 2 and 5, and
  [`.github/copilot-instructions.md`](../../.github/copilot-instructions.md)
  ("Current instructions", including "Adapt, do not kill").
- [`RAPP1_ADAPTATION_INVENTORY.json`](../../RAPP1_ADAPTATION_INVENTORY.json):
  `policies.adapt_dont_kill`, `EGG-001` and `OA-INVITE`.
- RAPP/1 rev-5 `SPEC.md` at `d2cd5abed48d3f52b86bbb975ac3558286d1db41`:
  §5, §9.1, §9.2, §9.3 and §10.
- The checker and reference implementation at
  `kody-w/rapp-1@591e014ad39e223b00ab343ae26e5d9a867ebeee`: `rapp_check.py`,
  `rapp.py` (`pack_egg`, `read_egg`, `verify_egg`, `egg_address`) and
  `egg_repack.py`.
- Source of the current egg bytes: commit
  `b824965a0297b133d04bd556f6d9726de9a2fefa`. The Cave
  `rapp_installer_agent.py` that the egg's `agent.py` matches: added in
  `f6bf5ed`, retired in `d3d2623`.
- Format: proposal 0001, pull request #119.
