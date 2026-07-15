"""LLM provider resolution (no network)."""
from __future__ import annotations

import os

from atlas_agent.llm_client import resolve_engine


def test_auto_prefers_zai_when_key_set(monkeypatch):
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("ZAI_API_KEY", "sk-test")
    assert resolve_engine("auto", prefer_cloud=True) == "zai"


def test_explicit_zai_without_key_falls_back(monkeypatch):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.delenv("Z_AI_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert resolve_engine("zai", prefer_cloud=True) == "local_rules"


def test_auto_local_first_when_prefer_cloud_false(monkeypatch):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-qwen")
    monkeypatch.setattr("atlas_agent.llm_client.is_ollama_available", lambda *a, **k: False)
    monkeypatch.setattr("atlas_agent.llm_client.is_gpt4all_available", lambda: False)
    assert resolve_engine("auto", prefer_cloud=False) == "qwen_cloud"
