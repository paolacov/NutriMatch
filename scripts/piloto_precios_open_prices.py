"""Piloto de precios REALES: materializar Open Prices — paso 6a del plan de trabajo.

Ver `docs/diagnostico_calidad_datos.md` (sección H, fila 6, parte a) y la decisión A35 de
`AGENTS.md`. Descarga los precios en MXN de Open Prices (`prices.openfoodfacts.org`, ODbL) y
cruza su `product_code` (GTIN) contra el universo México de 16.851 productos. Construye un
Parquet **nuevo**, siguiendo el esquema `price_*` de la sección D.3 del diagnóstico.

Deliberadamente acotado (A35):

- Solo Open Prices, solo `currency=MXN` — no un dump masivo ni un cruce con QQP (QQP no publica
  GTIN, A5; su piloto de match por texto es un paso aparte, no éste).
- El precio **no puntúa** (A5): este script no toca `score_final`, D1/D2/D3, `cov`, bandas de
  ranking ni ningún Parquet ya existente (`off_mexico_*.parquet`,
  `identidad_homologada_*.parquet`).
- Cada fila resultante es una **observación** REAL (A33): un mismo `code` puede tener varias
  filas (varias observaciones de precio en fechas o establecimientos distintos son válidas). No
  se colapsa a una sola fila por producto aquí; esa regla de "cuál se muestra" es un paso de la
  ficha, no de esta materialización.

Uso:
    python scripts/piloto_precios_open_prices.py                # pull completo, caché activa
    python scripts/piloto_precios_open_prices.py --no-cache      # repite todas las peticiones
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import httpx
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nutrimatch.providers.open_prices_api import obtener_precios_por_moneda

MONEDA_OBJETIVO = "MXN"  # Único mercado de este piloto: precios ya denominados en pesos mexicanos.


def log(mensaje: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def cargar_universo_mexico(ruta_off: Path) -> set[str]:
    con = duckdb.connect()
    return set(con.execute(f"SELECT code FROM '{ruta_off.as_posix()}'").df()["code"].tolist())


def construir_tabla_precios(precios, universo: set[str], *, fecha_pull: str) -> pd.DataFrame:
    """Filtra a los que cruzan con el universo y construye el esquema `price_*` (D.3)."""
    ahora = datetime.now(UTC).isoformat()
    filas: list[dict] = []
    for p in precios:
        if p.product_code not in universo:
            continue
        location_partes = [parte for parte in (p.location_city, p.location_country) if parte]
        filas.append(
            {
                "code": p.product_code,
                "product_code": p.product_code,
                "price": p.price,
                "currency": p.currency,
                "date_observado": p.date,
                "retailer": p.retailer,
                "location": ", ".join(location_partes) or None,
                "location_city": p.location_city,
                "location_country": p.location_country,
                "location_country_code": p.location_country_code,
                "location_lat": p.location_lat,
                "location_lon": p.location_lon,
                "source": "open_prices",
                "source_url": p.source_url,
                "match_method": "exact_gtin",
                "match_confidence": None,
                "price_status": "REAL",
                "retrieved_at": ahora,
                "pull_id": f"open_prices_{fecha_pull}",
            }
        )
    return pd.DataFrame(filas)


def reportar(precios_totales: int, codigos_unicos_api: int, resultado: pd.DataFrame) -> None:
    log(f"Precios en {MONEDA_OBJETIVO} descargados de Open Prices: {precios_totales}")
    log(f"  códigos de producto únicos entre esos: {codigos_unicos_api}")
    log(f"Filas que cruzan con el universo México (16.851): {len(resultado)}")
    if resultado.empty:
        return
    codigos_cruzan = resultado["code"].nunique()
    log(f"  códigos únicos que cruzan: {codigos_cruzan} ({codigos_cruzan / 16_851:.1%} del universo)")
    log(f"  moneda: 100% {resultado['currency'].unique().tolist()}")
    log(f"  rango de precio: ${resultado['price'].min():.2f} – ${resultado['price'].max():.2f} MXN")
    fechas_validas = resultado["date_observado"].dropna()
    if not fechas_validas.empty:
        log(f"  rango de fecha observada: {fechas_validas.min()} – {fechas_validas.max()}")
    log(f"  price_status: {resultado['price_status'].unique().tolist()} (100% REAL, A33)")
    log("  muestra:")
    muestra = resultado[["code", "price", "currency", "retailer", "location", "date_observado"]].head(5)
    for _, fila in muestra.iterrows():
        log(f"    {fila['code']}: ${fila['price']:.2f} {fila['currency']} · {fila['retailer']} · {fila['location']} · {fila['date_observado']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fecha-off", default="20260919", help="fecha del snapshot México (ej. 20260919)")
    parser.add_argument("--no-cache", action="store_true", help="ignora la caché local en disco")
    args = parser.parse_args()

    # Fecha local (vía `time`, no `datetime.now()` naive), no UTC: es la fecha "citable" que usa
    # el resto del proyecto en AGENTS.md (p. ej. "medido el 2026-09-26"). `retrieved_at` sigue en
    # UTC para trazabilidad de máquina.
    fecha_pull = time.strftime("%Y%m%d")
    ruta_off = REPO_ROOT / "datos" / "procesados" / f"off_mexico_{args.fecha_off}.parquet"
    ruta_salida = REPO_ROOT / "datos" / "procesados" / f"precios_open_prices_{fecha_pull}.parquet"

    if not ruta_off.exists():
        log(f"ERROR: no existe {ruta_off}. Corre `make ingest-off` primero.")
        return 1

    log(f"Leyendo universo México: {ruta_off.relative_to(REPO_ROOT)}")
    universo = cargar_universo_mexico(ruta_off)
    log(f"Universo: {len(universo):,} códigos")

    usar_cache = not args.no_cache
    log(f"Descargando precios {MONEDA_OBJETIVO} de Open Prices (caché: {'activa' if usar_cache else 'desactivada'})")
    with httpx.Client() as cliente:
        precios = obtener_precios_por_moneda(MONEDA_OBJETIVO, cliente=cliente, usar_cache=usar_cache)

    codigos_unicos_api = len({p.product_code for p in precios if p.product_code})
    resultado = construir_tabla_precios(precios, universo, fecha_pull=fecha_pull)

    log("")
    reportar(len(precios), codigos_unicos_api, resultado)

    resultado.to_parquet(ruta_salida, index=False)
    log("")
    log(f"Escrito: {ruta_salida.relative_to(REPO_ROOT)} ({ruta_salida.stat().st_size:,} bytes)")
    log("El precio no puntúa (A5): no se tocó score_final, D1/D2/D3, cov ni ningún Parquet existente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
