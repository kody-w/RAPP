"""
pomodoro_service.py — single-file Pomodoro timer.

The whole app: state + API + HTML face in one file. Dispatched via
/api/pomodoro/* by the kernel's service router. State lives in
.brainstem_data/pomodoro.json so it survives a restart.

Endpoints:
    GET  /api/pomodoro/          → HTML face (timer UI)
    POST /api/pomodoro/start     → body: {"phase": "work"|"break", "minutes": 25}
    GET  /api/pomodoro/status    → live remaining seconds + phase
    POST /api/pomodoro/stop      → cancel current timer (logs nothing)
    GET  /api/pomodoro/log       → completed sessions, newest first
"""

import json
import os
import time

name = "pomodoro"

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STATE_FILE = os.path.join(_BASE_DIR, ".brainstem_data", "pomodoro.json")

_DEFAULTS = {"work": 25, "break": 5}


def _load():
    if not os.path.exists(_STATE_FILE):
        return {"current": None, "log": []}
    try:
        with open(_STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"current": None, "log": []}


def _save(state):
    os.makedirs(os.path.dirname(_STATE_FILE), exist_ok=True)
    with open(_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def _settle(state):
    cur = state.get("current")
    if not cur:
        return state
    elapsed = time.time() - cur["started_at"]
    if elapsed >= cur["duration_seconds"]:
        state["log"].insert(0, {
            "phase": cur["phase"],
            "started_at": cur["started_at"],
            "completed_at": cur["started_at"] + cur["duration_seconds"],
            "duration_seconds": cur["duration_seconds"],
        })
        state["current"] = None
    return state


def _status_payload(state):
    cur = state.get("current")
    if not cur:
        return {"running": False, "log_count": len(state.get("log", []))}
    elapsed = time.time() - cur["started_at"]
    remaining = max(0, cur["duration_seconds"] - elapsed)
    return {
        "running": True,
        "phase": cur["phase"],
        "started_at": cur["started_at"],
        "duration_seconds": cur["duration_seconds"],
        "elapsed_seconds": round(elapsed, 1),
        "remaining_seconds": round(remaining, 1),
        "log_count": len(state.get("log", [])),
    }


def handle(method, path, body):
    state = _settle(_load())

    if method == "GET" and path in ("", "/"):
        _save(state)
        return _HTML.encode("utf-8"), 200, {"Content-Type": "text/html; charset=utf-8"}

    if method == "POST" and path == "start":
        phase = (body or {}).get("phase", "work")
        if phase not in ("work", "break"):
            return {"error": "phase must be 'work' or 'break'"}, 400
        minutes = float((body or {}).get("minutes", _DEFAULTS[phase]))
        state["current"] = {
            "phase": phase,
            "started_at": time.time(),
            "duration_seconds": minutes * 60.0,
        }
        _save(state)
        return _status_payload(state), 200

    if method == "POST" and path == "stop":
        state["current"] = None
        _save(state)
        return {"running": False}, 200

    if method == "GET" and path == "status":
        _save(state)
        return _status_payload(state), 200

    if method == "GET" and path == "log":
        _save(state)
        return {"log": state.get("log", [])}, 200

    return {"error": f"unknown route: {method} /api/pomodoro/{path}"}, 404


_HTML = """<!doctype html>
<meta charset="utf-8">
<title>Pomodoro</title>
<style>
  body { font: 16px/1.4 -apple-system, system-ui, sans-serif; background: #0d1117; color: #e6edf3; margin: 0; padding: 24px; max-width: 520px; margin: 0 auto; }
  h1 { font-size: 18px; opacity: .7; font-weight: 500; margin: 0 0 24px; }
  .timer { font-variant-numeric: tabular-nums; font-size: 96px; text-align: center; margin: 24px 0; }
  .phase { text-align: center; opacity: .6; text-transform: uppercase; letter-spacing: 2px; font-size: 12px; }
  .row { display: flex; gap: 8px; justify-content: center; margin: 16px 0; }
  button { background: #21262d; color: #e6edf3; border: 1px solid #30363d; padding: 10px 16px; border-radius: 6px; cursor: pointer; font: inherit; }
  button:hover { background: #30363d; }
  .work { color: #f78166; }
  .break { color: #56d364; }
  .log { margin-top: 32px; border-top: 1px solid #30363d; padding-top: 16px; font-size: 13px; opacity: .8; }
  .log-row { display: flex; justify-content: space-between; padding: 4px 0; }
</style>
<h1>🍅 Pomodoro</h1>
<div class="phase" id="phase">idle</div>
<div class="timer" id="timer">--:--</div>
<div class="row">
  <button onclick="start('work', 25)">Start work (25)</button>
  <button onclick="start('break', 5)">Start break (5)</button>
  <button onclick="stop()">Stop</button>
</div>
<div class="log" id="log"></div>
<script>
async function api(method, path, body) {
  const r = await fetch('/api/pomodoro/' + path, {
    method, headers: {'Content-Type': 'application/json'},
    body: body ? JSON.stringify(body) : undefined
  });
  return r.json();
}
function fmt(s) {
  s = Math.max(0, Math.round(s));
  const m = String(Math.floor(s / 60)).padStart(2, '0');
  const sec = String(s % 60).padStart(2, '0');
  return m + ':' + sec;
}
async function tick() {
  const s = await api('GET', 'status');
  const phase = document.getElementById('phase');
  const timer = document.getElementById('timer');
  if (s.running) {
    phase.textContent = s.phase;
    phase.className = 'phase ' + s.phase;
    timer.textContent = fmt(s.remaining_seconds);
  } else {
    phase.textContent = 'idle';
    phase.className = 'phase';
    timer.textContent = '--:--';
    refreshLog();
  }
}
async function refreshLog() {
  const r = await api('GET', 'log');
  const el = document.getElementById('log');
  el.innerHTML = (r.log || []).slice(0, 8).map(e => {
    const d = new Date(e.completed_at * 1000).toLocaleTimeString();
    const m = Math.round(e.duration_seconds / 60);
    return '<div class="log-row"><span class="' + e.phase + '">' + e.phase + ' · ' + m + 'm</span><span>' + d + '</span></div>';
  }).join('') || '<div style="opacity:.5">no completed sessions yet</div>';
}
async function start(phase, minutes) { await api('POST', 'start', {phase, minutes}); tick(); }
async function stop() { await api('POST', 'stop'); tick(); }
tick(); refreshLog();
setInterval(tick, 1000);
</script>
"""
