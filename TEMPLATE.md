# Using This Repo as a Template

> **Current RAPP/1 authority (rev-5).** For canonicalization, identity, frames,
> wire, eggs, registry, trust, and protocol evolution, follow
> [`RAPP1_AUTHORITY.json`](./RAPP1_AUTHORITY.json) and
> [`RAPP1_STATUS.md`](./RAPP1_STATUS.md). A genuinely new organism may mint
> once per RAPP/1 §6.2. Copying or moving an existing organism preserves its
> tail; only a verifiable §6.3 re-anchor may replace it in an enumerated case.

This is the RAPP species root. Variants spawned directly from here become **direct children of rapp** in the lineage tree — siblings of `wildhaven-ai-homes-twin` and any other top-level variant.

## When to template from RAPP (vs. a downstream variant)

Template from RAPP when:
- Your variant is structurally different from any existing variant pattern (not a Pre-Founder twin, not a memorial twin, etc.) — you want the full RAPP layout to remix from scratch.
- Your variant is a product/documentation fork. The immutable grail bytes
  remain pinned to `kody-w/rapp-installer@brainstem-v0.6.9`; protocol
  evolution still follows constitutional authority.
- You want legacy application `parent_rappid` provenance to name rapp directly
  (this does not affect RAPP identity or trust).

Template from a downstream (e.g., [wildhaven-ai-homes-twin](https://github.com/kody-w/wildhaven-ai-homes-twin)) when:
- You want to inherit a specific pattern (Pre-Founder twin, etc.) — the downstream's installer scaffolds that pattern's content for you.
- Your variant is a sibling of the downstream's existing variants. The chain becomes `you → downstream → rapp`.

## Single-parent rule

`parent_rappid` is legacy application provenance, not RAPP identity, trust, or
key succession. A template may preserve accurate source provenance, but
current acceptance validates the new §6 identity and resolves §13 state.

The existing lineage guard and initializer implement the legacy product
record. They do not yet prove a conformant §6 mint or §13 registration.

## Current RAPP/1 status

Do not use the initializer below to claim a RAPP/1-conformant plant until its
identity emitter is migrated and the owner actions in `RAPP1_STATUS.md` are
complete. It currently documents a bare-UUID-era flow.

## Historical template flow (superseded)

<!-- RAPP1-HISTORICAL-SECTION-START -->

The remaining commands and generated fields are preserved as migration
history, not current identity instructions.

## The flow

### 1. Click "Use this template"

On the RAPP GitHub page, click **Use this template** → **Create a new repository**, choose owner / name / visibility, and create.

### 2. Clone your new repo

```bash
git clone https://github.com/<your-user>/<your-repo>.git
cd <your-repo>
```

### 3. Run the initialization script

```bash
bash installer/initialize-variant.sh
```

This will:

1. Run `rapp_brainstem/utils/lineage_check.py` to verify this is a fresh template clone (refuses to run on the species root itself, or on an already-initialized variant without confirmation).
2. Generate a fresh rappid (UUIDv4).
3. Rewrite `rappid.json` with `parent_rappid = rappid:@kody-w/rapp:9a8f0a4b5a710e20f4d819a0f37d2a4c9f113b5e78fb3c29e70b54fff48a38f9` (rapp's species root) and `parent_repo = https://github.com/kody-w/RAPP.git`.
4. Record the parent commit.

### 4. Customize

The variant inherits the full RAPP layout. Strip whatever you don't need (`rapp_swarm`, `pages`, etc.) and edit `README.md` / `CLAUDE.md` to describe your variant.

### 5. Optional: become a template yourself

```bash
gh repo edit <your-user>/<your-repo> --template=true
```

Then add your rappid + canonical owner/repo to `KNOWN_TEMPLATE_REPOS` in `rapp_brainstem/utils/lineage_check.py` so descendants of your variant get the same uninitialized-clone detection.

## See also

- [`rappid.json`](./rappid.json) — the species-root anchor.
- [`rapp_brainstem/utils/lineage_check.py`](./rapp_brainstem/utils/lineage_check.py) — the boot guard.
- [`installer/initialize-variant.sh`](./installer/initialize-variant.sh) — this template's variant-init script.
- [Constitution Article XXXIV](./CONSTITUTION.md) — variant lineage protocol.

<!-- RAPP1-HISTORICAL-SECTION-END -->
