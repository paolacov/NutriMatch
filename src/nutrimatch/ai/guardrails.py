"""Critic determinista A–K más reglas de receta, Plato y contexto."""

from __future__ import annotations

import re
from typing import Any

_NUM = re.compile(r"(?<![A-Za-z])-?\d+(?:[.,]\d+)?")
_SALUD = re.compile(
    r"\b(saludable|insalubre|sano|dañino|mejor para la salud|malo para la salud|"
    r"recomendado para tu salud|poco saludable|diagn[oó]stico)\b",
    re.IGNORECASE,
)
_SIN_ALERGENOS = re.compile(
    r"sin al[eé]rgenos|no (tiene|contiene) al[eé]rgenos|libre de al[eé]rgenos",
    re.IGNORECASE,
)
_RECOMIENDA_OTRO = re.compile(
    r"te recomiendo|mejor opci[oó]n|en su lugar compra|otro producto",
    re.IGNORECASE,
)
_CERO_DINERO = re.compile(r"\$\s*0(?:[.,]0+)?\b")
_GRUPO_PLATO = re.compile(
    r"pertenece a(l grupo)? (verduras|frutas|cereales|leguminosas)|"
    r"es un (cereal|legumbre|alimento de origen animal)",
    re.IGNORECASE,
)
_DEL_PRODUCTO = re.compile(
    r"(?:usa|usar|incluye)\s+([a-záéíóúñü]+(?:\s+[a-záéíóúñü]+){0,3})\s+del producto",
    re.IGNORECASE,
)
_PRODUCTO_CONTIENE = re.compile(
    r"el (?:producto|registro) (?:tiene|contiene|trae|incluye)\s+"
    r"([a-záéíóúñü]+(?:\s+[a-záéíóúñü]+){0,3})",
    re.IGNORECASE,
)
_RECETA_NUTRICION = re.compile(
    r"la receta (tiene|aporta|contiene) \d",
    re.IGNORECASE,
)
_RECETA_DIETA = re.compile(
    r"la receta (es|queda) (vegana|vegetariana|apta|apto)|"
    r"apto para (veganos|vegetarianos|tu dieta)",
    re.IGNORECASE,
)


def _norm_num(texto: str) -> str:
    return texto.replace(",", ".")


def numeros_permitidos(payload: dict[str, Any]) -> set[str]:
    encontrados: set[str] = {"100"}

    def walk(nodo: Any) -> None:
        if isinstance(nodo, bool):
            return
        if isinstance(nodo, int):
            encontrados.add(str(nodo))
            return
        if isinstance(nodo, float):
            encontrados.add(_norm_num(f"{nodo:.4f}").rstrip("0").rstrip("."))
            encontrados.add(_norm_num(f"{nodo:.1f}"))
            encontrados.add(_norm_num(f"{nodo:.2f}"))
            if abs(nodo - round(nodo)) < 1e-9:
                encontrados.add(str(int(round(nodo))))
            return
        if isinstance(nodo, str):
            for match in _NUM.finditer(nodo):
                encontrados.add(_norm_num(match.group(0)))
            return
        if isinstance(nodo, dict):
            for valor in nodo.values():
                walk(valor)
            return
        if isinstance(nodo, list):
            for valor in nodo:
                walk(valor)

    walk(payload)
    return {_norm_num(x) for x in encontrados}


def _auditar_producto(texto: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    if "product" not in payload or "decision" not in payload:
        return []
    hallazgos: list[dict[str, str]] = []
    permitidos = numeros_permitidos(payload)
    decision = payload["decision"]
    constraints = payload.get("constraints") or {}
    price = payload.get("price") or {}
    availability = payload.get("availability") or {}

    for match in _NUM.finditer(texto):
        crudo = _norm_num(match.group(0))
        if crudo not in permitidos and crudo.lstrip("0") not in permitidos:
            if len(crudo) >= 8:
                continue
            hallazgos.append(
                {"code": "A", "detail": f"Número no presente en el payload: {match.group(0)}"}
            )

    if price.get("value") is None and re.search(r"\$\s*\d", texto):
        hallazgos.append({"code": "B", "detail": "Menciona un precio en dinero que el payload no tiene."})

    if _CERO_DINERO.search(texto) and (price.get("value") is None or price.get("value") != 0):
        hallazgos.append({"code": "B", "detail": "Afirma $0 sin un precio 0 en el payload."})

    if constraints.get("allergy_evaluable") is False:
        if re.search(r"\bno apto\b|alergia:\s*apto|\bes apto\b", texto, re.IGNORECASE):
            hallazgos.append({"code": "D", "detail": "Afirma apto/no apto sin alergia evaluable."})
        if _SIN_ALERGENOS.search(texto):
            hallazgos.append({"code": "D", "detail": "Afirma ausencia de alérgenos sin evaluación."})
    elif constraints.get("allergy_status") == "no_verificable":
        if _SIN_ALERGENOS.search(texto) or re.search(r"alergia:\s*apto|\bes apto\b", texto, re.IGNORECASE):
            hallazgos.append({"code": "D", "detail": "Convierte alergia no determinable en apto."})

    if _SIN_ALERGENOS.search(texto) and availability.get("allergens_registered"):
        hallazgos.append({"code": "J", "detail": "Convierte alérgenos no registrados en ausencia."})

    if constraints.get("diet_evaluable") is False:
        if re.search(r"\bincompatible\b|dieta:\s*compatible|\bes compatible\b", texto, re.IGNORECASE):
            hallazgos.append({"code": "E", "detail": "Afirma dieta sin dieta declarada."})
    elif constraints.get("diet_status") == "no_verificable":
        if re.search(r"dieta:\s*compatible|\bes compatible\b", texto, re.IGNORECASE):
            hallazgos.append({"code": "E", "detail": "Afirma compatibilidad dietética no determinable."})

    score = decision.get("score")
    if score is not None:
        for pieza in re.finditer(r"score[^\d]{0,12}(\d+(?:[.,]\d+)?)", texto, re.IGNORECASE):
            num = _norm_num(pieza.group(1))
            permitidos_score = {
                _norm_num(f"{score:.1f}"),
                _norm_num(f"{score:.2f}"),
                str(int(round(score))) if abs(score - round(score)) < 1e-6 else "",
            }
            if num not in permitidos_score and num not in permitidos:
                hallazgos.append({"code": "G", "detail": f"Posible score distinto al del motor: {num}"})

    banda = decision.get("band")
    etiquetas_banda = {
        "ranking": ("en ranking", "ranking"),
        "no_verificable": ("no verificable",),
        "informacion_insuficiente": ("información insuficiente", "informacion insuficiente"),
        "excluido": ("excluido",),
    }
    otras_bandas = {
        "ranking": ("excluido", "no verificable", "información insuficiente"),
        "no_verificable": ("excluido", "en ranking"),
        "informacion_insuficiente": ("excluido", "en ranking"),
        "excluido": ("en ranking",),
    }
    if banda in etiquetas_banda:
        texto_l = texto.lower()
        if not any(e in texto_l for e in etiquetas_banda[banda]):
            for ajena in otras_bandas[banda]:
                if ajena in texto_l:
                    hallazgos.append({"code": "H", "detail": f"Menciona una banda distinta: {ajena}."})
                    break

    if availability.get("d1") and re.search(r"az[uú]car(es)?\s+(es|son)\s+0", texto, re.IGNORECASE):
        hallazgos.append({"code": "J", "detail": "Convierte nutrición no disponible en cero."})

    return hallazgos


def _normalizar_ingrediente(texto: str) -> str:
    return " ".join(texto.lower().split())


def _auditar_receta(texto: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    receta = payload.get("recipe_context") or {}
    if not receta and payload.get("intent") != "recipe":
        return []
    hallazgos: list[dict[str, str]] = []
    observados = {_normalizar_ingrediente(i) for i in receta.get("observed_ingredients", []) if i}
    extras = {_normalizar_ingrediente(i) for i in receta.get("llm_extra_suggested", []) if i}

    for crudo in receta.get("claimed_product_ingredients", []):
        if _normalizar_ingrediente(crudo) not in observados:
            hallazgos.append(
                {"code": "L", "detail": f"Ingrediente de producto no observado: {crudo}"}
            )

    for match in (*_DEL_PRODUCTO.finditer(texto), *_PRODUCTO_CONTIENE.finditer(texto)):
        candidato = _normalizar_ingrediente(match.group(1))
        if candidato and candidato not in observados:
            hallazgos.append(
                {"code": "L", "detail": f"Ingrediente de producto no observado: {match.group(1)}"}
            )

    for extra in extras:
        if extra and re.search(
            rf"{re.escape(extra)}.{{0,80}}(del producto|en el registro)",
            texto,
            re.IGNORECASE,
        ):
            hallazgos.append(
                {"code": "L", "detail": f"Presenta un extra como dato del producto: {extra}"}
            )

    if _RECETA_NUTRICION.search(texto) and not receta.get("nutrition_available"):
        hallazgos.append({"code": "L", "detail": "Inventa nutrición de la receta."})

    if payload.get("intent") == "recipe":
        if _RECETA_DIETA.search(texto):
            hallazgos.append({"code": "L", "detail": "Afirma dieta de la receta sin evidencia."})
        if _SIN_ALERGENOS.search(texto):
            hallazgos.append({"code": "L", "detail": "Afirma alérgenos de la receta sin evidencia."})
    return hallazgos


def _auditar_plato(texto: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    grupos = payload.get("plato_groups") or []
    if not grupos:
        return []
    if any(g.get("group") == "unclassified" for g in grupos) and _GRUPO_PLATO.search(texto):
        if "no clasificado" not in texto.lower() and "no se puede" not in texto.lower():
            return [{"code": "M", "detail": "Asigna un grupo del Plato sin clasificación observada."}]
    return []


def auditar(texto: str, payload: dict[str, Any]) -> list[dict[str, str]]:
    if payload.get("intent") == "reject":
        return []
    if payload.get("intent") == "normalize_product":
        hallazgos: list[dict[str, str]] = []
        if _SALUD.search(texto):
            hallazgos.append({"code": "F", "detail": "Introduce un juicio de salud que el motor no emite."})
        if _RECETA_DIETA.search(texto) or _SIN_ALERGENOS.search(texto):
            hallazgos.append({"code": "L", "detail": "Inventa dieta o alérgenos en la normalización."})
        return hallazgos
    hallazgos = _auditar_producto(texto, payload)
    if payload.get("intent") == "fun_fact":
        # El dato es educación general. Un «2» en «tipo 2» no es un nutriente del producto.
        hallazgos = [h for h in hallazgos if h["code"] != "A"]
    if _SALUD.search(texto):
        hallazgos.append({"code": "F", "detail": "Introduce un juicio de salud que el motor no emite."})
    if _RECOMIENDA_OTRO.search(texto) and payload.get("intent") != "recipe":
        hallazgos.append({"code": "I", "detail": "Recomienda otro producto."})
    hallazgos.extend(_auditar_receta(texto, payload))
    hallazgos.extend(_auditar_plato(texto, payload))
    return hallazgos
