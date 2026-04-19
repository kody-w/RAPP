# Mobile PWA: IndexedDB as the filesystem

A user opens the mobile app on a train with no signal. The screen still snaps open. Their chat history is there. Their documents are there. A previously imported twin still responds, because its data and agents already live on the device. In `brainstem/mobile/rapp-mobile.js`, the design is stated plainly: local storage is primary on mobile, and network use is not required for ordinary reads and writes. On mobile, the filesystem is not a directory under `~/.rapp-twins/`. It is IndexedDB.

On the local simulator, state lives in a workspace on disk. On mobile, the PWA stores the same kinds of things in the browser’s database, using the same mental model: one workspace, many twins, predictable buckets for peer data, documents, messages, swarms, memory, settings, and conversations. The browser is standing in for the filesystem, not replacing the architecture.

You can see the mapping in the code:

```js
const DB_NAME = 'rapp-twin';
const DB_VERSION = 2;
// All stores are keyed by `<twin_id>:<inner_key>` so one DB holds many twins.
const STORES = ['twins', 'peers', 'documents', 'inbox', 'outbox',
                'swarms', 'memory', 'settings', 'conversations'];
```

That comment does most of the work. One database holds many twins. Each store is keyed by `<twin_id>:<inner_key>`.

```js
async function idbGet(s, k)   { const d = await db(); return new Promise((r,j)=>{const x=d.transaction(s).objectStore(s).get(k);x.onsuccess=()=>r(x.result);x.onerror=()=>j(x.error);}); }
async function idbPut(s, k, v){ const d = await db(); return new Promise((r,j)=>{const x=d.transaction(s,'readwrite').objectStore(s).put(v,k);x.onsuccess=()=>r(true);x.onerror=()=>j(x.error);}); }
async function idbDel(s, k)   { const d = await db(); return new Promise((r,j)=>{const x=d.transaction(s,'readwrite').objectStore(s).delete(k);x.onsuccess=()=>r(true);x.onerror=()=>j(x.error);}); }
async function idbList(s) {
  const d = await db();
  return new Promise((res, rej) => {
    const out = [];
    const c = d.transaction(s).objectStore(s).openCursor();
    c.onsuccess = (e) => { const cur = e.target.result; if (cur) { out.push({ key: cur.key, value: cur.value }); cur.continue(); } else res(out); };
    c.onerror = () => rej(c.error);
  });
}
```

The other key idea is the multi-twin model. A phone can hold more than one twin, but not all twins are equal. The code distinguishes between `SELF` and `IMPORTED` twins. A `SELF` twin includes full identity and the secret needed to sign T2T messages. An `IMPORTED` twin carries personality and agents, but no secret. It is read-only in the cryptographic sense: you can talk to it offline, but you cannot speak as it.

That split matters because it keeps custody local. If a user imports a public bundle, they get behavior without the signing secret. If they create a self twin, the signing secret stays on-device.

The crypto helpers show the boundary. Signing requires the local secret; imported twins, by definition, do not have one.

```js
async function sign(payload, secretHex) {
  const sig = await crypto.subtle.sign('HMAC', await _hmacKey(secretHex), new TextEncoder().encode(payload));
  return bytesToHex(new Uint8Array(sig));
}
```

The rest of the design follows local-first rules. Local actions are handled against on-device state. Imported twins continue to function from previously stored data. Data lives in IndexedDB and can be exported as JSON under user control. That is not a cache pattern. On mobile, IndexedDB is the working store.

There are limits to what this source shows. It names the stores and the keying scheme, and it states that the mobile runtime mirrors `swarm/server.py + swarm/t2t.py + swarm/workspace.py + swarm/llm.py + swarm/chat.py`. But it does not show the exact on-disk layout under `~/.rapp-twins/`, so we cannot prove store-for-directory equivalence line by line. The evidence supports a narrower claim: mobile and local sim share the same workspace model, and mobile implements that model with IndexedDB.
