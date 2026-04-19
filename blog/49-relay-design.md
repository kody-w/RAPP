# The relay design: a Cloudflare Worker that knows which laptop is online

We've shipped two ways to bridge the browser to local agents:

- **Tether** — browser → `localhost:8765` on the same machine.
- **Swarm** — browser → `localhost:7080` on the same machine, multi-tenant via GUID.

Both assume same-machine networking. Both work great when your phone and your laptop happen to be the same device, which they're not.

The design that closes the gap is a *relay* — a small server in the middle that the laptop registers with on startup, and the browser calls instead of localhost. This post is the design we'd build, before we build it.

**Architecture:**

```
phone browser ────POST─────▶ relay.workers.dev ───SSE/WS───▶ laptop
                                      │
                                      └──▶ laptop's swarm endpoint
                                              │
                                              ▼
                                            reply
                                      ▲
                                      └──response back──
                              ◀───────
```

Three actors:
- The relay (Cloudflare Worker + Durable Objects, or any equivalent).
- The user's laptop, running the existing swarm server PLUS a small client that maintains a persistent connection to the relay.
- The browser (any device), talking to the relay as if it were the swarm endpoint.

**Authentication: GitHub identity, end-to-end.**

The same OAuth flow the brainstem already uses. The laptop client signs in with the user's GitHub token at startup. The relay records `(github_user, machine_id) → socket`. The browser presents its own GitHub token; the relay only routes to the matching identity's online machines.

This means: only YOU can reach YOUR laptop. Other users' tokens won't route there. The relay never holds creds long-term — it holds the live socket, which is bound to the current GitHub session.

**Presence: long-lived WebSocket.**

The laptop opens a single WebSocket to the relay on startup and keeps it open. Heartbeats every 30s. When the laptop closes (or the connection drops), the relay marks the session offline. A `/api/relay/devices` endpoint lists everything currently online for the calling identity.

**Routing: requests-as-messages.**

Every request from the browser to `relay.workers.dev/swarm/{guid}/agent` becomes an envelope sent over the laptop's open socket:

```json
{ "id": "req_abc", "method": "POST",
  "path": "/api/swarm/{guid}/agent",
  "body": {...} }
```

The laptop's relay-client receives the envelope, makes the local HTTP call to its own swarm server, and sends the response back over the socket:

```json
{ "id": "req_abc", "status": 200, "body": {...} }
```

The relay marries response to request via the `id`, translates back to HTTP, returns to the browser.

**Latency:**

- Local-network round-trip: ~5ms
- Browser → relay → laptop → swarm: ~50ms (dominated by the WAN hop to the relay region)

Chat-shaped workloads don't notice 50ms. If you're doing real-time anything, the relay isn't the right architecture; the local-only path is.

**The trade-offs you take on:**

- **Connection state.** Workers are stateless; we'd need Durable Objects (or a Redis equivalent) to hold WebSocket connections across regions. CF's Durable Objects are the natural fit — one DO per `(user, machine)`. They scale automatically; cost is per-DO-hour.
- **Cost shape.** Workers free tier covers basic use. DO + WebSocket-hours move you onto paid plans somewhere around "regular daily use." Probably $1-5/month per heavy user.
- **Expanded attack surface.** Your laptop's swarm endpoint is no longer localhost-only. It's reachable by anyone holding your GitHub token AND knowing the relay endpoint. The token has narrow scope (just the `read:user` scope we already use), so this is bounded — but it's a meaningful expansion vs. localhost-only and worth thinking about.
- **Observability.** When something goes wrong you debug at three points instead of one. Log the request ID at every hop.

**What we'd ship first: read-only.**

Browser → relay → laptop's read endpoints (`/healthz`, `/swarm/list`, `/swarm/{guid}/healthz`). No write endpoints exposed through the relay yet. Lets users *inspect* their swarms from anywhere without expanding the blast radius. This is the smallest useful feature: "from my phone, see what's running on my laptop."

**What we'd ship second: writes.**

Agent calls. Memory operations. Real chat-from-anywhere. Once we trust the relay's auth, we open up.

**What we wouldn't ship:**

- A "browse other people's swarms" surface. The whole identity model is "your machines only." Sharing crosses into product territory we haven't designed for.
- A registry of "discoverable swarms." If someone wants to share a swarm, they share the bundle file (sneakernet) and the recipient deploys it locally.
- A managed-hosted version where we run the swarm server for users. We'd have to hold their data, and that changes the product significantly.

**Why we haven't built it yet:**

Same-machine reach covers most actual use. The brainstem in your laptop's browser already talks to your laptop's swarm. Cross-device wants — your phone reaching your laptop — are real but second-order. The first 100 users get more value from the same-machine experience working well than from cross-device working at all.

When the cross-device pull becomes loud enough (probably "I want to ask my brainstem from my phone while away from my laptop" hits ~10x in user requests), we ship the relay.

The design is settled enough that we could ship it in a week. We're banking it.
