"""Resolución del nombre de un producto para mostrar en la interfaz (decisión A28, AGENTS.md).

Hallazgo verificado al construir `notebooks/04_modelo_recomendacion.ipynb`: el campo
`product_name` del export CSV de Open Food Facts puede venir vacío para un producto que sí tiene
nombre en otras columnas del **mismo registro** (`generic_name`, `abbreviated_product_name`). No es
un dato inventado por NutriMatch ni un valor externo: son campos que el propio OFF ya trae para ese
producto, simplemente no siempre sincronizados entre sí por quien contribuyó el dato. Sobre los
16.851 productos del universo México (snapshot `off_csv_20260919`), 1.740 (10,3 %) no tienen
`product_name`; de esos, 68 (0,4 %) sí tienen `generic_name`.

Este módulo **no modifica el snapshot crudo**: `datos/procesados/off_mexico_20260919.parquet` sigue
teniendo `product_name` vacío tal cual lo entrega OFF, consistente con A2 (el dato crudo se
conserva, nunca se sobreescribe en silencio). La resolución se aplica solo al construir el nombre
que se muestra (notebook, ficha de producto, UI futura), con una bandera de trazabilidad que indica
si se usó un campo de respaldo — el mismo patrón que `salt_100g_flag_correccion_escala_aplicada`
(A21): reconciliar datos del propio producto, no inventar ni traer un valor externo.
"""

from __future__ import annotations

import math
from typing import Any

# Orden de fallback: el campo más "oficial" primero. Ver docstring del módulo para el hallazgo
# que motivó esta función.
CAMPOS_NOMBRE_EN_ORDEN: tuple[str, ...] = ("product_name", "generic_name", "abbreviated_product_name")


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


def resolver_nombre_producto(
    product_name: Any,
    generic_name: Any = None,
    abbreviated_product_name: Any = None,
) -> tuple[str | None, bool]:
    """Resuelve el nombre a mostrar de un producto, con fallback entre columnas del propio OFF.

    Prueba en orden `product_name`, `generic_name`, `abbreviated_product_name` (los tres tal como
    los trae el export de OFF para ESE producto) y devuelve el primero que tenga texto utilizable.

    Devuelve una tupla `(nombre, se_uso_respaldo)`:
    - `nombre`: el texto resuelto (sin espacios sobrantes), o `None` si ninguno de los tres campos
      tiene dato — sigue siendo un NULL genuino: no hay ningún nombre en absoluto para ese
      producto (decisión A2, nunca se inventa uno).
    - `se_uso_respaldo`: `True` si el nombre vino de `generic_name` o `abbreviated_product_name`
      en vez de `product_name` — bandera de trazabilidad: permite distinguir un nombre "tal cual
      vino en `product_name`" de uno "resuelto por esta regla".
    """
    valores = (product_name, generic_name, abbreviated_product_name)
    for indice, valor in enumerate(valores):
        if not _es_texto_nulo(valor):
            return str(valor).strip(), indice > 0
    return None, False
