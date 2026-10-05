"""Resolución de la categoría de referencia para D1 (decisión A16, AGENTS.md).

`categories_tags` de Open Food Facts es multietiqueta y jerárquica: cada
producto trae una lista de etiquetas separadas por comas, ordenada de lo más
genérico a lo más específico (así la publica OFF). La categoría de referencia
se elige por **retroceso ascendente**: se toma la etiqueta más específica del
producto; si su tamaño en el universo es menor que el mínimo, se sube un
nivel y se repite. Si se agota la jerarquía del producto sin alcanzar el
mínimo, el producto no tiene categoría de referencia válida — no se fuerza
ninguna, consistente con la decisión A2 (sin dato es NULL, nunca una
aproximación forzada).
"""

from __future__ import annotations

import pandas as pd

from nutrimatch.engine.constants import TAMANO_MINIMO_CATEGORIA


def _dividir_etiquetas(categories_tags: str) -> list[str]:
    return [etiqueta.strip() for etiqueta in categories_tags.split(",") if etiqueta.strip()]


def calcular_tamanos_de_categoria(categories_tags: pd.Series) -> dict[str, int]:
    """Tamaño de cada etiqueta: nº de productos que la traen en cualquier posición.

    Un producto etiquetado con una categoría específica también cuenta para
    sus categorías ancestras, que es como OFF construye su taxonomía. Este es
    el mismo método usado en el EDA para listar las categorías más frecuentes
    (notebooks/02_eda_universo_mexico.ipynb, sección 5).
    """
    conteo: dict[str, int] = {}
    for tags in categories_tags.dropna():
        for etiqueta in set(_dividir_etiquetas(tags)):
            conteo[etiqueta] = conteo.get(etiqueta, 0) + 1
    return conteo


def resolver_categoria_referencia(
    categories_tags: pd.Series,
    tamano_minimo: int = TAMANO_MINIMO_CATEGORIA,
) -> pd.DataFrame:
    """Resuelve, para cada producto, su categoría de referencia por retroceso ascendente.

    Devuelve un DataFrame con el mismo índice que `categories_tags` y dos
    columnas:

    - ``categoria_referencia``: la etiqueta elegida, o ``pd.NA`` si ninguna
      etiqueta del producto alcanza `tamano_minimo`.
    - ``nivel_retroceso``: 0 si se usó la etiqueta más específica, 1 si hubo
      que subir un nivel, 2 si dos, etc. ``pd.NA`` si no se resolvió ninguna
      categoría. Es información de trazabilidad: permite auditar cuántos
      productos necesitaron retroceder y cuánto.
    """
    tamanos = calcular_tamanos_de_categoria(categories_tags)

    referencias: list = []
    niveles: list = []
    for tags in categories_tags:
        if pd.isna(tags) or not str(tags).strip():
            referencias.append(pd.NA)
            niveles.append(pd.NA)
            continue

        etiquetas_especifica_a_generica = list(reversed(_dividir_etiquetas(tags)))
        elegido, nivel_elegido = pd.NA, pd.NA
        for nivel, etiqueta in enumerate(etiquetas_especifica_a_generica):
            if tamanos.get(etiqueta, 0) >= tamano_minimo:
                elegido, nivel_elegido = etiqueta, nivel
                break

        referencias.append(elegido)
        niveles.append(nivel_elegido)

    return pd.DataFrame(
        {"categoria_referencia": pd.array(referencias, dtype="string"), "nivel_retroceso": niveles},
        index=categories_tags.index,
    )
