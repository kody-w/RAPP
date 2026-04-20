# Write a RAPP Agent

Write a new single-file RAPP agent. Ask the user what the agent should do, then create the file.

## Rules

Follow the v1 agent contract exactly. Read [AGENTS.md](../../AGENTS.md) and use [rapp_brainstem/agents/hacker_news_agent.py](../../rapp_brainstem/agents/hacker_news_agent.py) as the reference implementation.

## Checklist

1. Filename: `<thing>_agent.py` in `rapp_brainstem/agents/`
2. Import `BasicAgent` from `agents.basic_agent`
3. One class extending `BasicAgent`
4. `self.name` — the tool name the LLM sees (PascalCase, no spaces)
5. `self.metadata` — OpenAI function-calling schema with `name`, `description`, `parameters`
6. `perform(**kwargs) -> str` returning `json.dumps({"status": "success|error", ...})`
7. Optional: `data_slush` key in the return dict for chaining
8. Optional: `system_context() -> str` for injecting into every system prompt
9. Optional: `__manifest__` dict at module level for RAR registry

## Constraints

- **No sibling imports** — agents cannot import other agents
- **No build steps** — the file must work when dropped into `agents/`
- **No frameworks** — only `BasicAgent` as the base class
- **Missing pip deps** are auto-installed at import time — declare them as normal imports
- The agent must be portable across Tier 1 (local), Tier 2 (Azure), and Tier 3 (Copilot Studio)

## After creating

Run the brainstem tests to verify:
```bash
cd rapp_brainstem && python3 -m pytest test_local_agents.py -v
```
