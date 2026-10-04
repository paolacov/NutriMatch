"""Piloto de match QQP por texto — Fase B del paso 6b del plan de trabajo.

Lee un CSV ya revisado a mano (columna `revisado`, llenada por Paola con `"correcto"` o
`"incorrecto"` — A35: nunca automático) y materializa **solo** las filas `"correcto"` en un
Parquet nuevo `price_*` (sección D.3 del diagnóstico), con `match_method="text_reviewed"` y
`match_confidence=score/100`.

La incertidumbre vive en el match, no en el precio (A5): PROFECO observó ese precio real en un
establecimiento y una fecha concretos, sea cual sea el `code` de OFF correcto — por eso
`price_status` sigue siendo `"REAL"`, nunca `"estimado"`.

No corre contra datos reales en este corte: la revisión manual (paso previo, solo humano)
todavía no existe. Sus pruebas (`tests/test_materializar_precios_qqp.py`) usan un CSV sintético.

Uso:
    python scripts/materializar_precios_qqp.py --csv datos/procesados/piloto_qqp_candidatos_20260926.csv
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

# Sin GTIN por fila (A5): la referencia a la fuente es al dataset, no a un recurso individual
# como en Open Prices (que sí tiene un `id` de precio por fila).
FUENTE_URL = "https://www.datos.gob.mx/busca/dataset/programa_quien_es_quien_precios_2026"


def log(mensaje: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def cargar_csv_revisado(ruta_csv: Path) -> pd.DataFrame:
    """Lee el CSV de candidatos ya revisado a mano.

    `dtype=str` en `code_candidato` es obligatorio: sin él, pandas infiere BIGINT de una
    columna que parece numérica y borra ceros iniciales en silencio (B15) — `code` es un
    identificador de texto (GTIN), nunca un número. Verificado en vivo el 2026-09-26: 3 de
    los 22 códigos de este mismo CSV perdieron su cero inicial exactamente por esta trampa
    antes de corregirse.
    """
    return pd.read_csv(ruta_csv, dtype={"code_candidato": str})


def construir_tabla_precios(csv_revisado: pd.DataFrame, *, fecha_pull: str) -> pd.DataFrame:
    """Filtra a `revisado == "correcto"` (sin distinguir mayúsculas/espacios) y construye el
    esquema `price_*` (D.3), reusando las columnas de `piloto_precios_open_prices.py` donde
    aplican y dejando `None` (nunca 0, A2) donde QQP no tiene el dato (p. ej. `product_code`,
    `retailer`, `location*`: la Fase A no los capturó en el CSV de candidatos)."""
    ahora = datetime.now(UTC).isoformat()
    revisado_normalizado = csv_revisado["revisado"].astype("string").str.strip().str.lower()
    correctos = csv_revisado[revisado_normalizado == "correcto"]

    filas: list[dict] = []
    for _, fila in correctos.iterrows():
        filas.append(
            {
                "code": fila["code_candidato"],
                "product_code": None,  # QQP no publica GTIN (A5).
                "price": fila["qqp_precio"],
                "currency": "MXN",
                "date_observado": fila["qqp_fecha"],
                "retailer": None,
                "location": None,
                "location_city": None,
                "location_country": None,
                "location_country_code": None,
                "location_lat": None,
                "location_lon": None,
                "source": "qqp_profeco",
                "source_url": FUENTE_URL,
                "match_method": "text_reviewed",
                "match_confidence": round(float(fila["score"]) / 100.0, 4),
                "price_status": "REAL",
                "retrieved_at": ahora,
                "pull_id": f"qqp_{fecha_pull}",
                # Texto original de QQP: trazabilidad de qué se comparó para llegar a este match
                # (A10, "estado de los datos"), no parte del esquema price_* mínimo de D.3.
                "qqp_marca": fila["qqp_marca"],
                "qqp_producto": fila["qqp_producto"],
                "qqp_presentacion": fila["qqp_presentacion"],
            }
        )
    return pd.DataFrame(filas)


def reportar(csv_revisado: pd.DataFrame, resultado: pd.DataFrame) -> None:
    total = len(csv_revisado)
    conteo = csv_revisado["revisado"].astype("string").fillna("").str.strip().str.lower().value_counts()
    log(f"Filas en el CSV revisado: {total}")
    for etiqueta, n in conteo.items():
        log(f"  revisado={etiqueta or '(vacío)'}: {n}")
    log(f"Materializadas (revisado=='correcto'): {len(resultado)}")
    if not resultado.empty:
        log(
            f"  match_confidence: min={resultado['match_confidence'].min():.2f} "
            f"max={resultado['match_confidence'].max():.2f}"
        )
        log(f"  codes únicos: {resultado['code'].nunique()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, help="ruta al CSV ya revisado a mano")
    args = parser.parse_args()

    ruta_csv = Path(args.csv)
    if not ruta_csv.exists():
        log(f"ERROR: no existe {ruta_csv}.")
        return 1

    csv_revisado = cargar_csv_revisado(ruta_csv)
    if "revisado" not in csv_revisado.columns:
        log("ERROR: el CSV no tiene columna 'revisado'.")
        return 1

    revisado_normalizado = csv_revisado["revisado"].astype("string").fillna("").str.strip()
    if revisado_normalizado.eq("").all():
        log(
            "ERROR: la columna 'revisado' está completamente vacía. Falta la revisión manual "
            "(A35): marca cada fila 'correcto'/'incorrecto' antes de correr esta fase."
        )
        return 1

    fecha_pull = time.strftime("%Y%m%d")
    ruta_salida = REPO_ROOT / "datos" / "procesados" / f"precios_qqp_{fecha_pull}.parquet"

    resultado = construir_tabla_precios(csv_revisado, fecha_pull=fecha_pull)
    log("")
    reportar(csv_revisado, resultado)

    if resultado.empty:
        log("")
        log("Ninguna fila marcada 'correcto': no se escribe ningún Parquet.")
        return 0

    resultado.to_parquet(ruta_salida, index=False)
    log("")
    log(f"Escrito: {ruta_salida.relative_to(REPO_ROOT)} ({ruta_salida.stat().st_size:,} bytes)")
    log(
        "El precio no puntúa (A5): no se tocó score_final, D1/D2/D3, cov ni ningún Parquet "
        "existente."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
