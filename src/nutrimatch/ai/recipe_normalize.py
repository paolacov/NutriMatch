"""Normalización culinaria de nombres, solo para la experiencia de recetas.

No escribe Parquet ni altera product_name del catálogo. El original se conserva
en ``RecipeProductContext.original_name``.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

from nutrimatch.ai.schemas import RecipeProductContext
from nutrimatch.schemas.product import ProductDetail

_LANG_PREFIX = re.compile(r"^(?:[a-z]{2})\s*:\s+", re.IGNORECASE)
_QTY = re.compile(
    r"\b\d+\s*[x×]\s*\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l|cl|mg|oz|lb|pz|pzas?|piezas?)?\b"
    r"|\b\d+(?:[.,]\d+)?\s*(?:g|kg|ml|l|cl|mg|oz|lb)\b"
    r"|\b\d+\s*(?:pz|pzas?|piezas?|unidades?)\b",
    re.IGNORECASE,
)
_CODE = re.compile(r"\b\d{8,14}\b")
_PACK = re.compile(
    r"\b(?:pack|paquete|promo|oferta|ahorro|familiar|multipack)\b",
    re.IGNORECASE,
)
_AMBIGUO = {"producto", "alimento", "articulo", "artículo", "item"}
_RELLENO_INICIO = {
    "delicioso",
    "deliciosa",
    "rico",
    "rica",
    "nuevo",
    "nueva",
    "super",
    "súper",
    "exquisito",
    "exquisita",
    "famoso",
    "famosa",
    "autentico",
    "auténtico",
    "autentica",
    "auténtica",
}
_PUNTOS = re.compile(r"[\s|/,\-–—]+")
_NO_ALFANUM = re.compile(r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ]+", re.IGNORECASE)

_TRADUCIR = {
    "yaourt": "yogur",
    "yogurt": "yogur",
    "yoghurt": "yogur",
    "yoghourt": "yogur",
    "creme": "crema",
    "crème": "crema",
    "nature": "natural",
    "entier": "entero",
    "entiere": "entera",
    "lait": "leche",
    "bread": "pan",
    "oats": "avena",
    "oatmeal": "avena",
}

_MINUSCULAS = {"de", "del", "la", "el", "los", "las", "y", "o", "con", "en", "a", "al", "un", "una"}
_DISPLAY_KEEP = {"natural", "griego", "griega", "integral"}
_DISPLAY_STOP = {
    "entero",
    "entera",
    "original",
    "premium",
    "clasico",
    "clásico",
    "light",
    "nuevo",
    "nueva",
    "extra",
}
_GENERIC_DE = {"crema", "creme", "aceite", "jugo", "zumo", "dulce", "tortilla", "tortillas"}
_PEGAMENTO = {"de", "del", "y", "con", "la", "el", "en", "a", "al", "un", "una", "los", "las"}
_COMIDA_CORTA = {"pan", "sal", "ajo", "miel", "uva", "ron", "gin", "te", "té", "soy", "mix", "dip", "pie"}
_ARTICULOS = {"la", "el", "los", "las", "un", "una"}

_CACHE: dict[str, RecipeProductContext] = {}


def limpiar_cache_normalizacion() -> None:
    _CACHE.clear()


def _plegar(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch)).lower()


def _capitalizar(texto: str) -> str:
    partes = [p for p in texto.split() if p]
    salida: list[str] = []
    despues_de = False
    for i, parte in enumerate(partes):
        baja = parte.lower()
        if i > 0 and (baja in _MINUSCULAS or baja in _DISPLAY_KEEP or despues_de):
            salida.append(baja)
        else:
            salida.append(baja[:1].upper() + baja[1:] if baja else parte)
        despues_de = baja in {"de", "del"}
    return " ".join(salida)


def _traducir_palabra(palabra: str) -> str:
    return _TRADUCIR.get(palabra.lower(), palabra)


def _quitar_marca(texto: str, brand: str | None) -> str:
    if not brand or not texto:
        return texto
    resultado = texto
    for trozo in re.split(r"[,/&]| y ", brand):
        marca = trozo.strip()
        if len(marca) < 2:
            continue
        variantes = {marca, re.sub(r"[^\w\s]", " ", marca)}
        for variante in variantes:
            variante = _PUNTOS.sub(" ", variante).strip()
            if len(variante) < 2:
                continue
            patron = re.compile(rf"\b{re.escape(variante)}\b", re.IGNORECASE)
            resultado = patron.sub(" ", resultado)
            plegado = _plegar(variante)
            if plegado:
                palabras = resultado.split()
                resultado = " ".join(p for p in palabras if _plegar(p) != plegado)
    return _PUNTOS.sub(" ", resultado).strip()


def _limpiar_comercial(crudo: str) -> str:
    texto = _LANG_PREFIX.sub("", crudo.strip())
    texto = _QTY.sub(" ", texto)
    texto = _CODE.sub(" ", texto)
    texto = _PACK.sub(" ", texto)
    texto = _NO_ALFANUM.sub(" ", texto)
    texto = _PUNTOS.sub(" ", texto).strip()
    palabras = [_traducir_palabra(p) for p in texto.split() if p]
    return " ".join(palabras).strip()


def _display_desde_palabras(palabras: list[str]) -> str:
    if not palabras:
        return ""
    nucleo = [palabras[0]]
    resto = palabras[1:]
    i = 0
    while i < len(resto):
        actual = resto[i].lower()
        if actual in {"de", "del"} and nucleo[0].lower() in _GENERIC_DE and i + 1 < len(resto):
            nucleo.extend([resto[i], resto[i + 1]])
            break
        if actual in _DISPLAY_KEEP and len(nucleo) < 3:
            nucleo.append(resto[i])
            if actual in {"griego", "griega", "integral"}:
                break
            i += 1
            continue
        if actual in _DISPLAY_STOP:
            break
        break
    return _capitalizar(" ".join(nucleo))


def _culinario_desde_display(display: str) -> str:
    palabras = display.split()
    if not palabras:
        return ""
    if palabras[0].lower() in _GENERIC_DE and len(palabras) >= 3:
        return " ".join(p.lower() for p in palabras[:3])
    return palabras[0].lower()


def normalizar_nombre_culinario(
    *,
    code: str = "",
    original_name: str | None,
    generic_name: str | None = None,
    brand: str | None = None,
    quantity: str | None = None,
    category: str | None = None,
    ingredients: list[str] | None = None,
) -> RecipeProductContext:
    """Baseline determinista. Conservador: si no hay señal, se deja el original."""
    original = _dato_texto(original_name, conservar_nan_literal=True)
    generico = _dato_texto(generic_name, conservar_nan_literal=False)
    fuente = original if original else generico
    ingredientes = [i for i in (ingredients or []) if i and str(i).strip()]
    marca = _dato_texto(brand, conservar_nan_literal=False)
    cantidad = _dato_texto(quantity, conservar_nan_literal=False)

    if fuente is None:
        return RecipeProductContext(
            code=code,
            original_name=original,
            display_name=None,
            culinary_name=None,
            product_type=None,
            confidence="low",
            brand=marca,
            quantity=cantidad,
            available_ingredients=ingredientes,
        )

    if original is not None and original.strip().upper() == "NAN":
        return RecipeProductContext(
            code=code,
            original_name=original,
            display_name="NAN",
            culinary_name="nan",
            product_type=None,
            confidence="high",
            brand=marca,
            quantity=cantidad,
            available_ingredients=ingredientes,
        )

    texto = _LANG_PREFIX.sub("", fuente.strip())
    texto = _quitar_marca(texto, marca)
    limpio = _limpiar_comercial(texto)
    limpio = _quitar_marca(limpio, marca)
    limpio = _PUNTOS.sub(" ", limpio).strip()
    if not limpio:
        limpio = fuente

    palabras = limpio.split()
    while palabras and palabras[0].lower() in _RELLENO_INICIO:
        palabras = palabras[1:]
    while palabras:
        cabeza = palabras[0]
        baja = cabeza.lower()
        if cabeza.isdigit():
            palabras = palabras[1:]
            continue
        if (
            1 <= len(cabeza) <= 3
            and baja not in _COMIDA_CORTA
            and baja not in _ARTICULOS
            and not baja.isdigit()
            and len(palabras) > 1
            and len(palabras[1]) >= 4
        ):
            palabras = palabras[1:]
            continue
        break
    if not palabras:
        palabras = limpio.split() or fuente.split()
    if palabras and palabras[0].lower() in _AMBIGUO:
        display = _capitalizar(limpio)
        culinary = display.lower()
        confianza: str = "low"
    else:
        display = _display_desde_palabras(palabras) or _capitalizar(limpio)
        culinary = _culinario_desde_display(display) or display.lower()
        distinto = (display or "").casefold() != fuente.casefold()
        if distinto:
            confianza = "high"
        elif len(display.split()) <= 3:
            confianza = "high"
        else:
            confianza = "medium"

    return RecipeProductContext(
        code=code,
        original_name=original,
        display_name=display,
        culinary_name=culinary,
        product_type=culinary,
        confidence=confianza,  # type: ignore[arg-type]
        brand=marca,
        quantity=cantidad,
        available_ingredients=ingredientes,
    )


def _clave_cache(
    code: str,
    original: str | None,
    generic: str | None,
    brand: str | None,
    ingredients: list[str],
) -> str:
    sig = ",".join(ingredients[:8])
    return f"{code}|{original or ''}|{generic or ''}|{brand or ''}|{sig}"


def _dato_texto(valor: Any, *, conservar_nan_literal: bool = False) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, float) and math.isnan(valor):
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    if not conservar_nan_literal and texto.lower() in {"nan", "none", "<na>"}:
        return None
    return texto


def contexto_desde_detalle(
    detalle: ProductDetail,
    fila: Any = None,
) -> RecipeProductContext:
    original = None
    generic = None
    if fila is not None:
        try:
            original = _dato_texto(fila.get("product_name"), conservar_nan_literal=True)
            generic = _dato_texto(fila.get("generic_name"), conservar_nan_literal=False)
        except Exception:
            original = None
            generic = None
    if original is None and generic is None:
        original = detalle.name.value if isinstance(detalle.name.value, str) else None
    brand = detalle.brand.value if isinstance(detalle.brand.value, str) else None
    clave = _clave_cache(detalle.code, original, generic, brand, list(detalle.ingredients))
    cached = _CACHE.get(clave)
    if cached is not None:
        return cached
    ctx = normalizar_nombre_culinario(
        code=detalle.code,
        original_name=original,
        generic_name=generic,
        brand=brand,
        quantity=detalle.quantity,
        category=detalle.category,
        ingredients=list(detalle.ingredients),
    )
    _CACHE[clave] = ctx
    return ctx


def contextos_desde_hechos(hechos: dict[str, Any], catalogo: Any | None = None) -> list[RecipeProductContext]:
    from nutrimatch.services.product import detalle_desde_fila

    codes = list(hechos.get("codes_found") or [])
    if not codes:
        return []
    salidas: list[RecipeProductContext] = []
    for code in codes:
        fila = None
        detalle = None
        if catalogo is not None:
            try:
                fila = catalogo.get_row(code)
                detalle = detalle_desde_fila(fila)
            except Exception:
                fila = None
        if detalle is None:
            continue
        salidas.append(contexto_desde_detalle(detalle, fila))
    return salidas


def guardar_en_cache(ctx: RecipeProductContext, fuente: dict[str, Any] | None = None) -> None:
    ingredientes = list(ctx.available_ingredients)
    original = ctx.original_name
    generic = None
    brand = ctx.brand
    if fuente:
        generic = fuente.get("generic_name") if isinstance(fuente.get("generic_name"), str) else None
        brand = fuente.get("brand") if fuente.get("brand") else brand
        ingredientes = list(fuente.get("ingredients") or ingredientes)
    _CACHE[_clave_cache(ctx.code, original, generic, brand, ingredientes)] = ctx


def tokens_permitidos(ctx_fuente: dict[str, Any]) -> set[str]:
    piezas: list[str] = []
    for clave in ("original_name", "generic_name", "brand", "category", "categories", "quantity", "ingredients_text"):
        valor = ctx_fuente.get(clave)
        if isinstance(valor, str):
            piezas.append(valor)
    for ing in ctx_fuente.get("ingredients") or []:
        if isinstance(ing, str):
            piezas.append(ing)
    tokens: set[str] = set(_PEGAMENTO)
    tokens.update(_TRADUCIR.values())
    tokens.update(_TRADUCIR.keys())
    tokens.update(_DISPLAY_KEEP)
    for pieza in piezas:
        limpio = _limpiar_comercial(pieza)
        for palabra in limpio.lower().split():
            if palabra:
                tokens.add(palabra)
                tokens.add(_plegar(palabra))
    return tokens


def refinamiento_aceptable(
    propuesto: str | None,
    tokens: set[str],
) -> bool:
    if not propuesto or not propuesto.strip():
        return False
    for palabra in propuesto.lower().split():
        if palabra in _PEGAMENTO or len(palabra) < 4:
            continue
        if palabra not in tokens and _plegar(palabra) not in tokens:
            return False
    return True


def aplicar_refinamiento_llm(
    base: RecipeProductContext,
    propuesto: dict[str, Any],
    fuente: dict[str, Any],
) -> RecipeProductContext:
    tokens = tokens_permitidos(fuente)
    display = propuesto.get("display_name")
    culinary = propuesto.get("culinary_name")
    tipo = propuesto.get("product_type")
    if not refinamiento_aceptable(display, tokens):
        display = None
    if not refinamiento_aceptable(culinary, tokens):
        culinary = None
    if tipo and not refinamiento_aceptable(str(tipo), tokens):
        tipo = None
    if display is None and culinary is None:
        return base
    confianza = propuesto.get("confidence") or base.confidence
    if confianza not in {"high", "medium", "low"}:
        confianza = base.confidence
    refinado = base.model_copy(
        update={
            "display_name": (display or "").strip() or base.display_name,
            "culinary_name": (culinary or "").strip().lower() or base.culinary_name,
            "product_type": (str(tipo).strip().lower() if tipo else None) or base.product_type,
            "confidence": confianza,
            "original_name": base.original_name,
        }
    )
    guardar_en_cache(refinado, fuente)
    return refinado


def fusionar_llm(
    bases: list[RecipeProductContext],
    propuestos: list[dict[str, Any]],
    fuentes: list[dict[str, Any]],
) -> list[RecipeProductContext]:
    por_code = {p.get("code"): p for p in propuestos if p.get("code")}
    fuentes_por_code = {f.get("code"): f for f in fuentes if f.get("code")}
    salida: list[RecipeProductContext] = []
    for base in bases:
        propuesto = por_code.get(base.code)
        fuente = fuentes_por_code.get(base.code) or {
            "original_name": base.original_name,
            "brand": base.brand,
            "quantity": base.quantity,
            "ingredients": base.available_ingredients,
        }
        if not propuesto:
            salida.append(base)
            continue
        salida.append(aplicar_refinamiento_llm(base, propuesto, fuente))
    return salida
