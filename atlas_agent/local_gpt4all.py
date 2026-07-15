from __future__ import annotations

import concurrent.futures
import os
import threading
from pathlib import Path
from typing import Any

_lock = threading.Lock()
_model: Any = None
_model_name: str | None = None
_LOAD_TIMEOUT_S = 90


def is_gpt4all_available() -> bool:
    if os.environ.get("ATLAS_SKIP_GPT4ALL", "").strip() in ("1", "true", "yes"):
        return False
    try:
        import gpt4all  # noqa: F401
    except ImportError:
        return False
    return model_is_cached(DEFAULT_GPT4ALL_MODEL)


DEFAULT_GPT4ALL_MODEL = "qwen2-1_5b-instruct-q4_0.gguf"


def model_is_cached(filename: str) -> bool:
    """GPT4All без локального файла может зависнуть на download — не использовать в scan."""
    name = Path(filename).name
    roots = []
    local = os.environ.get("LOCALAPPDATA", "")
    if local:
        roots.append(Path(local) / "nomic.ai" / "GPT4All")
    home = Path.home()
    roots.extend(
        [
            home / ".cache" / "gpt4all",
            home / "AppData" / "Local" / "nomic.ai" / "GPT4All",
        ]
    )
    for root in roots:
        if (root / name).is_file():
            return True
    return False


def _load_model(filename: str) -> Any:
    from gpt4all import GPT4All

    return GPT4All(filename, allow_download=True, verbose=False)


def get_model(filename: str):
    global _model, _model_name
    with _lock:
        if _model is not None and _model_name == filename:
            return _model
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_load_model, filename)
            try:
                _model = fut.result(timeout=_LOAD_TIMEOUT_S)
            except concurrent.futures.TimeoutError as exc:
                raise TimeoutError(
                    f"GPT4All model load exceeded {_LOAD_TIMEOUT_S}s"
                ) from exc
        _model_name = filename
        return _model


def generate(
    prompt: str,
    *,
    model_file: str = "qwen2-1_5b-instruct-q4_0.gguf",
    max_tokens: int = 1024,
    system: str = "",
) -> str:
    m = get_model(model_file)
    with m.chat_session(system_prompt=system or "You are a helpful assistant."):
        return m.generate(prompt, max_tokens=max_tokens, temp=0.2)
