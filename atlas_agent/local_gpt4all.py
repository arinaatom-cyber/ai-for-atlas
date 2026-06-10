from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
_model: Any = None
_model_name: str | None = None


def is_gpt4all_available() -> bool:
    try:
        import gpt4all  # noqa: F401

        return True
    except ImportError:
        return False


def get_model(filename: str):
    global _model, _model_name
    with _lock:
        if _model is not None and _model_name == filename:
            return _model
        from gpt4all import GPT4All

        _model = GPT4All(filename, allow_download=True, verbose=False)
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
