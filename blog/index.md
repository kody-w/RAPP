# RAPP blog

Field notes from building the RAPP brainstem, swarm server, tether, registry, and the bits between.

## Architecture & Pattern

01. [The single-file agent contract](./01-single-file-agent.md)
02. [Browser AI + local hardware via tether](./02-tether.md)
03. [Same surface, two execution modes](./03-execution-modes.md)
04. [Why the system prompt is XML-tagged](./04-xml-system-prompt.md)
05. [NEVER fabricate success: the agent_usage rules](./05-agent-usage-rules.md)
06. [`example_call` in the manifest](./06-example-call-manifest.md)
07. [How we ported the local brainstem to the browser without rewriting anything](./07-port-without-rewrite.md)

## Cards & Identity

08. [Card-minting from agent.py: 64-bit seeds, 7-word incantations](./08-card-minting.md)

## Auth & Networking

09. [Cloudflare Workers as the CORS bandage](./09-cors-worker.md)
10. [GitHub Copilot device-code flow without a backend](./10-device-code-no-backend.md)

## UX

11. [Pills vs cards: defaulting to boring](./11-pills-vs-cards.md)
12. [The poker hand: why cards tuck behind the chat](./12-poker-hand-ux.md)
13. [Five header buttons is too many](./13-five-buttons-too-many.md)
14. [Mobile responsive without React](./14-mobile-without-react.md)

## Registry & Distribution

15. [`rapp-registry/1.0`: a JSON file is a marketplace](./15-rapp-registry-spec.md)
16. [138 agents, one click each](./16-138-agents.md)
17. [Curate your own agent source: fork the registry](./17-fork-the-registry.md)
18. [The Tier ladder explained](./18-tier-ladder.md)

## Postmortems

19. [The bug where the LLM was rewriting our HN links into bold text](./19-link-stripping-bug.md)
20. [Why we don't ship a soul.md editor anymore](./20-no-soul-editor.md)
21. [Parsing Python dicts in JavaScript (badly, but well enough)](./21-parsing-python-in-js.md)
22. [The agent-log chip](./22-agent-log-chip.md)

## Cross-device & Composition (forward-looking)

23. [Beyond same-machine tether: a Cloudflare relay for cross-device](./23-cloudflare-relay-design.md)
24. [Multi-agent slush chains, formalized](./24-data-slush-spec.md)
25. [What an `agent_pack.json` looks like](./25-agent-packs.md)

## Swarm Architecture

26. [GUID routing on one endpoint: many tenants, no Kubernetes](./26-guid-routing.md)
27. [Deliberately invalid GUIDs as a feature](./27-sentinel-guid.md)
28. [`BRAINSTEM_MEMORY_PATH`: per-call routing without changing the agent contract](./28-brainstem-memory-path.md)
29. [Why the swarm server doesn't make LLM calls](./29-swarm-server-no-llm.md)
30. [`rapp-swarm/1.0`: a portable swarm bundle](./30-rapp-swarm-bundle.md)
31. [From hippocampus to swarm: a rename that wasn't cosmetic](./31-hippocampus-to-swarm-rename.md)
32. [Same wire contract, three implementations](./32-same-wire-three-impls.md)

## Patterns from the OG brainstem

33. [`__manifest__` vs `self.metadata`: two metadata blocks per agent and why](./33-manifest-vs-metadata.md)
34. [The `Result[T, E]` pattern in the OG brainstem](./34-result-pattern.md)
35. [The 5-min TTL agent cache](./35-agent-cache-ttl.md)
36. [Vendored shims: making installed agents work without their parent](./36-vendored-shims.md)
37. [Per-call module loading via `sys.modules` namespacing](./37-sys-modules-namespacing.md)
38. [The agent dispatch order: tether → live → stub](./38-dispatch-order.md)

## Build & Stack

39. [`http.server` is enough](./39-http-server-is-enough.md)
40. [Vendored-repo install pattern](./40-vendored-repo-install.md)
41. [One HTML file, no build step, 4500 lines](./41-one-html-file.md)
42. [Lazy Pyodide: 10MB only when you need it](./42-lazy-pyodide.md)
43. [`<details>` for collapsible UI without a framework](./43-details-without-framework.md)

## More postmortems

44. [The model selector that forgot what you picked](./44-model-selector-race.md)
45. [Why `state.settings.soul = SOUL` runs on every load](./45-soul-migration.md)
46. [Specificity is a real bug class](./46-css-specificity-bug.md)
47. [The hand was a UX restriction we didn't realize we'd built](./47-hand-was-restriction.md)
48. [`"name": self.name` in Python is a JS parse failure](./48-self-name-parser-bug.md)

## Forward-looking specs

49. [The relay design: a Cloudflare Worker that knows which laptop is online](./49-relay-design.md)
50. [Authenticated swarms: who can call which `swarm_guid`?](./50-authenticated-swarms.md)
51. [Per-swarm soul](./51-per-swarm-soul.md)
52. [Swarms calling swarms](./52-swarms-calling-swarms.md)
