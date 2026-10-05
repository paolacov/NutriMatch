"""D3 — subpuntaje de preferencias: porcentaje de etiquetas valoradas presentes (decisión A7).

`etiquetas_valoradas` son sellos NO nutricionales que la usuaria eligió (p. ej. ``en:organic``,
``en:no-gluten``, ``en:fair-trade``), tomados de `labels_tags` del producto.
"""

from __future__ import annotations

import math
from typing import Any


def _es_texto_nulo(valor: Any) -> bool:
    """True si `valor` no trae texto utilizable (ver misma función en `hard_filters.py`).

    Cubre `None`, cadenas vacías/blancas, y el `NaN` (float) con el que pandas representa un
    campo de texto ausente al leer un Parquet con DuckDB — `bool(float("nan"))` es `True` en
    Python, así que un chequeo ingenuo con `not valor` NO detecta este caso.
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


def calcular_d3(labels_tags_producto: Any, etiquetas_valoradas: list[str]) -> float | None:
    """Calcula D3 (0-100): porcentaje de `etiquetas_valoradas` presentes en `labels_tags`.

    Devuelve `None` (sin dato, nunca 0 forzado, decisión A2) en dos casos distintos:
    - La usuaria no eligió ninguna etiqueta valorada: D3 no aplica para ella.
    - El producto no tiene NINGÚN dato en `labels_tags` (ausente o vacío): no se puede confirmar
      que el producto carece de las etiquetas valoradas, solo que no se registraron etiquetas en
      absoluto — es la misma lógica que un nutriente sin dato, no una afirmación de "0 %".

    Si el producto sí tiene `labels_tags` (aunque ninguna coincida con lo valorado), el resultado
    es un porcentaje válido, incluyendo 0,0: en ese caso sí sabemos qué etiquetas tiene el
    producto y ninguna es de las valoradas.
    """
    if not etiquetas_valoradas:
        return None

    tags_producto = _dividir_tags(labels_tags_producto)
    if not tags_producto:
        return None

    presentes = sum(1 for etiqueta in etiquetas_valoradas if etiqueta in tags_producto)
    return presentes * 100.0 / len(etiquetas_valoradas)
