"""Cierra el catálogo que sirven FastAPI y Angular.

Lee el universo de 13 093 (`dataset_referencia_20260929.parquet`) y las
observaciones REAL del 26 de septiembre. Escribe un Parquet nuevo. No modifica
los archivos de origen, no recalcula D1/D2/D3 y no guarda precios de demostración.

Uso:
    uv run python scripts/cerrar_dataset_operativo.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nutrimatch.engine.operational_dataset import cerrar_dataset_operativo

PROCESADOS = REPO_ROOT / "datos" / "procesados"
ORIGEN = PROCESADOS / "dataset_referencia_20260929.parquet"
OBSERVACIONES = PROCESADOS / "observaciones_20260926.parquet"
DESTINO = PROCESADOS / "dataset_referencia_20261002.parquet"
METADATA = PROCESADOS / "dataset_referencia_20261002_metadata.json"
META_SNAP = REPO_ROOT / "datos" / "snapshots" / "off_csv_20260929" / "_metadata.json"
META_SNAP_19 = REPO_ROOT / "datos" / "snapshots" / "off_csv_20260919" / "_metadata.json"

COLUMNAS_RANKING = (
    "d2",
    "universo_puntuable",
    "percentil_sugars_100g",
    "percentil_salt_100g",
    "percentil_saturated-fat_100g",
    "percentil_fiber_100g",
    "percentil_proteins_100g",
    "categoria_referencia",
)


def log(mensaje: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def _sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _leer(ruta: Path) -> pd.DataFrame:
    if not ruta.exists():
        raise FileNotFoundError(ruta)
    return duckdb.connect().execute(
        f"SELECT * REPLACE (CAST(code AS VARCHAR) AS code) FROM read_parquet('{ruta.as_posix()}')"
    ).df()


def main() -> int:
    log(f"Origen: {ORIGEN.name}")
    base = _leer(ORIGEN)
    observaciones = _leer(OBSERVACIONES)
    n = len(base)
    if base["code"].nunique() != n:
        raise RuntimeError("el origen tiene code duplicado")

    log("Uniendo nombres REAL, precios REAL y calidad. Sin recalcular el ranking.")
    destino = cerrar_dataset_operativo(base, observaciones)
    if len(destino) != n or destino["code"].nunique() != n:
        raise RuntimeError("el cierre cambió el universo")
    for columna in COLUMNAS_RANKING:
        if not destino[columna].equals(base[columna]):
            raise RuntimeError(f"la columna de ranking {columna} cambió")
    for prohibida in ("d1", "d3", "cov", "score_final"):
        if prohibida in destino.columns:
            raise RuntimeError(f"no debe materializarse {prohibida}")
    if int((destino["price_status"] == "SYNTHETIC").sum()) != 0:
        raise RuntimeError("hay precios SYNTHETIC en el Parquet")

    reales = destino.loc[destino["price_status"] == "REAL"]
    conteo = reales.groupby(["price_source", "price_match_method"], dropna=False).size()
    log(f"Precios REAL:\n{conteo.to_string()}")
    nombres_api = int((destino["product_name_source"] == "openfoodfacts_api_producto").sum())
    log(f"Nombres de API integrados: {nombres_api}")
    log(
        "Calidad: "
        + destino["data_quality_level"].value_counts().to_string().replace("\n", " | ")
    )

    if DESTINO.resolve() == ORIGEN.resolve():
        raise RuntimeError("el destino no puede ser el archivo de origen")
    destino.to_parquet(DESTINO, index=False)
    log(f"Escrito {DESTINO.name} ({len(destino):,} × {destino.shape[1]})")

    snap = json.loads(META_SNAP.read_text(encoding="utf-8"))
    snap19 = json.loads(META_SNAP_19.read_text(encoding="utf-8"))
    filtrado = snap["filtrado"]
    metadata = {
        "dataset_id": "dataset_referencia_20261002",
        "generated_at": datetime.now(UTC).isoformat(),
        "n_filas": len(destino),
        "n_columnas": int(destino.shape[1]),
        "universo": "operativo",
        "origen": {
            "parquet": ORIGEN.name,
            "sha256": _sha256(ORIGEN),
            "n_filas": n,
            "nota": "No se modificó. Percentiles, D2 y universo_puntuable se copiaron.",
        },
        "observaciones": OBSERVACIONES.name,
        "sha256": _sha256(DESTINO),
        "candados_ingesta": {
            "fuente": "datos/snapshots/off_csv_20260929/_metadata.json",
            "export_identico_a": "off_csv_20260919",
            "sha256_gzip_20260919": snap19["procedencia"]["sha256"],
            "sha256_gzip_20260929": snap["procedencia"]["sha256"],
            "mismo_gzip": snap19["procedencia"]["sha256"] == snap["procedencia"]["sha256"],
            "filas_solo_pais": filtrado["filas_mexico_pais"],
            "tras_no_alimento": filtrado["filas_tras_categorias"],
            "excluidas_no_alimento": filtrado["filas_mexico_pais"] - filtrado["filas_tras_categorias"],
            "tras_integridad": filtrado["filas_tras_integridad"],
            "excluidas_integridad": filtrado["filas_tras_categorias"] - filtrado["filas_tras_integridad"],
            "tras_identidad": filtrado["filas_tras_identidad"],
            "excluidas_identidad": filtrado["filas_tras_integridad"] - filtrado["filas_tras_identidad"],
            "filas_operativas": filtrado["filas"],
            "nota": (
                "El gzip del 29 de septiembre es el mismo archivo que el del 19. "
                "La baja de 16 851 a 13 093 la producen los tres candados de "
                "scripts/ingesta_off.py (no-alimento, integridad, identidad), no un export nuevo. "
                "Los 13 093 códigos son un subconjunto de los 16 851."
            ),
        },
        "precios": {
            "REAL": int((destino["price_status"] == "REAL").sum()),
            "UNAVAILABLE": int((destino["price_status"] == "UNAVAILABLE").sum()),
            "SYNTHETIC_en_parquet": 0,
            "open_prices_exact_gtin": int(
                ((reales["price_source"] == "open_prices") & (reales["price_match_method"] == "exact_gtin")).sum()
            ),
            "qqp_profeco_text_reviewed": int(
                ((reales["price_source"] == "qqp_profeco") & (reales["price_match_method"] == "text_reviewed")).sum()
            ),
            "nota": (
                "SYNTHETIC no se materializa. La ficha lo emite al responder cuando "
                "price_status es UNAVAILABLE y hay GTIN. QQP no es match por código de barras."
            ),
        },
        "nombres_api": nombres_api,
        "calidad": "DERIVED sobre las 13 093 filas. No entra a D1/D2/D3.",
        "ranking": "Fórmulas no recalculadas. d2 y percentiles iguales al origen del 29.",
    }
    METADATA.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Metadato: {METADATA.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
