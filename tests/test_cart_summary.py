"""Pruebas del resumen de carrito (A12): quantity, NULL y no clasificado."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from nutrimatch.api.app import create_app
from nutrimatch.engine.cart_summary import (
    NO_CLASIFICADO,
    PLATO_CEREALES,
    PLATO_FRUTAS_VERDURAS,
    grupo_plato,
    parsear_gramos,
    resumir_carrito,
)
from nutrimatch.services.cart import resumir_codes
from tests.test_api import _catalogo_con_ficha


def test_parsear_gramos_solo_g_ml_claros() -> None:
    assert parsear_gramos("100 g") == 100.0
    assert parsear_gramos("330 ml") == 330.0
    assert parsear_gramos("1 L") == 1000.0
    assert parsear_gramos("1,5 kg") == 1500.0
    assert parsear_gramos("250g") == 250.0
    assert parsear_gramos(None) is None
    assert parsear_gramos("pack") is None
    assert parsear_gramos("12 x 330 ml") is None
    assert parsear_gramos("330") is None


def test_sin_quantity_no_pondera() -> None:
    resumen = resumir_carrito(
        [
            {"quantity": "100 g", "sugars_100g": 10.0, "main_category": "en:breads"},
            {"quantity": None, "sugars_100g": 4.0, "main_category": "en:breads"},
        ]
    )
    assert resumen["method"] == "promedio_100g"
    azucar = next(n for n in resumen["nutrients"] if n["key"] == "sugars")
    assert azucar["value"] == 7.0
    assert azucar["status"] == "DERIVED"


def test_todos_con_quantity_pondera_por_gramos() -> None:
    resumen = resumir_carrito(
        [
            {"quantity": "100 g", "sugars_100g": 10.0, "main_category": "en:breads"},
            {"quantity": "200 g", "sugars_100g": 4.0, "main_category": "en:breads"},
        ]
    )
    assert resumen["method"] == "ponderado_gramos"
    azucar = next(n for n in resumen["nutrients"] if n["key"] == "sugars")
    assert azucar["value"] == 6.0


def test_nutriente_ausente_es_null_nunca_cero() -> None:
    resumen = resumir_carrito(
        [
            {"quantity": "100 g", "sugars_100g": None, "fiber_100g": 3.0},
            {"quantity": "100 g", "sugars_100g": None, "fiber_100g": None},
        ]
    )
    azucar = next(n for n in resumen["nutrients"] if n["key"] == "sugars")
    fibra = next(n for n in resumen["nutrients"] if n["key"] == "fiber")
    assert azucar["value"] is None
    assert azucar["status"] == "UNAVAILABLE"
    assert azucar["n_with_data"] == 0
    assert fibra["value"] == 3.0
    assert fibra["n_with_data"] == 1
    assert fibra["n_products"] == 2


def test_tag_no_mapeado_va_a_no_clasificado() -> None:
    assert grupo_plato({"food_groups_tags": "en:sodas,en:sweetened-beverages"}) == NO_CLASIFICADO
    assert grupo_plato({"food_groups_tags": None, "main_category": None}) == NO_CLASIFICADO
    # Ancestro genérico en categories_tags no se usa: las almendras no son origen animal.
    assert (
        grupo_plato(
            {
                "food_groups_tags": "en:salty-snacks,en:nuts",
                "categories_tags": "en:legumes-and-their-products,en:almond-butters",
                "main_category": "en:almond-butters",
            }
        )
        == NO_CLASIFICADO
    )


def test_plato_no_inventa_grupo() -> None:
    assert grupo_plato({"food_groups_tags": "en:plant-based-foods-and-beverages,en:fruits"}) == (
        PLATO_FRUTAS_VERDURAS
    )
    assert grupo_plato({"main_category": "en:breads"}) == PLATO_CEREALES
    resumen = resumir_carrito(
        [
            {"food_groups_tags": "en:cereals", "main_category": "en:breads"},
            {"food_groups_tags": "en:sodas", "main_category": "en:sodas"},
        ]
    )
    plato = {b["key"]: b for b in resumen["plato"]}
    assert plato[PLATO_CEREALES]["n"] == 1
    assert plato[NO_CLASIFICADO]["n"] == 1
    assert plato[PLATO_CEREALES]["share"] == 0.5
    assert plato[NO_CLASIFICADO]["label"] == "no clasificado"
    cats = {b["key"]: b for b in resumen["categories"]}
    assert cats["en:sodas"]["n"] == 1
    assert "en:breads" in cats


def test_categoria_vacia_es_no_clasificado() -> None:
    resumen = resumir_carrito([{"sugars_100g": 1.0}])
    assert resumen["categories"][-1]["key"] == NO_CLASIFICADO
    assert resumen["categories"][-1]["n"] == 1


def test_resumir_codes_omite_desconocidos(tmp_path: Path) -> None:
    catalogo = _catalogo_con_ficha()
    resumen = resumir_codes(catalogo, ["75000001", "nope", "75000001"])
    assert resumen.n_products == 1
    assert resumen.method == "ponderado_gramos"


def test_api_cart_summary(tmp_path: Path) -> None:
    app = create_app(catalog=_catalogo_con_ficha(), db_path=tmp_path / "api.db")
    cliente = TestClient(app)
    vacio = cliente.post("/cart/summary", json={"codes": []})
    assert vacio.status_code == 200
    assert vacio.json()["n_products"] == 0
    assert vacio.json()["status"] == "DERIVED"
    cuerpo = cliente.post("/cart/summary", json={"codes": ["75000001", "75000002"]}).json()
    assert cuerpo["n_products"] == 2
    assert cuerpo["method"] == "ponderado_gramos"
    azucar = next(n for n in cuerpo["nutrients"] if n["key"] == "sugars")
    assert azucar["value"] == 1.2
    assert azucar["n_with_data"] == 1
    assert azucar["n_products"] == 2
