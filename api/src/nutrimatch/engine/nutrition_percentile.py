"""Percentiles de D1 dentro de la categoría de referencia y `category_stats`.

El percentil que se calcula aquí es **agnóstico del objetivo del usuario**:
0 es el valor más bajo del grupo de referencia y 100 el más alto, sin decidir
todavía si "más alto" es deseable o no. Convertir esto en un subpuntaje con
signo ("menos azúcar es mejor", "más fibra es mejor") es responsabilidad del
paso de ranking (paso 7 del plan), no de esta transformación: aquí el dato
depende solo del producto y su categoría, nunca del usuario.
"""

from __future__ import annotations

import pandas as pd

from nutrimatch.engine.constants import CORE8_NUTRIENTES, MINIMO_PEERS_PERCENTIL


def calcular_percentiles_por_categoria(
    valores_saneados: pd.DataFrame,
    categoria_referencia: pd.Series,
    minimo_peers: int = MINIMO_PEERS_PERCENTIL,
) -> pd.DataFrame:
    """Percentil (0-100) de cada nutriente saneado, dentro de su categoría de referencia.

    `valores_saneados` debe traer una columna ``<nutriente>_saneado`` por cada
    nutriente de CORE8_NUTRIENTES (ver `sanitize.sanear_nucleo_nutricional`).

    Devuelve una columna ``percentil_<nutriente>`` por nutriente. El valor es
    NaN si el producto no tiene categoría de referencia, si no tiene dato
    saneado para ese nutriente en particular, o si el número de pares (otros
    productos de la misma categoría con dato válido para ese nutriente) es
    menor que `minimo_peers` — un tamaño de categoría nominal suficiente no
    garantiza que haya suficientes productos con ese dato en particular.
    """
    base = pd.DataFrame({"categoria_referencia": categoria_referencia}, index=valores_saneados.index)
    salida = pd.DataFrame(index=valores_saneados.index)

    for nutriente in CORE8_NUTRIENTES:
        columna_saneada = f"{nutriente}_saneado"
        datos = base.join(valores_saneados[[columna_saneada]])

        tamano_efectivo = datos.groupby("categoria_referencia")[columna_saneada].transform("count")
        percentil = datos.groupby("categoria_referencia")[columna_saneada].rank(pct=True) * 100.0

        valido = (
            datos["categoria_referencia"].notna()
            & datos[columna_saneada].notna()
            & (tamano_efectivo >= minimo_peers)
        )
        salida[f"percentil_{nutriente}"] = percentil.where(valido)

    return salida


def construir_category_stats(
    valores_saneados: pd.DataFrame,
    categoria_referencia: pd.Series,
) -> pd.DataFrame:
    """Tabla `category_stats`: resumen por (categoría de referencia, nutriente).

    Es la tabla de auditoría y trazabilidad de los percentiles: cualquier
    percentil individual debe poder explicarse mostrando `n`, la media y la
    mediana de su grupo de referencia. Solo incluye categorías de referencia
    no nulas (los productos sin categoría resuelta no aportan filas aquí).
    """
    base = pd.DataFrame({"categoria_referencia": categoria_referencia})
    filas = []

    for nutriente in CORE8_NUTRIENTES:
        columna_saneada = f"{nutriente}_saneado"
        datos = base.join(valores_saneados[[columna_saneada]])
        datos = datos[datos["categoria_referencia"].notna()]

        agregado = (
            datos.groupby("categoria_referencia")[columna_saneada]
            .agg(n="count", media="mean", mediana="median", desviacion_estandar="std", minimo="min", maximo="max")
            .reset_index()
        )
        agregado.insert(1, "nutriente", nutriente)
        filas.append(agregado)

    resultado = pd.concat(filas, ignore_index=True)
    # Sin dato suficiente no es lo mismo que dato en cero: una categoría con 0
    # productos válidos para un nutriente no debería aparecer con media 0.
    return resultado[resultado["n"] > 0].reset_index(drop=True)
