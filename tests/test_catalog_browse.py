"""Catálogo de exploración: todos los productos, paginación y facetas OFF. No toca ranking."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from nutrimatch.api.app import create_app
from nutrimatch.schemas.catalog import FACETA_OTROS, FACETA_SIN_CATEGORIA
from nutrimatch.services.catalog import Catalog
from nutrimatch.services.catalog_browse import faceta_de_fila, listar_categorias, paginar_catalogo
from tests.test_api import _catalogo_con_ficha


def _catalogo_browse() -> Catalog:
    base = _catalogo_con_ficha().df.copy()
    base["main_category"] = ["en:breads", "en:breakfast-cereals", "en:crisps", None, "en:olive-oils"]
    base["main_category_en"] = [None, None, None, None, None]
    base["categoria_referencia"] = ["en:breads", "en:breakfast-cereals", "en:crisps", None, "en:olive-oils"]
    base["food_groups_tags"] = [None, None, None, None, None]
    base["categories_tags"] = [
        "en:plant-based-foods,en:breads",
        "en:cereals-and-their-products,en:breakfast-cereals",
        "en:snacks,en:salty-snacks,en:crisps",
        None,
        "en:fats,en:olive-oils",
    ]
    base["universo_puntuable"] = [True, False, False, False, True]
    return Catalog(df=base, snapshot_id="test_snapshot")


def _client(tmp_path: Path, catalog: Catalog | None = None) -> TestClient:
    app = create_app(catalog=catalog or _catalogo_browse(), db_path=tmp_path / "catalog.db")
    return TestClient(app)


def test_faceta_sin_categoria_y_food_groups() -> None:
    assert faceta_de_fila(pd.Series({"main_category": None})) == FACETA_SIN_CATEGORIA
    assert faceta_de_fila(pd.Series({"main_category": "en:olive-oils"})) == "en:fats-and-sauces"
    assert faceta_de_fila(pd.Series({"main_category": "en:breads"})) == "en:cereals-and-potatoes"
    assert faceta_de_fila(pd.Series({"categories_tags": "en:dairies,en:milks"})) == "en:milk-and-dairy-products"
    assert (
        faceta_de_fila(
            pd.Series(
                {
                    "food_groups_tags": "en:cereals-and-potatoes,en:bread",
                    "categories_tags": "en:snacks,en:crisps",
                }
            )
        )
        == "en:cereals-and-potatoes"
    )
    assert (
        faceta_de_fila(pd.Series({"food_groups_tags": "en:alcoholic-beverages"}))
        == "en:beverages"
    )


def test_listar_categorias_incluye_todas_y_sin_categoria() -> None:
    cats = listar_categorias(_catalogo_browse().df)
    por_id = {c.id: c for c in cats}
    assert por_id[""].name == "Todas"
    assert por_id[""].count == 5
    assert por_id["en:cereals-and-potatoes"].name == "Cereales y pan"
    assert por_id["en:cereals-and-potatoes"].count == 2
    assert por_id["en:salty-snacks"].count == 1
    assert por_id["en:fats-and-sauces"].count == 1
    assert FACETA_OTROS not in por_id
    assert por_id[FACETA_SIN_CATEGORIA].name == "Sin categoría"
    assert por_id[FACETA_SIN_CATEGORIA].count == 1


def test_paginar_no_filtra_por_universo_puntuable() -> None:
    pagina = paginar_catalogo(_catalogo_browse().df, page=1, page_size=24)
    assert pagina.total == 5
    assert {item.code for item in pagina.items} == {
        "75000001",
        "75000002",
        "75000003",
        "75000004",
        "75000005",
    }


def test_paginacion_y_total_pages() -> None:
    primera = paginar_catalogo(_catalogo_browse().df, page=1, page_size=2)
    assert primera.total == 5
    assert primera.total_pages == 3
    assert len(primera.items) == 2
    segunda = paginar_catalogo(_catalogo_browse().df, page=3, page_size=2)
    assert len(segunda.items) == 1
    vacia = paginar_catalogo(_catalogo_browse().df, page=9, page_size=2)
    assert vacia.items == []
    assert vacia.total == 5
    assert vacia.total_pages == 3


def test_busqueda_por_nombre_y_marca() -> None:
    por_nombre = paginar_catalogo(_catalogo_browse().df, search="pan")
    assert [item.code for item in por_nombre.items] == ["75000001"]
    por_marca = paginar_catalogo(_catalogo_browse().df, search="quaker")
    assert [item.code for item in por_marca.items] == ["75000002"]


def test_filtro_categoria_y_inexistente() -> None:
    panes = paginar_catalogo(_catalogo_browse().df, category="en:cereals-and-potatoes")
    assert panes.total == 2
    assert {item.code for item in panes.items} == {"75000001", "75000002"}
    inexistente = paginar_catalogo(_catalogo_browse().df, category="en:no-existe")
    assert inexistente.total == 0
    assert inexistente.items == []
    assert inexistente.total_pages == 0


def test_producto_sin_nombre_y_sin_categoria() -> None:
    df = _catalogo_browse().df.copy()
    df.loc[df["code"] == "75000004", "product_name"] = None
    df.loc[df["code"] == "75000004", "product_name_homologated"] = None
    pagina = paginar_catalogo(df, category=FACETA_SIN_CATEGORIA)
    assert pagina.total == 1
    assert pagina.items[0].code == "75000004"
    assert pagina.items[0].name.value is None
    assert pagina.items[0].category is None


def test_http_catalogo_paginado(tmp_path: Path) -> None:
    cliente = _client(tmp_path)
    categorias = cliente.get("/catalog/categories")
    assert categorias.status_code == 200
    assert categorias.json()[0] == {"id": "", "name": "Todas", "count": 5}

    pagina = cliente.get("/catalog/products", params={"page": 1, "page_size": 2})
    assert pagina.status_code == 200
    cuerpo = pagina.json()
    assert cuerpo["total"] == 5
    assert cuerpo["page"] == 1
    assert cuerpo["page_size"] == 2
    assert cuerpo["total_pages"] == 3
    assert len(cuerpo["items"]) == 2
    assert all("fit" not in item for item in cuerpo["items"])
    for item in cuerpo["items"]:
        if item["price"]["status"] == "REAL":
            assert item["price"]["source"] != "demo"
            assert item["price"]["value"] not in (None, 0)
        elif item["price"]["status"] == "SYNTHETIC":
            assert item["price"]["source"] == "demo"
            assert item["price"]["value"] not in (None, 0)
        else:
            assert item["price"]["value"] is None


def test_http_busqueda_categoria_y_params_invalidos(tmp_path: Path) -> None:
    cliente = _client(tmp_path)
    busqueda = cliente.get("/catalog/products", params={"search": "galleta"})
    assert [p["code"] for p in busqueda.json()["items"]] == ["75000003"]

    lacteos = cliente.get("/catalog/products", params={"category": "en:milk-and-dairy-products"})
    assert lacteos.json()["total"] == 0

    sin_cat = cliente.get("/catalog/products", params={"category": FACETA_SIN_CATEGORIA})
    assert sin_cat.json()["total"] == 1
    assert sin_cat.json()["items"][0]["code"] == "75000004"

    malo = cliente.get("/catalog/products", params={"page": 0})
    assert malo.status_code == 400
    grande = cliente.get("/catalog/products", params={"page_size": 200})
    assert grande.status_code == 400
