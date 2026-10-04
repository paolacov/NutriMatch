"""Las figuras describen el marco recibido y no aceptan un universo inconsistente."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import pandas as pd

from nutrimatch.eda.figures import FIGURAS, catalogo


def _marco() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": ["1", "2", "3", "4", "5"],
            "d2": [80.0, 40.0, None, 10.0, None],
            "n_percentiles_validos": [6, 5, 5, 2, 1],
            "universo_puntuable": [True, True, False, False, False],
            "price_status": ["REAL", "REAL", "UNAVAILABLE", "UNAVAILABLE", "UNAVAILABLE"],
            "price_source": ["open_prices", "qqp_profeco", None, None, None],
            "data_quality_level": ["alta", "media", "baja", "insuficiente", "alta"],
            "sugars_100g_saneado": [1.0, 8.0, 3.0, None, None],
            "salt_100g_saneado": [0.1, 1.2, 0.3, None, None],
            "saturated-fat_100g_saneado": [1.0, 9.0, 8.0, None, None],
            "fiber_100g_saneado": [2.0, 0.4, 0.0, None, None],
            "proteins_100g_saneado": [5.0, 12.0, 3.0, None, None],
            "percentil_saturated-fat_100g": [20.0, 70.0, None, None, None],
        }
    )


def test_el_catalogo_cubre_eda_e_ingenieria():
    figuras = catalogo(_marco(), dataset_id="fixture")
    assert set(figuras) == set(FIGURAS)
    assert any(nombre.startswith("eda_") for nombre in figuras)
    assert any(nombre.startswith("ingenieria_") for nombre in figuras)


def test_universo_puntuable_inconsistente_se_rechaza():
    marco = _marco()
    marco.loc[0, "universo_puntuable"] = False
    try:
        catalogo(marco, dataset_id="fixture")
    except ValueError as error:
        assert "A22" in str(error)
    else:
        raise AssertionError("se esperaba un rechazo")
