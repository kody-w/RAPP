# Twin Simulator: deterministic ports from name hash

You type one command:

```bash
bash hippocampus/twin-sim.sh start molly
```

A few seconds later, the script prints a URL on `127.0.0.1`, writes a `workspace.json` file under `~/.rapp-twins/molly/`, and leaves a Python server running in the background. If you reboot your machine and run the same command again, Molly comes back on the same port. No registry. No lock service. No “next available port” scan. The name alone decides where the twin lives.

That design sits in one small function in `hippocampus/twin-sim.sh`:

```bash
# Deterministic port: 7090 + (name-hash % 100). Reproducible across runs.
port_for() {
    local name="$1"
    python3 -c "import sys, hashlib; n = sys.argv[1]; print(7090 + int(hashlib.sha256(n.encode()).hexdigest(), 16) % 100)" "$name"
}
```

The rule is simple: take the twin’s name, hash it with SHA-256, reduce it modulo 100, then add 7090. Same name in, same port out. Every time.

The startup path reinforces that idea. In `cmd_start()`, the script normalizes the name, computes the port, creates the directory, writes metadata, and launches `swarm/server.py` with that root:

```bash
cmd_start() {
    local name="$1"
    [ -z "$name" ] && { echo "usage: twin-sim.sh start <name>"; exit 2; }
    name=$(echo "$name" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-')

    if twin_running "$name"; then
        echo "✓ '$name' already running on http://127.0.0.1:$(port_for "$name")"
        return 0
    fi

    local d=$(twin_dir "$name")
    local port=$(port_for "$name")
    mkdir -p "$d"

    # Free the port if a stale server is squatting on it
    lsof -ti:$port 2>/dev/null | xargs -r kill -9 2>/dev/null || true
```

There is no allocator call because there is nothing to allocate. The script derives, then starts.

The `workspace.json` file is there for convenience and inspection, not as the source of truth for port assignment. The code writes the port into metadata every time startup runs:

```python
mp = d / "workspace.json"
meta = json.loads(mp.read_text()) if mp.exists() else {}
meta.setdefault("name", name)
meta.setdefault("created_at", datetime.datetime.utcnow().isoformat() + "Z")
meta["port"] = port
meta["url"] = f"http://127.0.0.1:{port}"
mp.write_text(json.dumps(meta, indent=2))
```

That detail matters. The simulator is reproducible because the port comes from the name hash, not from whatever happened to be written last week. `workspace.json` records the result; it does not invent it.

There are tradeoffs. A modulo-100 range means collisions are possible: two different names can hash to the same offset. The source does not describe a collision-resolution scheme. The startup path also force-frees the computed port with `lsof -ti:$port | xargs -r kill -9` before launch. That clears stale listeners, but it also means “deterministic” here describes address selection, not safe coexistence with whatever else may already be bound there. If another local process is using that port, the script will terminate it. If two distinct twin names hash to the same port, the code shown here does not resolve that conflict.

For local development, the upside is still clear. You can tell a teammate, “Start `molly`,” and both of you can predict where it will be. You can script peer links and health checks against stable localhost addresses. You can stop a twin, keep its files, and bring it back without consulting any shared service.

A twin here is a name, a hash, a port, and a directory under `~/.rapp-twins/<name>/`. That is enough to make it come back the same way tomorrow.
