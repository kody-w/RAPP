"""utils/llm.py — one LLM door for every rapplication singleton.

Collapsed singletons call `from utils.llm import call_llm`. Inside a running
brainstem that resolves HERE, and the call rides the host's own model and
credentials (the brainstem's call_copilot): no second key, no second config —
a rapplication speaks with the voice of the brainstem it hatched into.
"""


def call_llm(messages, tools=None):
    """messages: chat-completions message list → the model's text reply."""
    import sys

    host = sys.modules.get("__main__")
    call = getattr(host, "call_copilot", None)
    if call is None:
        raise RuntimeError(
            "no LLM host: utils.llm only works inside a running brainstem"
        )
    response, _model = call(messages, tools=tools)
    return (response["choices"][0]["message"].get("content") or "").strip()
