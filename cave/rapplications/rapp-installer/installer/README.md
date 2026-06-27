# installer/ — the RAPP installer payload, across tiers

This is the deployment surface the rapp installer carries, ported into the
rapplication. It lets this self-contained brainstem do what the installer does
across all three tiers — **without** the one thing that reintroduces grail-commit
risk.

## Tier 1 — the brainstem (local)

**Standup is `../bootstrap.sh` / `../serve.py`** — repo-independent, no grail.
`start.sh` / `start.ps1` here run a brainstem the classic way (venv + deps).

> ⚠️ The public **`install.sh` / `install.ps1` / `install.cmd` / `install.command`**
> are intentionally **NOT bundled**. Those scripts do `rm -rf ~/.brainstem/src`
> and `git clone github.com/kody-w/rapp-installer ~/.brainstem/src` — i.e. they
> re-create the **grail** working tree, which is exactly the accidental-commit
> risk this rapplication removes. Use `bootstrap.sh` instead. If you ever need
> the public grail install, get it from the grail's own one-liner, knowingly.

## Tier 2 — Azure (Spinal Cord)

- `azuredeploy.json` — ARM template (Azure Functions + Azure OpenAI)
- `deploy.sh` / `deploy.ps1` — drive the deployment

## Tier 3 — M365 / Copilot Studio (Nervous System)

- `MSFTAIBASMultiAgentCopilot_*.zip` — the Power Platform solution to import

## Hippocampus path + onboarding

- `community_rapp/` — the parallel Tier-2 community installer scripts
- `skill.md` — the Moltbook-pattern onboarding skill
