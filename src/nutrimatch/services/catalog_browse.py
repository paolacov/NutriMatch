"""Exploración del catálogo completo. No filtra por universo_puntuable ni calcula scores."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from nutrimatch.schemas.catalog import (
    FACETA_OTROS,
    FACETA_SIN_CATEGORIA,
    FACETA_TODAS,
    CatalogCategory,
    CatalogPage,
)
from nutrimatch.services.product import detalle_desde_fila
from nutrimatch.services.ranking import filtrar_por_query

PAGE_SIZE_POR_DEFECTO = 24
PAGE_SIZE_MAXIMO = 60

# Facetas de exploración = food_groups de OFF (primer tag) + respaldo por tags ya presentes.
# No se escriben al Parquet. "Otros" no se ofrece como chip.
_GRUPO_FOOD: dict[str, str] = {
    "en:milk-and-dairy-products": "en:milk-and-dairy-products",
    "en:beverages": "en:beverages",
    "en:alcoholic-beverages": "en:beverages",
    "en:cereals-and-potatoes": "en:cereals-and-potatoes",
    "en:sugary-snacks": "en:sugary-snacks",
    "en:salty-snacks": "en:salty-snacks",
    "en:fats-and-sauces": "en:fats-and-sauces",
    "en:fish-meat-eggs": "en:fish-meat-eggs",
    "en:fruits-and-vegetables": "en:fruits-and-vegetables",
    "en:composite-foods": "en:composite-foods",
    "en:baby-foods-and-milks": "en:milk-and-dairy-products",
}

_FACETAS: tuple[tuple[str, str, frozenset[str]], ...] = (
    (
        "en:milk-and-dairy-products",
        "Lácteos",
        frozenset(
            {
                "en:milk-and-dairy-products",
                "en:dairies",
                "en:milks",
                "en:yogurts",
                "en:cheeses",
                "en:dairy-drinks",
                "en:cream",
                "en:butters",
                "fr:crema",
                "en:baby-foods-and-milks",
            }
        ),
    ),
    (
        "en:beverages",
        "Bebidas",
        frozenset(
            {
                "en:beverages",
                "en:alcoholic-beverages",
                "en:plant-based-beverages",
                "en:sweetened-beverages",
                "en:unsweetened-beverages",
                "en:waters",
                "en:sodas",
                "en:fruit-juices",
                "en:fruit-based-beverages",
                "en:teas",
                "en:coffees",
                "en:energy-drinks",
                "es:jugos",
                "es:refrescos",
            }
        ),
    ),
    (
        "en:cereals-and-potatoes",
        "Cereales y pan",
        frozenset(
            {
                "en:cereals-and-potatoes",
                "en:cereals-and-their-products",
                "en:breakfast-cereals",
                "en:pastas",
                "en:rices",
                "en:flours",
                "en:breads",
                "en:bread",
                "en:sliced-breads",
                "es:pan-dulce",
                "en:toasts",
                "es:tortillas",
            }
        ),
    ),
    (
        "en:sugary-snacks",
        "Dulces",
        frozenset(
            {
                "en:sugary-snacks",
                "en:sweet-snacks",
                "en:biscuits",
                "en:confectioneries",
                "en:candies",
                "en:chocolates",
                "en:ice-creams",
                "en:ice-creams-and-sorbets",
                "en:jams",
            }
        ),
    ),
    (
        "en:salty-snacks",
        "Botanas",
        frozenset({"en:salty-snacks", "en:appetizers", "en:crisps", "en:snacks"}),
    ),
    (
        "en:fats-and-sauces",
        "Salsas y aceites",
        frozenset(
            {
                "en:fats-and-sauces",
                "en:sauces",
                "en:condiments",
                "en:tomato-sauces",
                "en:hot-sauces",
                "en:spreads",
                "en:sweet-spreads",
                "en:pates-a-tartiner",
                "fr:pates-a-tartiner",
                "en:olive-oils",
                "en:fats",
                "es:sazonador",
                "en:sweeteners",
                "en:tabletop-sweeteners",
            }
        ),
    ),
    (
        "en:fish-meat-eggs",
        "Carnes y huevo",
        frozenset(
            {
                "en:fish-meat-eggs",
                "en:tunas",
                "en:eggs",
                "en:meats",
                "en:sausages",
                "en:seafood",
                "en:protein-powders",
            }
        ),
    ),
    (
        "en:fruits-and-vegetables",
        "Frutas y verduras",
        frozenset(
            {
                "en:fruits-and-vegetables",
                "en:vegetables-based-foods",
                "en:frozen-vegetables",
                "en:dried-fruits",
                "en:refried-beans",
                "es:enlatados",
            }
        ),
    ),
    (
        "en:composite-foods",
        "Preparados",
        frozenset(
            {
                "en:composite-foods",
                "en:frozen-ready-made-meals",
                "en:dehydrated-soups",
                "en:dietary-supplements",
                "en:refrigerated-foods",
            }
        ),
    ),
)

_IDS_CONOCIDOS = {FACETA_TODAS, FACETA_SIN_CATEGORIA, FACETA_OTROS} | {fid for fid, _, _ in _FACETAS}


def _es_nulo(valor: Any) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def _texto(valor: Any) -> str | None:
    if _es_nulo(valor):
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() in {"nan", "none", "<na>"}:
        return None
    return texto


def _partir_tags(valor: Any) -> list[str]:
    texto = _texto(valor)
    if texto is None:
        return []
    return [parte.strip().lower() for parte in texto.split(",") if parte.strip()]


def _campo(fila: Any, col: str) -> Any:
    if hasattr(fila, "get"):
        return fila.get(col)
    try:
        return fila[col]
    except (KeyError, TypeError, IndexError):
        return None


def tags_categoria_de_fila(fila: Any) -> list[str]:
    """Etiquetas OFF ya presentes. No inventa categorías nuevas."""
    tags: list[str] = []
    for col in ("food_groups_tags", "categories_tags"):
        tags.extend(_partir_tags(_campo(fila, col)))
    for col in ("main_category", "main_category_en", "categoria_referencia"):
        texto = _texto(_campo(fila, col))
        if texto:
            tags.append(texto.lower())
    return tags


def _food_groups(fila: Any) -> list[str]:
    return _partir_tags(_campo(fila, "food_groups_tags"))


def faceta_de_fila(fila: Any) -> str:
    grupos = _food_groups(fila)
    if grupos:
        mapeado = _GRUPO_FOOD.get(grupos[0])
        if mapeado:
            return mapeado
        for grupo in grupos[1:]:
            mapeado = _GRUPO_FOOD.get(grupo)
            if mapeado:
                return mapeado
    tags = set(tags_categoria_de_fila(fila))
    if not tags:
        return FACETA_SIN_CATEGORIA
    for facet_id, _nombre, miembros in _FACETAS:
        if tags & miembros:
            return facet_id
    return FACETA_OTROS


def faceta_conocida(category: str) -> bool:
    return category in _IDS_CONOCIDOS


def _serie_facetas(df: pd.DataFrame) -> pd.Series:
    return pd.Series([faceta_de_fila(fila) for fila in df.to_dict(orient="records")], index=df.index)


def _ordenar(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    nombres = df["product_name"] if "product_name" in df.columns else pd.Series([None] * len(df), index=df.index)
    clave = nombres.map(_texto).fillna("\uffff")
    ordenado = df.assign(_catalog_sort=clave).sort_values(["_catalog_sort", "code"], kind="mergesort")
    return ordenado.drop(columns=["_catalog_sort"])


def listar_categorias(df: pd.DataFrame) -> list[CatalogCategory]:
    facetas = _serie_facetas(df)
    conteo = facetas.value_counts()
    items = [
        CatalogCategory(id=FACETA_TODAS, name="Todas", count=int(len(df))),
    ]
    for facet_id, nombre, _miembros in _FACETAS:
        n = int(conteo.get(facet_id, 0))
        if n:
            items.append(CatalogCategory(id=facet_id, name=nombre, count=n))
    n_sin = int(conteo.get(FACETA_SIN_CATEGORIA, 0))
    if n_sin:
        items.append(CatalogCategory(id=FACETA_SIN_CATEGORIA, name="Sin categoría", count=n_sin))
    return items


def paginar_catalogo(
    df: pd.DataFrame,
    *,
    search: str = "",
    category: str = FACETA_TODAS,
    page: int = 1,
    page_size: int = PAGE_SIZE_POR_DEFECTO,
) -> CatalogPage:
    if not faceta_conocida(category):
        return CatalogPage(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    filtrado = filtrar_por_query(df, search)
    if category:
        mascara = _serie_facetas(filtrado) == category
        filtrado = filtrado.loc[mascara]

    total = int(len(filtrado))
    total_pages = math.ceil(total / page_size) if total else 0
    if total == 0:
        return CatalogPage(items=[], total=0, page=page, page_size=page_size, total_pages=0)

    if page > total_pages:
        return CatalogPage(items=[], total=total, page=page, page_size=page_size, total_pages=total_pages)

    ordenado = _ordenar(filtrado)
    inicio = (page - 1) * page_size
    ventana = ordenado.iloc[inicio : inicio + page_size]
    items = [detalle_desde_fila(fila) for _, fila in ventana.iterrows()]
    return CatalogPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
