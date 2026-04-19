# HTTP 423 Locked is real and useful

When the swarm server gets a deploy request targeting a sealed swarm_guid, it returns:

```http
HTTP/1.1 423 Locked
Content-Type: application/json

{"status":"error","message":"swarm <guid> is sealed; redeploy rejected","sealed":true}
```

`423 Locked`. Not 403. Not 409. Not 500. Almost no API uses 423. You've probably never seen it. It's the right code.

**The 4xx codes you might consider for "you can't do this to this resource":**

| Code | Meaning | Right for sealed-swarm rejection? |
|---|---|---|
| 400 Bad Request | Your request is malformed | No — the request is valid, the target's state isn't |
| 401 Unauthorized | Authenticate first | No — auth isn't the problem |
| 403 Forbidden | You're authenticated but not allowed | Closer — but implies an authorization issue, not a state one |
| 404 Not Found | Resource doesn't exist | No — it exists, in a particular state |
| 409 Conflict | Your request conflicts with current state | Often used for this; defensible |
| 410 Gone | Resource existed but no longer | No — it still exists, just sealed |
| **423 Locked** | **Resource is locked against this kind of access** | **Exactly right** |

`423` was introduced in WebDAV (RFC 4918) for the "the resource you're trying to modify is currently locked" case. The intended use was for collaborative document editing where multiple clients might try to write simultaneously — one client's lock blocks the others.

The semantics generalize beyond WebDAV. Anywhere a resource has a state that *prevents* modification but doesn't prevent identification or read access, 423 fits. Sealed swarms are exactly that. The swarm exists. You can `GET` its state. You can call its agents (read-only). You just can't redeploy or delete it.

**Why not 409?**

`409 Conflict` is a reasonable second-best. It's used for "your request would conflict with the current resource state." Most APIs reach for it because more developers recognize it. The downside is `409` is *generic*: it covers everything from "version mismatch in optimistic concurrency" to "you can't delete a non-empty bucket" to "resource is currently being processed."

`423 Locked` is *specific*: "this resource is in a locked state and that's why you can't do this." A client looking at the response code knows immediately that the issue isn't a transient conflict that retry might resolve — it's a durable state of the target. That distinction matters operationally.

**Why not 403?**

`403 Forbidden` is about authorization. The caller is authenticated (or anonymous) and the system has decided they aren't permitted to do this. With sealed swarms, the issue isn't authorization — even the *original principal* can't redeploy a sealed swarm. The block isn't about who; it's about the resource's state.

**The lesson: use the specific code.**

HTTP has a 60-code surface and most APIs use eight of them. The unused codes aren't decorative — they exist to communicate specific situations. When your situation matches one of them, use it. Clients that read documentation will understand exactly what happened. Clients that don't will at least see the error and can look it up.

Other underused HTTP codes worth knowing:

- **207 Multi-Status** — partial success in batch operations (some items OK, some failed)
- **226 IM Used** — your delta-encoding response is what was asked for (rarely useful but well-defined)
- **402 Payment Required** — for "this operation requires a paid tier" (some APIs use this; we will eventually)
- **418 I'm a Teapot** — joke code, but standardized; valid response for "request makes no sense"
- **425 Too Early** — for "your request was sent before the system is ready to process it"
- **451 Unavailable for Legal Reasons** — when you've taken something down due to legal compliance
- **507 Insufficient Storage** — quota exhausted
- **511 Network Authentication Required** — for captive portal scenarios

If you're shipping APIs, learn the codes. The eight everyone uses (200, 201, 204, 400, 401, 403, 404, 500) are the floor. Going beyond them communicates more.

**The smaller lesson:** when you choose a status code, ask "what would a client implementing my API do differently if they got *this* code instead of a generic one?" If the answer is "nothing," your generic code is fine. If the answer is "they'd retry differently / give the user a different message / log differently," the specific code is the right one.

For sealed swarms, a client should: not retry, surface a "this is preserved" message to the user, optionally offer to query the sealed swarm read-only instead. `423 Locked` cleanly signals all of that. `409 Conflict` would not.
