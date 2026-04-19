# Multi-agent slush chains, formalized

When a RAPP agent finishes, it returns a JSON envelope:

```json
{
  "status": "success",
  "summary": "Top 5 stories on Hacker News:\n\n1. ...",
  "data_slush": {
    "count": 5,
    "top_url": "https://www.nature.com/..."
  }
}
```

Three keys matter to the brainstem:

- **`status`** — `success`, `error`, or `incomplete`. Drives the chat loop's retry / follow-up logic.
- **`summary`** — what the LLM sees as the human-facing result. Renders into the chat after the model wraps it.
- **`data_slush`** — structured data the next agent in the chain can consume.

The first two are obvious. The third is the convention this post is about.

`data_slush` is the *typed handoff* between agents in a multi-step workflow. It's not in the SPEC formally yet, but it's the convention every starter agent ships with. The pattern: when an agent has structured output the LLM might want to pass to a subsequent agent call, it emits it under `data_slush` instead of cluttering the summary.

Example chain:

1. User: *"Look at the top HN story and save its URL to my reading list."*
2. Model calls `HackerNews(count=1)`. Agent returns `summary: "1. **[NIST...](url)** ..."`, `data_slush: {top_url: "https://nature.com/..."}`.
3. Model sees the slush. Calls `SaveBookmark(url="https://nature.com/...")`. Notice — the URL came from the slush, not from the summary text the model would otherwise have to re-extract.

That re-extract step is where models go wrong. They fabricate URLs. They paraphrase. They get the URL almost-right. The slush is the model's "machine-readable scratchpad" for the next call, and the LLM is much better at copying a JSON value verbatim than at parsing prose for one.

**What we'd standardize in a SPEC:**

- `status` ∈ `{success, error, incomplete}`. Required.
- `summary` is markdown, human-facing. Required for `success`. Optional for `error` (use `message` instead).
- `message` for `error`/`incomplete`. Replaces `summary` when those statuses fire.
- `data_slush` is an arbitrary object. Optional. No required keys, but well-known keys agents SHOULD use when applicable: `url`, `urls`, `count`, `id`, `ids`, `next_action`, `cursor`, `error_type`.
- `requires_additional_action: true` — explicit signal that the chat loop should let the model run another tool call without surfacing the in-progress response yet.

**What the chat loop does today:**

Looks for `result.status === 'incomplete'` or `result.requires_additional_action === true` to decide whether to keep looping. Otherwise calls the LLM once more for the natural-language wrap-up and returns to the user.

**What it doesn't do yet:**

Pass the slush forward as structured input to the next agent call. Today the LLM has to decide to thread the slush value through. A future version could automatically inject the previous call's `data_slush` as a hidden context block: `<previous_tool_output_slush>{...}</previous_tool_output_slush>`. The model would no longer need to "remember" the slush across turns; it would always be visible in the next system prompt.

The slush is the difference between "model improvises a chain by re-extracting from prose" and "agents pass typed values to each other through the model." The latter is faster, more accurate, and more debuggable. The slush convention makes that explicit.

Worth shipping as a SPEC §X, with a tooling story (lints, examples, a `data_slush_keys` field in the manifest).
