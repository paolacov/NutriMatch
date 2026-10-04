"""Cliente OpenAI de la capa de lenguaje. Sin clave no hay red. Nunca registra la clave."""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Literal

from pydantic import BaseModel, Field

from nutrimatch.ai.prompts.base import SYSTEM_PROMPT, slot_fun_fact, user_prompt

logger = logging.getLogger("nutrimatch.ai")

DEFAULT_MODEL = "gpt-4o-mini"
TIMEOUT_SECONDS = 30.0
MAX_OUTPUT_TOKENS = 500
MAX_OUTPUT_TOKENS_RECIPE = 1600
TEMPERATURE = 0.0
SEED = 20260927
PROVIDER = "openai"

ErrorKind = Literal[
    "missing_key",
    "sdk_missing",
    "auth",
    "timeout",
    "network",
    "rate_limit",
    "api",
    "empty",
    "schema",
]

_CLAVE_PATRON = re.compile(r"sk-[A-Za-z0-9_-]+")


class ExplanationOutput(BaseModel):
    explanation: str = Field(min_length=1)
    extra_suggested: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    recipe_name: str | None = None


class RecipeIdeaOut(BaseModel):
    recipe_name: str = Field(min_length=1)
    short_description: str = ""
    used_products: list[str] = Field(default_factory=list)
    extra_suggested: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)


class RecipeBatchOutput(BaseModel):
    explanation: str = Field(min_length=1)
    recipes: list[RecipeIdeaOut] = Field(default_factory=list)


class NormalizedProductOut(BaseModel):
    code: str
    original_name: str | None = None
    display_name: str = Field(min_length=1)
    culinary_name: str = Field(min_length=1)
    product_type: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"


class NormalizeOutput(BaseModel):
    explanation: str = Field(min_length=1)
    products: list[NormalizedProductOut] = Field(default_factory=list)


def _redactar(texto: str) -> str:
    return _CLAVE_PATRON.sub("[redactado]", texto)


def sin_secretos(obj: Any) -> Any:
    if isinstance(obj, str):
        return _redactar(obj)
    if isinstance(obj, dict):
        return {clave: sin_secretos(valor) for clave, valor in obj.items()}
    if isinstance(obj, list):
        return [sin_secretos(valor) for valor in obj]
    return obj


def _cargar_dotenv_del_proyecto() -> None:
    """Misma fuente que el spike: `.env` en la raíz del repo, no el cwd."""
    try:
        from dotenv import load_dotenv

        from nutrimatch.core.config import project_root

        load_dotenv(project_root() / ".env", override=False)
    except Exception:
        return


def _clave_desde_entorno() -> str:
    _cargar_dotenv_del_proyecto()
    directa = os.environ.get("OPENAI_API_KEY", "").strip()
    if directa:
        return directa
    try:
        from nutrimatch.core.config import get_settings

        return (get_settings().openai_api_key or "").strip()
    except Exception:
        return ""


def modelo_configurado() -> str:
    elegido = os.environ.get("OPENAI_MODEL", "").strip()
    if elegido:
        return elegido
    try:
        from nutrimatch.core.config import get_settings

        return (get_settings().openai_model or "").strip() or DEFAULT_MODEL
    except Exception:
        return DEFAULT_MODEL


def llm_disponible() -> bool:
    return bool(_clave_desde_entorno())


def _resultado(
    *,
    ok: bool,
    model: str | None,
    text: str | None,
    error_kind: ErrorKind | None,
    skip_reason: str | None,
    latency_ms: float | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    source: str | None = None,
    extra_suggested: list[str] | None = None,
    steps: list[str] | None = None,
    recipe_name: str | None = None,
    normalized_products: list[dict[str, Any]] | None = None,
    recipes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "provider": PROVIDER,
        "model": model,
        "text": text,
        "error_kind": error_kind,
        "skip_reason": _redactar(skip_reason) if skip_reason else None,
        "latency_ms": latency_ms,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        "source": source,
        "extra_suggested": extra_suggested or [],
        "steps": steps or [],
        "recipe_name": recipe_name,
        "normalized_products": normalized_products or [],
        "recipes": recipes or [],
    }


def _nuevo_cliente(api_key: str) -> Any:
    from openai import OpenAI

    return OpenAI(api_key=api_key, timeout=TIMEOUT_SECONDS)


def _uso(respuesta: Any) -> tuple[int | None, int | None, int | None]:
    usage = getattr(respuesta, "usage", None)
    if usage is None:
        return None, None, None
    return (
        getattr(usage, "prompt_tokens", None),
        getattr(usage, "completion_tokens", None),
        getattr(usage, "total_tokens", None),
    )


def _kind_desde_excepcion(exc: Exception) -> ErrorKind:
    try:
        from openai import (
            APIConnectionError,
            APIError,
            APITimeoutError,
            AuthenticationError,
            RateLimitError,
        )
    except ImportError:
        return "api"

    if isinstance(exc, AuthenticationError):
        return "auth"
    if isinstance(exc, RateLimitError):
        return "rate_limit"
    if isinstance(exc, APITimeoutError):
        return "timeout"
    if isinstance(exc, APIConnectionError):
        return "network"
    if isinstance(exc, APIError):
        return "api"
    nombre = type(exc).__name__
    if "Timeout" in nombre:
        return "timeout"
    if "Connection" in nombre:
        return "network"
    return "api"


def narrar_llm(payload: dict[str, Any], *, intent: str, message: str | None) -> dict[str, Any]:
    model = modelo_configurado()
    clave = _clave_desde_entorno()
    if not clave:
        logger.info("proveedor=%s modelo=%s ok=false error_kind=missing_key fallback=true", PROVIDER, model)
        return _resultado(
            ok=False,
            model=None,
            text=None,
            error_kind="missing_key",
            skip_reason="OPENAI_API_KEY ausente. No se llama a red.",
        )

    try:
        cliente = _nuevo_cliente(clave)
    except ImportError:
        logger.info("proveedor=%s modelo=%s ok=false error_kind=sdk_missing fallback=true", PROVIDER, model)
        return _resultado(
            ok=False,
            model=model,
            text=None,
            error_kind="sdk_missing",
            skip_reason="paquete openai no instalado (extra llm). No se llama a red.",
        )

    tope = MAX_OUTPUT_TOKENS_RECIPE if intent in {"recipe", "normalize_product"} else MAX_OUTPUT_TOKENS
    if intent == "normalize_product":
        esquema = NormalizeOutput
    elif intent == "recipe":
        esquema = RecipeBatchOutput
    else:
        esquema = ExplanationOutput
    inicio = time.perf_counter()
    try:
        respuesta = cliente.chat.completions.parse(
            model=model,
            temperature=TEMPERATURE,
            max_tokens=tope,
            seed=SEED + (slot_fun_fact(message) if intent == "fun_fact" else 0),
            timeout=TIMEOUT_SECONDS,
            response_format=esquema,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt(payload, intent=intent, message=message)},
            ],
        )
    except Exception as exc:
        latency_ms = round((time.perf_counter() - inicio) * 1000, 1)
        kind = _kind_desde_excepcion(exc)
        logger.info(
            "proveedor=%s modelo=%s ok=false error_kind=%s latency_ms=%s fallback=true",
            PROVIDER,
            model,
            kind,
            latency_ms,
        )
        return _resultado(
            ok=False,
            model=model,
            text=None,
            error_kind=kind,
            skip_reason=f"OpenAI no disponible ({kind}). Se usa el baseline.",
            latency_ms=latency_ms,
        )

    latency_ms = round((time.perf_counter() - inicio) * 1000, 1)
    prompt_tokens, completion_tokens, total_tokens = _uso(respuesta)
    try:
        parsed = respuesta.choices[0].message.parsed
    except (IndexError, AttributeError):
        parsed = None
    texto = (getattr(parsed, "explanation", None) or "").strip() if parsed is not None else ""
    extras = [
        e.strip()
        for e in (getattr(parsed, "extra_suggested", None) or [])
        if e and str(e).strip()
    ]
    pasos = [p.strip() for p in (getattr(parsed, "steps", None) or []) if p and str(p).strip()]
    nombre = getattr(parsed, "recipe_name", None)
    nombre = nombre.strip() if isinstance(nombre, str) and nombre.strip() else None
    normalizados: list[dict[str, Any]] = []
    lote: list[dict[str, Any]] = []
    if intent == "normalize_product" and parsed is not None:
        for item in getattr(parsed, "products", None) or []:
            if hasattr(item, "model_dump"):
                normalizados.append(item.model_dump())
    if intent == "recipe" and parsed is not None:
        for item in getattr(parsed, "recipes", None) or []:
            if hasattr(item, "model_dump"):
                lote.append(item.model_dump())
        if not lote and (nombre or extras or pasos):
            lote = [
                {
                    "recipe_name": nombre,
                    "short_description": "",
                    "used_products": [],
                    "extra_suggested": extras,
                    "steps": pasos,
                }
            ]
        if lote and not extras:
            extras = [
                e.strip()
                for idea in lote
                for e in (idea.get("extra_suggested") or [])
                if e and str(e).strip()
            ]
        if lote and not pasos:
            pasos = [
                p.strip()
                for idea in lote
                for p in (idea.get("steps") or [])
                if p and str(p).strip()
            ]
        if lote and not nombre:
            crudo = lote[0].get("recipe_name")
            nombre = crudo.strip() if isinstance(crudo, str) and crudo.strip() else None
    if not texto:
        logger.info(
            "proveedor=%s modelo=%s ok=false error_kind=empty latency_ms=%s fallback=true",
            PROVIDER,
            model,
            latency_ms,
        )
        return _resultado(
            ok=False,
            model=model,
            text=None,
            error_kind="empty" if parsed is not None else "schema",
            skip_reason="La explicación llegó vacía o no cumple el esquema.",
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

    logger.info(
        "proveedor=%s modelo=%s ok=true latency_ms=%s tokens=%s",
        PROVIDER,
        model,
        latency_ms,
        total_tokens,
    )
    return _resultado(
        ok=True,
        model=model,
        text=texto,
        error_kind=None,
        skip_reason=None,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        source="openai",
        extra_suggested=extras if intent == "recipe" else [],
        steps=pasos if intent == "recipe" else [],
        recipe_name=nombre if intent == "recipe" else None,
        normalized_products=normalizados if intent == "normalize_product" else [],
        recipes=lote if intent == "recipe" else [],
    )
