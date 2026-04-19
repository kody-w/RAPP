# Authenticated swarms: who can call which `swarm_guid`?

The current swarm server has no auth. If you know the URL of a deployed swarm and you can reach the network it's on, you can call it. For a localhost-bound swarm, the network containment is the security model — `127.0.0.1` is unreachable from the outside, and that's enough.

The moment swarms become network-reachable — exposed via `--host 0.0.0.0` for LAN access, deployed to Azure Functions, or called through a Cloudflare relay — that model breaks. Anyone who can reach the URL can call any swarm. There's no concept of "this swarm belongs to this user" enforced anywhere.

This post is the design we'd ship when we need to add auth.

**Threat model:**

Three kinds of unauthorized access we care about:
1. **Random internet users** finding a public swarm endpoint and pinging it.
2. **Someone within the same LAN** (a coworker, a guest, a compromised IoT device) calling a swarm meant for one user.
3. **A coworker's swarm being called by someone else on the team** when fine-grained access matters.

The first two have the same answer: any auth system will block them. The third is more interesting and is where most of the design decisions live.

**Option A: shared secret per swarm.**

Each swarm gets a randomly-generated token at deploy time. The deploy response includes it:

```json
{
  "status": "ok",
  "swarm_guid": "abc-123",
  "swarm_url": "https://endpoint/api/swarm/abc-123/agent",
  "swarm_token": "rsk_4f2a8b9c..."
}
```

Every subsequent call to that swarm includes `Authorization: Bearer rsk_4f2a8b9c...`. The server validates token against swarm. Tokens stored hashed at rest (bcrypt or similar).

**Pros:** Simple. No auth provider needed. Easy to rotate (re-deploy swarm, get new token). Easy to share (paste token in a Slack DM to a coworker who needs access).
**Cons:** Token sharing is the auth model. Lose the token, lose access. Steal the token, get full access. No fine-grained "user X can call agent Y but not agent Z."

**Option B: GitHub OAuth (matches the rest of RAPP).**

The brainstem already does OAuth. The deploy step records the deployer's GitHub identity. Calls to the swarm require `Authorization: Bearer ghu_...` matching the deployer's identity (or being on an explicit allowlist).

```json
{
  "swarm_guid": "abc-123",
  "owner": "wildfeuer05",
  "allowed_users": ["wildfeuer05", "coworker1@org"]
}
```

**Pros:** Identity-based, not token-based. Revoking access is "remove from allowlist." Sharing is invitation, not credential leak. Same identity model as everything else in RAPP.
**Cons:** Every caller needs an OAuth flow. The swarm server has to validate GitHub tokens (HTTP call to GitHub on every request, or a cache thereof). More moving parts.

**Option C: per-call signed envelopes (what Anthropic uses for some APIs).**

The brainstem signs each request with the user's identity. The swarm server validates the signature. No long-lived bearers; every call is independently authenticated.

**Pros:** Most secure. No standing access — each request must be authentic.
**Cons:** Most complex. Requires a key-management story (where does the signing key live? rotate it how?).

**My pick: A first, B once we have multi-user.**

For the single-user case (your laptop, your swarms), shared secret is enough. The token lives in the brainstem's `state.settings.deployedSwarms` next to the URL. Calls automatically include it. The user never types it.

For the multi-user case (deploying a swarm for a team to call), GitHub OAuth wins. Allowlists by GitHub username are the natural granularity. The brainstem can check "you're already signed into GitHub; you're on this swarm's allowlist" and route accordingly.

C is theoretically nicer but the operational cost is too high for a project this small.

**Per-agent permissions inside a swarm:**

A maximalist model would let a swarm declare per-agent ACLs:

```json
{
  "agents": [
    {"name": "PublicWeather", "allowed_users": "*"},
    {"name": "InternalCRMQuery", "allowed_users": ["sales-team@org"]}
  ]
}
```

The model could call `PublicWeather` for any caller; the LLM has to know not to even *propose* `InternalCRMQuery` for unauthorized users (or surface a clean "you don't have permission" if it tries).

This is real complexity. Pretty sure we don't need it on day one. A swarm is a coherent unit of trust — if you're on the swarm's allowlist, you can call any agent in it. If you need finer granularity, deploy two swarms.

**The rollout plan when we get to it:**

1. Make the swarm server's `/api/swarm/deploy` mint a token by default (Option A). Backwards-compatible: existing public swarms keep working without a token, but new deploys get one.
2. Brainstem stores the token alongside the URL in `deployedSwarms`. Every call includes it.
3. Add an `--auth-required` flag on the swarm server that rejects calls without a valid token. Off by default for now; on by default once tokens are universal.
4. Layer Option B (GitHub OAuth) for swarms that need team access. Deploy-time flag.

Auth is one of those things you ship just before you actually need it, never sooner. Right now the cost-benefit isn't there for most users. We'll know when it is.
