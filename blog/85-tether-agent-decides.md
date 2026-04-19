# Tether bridge: the agent.py decides

A user asks to see what is in `~/Documents`. The model knows which agent to call: `agents/list_files_agent.py`. That file does not hint at OS access. It says so outright.

```python
__manifest__ = {
    "schema": "rapp-agent/1.0",
    "name": "@rapp/list-files",
    "tier": "core",
    "trust": "community",
    "version": "0.1.0",
    "tags": ["tether", "filesystem"],
    "tether_required": True,
    "example_call": {"args": {"path": "~/Documents"}},
}
```

That one flag changes the path of execution. If `tether_required` is `True`, the call is treated as one that must go through the local tether process to reach the real filesystem. If the tether is not running, the intended behavior is a graceful error so the model can tell the user to start it.

That is the chapter’s core rule: `agent.py` decides.

The design is direct because the boundary is direct. The browser-side brainstem runs in Pyodide. Pyodide can execute Python, but it cannot do the things users usually mean by “use my computer”: read local files, spawn subprocesses, scan the LAN, or talk to hardware. `tether/server.py` exists to bridge exactly that gap.

Its own top-level docstring says the quiet part out loud:

```python
"""
RAPP Tether Server — exposes local *_agent.py files to the virtual brainstem
running at https://kody-w.github.io/RAPP/brainstem/.

Why: the virtual brainstem runs in the browser via Pyodide. Pyodide can't
touch the local filesystem, spawn subprocesses, hit the LAN, or talk to
hardware. The tether server bridges that gap — when "Tether" is enabled in
the virtual brainstem's Settings, every agent call routes through this
process instead of Pyodide, so you get real OS access for free.
"""
```

The trust model follows from that architecture. The tether is not just another tool. It is a local Python process importing agents and running their `perform` methods against the real machine. In `ListFilesAgent`, that means `os.path.exists`, `os.path.isdir`, `os.listdir`, and `os.path.getsize` run against the user’s disk, not a sandbox.

The code is ordinary, which is exactly why it matters. There is no theatrical privilege escalation here, just standard Python doing OS work through the local process:

```python
def perform(self, path="~", max_entries=50, **kwargs):
    target = os.path.expanduser(str(path))
    if not os.path.exists(target):
        return f"Path not found: {target}"
    if not os.path.isdir(target):
        return f"Not a directory: {target}"
    try:
        entries = sorted(os.listdir(target))[: int(max_entries)]
    except PermissionError:
        return f"Permission denied: {target}"
```

That ordinariness is part of the security story. Local execution is powerful, intentional, and gated. The manifest flag is important because it makes the requested execution path explicit, but it is not the only control that matters. The broader boundary also includes the routing layer, the user’s decision to run the tether, and the fact that OS-level actions only become possible when that local process is available.

So the right default is deny. An agent must declare `__manifest__['tether_required'] = True`, and the user must separately opt in by running the tether. That combination does not eliminate risk; it makes the boundary legible before the call leaves the browser.

The value of this pattern is not that it asks for trust. It makes capability visible. You do not infer OS access from behavior after the fact. You read `tether_required: True` before execution crosses from the browser into the local process. In a system like this, that is what a trust model should provide: not “trust me,” but “show me.”
