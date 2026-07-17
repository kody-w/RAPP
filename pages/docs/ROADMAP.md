# RAPP Roadmap

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). Roadmap work must migrate or
> retire incompatible forms rather than preserve them indefinitely.

Post-v1 product directions retain the single-file agent rule, but the former
local v1 wire contract in [`SPEC.md`](./SPEC.md) is superseded for protocol
matters by RAPP/1 rev-5.

---

## Recently shipped

> **Historical release ledger.** Dated shipped sections preserve what the
> repository released and called canonical at that time. Retired identity,
> frame, wire, and egg forms in those records are superseded migration
> evidence, not current implementation instructions.

### 2026-05-10 — `.egg` cartridge unification + tethered vBrainstem

**Status:** SHIPPED. See [SPEC.md §18.10–§18.12](./SPEC.md).

- **Egg-cartridge family.** Five variants under one `.egg` extension, one rappzoo Pokédex shelf, one introspection-routing kernel agent ([`egg_hatcher_agent.py`](../../rapp_brainstem/agents/egg_hatcher_agent.py)): `brainstem-egg/2.2-organism` (shipping), `2.2-rapplication` (shipping), `2.3-session` (shipping), `2.3-neighborhood` (planned), `2.3-estate` (planned).
- **Tethered vBrainstem.** Public surface at [`pages/vbrainstem.html`](../vbrainstem.html). Multi-participant browser-tab brainstem with QR-pair WebRTC handshake (PeerJS broker + ECDSA P-256 keypair + 6-digit safety code), three exchangeable LLM backends (localhost default / `?brainstem=URL` / `?copilot=1` via Doorman + Pyodide-loaded Python agents), Coordinator-driven debate-demo workflow, transcript-as-cartridge round-trip.

> **Current supersession:** do not extend the legacy schema/type hatcher.
> Replace that path with RAPP/1 §9 variant dispatch and complete §9.3
> verification; identity continuity additionally requires §§6, 10, and 13.

**Historical next step (superseded):** automate `neighborhood` and `estate` hatch paths in `egg_hatcher_agent.py` (currently they return manual instructions). When those land, .egg = absolute parity across organism / rapplication / session / neighborhood / estate.

### 2026-05-18 — Neighborhood-egg snapshot/hatch, multi-carrier

**Status:** SHIPPED. See [[Neighborhood Egg — Snapshot and Hatch]] and [`NEIGHBORHOOD_EGG_SPEC.md`](./NEIGHBORHOOD_EGG_SPEC.md).  Implementation in [`kody-w/rappLocalFirstFleet`](https://github.com/kody-w/rappLocalFirstFleet).

- **Matched-pair agents.** `NeighborhoodSnapshot` (snapshot / inspect / list_eggs) + `NeighborhoodRun` (inspect / plan / hatch / list_eggs).  Single-file, BasicAgent contract, hot-loaded into any brainstem.
- **Cross-substrate carriers.** The cartridge format is substrate-agnostic; per-peer carrier is selected by which coordinate fields are present in `~/.rapp/peers.json`:
  - **LAN-SSH** ✅ shipping — `ssh_user` + `ssh_host`; `tar -czf -` over SSH for capture, `tar -xzf -` for restore.
  - **GitHub-neighborhood** ✅ shipping (read + opt-in PR write) — `github_neighborhood: "<owner>/<repo>"`; reads `members.json`, parses each member's v2 rappid (per [`ESTATE_SPEC.md`](./ESTATE_SPEC.md) §1) → owner/repo/hash, fetches the repo tree via `gh api`, packs as a tarball.  PR-mode write is opt-in (`github_write_enabled=true`), never touches `main` directly.  `github_write_dry_run=true` previews the diff.
  - **Tailscale** ✅ shipping (implicit) — uses LAN-SSH with `ssh_host` resolving over the Tailnet.  No carrier code change.
- **Two hatch targets.**  `target=in-place` (default) pushes peer assets back via each peer's carrier.  `target=local-simulate` extracts peer assets into `~/.rapp/simulated/<peer>/twins/<hash>/` on the host doing the hatch — no network, full offline replay.
- **Safety model.**  Hatch defaults to gap-filling.  Per-category opt-in flags (`overwrite_agents`, `overwrite_core`, `overwrite_data`, `overwrite_global_state`, `overwrite_twins`, `overwrite_peer_twins`) for destructive operations.  `plan` action does a read-only dry-run.
- **Allowlist/denylist for global state.**  `rappid.json`, `estate.json`, `self_healing_cron_state.json` travel; `private-estate-secret`, `keys/`, `venv/`, `logs/` never do.  Secrets stay home.
- **Verified end-to-end.**  Cross-device destructive restore on two LAN peers (RappterTwo, MacBookPro3) + GitHub capture from `kody-w/rapp-commons` walking its `members.json` → `kody-w/RAPP` → 1107-file tarball → simulated locally.  Github-write dry-run against the live RappCommons egg.

### 2026-05-18 — The Brainstem Mandate

**Status:** SHIPPED.  See [`BRAINSTEM_MANDATE.md`](../../BRAINSTEM_MANDATE.md).  Foundational directive written in deliberate parallel to the 2002 API Mandate.  The local brainstem is the platform surface; APIs are not.  Eight tenets, declarative, with consequences.  Linked from the README front matter.

---

## Neighborhood-egg — remaining carrier work

**Status:** proposed · **Depends on:** neighborhood-egg snapshot/hatch (shipped 2026-05-18)

Three carriers left after LAN-SSH + GitHub + Tailscale.  Each enables a different substrate the neighborhood-egg format can ride on without changing the format itself.

### HTTPS-with-auth carrier

**Why:**  Brainstems behind a Cloudflare tunnel, behind an Auth-Cascade front gate, behind a corporate proxy — anywhere SSH isn't viable but HTTPS-with-token is.  Closes the substrate ladder for the "I'm a brainstem operator but my peer's network is locked down" case.

**Shape:**

- Peer entry declares `auth_url: "https://peer.example.com/api"` and `auth_token_env: "PEER_TOKEN"` (env var name holding the token, not the token itself).
- **Receiver side:** add a `RemoteTwinSnapshot` agent behind the exact RAPP/1
  §8 `POST /chat` boundary. Its registered actions cover list, snapshot, plan,
  and restore; destructive restore remains opt-in and authenticated.
- **Carrier side** (in NeighborhoodSnapshot / NeighborhoodRun): invoke the
  agent through exact `/chat`; the HTTPS tunnel does not add sibling protocol
  capability routes.
- Bearer tokens live in operator env, **never in `peers.json`**.

**Acceptance:**
- Snapshot from a brainstem on Mac A → captures twins from a brainstem on Mac B reachable only via Cloudflare Tunnel HTTPS.
- Hatch with `target=in-place` pushes back via the same HTTPS+token path.
- Secrets denylist holds: token env-var names are recorded in the egg; values never are.

### `github_repos` carrier (individual twin repos, no neighborhood wrapper)

**Why:**  Today the GitHub carrier requires a *neighborhood* repo (a repo with `members.json`).  Sometimes you just want to snapshot a few individual twin repos directly — no neighborhood envelope.  The selector already exists in `_select_carrier()` (`github_repos: ["owner1/repo1", "owner2/repo2"]`) but the implementation branch isn't wired.

**Shape:**

- Each repo in `github_repos` is one twin.
- Selector returns `"github-repos"`; the snapshot loop dispatches to a sibling of `github-neighborhood` that skips the `members.json` walk and goes straight to fetching each listed repo.
- The hatch write path mirrors github-neighborhood (clone + apply + PR + opt-in `github_write_enabled`).

**Acceptance:**  Snapshot a peer entry with `github_repos: ["kody-w/aibast-twin", "kody-w/heimdall"]` → both repos captured as twins, manifest's `peers[].twins` lists both, local-simulate extracts both correctly.

### Boot-simulated-peers

**Why:**  Today `target=local-simulate` extracts peer twin workspaces into `~/.rapp/simulated/<peer>/twins/<hash>/` but **does not boot them**.  Simulated twins are file-level replays only.  For a true offline-replay demo (every peer twin queryable like the real one), the simulated twins should boot on local ports the local Twin agent knows about.

**Shape:**

- New flag on `NeighborhoodRun.hatch`: `boot_simulated_peers=true`.
- Each simulated twin gets a rebased local port — `simulated_port = base + offset_from_peer_index*100 + twin_index`, or some deterministic-but-collision-safe scheme.
- The Twin agent gets a sibling registry path (`~/.rapp/simulated/<peer>/.brainstem_data/twin_registry.json`) so `Twin.list` can enumerate simulated peers alongside real ones, namespaced as `<peer>/<name>`.
- `Twin.chat` works against simulated twins same as real twins.

**Acceptance:**  `target=local-simulate` + `boot_simulated_peers=true` → every captured peer twin is reachable via `Twin.chat` on this Mac, on a port the runner picked.  The originals on the real peers remain untouched.

### Real github-write PR acceptance test

**Why:**  The github-write code path is verified via dry-run.  No PR has yet been opened by it.  Before recommending it for non-trivial use, run it end-to-end against a real sandbox repo and inspect the resulting PR for sanity (branch naming, commit message, file diff layout, PR body framing).

**Shape:**  pick a private sandbox repo, capture it as a github-peer, modify a file in the simulated workspace, hatch with `github_write_enabled=true`, review the PR.

### SelfHealingCron pattern doc + cron daemon

**Status:** half-shipped 2026-05-18.

`SelfHealingCron` agent ships (canonical home `kody-w/rappLocalFirstFleet`, also available on the local brainstem).  Action surface: setup / check / status / history / teardown.  Disk-persisted state at `~/.brainstem/self_healing_cron_state.json` so jobs survive the brainstem's per-`/chat` agent reload.

**Missing pieces:**
- **Pattern doc.**  Goes at `pages/vault/Architecture/The Self-Healing Cron Pattern.md`.  Same shape as the other Architecture vault notes: hook, the shape, why-it-works, worked example.
- **Real tick daemon.**  The `schedule` field is stored but inert — nothing ticks `check` on the schedule.  Two options: a launchd plist generator (clean for single-machine ops) or an external tick process the operator runs (cleaner for multi-machine ops).  Recommend launchd plist generator first — it's the smaller surface and matches macOS native primitives.

**Acceptance:**  Pattern doc reviewed and merged.  Tick daemon ships such that `SelfHealingCron(action="setup", schedule="*/5 * * * *", ...)` plus a follow-up "make this routine real" call actually wakes `check` every 5 minutes without the operator running anything else.

---

## Native GUI installer for non-technical users

**Status:** proposed · **Shape:** OS-native installer package · **Depends on:** background service (shipped)

Right now the only supported install path is `curl | bash` / `iwr | iex`.
That's the right answer for developers and the discipline of Article V
(the one-liner is sacred) — but for a non-technical user, opening a
terminal is already friction. A first-time user should be able to
double-click an icon and end up with a running brainstem that auto-starts
on login, without ever seeing a shell.

The one-liner stays sacred. The GUI installer wraps it, not replaces it.

### Target packages

| OS | Format | What it does |
|---|---|---|
| macOS | `.pkg` (signed + notarized) | Installs Python 3.11 if missing, drops the repo in `~/.brainstem/`, writes the launchd plist, sets up the venv, opens the browser. |
| Windows | `.msi` or signed `.exe` (MSIX preferred) | Same shape via winget preflight + Scheduled Task registration + browser launch. |
| Linux | `.deb` + `.rpm` | systemd `--user` unit, standard Linux package conventions. |

### What it MUST preserve

- **The one-liner still works.** GUI installers are additive, not
  replacement. Everything the `.pkg` does is also in the shell script.
- **Same on-disk layout.** `~/.brainstem/`, same VERSION file, same
  service unit — so `brainstem doctor` output is identical regardless of
  whether the user came in via GUI or CLI.
- **Same upgrade path.** The installer should know how to upgrade an
  existing install (detect VERSION, same hard-sync logic as install.sh).

### What it gets the user

- Double-click install. No Terminal.
- App in `/Applications` (macOS) / Start Menu (Windows) that opens
  the brainstem UI in the default browser.
- Automatic updates through the same repo (maybe tie into Sparkle on
  macOS, Squirrel on Windows).
- Uninstaller that `launchctl bootout` / `Unregister-ScheduledTask` and
  removes `~/.brainstem/` cleanly.

### Open questions

- Signing + notarization (both macOS Gatekeeper and Windows SmartScreen
  hate unsigned installers) — a real Apple Developer account and a
  code-signing cert add ongoing cost.
- How much of the `install.sh` flow do we bundle vs. fetch live? Bundled
  = works offline / in air-gapped environments; live-fetch = always
  current but needs network.
- Where does the installer live — a GitHub Release asset, a custom
  landing page, both?

Until the GUI installer exists, the fallback for non-technical users is
`curl | bash` → launchd service → auto-browser-open, which is the
lightest-weight thing we can do without a packaging pipeline.

---

## Digital Twin Companion — a third split, like `|||VOICE|||`

**Status:** shipped (v0) · **Shape:** prompt change + parser change · **Surface:** brainstem side panel

A persistent mirror rendered next to the main chat, reacting to the turn the
user just had. Think Claude Code's side-panel buddy — but instead of a
generic helper, it's *your digital twin* watching the conversation with
you: hints, risks, what you'd say next if you were watching someone else
have this conversation.

### The whole trick is one more delimiter

The brainstem already splits LLM output on `|||VOICE|||` — a sacred OG
pattern where the model produces two parts in one response:

```
<full formatted reply>
|||VOICE|||
<concise TTS line>
```

The parser is ~15 lines (`_parse_voice_split` in `rapp_swarm/function_app.py`).
It takes the raw completion and returns `(formatted, voice)`.

The twin is **exactly the same move, one more delimiter**:

```
<full formatted reply>
|||VOICE|||
<concise TTS line>
|||TWIN|||
<twin's first-person reaction to the turn>
```

The parser returns `(formatted, voice, twin)`. The UI renders `formatted`
in the main chat, pipes `voice` to TTS (unchanged), and drops `twin` into
a side panel. Empty twin section = no side-panel update that turn.

**No new agent. No new hook. No parallel call. No new cost.** Same LLM
completion, same turn, same latency. Adding the twin panel is one prompt
change and one parser change.

### What drives the twin

The system prompt. That's it.

Today's prompt says *"structure your response in TWO parts separated by
`|||VOICE|||`"*. The updated prompt says *"...THREE parts. Third part
after `|||TWIN|||` is your first-person reaction to what just happened:
observations, hints, concerns, the thing you'd whisper to yourself if you
were watching this conversation from the outside. Keep it short. Empty is
fine."*

The twin's personality — its voice, its priorities, what it notices — is
authored by the user as a section of `soul.md` (or a standalone
`twin_soul.md` loaded into the same system message). The soul is already
sacred (§7). The twin's voice is just another paragraph in it.

### Why this is the right shape

- **Honors §5 / §8.** The agent contract doesn't change. `/chat` request
  and response shapes don't change — the twin content lives *inside* the
  existing `response` string. This is an application rendering convention
  inside the exact §8 string field, not permission for alternate protocol
  response shapes or perpetual legacy readers.
- **Honors `data_slush`.** The twin sees the whole turn because it *is*
  the turn. No separate context bus, no parallel agent reading the same
  state from a second place.
- **Honors the Sacred Tenet.** The agent file is untouched. No new
  `digital_twin_agent.py`. No new primitive. The twin is a prompt
  pattern, not a new thing to maintain.
- **Reversibility.** Remove the delimiter from the prompt and the twin
  disappears. The parser's `twin` return just stays empty. Zero cleanup.

### Parser rules

```python
def _parse_twin_split(content):
    """Split on |||VOICE||| then |||TWIN|||. Returns (formatted, voice, twin).
    All delimiters optional — missing ones yield empty strings downstream."""
    if not content:
        return "", "", ""
    main, _, rest = content.partition("|||VOICE|||")
    voice, _, twin = rest.partition("|||TWIN|||")
    return main.strip(), voice.strip(), twin.strip()
```

**Order matters.** `|||VOICE|||` comes before `|||TWIN|||`. If the model
emits `|||TWIN|||` without `|||VOICE|||`, the twin text leaks into
`voice` — treat that as a prompt-authoring bug, not a parser bug.

### What the twin SHOULD produce

- Short. A sentence, maybe a short list. The panel is ambient.
- First-person: *"I'd push back on the third claim. We've seen that
  pattern before and it cost us a week."* Not *"The user should..."*.
- Silent when there's nothing to add. Empty is valid.
- Structured when useful: bold one-word tags (`**Risk:**`, `**Hint:**`,
  `**Question:**`) — but only if the prompt asks for it.

### What the twin MUST NOT do

- Call tools. The twin is a reaction, not an actor. If the twin wants
  tool calls, authoring is wrong — add the agent to the binder and let
  the main loop call it.
- Contain a second response to the user. That's what the main reply is
  for. The twin comments *on* the turn; it doesn't *replace* part of it.
- Exceed a ~500-token soft cap. Prompt should enforce. Long twin output =
  the twin is trying to be the assistant; re-author.

### UI (thin)

- A right-side panel in `rapp_brainstem/web/index.html`. Fixed width on
  desktop, collapsible. Hidden on narrow viewports.
- Markdown render (we already have a renderer for the main chat — reuse).
- One panel per turn. No scrollback — the twin is about *this* turn.
  Prior turns roll off. (If the user wants history, ship it later.)
- Visual treatment: muted, slightly offset typography, so it's legible
  without competing with the main chat.

### Acceptance

1. `_parse_twin_split` (or equivalent) lands as a ~20-line addition to the
   chat response path.
2. The default soul prompt is updated to emit three parts. A user running
   without the updated soul still works — the twin is just empty.
3. Side panel renders markdown, empty panel collapses, zero new JS
   dependencies.
4. The existing `/chat` response shape is unchanged. Clients that don't
   know about the twin see the main reply in the existing field.
5. Tier 2 (`rapp_swarm/`) and Tier 3 (Copilot Studio) ship the same
   delimiter convention — the main reply surface ignores the twin block
   if the surface has nowhere to render it. (Twin text is not lost —
   it's just not rendered; a future tier 2 UI can read it.)

### Open questions

- **Third delimiter conflict.** If the model happens to emit
  `|||TWIN|||` inside a code block, it'd be misparsed. In practice
  `|||VOICE|||` hasn't hit this in production. Keep the delimiter as-is
  and revisit only if a real collision shows up.
- **Turn-scoping the twin.** Does the twin ever see *its own prior
  output*? Right now — no, the conversation history passed to the LLM
  is just user/assistant text. The main reply is the anchor; the twin
  is a fresh reaction each turn. If continuity becomes important later,
  add the prior twin as a system-note on the next turn.
- **A per-agent twin voice.** Different binders might want different
  twin personas (the book-factory twin vs. the sales twin). Scope for
  later — for v1 of this feature, one twin per tenant, authored in the
  soul.

---

## Twin Calibration — fidelity that grows autonomously

**Status:** proposed · **Shape:** prompt change + a small JSONL log · **Depends on:** the twin companion v0

The v0 twin emits hints every turn. Some hints are right, some are noise.
The user votes with their next turn — they act on the hint, push back
against it, or ignore it. That signal is sitting there, free. Calibration
is the move that captures it and uses it to make the twin better over
time, without any explicit teach step from the user.

### The loop

1. **Predict.** Each turn the twin emits its commentary inside `|||TWIN|||`
   AND optionally tags predictions it made, e.g.:
   ```
   |||TWIN|||
   **Hint:** the oldest PR is the release blocker.
   <probe id="t-4711" kind="priority-claim" subject="PR#123" confidence="0.7"/>
   ```
   The probe tag is part of the twin's output, not a separate primitive.
2. **Observe.** On the *next* turn, the twin receives its own prior
   `|||TWIN|||` output as context (appended to the system prompt as a
   tiny `<prior_twin_probes>` block). The twin now knows what it claimed
   a turn ago.
3. **Score.** The twin's prompt instructs: *"For each prior probe,
   judge whether the user's most recent message validates, contradicts,
   or is silent on the claim. Emit a calibration line."* That line
   looks like:
   ```
   <calibration id="t-4711" outcome="validated" note="user merged PR#123 first"/>
   ```
4. **Log.** The brainstem parses any `<calibration …/>` tags out of the
   `|||TWIN|||` block and appends each to `<twin-root>/.twin_calibration.jsonl`
   before rendering. The user never sees the tags; they're stripped
   from what renders in the side panel.
5. **Recalibrate.** The next turn's system prompt injects a rolling
   summary of the twin's hit-rate by `kind`:
   *"Your historical accuracy: priority-claim 62% (21/34), risk-flag
   81% (17/21), api-shape-guess 44%."* The twin uses that to decide
   how confidently to emit new probes of each kind.

### Why this works without a new primitive

- The probes and calibration marks are just **XML-ish tags inside the
  existing `|||TWIN|||` block**. No new delimiter, no new wire field.
  The parser needs one more step — extract-and-strip `<probe/>` and
  `<calibration/>` before rendering — which is a ~20-line addition.
- The log is one JSONL file per twin-root. No DB. Grep-readable.
  Deletable. Exportable.
- No separate LLM call. The twin already runs every turn; it now does
  slightly more work inside the same completion.

### The autonomy claim

The user never has to say *"good hint"* or *"bad hint"*. The twin
watches what the user actually does on the following turn — that's the
ground truth. If the user merges PR#123 after the twin flagged it as
the blocker, the claim is validated. If the user merges a different PR,
the claim is contradicted. If the user changes topic entirely, the
claim is silent — don't count it either way.

This is the *confirm with numbers* move — the twin's confidence for
each probe kind is an actual ratio, stored, auditable, and drifting
toward reality as more turns happen. If the twin starts off overconfident
about priority claims and underconfident about API shapes, the
calibration log will show that, and the next turn's prompt will nudge
the twin to adjust.

### Acceptance

1. `<probe/>` and `<calibration/>` tags are stripped from the rendered
   twin panel and written to `.twin_calibration.jsonl` instead.
2. A rolling accuracy summary is injected into the system prompt — at
   most ~200 tokens, showing last-N windowed hit rates by `kind`.
3. Removing the calibration block from the prompt collapses back to
   v0 twin behavior. Removing the JSONL file resets the twin's
   confidence to neutral. Both are cleanly reversible.
4. The user can read `.twin_calibration.jsonl` with `jq` and see
   what the twin thought and what happened.
