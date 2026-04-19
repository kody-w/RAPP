# Why the system prompt is XML-tagged

Our first system prompt was three sentences:

> You are a helpful, concise RAPP brainstem assistant. Use the loaded tools when relevant. After tool calls, summarize the result in plain English.

It worked, sort of. The problem became visible the day we asked for the top stories on Hacker News and the model returned bold titles with no clickable links — even though the agent was returning markdown like `[title](url)` in its summary. The third sentence ("summarize the result in plain English") was active instruction. The model was doing exactly what we asked: stripping the formatting, distilling the URLs out of existence.

We replaced the whole thing with the OG community RAPP `_prepare_messages()` structure, ported verbatim. The new prompt is XML-tagged sections inside one document:

```xml
<identity> ... </identity>
<shared_memory_output> ... </shared_memory_output>
<specific_memory_output> ... </specific_memory_output>
<context_instructions> ... </context_instructions>
<agent_usage> ... </agent_usage>
<personality> ... </personality>
<knowledge> ... </knowledge>
<tier_2_hippocampus>
  <install_command os="macos_linux">curl ...</install_command>
  <install_command os="windows">irm ...</install_command>
</tier_2_hippocampus>
<how_to_help> ... </how_to_help>
<response_format> ... </response_format>
<boundaries> ... </boundaries>
<loaded_tools>
  <tool name="HackerNews">Fetches the top N stories...</tool>
  ...
</loaded_tools>
```

Three things change when you switch markdown headings to XML tags.

**Sections stop bleeding.** With markdown, the model treats everything between `## Personality` and `## Knowledge` as one rolling thought. Personality bullets influence knowledge claims. With explicit `</personality>` and `<knowledge>` boundaries, Claude in particular is much more disciplined about treating each block as standalone.

**Repeatable values become extractable.** Inside `<install_command os="macos_linux">curl …</install_command>`, the model sees a self-contained chunk it shouldn't paraphrase. Before, the install one-liner was inside a markdown code block, and the model would sometimes "helpfully" rewrite it with explanatory comments inline. Now it copies it verbatim because it understands the tag is the boundary.

**Dynamic injection is obvious.** `<shared_memory_output>` is a slot. Every chat turn, we read `localStorage['rapp_memory_v1']`, format the entries, and drop them between the tags. The structure is the same whether the user has 0 memories or 50. The model treats it as data, not as instruction text it might mistake for advice.

The XML doesn't have to be valid XML — we don't parse it server-side, the model does. Anthropic's models particularly are trained to recognize XML structure as content boundaries. (Other model families do too, just less reliably.) The cost is a few extra characters per section. The benefit is that the model stops collapsing your carefully-separated concerns into one prose blob.

Three sentences was wrong because every clause was a directive. XML tags let you write directives where you mean them and data where you mean it.
