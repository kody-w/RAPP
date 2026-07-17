# Public installer entrypoints retired — HTTP 410 Gone

> **HTTP 410 Gone.** The target-owned public distribution, deployment, and
> download entrypoints in `installer/` are retired.

No public runtime installation is available from this directory. Its retired
artifacts are inert historical evidence, not supported distribution,
deployment, download, or import paths.

The repository-local `initialize-variant.sh` lineage utility remains active
only for fresh template clones. It is mint-once: it records lineage once and
performs no runtime install or deploy. A fresh child preserves template
product metadata but drops root-only migration, legacy UUID, re-anchor, and
attestation-note evidence; its unattested state remains `null` rather than
fabricating a child re-anchor. It is not a public distribution, deployment, or
download entrypoint.

This README intentionally provides no public installation, deployment, or
download commands. For the repository's current contained state, read
[`RAPP1_STATUS.md`](../RAPP1_STATUS.md). For protocol rules, read the pinned
[`RAPP/1 rev-5 authority`](../RAPP1_AUTHORITY.json). Neither document revives
the retired public entrypoints.
