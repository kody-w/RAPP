# Offline-resilient send queue

A message is halfway out the door when the network disappears.

The user has already hit send. The sentence is in motion. Then Wi‑Fi drops, the browser goes offline, and the usual web-app bargain breaks: spinner, error toast, maybe lost text. This system is built around a different goal: when delivery cannot happen immediately, the user’s intent is still recorded locally and can be retried later.

That goal lives in two behaviors described by the source. First, `chatWithSwarmResilient` is intended to stay calm when delivery cannot happen right now. Second, the send queue is not an in-memory courtesy. It persists in IndexedDB, survives refreshes, and is meant to drain itself when the browser comes back online.

The shape of the system shows up in the surrounding code. State is already treated as local, durable, and namespaced per twin. Deletion is explicit and store-by-store:

```js
win(twin_id) {
  // Wipe all twin-namespaced records across stores
  for (const s of ['peers', 'documents', 'inbox', 'outbox', 'swarms',
                    'memory', 'conversations']) {
    const rows = await idbList(s);
    for (const r of rows) if (r.key.startsWith(twin_id + ':')) await idbDel(s, r.key);
  }
  await idbDel('twins', twin_id);
  // If active, pick another or create a fresh self
  const active = await idbGet('twins', ACTIVE_KEY);
  if (active && active.twin_id === twin_id) {
    const remaining = await listTwins();
    if (remaining.length) await setActiveTwin(remaining[0].twin_id);
    else { const t = await createSelfTwin('@unhatched'); await setActiveTwin(t.twin_id); }
  }
}
```

That list of stores matters: `'outbox'` is right there beside `'inbox'`, `'documents'`, and `'conversations'`. Outgoing work is treated as first-class local data.

The companion to that guarantee is `drainPendingQueue`. If enqueue is the write path, drain is the repair loop. When connectivity returns, the browser’s `online` event is described as a wake-up signal: check IndexedDB, pull pending items from `'outbox'`, and try delivery again. No manual retry button required. No assumption that the tab stayed open continuously. The queue is durable enough that “later” can mean after a refresh or after lunch.

That durability is useful, but it also has implications. If outbound messages persist locally, then sensitive content may remain on-device until it is delivered or deleted. The deletion snippet shows that cleanup is explicit and store-by-store, including `'outbox'`, but this chapter cannot say more than that about retention policy, encryption, or browser-specific storage behavior.

There is one gap in the source worth stating plainly. We are told the key invariant — calm send behavior, queue persisted in IDB, auto-drain on `online` — but we are not shown the implementation of `chatWithSwarmResilient` or `drainPendingQueue` themselves. So the chapter can name the contract with confidence, but not the exact retry policy, ordering rules, deduplication logic, item schema inside `'outbox'`, or how the system distinguishes queued, sent, and failed states.

The design principle is still clear. In a network-fragile environment, the important thing is not pretending the network is reliable. It is recording intent locally, keeping transient disconnection from turning into data loss, and retrying when the platform says it is online again.
