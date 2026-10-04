"""Experimento de recuperación de nombres por EAN — paso 4 del plan de trabajo.

Ver `docs/diagnostico_calidad_datos.md` (sección H, paso 4) y la decisión A37 (punto 4) de
`AGENTS.md`. Pregunta que responde: de los productos que quedaron **sin ningún nombre** tras
homologar (paso 3, `product_name_status = "UNAVAILABLE"` en `identidad_homologada_20260919.parquet`,
1.685 códigos), ¿cuántos sí tienen nombre en la ficha **viva** de la API de Open Food Facts, que a
veces trae más dato que el export CSV usado para el snapshot?

Deliberadamente acotado (A37, B4-B5, AGENTS.md):

- Muestra de 50-100 códigos (por defecto 80), **no** los 1.685 completos: es un experimento para
  decidir si vale la pena un enriquecimiento mayor, no una descarga masiva.
- Un `code` a la vez contra `world.openfoodfacts.org` (producción, nunca staging — B1), respetando
  el límite de 15 peticiones/minuto y con reintentos acotados ante el 503 anti-crawl (B4).
- Un nombre recuperado aquí es **REAL de esa fuente** (la API viva), no un overwrite del export:
  se guarda en un Parquet nuevo, separado de `identidad_homologada_20260919.parquet`.

Uso:
    python scripts/experimento_recuperacion_nombres.py                  # muestra de 80, caché activa
    python scripts/experimento_recuperacion_nombres.py --n 50 --seed 7  # otra muestra reproducible
    python scripts/experimento_recuperacion_nombres.py --no-cache       # repite todas las peticiones
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import httpx
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nutrimatch.engine.identity_homologation import resolver_nombre_homologado
from nutrimatch.providers.off_product_api import (
    DIR_CACHE_POR_DEFECTO,
    INTERVALO_MINIMO_SEGUNDOS,
    USER_AGENT,
    LimitadorDeTasa,
    obtener_producto,
)

SEMILLA_POR_DEFECTO = 20260926  # fecha de esta decisión (A37), no un número arbitrario.
TAMANO_MUESTRA_POR_DEFECTO = 80  # dentro del rango 50-100 que fija A37/H.


def log(mensaje: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def cargar_codigos_sin_nombre(ruta_identidad: Path) -> list[str]:
    con = duckdb.connect()
    codigos = con.execute(
        f"""
        SELECT code FROM '{ruta_identidad.as_posix()}'
        WHERE product_name_status = 'UNAVAILABLE'
        ORDER BY code
        """
    ).df()["code"].tolist()
    return codigos


def ejecutar_experimento(codigos_muestra: list[str], *, usar_cache: bool) -> pd.DataFrame:
    limitador = LimitadorDeTasa(INTERVALO_MINIMO_SEGUNDOS)
    filas: list[dict] = []
    ahora = datetime.now(UTC).isoformat()

    with httpx.Client() as cliente:
        for i, code in enumerate(codigos_muestra, start=1):
            respuesta = obtener_producto(
                code, cliente=cliente, limitador=limitador, usar_cache=usar_cache
            )

            nombre_recuperado: str | None = None
            campo_usado: str | None = None
            placeholder_en_api = False
            if respuesta.resultado == "encontrado":
                nombre_recuperado, campo_usado, placeholder_en_api = resolver_nombre_homologado(
                    respuesta.product_name,
                    respuesta.generic_name,
                    respuesta.abbreviated_product_name,
                )

            es_hit = nombre_recuperado is not None
            filas.append(
                {
                    "code": code,
                    "resultado_api": respuesta.resultado,
                    "http_status": respuesta.http_status,
                    "desde_cache": respuesta.desde_cache,
                    "intentos": respuesta.intentos,
                    "product_name_api": respuesta.product_name,
                    "generic_name_api": respuesta.generic_name,
                    "abbreviated_product_name_api": respuesta.abbreviated_product_name,
                    "brands_api": respuesta.brands,
                    "nombre_recuperado": nombre_recuperado,
                    "campo_usado": campo_usado,
                    "placeholder_tambien_en_api": placeholder_en_api,
                    "es_hit": es_hit,
                    "source": "openfoodfacts_api_producto",
                    "source_url": f"https://world.openfoodfacts.org/api/v2/product/{code}.json",
                    "retrieved_at": ahora,
                    "status_valor": "REAL" if es_hit else "UNAVAILABLE",
                }
            )

            marca = "HIT" if es_hit else respuesta.resultado.upper()
            origen = " (caché)" if respuesta.desde_cache else ""
            log(f"  [{i}/{len(codigos_muestra)}] {code}: {marca}{origen}")

    return pd.DataFrame(filas)


def reportar(resultado: pd.DataFrame) -> None:
    n = len(resultado)
    encontrados_api = (resultado["resultado_api"] == "encontrado").sum()
    hits = resultado["es_hit"].sum()
    placeholder_en_api = resultado["placeholder_tambien_en_api"].sum()
    errores_anticrawl = (resultado["resultado_api"] == "error_anticrawl").sum()
    errores_otro = (resultado["resultado_api"] == "error_otro").sum()
    no_encontrados = (resultado["resultado_api"] == "no_encontrado").sum()
    desde_cache = resultado["desde_cache"].sum()

    log(f"Muestra: {n}")
    log(f"  encontrados en la API viva: {encontrados_api} ({encontrados_api / n:.1%})")
    log(f"  con nombre recuperable (hit): {hits} ({hits / n:.1%})")
    log(f"  placeholder 'Cargando…' también en la API: {placeholder_en_api}")
    log(f"  no encontrados en la API (code inexistente ahí): {no_encontrados}")
    log(f"  error anti-crawl (503/429 tras agotar reintentos): {errores_anticrawl}")
    log(f"  error de otro tipo: {errores_otro}")
    log(f"  resueltos desde caché local (sin petición nueva): {desde_cache}")
    log("")
    if hits / n >= 0.20:
        log("  Lectura: tasa de hit >= 20% -> parece defendible ampliar la muestra o el universo.")
    else:
        log("  Lectura: tasa de hit < 20% -> el enriquecimiento por API no rinde lo suficiente")
        log("    para justificar ampliar el experimento sin revisar la causa primero.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fecha", default="20260919", help="fecha del snapshot (ej. 20260919)")
    parser.add_argument("--n", type=int, default=TAMANO_MUESTRA_POR_DEFECTO, help="tamaño de muestra")
    parser.add_argument("--seed", type=int, default=SEMILLA_POR_DEFECTO, help="semilla de muestreo")
    parser.add_argument("--no-cache", action="store_true", help="ignora la caché local en disco")
    args = parser.parse_args()

    ruta_identidad = REPO_ROOT / "datos" / "procesados" / f"identidad_homologada_{args.fecha}.parquet"
    ruta_salida = (
        REPO_ROOT
        / "datos"
        / "procesados"
        / f"experimento_recuperacion_nombres_{args.fecha}.parquet"
    )

    if not ruta_identidad.exists():
        log(f"ERROR: no existe {ruta_identidad}. Corre `make homologar-identidad` primero.")
        return 1

    log(f"Leyendo {ruta_identidad.relative_to(REPO_ROOT)}")
    codigos_sin_nombre = cargar_codigos_sin_nombre(ruta_identidad)
    log(f"Códigos sin ningún nombre tras homologar: {len(codigos_sin_nombre):,}")

    n = min(args.n, len(codigos_sin_nombre))
    muestra = random.Random(args.seed).sample(codigos_sin_nombre, n)
    log(f"Muestra: {n} códigos (semilla {args.seed}, reproducible)")

    usar_cache = not args.no_cache
    log(f"Caché local: {'activa' if usar_cache else 'desactivada'} ({DIR_CACHE_POR_DEFECTO.relative_to(REPO_ROOT)})")
    log(f"User-Agent: {USER_AGENT}")
    log(f"Espaciado mínimo entre peticiones: {INTERVALO_MINIMO_SEGUNDOS}s (~{60 / INTERVALO_MINIMO_SEGUNDOS:.1f}/min, límite OFF: 15/min)")
    log("Consultando world.openfoodfacts.org (producción) un code a la vez...")

    resultado = ejecutar_experimento(muestra, usar_cache=usar_cache)

    log("")
    reportar(resultado)

    resultado.to_parquet(ruta_salida, index=False)
    log(f"Escrito: {ruta_salida.relative_to(REPO_ROOT)} ({ruta_salida.stat().st_size:,} bytes)")
    log("Crudo y `identidad_homologada` intactos: no se sobrescribió ningún Parquet existente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
