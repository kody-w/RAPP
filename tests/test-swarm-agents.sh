#!/bin/bash
# tests/test-swarm-agents.sh — stdlib-only test of the 7 swarm-management agents.
#
# Proves they are drop-in compatible with any brainstem by instantiating
# each agent directly (no Flask server, no HTTP) against a synthetic
# BRAINSTEM_HOME. Covers happy path + error cases + the end-to-end
# deploy → invoke → snapshot → seal → (refuse delete) → unseal → delete
# lifecycle that every usable swarm goes through.
#
#     bash tests/test-swarm-agents.sh
#
# Exits 0 on success, non-zero with diagnostics on failure.

set -e
set -o pipefail

TEST_HOME="/tmp/rapp-swarm-agents-test-$$"
rm -rf "$TEST_HOME"
mkdir -p "$TEST_HOME"

cleanup() { rm -rf "$TEST_HOME"; }
trap cleanup EXIT

cd "$(dirname "$0")/.."

python3 - <<PY
import json, os, sys, tempfile
from pathlib import Path

os.environ["BRAINSTEM_HOME"] = "$TEST_HOME"
sys.path.insert(0, "rapp_brainstem")

PASS = 0
FAIL = 0
FAIL_NAMES = []

def eq(name, expected, actual):
    global PASS, FAIL
    if expected == actual:
        print(f"  ✓ {name}")
        PASS += 1
    else:
        print(f"  ✗ {name}")
        print(f"      expected: {expected!r}")
        print(f"      actual:   {actual!r}")
        FAIL += 1
        FAIL_NAMES.append(name)

def truthy(name, cond, note=""):
    global PASS, FAIL
    if cond:
        print(f"  ✓ {name}")
        PASS += 1
    else:
        print(f"  ✗ {name}{(' — ' + note) if note else ''}")
        FAIL += 1
        FAIL_NAMES.append(name)

# Import each agent module fresh
from agents.swarm_deploy_agent    import SwarmDeployAgent
from agents.swarm_list_agent      import SwarmListAgent
from agents.swarm_info_agent      import SwarmInfoAgent
from agents.swarm_invoke_agent    import SwarmInvokeAgent
from agents.swarm_seal_agent      import SwarmSealAgent
from agents.swarm_snapshot_agent  import SwarmSnapshotAgent
from agents.swarm_delete_agent    import SwarmDeleteAgent

deploy   = SwarmDeployAgent()
lst      = SwarmListAgent()
info     = SwarmInfoAgent()
invoke   = SwarmInvokeAgent()
seal     = SwarmSealAgent()
snap     = SwarmSnapshotAgent()
delete   = SwarmDeleteAgent()

def pj(raw):
    """parse the agent's JSON string return value"""
    return json.loads(raw)


# ── Section 1: empty state ─────────────────────────────────────────────

print("--- Section 1: empty state ---")
r = pj(lst.perform())
eq("ListSwarms on empty home returns 0 swarms", 0, r["swarm_count"])
eq("ListSwarms status is success",              "success", r["status"])


# ── Section 2: deploy a swarm ──────────────────────────────────────────

print("")
print("--- Section 2: deploy ---")

# Build a tiny bundle with one simple agent
echo_agent_source = """from agents.basic_agent import BasicAgent
import json

class EchoAgent(BasicAgent):
    def __init__(self):
        self.name = "Echo"
        self.metadata = {"name": self.name, "description": "echoes msg", "parameters": {"type":"object","properties":{"msg":{"type":"string"}},"required":["msg"]}}
        super().__init__(name=self.name, metadata=self.metadata)
    def perform(self, **kw):
        return json.dumps({"status": "success", "echoed": kw.get("msg", "")})
"""

bundle = {
    "schema": "rapp-swarm/1.0",
    "name":   "Test Swarm",
    "purpose": "integration test",
    "created_by": "test-suite",
    "agents": [
        {"filename": "echo_agent.py", "source": echo_agent_source},
    ],
}

r = pj(deploy.perform(bundle=bundle))
eq("DeploySwarm happy path: status=success", "success", r["status"])
GUID = r.get("swarm_guid", "")
truthy("DeploySwarm returned a GUID", bool(GUID))
eq("DeploySwarm reports 1 agent", 1, r["agent_count"])
truthy("DeploySwarm wrote manifest.json",
       Path(r["path"]).joinpath("manifest.json").is_file())
truthy("DeploySwarm wrote echo_agent.py",
       Path(r["path"]).joinpath("agents/echo_agent.py").is_file())
truthy("DeploySwarm created memory/shared dir",
       Path(r["path"]).joinpath("memory/shared").is_dir())
truthy("DeploySwarm returns data_slush with swarm_guid",
       r.get("data_slush", {}).get("swarm_guid") == GUID)

# Error: bundle with no name
r = pj(deploy.perform(bundle={"schema": "rapp-swarm/1.0", "agents": []}))
eq("DeploySwarm rejects bundle without name",   "error", r["status"])

# Error: bad agent filename
r = pj(deploy.perform(bundle={
    "schema": "rapp-swarm/1.0", "name": "x",
    "agents": [{"filename": "../escape.py", "source": ""}]
}))
eq("DeploySwarm rejects path-traversal filename", "error", r["status"])

# Error: filename not ending in _agent.py
r = pj(deploy.perform(bundle={
    "schema": "rapp-swarm/1.0", "name": "x",
    "agents": [{"filename": "bad.py", "source": ""}]
}))
eq("DeploySwarm rejects non-_agent.py filename", "error", r["status"])

# Error: bundle_path doesn't exist
r = pj(deploy.perform(bundle_path="/tmp/nonexistent_bundle_12345.json"))
eq("DeploySwarm errors on missing bundle_path", "error", r["status"])

# bundle_path: write a real bundle to disk and load it
with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
    json.dump({
        "schema": "rapp-swarm/1.0",
        "name":   "From Path",
        "agents": [{"filename": "echo_agent.py", "source": echo_agent_source}],
    }, f)
    path_bundle = f.name
r = pj(deploy.perform(bundle_path=path_bundle))
eq("DeploySwarm via bundle_path: status=success", "success", r["status"])
GUID2 = r["swarm_guid"]
os.unlink(path_bundle)


# ── Section 3: list + info ─────────────────────────────────────────────

print("")
print("--- Section 3: list + info ---")
r = pj(lst.perform())
eq("ListSwarms now sees 2 swarms", 2, r["swarm_count"])
guids = sorted(s["swarm_guid"] for s in r["swarms"])
eq("ListSwarms returns both GUIDs", sorted([GUID, GUID2]), guids)

r = pj(info.perform(swarm_guid=GUID))
eq("SwarmInfo status=success",               "success", r["status"])
eq("SwarmInfo name matches",                 "Test Swarm", r["name"])
eq("SwarmInfo agent_count=1",                1, r["agent_count"])
eq("SwarmInfo sealed=False initially",       False, r["sealed"])
eq("SwarmInfo lists echo_agent.py",          ["echo_agent.py"], r["agents"])

# Error: info on missing swarm
r = pj(info.perform(swarm_guid="00000000-0000-0000-0000-000000000000"))
eq("SwarmInfo on missing guid: status=error", "error", r["status"])

# Error: info with invalid guid format
r = pj(info.perform(swarm_guid="not-a-guid"))
eq("SwarmInfo with bad guid: status=error",  "error", r["status"])


# ── Section 4: invoke ──────────────────────────────────────────────────

print("")
print("--- Section 4: invoke ---")
r = pj(invoke.perform(swarm_guid=GUID, agent_name="Echo", args={"msg": "hello"}))
eq("InvokeSwarmAgent: status=success", "success", r["status"])
inner = pj(r["result"])
eq("InvokeSwarmAgent returns the sibling agent's payload",
   "hello", inner["echoed"])

# Error: unknown agent in swarm
r = pj(invoke.perform(swarm_guid=GUID, agent_name="NoSuchAgent", args={}))
eq("InvokeSwarmAgent errors on unknown agent_name", "error", r["status"])

# Error: args must be dict
r = pj(invoke.perform(swarm_guid=GUID, agent_name="Echo", args="nope"))
eq("InvokeSwarmAgent rejects non-dict args", "error", r["status"])

# Invoke also rebinds BRAINSTEM_MEMORY_PATH to the sibling swarm, restoring
# on exit. Confirm the env is clean after call.
prev_mem = os.environ.get("BRAINSTEM_MEMORY_PATH")
_ = pj(invoke.perform(swarm_guid=GUID, agent_name="Echo", args={"msg": "x"}))
eq("InvokeSwarmAgent restores BRAINSTEM_MEMORY_PATH env",
   prev_mem, os.environ.get("BRAINSTEM_MEMORY_PATH"))


# ── Section 5: seal + unseal ───────────────────────────────────────────

print("")
print("--- Section 5: seal ---")
r = pj(seal.perform(swarm_guid=GUID, action="status"))
eq("SealSwarm status on unsealed: sealed=False", False, r["sealed"])

r = pj(seal.perform(swarm_guid=GUID, action="seal", reason="testing"))
eq("SealSwarm seal: sealed=True",  True, r["sealed"])
eq("SealSwarm seal: changed=True", True, r["data_slush"]["changed"])

r = pj(seal.perform(swarm_guid=GUID, action="seal"))
eq("SealSwarm seal-when-sealed: changed=False", False, r["data_slush"]["changed"])

r = pj(info.perform(swarm_guid=GUID))
eq("SwarmInfo reflects seal=True",  True, r["sealed"])

# ── Section 6: snapshot — refused when sealed, allowed when unsealed ───

print("")
print("--- Section 6: snapshot ---")
r = pj(snap.perform(swarm_guid=GUID, action="create", name="attempt-during-seal"))
eq("SnapshotSwarm refused on sealed swarm", "error", r["status"])

r = pj(seal.perform(swarm_guid=GUID, action="unseal"))
eq("SealSwarm unseal: sealed=False", False, r["sealed"])

r = pj(snap.perform(swarm_guid=GUID, action="create", name="milestone-1"))
eq("SnapshotSwarm create: status=success",      "success", r["status"])
eq("SnapshotSwarm create: name=milestone-1",   "milestone-1", r["snapshot_name"])
truthy("SnapshotSwarm copied manifest.json",
       Path(r["path"]).joinpath("manifest.json").is_file())
truthy("SnapshotSwarm copied agents/echo_agent.py",
       Path(r["path"]).joinpath("agents/echo_agent.py").is_file())
truthy("SnapshotSwarm wrote .snapshot.json stamp",
       Path(r["path"]).joinpath(".snapshot.json").is_file())

# Error: duplicate snapshot name
r = pj(snap.perform(swarm_guid=GUID, action="create", name="milestone-1"))
eq("SnapshotSwarm rejects duplicate name", "error", r["status"])

# Error: bad snapshot name
r = pj(snap.perform(swarm_guid=GUID, action="create", name="../escape"))
eq("SnapshotSwarm rejects path-traversal name", "error", r["status"])

# List
r = pj(snap.perform(swarm_guid=GUID, action="list"))
eq("SnapshotSwarm list: 1 snapshot",  1, r["snapshot_count"])
eq("SnapshotSwarm list: correct name", ["milestone-1"], r["snapshots"])

# Info now reflects snapshot count
r = pj(info.perform(swarm_guid=GUID))
eq("SwarmInfo reports snapshot_count=1", 1, r["snapshot_count"])


# ── Section 7: delete lifecycle ────────────────────────────────────────

print("")
print("--- Section 7: delete ---")

# Refuse without confirm
r = pj(delete.perform(swarm_guid=GUID2))
eq("DeleteSwarm refuses without confirm=true", "error", r["status"])

# Seal → delete refused
r = pj(seal.perform(swarm_guid=GUID2, action="seal"))
eq("Seal GUID2",  True, r["sealed"])
r = pj(delete.perform(swarm_guid=GUID2, confirm=True))
eq("DeleteSwarm refused while sealed", "error", r["status"])

# Unseal → delete allowed
r = pj(seal.perform(swarm_guid=GUID2, action="unseal"))
eq("Unseal GUID2", False, r["sealed"])
r = pj(delete.perform(swarm_guid=GUID2, confirm=True))
eq("DeleteSwarm succeeds after unseal", "success", r["status"])

# List now shows 1
r = pj(lst.perform())
eq("ListSwarms after delete: 1 swarm", 1, r["swarm_count"])


# ── Section 8: drop-in compat — operate against an ad-hoc swarms root ──

print("")
print("--- Section 8: BRAINSTEM_HOME drop-in compat ---")

ALT = "/tmp/rapp-swarm-agents-test-alt-$$"
import shutil as _sh
_sh.rmtree(ALT, ignore_errors=True)
Path(ALT).mkdir(parents=True, exist_ok=True)
os.environ["BRAINSTEM_HOME"] = ALT

# The same agent instances (reusing objects we built before) MUST honor
# the new env — proving they resolve state on every call, never caching.
r = pj(lst.perform())
eq("ListSwarms on fresh BRAINSTEM_HOME: 0 swarms", 0, r["swarm_count"])

r = pj(deploy.perform(bundle={
    "schema": "rapp-swarm/1.0", "name": "Alt Home",
    "agents": [{"filename": "echo_agent.py", "source": echo_agent_source}],
}))
eq("DeploySwarm against alt home: success", "success", r["status"])
ALT_GUID = r["swarm_guid"]

truthy("Deploy wrote into alt home",
       Path(ALT).joinpath("swarms", ALT_GUID, "manifest.json").is_file())

# Flip back — the original swarm still listed only what's under its own home
os.environ["BRAINSTEM_HOME"] = "$TEST_HOME"
r = pj(lst.perform())
eq("After env flip back: only original 1 swarm visible", 1, r["swarm_count"])

_sh.rmtree(ALT, ignore_errors=True)


# ── Summary ────────────────────────────────────────────────────────────

print("")
print("=" * 40)
print(f"  {PASS} passed, {FAIL} failed")
print("=" * 40)
if FAIL:
    for n in FAIL_NAMES:
        print(f"  - {n}")
    sys.exit(1)
sys.exit(0)
PY
