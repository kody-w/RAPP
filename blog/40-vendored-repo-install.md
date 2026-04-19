# Vendored-repo install pattern: `~/.brainstem-swarm/_repo/`

The tether and swarm install one-liners do the same surprising thing: they `git clone` the entire RAPP repo into a hidden directory, then run a script out of that clone. Not pip install. Not single-file download. Whole-repo clone.

```bash
# install-tether.sh
TETHER_HOME="$HOME/.brainstem-tether"
git clone --quiet --depth 1 https://github.com/kody-w/RAPP.git "$TETHER_HOME"

# install-swarm.sh
SWARM_HOME="$HOME/.rapp-swarm"
SRC="$SWARM_HOME/_repo"
git clone --quiet --depth 1 https://github.com/kody-w/RAPP.git "$SRC"
```

The CLI wrapper (`brainstem-tether`, `brainstem-swarm`) just executes the right Python file out of that clone:

```bash
exec "$python_cmd" "$TETHER_HOME/tether/server.py" --agents "$TETHER_HOME/agents" "$@"
```

**Why clone the whole repo and not just the script?**

Three reasons, in increasing importance:

**1. Dependencies travel together.** The tether server expects an `agents/` directory full of `*_agent.py` files. The swarm server expects a `_basic_agent_shim.py` it can vendor. The repo has all of these in one place. Cloning gets you the script PLUS its expected layout, in one operation. If you single-file downloaded `tether/server.py`, you'd then have to download `agents/save_memory_agent.py`, `agents/recall_memory_agent.py`, `agents/hacker_news_agent.py`, `agents/basic_agent.py` separately.

**2. Updates are a `git pull`.** The CLI wrapper checks for updates by running `git pull` against the cloned dir. There's no version metadata to manage, no upgrade endpoint to call, no package registry to publish to. You release new versions by pushing to `main`. Users get them on their next `brainstem-tether` invocation.

**3. Hackable.** The user can `cd ~/.brainstem-tether && git diff` to see what they're running. They can edit a file. They can `git checkout` an older commit. They can fork their local copy and customize. The clone is THEIR copy, not a frozen-in-time download.

**Why a hidden directory?**

`~/.brainstem-tether/`, `~/.rapp-swarm/` — both start with a dot. Standard Unix convention for "this is config / state, not user content." They don't show up in default `ls`, they don't clutter the home directory. They're discoverable for users who want to find them, invisible for users who don't.

**Why `_repo/` inside `~/.rapp-swarm/`?**

The swarm server has both source code AND deployed swarm data. The data is at `~/.rapp-swarm/swarms/<guid>/`. The source is at `~/.rapp-swarm/_repo/`. Putting them in the same parent dir keeps everything related to the swarm server in one place; the leading underscore on `_repo` signals "this is the runtime, not your data." If a user is poking around their data, they can ignore `_repo/` cleanly.

(The tether server is simpler — just one piece, no separate data — so it skips the `_repo` indirection and clones straight into `~/.brainstem-tether/`.)

**The CLI wrapper holds it all together:**

```bash
#!/bin/bash
# /usr/local/bin/brainstem-tether
exec "$python_cmd" "$TETHER_HOME/tether/server.py" \
    --agents "$TETHER_HOME/agents" \
    "$@"
```

The wrapper is the *only* thing on PATH. Everything it points at lives in the clone. If the user uninstalls (`rm ~/.local/bin/brainstem-tether && rm -rf ~/.brainstem-tether`), nothing else is left behind. Clean install, clean uninstall.

**What we don't do:**

- **PyPI package.** Would require version management, a release process, separate test surface. The clone-and-run model is simpler for a project this small.
- **Single-file download.** Would lose the agents/ directory and the upgrade story.
- **Shell function in `.bashrc`.** Would tie installation to the user's shell config; hard to uninstall cleanly.

**The pattern generalizes:**

When you ship a CLI tool with multiple files and you don't want to be a package maintainer, vendor the whole repo into a hidden dir, drop a wrapper script on PATH that points at the right entry point. Updates are `git pull`. Uninstall is `rm`. The user has a complete, hackable copy of your project at all times.

This pattern is approximately what `nvm`, `pyenv`, `rbenv`, and a dozen other "manage versions of $thing" tools do internally. They clone the underlying tool's repo, manage a wrapper that picks the right one, and let the user override anything by editing files in the clone.

It's not glamorous. It's not what package managers want you to do. It's right for a project that's one user's `git push` away from a release.
