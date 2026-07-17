# PUBLIC_BOUNDARY.md — the cave's pre-push scrub gate

> **Historical cave runbook.** For canonicalization, identity, frames, wire,
> eggs, registry, trust, and protocol evolution, follow RAPP/1 rev-5 through
> [`RAPP1_AUTHORITY.json`](../../RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](../../RAPP1_STATUS.md). The prepared cave installer,
> moving-branch downloads, and unsigned catalogs are inert/untrusted history.

<!-- RAPP1-HISTORICAL-SECTION-START -->

> Schema doctrine: `PUBLIC_PRIVATE_BOUNDARY.md §1.8` (bones vs substance) ·
> Enforces `specs/CAVE_PROTOCOL.md §3` for the open web ·
> Neighborhood: `rappid:@kody-w/rapp-cave:ca72ca0a3cb90c357fb09e38b02f85f09935cacbf61e94740c57f1eb30a73e0a`
> Parent: `rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9` (the RAPP species root)

`CAVE_PROTOCOL.md §3` states the **policy** ("bones, not substance — load-bearing
on the open web"). This file is the **enforcement**: the exact register of what
the public flip excluded from the private batcave, plus the runnable checklist
any contributor or integrator MUST pass before pushing. The cave lives under the
public `kody-w/RAPP` repo at `cave/` and is served at
`https://kody-w.github.io/RAPP/cave/` — **everything committed here is
world-readable forever.** There is no collaborator gate, no 404 guard, no sealed
channel to fall back on. The scrub is the only guard.

This is the public counterpart to the batcave's defenses (`channel-secret.json`
gating, `.gitignore`, and `cave stash` refusing secret-shaped files). Where the
batcave was at least collaborator-gated, the cave is on the open internet, so the
boundary is not hygiene — it is the perimeter.

## 1. Exclusion register — what the public flip dropped from the batcave

The cave is a faithful PUBLIC mirror of the private batcave
(`~/.brainstem/neighborhoods/rapp-batcave/clone`), with these artifacts
**deliberately NOT mirrored**. None of them may ever appear under `cave/`:

| Excluded from batcave | Why | Mirrored as |
|---|---|---|
| `channel-secret.json` (`rapp-batcave-channel/1.0`, the AES-256-GCM key material) | shared secret; the public room has no sealed channel | dropped entirely |
| Private operator agents in `cubbies/kody-w/agents/`: `workiq_agent.py`, `twin_me_agent.py`, `clawpilot_twin_agent.py`, `commons_agent.py`, `schedule_reply_agent.py`, `copilot_studio_deploy_agent.py`, `mcs_compare_agent.py`, `transcript2prototype_agent.py`, `batcave_wwf_agent.py`, `ms_architecture_diagram_agent_1_agent.py` | kody's internal/customer-facing operators; not public-safe | dropped; the retained `rapp-installer` subtree is inert history |
| Third-party member cubbies: `cubbies/billwhalenmsft/`, `cubbies/brkuklen/`, `cubbies/BlazingBeard/` | naming a private crew's membership is a relationship-PII leak | dropped; cave seeds only `kody-w` + `_template` |
| `members.json` private roster (logins, `via` notes, `joined_at`, pending-invite notes), `cubbies/index.json` private "what I'm cooking" lines | members' association + activity is private substance | rewritten to a single public `operator` seat, `open_to_anyone: true` |
| Anyone's `.env`, `.copilot_token`, `.copilot_session`, `.lineage_key`, `private-estate-secret`, `*.pem`, `keys/`, `*-secret.json`, `.brainstem_data/`, transcripts, customer names | PII / secret substance — stays on-device per §1.8 | never committed (RAPP root `.gitignore` covers the defaults) |

## 2. Keep-vs-flip rule (do not over-scrub the engine)

Two surfaces both contain the string `gh auth` / `ghu_`. They are NOT the same and
must be treated differently:

- **KEEP — engine Copilot auth.** `rapplications/rapp-installer/kernel/brainstem.py`
  and `kernel/.env.example` reference `gh auth` / `ghu_`/`gho_` tokens because the
  brainstem authenticates to the **GitHub Copilot API** that way. This is the public
  engine's normal, correct auth. It is not private framing. Leave it.
- **RETIRED — distribution/bootstrap framing.** Fork + PR may describe
  application membership, but direct raw downloads, cave installer bootstraps,
  and catalogs must not be presented as authenticated RAPP/1 distribution.

## 3. The pre-push scrub checklist (run from the cave root)

```bash
CAVE=~/.brainstem/neighborhoods/RAPP/cave

# 1. Channel secret + schema — MUST be empty. Detect by schema/filename and by
#    base64 key shape (do NOT paste the literal secret into this public file).
grep -rni "channel-secret\|rapp-batcave-channel\|\"secret\"" "$CAVE"
grep -rnoE "[A-Za-z0-9+/]{40,}={0,2}" "$CAVE" --include=*.json   # 32-byte+ base64 blobs

# 2. Private operator agent names — MUST be empty
grep -rniE "workiq|twin_me|clawpilot|commons_agent|schedule_reply|copilot_studio_deploy|mcs_compare|transcript2prototype|batcave_wwf|ms_architecture_diagram" "$CAVE"

# 3. Third-party private member handles — MUST be empty
#    (NB: blazingbeard.github.io/quests is a PUBLIC tutorial link shipped in the
#     canonical grail brainstem — that single hit is reviewed-clean, not a leak.)
grep -rniE "billwhalenmsft|brkuklen|blazingbeard" "$CAVE"

# 4. Tokens / keys / cloud creds — MUST be empty
grep -rnE "ghp_[A-Za-z0-9]{20,}|gho_[A-Za-z0-9]{20,}|github_pat_|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----" "$CAVE"

# 5. Raw emails / PII — MUST be empty (handles like @kody-w/ are fine)
grep -rnoE "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}" "$CAVE" | grep -viE "@rapp/|@kody-w/|example\.com|noreply"

# 6. Private DISTRIBUTION framing that escaped the flip — review every hit
#    (matches inside neighborhood.json / .well-known that NEGATE these words —
#     "no collaborator gate", "no gh auth" — are the correct public posture, not leaks)
grep -rniE "private batcave|collaborator access|dial tone|payphone|outsiders 404|no public front door|out-of-band" "$CAVE"

# 7. Secret-shaped files that must not exist (.env.example is the only allowed *.env*)
find "$CAVE" \( -name "channel-secret.json" -o -name "*.pem" -o -name ".env" -o -name "*-secret.json" -o -name ".copilot_token" -o -name ".lineage_key" \)
```

**This file self-matches by design** — it documents the patterns and the
exclusion register, so it is the expected sole hit for checks 2 and 6. Add
`--exclude=PUBLIC_BOUNDARY.md` (or confirm every hit points only here) when
reading results.

A push is clean only when 1–5 and 7 return nothing, and every hit in 6 is either
(a) a public-posture negation ("no collaborator gate") or (b) intentionally
flipped to public curl/fork+PR. Anything else blocks the push.

## 4. .gitignore reliance

The cave has no cave-local `.gitignore`; the **`kody-w/RAPP` repo-root
`.gitignore` governs** and already excludes `.env`, `.env.*`, `.copilot_token`,
`.copilot_session`, `.brainstem_data/`, `*.secret`, `secrets.json`, `.venv/`.
Contributors adding a cubby rely on those defaults — but the scrub in §3 is the
authority, because a `.gitignore` only stops *new* untracked files, not a secret
pasted into a tracked `.json`. Audit the diff, then push.

---

*Public means forever. The cave keeps the batcave's anatomy and mechanics; it
keeps none of its secrets.*

<!-- RAPP1-HISTORICAL-SECTION-END -->
