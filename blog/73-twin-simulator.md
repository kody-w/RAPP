# RAPP Twin Simulator: the cloud, but on your laptop

We deployed two twins to Azure Functions yesterday. Each in its own resource group, each with its own URL, each isolated. It worked. It cost real money (well — pennies). It took 5 minutes per twin.

Then we asked: *what if you could just do this locally? Same isolation, same per-twin endpoints, same T2T protocol, no cloud?*

That's the **RAPP Twin Simulator**. It's `hippocampus/twin-sim.sh` — a 200-line shell script that gives you the full Twin Stack ecosystem on one machine.

**One twin per directory + port:**

```bash
$ bash hippocampus/twin-sim.sh start kody
✓ Twin 'kody' running on http://127.0.0.1:7142 (workspace: ~/.rapp-twins/kody)

$ bash hippocampus/twin-sim.sh start molly
✓ Twin 'molly' running on http://127.0.0.1:7094 (workspace: ~/.rapp-twins/molly)
```

The port is deterministic — `7090 + hash(name) % 100`. Same name always gets the same port across reboots. So `~/.rapp-twins/kody/` is *Kody's twin*, full stop. Same workspace, same identity, same hatched swarms across sessions.

**Workspaces look like cloud RGs but on your filesystem:**

```
~/.rapp-twins/kody/
  workspace.json           name, port, created_at, url
  swarms/<guid>/...        each hatched cloud
  t2t/identity.json        cloud_id + secret + handle
  t2t/peers.json           whitelisted peer twins
  t2t/conversations/...    HMAC-verified chat logs
  documents/               twin-owned documents
  inbox/                   docs received from peers (sender-prefixed)
  outbox/                  audit trail of sent docs
  server.log
  server.pid
```

That's the same shape that `BRAINSTEM_HOME` points to in the deployed Function App. Move a workspace dir to a cloud blob mount → instant graduation. The simulator and the cloud share their entire data layout.

**Mutual peering in one command:**

```bash
$ bash hippocampus/twin-sim.sh peer kody molly
✓ Mutual T2T peering: @kody.local ↔ @molly.local
  Now twins can chat, share docs, and invoke each other's swarms.
```

The script reads each twin's identity.json directly from disk and hits both `/api/t2t/peers` endpoints with the OOB-exchanged secrets. Out-of-band exchange is "I have file access to both directories" — the strongest possible OOB channel.

**What this unlocks:**

- **Test multi-twin scenarios** without cloud spend. Boot 5 twins, run a synthetic C-suite committee.
- **Develop the T2T protocol** without two devices. localhost ports stand in for cross-device endpoints — same wire format.
- **Demo to investors** offline. The hero demo runs on a plane.
- **Fork your own twin** — `start kody-experiment`, peer it to the original, snapshot before risky soul edits.
- **Prove the data layout** before committing to cloud storage. If a workspace dir works locally, it works in Azure Files.

**The pattern matters more than the script:**

The lesson is *the cloud topology is reproducible at the filesystem level*. A "cloud twin" is a directory with conventions. The conventions are public, the directory layout is filesystem-native, the protocol between twins is HMAC over HTTP. There's nothing magical about Azure Functions — Azure Functions just gives you a publicly-reachable port pointed at a directory. The simulator gives you the same port + directory locally.

When the question becomes *"do we deploy this to the cloud?"* the answer is no longer "first we figure out the cloud architecture." The answer is "we move the directory."
