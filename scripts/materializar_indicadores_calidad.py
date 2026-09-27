"""Materializa indicadores DERIVED de calidad en un Parquet nuevo.

Lee `dataset_referencia_20260926.parquet` y escribe `dataset_referencia_<fecha>.parquet`
sin modificar el archivo de origen. No imputa, no sintetiza, no toca D1/D2/D3/`cov`/score.

Uso:
    uv run python scripts/materializar_indicadores_calidad.py
    uv run python scripts/materializar_indicadores_calidad.py --fecha 20260927
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nutrimatch.engine.data_quality import (
    COLUMNAS_CALIDAD,
    _es_nulo,
    anexar_indicadores_calidad,
)
from nutrimatch.engine.nutrition_score import NUTRIENTES_D1_SIGNO, calcular_subpuntaje_d1

PROCESADOS = REPO_ROOT / "datos" / "procesados"
REFERENCIA_ORIGEN = PROCESADOS / "dataset_referencia_20260926.parquet"
COLUMNAS_NO_MATERIALIZADAS = ("d1", "d3", "cov", "score_final")


def log(mensaje: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def _sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _leer_parquet(ruta: Path) -> pd.DataFrame:
    if not ruta.exists():
        raise FileNotFoundError(ruta)
    return duckdb.connect().execute(f"SELECT * FROM read_parquet('{ruta.as_posix()}')").df()


def _es_cero_numerico(serie: pd.Series) -> pd.Series:
    numerica = pd.to_numeric(serie, errors="coerce")
    return numerica.eq(0) & serie.notna()


def _n_d1_calculable(frame: pd.DataFrame) -> int:
    n = 0
    for fila in frame.to_dict(orient="records"):
        percentiles = {nut: fila.get(f"percentil_{nut}") for nut in NUTRIENTES_D1_SIGNO}
        d1, _detalle = calcular_subpuntaje_d1(percentiles)
        if d1 is not None:
            n += 1
    return n


def _contar_nulos(serie: pd.Series) -> int:
    return int(sum(_es_nulo(v) for v in serie.tolist()))


def _columnas_equivalentes(antes: pd.Series, despues: pd.Series) -> bool:
    """Misma máscara de nulos y mismos valores; no caste a float un texto (p. ej. nombre 'NAN')."""
    if len(antes) != len(despues):
        return False
    av = antes.tolist()
    bv = despues.tolist()
    for x, y in zip(av, bv, strict=True):
        xn, yn = _es_nulo(x), _es_nulo(y)
        if xn and yn:
            continue
        if xn or yn:
            return False
        if isinstance(x, bool) or isinstance(y, bool):
            if bool(x) != bool(y):
                return False
            continue
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            if float(x) != float(y):
                return False
            continue
        if str(x) != str(y):
            return False
    return True


def validar_antes_despues(origen: pd.DataFrame, destino: pd.DataFrame) -> pd.DataFrame:
    """Compara origen vs destino. Lanza si se alteró algo que no sea calidad DERIVED."""
    filas: list[dict[str, Any]] = []

    def _fila(indicador: str, antes: Any, despues: Any, ok_esperada: bool | None = None) -> None:
        diferencia: Any
        if isinstance(antes, (int, float)) and isinstance(despues, (int, float)):
            diferencia = despues - antes
        elif antes == despues:
            diferencia = 0
        else:
            diferencia = "distinto"
        ok = (antes == despues) if ok_esperada is None else ok_esperada
        filas.append(
            {
                "indicador": indicador,
                "antes": antes,
                "despues": despues,
                "diferencia": diferencia,
                "ok": ok,
            }
        )

    _fila("n_filas", len(origen), len(destino))
    _fila("n_columnas", len(origen.columns), len(destino.columns), ok_esperada=len(destino.columns) == len(origen.columns) + len(COLUMNAS_CALIDAD))
    _fila("n_columnas_nuevas", 0, len(COLUMNAS_CALIDAD), ok_esperada=True)

    codes_origen = origen["code"].astype(str)
    codes_destino = destino["code"].astype(str)
    _fila("n_code_unicos", int(codes_origen.nunique()), int(codes_destino.nunique()))
    _fila("n_duplicados_code", int(len(origen) - codes_origen.nunique()), int(len(destino) - codes_destino.nunique()))
    mismos_codes = set(codes_origen) == set(codes_destino) and list(codes_origen) == list(codes_destino)
    _fila("mismos_gtin_mismo_orden", True, mismos_codes, ok_esperada=mismos_codes)

    columnas_nuevas = [c for c in destino.columns if c not in origen.columns]
    columnas_perdidas = [c for c in origen.columns if c not in destino.columns]
    _fila("columnas_perdidas", 0, len(columnas_perdidas), ok_esperada=len(columnas_perdidas) == 0)
    _fila(
        "columnas_nuevas",
        "",
        ",".join(columnas_nuevas),
        ok_esperada=columnas_nuevas == list(COLUMNAS_CALIDAD),
    )

    n_columnas_alteradas = 0
    n_nulos_origen = 0
    n_nulos_destino_viejas = 0
    n_ceros_origen = 0
    n_ceros_destino = 0
    for col in origen.columns:
        n_nulos_origen += _contar_nulos(origen[col])
        n_nulos_destino_viejas += _contar_nulos(destino[col])
        n_ceros_origen += int(_es_cero_numerico(origen[col]).sum())
        n_ceros_destino += int(_es_cero_numerico(destino[col]).sum())
        if not _columnas_equivalentes(origen[col], destino[col]):
            n_columnas_alteradas += 1
    _fila("columnas_existentes_alteradas", 0, n_columnas_alteradas)
    _fila("n_nulos_columnas_originales", n_nulos_origen, n_nulos_destino_viejas)
    _fila("n_ceros_columnas_originales", n_ceros_origen, n_ceros_destino)

    _fila("universo_puntuable_true", int(origen["universo_puntuable"].sum()), int(destino["universo_puntuable"].sum()))
    _fila("d2_no_nulo", int(origen["d2"].notna().sum()), int(destino["d2"].notna().sum()))
    _fila("n_d1_calculable", _n_d1_calculable(origen), _n_d1_calculable(destino))

    for col in COLUMNAS_NO_MATERIALIZADAS:
        en_origen = col in origen.columns
        en_destino = col in destino.columns
        _fila(f"{col}_en_parquet", en_origen, en_destino, ok_esperada=(not en_origen) and (not en_destino))

    _fila("price_real", int((origen["price_status"] == "REAL").sum()), int((destino["price_status"] == "REAL").sum()))
    _fila("price_unavailable", int((origen["price_status"] == "UNAVAILABLE").sum()), int((destino["price_status"] == "UNAVAILABLE").sum()))
    _fila(
        "price_source_valores",
        ",".join(sorted(origen["price_source"].dropna().astype(str).unique())),
        ",".join(sorted(destino["price_source"].dropna().astype(str).unique())),
    )

    n_synthetic = 0
    for col in COLUMNAS_CALIDAD:
        if destino[col].astype(str).str.contains("SYNTHETIC", na=False).any():
            n_synthetic += 1
    _fila("columnas_calidad_con_synthetic", 0, n_synthetic)
    _fila("data_quality_score_nulos", 0, int(destino["data_quality_score"].isna().sum()))
    _fila("data_quality_level_nulos", 0, int(destino["data_quality_level"].isna().sum()))

    reporte = pd.DataFrame(filas)
    fallos = reporte.loc[~reporte["ok"]]
    if not fallos.empty:
        raise ValueError(f"validación fallida:\n{fallos.to_string(index=False)}")
    return reporte


def escribir_metadata(
    ruta: Path,
    *,
    origen: Path,
    n_filas: int,
    n_columnas: int,
    sha256_origen: str,
    sha256_destino: str,
) -> None:
    metadata = {
        "dataset_id": ruta.name.replace("_metadata.json", ""),
        "generated_at": datetime.now(UTC).isoformat(),
        "n_filas": n_filas,
        "n_columnas": n_columnas,
        "origen": {
            "parquet": origen.name,
            "sha256": sha256_origen,
            "n_columnas": 267,
        },
        "sha256": sha256_destino,
        "columnas_nuevas": list(COLUMNAS_CALIDAD),
        "procedencia_columnas_nuevas": "DERIVED",
        "fuentes_reutilizadas": [
            "n_percentiles_validos",
            "ingredients_text",
            "categoria_referencia",
            "nova_group",
            "additives_n",
            "labels_tags",
            "*_100g_flag_fuera_de_rango",
            "flag_suma_macros_excede_100",
        ],
        "nota": (
            "Copia del dataset de referencia 20260926 más tres columnas DERIVED de calidad "
            "de información. No hay SYNTHETIC ni IMPUTED. El Parquet 20260926 no se modificó. "
            "D1/D2/D3/cov/score no se recalcularon ni se persistieron."
        ),
        "fuera_de_alcance": (
            "No se tocó engine/*_score.py, services/catalog.py, services/ranking.py ni Angular."
        ),
    }
    ruta.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fecha", default=time.strftime("%Y%m%d"))
    parser.add_argument(
        "--origen",
        default=str(REFERENCIA_ORIGEN),
        help="Parquet de referencia que no se sobrescribe.",
    )
    args = parser.parse_args()

    ruta_origen = Path(args.origen)
    if not ruta_origen.is_absolute():
        ruta_origen = REPO_ROOT / ruta_origen
    if ruta_origen.name != "dataset_referencia_20260926.parquet":
        log("ADVERTENCIA: el origen no es dataset_referencia_20260926.parquet.")

    ruta_destino = PROCESADOS / f"dataset_referencia_{args.fecha}.parquet"
    if ruta_destino.resolve() == ruta_origen.resolve():
        log("ERROR: el destino no puede ser el Parquet de origen.")
        return 1

    ruta_metadata = PROCESADOS / f"dataset_referencia_{args.fecha}_metadata.json"
    ruta_reporte = PROCESADOS / f"validacion_indicadores_calidad_{args.fecha}.csv"

    log(f"Hash origen antes: {ruta_origen}")
    sha_antes = _sha256(ruta_origen)
    log(f"  sha256={sha_antes}")

    log("Leyendo origen (DuckDB)...")
    origen = _leer_parquet(ruta_origen)
    log(f"  {len(origen):,} filas × {len(origen.columns)} columnas")

    log("Anexando indicadores DERIVED de calidad...")
    destino = anexar_indicadores_calidad(origen)

    log("Validando antes/después (en memoria, antes de escribir)...")
    reporte = validar_antes_despues(origen, destino)
    log(f"  {len(reporte)} indicadores, todos ok")

    destino.to_parquet(ruta_destino, index=False)
    sha_despues_origen = _sha256(ruta_origen)
    if sha_despues_origen != sha_antes:
        raise RuntimeError("el Parquet de origen cambió al escribir el nuevo archivo")
    sha_destino = _sha256(ruta_destino)

    log("Releyendo destino y revalidando...")
    destino_disco = _leer_parquet(ruta_destino)
    reporte_disco = validar_antes_despues(origen, destino_disco)
    reporte_disco.to_csv(ruta_reporte, index=False)

    escribir_metadata(
        ruta_metadata,
        origen=ruta_origen,
        n_filas=len(destino_disco),
        n_columnas=len(destino_disco.columns),
        sha256_origen=sha_antes,
        sha256_destino=sha_destino,
    )

    log("")
    log(f"Origen intacto: {ruta_origen.relative_to(REPO_ROOT)} sha256={sha_antes}")
    log(f"Escrito: {ruta_destino.relative_to(REPO_ROOT)} ({ruta_destino.stat().st_size:,} bytes)")
    log(f"Escrito: {ruta_metadata.relative_to(REPO_ROOT)}")
    log(f"Escrito: {ruta_reporte.relative_to(REPO_ROOT)}")
    log(
        "Niveles: "
        + ", ".join(
            f"{nivel}={int((destino_disco['data_quality_level'] == nivel).sum())}"
            for nivel in ("alta", "media", "baja", "insuficiente")
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
