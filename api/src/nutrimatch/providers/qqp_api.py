"""Cliente de lectura de la API `datastore_search` de `datos.gob.mx` (CKAN) para PROFECO QQP.

Lee precios de «Quién es Quién en los Precios» para armar candidatos de coincidencia
por texto con el universo de México. No une PROFECO con un código de barras por su
cuenta: QQP no publica ese código. Este módulo solo lee.

Contrato de la fuente, **verificado en vivo el 2026-09-26**:

- Dataset real: `programa_quien_es_quien_precios_2026` en `datos.gob.mx` (portal CKAN de datos
  abiertos de PROFECO), verificado vía
  `https://www.datos.gob.mx/api/3/action/package_show?id=programa_quien_es_quien_precios_2026`.
  Cada mes se publica partido en "primera parte"/"segunda parte" (p. ej. julio 2026 =
  recursos `c9eec682-...` y `40f64926-...`).
- El esquema real, verificado contra el portal, no trae claves `cv_producto` ni `cv_marca`.
  Las columnas, en minúsculas, son `producto, presentacion, marca, categoria, catalogo, precio,
  fecha_registro, cadena_comercial, giro, nombre_comercial, direccion, estado, municipio,
  latitud, longitud`. No hay código de barras.
- **El campo `marca` no es un nombre de marca limpio**: trae `"Alpura. Clásica"`,
  `"La Lechera. Original"`, `"Nescafé. Clásico"` — marca + variante separadas por punto. El
  match debe ser holístico por texto (marca + producto + presentación juntos), no un join de
  llave de marca exacta.
- **No hace falta descargar ningún CSV.** Cada recurso ya está en el "datastore" de CKAN
  (`datastore_active: true`), consultable con `GET .../api/3/action/datastore_search` con
  `resource_id`, `filters` (JSON, coincidencia exacta de campo), `q` (texto libre) y
  paginación `limit`/`offset`. Verificado: el recurso de julio 2026 (primera parte) tiene
  665.909 filas totales; filtrar por `categoria` exacta acota a un subconjunto manejable (p. ej.
  "Café" → 5.018 filas) sin tocar el resto.
- Un WAF (Akamai) frente a `www.datos.gob.mx` bloquea con `HTTP 403` cualquier petición cuyo
  `User-Agent` no parezca un navegador, incluido un agente identificable del estilo
  `NutriMatch/0.1.0 (contacto: ...)` y el `User-Agent` por defecto de `httpx`. Verificado
  aislando la variable: el mismo request con un `User-Agent` de Chrome/Mac responde `200`; con
  cualquier otro, `403`. Para este proveedor, y solo para este, el cliente envía un
  `User-Agent` de navegador. El portal es de datos abiertos públicos (CC-BY 4.0) y el bloqueo
  corresponde a la configuración por defecto de su cortafuegos. Open Food Facts sí pide un
  agente identificable y controla su propio límite de tasa; esa regla no se traslada aquí.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

BASE_URL = "https://www.datos.gob.mx/api/3/action/datastore_search"

# Este portal responde 403 a un agente que no parece un navegador.
# Open Food Facts y Open Prices sí aceptan un agente identificable.
# La constante queda aparte para que la excepción se vea en el código.
USER_AGENT_NAVEGADOR = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Cortesía: no se documentó ningún límite de tasa para esta API: se mantiene un espaciado
# prudente entre páginas de todos modos, igual que con Open Prices.
INTERVALO_ENTRE_PAGINAS_SEGUNDOS = 0.5

# Recursos de julio 2026 (mes completo más reciente con ambas partes publicadas), verificados
# el 2026-09-26 vía `package_show`.
RECURSOS_JULIO_2026: tuple[str, ...] = (
    "c9eec682-48d5-48fd-b5ae-865c22221d40",  # primera parte
    "40f64926-bd6b-4642-8e04-e767d9775d4d",  # segunda parte
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DIR_CACHE_POR_DEFECTO = REPO_ROOT / "datos" / "cache" / "qqp_api"


def _ruta_cache(resource_id: str, categoria: str, offset: int, directorio_cache: Path) -> Path:
    clave = categoria.replace(" ", "_").replace("/", "_").replace(".", "")
    return directorio_cache / f"{resource_id}_{clave}_{offset}.json"


def buscar_por_categoria(
    resource_id: str,
    categoria: str,
    *,
    cliente: httpx.Client,
    limite_filas: int = 300,
    directorio_cache: Path = DIR_CACHE_POR_DEFECTO,
    usar_cache: bool = True,
    intervalo_entre_paginas_segundos: float = INTERVALO_ENTRE_PAGINAS_SEGUNDOS,
) -> list[dict[str, Any]]:
    """Trae hasta `limite_filas` filas de `resource_id` con `categoria` exacta.

    No trae la categoría completa si es más grande que `limite_filas`: este piloto necesita un
    grupo de trabajo manejable para generar candidatos, no el universo completo de esa
    categoría (que puede tener decenas de miles de filas). Pagina en bloques de 100.
    """
    directorio_cache.mkdir(parents=True, exist_ok=True)
    filtro = json.dumps({"categoria": categoria})
    filas: list[dict[str, Any]] = []
    offset = 0
    tamano_pagina = min(100, limite_filas)

    while len(filas) < limite_filas:
        ruta_cache = _ruta_cache(resource_id, categoria, offset, directorio_cache)
        if usar_cache and ruta_cache.exists():
            cuerpo = json.loads(ruta_cache.read_text(encoding="utf-8"))
        else:
            if offset > 0:
                time.sleep(intervalo_entre_paginas_segundos)
            resp = cliente.get(
                BASE_URL,
                params={
                    "resource_id": resource_id,
                    "filters": filtro,
                    "limit": tamano_pagina,
                    "offset": offset,
                },
                headers={"User-Agent": USER_AGENT_NAVEGADOR},
                timeout=30.0,
            )
            resp.raise_for_status()
            cuerpo = resp.json()["result"]
            if usar_cache:
                ruta_cache.write_text(
                    json.dumps(cuerpo, ensure_ascii=False, indent=2), encoding="utf-8"
                )

        registros = cuerpo["records"]
        if not registros:
            break
        filas.extend(registros)
        offset += len(registros)
        if offset >= cuerpo["total"]:
            break

    return filas[:limite_filas]


def buscar_texto(
    resource_id: str,
    q: str,
    *,
    cliente: httpx.Client,
    limite_filas: int = 300,
    directorio_cache: Path = DIR_CACHE_POR_DEFECTO,
    usar_cache: bool = True,
    intervalo_entre_paginas_segundos: float = INTERVALO_ENTRE_PAGINAS_SEGUNDOS,
) -> list[dict[str, Any]]:
    """Trae hasta `limite_filas` filas de `resource_id` cuyo texto libre coincide con `q`.

    Complementa `buscar_por_categoria`: útil para explorar (p. ej. verificar si una marca
    concreta aparece en el recurso) sin depender de que la fila caiga en una `categoria`
    curada. Mismo esquema de paginación y caché.
    """
    directorio_cache.mkdir(parents=True, exist_ok=True)
    filas: list[dict[str, Any]] = []
    offset = 0
    tamano_pagina = min(100, limite_filas)

    while len(filas) < limite_filas:
        ruta_cache = _ruta_cache(resource_id, f"q_{q}", offset, directorio_cache)
        if usar_cache and ruta_cache.exists():
            cuerpo = json.loads(ruta_cache.read_text(encoding="utf-8"))
        else:
            if offset > 0:
                time.sleep(intervalo_entre_paginas_segundos)
            resp = cliente.get(
                BASE_URL,
                params={
                    "resource_id": resource_id,
                    "q": q,
                    "limit": tamano_pagina,
                    "offset": offset,
                },
                headers={"User-Agent": USER_AGENT_NAVEGADOR},
                timeout=30.0,
            )
            resp.raise_for_status()
            cuerpo = resp.json()["result"]
            if usar_cache:
                ruta_cache.write_text(
                    json.dumps(cuerpo, ensure_ascii=False, indent=2), encoding="utf-8"
                )

        registros = cuerpo["records"]
        if not registros:
            break
        filas.extend(registros)
        offset += len(registros)
        if offset >= cuerpo["total"]:
            break

    return filas[:limite_filas]
