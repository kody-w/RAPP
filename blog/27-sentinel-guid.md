# `c0p110t0-aaaa-bbbb-cccc-123456789abc`: deliberately invalid GUIDs as a feature

The community RAPP brainstem ships this constant:

```python
DEFAULT_USER_GUID = "c0p110t0-aaaa-bbbb-cccc-123456789abc"
```

It looks like a UUID. It isn't. The first segment contains `p`, `l` — characters that are not legal hex digits. Any UUID parser anywhere will reject it. That rejection is the entire point.

**Why a sentinel?** Anonymous sessions need an identifier. They can't have nothing — too much code assumes a non-empty `user_guid` to route memory and log requests. They can't have a real GUID — we'd be issuing identifiers to anonymous users, which gets you into "should this become an account?" territory and the answer is no. So you pick a marker.

**Why intentionally invalid?** Three benefits, in order of how important they turn out to be:

**1. Database guardrail.** If you're persisting GUIDs in a `UUID` column (Postgres, SQL Server, anywhere with type validation), inserting `c0p110t0-aaaa-bbbb-cccc-123456789abc` raises an error. That's the desired behavior. Anonymous-session events should never end up in your real users table. The invalid string blocks that class of bug at the database layer, before any application code has a chance to make the wrong decision.

**2. Log readability.** Real GUIDs look like `41eacba49218b45e9e3c8cccfdaccc107b40e87d`. They're unmemorable, identical-looking, and easy to skim past. `c0p110t0-aaaa-...` is instantly recognizable in a log line: "anonymous session." When you're debugging a memory routing issue, the difference between staring at three real GUIDs vs. one obvious sentinel is real cognitive load.

**3. Spells "copilot."** `c0p110t0` reads as "copilot" if you're squinting. Non-functional, but: the constant ends up in error messages and UI surfaces sometimes. The fact that it spells the parent product is a small win for whoever has to read it later.

**How the swarm server uses it.** Same exact pattern, lifted verbatim:

```python
def memory_path(self, swarm_guid, user_guid):
    if not user_guid or user_guid == DEFAULT_USER_GUID or not GUID_RE.match(user_guid):
        return self.swarm_dir(swarm_guid) / "memory" / "shared" / "memory.json"
    return self.swarm_dir(swarm_guid) / "memory" / user_guid / "memory.json"
```

Three things route to shared memory: missing GUID, the sentinel, anything that fails the regex. The error-handling fallthrough is *the same as the explicit-anonymous fallthrough*. That's not a bug. It's the design — invalid input is the same as "no user," because we couldn't identify them anyway.

**The pattern generalizes.** Anywhere you have a "this thing must be present but it's not really a thing" slot, give it a sentinel that fails downstream validation. Don't use `null` (it forces null-checks everywhere). Don't use empty string (it's hard to tell from "we forgot to set it"). Use a value that *looks* legal at the type level but *fails* at the validation level.

It's the same trick as `0x00000000-0000-0000-0000-deadbeefcafe` for "we should have set this and didn't, here's a value you can grep for in production." Or `999.999.999.999` for "this is a fake IP we shipped by accident." Sentinels that fail validation are debugging gifts to your future self.

This is one constant in one Python file. It does more work than constants twice its size. The trick is to give it a job *as a value*, not just as a marker.
