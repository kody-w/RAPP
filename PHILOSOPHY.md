# Why RAPP

RAPP is the public foundation for growing portable digital organisms around an
immutable Grail.

Every RAPP begins with one question:

> **What should I do?**

The problem is wrapped one verifiable layer at a time. Each meaningful attempt
becomes a frame. Agents, organs, policy, memory, state, deployment, and
experience grow outward rather than being welded into the kernel. When the
organism reliably fulfills its bounded goal, it can graduate into the wild.

Portable, self-documenting organisms may later produce distinctly identified
offspring or crosses while preserving every ancestor and lineage address.

## Why everything goes through /chat: the transcript is the window

RAPP has one door. Every request a Brainstem answers, every agent it calls,
and every reply it gives travels through `POST /chat` as plain text. That
minimalism is deliberate, and the reason is people, not plumbing.

- **One door means one readable record.** Because nothing happens through a
  side route, the chat transcript is the complete account of what the AI was
  asked, what it decided, and what it did. There is no second log to find.
- **Anyone can audit it.** You do not need to be an engineer to know what an
  AI did on your behalf. You read the conversation, the same way you would
  read an email thread.
- **It works with whatever AI is on the other end.** A Brainstem talking to a
  person, to another Brainstem, or to any other AI tool uses the same shape:
  text in, text out. Any system that can hold a conversation can join, and
  every exchange stays legible to the humans watching. That is universal
  accessibility into any AI tool.
- **Capability grows behind the door, never beside it.** New abilities arrive
  as agents a Brainstem can call from inside the conversation, never as new
  endpoints. The wire stays the same size while what it can do keeps growing.
- **Even actions stay legible.** When a Brainstem drives something outside
  itself, such as a browser or another tool, it proposes the action as text in
  the chat and a person approves it there. The record of what was done is the
  same record as what was said.

If you want to know what a RAPP system is doing, read its transcript. That is
the whole design.

## Repository boundary

- **`kody-w/RAPP`** — canonical foundation, product home, organism model,
  public reference implementation, and philosophy.
- **`kody-w/rapp-1`** — canonical interoperable protocol: bytes, addresses,
  identity, frames, wire, eggs, trust, registry, and protocol profiles.
- **Rappter** — the singular downstream customer-facing brand at
  `rappter.com`.
- **RapterBox** — the company name and a separate downstream sub-product.

RAPP/1 does not replace the RAPP repository. RapterBox LLC products may build
on RAPP, but private LLC doctrine, ownership administration, customer data, and
proprietary product code do not belong in the RAPP foundation.

Downstream Rappter and RapterBox implementations may live in their own
repositories. They consume the foundation; they do not become a second
authority for RAPP.

## Current protocol status

The main `kody-w/RAPP` repository's current implementation pin is the
structural RAPP/1 rev-5 record in
[`RAPP1_AUTHORITY.json`](https://github.com/kody-w/RAPP/blob/main/RAPP1_AUTHORITY.json),
and its limitations remain explicit in
[`RAPP1_STATUS.md`](https://github.com/kody-w/RAPP/blob/main/RAPP1_STATUS.md).

Canonicalization, identity, frames, wire, eggs, registry, trust, and protocol
evolution defer to that pinned authority until an authorized migration advances
the implementation pin. The public RAPP/1 standard may advance independently.

## Open-source direction

RAPP is the public foundation and is intended for open-source stewardship.
The repository's currently published PolyForm and documentation licenses remain
legally operative until the contributor/rights inventory and authorized license
migration are complete. Repository administration does not itself establish
ownership allocation; see
[`RIGHTS-NOTICE.md`](https://github.com/kody-w/RAPP/blob/main/RIGHTS-NOTICE.md).

The survival rule is simple:

> Keep the RAPP foundation public and interoperable. Keep Rappter and
> RapterBox LLC product IP distinct.
