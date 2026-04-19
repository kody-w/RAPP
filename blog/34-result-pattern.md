# The `Result[T, E]` pattern in the OG brainstem

Most Python codebases use exceptions for failure. The community RAPP brainstem uses both: exceptions for genuinely-exceptional things (network down, file missing), and a typed `Result[T, E]` for *expected* failure modes that the caller is supposed to handle.

```python
from utils.result import Result, Success, Failure, AgentLoadError

def _load_single_agent_local(file: str) -> Result[BasicAgent, AgentLoadError]:
    """Load a single agent from local agents/ folder. Returns Result."""
    module_name = file[:-3]
    try:
        module = importlib.import_module(f'agents.{module_name}')
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and issubclass(obj, BasicAgent) and obj is not BasicAgent:
                return Success(obj())
        return Failure(AgentLoadError(file, 'local', 'no_class', 'No BasicAgent subclass found'))
    except SyntaxError as e:
        return Failure(AgentLoadError(file, 'local', 'syntax', str(e)))
    except ImportError as e:
        return Failure(AgentLoadError(file, 'local', 'import', str(e)))
    except Exception as e:
        return Failure(AgentLoadError(file, 'local', 'instantiation', str(e)))
```

The function never raises. It catches every category of "this file might fail to load," wraps it as a `Failure(AgentLoadError(...))`, and returns. The caller does:

```python
for file in agent_files:
    result = _load_single_agent_local(file)
    if result.is_success:
        declared_agents[result.value.name] = result.value
    else:
        all_errors.append(result.error)

# Later:
if all_errors:
    logging.warning(f"Agent loading completed with {len(all_errors)} error(s):")
    for error in all_errors:
        logging.error(f"  - {error}")
```

Every error gets a structured record: which file, which source (local or Azure), which failure mode (`syntax`, `import`, `no_class`, `instantiation`), and the underlying message. The loader keeps going. Some agents fail; the rest still load. The errors get aggregated, logged once, and the assistant starts up with whatever loaded successfully.

**Compare with the exceptions-everywhere alternative:**

```python
for file in agent_files:
    try:
        agent = load(file)
        declared_agents[agent.name] = agent
    except Exception as e:
        logging.error(f"Failed to load {file}: {e}")
```

The exception version works. It's two-thirds as much code. It's also two-thirds as useful:

- **Lost categorization.** "Failed" is too coarse. The OG distinguishes `syntax`, `import`, `no_class`, `instantiation`. A user looking at the log sees specifically *what kind* of breakage their file has.
- **Lost source dimension.** Local agents and Azure-stored agents fail in different shapes; the `source: 'local' | 'azure'` field differentiates them in logs.
- **Implicit aggregation logic.** With exceptions you log per-error inline. With Result you collect first, log structured second — easier to count, easier to summarize, easier to surface to the user as "loaded 23 agents, 2 failed: X, Y."

**When Result earns its weight:**

- Many possible failure modes per call.
- Caller wants to make routing decisions based on which mode fired.
- You need to *aggregate* failures across many calls before reporting.
- The result is "expected enough" that an exception's stack trace is overkill.

**When you don't need it:**

- One call, one outcome, fail-fast is fine.
- The caller just propagates the error upward.
- The error category is genuinely "unknown / programmer error" — that's what exceptions are for.

The brainstem uses `Result` for: agent loading (many files, several failure modes, aggregate report at startup), OpenAI API calls (rate-limit / auth / timeout / bad-request / server — caller routes differently per category), and a couple of storage operations. Everything else uses normal Python exceptions.

**Why we don't use it everywhere:**

Python doesn't have algebraic data types or pattern matching (well, `match` exists since 3.10, but it's not as ergonomic as Rust's). Every `Result` use site is `if result.is_success` plus an `else`. That's three lines for what could be a single try-block. For functions that return one thing on success and raise on failure, you save lines and clarity by sticking with exceptions.

The `Result` pattern is a tool for the specific shape of "I have a function with several enumerable failure modes that the caller is supposed to handle structurally." When you have that shape, it's worth importing the `Result` type. When you don't, exceptions are correct.

Pick the failure-handling style that matches the failure shape. Don't pick one and force every situation through it.
