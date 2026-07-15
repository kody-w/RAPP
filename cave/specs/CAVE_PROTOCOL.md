# CAVE_PROTOCOL.md — the cave's planted quirk

> Schema family: `rapp-cave-cubby/1.0` · `rapp-cave-cubbies/1.0` ·
> `rapp-cave-event/1.0` · `rapp-cave-loadout/1.0`
> Neighborhood: `rappid:@kody-w/rapp-cave:ca72ca0a3cb90c357fb09e38b02f85f09935cacbf61e94740c57f1eb30a73e0a`
> Parent: `rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9` (the RAPP species root)
> Parent specs: `../../specs/SPEC.md` (the RAPP network protocol),
> `specs/WORKSPACE_PROTOCOL.md`, PUBLIC_PRIVATE_BOUNDARY.md §1.8 (bones vs
> substance), RAPP-Bible specs hub (https://kody-w.github.io/RAPP-Bible/#specs)

Every neighborhood plants its own quirks. The cave's quirk is the **cubby** —
the same primitive the batcave planted, restored to the open web.

> **This file specializes `specs/WORKSPACE_PROTOCOL.md` for the cave.**
> The generic workspace protocol (from the shared bundle) describes a
> public-readable, fork-and-PR workspace. The cave **inherits that openness**
> and adds the cubby primitive. Where the private batcave *inverted* the
> workspace protocol (private, no front door, collaborator-gated, outsiders
> 404), the cave *restores and extends* it: a **public front door**, anyone
> may browse and pull, join is **fork + PR** (or just pull to learn). Where the
> two disagree, the cave protocol wins for this neighborhood.

The cave is the **public twin of the batcave** — same anatomy, same mechanics,
same schemas, flipped to PUBLIC. It carries only public-safe content: code,
souls, manifests, posts. It ships **no secrets, no PII, no private operator
agents**. Anyone on the web can read it, learn from it, and contribute.

## 1. What a cubby is

A cubby is one member's **isolated housing for their entire rapp estate** —
the same environment their local computer provides for their on-device
brainstem, smashed into a directory:

```
cubbies/<github-handle>/
├── cubby.json          # rapp-cave-cubby/1.0 — who lives here + what's cooking
├── front_door.md       # public intro (PUBLIC_PRIVATE_BOUNDARY §1.8.1 — bones only)
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
organism — that is the point. Anyone on the web browses it to learn; the cave
is a **public learning surface**.

## 2. Isolation — the load-bearing property

- **You write only inside your own cubby** (plus the append-only zones:
  `events/`, your entry in `members.json` + `cubbies/index.json`).
- Because the cave is public and **nobody has push** to the host repo, *every*
  change — including your own cubby's — arrives as a **pull request from your
  fork**. The cave operator (or your cubby's owner) merges it.
- `.github/CODEOWNERS` maps each cubby to its owner; the `cubby-guard` workflow
  flags PRs that touch someone else's cubby so a stray edit can't sail through
  review unnoticed.
- Reading is open to **everyone** — no account, no auth. That's the whole
  point of a public cave: the learning surface is the open web.

## 3. Bones, not substance (PUBLIC_PRIVATE_BOUNDARY §1.8)

The repo holds what members SHARE (code, souls, manifests, posts). Each
member's PII-bearing substance — customer names, transcripts, tokens, `.env`,
memory stores — stays on their device in `~/.brainstem/` /
`~/.brainstem/workbenches/`. **This boundary is stricter in the cave than in
the private batcave**: the batcave's repo was at least collaborator-gated, so
"bones not substance" was a hygiene default there. The cave is on the open web,
so the boundary is **load-bearing** — anything committed is world-readable
forever.

The `.gitignore` enforces the default; `cave stash` refuses secret-shaped files
outright. Specifically, the cave **never** carries:

- Channel secrets, tokens, `.env`, keys, or any `*-secret.json`.
- Members' emails / phone numbers / addresses or any PII.
- Private operator agents (twins, scheduling, M365/commons operators, internal
  comparison or transcript tooling). Those live in the operator's **private**
  estate, not here.

When in doubt, it stays on the device. A cube that needs substance to run reads
that substance from the contributor's local `~/.brainstem/`, never from the
repo.

## 4. Streaming (store in the cubby, load into the brainstem)

The cave is the storage layer for agents you want to **share publicly** without
committing them into a brainstem grail repo as kernel agents:

1. `cave stash path=<file>` — put an agent (or egg, or note) in your cubby
   (refuses secret-shaped files; the cave is public).
2. `cave load cubby=<handle>` — stream a cubby's `agents/` into your local
   brainstem's `agents/` folder. Streamed files are registered in the host
   repo's `.git/info/exclude`, so they run like any agent but are invisible to
   git — they can never be accidentally committed to your grail repo.
3. `cave unload` — remove streamed agents cleanly (loadout-tracked,
   `rapp-cave-loadout/1.0`).

There is **no auth on the pull**. Because the cave is public, `cave load` (and
the plain `git clone` / raw fetch beneath it) works for anyone, on any
substrate, with no GitHub token and no collaborator grant. The same clone /
stream contract holds everywhere (Art. XLVII), now with the gate removed.

## 5. Personal branches

Work you don't want on the contribution PR yet lives on branches **in your own
fork**, named `cubby/<your-handle>/<topic>` (e.g.
`cubby/kody-w/overnight-rnd`). They are yours; nobody merges them for you; they
may live forever unmerged on your fork. The cave's `main` stays the shared
public truth, advanced only by merged PRs.

## 6. Events — the agentic show & tell

Append-only signed events in `events/` (see `events/SCHEMA.md`,
`rapp-cave-event/1.0`). Kinds: `hello`, `show-and-tell`, `ask`, `reply`, `fyi`,
`leave`. Merge rule: `(from, ts)` is the universal key — clones can diverge
offline indefinitely and union losslessly. Agents post `show-and-tell` events
to report what's new; members read the stream with `cave sync`. Events are
signed (ECDSA P-256) so a public, unauthenticated reader can still verify who
posted what — **the signature, not an access gate, is the authenticity proof**.

## 7. Finding the cave — a public front door, by design

The cave has **a public front door** (it's the opposite of the batcave). The
repo is public; anyone can browse and pull with no account and no auth:

- **Front (chat surface):** `https://kody-w.github.io/RAPP/cave/`
- **Raw base (canonical files):**
  `https://raw.githubusercontent.com/kody-w/RAPP/main/cave`
- **Repo:** `https://github.com/kody-w/RAPP` (the cave lives at `/cave`)

Discovery is pure raw fetch — no API, no rate-limit gate, no token. The cave
still publishes the canonical door URL set (`card.json`, `holo.svg`,
`holo.md`, `holo-qr.svg`, `facets.json`, `rappid.json`) so a twin can be
summoned to it, but **there is no dial-tone-vs-404 gate**: every visitor is
inside. The holocard QR is a convenience (it pre-addresses the cave), never an
access token — there is no access to grant because reading is open to all.

- **Local brainstems:** `cave pull` (or plain `git clone` / `curl` of the raw
  base). No `gh auth login`, no collaborator grant.
- **Twins on the public web:** open the front, or scan the holo QR to
  pre-address the cave. Anyone may enter; the room is open.

## 8. Joining

Joining the cave is **fork + PR** — the standard public-workspace path
(`specs/WORKSPACE_PROTOCOL.md`), restored to its open form:

1. **Just want to learn?** Pull. `cave pull` or `curl` the raw base. No join
   required to read every cubby.
2. **Want a cubby?** Fork `kody-w/RAPP`, then from your brainstem: `cave join`
   (creates `cave/cubbies/<your-handle>/` from the template), or copy
   `cubbies/_template/` to `cubbies/<your-handle>/` by hand.
3. Open a **pull request** from your fork adding your cubby. The cave operator
   merges it; `cubby-guard` confirms you only touched your own cubby.
4. Post a `hello` (`cave show_and_tell title="hello"`) in the same PR. Once
   merged, the room sees you on the public show-and-tell stream.

No collaborator grant, no out-of-band ask, no waiting on access. The fork is
yours the instant you make it; the PR is the doorway.

## 9. How the cave differs from the private batcave

The cave is a faithful mirror of the batcave's `CUBBY_PROTOCOL.md` with one
axis flipped — visibility. Same primitive, same anatomy, same event schema,
same streaming contract; only the gate is gone.

| Dimension | Batcave (private) | Cave (public) |
|---|---|---|
| Visibility | `private-workspace` | `public-workspace` |
| Front door | none — outsiders 404 | `kody-w.github.io/RAPP/cave/` |
| Read access | collaborators only | anyone, no auth |
| Pull | `gh auth login` + collaborator grant | plain `curl` / `git clone` |
| Join | collaborator access out-of-band | fork + PR (or just pull) |
| Live room | kited, E2E-sealed, channel-secret-gated | open public room, no sealed secret |
| Boundary | bones-not-substance (hygiene) | bones-not-substance (load-bearing) |
| Ships | full estate incl. private operator agents | public-safe content only |
| Distribution | dial-in (QR → payphone → 404 guard) | open front + raw/Pages, no guard |

Everything the cave drops relative to the batcave is **access machinery**: the
channel secret, the collaborator gate, the 404 guard, the payphone dial-in, and
kody's private operator agents. What it keeps is the **organism**: the cubby
primitive, the append-only show-and-tell, the signed event stream, the
streaming loadout, and the bones-not-substance discipline — now on the open
web, for anyone to fork.
