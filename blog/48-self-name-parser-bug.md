# `"name": self.name` in Python is a JS parse failure

The brainstem renders agent cards in the browser. To do that, it parses each `*_agent.py` source file and extracts the metadata block:

```python
class SaveMemoryAgent(BasicAgent):
    def __init__(self):
        self.name = "SaveMemory"
        self.metadata = {
            "name": self.name,                  # ← here
            "description": "Saves information to persistent memory...",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_type": {"type": "string", "enum": ["fact", "preference", "insight", "task"]},
                    "content": {"type": "string"},
                    "importance": {"type": "integer", "minimum": 1, "maximum": 5},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["memory_type", "content"],
            },
        }
        super().__init__(name=self.name, metadata=self.metadata)
```

The brainstem's `pythonDictToJson()` is supposed to take that dict literal as a string and return parsed JSON. From there we read `description` (for the binder) and `parameters` (for the OpenAI tool schema).

For weeks, this was silently failing. The model would receive a tool spec like:

```json
{
  "type": "function",
  "function": {
    "name": "SaveMemory",
    "description": "",
    "parameters": {"type": "object", "properties": {}, "required": []}
  }
}
```

Empty description. Empty parameters. The function had a name; everything else fell through to defaults.

**The model's response to a schema-less tool:**

It didn't refuse. It guessed. The user asked the brainstem to remember something, the model decided to call SaveMemory, and it invented its own parameter shape based on the user's phrasing:

```json
{"facts": [{"fact": "User's name is Kody and they work on RAPP."}]}
```

`facts: [{fact: ...}]`. Not `content`. Not `memory_type`. Just whatever sounded plausible. SaveMemory rejected the call because `content` was missing. The model said "I'm having trouble saving that, sorry." The user thought the agent was broken.

The bug was in `pythonDictToJson`. Specifically: the parser didn't know what to do with `self.name` inside the dict literal:

```python
self.metadata = {
    "name": self.name,        # ← this line
    ...
}
```

`self.name` is a Python attribute reference. Inside a dict literal, Python evaluates it to whatever `self.name` is — at runtime, `"SaveMemory"`. JSON has no such concept. The parser tried to feed `{ "name": self.name, ... }` to `JSON.parse`, got `Unexpected token s`, threw, and returned `null`.

The caller fell back to default parameters: empty schema. Tool went to the model with nothing to constrain it. The model invented.

**The fix:**

Substitute `self.name` with the literal string before calling `JSON.parse`. The parser already extracts `r.name` (via regex on `self.name = '...'`) earlier in the parse pipeline, so that value is available. Pass it as `ctx.selfName`:

```js
function pythonDictToJson(src, ctx) {
  let s = src;

  // Resolve `self.name` references inside the dict (used in agent metadata
  // as `"name": self.name`) — the OG ran in Python where this just works;
  // we have to substitute the literal before JSON.parse.
  const selfName = ctx && ctx.selfName;
  if (selfName) {
    s = s.replace(/\bself\.name\b/g, JSON.stringify(selfName));
  }

  // Strip any other unresolved `self.<ident>` so the parser doesn't choke
  // on agent-specific runtime references that aren't part of the schema.
  s = s.replace(/\bself\.[A-Za-z_]\w*/g, 'null');

  // ... existing tokenization / Python-literal substitutions ...

  return JSON.parse(out);
}
```

Two regex passes: replace `self.name` with the literal, replace any other `self.X` with `null`. The first one fixes the actual case we care about; the second is defensive — if some agent has `self.foo` in its metadata, we degrade to `null` instead of crashing.

**Verified the fix:**

```
$ node -e "..." # parse save_memory_agent.py
parameters: {
  "type": "object",
  "properties": {
    "memory_type": {"type": "string", "enum": ["fact", "preference", "insight", "task"]},
    "content": {"type": "string"},
    "importance": {"type": "integer", "minimum": 1, "maximum": 5},
    "tags": {"type": "array", "items": {"type": "string"}}
  },
  "required": ["memory_type", "content"]
}
```

Full schema. The model now sees `content` is required and uses it. SaveMemory works on the first try.

**Two lessons:**

**One: silent parse failures are the worst kind of failure.** Our parser caught the `JSON.parse` exception and returned `null`. The caller treated `null` as "no schema available" and used defaults. The user-visible symptom was "the LLM invents parameter names" — which looks like an LLM problem, not a parser problem. Three layers of indirection between root cause and visible symptom. If the parser had thrown loudly, we'd have caught this in five minutes.

**Two: when porting code across runtimes, the runtime's affordances become your problem.** Python evaluates `self.name` at instantiation. JavaScript reading the source as text doesn't have that runtime; we had to simulate it. Every Python feature that "just works" in Python is a feature we have to either implement or refuse. The agent contract doesn't formally ban `self.<anything>` in metadata, but our parser only handles the most common case (`self.name`). A more complex case (`self.config['version']`) would still fail. We accept that limit.

The fix shipped as commit `9f676d9`. The parser is now slightly more robust, the model gets real schemas, and SaveMemory does what its docstring says.
