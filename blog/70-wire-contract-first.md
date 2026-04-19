# How we built the wire contract first, then the implementation

There's an order to building distributed systems. Most teams reverse it.

The reversed order: build the implementation first, then document what it does as the wire contract. Result: the contract is shaped by implementation accidents — quirks of the framework you used, oddities of how the team happened to think about the problem, side effects of last-minute fixes. Once the contract is published, you're stuck with it; the next implementation has to honor those accidents forever.

The right order: design the wire contract first. Implement it second. The implementation is judged against the spec, not the other way around.

**For RAPP swarms:**

The wire contract is six lines:

```
GET    /api/swarm/healthz                    list all swarms hosted here
POST   /api/swarm/deploy                     install a rapp-swarm/1.0 bundle
GET    /api/swarm/{guid}/healthz             info + agents for one swarm
POST   /api/swarm/{guid}/agent               run an agent (with optional user_guid)
GET    /api/swarm/{guid}/seal                sealing status
POST   /api/swarm/{guid}/seal                seal the swarm
```

That's the entire externally-visible contract. We designed those endpoints — their URLs, their bodies, their response shapes — before writing the implementation. The design doc was a markdown table that fit on one screen.

Then the implementation. Then more endpoints (snapshots) added the same way: design the wire shape first, ship the implementation second.

**Why this order matters:**

**Multiple implementations are possible from day one.** With a tight, intentional wire spec, anyone (us, a competitor, an integrator) can implement the contract. We've written the local stdlib version (`swarm/server.py`); a future Azure-Functions version would speak the same contract; a Cloudflare-Workers version could too. Each implementation can be optimized for its substrate without worrying about leaking implementation details into the spec.

**Spec discussions stay focused.** When you're discussing "should /api/swarm/{guid}/seal accept a body?" without an existing implementation to defend, you can think about what's RIGHT. After implementation exists, the same discussion becomes "well, the implementation already does X, can we change it?" — much harder to make changes.

**Tests are written against the spec, not the code.** The end-to-end test suite for sealing+snapshot is curl invocations against the wire contract. Any compliant implementation should pass the same tests. The tests aren't coupled to one implementation's internals.

**Backward compatibility is explicit.** When you ship `rapp-swarm/1.0` and later contemplate `rapp-swarm/1.1`, the version is in the schema string. Old clients reading new servers know to treat new fields as optional; old servers reading new clients can reject `1.1`-only bundles cleanly. The versioning discipline is in the spec.

**The two-step process:**

**Step 1: Design the wire contract.**

Write a one-page markdown spec listing every endpoint, request body, response body, and status code. Include error codes. Include success codes. Don't write implementation pseudocode; write what's on the wire.

For each endpoint, ask:
- What's the HTTP method? Is the verb appropriate?
- What's the URL path? Does it follow the resource-oriented pattern of your other endpoints?
- What goes in the body? What's required vs. optional?
- What does success look like? What does failure look like?
- What status codes are possible?

Do this for the whole contract before writing any implementation code. Expect to revise. The spec gets cleaner with each revision; you find seams that wouldn't have been visible if you were head-down in code.

**Step 2: Implement.**

Write code that honors the spec. When you discover the spec is unworkable in some way, update the spec FIRST, then update the code. The spec is the source of truth; the code chases.

This is why we wrote a 30-line shell script test suite (`tests/test-sealing-snapshot.sh`) BEFORE the sealing implementation. The tests encode the spec. The implementation either passes the tests or it doesn't. When tests fail, we ask: is the implementation wrong, or is the spec wrong? Either way, fix it. The tests catch drift.

**What goes wrong without this discipline:**

You ship a feature in code. The behavior is what your code does today. You document it in the README. Later, a customer integrates against your README; their code breaks because what your code actually does diverges from what the README says. You fix the README; some other customer breaks. You realize the README isn't authoritative; you have no actual spec. The contract emerges through customer complaints and gradual documentation.

This is how most APIs work. It's bad. The cost is invisible until you have a second implementation or a third-party integrator.

**For protocol design specifically:**

The wire contract design phase is when you ask:

- **Idempotency.** Can a request be retried safely? What happens if it's processed twice?
- **Pagination.** What if the response would be 10MB?
- **Errors as first-class.** What's the error envelope? Does it include enough information for the caller to act differently?
- **Backward compatibility.** What happens when a v1.0 client hits a v1.1 server? Vice versa?
- **Authentication.** Where does the credential go? In the URL? Bearer header? mTLS?
- **Capability discovery.** Can a client introspect what an endpoint supports?

These questions are easier to answer in spec form than in code form. Once code exists, the inertia is to keep the existing answer; in spec form, you can entertain alternatives without throwing away work.

**The lesson:**

For any system that other code is going to talk to — even just code you write tomorrow — design the wire contract first as a deliberate artifact. Markdown table with endpoints + request bodies + response bodies + status codes. Iterate the spec until it's clean. THEN write the implementation. THEN write the tests.

The order is: spec → tests → implementation. Not implementation → tests → spec, which is what most teams do.

For RAPP, this ordering let us ship sealing + snapshots with 23 of 23 tests passing on the first integration. The tests were written against the wire spec; the implementation was written to satisfy the tests. No "gotchas," no "wait, the spec doesn't actually match the code" moments. Spec, tests, code, in that order.

The discipline is uncomfortable for engineers used to coding first. It's also faster overall — by a lot — because you spend less time on rework when you've thought through the contract before committing to an implementation.
