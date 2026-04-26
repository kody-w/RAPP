# rapp_store moved

The catalog of RAPP rapplications now lives at:

**[github.com/kody-w/rapp_store](https://github.com/kody-w/rapp_store)**

Catalog URL (use this in `RAPPSTORE_URL`, brainstem fetches, etc.):

```
https://raw.githubusercontent.com/kody-w/rapp_store/main/index.json
```

## Why the split

The engine (brainstem, swarm, worker), Constitution, and vault stay in `kody-w/RAPP`. The catalog is *content* that grows independently; keeping it in its own repo lets it move at its own cadence and keeps "in the catalog" purely a content claim — not a status signal. RAR (the trust layer) provides identity attestation separately. See `pages/vault/Architecture/` for the long-form rationale.

## If you have an old install pointing here

Re-run the install one-liner — it ships brainstem code that points at the new catalog URL by default:

```bash
curl -fsSL https://kody-w.github.io/RAPP/installer/install.sh | bash
```

Or override `RAPPSTORE_URL` in your env to point at a fork/mirror — the brainstem honors that and the binder will install from wherever you point it.
