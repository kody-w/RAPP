# `PermissionError` as a first-class signal

When the swarm server seals a swarm, every memory file in that swarm gets `chmod 0444`. Read-only at the OS layer. The next time an agent tries to write — `SaveMemory.perform()` opens the file for writing — the OS raises `PermissionError`.

The naive instinct is to catch this and convert it into a generic 500 error. Or worse, swallow it silently.

We do neither. We translate `PermissionError` into a domain signal:

```python
try:
    output = agent.perform(**(args or {}))
    return {"status": "ok", "output": output}
except PermissionError as e:
    return {"status": "ok", "output": json.dumps({
        "status": "error",
        "message": f"swarm is sealed; writes rejected ({e})",
        "sealed": True,
    })}
```

The HTTP response is still 200. The envelope is still `{status: "ok", output: ...}`. But the *output payload* — the thing the LLM will read in its next turn — explicitly says `sealed: true`. The model sees this and explains to the user: *"I tried to save that, but your twin is sealed and writes are no longer accepted. Here's what to do instead..."*

**Three benefits of this pattern:**

**The OS does the enforcement.** No application-layer "is this swarm sealed?" check on every write. We set `chmod 0444` once at sealing time; the kernel handles every subsequent write attempt. Less code, more reliable, no race conditions.

**The error is debuggable.** `PermissionError: [Errno 13] Permission denied: '...memory.json'` tells you exactly what failed. If you ever see it for non-sealed reasons (someone manually changed permissions; storage layer misconfiguration), the same exception fires and you investigate. Generic enforcement masks this.

**The model gets a structured signal.** `{sealed: true}` in the response payload is a token the LLM can pattern-match on. It's not a vague "I couldn't save that" — it's a specific, actionable signal that the model uses to give the user a coherent explanation.

**The pattern generalizes.** Use OS-level state changes as your enforcement primitive when the OS supports them; use exception types as your in-process signal channel.

- File should be read-only? `chmod 0444`. Catch `PermissionError`.
- Resource over its quota? Set `RLIMIT_*`. Catch `OSError`.
- Process should not exceed memory? `setrlimit(RLIMIT_AS)`. Catch `MemoryError`.
- File should not be deleted by accident? `chflags uchg` on macOS, `chattr +i` on Linux. Catch `PermissionError`.

Each of these uses the OS's own enforcement instead of building parallel application-layer machinery. Your code becomes shorter, more reliable, and the failure modes become inspectable via standard tooling (`stat`, `lsattr`, `ls -l`).

**The anti-pattern:**

```python
if self.is_sealed(swarm_guid):
    raise SealedError("nope")  # block in app layer
```

Works, but: now your sealing enforcement lives in N places (every write path needs the check), and any forgotten path is a bypass. We DO have one app-level check (`deploy` rejects redeploy of sealed swarms with HTTP 423) — because there's no OS primitive that says "don't let this directory be overwritten by a deploy operation." Where the OS provides the primitive, lean on it. Where it doesn't, app-layer enforcement is the fallback.

**The lesson:**

`PermissionError` isn't a bug to be hidden. It's a signal to be honored. When you `chmod` a file and a write later fails, that's the system working as designed. Translate the failure into a domain-meaningful response and pass it up the stack as data, not as a stack trace.

The OS already has correct semantics for "this resource is read-only." Use them. Build product on top of OS primitives instead of next to them.
