# The .egg snapshot format

A developer is standing at one machine with a live Twin Stack under `~/.rapp-twins`. There are two twins, `kody` and `molly`. `kody` has `swarms/abc`, `t2t/conversations`, `documents`, `inbox`, and `outbox`. There is also a shared pipeline directory at `.shared/book-factory`, holding in-flight artifacts from a multi-twin workflow. The goal is not a backup in the loose sense. The goal is stricter: pack that whole state on machine A, move one file to machine B, unpack it, and restore the same Twin Stack state, with transient runtime junk left behind.

That intent is stated plainly at the top of `hippocampus/twin-egg.sh`:

```bash
#!/bin/bash
# hippocampus/twin-egg.sh — pack/unpack the full local Twin Stack as a .egg
#
# A .egg is a single zipfile capturing the entire local Twin Stack ecosystem:
# every twin's workspace, identity, peers, conversations, documents, inbox,
# outbox, hatched swarms, and the shared workflow dir (where book-factory
# and other multi-twin pipelines drop in-flight artifacts). Excludes
# transient runtime state (server.pid, server.log).
#
# Restore is byte-identical. Pack on machine A, unpack on machine B (or on
# A six months later) → state resumes as if no time passed and no machine
# was changed. Twins keep their identities, their peer relationships, their
# in-progress conversations, their inbox-pending documents.
```

The command surface is small enough to memorize:

```bash
#     bash hippocampus/twin-egg.sh pack  [--out twinstack-2026-04-19.egg]
#     bash hippocampus/twin-egg.sh unpack twinstack.egg [--into ~/.rapp-twins] [--start]
#     bash hippocampus/twin-egg.sh info  twinstack.egg
#
# Defaults: TWINS_HOME=~/.rapp-twins. .egg files are zipfiles (use `unzip -l`
# to inspect contents directly).
```

`pack` captures the current `TWINS_HOME`, plus any explicitly included directories. `unpack` restores into a target directory and can optionally `--start` every restored twin. `info` reads the embedded manifest without extracting the archive.

The tests make those claims concrete. `tests/test-twin-egg.sh` builds a synthetic `TWINS_HOME` under `/tmp`, creates twin directories for `kody` and `molly`, and adds `.shared/book-factory`. Then it verifies six things: pack creates a single `.egg`; the manifest includes `schema=rapp-egg/1.0`, twins, and SHA-256 hashes; unpack restores into a fresh directory; the round-trip preserves `workspace.json`, `t2t/identity`, peers, swarms, documents, inbox, outbox, and `.shared/`; transient files are excluded; and `info` can read the manifest without extraction.

That list tells you what restore means here. It is not a slogan. It is a contract with specific fixtures and explicit exclusions.

There are limits to what the source shows. We can see the shell interface, the intent, and the test criteria. We can also see that Python’s `zipfile` and `hashlib` are used inside `cmd_pack`, which suggests deterministic control over archive creation. But the excerpt stops before the full packing logic, so any deeper claim about manifest layout or timestamp normalization would be guesswork.
