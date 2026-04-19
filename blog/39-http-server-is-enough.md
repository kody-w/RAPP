# `http.server` is enough

The swarm server (`swarm/server.py`) and the tether server (`tether/server.py`) are both Python HTTP servers that run on a developer's laptop. The community RAPP brainstem uses Flask. Most "I need an HTTP endpoint in Python" tutorials reach for FastAPI or Flask. We deliberately use Python's stdlib `http.server` for the standalone components.

The case against `http.server` is real and well-known:

- **Single-threaded by default.** One request at a time.
- **No routing.** You write your own URL parser.
- **No middleware.** No auto-JSON, no auto-CORS, no auto-validation.
- **No async.** Pure synchronous request handling.

For most web apps, those tradeoffs aren't worth it — you want a framework. For a *local* server doing chat-shaped work, they're exactly right.

**The math:**

- Chat workloads have low concurrency. One user typing into a UI generates one request at a time, occasionally with overlap during streaming. Single-threaded handling is fine. (If we ever needed concurrency: `ThreadingHTTPServer` is a one-line swap.)
- The whole server is two endpoints. Writing a 5-line routing function (split path, dispatch by exact match) takes less time than learning a framework's router decorators.
- CORS is half a function. JSON parsing is `json.loads(self.rfile.read(n))`. There's nothing the framework would auto-do that's faster than writing it yourself, once.
- No async means no `async def` everywhere, no event loop, no "wait, why is my function never called" debugging. Synchronous code is the default mental model; you only escape it when you have a reason.

**What the whole server looks like:**

```python
from http.server import BaseHTTPRequestHandler, HTTPServer
import json, re

class SwarmHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        # ... CORS headers ...
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/swarm/healthz":
            return self._send_json(200, {"status": "ok", ...})
        m = re.match(r"^/api/swarm/([0-9a-f-]+)/healthz/?$", self.path)
        if m:
            return self._send_json(200, manifest_for(m.group(1)))
        return self._send_json(404, {"status": "error"})

    def do_POST(self):
        # ... etc
        pass

server = HTTPServer(("127.0.0.1", 7080), SwarmHandler)
server.serve_forever()
```

That's the whole shape. About 50 lines of "framework code" for any number of routes.

**What you give up:**

- **No automatic routing.** You write `if self.path == ... elif ...` chains. If you have 50 routes, they get long.
- **No automatic validation.** You parse the JSON body manually. If a field is missing or wrong type, you check explicitly.
- **No automatic OpenAPI.** The framework can't generate docs from your handler signatures because there are no signatures.

For a server with 5-10 routes (and ours has 5), none of these matter. For a server with 50 routes, they do.

**Practical wins:**

- **Stdlib means stdlib.** No `pip install`, no virtualenv, no requirements.txt. The user runs `python swarm/server.py` and it just works on any Python ≥3.8. Our install scripts don't ship a venv because they don't need one.
- **Boot time is microseconds.** Flask loads decorators and middleware. `http.server` doesn't load anything you didn't import. The swarm server is responsive immediately.
- **Failure modes are obvious.** When something breaks, the stack trace points at your code, not at framework internals. Debugging is easier when there's less stack between your code and the OS.

**When to NOT use `http.server`:**

- You need real concurrency (high-throughput services).
- You have many routes (>20) and want auto-routing to keep them organized.
- You need WebSockets or async (use FastAPI / Starlette).
- You need middleware (auth, rate limiting, logging) that's already a solved problem.

**The principle:**

Reach for the smallest tool that does the job. If `http.server` is enough, use `http.server`. If you outgrow it, the migration to Flask or FastAPI is mechanical — your handlers become decorators, your routing becomes URL converters, your `_send_json` becomes `return jsonify(...)`. You haven't locked anything in by starting small.

Ship the smallest thing. Add framework when you have a reason. The reason almost never arrives.
