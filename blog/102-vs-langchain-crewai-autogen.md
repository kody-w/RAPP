# Why agent.py-all-the-way-down beats LangChain / CrewAI / AutoGen for shipping

We have built agents in LangChain. We have built crews in CrewAI. We have run conversational loops in AutoGen. Each of those frameworks is good at what it optimizes for, and we are not interested in pretending otherwise. This post is about a narrower claim: when the unit you actually need to deliver is *a workflow somebody else will install and run*, none of those frameworks beat shipping one Python file. The rest is about why.

## What each framework is actually good at

**LangChain** optimizes for composability of building blocks. Vector stores, document loaders, retrievers, output parsers, memory adapters — the value is the catalog and the glue. If your problem is "I have 14 weird data sources and I need to wire them into a retrieval pipeline," LangChain has already written most of the connectors. Reaching for LangChain there is the right call.

**CrewAI** optimizes for role-based multi-agent collaboration. It gives you hierarchies, delegation, declarative crew definitions where Researcher hands to Writer hands to Editor. If the mental model of your problem is "a team of specialists with explicit reporting lines," CrewAI fits the model.

**AutoGen** optimizes for conversational multi-agent loops with auto-correction. Two or more agents converse, critique each other, retry until convergence. For problems where the loop *is* the algorithm — code generation with self-review, math reasoning with verification — AutoGen's substrate is the right substrate.

Use the right tool for the job.

## What the three share that we deliberately do not have

There is a shape these frameworks share, and it is the shape we walked away from:

- A runtime layer between your code and the LLM call.
- A graph / DAG / state-machine abstraction you must learn to express your workflow.
- A package you `pip install` whose major versions break your code on upgrade.
- A versioned API surface that is bigger than your problem.

None of these are wrong. They are the cost of what the framework gives you. Our claim is narrow: for *shipping*, the cost is higher than people notice.

## The cost of those abstractions for shipping

To deploy a LangChain agent to a new environment, you ship the chain definition files, the LangChain version pin, the rest of the Python dependency manifest, and runtime config so the loaders and adapters resolve. To deploy a CrewAI crew, same shape. To deploy an AutoGen group, same shape.

In each case the artifact is *a directory of code, plus a dependency manifest, plus assumptions about the runtime hosting it*. None of those can be moved by email. None can be inspected by `cat`. None can be hot-loaded by dropping a file into a directory. The framework boundary travels with you everywhere.

If shipping is rare and the framework's catalog is the value, the cost is fine. If shipping is *the point*, the cost adds up.

## The agent.py-all-the-way-down alternative

A RAPP agent is one Python file. It declares a `__manifest__`, extends a six-line `BasicAgent`, defines `perform(**kwargs)`, returns a string. That is the entire contract. We covered the foundational version of this in [the single-file agent contract](./01-single-file-agent.md).

What is new is that this scales up. `agents/bookfactory_agent.py` is the deployable form of the BookFactory pipeline: writer, five editor specialists, two CEO specialists, publisher, reviewer — thirteen sacred files in their multi-file form, collapsed into one ship-time artifact. 542 lines. About 24KB. One `from agents.basic_agent import BasicAgent` and an LLM key in the environment, and it runs. No transitive deps, no version skew, no directory layout assumptions.

Drop it in `agents/`. The brainstem hot-loads it on the next request. That is the deploy.

## The size comparison, honestly

`bookfactory_agent.py`: 542 lines, ~24KB, one file, one import beyond stdlib (`BasicAgent`, itself six lines).

Equivalent functionality in the three frameworks would, approximately[^1], look like:

- **LangChain:** ~15–20 files (chain definitions, prompt templates, custom tool classes, output parsers) plus the langchain install. langchain pulls numpy, pydantic, tiktoken, tenacity, and a long tail; the transitive footprint is on the order of ~100MB+.
- **CrewAI:** a crew definition module plus per-agent role files, plus crewai. crewai depends on langchain underneath, so you pay roughly the same transitive cost.
- **AutoGen:** an agent group plus per-agent system prompts, plus pyautogen. Lighter than the langchain-rooted ones — order of tens of MB — but still a versioned package boundary.

[^1]: We did not run a fresh `pip install` of each into a clean venv to measure to the byte. Treat the sizes as order-of-magnitude. The qualitative point — *they bring a transitive dependency tree, the single file does not* — is the load-bearing part.

The dependency cost is not the headline. The headline is that the unit of distribution is different in kind. Theirs is *a project directory plus a manifest*. Ours is *a file*.

## When you SHOULD use the frameworks

If you need LangChain's connector catalog, use LangChain. Re-implementing 40 vector-store adapters because you wanted one file is silly. If your problem is genuinely a hierarchy of conversing roles, CrewAI's abstractions match. If your loop is a self-correcting two-agent dialogue, AutoGen will get you there faster than rolling your own.

These frameworks exist because their abstractions earned the right to exist. Real teams shipped real things on them.

## When you should use agent.py-all-the-way-down

Use it when:

- The unit of distribution is *a workflow people will install*, not a SaaS endpoint you will operate.
- Portability across runtimes matters. The same file has to run in a local Flask brainstem, a stdlib tether server, and the in-browser Pyodide brainstem.
- The next maintainer should be able to `cat` the file and read it — no IDE jump-to-definition required.
- You want users to fork the file instead of file feature requests against your framework.

This is the same argument we made about [the swarm server having no LLM](./29-swarm-server-no-llm.md) and about [the brainstem being one HTML file](./41-one-html-file.md). The unit you ship should be the smallest thing that can carry its own meaning. For agents, that unit is a Python file.

## How you actually get there: the double-jump loop

A fair objection: composite agents are hard to write directly as one file. The pipeline that produced the converged BookFactory has thirteen sources, not one. How does it become one file?

Authoring happens in the multi-file form. Each persona is its own sacred `agent.py`. The double-jump loop iterates against that form: run both writers, score head-to-head, encode each diagnosis as a soul-prompt edit or a new specialist file, re-run, re-score, stop when the curve flattens. We described this in [the double-jump post](./89-double-jump-loop.md).

When the loop converges, a build step collapses the thirteen sources into the singleton: SOULs inlined as constants, helper classes prefixed `_Internal` so the brainstem's discovery only sees the public `BookFactory`, one inlined `_llm_call` at the bottom. That singleton is the deliverable.

You can build a rapplication in any framework. But to *ship* a single-file rapplication, the design has to match the file. Multi-file frameworks fight the collapse step — their abstractions assume the directory is permanent. Ours assume the directory is scaffolding and the file is the product.

## The architectural insight

The rapplication is the deliverable. The loop is the process. The framework you used to author it is private.

The public contract should be a file, not a framework dependency. Whatever you do behind that contract — LangChain, CrewAI, AutoGen, raw httpx, hand-rolled subagents — is your business. What crosses the boundary to the user is one Python file they can read, fork, email, and drop into a directory.

That is the thing the other frameworks are not optimizing for, because they are optimizing for other things. It is the thing we are optimizing for, because shipping is what we are doing.
