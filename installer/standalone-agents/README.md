# Standalone agents

Single-file agents operators can drop into their brainstem's `agents/` directory. These are *operator-side* tools — they run from YOUR brainstem and act on YOUR behalf — distinct from neighborhood-shared agents that ship with a neighborhood seed.

## How to install one

```bash
# From your brainstem root:
curl -fsSL https://kody-w.github.io/RAPP/installer/standalone-agents/<name>.py \
  > agents/<name>.py

# Restart your brainstem (or wait for hot-discovery on the next request).
```

## Catalog

| Agent | Purpose |
|---|---|
| [`plant_discord_neighborhood_agent.py`](./plant_discord_neighborhood_agent.py) | One-shot: given a Discord webhook URL + a name, plants a real GitHub repo from a template, writes the Discord block into `neighborhood.json`, posts a welcome to the channel. Pure stdlib. Requires `GITHUB_TOKEN` with `repo` scope. |

## How `plant_discord_neighborhood_agent` works

```
operator chats their brainstem
        │
        │ "@brainstem plant a neighborhood for our Design Team 2026
        │  Discord channel — webhook https://discord.com/api/webhooks/..."
        ▼
plant_discord_neighborhood_agent.perform(
   neighborhood_name="design-team-2026",
   display_name="Design Team 2026",
   discord_webhook_url="https://discord.com/api/webhooks/...",
   kind="braintrust",        # default — federated research
)
        │
        ▼
1. Validate inputs + mint a fresh neighborhood_rappid
2. Fetch template files from kody-w/braintrust-template (raw.githubusercontent.com)
3. Customize neighborhood.json with new rappid + Discord block
4. POST /user/repos → create kody-w/design-team-2026 (private)
5. PUT /repos/.../contents/<path> for each file (10–15 calls)
6. POST to the Discord webhook with the welcome message
7. Return URLs + next_steps[]
        │
        ▼
operator sees:
  ✓ planted https://github.com/kody-w/design-team-2026
  ✓ Discord channel got a welcome message with `brainstem join` command
  → other team members run that command in their own brainstem,
    they're now subscribed; chat happens in Discord; canonical state
    lives in GitHub.
```

## Why this is one file

The platform's master plan: every plug-in unit is a single `*_agent.py` file. No build steps, no frameworks, no SDKs. This agent is no exception — drop it, run it, planting works.

## Why pure stdlib

So that `curl https://… > agents/x.py` is the entire installation. No `pip install`. No virtualenv. The brainstem already has Python; the agent uses what's there.

## Variants

To plant a different pattern, set `kind`:

- `"braintrust"` (default) — federated research with bibliography
- `"workspace"` (Bill's solo-then-shared) — private workspace template
- `"neighborhood"` — public neighborhood (defaults to public-art-collective template)

Override the template explicitly with `template="<repo-name>"` if you want a different starting point.

## Discord webhook prep

Before invoking the agent:

1. In Discord, open the channel → Edit Channel → Integrations → Webhooks → **New Webhook**
2. Copy the URL (looks like `https://discord.com/api/webhooks/<id>/<token>`)
3. Optionally enable Discord Developer Mode + copy the Server ID and Channel ID for the bridge metadata

The webhook URL is the only required field beyond the neighborhood name. Everything else has sensible defaults.

## What the agent does NOT do

- Add Discord users as GitHub collaborators automatically (you do that manually with `gh api -X PUT /repos/.../collaborators/<login>`; Discord identities don't map 1:1 to GitHub identities)
- Configure Discord-side bots or slash commands (that's the inverse direction; would be a `discord_organ.py`)
- Sync chat history (Discord chat stays in Discord; canonical decisions go to GitHub)

These are intentional — the agent's job is the planting moment. Ongoing bridge logic happens in the `discord_bridge_agent.py` shipped with each neighborhood seed.
