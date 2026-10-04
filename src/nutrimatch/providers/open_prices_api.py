"""Cliente de lectura de la API pública de **Open Prices** (`prices.openfoodfacts.org`).

Piloto de precios REALES (paso 6a del plan de trabajo, decisión A35): materializar los precios
MXN de Open Prices que ya cruzan por `product_code` (GTIN) con el universo México. Este módulo
solo lee; Open Prices también acepta escritura de precios pero eso no es parte de NutriMatch.

Contrato de la API, **verificado en vivo el 2026-09-26** (no estaba documentado en este repo
antes de este módulo — la única referencia previa era una "sonda" ad-hoc sin código persistido,
citada en A35/`docs/diagnostico_calidad_datos.md` sección D):

- Endpoint: `GET https://prices.openfoodfacts.org/api/v1/prices`.
- El filtro `location_country_code` **no existe** en `PriceFilter` (verificado leyendo
  `open_prices/api/prices/filters.py` del repo de Open Prices): django-filter ignora en
  silencio cualquier parámetro no reconocido, así que un query con ese nombre devuelve
  resultados **sin filtrar** en vez de fallar — una trampa real, no hipotética (se comprobó:
  devolvía una fila de Francia con ese parámetro puesto a `"mx"`).
- El filtro correcto para este piloto es **`currency=MXN`** (`currency` sí es un campo exacto de
  `PriceFilter`). Verificado: da **346** resultados totales, de los cuales **340** tienen
  `location.osm_address_country_code == "MX"` y **276** códigos de producto únicos — cifras
  idénticas a las de la sonda citada en A35, medidas de nuevo el mismo día.
- Paginación: `size` (máx. 100, por `CustomPagination` del backend) y `page` (base 1). La
  respuesta trae `items`, `page`, `pages`, `size`, `total` (no `next`/`previous`).
- No se observó ningún header de límite de tasa ni ningún `429`/`503` al pedir las 4 páginas
  necesarias para las 346 filas con un espaciado de 0,5 s — a diferencia de la API de producto
  de OFF (B4), esta API no tiene (o no expone) el mismo límite anti-crawl. Se mantiene un
  espaciado prudente de todos modos, por cortesía, no porque se haya medido un límite real.
- Item relevante trae: `id`, `price`, `currency`, `date`, `product_code`, y un objeto `location`
  con `osm_name` (nombre del establecimiento), `osm_address_city`, `osm_address_country`,
  `osm_address_country_code`, `osm_lat`/`osm_lon`.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from nutrimatch.providers.off_product_api import USER_AGENT

BASE_URL = "https://prices.openfoodfacts.org/api/v1/prices"

# Máximo permitido por `CustomPagination.max_page_size` del backend de Open Prices (verificado
# en vivo el 2026-09-26 leyendo `open_prices/api/pagination.py`).
TAMANO_PAGINA = 100

# Cortesía, no un límite medido (ver docstring del módulo): no se observó 429/503 en la prueba
# real con 4 páginas espaciadas 0,5 s, pero un espaciado algo mayor no cuesta nada en un piloto
# de unas pocas páginas.
INTERVALO_ENTRE_PAGINAS_SEGUNDOS = 1.0

REPO_ROOT = Path(__file__).resolve().parents[3]
DIR_CACHE_POR_DEFECTO = REPO_ROOT / "datos" / "cache" / "open_prices_api"


@dataclass(frozen=True)
class PrecioOpenPrices:
    """Una fila de precio de Open Prices, ya aplanada (sin el anidamiento del JSON crudo)."""

    price_id: int
    product_code: str
    price: float
    currency: str
    date: str | None
    retailer: str | None
    location_city: str | None
    location_country: str | None
    location_country_code: str | None
    location_lat: float | None
    location_lon: float | None
    source_url: str


def _ruta_cache_pagina(pagina: int, filtro: str, directorio_cache: Path) -> Path:
    return directorio_cache / f"{filtro}_pagina_{pagina}.json"


def _parsear_item(item: dict[str, Any]) -> PrecioOpenPrices:
    ubicacion = item.get("location") or {}
    return PrecioOpenPrices(
        price_id=item["id"],
        product_code=item.get("product_code") or "",
        price=item["price"],
        currency=item["currency"],
        date=item.get("date"),
        retailer=ubicacion.get("osm_name"),
        location_city=ubicacion.get("osm_address_city"),
        location_country=ubicacion.get("osm_address_country"),
        location_country_code=ubicacion.get("osm_address_country_code"),
        location_lat=ubicacion.get("osm_lat"),
        location_lon=ubicacion.get("osm_lon"),
        source_url=f"{BASE_URL}/{item['id']}",
    )


def obtener_precios_por_moneda(
    currency: str,
    *,
    cliente: httpx.Client,
    directorio_cache: Path = DIR_CACHE_POR_DEFECTO,
    usar_cache: bool = True,
    intervalo_entre_paginas_segundos: float = INTERVALO_ENTRE_PAGINAS_SEGUNDOS,
) -> list[PrecioOpenPrices]:
    """Descarga **todas** las páginas de precios con `currency` exacto, paginando `size=100`.

    Cachea cada página como JSON en disco (`datos/cache/open_prices_api/`, no versionada) para
    que repetir el piloto no repita peticiones ya hechas. No hay reintento ante error HTTP:
    si la API falla a media descarga, se prefiere que la excepción suba y el piloto se detenga
    en vez de reportar un total parcial como si fuera completo.
    """
    directorio_cache.mkdir(parents=True, exist_ok=True)
    resultados: list[PrecioOpenPrices] = []
    pagina = 1
    total_paginas: int | None = None

    while total_paginas is None or pagina <= total_paginas:
        ruta_cache = _ruta_cache_pagina(pagina, currency, directorio_cache)
        if usar_cache and ruta_cache.exists():
            cuerpo = json.loads(ruta_cache.read_text(encoding="utf-8"))
        else:
            if pagina > 1:
                time.sleep(intervalo_entre_paginas_segundos)
            resp = cliente.get(
                BASE_URL,
                params={"currency": currency, "size": TAMANO_PAGINA, "page": pagina},
                headers={"User-Agent": USER_AGENT},
                timeout=20.0,
            )
            resp.raise_for_status()
            cuerpo = resp.json()
            if usar_cache:
                ruta_cache.write_text(
                    json.dumps(cuerpo, ensure_ascii=False, indent=2), encoding="utf-8"
                )

        total_paginas = cuerpo["pages"]
        resultados.extend(_parsear_item(item) for item in cuerpo["items"])
        pagina += 1

    return resultados
