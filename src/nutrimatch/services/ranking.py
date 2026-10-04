"""Orquestación del ranking: filtros duros, score, bandas exclusivas y búsqueda (A19, A32).

No calcula subpuntajes nuevos: llama a `engine/` y asigna cada producto a exactamente una banda.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from nutrimatch import __version__
from nutrimatch.engine.compatibility_score import calcular_score_compatibilidad
from nutrimatch.engine.constants import CORE8_NUTRIENTES
from nutrimatch.engine.hard_filters import evaluar_alergia, evaluar_dieta
from nutrimatch.engine.nutrition_score import calcular_subpuntaje_d1
from nutrimatch.engine.preference_score import calcular_d3
from nutrimatch.engine.user_weights import convertir_prioridades_a_pesos
from nutrimatch.schemas.profile import UserProfile
from nutrimatch.schemas.ranking import (
    AlternativesResult,
    Band,
    BandSlice,
    DimensionExplanation,
    NutrientExplanation,
    ProductExplanation,
    RankingItem,
    RankingRequest,
    RankingResult,
)
from nutrimatch.services.catalog import Catalog

DIETA_SIN_RESTRICCION = "compatible"
ALTERNATIVAS_TOPE = 5


def _es_nulo(valor: Any) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


def _float_or_none(valor: Any) -> float | None:
    if _es_nulo(valor):
        return None
    return float(valor)


def _str_or_none(valor: Any) -> str | None:
    if _es_nulo(valor):
        return None
    texto = str(valor).strip()
    return texto or None


def asignar_banda(
    allergy_status: str,
    diet_status: str,
    informacion_insuficiente: bool,
) -> Band:
    """Regla exclusiva de bandas (A32): un producto cae en una sola.

    1. excluido — alergia no_apto o dieta incompatible (no se lista).
    2. no_verificable — alergia o dieta no_verificable (nunca se mezcla con apto, A15).
    3. informacion_insuficiente — cov < 0.5 (A2).
    4. ranking — el resto.
    """
    if allergy_status == "no_apto" or diet_status == "incompatible":
        return "excluido"
    if allergy_status == "no_verificable" or diet_status == "no_verificable":
        return "no_verificable"
    if informacion_insuficiente:
        return "informacion_insuficiente"
    return "ranking"


def filtrar_por_query(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Búsqueda sobre el catálogo entero (A19): `code` o nombre, case-insensitive.

    Query vacía = sin filtro. No usa regex: el texto se toma literal.
    """
    texto = query.strip()
    if not texto:
        return df
    codigo = df["code"].astype(str)
    nombre = df["product_name"].fillna("").astype(str)
    needle = texto.casefold()
    mascara = codigo.str.casefold().str.contains(needle, regex=False) | nombre.str.casefold().str.contains(
        needle, regex=False
    )
    for col in ("brand_original", "brands"):
        if col in df.columns:
            marca = df[col].fillna("").astype(str)
            mascara = mascara | marca.str.casefold().str.contains(needle, regex=False)
            break
    return df.loc[mascara]


def _percentiles_de_fila(fila: pd.Series) -> dict[str, float | None]:
    return {
        nutriente: _float_or_none(fila[f"percentil_{nutriente}"])
        if f"percentil_{nutriente}" in fila.index
        else None
        for nutriente in CORE8_NUTRIENTES
    }


def _evaluar_dieta(ingredients_analysis_tags: Any, diet: str | None) -> str:
    if diet is None:
        return DIETA_SIN_RESTRICCION
    return evaluar_dieta(ingredients_analysis_tags, diet)


def _banderas_faltantes(
    d1: float | None,
    d2: float | None,
    d3: float | None,
    allergy_status: str,
    diet_status: str,
) -> list[str]:
    banderas: list[str] = []
    if d1 is None:
        banderas.append("D1_sin_dato")
    if d2 is None:
        banderas.append("D2_sin_dato")
    if d3 is None:
        banderas.append("D3_sin_dato")
    if allergy_status == "no_verificable":
        banderas.append("alergia_no_verificable")
    if diet_status == "no_verificable":
        banderas.append("dieta_no_verificable")
    return banderas


def _explicacion(
    fila: pd.Series,
    profile: UserProfile,
    pesos: dict[str, float],
    d1: float | None,
    d2: float | None,
    d3: float | None,
    allergy_status: str,
    diet_status: str,
) -> ProductExplanation:
    resultado = calcular_score_compatibilidad({"D1": d1, "D2": d2, "D3": d3}, pesos)
    _, detalle_d1 = calcular_subpuntaje_d1(_percentiles_de_fila(fila))
    dimensiones = {
        clave: DimensionExplanation(
            subscore=_float_or_none(detalle["subpuntaje"]),
            weight=float(detalle["peso"]),
            available=bool(detalle["disponible"]),
            weighted_contribution=_float_or_none(detalle["contribucion_ponderada"]),
        )
        for clave, detalle in resultado["dimensiones"].items()
    }
    nutrientes = {
        clave: NutrientExplanation(
            percentile=_float_or_none(detalle["percentil"]),
            sign=int(detalle["signo"]),
            available=bool(detalle["disponible"]),
            contribution=_float_or_none(detalle["contribucion"]),
        )
        for clave, detalle in detalle_d1.items()
    }
    return ProductExplanation(
        score=_float_or_none(resultado["score_final"]),
        cov=float(resultado["cov"]),
        dimensions=dimensiones,
        d1_nutrients=nutrientes,
        allergy_status=allergy_status,  # type: ignore[arg-type]
        diet_status=diet_status,  # type: ignore[arg-type]
        missing_flags=_banderas_faltantes(d1, d2, d3, allergy_status, diet_status),
        category=_str_or_none(fila.get("categoria_referencia")),
        nova_group=_float_or_none(fila.get("nova_group")),
        additives_n=_float_or_none(fila.get("additives_n")),
        name_used_fallback=bool(fila.get("product_name_flag_respaldo_usado", False)),
    )


def _item_desde_fila(
    fila: pd.Series,
    profile: UserProfile,
    pesos: dict[str, float],
    *,
    con_explicacion: bool,
) -> tuple[RankingItem, Band]:
    d1 = _float_or_none(fila.get("d1"))
    d2 = _float_or_none(fila.get("d2"))
    d3 = calcular_d3(fila.get("labels_tags"), profile.valued_labels)
    allergy_status = evaluar_alergia(fila.get("allergens"), fila.get("traces"), profile.allergen_tags)
    diet_status = _evaluar_dieta(fila.get("ingredients_analysis_tags"), profile.diet)
    resultado = calcular_score_compatibilidad({"D1": d1, "D2": d2, "D3": d3}, pesos)
    banda = asignar_banda(allergy_status, diet_status, bool(resultado["informacion_insuficiente"]))
    explicacion = (
        _explicacion(fila, profile, pesos, d1, d2, d3, allergy_status, diet_status)
        if con_explicacion
        else None
    )
    item = RankingItem(
        code=str(fila["code"]),
        product_name=_str_or_none(fila.get("product_name")),
        category=_str_or_none(fila.get("categoria_referencia")),
        band=banda,
        score=_float_or_none(resultado["score_final"]),
        d1=d1,
        d2=d2,
        d3=d3,
        cov=float(resultado["cov"]),
        allergy_status=allergy_status,
        diet_status=diet_status,  # type: ignore[arg-type]
        explanation=explicacion,
    )
    return item, banda


class RankingService:
    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    def rank(self, request: RankingRequest) -> RankingResult:
        pesos = convertir_prioridades_a_pesos(list(request.profile.priority_order))
        candidatos = filtrar_por_query(self.catalog.df, request.query)
        cubetas: dict[Band, list[RankingItem]] = {
            "ranking": [],
            "no_verificable": [],
            "informacion_insuficiente": [],
            "excluido": [],
        }
        # `name=None`: columnas con guion (`saturated-fat_100g`) no son identificadores
        # válidos y `itertuples` nombrado las reescribiría.
        columnas = list(candidatos.columns)
        for tupla in candidatos.itertuples(index=False, name=None):
            serie = pd.Series(dict(zip(columnas, tupla, strict=True)))
            item, banda = _item_desde_fila(serie, request.profile, pesos, con_explicacion=False)
            cubetas[banda].append(item)

        cubetas["ranking"].sort(key=lambda i: (i.score is None, -(i.score or 0.0)))
        cubetas["no_verificable"].sort(key=lambda i: (i.score is None, -(i.score or 0.0)))
        cubetas["informacion_insuficiente"].sort(key=lambda i: i.code)

        def _slice(banda: Band) -> BandSlice:
            todos = cubetas[banda]
            top = todos[: request.top_n]
            items_con_ficha: list[RankingItem] = []
            for rango, item in enumerate(top, start=1):
                fila = self.catalog.get_row(item.code)
                explicado, _ = _item_desde_fila(fila, request.profile, pesos, con_explicacion=True)
                items_con_ficha.append(explicado.model_copy(update={"rank": rango}))
            return BandSlice(items=items_con_ficha, total=len(todos))

        return RankingResult(
            snapshot_id=self.catalog.snapshot_id,
            engine_version=__version__,
            query=request.query,
            weights=pesos,
            ranking=_slice("ranking"),
            no_verificable=_slice("no_verificable"),
            informacion_insuficiente=_slice("informacion_insuficiente"),
            excluded_count=len(cubetas["excluido"]),
            n_matched=len(candidatos),
        )

    def explain(self, code: str, profile: UserProfile) -> RankingItem:
        pesos = convertir_prioridades_a_pesos(list(profile.priority_order))
        fila = self.catalog.get_row(code)
        item, _banda = _item_desde_fila(fila, profile, pesos, con_explicacion=True)
        return item

    def alternatives(self, code: str, profile: UserProfile) -> AlternativesResult:
        """Pares del mismo grupo de referencia, con el ranking ya definido.

        No recalcula percentiles ni crea otro score. Descarta al producto de
        origen y se queda con la banda de ranking, hasta cinco.
        """
        fila = self.catalog.get_row(code)
        categoria = (
            _str_or_none(fila.get("categoria_referencia"))
            if "categoria_referencia" in fila.index
            else None
        )
        vacio = AlternativesResult(
            code=str(fila["code"]),
            category=categoria,
            reason="sin_categoria",
            snapshot_id=self.catalog.snapshot_id,
            engine_version=__version__,
            total=0,
            items=[],
        )
        if categoria is None or "categoria_referencia" not in self.catalog.df.columns:
            return vacio

        pesos = convertir_prioridades_a_pesos(list(profile.priority_order))
        categorias = self.catalog.df["categoria_referencia"].map(_str_or_none)
        codigos = self.catalog.df["code"].astype(str)
        candidatos = self.catalog.df.loc[(categorias == categoria) & (codigos != str(fila["code"]))]
        pares: list[RankingItem] = []
        columnas = list(candidatos.columns)
        for tupla in candidatos.itertuples(index=False, name=None):
            serie = pd.Series(dict(zip(columnas, tupla, strict=True)))
            item, banda = _item_desde_fila(serie, profile, pesos, con_explicacion=False)
            if banda == "ranking":
                pares.append(item)

        pares.sort(key=lambda i: (i.score is None, -(i.score or 0.0)))
        items: list[RankingItem] = []
        for rango, item in enumerate(pares[:ALTERNATIVAS_TOPE], start=1):
            explicado, _banda = _item_desde_fila(
                self.catalog.get_row(item.code),
                profile,
                pesos,
                con_explicacion=True,
            )
            items.append(explicado.model_copy(update={"rank": rango}))
        return vacio.model_copy(
            update={
                "reason": "ok" if items else "sin_opciones",
                "total": len(pares),
                "items": items,
            }
        )
