# Beyond same-machine tether: a Cloudflare relay for cross-device

The current tether and swarm endpoints both assume same-machine reach. Your laptop's browser talks to your laptop's `localhost:8765` (tether) or `localhost:7080` (swarm). That works. It doesn't help when your phone wants to reach your laptop — different network paths, no localhost on a phone reaching another box, NAT traversal headaches.

The natural extension is a relay. This post is the design we'd build, with the tradeoffs visible upfront.

**Architecture:**

```
  phone browser ─POST─▶ relay.workers.dev ─SSE/WS─▶ laptop
                                             │
                                             └─▶ laptop's swarm endpoint
                                                   │
                                                   ▼
                                                 reply
```

Three actors. The relay is a Cloudflare Worker (or Deno Deploy, or Lambda — same shape). The laptop runs the existing `swarm/server.py` plus a small client that maintains a persistent connection to the relay. The phone (or any browser) talks to the relay as if it were the swarm endpoint.

**Authentication:** GitHub identity, same as the brainstem. The laptop registers itself with the relay using the user's GitHub token; the relay knows "this socket is wildfeuer05@gmail.com's box-1." The browser presents its own GitHub token and the relay only routes to the matching identity's online boxes.

**Presence:** the laptop's client opens a long-lived WebSocket to the relay on startup. Relay tracks `(github_user, box_id) → socket`. When the laptop quits, the socket closes; the relay marks it offline. A `/api/relay/devices` endpoint lists everything online for the calling identity.

**Routing:** every request from the browser to `relay.workers.dev/swarm/{guid}/agent` becomes:
1. Look up which laptop hosts `swarm/{guid}` (cached after first call).
2. Forward over the laptop's open socket as a JSON message: `{ id, method: 'POST', path, body }`.
3. Wait for the laptop to reply with `{ id, status, body }`.
4. Translate back to HTTP, return to browser.

The hop adds maybe 50ms of latency. For chat-shaped workloads that's invisible.

**The trade-offs you take on:**

- **Connection state.** Workers are stateless; we'd need Durable Objects (or a Redis equivalent) to hold WebSocket connections across regions. Cloudflare's Durable Objects are the natural fit — one DO per `(user, box_id)`.
- **Cost shape.** Workers free tier covers basic use. Durable Objects + WebSocket-hours move you onto paid plans somewhere around "actually using this regularly." Probably $1-5/mo for one heavy user.
- **Quoted credentials.** The laptop's process is now exposed to anyone with your GitHub token AND the relay endpoint. The token has narrow scope (just the `read:user` we already use) so this is bounded, but it is a meaningful expansion of attack surface vs. localhost-only.
- **Observability.** When something goes wrong you have to debug at three points instead of one. Logging discipline matters more.

**What we'd ship first:** read-only relay. Browser → relay → laptop swarm read endpoints (`GET /healthz`, `GET /agents/list`). No write endpoints. Lets people inspect their swarms from anywhere without expanding the blast radius.

**What we'd ship second:** writes. Agent calls. Memory operations. Real chat-from-anywhere usability.

**What we wouldn't ship:** a "discover other people's swarms" surface. The whole identity model is "your boxes only." Adding sharing crosses into product territory we haven't designed for.

A relay is a separate post on a separate page that the user opts in to. The localhost path stays the default; this is the upgrade for users who actually want cross-device reach.
