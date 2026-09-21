"""Pruebas de regresión del golden set (decisión A8/A29) contra el snapshot real committeado.

A diferencia del resto de `tests/`, este archivo SÍ lee datos reales: `datos/procesados/*.parquet`
está versionado (ver `.gitignore`) precisamente para que este tipo de prueba sea reproducible sin
depender de una descarga ni de una ejecución previa del pipeline de ingesta/transformación.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from evaluacion.golden_set import CASOS, evaluar

RAIZ = Path(__file__).resolve().parents[1]
RUTA_MATRIZ = RAIZ / "datos" / "procesados" / "matriz_nut_100g_20260919.parquet"
RUTA_SNAPSHOT_CRUDO = RAIZ / "datos" / "procesados" / "off_mexico_20260919.parquet"


def _existen_los_parquets() -> bool:
    return RUTA_MATRIZ.exists() and RUTA_SNAPSHOT_CRUDO.exists()


@pytest.fixture(scope="module")
def df_evaluacion() -> pd.DataFrame:
    matriz = duckdb.execute(f"SELECT * FROM '{RUTA_MATRIZ.as_posix()}'").df()
    crudo = duckdb.execute(
        f"""
        SELECT
            code,
            product_name AS product_name_bruto,
            generic_name,
            abbreviated_product_name,
            labels_tags,
            allergens,
            traces,
            ingredients_analysis_tags
        FROM '{RUTA_SNAPSHOT_CRUDO.as_posix()}'
        """
    ).df()
    return matriz.merge(crudo, on="code", how="left")


pytestmark = pytest.mark.skipif(
    not _existen_los_parquets(),
    reason="Requiere datos/procesados/*.parquet (versionados en el repo; ver .gitignore)",
)


def test_todos_los_codes_del_golden_set_existen_en_el_snapshot(df_evaluacion: pd.DataFrame) -> None:
    codes_presentes = set(df_evaluacion["code"])
    faltantes = [caso.code for caso in CASOS if caso.code not in codes_presentes]
    assert not faltantes, f"codes del golden set ausentes del snapshot: {faltantes}"


def test_golden_set_completo_pasa(df_evaluacion: pd.DataFrame) -> None:
    reporte = evaluar(df_evaluacion)
    fallidos = reporte[~reporte["paso"]]
    if not fallidos.empty:
        detalle = "\n".join(
            f"- {fila.code}: {fila.descripcion}\n    fallos: {fila.fallos}" for fila in fallidos.itertuples()
        )
        pytest.fail(f"{len(fallidos)}/{len(reporte)} casos del golden set fallaron:\n{detalle}")


@pytest.mark.parametrize("caso", CASOS, ids=[caso.code for caso in CASOS])
def test_cada_caso_individual(df_evaluacion: pd.DataFrame, caso) -> None:
    # Se corre `evaluar()` sobre el DataFrame completo (no solo la fila de `caso`) porque
    # `evaluar()` reporta un fallo explícito por cada `code` de CASOS ausente del DataFrame que
    # recibe: filtrar a una sola fila haría fallar "en falso" a los otros 12 casos.
    reporte = evaluar(df_evaluacion)
    fila = reporte[reporte["code"] == caso.code].iloc[0]
    assert fila["paso"], f"{caso.descripcion}\nfallos: {fila['fallos']}"
