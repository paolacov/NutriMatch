from __future__ import annotations

import pandas as pd
import pytest

from evaluacion.coverage_diagnostic import diagnosticar_cobertura

PESOS_IGUALES = {"D1": 1 / 3, "D2": 1 / 3, "D3": 1 / 3}


def test_todo_disponible_da_cero_informacion_insuficiente() -> None:
    disponibilidad = pd.DataFrame(
        {"D1": [True, True], "D2": [True, True], "D3": [True, True]}
    )

    reporte = diagnosticar_cobertura(disponibilidad, PESOS_IGUALES)

    assert reporte["n_total"] == 2
    assert reporte["n_informacion_insuficiente"] == 0
    assert reporte["porcentaje_informacion_insuficiente"] == 0.0
    assert reporte["desglose_por_combinacion_faltante"].empty


def test_falta_una_dimension_con_pesos_iguales_no_es_insuficiente() -> None:
    # cov = 2/3 = 0.667 >= 0.5: no cae en la banda, aunque falte una dimension.
    disponibilidad = pd.DataFrame({"D1": [True], "D2": [True], "D3": [False]})

    reporte = diagnosticar_cobertura(disponibilidad, PESOS_IGUALES)

    assert reporte["n_informacion_insuficiente"] == 0
    assert reporte["cov"].iloc[0] == pytest.approx(2 / 3)


def test_faltan_dos_dimensiones_cae_en_insuficiente_y_se_desglosa() -> None:
    disponibilidad = pd.DataFrame(
        {
            "D1": [True, True, False],
            "D2": [False, False, False],
            "D3": [False, True, False],
        }
    )
    # fila 0: falta D2, D3 -> cov = 1/3 < 0.5 -> insuficiente, faltante "D2+D3"
    # fila 1: falta D2 -> cov = 2/3 >= 0.5 -> NO insuficiente
    # fila 2: falta D1, D2, D3 -> cov = 0 -> insuficiente, faltante "D1+D2+D3"

    reporte = diagnosticar_cobertura(disponibilidad, PESOS_IGUALES)

    assert reporte["n_total"] == 3
    assert reporte["n_informacion_insuficiente"] == 2

    desglose = reporte["desglose_por_combinacion_faltante"].set_index("dimensiones_faltantes")
    assert desglose.loc["D2+D3", "n"] == 1
    assert desglose.loc["D1+D2+D3", "n"] == 1
    assert desglose["n"].sum() == reporte["n_informacion_insuficiente"]
    assert desglose.loc["D2+D3", "porcentaje_del_total"] == pytest.approx(100 / 3)
    assert desglose.loc["D2+D3", "porcentaje_de_insuficientes"] == pytest.approx(50.0)


def test_umbral_es_estrictamente_menor_que_no_menor_o_igual() -> None:
    # cov == 0.5 exacto: A2 dice "cov < 0.5", asi que 0.5 NO debe caer en informacion insuficiente.
    disponibilidad = pd.DataFrame({"D1": [True], "D2": [False], "D3": [False]})
    pesos = {"D1": 0.5, "D2": 0.3, "D3": 0.2}

    reporte = diagnosticar_cobertura(disponibilidad, pesos)

    assert reporte["cov"].iloc[0] == pytest.approx(0.5)
    assert reporte["n_informacion_insuficiente"] == 0


def test_dataframe_vacio_no_falla() -> None:
    disponibilidad = pd.DataFrame({"D1": [], "D2": [], "D3": []})

    reporte = diagnosticar_cobertura(disponibilidad, PESOS_IGUALES)

    assert reporte["n_total"] == 0
    assert reporte["n_informacion_insuficiente"] == 0
    assert reporte["porcentaje_informacion_insuficiente"] == 0.0
    assert reporte["desglose_por_combinacion_faltante"].empty


def test_ninguna_dimension_disponible_para_todos() -> None:
    disponibilidad = pd.DataFrame({"D1": [False, False], "D2": [False, False], "D3": [False, False]})

    reporte = diagnosticar_cobertura(disponibilidad, PESOS_IGUALES)

    assert reporte["n_informacion_insuficiente"] == 2
    assert reporte["porcentaje_informacion_insuficiente"] == 100.0
    desglose = reporte["desglose_por_combinacion_faltante"]
    assert len(desglose) == 1
    assert desglose.iloc[0]["dimensiones_faltantes"] == "D1+D2+D3"
    assert desglose.iloc[0]["n"] == 2
