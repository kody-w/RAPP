# Snapshots as conversational artifacts, not backups

Most snapshot systems are restore-overs. You took a snapshot last Tuesday; today's filesystem is corrupted; you restore from Tuesday and Tuesday's state replaces today's. The snapshot is a recovery mechanism. Its consumer is the system administrator.

Swarm snapshots in RAPP are not that. They're not a recovery mechanism. They're not consumed by sysadmins.

A swarm snapshot is a frozen, queryable, conversable copy of the swarm at a moment in time. You take a snapshot of grandfather's twin every year on his birthday. After he's gone, you don't restore from a snapshot — you *visit* it. You have a conversation with grandfather-at-age-30, alongside (not instead of) the final-sealed grandfather-at-age-86.

```
POST /api/swarm/{guid}/snapshots/{snap_name}/agent
     body: {name: "AskGrandfather", args: {...}}
     → output from agents loaded from the snapshot's frozen state
```

That endpoint shape — `/snapshots/{name}/agent` instead of `/snapshots/{name}/restore` — encodes the design. Snapshots are reachable as their own conversational endpoints. They don't displace the active swarm. They coexist.

**Three things this changes:**

**Snapshots are read-only forever, not just until restore.** A snapshot can never become writable. There's no "promote to current" operation. This simplifies the mental model: snapshots are crystallized past states; you can talk to them, you can't change them, ever.

**Multiple snapshots can be conversed with concurrently.** Three different descendants can each be in a separate conversation with grandfather-at-30, grandfather-at-50, and grandfather-at-70 at the same time. None of those conversations affect each other or the live swarm. A single deceased grandfather is reachable as multiple temporal versions in parallel.

**The product surface stops being "snapshot management" and becomes "memorial visit."** Grandchildren don't see a snapshot picker. They see a list of "grandfather at moments." The fact that "moments" are technically snapshots is an implementation detail.

**The implementation is small:**

```python
def execute_against_snapshot(self, swarm_guid, snapshot_name, agent_name, args, user_guid):
    snap_root = self.snapshots_dir(swarm_guid) / snapshot_name
    if not snap_root.exists():
        return {"status": "error", "message": f"snapshot not found: {snapshot_name}"}

    cache_key = f"{swarm_guid}::snapshot::{snapshot_name}"
    if cache_key not in self._loaded_agents:
        # Load agents from the frozen snapshot directory
        # ... importlib.util.spec_from_file_location with unique modnames ...

    agents = self._loaded_agents[cache_key]
    agent = agents.get(agent_name)

    # Memory points at frozen tree, which is chmod 0444 from the snapshot copy
    mem_path = snap_root / "memory" / (user_guid or "shared") / "memory.json"
    os.environ["BRAINSTEM_MEMORY_PATH"] = str(mem_path)
    output = agent.perform(**(args or {}))
    return {"status": "ok", "output": output, "snapshot": snapshot_name, "read_only": True}
```

Same memory routing as the live agent path. Same agent execution. Different swarm-state directory. Snapshots reuse the existing conversational machinery; they're not a separate code path.

**What snapshots are NOT:**

- **Backups.** Use a backup tool for backups. Snapshots are conversational endpoints.
- **Branches.** Git-style "branch off, work in parallel, merge back" is not the model. Snapshots are read-only forever.
- **Versions.** Software versioning ("v1.2.3") implies linearity and supersession. Snapshots are temporal coordinates of the same person.

**The lesson:** when you give an old word a new product role, its connotations follow you. "Snapshot" implies "temporary backup you might restore from." The product needs to teach a new connotation: "moment in a lifetime you can visit."

The endpoint shape does some of that teaching. Calling them "moments" instead of "snapshots" in user-facing copy does the rest.
