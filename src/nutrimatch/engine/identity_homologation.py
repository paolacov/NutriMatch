"""Homologación de nombre y marca para mostrar (decisiones A28/A33/A37/A38, AGENTS.md).

Paso 3 del plan de trabajo de `docs/diagnostico_calidad_datos.md` (sección H): antes de este
módulo, `product_naming.resolver_nombre_producto` (A28) ya resolvía el nombre por fallback entre
`product_name`, `generic_name` y `abbreviated_product_name` del **mismo** registro. Este módulo
añade dos cosas que A28 no cubría, verificadas en `notebooks/08_re_eda_identidad.ipynb`
(hallazgos 2 y 4, 2026-09-26), y las clasifica como **DERIVED** (A33): calculadas a partir de
REAL sin modelo predictivo.

1. **Placeholders de captura en `product_name`.** 14 de los 16.851 productos traen literalmente
   `"Cargando…"` en `product_name` — un texto de la interfaz de contribución de Open Food Facts
   grabado por error, no un nombre de producto. Tratarlo como si fuera un nombre real (A28 lo
   habría aceptado tal cual, porque el campo no está vacío) sería mostrar un dato falso. Este
   módulo lo trata como si `product_name` estuviera vacío y sigue la cadena de fallback: al menos
   un producto (`7503028965717`) sí recupera un nombre real de `generic_name` gracias a esto.
2. **Homologación de marca.** `brands` tiene la misma marca escrita de formas distintas: 140 filas
   `"Nestlé"` y 106 `"nestle"` como si fueran marcas separadas. Minúsculas + plegado de acentos +
   colapso de espacios fusiona automáticamente 73 de 4.189 marcas únicas del universo México sin
   necesitar un diccionario de alias mantenido a mano (que sería una lista arbitraria, no una
   regla determinista aplicable a cualquier corte del mismo export).

**No modifica el snapshot crudo.** `datos/procesados/off_mexico_20260919.parquet` sigue intacto
(A2). Este módulo se usa desde `scripts/homologar_identidad.py` para escribir un Parquet **nuevo**
(`identidad_homologada_20260919.parquet`) con el original y el homologado lado a lado.
"""

from __future__ import annotations

import math
import unicodedata
from typing import Any

# Placeholders verificados en notebooks/08_re_eda_identidad.ipynb (hallazgo 2, 2026-09-26):
# exactamente 14 filas de 16.851 traen alguna de estas variantes en `product_name`. Comparación
# insensible a mayúsculas y a espacios sobrantes.
PLACEHOLDERS_NOMBRE: frozenset[str] = frozenset({"cargando", "cargando…", "cargando..."})

# Orden de fallback: idéntico a `product_naming.CAMPOS_NOMBRE_EN_ORDEN` (A28). Se repite aquí en
# vez de importarse porque este módulo necesita iterar también sobre el nombre del campo, no solo
# sobre el valor.
CAMPOS_NOMBRE_EN_ORDEN: tuple[str, ...] = ("product_name", "generic_name", "abbreviated_product_name")


def _es_texto_nulo(valor: Any) -> bool:
    """True si `valor` no trae texto utilizable (mismo criterio que en `product_naming.py`).

    Cubre `None`, cadenas vacías/blancas, y el `NaN` (float) con el que pandas representa un
    campo de texto ausente al leer un Parquet con DuckDB — `bool(float("nan"))` es `True` en
    Python, así que un chequeo ingenuo con `not valor` NO detecta este caso (B13, AGENTS.md).
    """
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    return not str(valor).strip()


def _es_placeholder(valor: Any) -> bool:
    """True si `valor` es un placeholder de captura conocido (no un nombre real)."""
    if _es_texto_nulo(valor):
        return False
    return str(valor).strip().lower() in PLACEHOLDERS_NOMBRE


def normalizar_texto_cosmetico(valor: Any) -> str | None:
    """Normaliza espacios y forma Unicode sin tocar mayúsculas, acentos ni el contenido.

    Aplica trim, colapso de espacios internos (incluye tabs/saltos de línea sueltos) y
    normalización Unicode a forma NFC (composición canónica: un carácter con acento se
    representa igual sin importar si el export lo trajo compuesto o descompuesto). No cambia
    mayúsculas ni quita acentos — a diferencia de `homologar_marca`, este valor es para
    **mostrarse**, no para usarse como llave de coincidencia.

    Devuelve `None` si no queda texto utilizable (nunca cadena vacía, decisión A2).
    """
    if _es_texto_nulo(valor):
        return None
    texto = unicodedata.normalize("NFC", str(valor))
    texto = " ".join(texto.split())
    return texto or None


def resolver_nombre_homologado(
    product_name: Any,
    generic_name: Any = None,
    abbreviated_product_name: Any = None,
) -> tuple[str | None, str | None, bool]:
    """Resuelve y homologa el nombre a mostrar, saltando placeholders de captura.

    Mismo orden de fallback que A28 (`product_name` → `generic_name` →
    `abbreviated_product_name`), con una diferencia: si el campo con dato es un placeholder de
    captura conocido (ver `PLACEHOLDERS_NOMBRE`), se trata como si no tuviera dato y se sigue
    probando el siguiente campo, en vez de aceptarlo como nombre real.

    Devuelve una tupla `(nombre_homologado, campo_usado, se_removio_placeholder)`:
    - `nombre_homologado`: el texto resuelto y normalizado cosméticamente (ver
      `normalizar_texto_cosmetico`), o `None` si ningún campo tiene un nombre real utilizable
      (NULL genuino, A2 — nunca se inventa uno).
    - `campo_usado`: cuál de los tres campos aportó el nombre (`"product_name"`,
      `"generic_name"` o `"abbreviated_product_name"`), o `None` si no se encontró nombre.
    - `se_removio_placeholder`: `True` si al menos un campo tenía dato pero era un placeholder
      descartado en el camino — trazabilidad de que hubo intervención, no solo un fallback A28
      normal.
    """
    se_removio_placeholder = False
    for campo, valor in zip(CAMPOS_NOMBRE_EN_ORDEN, (product_name, generic_name, abbreviated_product_name), strict=True):
        if _es_texto_nulo(valor):
            continue
        if _es_placeholder(valor):
            se_removio_placeholder = True
            continue
        return normalizar_texto_cosmetico(valor), campo, se_removio_placeholder
    return None, None, se_removio_placeholder


def homologar_marca(brands: Any) -> str | None:
    """Normaliza `brands` en una llave de coincidencia determinista, no en un valor de despliegue.

    Minúsculas + plegado de acentos (Unicode NFKD, se descartan los caracteres combinantes) +
    colapso de espacios. Verificado en `notebooks/08_re_eda_identidad.ipynb` (hallazgo 4,
    2026-09-26): esta regla fusiona automáticamente 73 de 4.189 marcas únicas del universo México
    que solo diferían en acento o caja — `Nestlé`/`nestle`, `La Costeña`/`la costena`,
    `Nescafé`/`nescafe`, `Tajín`/`tajin`, entre otras — sin diccionario de alias mantenido a
    mano. Es DERIVED (A33): una función pura sobre el propio dato, no una lista de casos
    especiales que dejaría de servir en el próximo snapshot.

    A propósito **no** es apta para mostrarse tal cual en la interfaz (pierde acentos y
    mayúsculas): sirve como llave interna para agrupar y para el cruce de texto
    con QQP (A35). El valor a mostrar sigue siendo `brands` original.

    No separa multi-marca: `"walmart,sams club"` se homologa como una sola cadena, no se parte en
    una lista.

    Devuelve `None` si `brands` no trae texto utilizable.
    """
    if _es_texto_nulo(brands):
        return None
    descompuesto = unicodedata.normalize("NFKD", str(brands))
    sin_acentos = "".join(c for c in descompuesto if not unicodedata.combining(c))
    colapsado = " ".join(sin_acentos.lower().split())
    return colapsado or None
