from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import requests

PROMPTS_DIR = Path(__file__).parent / "prompts"

DEFAULT_OLLAMA_BASE = "http://127.0.0.1:11434/v1"
DEFAULT_OLLAMA_MODEL = "qwen2.5:3b"
DEFAULT_GPT4ALL_MODEL = "qwen2-1_5b-instruct-q4_0.gguf"
DEFAULT_ZAI_BASE = "https://api.z.ai/api/paas/v4"
DEFAULT_ZAI_MODEL = "glm-4-flash"
DEFAULT_QWEN_MODEL = "qwen-plus"
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"

# При prefer_cloud=True (по умолчанию): облако с ключом → Ollama → GPT4All → regex.
AUTO_CLOUD_ORDER = ("zai", "qwen", "claude")
AUTO_LOCAL_ORDER = ("ollama", "gpt4all")


def _load_system_prompt() -> str:
    return (PROMPTS_DIR / "system.txt").read_text(encoding="utf-8")


def is_ollama_available(base_url: str | None = None) -> bool:
    base = (base_url or os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE).rstrip("/")
    root = base.replace("/v1", "")
    try:
        r = requests.get(f"{root}/api/tags", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False


def is_gpt4all_available() -> bool:
    try:
        from atlas_agent.local_gpt4all import is_gpt4all_available as _g

        return _g()
    except ImportError:
        return False


def zai_api_key() -> str:
    return (
        os.environ.get("ZAI_API_KEY", "").strip()
        or os.environ.get("Z_AI_API_KEY", "").strip()
    )


def is_zai_available() -> bool:
    return bool(zai_api_key())


def is_qwen_cloud_available() -> bool:
    return bool(
        os.environ.get("DASHSCOPE_API_KEY", "").strip()
        or os.environ.get("QWEN_API_KEY", "").strip()
    )


def is_claude_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def _engine_available(engine: str, base_url: str | None = None) -> bool:
    if engine == "zai":
        return is_zai_available()
    if engine == "qwen":
        return is_qwen_cloud_available()
    if engine == "claude":
        return is_claude_available()
    if engine == "ollama":
        return is_ollama_available(base_url)
    if engine == "gpt4all":
        return is_gpt4all_available()
    return False


def is_llm_available(provider: str, *, prefer_cloud: bool = True) -> bool:
    p = (provider or "auto").lower()
    if p == "auto":
        if prefer_cloud and any(_engine_available(e) for e in AUTO_CLOUD_ORDER):
            return True
        return any(_engine_available(e, None) for e in AUTO_LOCAL_ORDER) or any(
            _engine_available(e) for e in AUTO_CLOUD_ORDER
        )
    if p == "zai":
        return is_zai_available()
    if p == "ollama":
        return is_ollama_available()
    if p == "gpt4all":
        return is_gpt4all_available()
    if p == "qwen":
        return is_qwen_cloud_available()
    if p == "claude":
        return is_claude_available()
    return False


def resolve_engine(
    provider: str,
    base_url: str | None = None,
    *,
    prefer_cloud: bool = True,
) -> str:
    """Какой движок реально будет использован."""
    p = (provider or "auto").lower()
    if p != "auto":
        if p == "zai" and is_zai_available():
            return "zai"
        if p == "ollama" and is_ollama_available(base_url):
            return "ollama"
        if p == "gpt4all" and is_gpt4all_available():
            return "gpt4all"
        if p == "qwen" and is_qwen_cloud_available():
            return "qwen_cloud"
        if p == "claude" and is_claude_available():
            return "claude"
        return "local_rules"

    order: list[str] = []
    if prefer_cloud:
        order.extend(AUTO_CLOUD_ORDER)
    order.extend(AUTO_LOCAL_ORDER)
    if not prefer_cloud:
        order.extend(AUTO_CLOUD_ORDER)
    for engine in order:
        if _engine_available(engine, base_url):
            return "zai" if engine == "zai" else ("qwen_cloud" if engine == "qwen" else engine)
    return "local_rules"


def list_llm_engines(*, prefer_cloud: bool = True) -> list[dict[str, Any]]:
    """Статус всех провайдеров (для `run_discovery.py llm`)."""
    rows = [
        ("zai", "Z.AI (GLM)", is_zai_available(), DEFAULT_ZAI_MODEL, "ZAI_API_KEY"),
        ("qwen_cloud", "Qwen (DashScope)", is_qwen_cloud_available(), DEFAULT_QWEN_MODEL, "DASHSCOPE_API_KEY"),
        ("claude", "Claude", is_claude_available(), DEFAULT_CLAUDE_MODEL, "ANTHROPIC_API_KEY"),
        ("ollama", "Ollama (local)", is_ollama_available(), DEFAULT_OLLAMA_MODEL, "—"),
        ("gpt4all", "GPT4All (local)", is_gpt4all_available(), DEFAULT_GPT4ALL_MODEL, "—"),
    ]
    active = resolve_engine("auto", prefer_cloud=prefer_cloud)
    out: list[dict[str, Any]] = []
    for eng, label, ok, model, key in rows:
        out.append({
            "engine": eng,
            "label": label,
            "available": ok,
            "default_model": model,
            "key_env": key,
            "active": eng == active,
        })
    return out


def _parse_json_response(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "executive_summary": raw[:2000],
            "normalization_review": "",
            "action_items": [],
            "projects_needing_manual_review": [],
        }


def _slim_report(report_payload: dict, *, compact: bool = False) -> dict:
    if compact:
        s = report_payload.get("summary") or {}
        return {
            "projects": s.get("total_projects"),
            "tmt": s.get("tmt_projects"),
            "rules": (report_payload.get("dependency_rules") or [])[:3],
            "norm_top": list((report_payload.get("normalization_landscape") or {}).items())[:5],
            "norm_check": [
                {
                    "id": v.get("project_id"),
                    "st": (v.get("validation") or {}).get("status"),
                }
                for v in (report_payload.get("normalization_validation") or [])[:5]
            ],
        }
    return {
        "summary": report_payload.get("summary"),
        "dependency_rules": report_payload.get("dependency_rules"),
        "normalization_landscape": dict(
            list((report_payload.get("normalization_landscape") or {}).items())[:8]
        ),
        "normalization_validation": report_payload.get("normalization_validation", [])[:5],
    }


def _chat_openai_compatible(
    user_prompt: str,
    *,
    model: str,
    base_url: str,
    api_key: str,
    max_tokens: int,
    system: str,
) -> tuple[str, dict]:
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )
    raw = resp.choices[0].message.content or ""
    usage = {}
    if resp.usage:
        usage = {
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
        }
    return raw, usage


def _chat_gpt4all(user_prompt: str, *, model_file: str, max_tokens: int, system: str) -> str:
    from atlas_agent.local_gpt4all import generate

    short_system = "Ты помощник по TMT-протеомике. Отвечай кратко на русском. Только JSON."
    return generate(
        user_prompt,
        model_file=model_file,
        max_tokens=min(max_tokens, 800),
        system=short_system,
    )


def _chat_claude(user_prompt: str, *, model: str, max_tokens: int, system: str) -> tuple[str, dict]:
    from anthropic import Anthropic

    client = Anthropic()
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    parts = [b.text for b in message.content if hasattr(b, "text")]
    return "\n".join(parts).strip(), {
        "input_tokens": getattr(message.usage, "input_tokens", None),
        "output_tokens": getattr(message.usage, "output_tokens", None),
    }


def _build_user_prompt(slim: dict, *, compact: bool = False) -> str:
    if compact:
        return (
            "Atlas TMT proteomics. JSON:\n"
            + json.dumps(slim, ensure_ascii=False)
            + '\nОтвет JSON: {"executive_summary":"...","normalization_review":"...","action_items":[],"projects_needing_manual_review":[]}'
        )
    return f"""Проанализируй сводку Atlas Agent.

JSON:
{json.dumps(slim, ensure_ascii=False, indent=2)}

Ответ только JSON:
{{"executive_summary":"...","normalization_review":"...","action_items":[],"projects_needing_manual_review":[]}}
"""


def _run_llm(
    user_prompt: str,
    system: str,
    *,
    provider: str,
    model: str | None,
    base_url: str | None,
    gpt4all_model: str | None,
    max_tokens: int,
    prefer_cloud: bool = True,
) -> tuple[str, str, dict]:
    """Returns (raw_text, engine_name, usage_dict)."""
    p = (provider or "auto").lower()
    engine = resolve_engine(p, base_url, prefer_cloud=prefer_cloud)

    if engine == "zai":
        url = (base_url or os.environ.get("ZAI_BASE_URL") or DEFAULT_ZAI_BASE).rstrip("/") + "/"
        m = model or os.environ.get("ZAI_MODEL") or DEFAULT_ZAI_MODEL
        raw, usage = _chat_openai_compatible(
            user_prompt,
            model=m,
            base_url=url,
            api_key=zai_api_key(),
            max_tokens=max_tokens,
            system=system,
        )
        return raw, f"zai:{m}", usage

    if engine == "ollama":
        url = base_url or os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE
        m = model or os.environ.get("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL
        raw, usage = _chat_openai_compatible(
            user_prompt,
            model=m,
            base_url=url,
            api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            max_tokens=max_tokens,
            system=system,
        )
        return raw, "ollama", usage

    if engine == "gpt4all":
        mf = gpt4all_model or model or DEFAULT_GPT4ALL_MODEL
        raw = _chat_gpt4all(user_prompt, model_file=mf, max_tokens=max_tokens, system=system)
        return raw, f"gpt4all:{mf}", {}

    if engine == "qwen_cloud":
        url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        m = model or DEFAULT_QWEN_MODEL
        key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("QWEN_API_KEY")
        raw, usage = _chat_openai_compatible(
            user_prompt, model=m, base_url=url, api_key=key, max_tokens=max_tokens, system=system
        )
        return raw, "qwen_cloud", usage

    if engine == "claude":
        m = model or DEFAULT_CLAUDE_MODEL
        raw, usage = _chat_claude(user_prompt, model=m, max_tokens=max_tokens, system=system)
        return raw, "claude", usage

    raise RuntimeError("no_llm_engine")


def ping_llm(
    *,
    provider: str = "auto",
    model: str | None = None,
    base_url: str | None = None,
    gpt4all_model: str | None = None,
    prefer_cloud: bool = True,
) -> dict[str, Any]:
    """Короткий запрос к активному движку (для `run_discovery.py llm --test`)."""
    engine = resolve_engine(provider, base_url, prefer_cloud=prefer_cloud)
    if engine == "local_rules":
        return {"ok": False, "engine": engine, "error": "no_llm_engine"}
    try:
        raw, used, usage = _run_llm(
            'Ответь JSON: {"status":"ok","engine":"' + engine + '"}',
            "Отвечай только JSON.",
            provider=provider,
            model=model,
            base_url=base_url,
            gpt4all_model=gpt4all_model,
            max_tokens=64,
            prefer_cloud=prefer_cloud,
        )
        return {
            "ok": True,
            "engine": used,
            "reply": raw[:200],
            "usage": usage,
        }
    except Exception as e:
        return {"ok": False, "engine": engine, "error": str(e)}


def analyze_report(
    report_payload: dict,
    *,
    provider: str = "auto",
    model: str | None = None,
    base_url: str | None = None,
    gpt4all_model: str | None = None,
    max_tokens: int = 2048,
    df=None,
    use_ai: bool = True,
    prefer_cloud: bool = True,
) -> dict[str, Any]:
    if not use_ai:
        return {"available": False, "error": "ИИ отключён"}

    engine = resolve_engine(provider, base_url, prefer_cloud=prefer_cloud)
    compact = engine.startswith("gpt4all")
    system = _load_system_prompt() if not compact else "TMT atlas assistant"
    slim = _slim_report(report_payload, compact=compact)
    user_prompt = _build_user_prompt(slim, compact=compact)

    try:
        raw, engine, usage = _run_llm(
            user_prompt,
            system,
            provider=provider,
            model=model,
            base_url=base_url,
            gpt4all_model=gpt4all_model,
            max_tokens=max_tokens,
            prefer_cloud=prefer_cloud,
        )
        parsed = _parse_json_response(raw)
        parsed["available"] = True
        parsed["engine"] = engine
        if engine.startswith("zai:"):
            parsed["model"] = engine.split(":", 1)[1]
        elif engine.startswith("gpt4all:"):
            parsed["model"] = engine.split(":", 1)[1]
        else:
            parsed["model"] = model or gpt4all_model or DEFAULT_GPT4ALL_MODEL
        parsed["usage"] = usage
        return parsed
    except RuntimeError:
        pass
    except Exception as e:
        from atlas_agent.local_analyst import generate_local_analysis

        out = generate_local_analysis(report_payload, df)
        out["llm_note"] = f"Локальный LLM ошибка ({e!s}). Установите: pip install gpt4all"
        return out

    from atlas_agent.local_analyst import generate_local_analysis

    out = generate_local_analysis(report_payload, df)
    out["llm_note"] = (
        "Облачный ИИ: задайте ZAI_API_KEY (Z.AI GLM), DASHSCOPE_API_KEY (Qwen) "
        "или ANTHROPIC_API_KEY (Claude). Локально: Ollama или pip install gpt4all."
    )
    return out


def ask_about_project(
    row: dict,
    *,
    provider: str = "auto",
    model: str | None = None,
    base_url: str | None = None,
    gpt4all_model: str | None = None,
    question: str | None = None,
    max_tokens: int = 1536,
    prefer_cloud: bool = True,
) -> str:
    q = question or "Кратко: нормализация, дизайн, статистика для этого проекта."
    system = _load_system_prompt()
    user_prompt = f"Вопрос: {q}\n\nJSON:\n{json.dumps(row, ensure_ascii=False, indent=2)}"
    try:
        raw, engine, _ = _run_llm(
            user_prompt,
            system,
            provider=provider,
            model=model,
            base_url=base_url,
            gpt4all_model=gpt4all_model,
            max_tokens=max_tokens,
            prefer_cloud=prefer_cloud,
        )
        return f"[{engine}]\n{raw}"
    except Exception as e:
        return (
            f"ИИ недоступен: {e}\n"
            "Задайте ZAI_API_KEY в .env или config llm.provider: zai\n"
            "Локально: pip install gpt4all или Ollama."
        )
