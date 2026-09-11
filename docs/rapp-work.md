# RAPP Work

RAPP Work is the business collaboration and compliance layer built on RAPP/1.
It does not fork or weaken RAPP/1. Identity, frames, canonicalization, content
addressing, eggs, signatures, registries, and trust remain governed by the
canonical RAPP/1 specification.

RAPP Work adds subordinate operational profiles for business requirements such
as:

- organizational and world boundaries;
- human, AI, agent, and service collaboration through equal RAPPID membership;
- role-, room-, and audience-scoped access;
- DOGG/GODD data classification;
- PII-free public projections;
- encrypted GODD sharing and scoped key release;
- provenance, audit history, and attributable approval;
- portable storage and multi-channel projection; and
- deterministic reconciliation of parallel work.

[`rapp-hive/1`](../protocols/rapp-hive/1/SPEC.md) is the first RAPP Work
profile. It defines the RAPP Private Hive: an access-restricted workspace that
can hold any verified RAPP/1 object, share explicitly selected GODD safely,
carry DOGG without changing its classification, and converge distributed
dimensions into one Mother Hive through Dream Catcher.

[`rapp-federation/1`](../protocols/rapp-federation/1/SPEC.md) defines the Hive
Mind: the one universal logical federation and interoperable graph formed by
many sovereign Private Hives. Each Hive retains its own owner, registry,
policies, keys, worlds, and Mother Hive head. Federation adds signed DOGG-safe
discovery, explicit peer consent, recipient-scoped sealed exchange, bilateral
business agreements, durable idempotency, phased receipts, revocation and
moderation, and delay-tolerant operation across long partitions.

Universal and galactic do not mean centralized or globally visible. The Hive
Mind has no universal owner, signing key, writable head, complete database,
mandatory relay, or public GODD graph. ActivityPub, AT Protocol, Git, HTTP,
Matrix, and delay-tolerant transports are replaceable adapters; none confers
RAPP authority.

The checked-in federation reference is a bounded, offline receiver and
conformance candidate. It does not claim that an estate has activated the
profile, that a live federation exists, or that unsupported transport and
native ECDH key-acquisition services have been deployed.

The invariant is simple:

> RAPP Work may add business policy around a RAPP/1 object. It never changes
> what makes that object RAPP/1 conformant.
