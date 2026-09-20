"""Pruebas de src/nutrimatch/engine/user_weights.py (decisión A6)."""

from __future__ import annotations

import pytest

from nutrimatch.engine.user_weights import convertir_prioridades_a_pesos


def test_primer_lugar_recibe_el_peso_mas_alto():
    pesos = convertir_prioridades_a_pesos(["D1", "D2", "D3"])
    assert pesos["D1"] > pesos["D2"] > pesos["D3"]


def test_pesos_suman_uno():
    pesos = convertir_prioridades_a_pesos(["D3", "D1", "D2"])
    assert sum(pesos.values()) == pytest.approx(1.0)


def test_valores_exactos_3_2_1_normalizado():
    pesos = convertir_prioridades_a_pesos(["D2", "D3", "D1"])
    assert pesos["D2"] == pytest.approx(3 / 6)
    assert pesos["D3"] == pytest.approx(2 / 6)
    assert pesos["D1"] == pytest.approx(1 / 6)


def test_el_orden_determina_a_quien_se_asigna_cada_peso():
    pesos_a = convertir_prioridades_a_pesos(["D1", "D2", "D3"])
    pesos_b = convertir_prioridades_a_pesos(["D3", "D2", "D1"])
    assert pesos_a["D1"] == pesos_b["D3"]
    assert pesos_a["D3"] == pesos_b["D1"]


@pytest.mark.parametrize(
    "orden_invalido",
    [
        ["D1", "D2"],  # incompleto
        ["D1", "D2", "D3", "D1"],  # repetido y de más
        ["D1", "D2", "D4"],  # dimensión inexistente
        [],
    ],
)
def test_orden_invalido_lanza_value_error(orden_invalido):
    with pytest.raises(ValueError):
        convertir_prioridades_a_pesos(orden_invalido)
