"""Pruebas de scripts/confirmar_ranking_v1.py (paso 10, decisión A44)."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from confirmar_ranking_v1 import (
    N_UNIVERSO_PUNTUABLE,
    construir_resumen,
    disponibilidad_para_perfil,
    medir_g1,
    percentiles_d1_de_fila,
)

RUTA_REFERENCIA = REPO_ROOT / "datos" / "procesados" / "dataset_referencia_20260926.parquet"


def _fila_con_percentiles(**kwargs) -> pd.Series:
    base = {f"percentil_{k}": None for k in (
        "sugars_100g",
        "salt_100g",
        "saturated-fat_100g",
        "fiber_100g",
        "proteins_100g",
    )}
    base.update({f"percentil_{k}": v for k, v in kwargs.items()})
    return pd.Series(base)


def test_percentiles_d1_ignora_nan():
    fila = _fila_con_percentiles(sugars_100g=40.0, salt_100g=float("nan"))
    percentiles = percentiles_d1_de_fila(fila)
    assert percentiles["sugars_100g"] == 40.0
    assert percentiles["salt_100g"] is None


def test_medir_g1_sobre_fixture():
    df = pd.DataFrame(
        [
            {
                "percentil_sugars_100g": 10.0,
                "percentil_salt_100g": None,
                "percentil_saturated-fat_100g": None,
                "percentil_fiber_100g": None,
                "percentil_proteins_100g": None,
                "d2": 50.0,
                "universo_puntuable": True,
                "price_status": "REAL",
            },
            {
                "percentil_sugars_100g": None,
                "percentil_salt_100g": None,
                "percentil_saturated-fat_100g": None,
                "percentil_fiber_100g": None,
                "percentil_proteins_100g": None,
                "d2": None,
                "universo_puntuable": False,
                "price_status": "UNAVAILABLE",
            },
        ]
    )

    g1 = medir_g1(df)

    assert g1["n_total"] == 2
    assert g1["n_d1_calculable"] == 1
    assert g1["n_d2_calculable"] == 1
    assert g1["n_universo_puntuable"] == 1
    assert g1["n_price_real"] == 1


def test_disponibilidad_d3_none_si_usuaria_sin_etiquetas():
    df = pd.DataFrame(
        [
            {
                "percentil_sugars_100g": 10.0,
                "percentil_salt_100g": None,
                "percentil_saturated-fat_100g": None,
                "percentil_fiber_100g": None,
                "percentil_proteins_100g": None,
                "d2": 25.0,
                "labels_tags": "en:organic",
            }
        ]
    )

    disponibilidad = disponibilidad_para_perfil(df, [])

    assert disponibilidad["D1"].iloc[0]
    assert disponibilidad["D2"].iloc[0]
    assert not disponibilidad["D3"].iloc[0]


def test_construir_resumen_marca_fallo_si_no_reproduce():
    g1 = {
        "n_total": 16_851,
        "n_d1_calculable": 7_040,
        "n_d2_calculable": 6_781,
        "n_universo_puntuable": 5_864,
        "n_price_real": 0,
    }
    a31 = {
        "Ana": {"n_informacion_insuficiente": 9_517, "causa_dominante": "D1+D2+D3"},
        "Caro": {"n_informacion_insuficiente": 10_974, "causa_dominante": "D1+D2+D3"},
    }

    resumen = construir_resumen(g1, a31)

    assert not resumen.loc[resumen["metrica"] == "n_price_real", "ok"].iloc[0]
    assert resumen.loc[resumen["metrica"] == "n_universo_puntuable", "ok"].iloc[0]


@pytest.mark.skipif(not RUTA_REFERENCIA.exists(), reason="falta dataset_referencia")
def test_universo_puntuable_del_dataset_referencia_es_5864():
    n = duckdb.execute(
        f"SELECT SUM(CAST(universo_puntuable AS INTEGER)) "
        f"FROM read_parquet('{RUTA_REFERENCIA.as_posix()}')"
    ).fetchone()[0]
    assert int(n) == N_UNIVERSO_PUNTUABLE
