"""Elige el texto final: LLM solo si el critic local pasa."""

from __future__ import annotations

from typing import Any


def elegir_texto_final(
    *,
    baseline: str,
    llm: dict[str, Any],
    critic_llm: list[dict[str, str]],
) -> dict[str, Any]:
    texto_llm = (llm.get("text") or "").strip() if llm else ""
    if not llm or not llm.get("ok") or not texto_llm:
        motivo = llm.get("error_kind") if llm else "missing_key"
        return {
            "final_text": baseline,
            "final_source": "baseline",
            "fallback": True,
            "fallback_reason": motivo or "llm_no_disponible",
            "critic_pass": None,
        }
    if critic_llm:
        return {
            "final_text": baseline,
            "final_source": "baseline",
            "fallback": True,
            "fallback_reason": "critic_fail",
            "critic_pass": False,
        }
    return {
        "final_text": texto_llm,
        "final_source": "llm",
        "fallback": False,
        "fallback_reason": None,
        "critic_pass": True,
    }
