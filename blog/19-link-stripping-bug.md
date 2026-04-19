# The bug where the LLM was rewriting our HN links into bold text

The HackerNews agent returns a markdown-formatted summary:

```
1. **[NIST scientists create 'any wavelength' lasers](https://www.nature.com/...)** — 197 points, by rbanffy · [83 comments](https://news.ycombinator.com/item?id=44567890)
```

Two clickable links per story: the title (to the article) and the comment count (to the HN thread). The agent does the work of formatting because it has the data, the model doesn't.

The brainstem rendered the model's response, which looked like:

```
1. **NIST scientists create 'any wavelength' lasers** — 197 points
2. **State of Kdenlive** — 343 pts
...
```

Bold titles. No links. Pure prose. The model had read the agent's beautifully-formatted markdown and rewritten it as plain text with the URLs stripped.

This happened on every HN call. I assumed for a while it was a model behavior I'd have to work around with stronger prompting. The fix turned out to be one sentence in the system prompt.

The default soul read:

> You are a helpful, concise RAPP brainstem assistant. Use the loaded tools when relevant. **After tool calls, summarize the result in plain English.**

That last sentence was the bug.

"Summarize" is a directive to compress and rephrase. "In plain English" is a directive to strip formatting. Combined, they tell the model: take the agent's output and turn it into prose. The model was doing exactly what we asked. The links and bullets and bold spans got summarized away because that's what the prompt said to do.

The fix:

> You are a helpful, concise RAPP brainstem assistant. Use the loaded tools when relevant. **When a tool returns markdown — links like [title](url), lists, code blocks — render that markdown verbatim in your reply. Preserve every clickable link exactly as the tool wrote it; do not strip URLs, do not rewrite titles into plain text, do not collapse formatted output into prose.**

Six negations. Specifically calling out the failure modes we'd seen — strip URLs, rewrite titles, collapse to prose. Models follow specific don'ts much better than abstract dos.

The next chat call rendered the HN list with all links intact. Same model, same agent, same data. Different system prompt.

Two lessons.

**One: every clause in your system prompt is an instruction the model will try to obey.** "Be helpful" is harmless. "Summarize" is a verb the model will execute on whatever input it sees, including tool output you didn't mean to summarize. There are no decorative sentences in a system prompt. Every sentence either steers behavior or competes with sentences that do.

**Two: when you see a class of behavior you don't like, look at your prompt before you look at the model.** It's tempting to blame "Claude/GPT/whatever doesn't follow instructions well." Often the model is following an instruction you didn't realize you were giving. The model doesn't know which sentences in your prompt you cared about; they're all gospel.

The fix shipped as a one-shot localStorage migration so existing users with the cached old soul got the new one without wiping their data. No user action required. The HN links came back.
