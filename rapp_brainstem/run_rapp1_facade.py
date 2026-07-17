"""Launch the target-owned pre-acceptance RAPP/1 facade."""

from __future__ import annotations

import hashlib
import sys
import threading
from pathlib import Path
from typing import Any, Sequence

if __package__:
    from .rapp1_facade import create_app, runtime_config
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from rapp1_facade import create_app, runtime_config


_PINNED_GRAIL_SHA256 = (
    "a293dd9f11eef915bf15776f08c736faa60cb749820871b6753ea98233142a71"
)
_grail_call = None
_grail_lock = threading.Lock()


def _private_grail_inference(
    messages: Sequence[dict[str, str]],
) -> Any:
    """Call only the pinned grail's side-effect-free, tool-less inference."""
    global _grail_call
    if _grail_call is None:
        with _grail_lock:
            if _grail_call is None:
                grail_path = Path(__file__).with_name("brainstem.py")
                digest = hashlib.sha256(grail_path.read_bytes()).hexdigest()
                if digest != _PINNED_GRAIL_SHA256:
                    raise RuntimeError("immutable grail hash mismatch")

                # Retain only the inference callable. The grail Flask app is never
                # mounted on or served by this facade.
                if __package__:
                    from .brainstem import call_copilot
                else:
                    from brainstem import call_copilot

                _grail_call = call_copilot

    result = _grail_call(messages, tools=None)
    if type(result) is not tuple or len(result) != 2:
        raise RuntimeError("pinned grail returned an invalid result")
    completion, model = result
    if type(completion) is not dict or type(model) is not str or not model:
        raise RuntimeError("pinned grail returned an invalid result")
    return completion


def main() -> None:
    config = runtime_config()
    app = create_app(
        inference=_private_grail_inference,
        database_path=config.database_path,
    )
    app.run(
        host=config.host,
        port=config.port,
        threaded=True,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
