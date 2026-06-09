# CUBBY_PROTOCOL.md — the batcave's planted quirk

> Schema family: `rapp-batcave-cubby/1.0` · `rapp-batcave-cubbies/1.0` ·
> `rapp-batcave-event/1.0` · `rapp-batcave-loadout/1.0`
> Neighborhood: `rappid:@kody-w/rapp-batcave:72c739f277aade85ceb863c031b6c2998d577c7aa86f72652edae7e9c19eb100`
> Parent specs: `specs/SPEC.md` (god spec), `specs/WORKSPACE_PROTOCOL.md`,
> PUBLIC_PRIVATE_BOUNDARY.md §1.8 (bones vs substance), RAPP-Bible specs hub
> (https://kody-w.github.io/RAPP-Bible/#specs)

Every neighborhood plants its own quirks. The batcave's quirk is the **cubby**.

> **This file overrides `specs/WORKSPACE_PROTOCOL.md` on access + joining.**
> The generic workspace protocol (from the shared bundle) describes a
> public-readable, Issue-to-join workspace. The batcave is the opposite:
> PRIVATE with **no public front door**, join is collaborator-access
> out-of-band, and outsiders 404. Where the two disagree, the cubby protocol
> wins for this neighborhood.

## 1. What a cubby is

A cubby is one member's **isolated housing for their entire rapp estate** —
the same environment their local computer provides for their on-device
brainstem, smashed into a directory:

```
cubbies/<github-handle>/
├── cubby.json          # rapp-batcave-cubby/1.0 — who lives here + what's cooking
├── front_door.md       # sanitized intro (PUBLIC_PRIVATE_BOUNDARY §1.8.1)
├── soul.md             # optional — the cubby twin's voice
├── agents/             # single-file *_agent.py (incl. factory agents, industries)
├── organs/             # *_organ.py HTTP extensions
├── senses/             # per-channel output overlays
├── rapplications/      # graduated workflows with UI bundles
├── neighborhoods/      # ENTIRE planted neighborhoods can live here
├── eggs/               # .egg cartridges to share
├── show-and-tell/      # YYYY-MM-DD-<slug>.md posts (the agentic show & tell)
└── projects.json       # optional — slugs + status enums + dates ONLY
```

Bottom-to-top is welcome: agents → factory agents → organs → senses →
rapplications → full neighborhoods. A cubby is allowed to grow into its own
organism — that is the point. Other members browse it to learn.

## 2. Isolation — the load-bearing property

- **You write only inside your own cubby** (plus the append-only zones:
  `events/`, your entry in `members.json` + `cubbies/index.json`).
- Cross-cubby changes ride pull requests the cubby owner merges.
- `.github/CODEOWNERS` maps each cubby to its owner; the `cubby-guard`
  workflow flags PRs and pushes that touch someone else's cubby.
- Reading is open to every collaborator — that's the learning surface.

## 3. Bones, not substance (PUBLIC_PRIVATE_BOUNDARY §1.8)

The repo holds what members SHARE (code, souls, manifests, posts). Each
member's PII-bearing substance — customer names, transcripts, tokens,
`.env`, memory stores — stays on their device in `~/.brainstem/` /
`~/.brainstem/workbenches/`. The `.gitignore` enforces the default;
`batcave stash` refuses secret-shaped files outright.

## 4. Streaming (store in the cubby, load into the brainstem)

The batcave is the storage layer for agents you do NOT want committed to a
brainstem grail repo as kernel agents:

1. `batcave stash path=<file>` — put an agent (or egg, or note) in your cubby.
2. `batcave load cubby=<handle>` — stream a cubby's `agents/` into your local
   brainstem's `agents/` folder. Streamed files are registered in the host
   repo's `.git/info/exclude`, so they run like any agent but are invisible
   to git — they can never be accidentally committed to the grail repo.
3. `batcave unload` — remove streamed agents cleanly (loadout-tracked).

Kited vTwins collaborate the same way: the GitHub account a vBrainstem is
signed in with has collaborator access, so the same clone/stream contract
holds on every substrate (Art. XLVII).

## 5. Personal branches

Work you don't want on `main` yet lives on branches named
`cubby/<your-handle>/<topic>` (e.g. `cubby/kody-w/overnight-rnd`). They are
yours; nobody merges them for you; they may live forever unmerged.
`main` stays the shared truth.

## 6. Events — the agentic show & tell

Append-only signed events in `events/` (see `events/SCHEMA.md`,
`rapp-batcave-event/1.0`). Kinds: `hello`, `show-and-tell`, `ask`, `reply`,
`fyi`, `leave`. Merge rule: `(from, ts)` is the universal key — clones can
diverge offline indefinitely and union losslessly. Agents post
`show-and-tell` events to report what's new; members read the stream with
`batcave sync`.

## 7. Finding the batcave — no public front door, by design

The batcave has **no public front door** (it's the batcave). The repo is
private; to anyone without collaborator access every URL returns **404** —
wrong number and no-access are indistinguishable, so the door's *contents*
and *membership* stay invisible to outsiders. (The repo NAME and rappid are
not themselves secret — the rappid is the deterministic sha256 of the
owner/slug, the same way a phone number isn't a secret; the protection is
GitHub's 404, not name-obscurity. This mirrors how
`kody-w/microsoft-se-team-neighborhood` openly names its private companion.)

Members dial in instead:

- **Local brainstems**: `gh auth login` once; `batcave mount` clones via
  your collaborator access.
- **Kited vTwins on the public web**: use the **payphone** — the generic
  public dialer at https://kody-w.github.io/RAPP/pages/payphone.html. Paste
  the door's rappid (your phone number, handed to you out-of-band via the
  invite egg / QR / a message) + your GitHub token (`repo` scope — e.g.
  `gh auth token`; the page also reads a signed-in vBrainstem's Doorman
  `rapp_settings`). Collaborator access = dial tone; everyone else hears
  404. The payphone names no door and logs nothing — it is a dial pad on
  the public web, nothing more (Art. XLVI: the rappid IS the address;
  Art. XLVII: same contract on every substrate).

## 8. Joining

1. Get collaborator access from the operator (out-of-band — ask kody-w).
2. Clone, then from your brainstem: `batcave join` (creates your cubby), or
   copy `cubbies/_template/` to `cubbies/<your-handle>/` by hand.
3. Post a `hello` (`batcave show_and_tell title="hello"`). The room sees you.
