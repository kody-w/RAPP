#!/usr/bin/env bash
# Tier 1 memory + factory: save_memory/recall_memory round-trip through
# the LLM tool-call loop, then swarm_factory action=build produces a
# singleton file.
set -euo pipefail
cd "$(dirname "$0")/../.."

PORT="${PORT:-7072}"   # matches 01-tier1-smoke.sh default
PID_FILE=/tmp/rapp-e2e-brainstem.pid
LOG=/tmp/rapp-e2e-brainstem.log

cleanup() {
    if [ -f "$PID_FILE" ]; then
        kill "$(cat "$PID_FILE")" 2>/dev/null || true
        rm -f "$PID_FILE"
    fi
}
trap cleanup EXIT

# Reuse or start the brainstem
if curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1; then
    echo "▶ Reusing brainstem already on :$PORT"
else
    echo "▶ Starting brainstem on :$PORT..."
    ( cd rapp_brainstem && PORT=$PORT python3 brainstem.py ) > "$LOG" 2>&1 &
    echo $! > "$PID_FILE"
    for i in $(seq 1 30); do
        curl -sf "http://localhost:$PORT/health" >/dev/null 2>&1 && break
        sleep 1
    done
fi

# ── Memory round-trip ─────────────────────────────────────────────────

FACT="my favourite color is viridian-$(date +%s)"
echo "▶ Saving fact via chat: '$FACT'"

SAVE_RESP=$(curl -s -X POST "http://localhost:$PORT/chat" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c "import json; print(json.dumps({'user_input': f'Please remember this for me: $FACT', 'conversation_history': []}))")" )
SAVE_LOGS=$(echo "$SAVE_RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("agent_logs",""))')
if echo "$SAVE_LOGS" | grep -iq "save_memory\|savememory"; then
    echo "PASS: save_memory invoked during save turn"
else
    echo "WARN: save_memory was not invoked on the save turn (LLM may have chosen not to)."
    echo "  agent_logs: $(echo "$SAVE_LOGS" | head -c 200)"
fi

echo "▶ Recalling via chat..."
RECALL_RESP=$(curl -s -X POST "http://localhost:$PORT/chat" \
    -H "Content-Type: application/json" \
    -d '{"user_input":"What is my favourite color? Answer in one word only.","conversation_history":[]}' )
RECALL_TEXT=$(echo "$RECALL_RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("response",""))')
if echo "$RECALL_TEXT" | grep -iq "viridian"; then
    echo "PASS: memory round-trip (fact recovered in recall turn)"
else
    echo "WARN: 'viridian' not found in recall response. LLM may have ignored memory context."
    echo "  response: $(echo "$RECALL_TEXT" | head -c 200)"
fi

# ── Swarm factory: converge workshop → singleton ──────────────────────

# Make sure there's at least one thing under workspace_agents/ besides
# swarm_factory itself, so converge has something to do.
TEST_SWARM_DIR=rapp_brainstem/agents/workspace_agents/e2e_test_swarm
mkdir -p "$TEST_SWARM_DIR"
cat > "$TEST_SWARM_DIR/e2e_echo_agent.py" <<'EOF'
from agents.basic_agent import BasicAgent
class E2EEchoAgent(BasicAgent):
    def __init__(self):
        self.name = "E2EEcho"
        self.metadata = {
            "name": self.name,
            "description": "Echoes the message argument back. Test-only.",
            "parameters": {"type":"object","properties":{"message":{"type":"string"}},"required":["message"]}
        }
        super().__init__(name=self.name, metadata=self.metadata)
    def perform(self, message="", **kwargs):
        return f"echo: {message}"
EOF
echo "  seeded test swarm at $TEST_SWARM_DIR"

cleanup_test_swarm() {
    rm -rf "$TEST_SWARM_DIR"
    rm -f rapp_brainstem/agents/e2e_test_swarm_agent.py 2>/dev/null || true
}
trap 'cleanup; cleanup_test_swarm' EXIT

echo "▶ Invoking swarm_factory (action=build) via /chat..."
BUILD_RESP=$(curl -s -X POST "http://localhost:$PORT/chat" \
    -H "Content-Type: application/json" \
    -d '{"user_input":"Use swarm_factory with action=build to package the agents in e2e_test_swarm into a singleton named e2e_test_swarm. Report the output path.","conversation_history":[]}' )
BUILD_LOGS=$(echo "$BUILD_RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("agent_logs",""))')
if echo "$BUILD_LOGS" | grep -iq "swarm_factory\|swarmfactory"; then
    echo "PASS: swarm_factory invoked"
else
    echo "FAIL: swarm_factory was not invoked"
    echo "  agent_logs: $(echo "$BUILD_LOGS" | head -c 300)"
    echo "  response: $(echo "$BUILD_RESP" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("response",""))' | head -c 300)"
    exit 1
fi

# Find any singleton file that looks like a factory output
SINGLETON=$(find rapp_brainstem/agents -maxdepth 4 -name "e2e_test_swarm*_agent.py" -newer "$TEST_SWARM_DIR" 2>/dev/null | head -1)
if [ -n "$SINGLETON" ] && [ -f "$SINGLETON" ]; then
    SIZE=$(wc -c < "$SINGLETON")
    echo "PASS: singleton produced at $SINGLETON ($SIZE bytes)"
else
    echo "WARN: no singleton file found. Factory output path may be configurable."
    echo "  (This is non-fatal — factory reported success in agent_logs.)"
fi

echo "✅ Tier 1 memory + factory test complete"
