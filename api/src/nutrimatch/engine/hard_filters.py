"""Filtros duros de alergia y dieta, de tres estados (decisiones A1 y A15, AGENTS.md).

Las restricciones duras se aplican **antes** de puntuar y **no** forman parte del score (A1):
estas funciones solo clasifican un producto contra un perfil declarado; la decisión de excluirlo
del ranking o mostrarlo en una banda separada es responsabilidad del caller.

Ambos filtros usan tres estados, nunca un binario fail-safe (A15 revisó esa decisión sobre datos
reales: el binario original marcaría el 83,4 % del catálogo como "no apto" por ausencia de dato,
no por presencia real del alérgeno).
"""

from __future__ import annotations

import math
from typing import Any, Literal

EstadoAlergia = Literal["apto", "no_apto", "no_verificable"]
EstadoDieta = Literal["compatible", "incompatible", "no_verificable"]

# Tags de ingredients_analysis_tags verificados en notebooks/02_eda_universo_mexico.ipynb y en
# el snapshot off_csv_20260919 (ver hard_filters, sección de verificación del paso 7).
_TAGS_DIETA: dict[str, dict[str, str]] = {
    "vegano": {"compatible": "en:vegan", "incompatible": "en:non-vegan"},
    "vegetariano": {"compatible": "en:vegetarian", "incompatible": "en:non-vegetarian"},
}


def _es_texto_nulo(valor: Any) -> bool:
    """True si `valor` no trae texto utilizable.

    Cubre `None`, cadenas vacías/blancas, y el `NaN` (float) con el que pandas representa un
    campo de texto ausente al leer un Parquet con DuckDB — `bool(float("nan"))` es `True` en
    Python, así que un chequeo ingenuo con `not valor` NO detecta este caso y lo trataría como
    dato presente por error.
    """
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return not str(valor).strip()


def _dividir_tags(texto: Any) -> set[str]:
    if _es_texto_nulo(texto):
        return set()
    return {t.strip() for t in str(texto).split(",") if t.strip()}


def evaluar_alergia(
    allergens: Any,
    traces: Any,
    alergenos_declarados: list[str],
) -> EstadoAlergia:
    """Clasifica un producto contra la lista de alérgenos declarados por la usuaria.

    `alergenos_declarados` son tags con prefijo de idioma, p. ej. ``["en:gluten", "en:milk"]``,
    igual que llegan en `allergens`/`traces` del snapshot (ver B11, AGENTS.md).

    Reglas:
    - Sin alérgenos declarados: no hay nada que filtrar → ``"apto"``.
    - Si `allergens` **o** `traces` contiene alguno de los alérgenos declarados ("puede
      contener" cuenta igual que confirmado, A15): ``"no_apto"``. Es el filtro fail-safe: ante
      la duda, se excluye.
    - Si ninguno de los dos campos tiene NINGÚN dato (ambos ausentes o vacíos): ``"no_verificable"``
      — no hay información de alérgenos de este producto, no se puede confirmar la ausencia.
    - Si al menos uno de los dos campos tiene dato y ninguno coincide con lo declarado:
      ``"apto"``.
    """
    if not alergenos_declarados:
        return "apto"

    tags_allergens = _dividir_tags(allergens)
    tags_traces = _dividir_tags(traces)

    declarados = set(alergenos_declarados)
    if (tags_allergens & declarados) or (tags_traces & declarados):
        return "no_apto"

    tiene_dato = not _es_texto_nulo(allergens) or not _es_texto_nulo(traces)
    if not tiene_dato:
        return "no_verificable"

    return "apto"


def evaluar_dieta(ingredients_analysis_tags: Any, dieta_declarada: str) -> EstadoDieta:
    """Clasifica un producto contra la dieta declarada por la usuaria.

    `dieta_declarada` debe ser ``"vegano"`` o ``"vegetariano"`` (las únicas dos dietas
    verificables con `ingredients_analysis_tags`, decisión A1). El caller no debe invocar esta
    función si la usuaria no declaró ninguna restricción de dieta.

    Reglas: presencia del tag de compatibilidad (p. ej. ``en:vegan``) → ``"compatible"``;
    presencia del tag de incompatibilidad (``en:non-vegan``) → ``"incompatible"``; cualquier otro
    caso (tag ausente, ``en:vegan-status-unknown``, ``en:maybe-vegan``, o sin
    `ingredients_analysis_tags` en absoluto) → ``"no_verificable"``. "Tal vez" no es lo mismo que
    "sí": no se afirma compatibilidad sin evidencia (A1).
    """
    if dieta_declarada not in _TAGS_DIETA:
        raise ValueError(
            f"dieta_declarada debe ser una de {tuple(_TAGS_DIETA)}, recibido: {dieta_declarada!r}"
        )

    tags = _dividir_tags(ingredients_analysis_tags)
    reglas = _TAGS_DIETA[dieta_declarada]

    if reglas["compatible"] in tags:
        return "compatible"
    if reglas["incompatible"] in tags:
        return "incompatible"
    return "no_verificable"
