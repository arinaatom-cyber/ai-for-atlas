"""Совместимость: старый импорт → llm_client (Qwen по умолчанию)."""
from atlas_agent.llm_client import (  # noqa: F401
    analyze_report,
    ask_about_project,
    is_claude_available,
    is_qwen_available,
    is_llm_available,
)
