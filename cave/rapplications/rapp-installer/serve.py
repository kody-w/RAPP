#!/usr/bin/env python3
"""
serve.py — boot the RAPP Installer as a SELF-CONTAINED, repo-independent
brainstem rapplication.

This is the whole RAPP brainstem (the "grail" engine) ported OUT of the
kody-w/rapp-installer git repo so you can run it, develop agents against it,
and edit it in VS Code WITHOUT any risk of accidentally committing to the
sacred grail. It lives in a cubby (~/.brainstem/cubbies/rapp-installer/),
which is not a git repo — so there is nothing to accidentally commit.

Unlike a normal "summoned" rapplication, this one carries its OWN copy of the
kernel under ./kernel/ and points KERNEL at it. It NEVER imports the engine
from ~/.brainstem/src/rapp_brainstem (the grail). Prove it:

    grep -R "/.brainstem/src" serve.py   # → no matches

The bundled kernel (kernel/brainstem.py) is byte-identical to the grail's, so
this rapplication does everything the rapp installer's brainstem does:
GitHub-Copilot auth, /chat agent orchestration, the web UI, the agent system,
memory agents, model switching, voice mode — full parity.

Run:
    python3 serve.py                 # serves on :7077 (coexists with a :7071 grail)
    PORT=7071 python3 serve.py       # or pick your own port

Endpoints: every kernel route (/, /chat, /agents, /models, /health, /login, …)
plus /api/agent/<Name> (call a loaded agent's perform(**body) directly, no LLM).
"""
import os
import sys

# Everything resolves relative to THIS file, so the rapplication works wherever
# the egg is hatched — no absolute paths, no grail dependency.
HERE   = os.path.dirname(os.path.abspath(__file__))
KERNEL = os.environ.get("KERNEL") or os.path.join(HERE, "kernel")     # bundled engine — NOT the grail
WEB    = os.path.join(HERE, "web")

# Hard guard: refuse to boot against the grail repo (or anything under it) even
# if KERNEL is mis-set — mirrors hatch.py's grail guard.
_grail = os.path.realpath(os.path.expanduser("~/.brainstem/src/rapp_brainstem"))
_rp = os.path.realpath(KERNEL)
if _rp == _grail or _rp.startswith(_grail + os.sep):
    sys.exit("[rapp-installer] refusing to boot against the grail repo — set KERNEL to the bundled ./kernel")

# brainstem.py reads AGENTS_PATH / SOUL_PATH at import time — set them BEFORE importing.
os.environ.setdefault("AGENTS_PATH", os.path.join(HERE, "agents"))
os.environ.setdefault("SOUL_PATH",   os.path.join(HERE, "soul.md"))

sys.path.insert(0, KERNEL)
os.chdir(KERNEL)                       # runtime state (.copilot_*, book.json) stays inside the cubby
import brainstem                       # the bundled kernel — defines app, does NOT run (guarded by __main__)
from flask import send_from_directory, request, jsonify


def _index():
    """Serve the rapplication's web UI (web/index.html) at /."""
    return send_from_directory(WEB, "index.html")
brainstem.app.view_functions["index"] = _index     # override ONLY the landing view


@brainstem.app.route("/app/<path:p>")
def _app_asset(p):
    return send_from_directory(WEB, p)


@brainstem.app.route("/api/agent/<name>", methods=["POST"])
def _agent_call(name):
    """Call a loaded agent's perform(**body) directly — no LLM round-trip."""
    try:
        agents = brainstem.load_agents()
        inst = agents.get(name)
        if inst is None:
            return jsonify({"ok": False, "error": f"no agent '{name}'",
                            "available": sorted(agents)}), 404
        body = request.get_json(silent=True) or {}
        return jsonify({"ok": True, "result": inst.perform(**body)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7077"))   # 7077 by default so it coexists with a :7071 grail
    print(f"[rapp-installer] self-contained brainstem  ws={HERE}", flush=True)
    print(f"[rapp-installer] kernel={KERNEL}  (bundled — NOT the grail)", flush=True)
    print(f"[rapp-installer] serving on http://localhost:{port}", flush=True)
    brainstem.app.run(host="0.0.0.0", port=port, debug=False)
