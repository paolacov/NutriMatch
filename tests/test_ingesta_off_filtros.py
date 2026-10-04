"""Candados de calidad del universo México en scripts/ingesta_off.py."""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ingesta_off import sql_where_calidad

COLUMNAS = {
    "code",
    "product_name",
    "generic_name",
    "abbreviated_product_name",
    "brands",
    "main_category",
    "categories_tags",
    "categories",
    "pnns_groups_1",
    "pnns_groups_2",
    "food_groups_tags",
    "ingredients_text",
    "ingredients_tags",
    "nova_group",
    "energy-kcal_100g",
    "fat_100g",
    "carbohydrates_100g",
    "proteins_100g",
    "sugars_100g",
    "fiber_100g",
    "salt_100g",
}


def _vacío() -> dict[str, object]:
    return {c: None for c in COLUMNAS}


def _filtrar(filas: list[dict[str, object]]) -> set[str]:
    df = pd.DataFrame(filas)
    con = duckdb.connect()
    con.register("off", df)
    where = sql_where_calidad(COLUMNAS)
    codes = con.execute(f"SELECT code FROM off WHERE {where}").fetchall()
    con.close()
    return {row[0] for row in codes}


def test_sql_where_calidad_compila_en_duckdb():
    where = sql_where_calidad(COLUMNAS)
    df = pd.DataFrame([_vacío() | {"code": "x"}])
    con = duckdb.connect()
    con.register("off", df)
    con.execute(f"SELECT count(*) FROM off WHERE {where}")
    con.close()
    assert "en:non-food-products" in where
    assert "ingredients_text" in where
    assert "cargando" in where


def test_basura_gtin_como_nombre_sin_categoria_se_excluye():
    filas = [
        {
            **_vacío(),
            "code": "0000100561067",
            "product_name": "076750267156369333439407316452",
            "brands": "Regalo",
        }
    ]
    assert _filtrar(filas) == set()


def test_nombre_solo_digitos_con_categoria_alimentaria_se_conserva():
    filas = [
        {
            **_vacío(),
            "code": "7501013105735",
            "product_name": "7501013105735",
            "brands": "Jumex",
            "main_category": "en:fruit-juices",
            "ingredients_text": "agua, jugo de naranja",
        }
    ]
    assert _filtrar(filas) == {"7501013105735"}


def test_no_alimento_se_excluye():
    filas = [
        {
            **_vacío(),
            "code": "nf-1",
            "product_name": "Shampoo",
            "main_category": "en:cosmetics",
            "categories_tags": "en:non-food-products,en:cosmetics",
            "ingredients_text": "sodium laureth sulfate",
        }
    ]
    assert _filtrar(filas) == set()


def test_ficha_sin_ingredientes_ni_nova_ni_macros_se_excluye():
    filas = [
        {
            **_vacío(),
            "code": "vacio-1",
            "product_name": "Producto misterioso",
            "brands": "Acme",
            "main_category": "en:yogurts",
        }
    ]
    assert _filtrar(filas) == set()


def test_macros_en_cero_sin_ingredientes_se_excluye():
    filas = [
        {
            **_vacío(),
            "code": "ceros-1",
            "product_name": "Aire envasado",
            "main_category": "en:beverages",
            "energy-kcal_100g": "0",
            "fat_100g": "0",
            "carbohydrates_100g": "0",
            "proteins_100g": "0",
            "sugars_100g": "0",
            "fiber_100g": "0",
            "salt_100g": "0",
        }
    ]
    assert _filtrar(filas) == set()


def test_agua_con_ingredientes_y_macros_cero_se_conserva():
    filas = [
        {
            **_vacío(),
            "code": "agua-1",
            "product_name": "Agua natural",
            "main_category": "en:waters",
            "ingredients_text": "agua",
            "energy-kcal_100g": "0",
            "fat_100g": "0",
            "carbohydrates_100g": "0",
            "proteins_100g": "0",
            "sugars_100g": "0",
            "fiber_100g": "0",
            "salt_100g": "0",
        }
    ]
    assert _filtrar(filas) == {"agua-1"}


def test_cargando_sin_respaldo_ni_categoria_se_excluye():
    filas = [
        {
            **_vacío(),
            "code": "cargando-1",
            "product_name": "Cargando…",
        }
    ]
    assert _filtrar(filas) == set()


def test_cargando_con_generic_name_y_nova_se_conserva():
    filas = [
        {
            **_vacío(),
            "code": "7503028965717",
            "product_name": "Cargando…",
            "generic_name": "Totopos de maíz horneados con nopal",
            "brands": "Sanissimo",
            "main_category": "es:totopos-horneados-con-nopal",
            "nova_group": "3",
        }
    ]
    assert _filtrar(filas) == {"7503028965717"}
