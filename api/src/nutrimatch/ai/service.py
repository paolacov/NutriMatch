"""Orquesta hechos → baseline → OpenAI opcional → critic → texto final."""

from __future__ import annotations

import logging
import re
from typing import Any

from nutrimatch.ai.baseline import narrar_baseline
from nutrimatch.ai.client import narrar_llm
from nutrimatch.ai.facts import ensamblar_hechos
from nutrimatch.ai.guardrails import auditar
from nutrimatch.ai.planner import planear_intent
from nutrimatch.ai.recipe_normalize import contextos_desde_hechos, fusionar_llm
from nutrimatch.ai.resolver import elegir_texto_final
from nutrimatch.ai.schemas import AskObservability, AskRequest, AskResponse, RecipeDraft, RecipeProductContext
from nutrimatch.services.catalog import Catalog
from nutrimatch.services.ranking import RankingService

logger = logging.getLogger("nutrimatch.ai")

MAX_PASOS_RECETA = 5
MIN_RECETAS = 3
MAX_RECETAS = 6

_EXTRAS_BLOQUE = re.compile(
    r"(?:adicionales(?: sugeridos)?|ingredientes extra|extras sugeridos)\s*:\s*([^\n.]+)",
    re.IGNORECASE,
)
_PASO_NUM = re.compile(r"(?:^|\n)\s*\d+[.\)]\s+(.+)")


def _normalizar_ingrediente(texto: str) -> str:
    return " ".join(texto.lower().split())


def _limpiar_lista(valores: list[str] | None) -> list[str]:
    vistos: set[str] = set()
    limpios: list[str] = []
    for crudo in valores or []:
        pieza = " ".join(str(crudo).split()).strip()
        if not pieza:
            continue
        clave = _normalizar_ingrediente(pieza)
        if clave in vistos:
            continue
        vistos.add(clave)
        limpios.append(pieza)
    return limpios


def parsear_receta_del_texto(texto: str) -> tuple[list[str], list[str]]:
    """Extras y pasos explícitos en el narrado. No inventa si no hay etiqueta."""
    extras: list[str] = []
    match = _EXTRAS_BLOQUE.search(texto or "")
    if match:
        extras = _limpiar_lista(re.split(r",|;| y ", match.group(1)))
    pasos = _limpiar_lista([m.group(1) for m in _PASO_NUM.finditer(texto or "")])
    return extras, pasos


def _cubre_producto(extra: str, nombres: list[str]) -> bool:
    extra_n = _normalizar_ingrediente(extra)
    if len(extra_n) < 3:
        return False
    for nombre in nombres:
        tokens = _normalizar_ingrediente(nombre).split()
        if extra_n in tokens or extra_n == _normalizar_ingrediente(nombre):
            return True
        if extra_n in _normalizar_ingrediente(nombre) and len(extra_n) >= 4:
            return True
    return False


def _es_platillo(nombre: str, disponibles: list[str]) -> bool:
    clave = _normalizar_ingrediente(nombre)
    if not clave:
        return False
    return not any(_normalizar_ingrediente(d) == clave for d in disponibles)


def _emparejar_usados(usados: list[str], disponibles: list[str]) -> list[str]:
    if not disponibles:
        return []
    if not usados:
        return list(disponibles)
    vistos: set[str] = set()
    coinciden: list[str] = []
    for crudo in usados:
        pieza = _normalizar_ingrediente(crudo)
        if not pieza:
            continue
        for disponible in disponibles:
            clave = _normalizar_ingrediente(disponible)
            if clave in vistos:
                continue
            if pieza == clave or _cubre_producto(crudo, [disponible]) or _cubre_producto(disponible, [crudo]):
                vistos.add(clave)
                coinciden.append(disponible)
                break
    return coinciden


def ensamblar_receta(
    hechos: dict[str, Any],
    texto: str,
    *,
    source: str,
    extras: list[str] | None = None,
    pasos: list[str] | None = None,
    nombre: str | None = None,
    usados: list[str] | None = None,
    descripcion: str | None = None,
) -> RecipeDraft | None:
    ctx = hechos.get("recipe_context")
    if not ctx:
        return None
    observados = _limpiar_lista(list(ctx.get("observed_ingredients") or []))
    nombres = _limpiar_lista(
        list(ctx.get("display_names") or [])
        + list(ctx.get("culinary_names") or [])
        + list(ctx.get("product_names") or [])
    )
    disponibles = _limpiar_lista(list(ctx.get("display_names") or ctx.get("product_names") or []))
    usados_final = _emparejar_usados(_limpiar_lista(usados), disponibles)
    disponibles_visibles = usados_final or disponibles
    obs_norm = {_normalizar_ingrediente(x) for x in observados}
    extras_entrada = _limpiar_lista(extras)
    pasos_entrada = _limpiar_lista(pasos)
    if source == "llm":
        parse_extras, parse_pasos = parsear_receta_del_texto(texto)
        if not extras_entrada:
            extras_entrada = parse_extras
        if not pasos_entrada:
            pasos_entrada = parse_pasos
    extras_final = [
        extra
        for extra in extras_entrada
        if _normalizar_ingrediente(extra) not in obs_norm and not _cubre_producto(extra, nombres)
    ]
    pasos_final = pasos_entrada[:MAX_PASOS_RECETA]
    return RecipeDraft(
        name=(nombre or "").strip() or "Preparación con productos seleccionados",
        short_description=(descripcion or "").strip(),
        used_products=disponibles_visibles,
        available_ingredients=disponibles_visibles,
        extra_suggested=extras_final if source == "llm" else [],
        steps=pasos_final if source == "llm" else [],
        nutrition_note="No se calculó la nutrición de esta preparación: faltan datos para agregarla.",
    )


def ensamblar_lote_recetas(
    hechos: dict[str, Any],
    texto: str,
    *,
    source: str,
    ideas: list[dict[str, Any]] | None = None,
) -> list[RecipeDraft]:
    if source != "llm":
        return []
    ctx = hechos.get("recipe_context") or {}
    disponibles = _limpiar_lista(list(ctx.get("display_names") or ctx.get("product_names") or []))
    lote: list[RecipeDraft] = []
    vistos: set[str] = set()
    for idea in ideas or []:
        receta = ensamblar_receta(
            hechos,
            texto,
            source=source,
            extras=list(idea.get("extra_suggested") or []),
            pasos=list(idea.get("steps") or []),
            nombre=idea.get("recipe_name") or idea.get("name"),
            usados=list(idea.get("used_products") or []),
            descripcion=idea.get("short_description") or idea.get("description"),
        )
        if receta is None or not receta.steps:
            continue
        if not _es_platillo(receta.name, disponibles):
            continue
        clave = _normalizar_ingrediente(receta.name)
        if clave in vistos:
            continue
        vistos.add(clave)
        lote.append(receta)
        if len(lote) >= MAX_RECETAS:
            break
    lote.sort(key=lambda r: len(r.used_products), reverse=True)
    return lote[:MAX_RECETAS]


def _inyectar_nombres_culinarios(hechos: dict[str, Any], productos: list[RecipeProductContext]) -> None:
    hechos["recipe_products"] = [p.model_dump() for p in productos]
    ctx = hechos.get("recipe_context")
    if not isinstance(ctx, dict):
        return
    visibles = [p.display_name or p.culinary_name or p.original_name for p in productos]
    visibles = [n for n in visibles if n]
    culinarios = [p.culinary_name for p in productos if p.culinary_name]
    originales = [p.original_name for p in productos if p.original_name]
    if visibles:
        ctx["product_names"] = visibles
        ctx["display_names"] = visibles
    if culinarios:
        ctx["culinary_names"] = culinarios
    if originales:
        ctx["original_names"] = originales


def preguntar(
    peticion: AskRequest,
    *,
    catalogo: Catalog,
    servicio: RankingService,
) -> AskResponse:
    codes = [c.strip() for c in peticion.codes if c.strip()]
    intent = planear_intent(peticion.intent, peticion.message, n_codes=len(codes))
    hechos = ensamblar_hechos(
        catalogo=catalogo,
        servicio=servicio,
        codes=codes,
        profile=peticion.profile,
        intent=intent,
        message=peticion.message,
        culinary_goal=peticion.culinary_goal,
        surface=peticion.surface,
    )
    productos: list[RecipeProductContext] = []
    if intent in {"recipe", "normalize_product"}:
        productos = contextos_desde_hechos(hechos, catalogo)
        _inyectar_nombres_culinarios(hechos, productos)
    baseline = narrar_baseline(hechos, intent=intent)
    if intent == "reject":
        observabilidad = AskObservability(
            intent="reject",
            model=None,
            ok=True,
            fallback=True,
            fallback_reason="fuera_de_contexto",
            error_kind="fuera_de_contexto",
        )
        logger.info(
            "ai_ask intent=reject model=n/a latency_ms=n/a tokens=n/a ok=true fallback=true fallback_reason=fuera_de_contexto",
        )
        return AskResponse(
            intent="reject",
            text=baseline,
            source="baseline",
            fallback=True,
            fallback_reason="fuera_de_contexto",
            critic_pass=None,
            plato_education=list(hechos.get("plato_education") or []),
            facts_summary={"codes": hechos.get("codes_found"), "intent": "reject"},
            observability=observabilidad,
        )

    llm = narrar_llm(hechos, intent=intent, message=peticion.message)
    if intent == "normalize_product" and llm.get("ok"):
        productos = fusionar_llm(
            productos,
            list(llm.get("normalized_products") or []),
            list(hechos.get("normalize_sources") or []),
        )
        _inyectar_nombres_culinarios(hechos, productos)
    if intent == "recipe":
        ctx = hechos.setdefault("recipe_context", {})
        extras_lote = list(llm.get("extra_suggested") or [])
        pasos_lote = list(llm.get("steps") or [])
        for idea in llm.get("recipes") or []:
            extras_lote.extend(idea.get("extra_suggested") or [])
            pasos_lote.extend(idea.get("steps") or [])
        ctx["llm_extra_suggested"] = _limpiar_lista(extras_lote)
        ctx["llm_steps"] = _limpiar_lista(pasos_lote)
        ctx["llm_recipe_name"] = llm.get("recipe_name")
    texto_critic = llm.get("text") or ""
    if intent == "recipe":
        for idea in llm.get("recipes") or []:
            texto_critic += " " + str(idea.get("recipe_name") or "")
            texto_critic += " " + " ".join(idea.get("steps") or [])
    critic = auditar(texto_critic, hechos) if texto_critic.strip() else []
    eleccion = elegir_texto_final(baseline=baseline, llm=llm, critic_llm=critic)
    uso = llm.get("usage") or {}
    observabilidad = AskObservability(
        intent=intent,
        model=llm.get("model"),
        latency_ms=llm.get("latency_ms"),
        prompt_tokens=uso.get("prompt_tokens"),
        completion_tokens=uso.get("completion_tokens"),
        total_tokens=uso.get("total_tokens"),
        ok=bool(llm.get("ok")) and not eleccion["fallback"],
        fallback=eleccion["fallback"],
        fallback_reason=eleccion["fallback_reason"],
        error_kind=llm.get("error_kind") if eleccion["fallback"] else None,
    )
    logger.info(
        "ai_ask intent=%s model=%s latency_ms=%s tokens=%s ok=%s fallback=%s fallback_reason=%s",
        intent,
        observabilidad.model or "n/a",
        observabilidad.latency_ms if observabilidad.latency_ms is not None else "n/a",
        observabilidad.total_tokens if observabilidad.total_tokens is not None else "n/a",
        observabilidad.ok,
        observabilidad.fallback,
        observabilidad.fallback_reason or "n/a",
    )
    receta = None
    lote: list[RecipeDraft] = []
    if intent == "recipe":
        fuente = "llm" if eleccion["final_source"] == "llm" else "baseline"
        ideas = list(llm.get("recipes") or [])
        if not ideas and fuente == "llm":
            ideas = [
                {
                    "recipe_name": llm.get("recipe_name"),
                    "short_description": "",
                    "used_products": [],
                    "extra_suggested": list(llm.get("extra_suggested") or []),
                    "steps": list(llm.get("steps") or []),
                }
            ]
        lote = ensamblar_lote_recetas(
            hechos,
            eleccion["final_text"],
            source=fuente,
            ideas=ideas,
        )
        receta = lote[0] if lote else ensamblar_receta(
            hechos,
            eleccion["final_text"],
            source=fuente,
            extras=list(llm.get("extra_suggested") or []) if fuente == "llm" else [],
            pasos=list(llm.get("steps") or []) if fuente == "llm" else [],
            nombre=llm.get("recipe_name") if fuente == "llm" else None,
        )
    return AskResponse(
        intent=intent,
        text=eleccion["final_text"],
        source="llm" if eleccion["final_source"] == "llm" else "baseline",
        fallback=eleccion["fallback"],
        fallback_reason=eleccion["fallback_reason"],
        critic_pass=eleccion["critic_pass"],
        recipe=receta,
        recipes=lote,
        recipe_products=productos,
        comparison=hechos.get("comparison"),
        plato_education=list(hechos.get("plato_education") or []),
        facts_summary={
            "codes": hechos.get("codes_found"),
            "intent": intent,
            "llm_error_kind": llm.get("error_kind"),
        },
        observability=observabilidad,
    )
