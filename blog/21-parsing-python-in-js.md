# Parsing Python dicts in JavaScript (badly, but well enough)

The brainstem reads agent files in the browser. Each `*_agent.py` declares two metadata blocks — `__manifest__` at module level and `self.metadata = {...}` inside `__init__`. We need to extract those blocks to mint cards, render the binder, and send tool schemas to the LLM. We can't import Python in JS. We have to parse it.

The parser is `pythonDictToJson(src)` in `brainstem/rapp.js`. About 60 lines. Here's what it survives.

**Single-quoted strings.** Python is happy with `'foo'`; JSON insists on `"foo"`. We tokenize and rewrite, handling escaped quotes inside the body. Happens character-by-character so we don't break strings that contain the wrong quote.

**Python literals.** `True`, `False`, `None` become `true`, `false`, `null` via three regex passes. The `\b` word boundaries matter — without them you start corrupting strings.

**Trailing commas.** Python allows `{ "a": 1, }`; JSON doesn't. Strip them before `JSON.parse`.

**Comments.** Python `# foo` line comments get skipped. JSON has no comments at all.

That's the easy stuff. The two hard cases that took real bug fixes:

**Implicit string concatenation.**

```python
"description": (
    "Saves information to persistent memory. "
    "Call this whenever the user asks you to remember something."
),
```

Python concatenates adjacent string literals automatically. JSON does not. Our HackerNews agent was returning summaries with `description` parsed as `null` because the parser saw `"foo" "bar"` and gave up. Fix: after tokenization, repeatedly collapse `"X"\s*"Y"` → `"XY"` until stable, then unwrap `("string")` parens.

**`self.name` references.**

```python
self.metadata = {
    "name": self.name,
    "description": "...",
}
```

Python evaluates `self.name` to whatever the instance's `name` is. JSON has no notion of variable references. Without handling this, `JSON.parse` throws `Unexpected token s` and the whole metadata block falls through to the empty default — meaning the LLM gets a tool with no schema and starts inventing parameter names like `{facts: [{fact: "..."}]}` instead of using `content`.

Fix: in `parseAgentSource`, extract `self.name` first via regex, then pass it as `ctx.selfName` to `pythonDictToJson`. The parser substitutes `self.name` → `"ExtractedName"` before tokenization. Any other unresolved `self.<ident>` becomes `null` so the parse doesn't crash.

The result is a parser that handles maybe 80% of real-world Python dict literals. It will choke on f-strings, list comprehensions, and any expression more complex than a literal lookup. That's fine. Agent metadata blocks aren't supposed to contain expressions. The parser fails closed: it returns `null`, and the caller falls back to module-level `__manifest__` (which the build script already serializes as plain JSON).

The lesson: when you have to parse another language's syntax, identify the 5–10 things real authors actually write, handle those, and let everything else fail gracefully. Don't try to write a Python parser. Write a "what real agent files contain" parser.
