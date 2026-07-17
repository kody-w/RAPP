"""Launch the target-owned pre-acceptance RAPP/1 facade fail-closed."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import NoReturn, Sequence

if __package__:
    from .rapp1_facade import (
        Inference,
        RuntimeConfig,
        create_app,
        runtime_config,
    )
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from rapp1_facade import (
        Inference,
        RuntimeConfig,
        create_app,
        runtime_config,
    )


def fail_closed_inference(
    _messages: Sequence[dict[str, str]],
) -> NoReturn:
    """Refuse until a reviewed side-effect-free adapter is injected."""
    raise RuntimeError("no safe inference adapter is configured")


def create_production_app(
    *,
    inference: Inference | None = None,
    config: RuntimeConfig | None = None,
):
    selected_config = runtime_config() if config is None else config
    selected_inference = (
        fail_closed_inference if inference is None else inference
    )
    return create_app(
        inference=selected_inference,
        database_path=selected_config.database_path,
    )


def main(*, inference: Inference | None = None) -> None:
    config = runtime_config()
    app = create_production_app(
        inference=inference,
        config=config,
    )
    app.run(
        host=config.host,
        port=config.port,
        threaded=True,
        use_reloader=False,
    )


if __name__ == "__main__":
    main()
