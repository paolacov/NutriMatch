"""Pruebas de RankingService: bandas exclusivas, búsqueda y ficha (A32)."""

from __future__ import annotations

import pandas as pd
import pytest

from nutrimatch.schemas.profile import UserProfile
from nutrimatch.schemas.ranking import RankingRequest
from nutrimatch.services.catalog import Catalog
from nutrimatch.services.ranking import RankingService, asignar_banda, filtrar_por_query


def _catalogo_minimo() -> Catalog:
    df = pd.DataFrame(
        {
            "code": ["75000001", "75000002", "75000003", "75000004", "75000005"],
            "product_name": ["Pan integral", "Avena", "Galleta", "Tisana", "Aceite"],
            "categoria_referencia": ["en:breads"] * 5,
            "d1": [80.0, 70.0, 20.0, None, 60.0],
            "d2": [90.0, 80.0, 10.0, 25.0, None],
            "labels_tags": ["en:organic", "en:organic", None, None, "en:fair-trade"],
            "allergens": ["en:gluten", None, "en:milk", None, None],
            "traces": [None, None, None, None, None],
            "ingredients_analysis_tags": ["en:vegan", "en:vegan", "en:non-vegan", None, "en:vegan"],
            "product_name_flag_respaldo_usado": [False] * 5,
            "nova_group": [1.0, 1.0, 4.0, 4.0, None],
            "additives_n": [0.0, 0.0, 5.0, 1.0, None],
        }
    )
    return Catalog(df=df, snapshot_id="test_snapshot")


def test_asignar_banda_prioridad_exclusiva() -> None:
    assert asignar_banda("no_apto", "compatible", False) == "excluido"
    assert asignar_banda("apto", "incompatible", False) == "excluido"
    assert asignar_banda("no_verificable", "compatible", True) == "no_verificable"
    assert asignar_banda("apto", "no_verificable", False) == "no_verificable"
    assert asignar_banda("apto", "compatible", True) == "informacion_insuficiente"
    assert asignar_banda("apto", "compatible", False) == "ranking"


def test_no_verificable_no_se_mezcla_con_ranking() -> None:
    servicio = RankingService(_catalogo_minimo())
    perfil = UserProfile(allergen_tags=["en:gluten"], priority_order=["D1", "D2", "D3"])
    resultado = servicio.rank(RankingRequest(profile=perfil, top_n=10))

    codes_ranking = {item.code for item in resultado.ranking.items}
    codes_nv = {item.code for item in resultado.no_verificable.items}
    assert codes_ranking.isdisjoint(codes_nv)
    # 75000001: gluten confirmado → excluido. 02, 04, 05: sin dato de alérgenos → no_verificable.
    assert resultado.excluded_count == 1
    assert "75000001" not in codes_ranking
    assert {"75000002", "75000004", "75000005"} <= codes_nv
    # 75000003 declara leche (hay dato) y no gluten: apto, dieta no declarada → ranking.
    assert "75000003" in codes_ranking


def test_busqueda_por_nombre_y_por_code() -> None:
    df = _catalogo_minimo().df
    por_nombre = filtrar_por_query(df, "pan")
    assert list(por_nombre["code"]) == ["75000001"]
    por_code = filtrar_por_query(df, "75000003")
    assert list(por_code["code"]) == ["75000003"]
    vacio = filtrar_por_query(df, "   ")
    assert len(vacio) == 5


def test_busqueda_restringe_el_ranking() -> None:
    servicio = RankingService(_catalogo_minimo())
    perfil = UserProfile()
    resultado = servicio.rank(RankingRequest(profile=perfil, query="Avena", top_n=10))
    assert resultado.n_matched == 1
    todos = (
        [i.code for i in resultado.ranking.items]
        + [i.code for i in resultado.no_verificable.items]
        + [i.code for i in resultado.informacion_insuficiente.items]
    )
    assert todos == ["75000002"]


def test_dieta_vegana_excluye_non_vegan() -> None:
    servicio = RankingService(_catalogo_minimo())
    perfil = UserProfile(diet="vegano")
    resultado = servicio.rank(RankingRequest(profile=perfil, top_n=10))
    codes_ranking = {item.code for item in resultado.ranking.items}
    assert "75000003" not in codes_ranking
    assert resultado.excluded_count >= 1


def test_caro_d3_vacio_renormaliza_y_no_inventa_cero() -> None:
    """Perfil tipo Caro: sin etiquetas valoradas, D3 es None (A26), no 0."""
    servicio = RankingService(_catalogo_minimo())
    perfil = UserProfile(valued_labels=[], priority_order=["D3", "D1", "D2"])
    resultado = servicio.rank(RankingRequest(profile=perfil, top_n=10))
    assert resultado.weights["D3"] == pytest.approx(0.5)
    # A tiene D1 y D2: cov = 0.33+0.17 = 0.5 → ranking (no insuficiente). D3 sigue None.
    item_a = next(i for i in resultado.ranking.items if i.code == "75000001")
    assert item_a.d3 is None
    assert item_a.score is not None
    assert item_a.cov == pytest.approx(0.5)
    # 75000004 solo tiene D2: cov = 0.17 < 0.5 → información insuficiente.
    codes_ins = {i.code for i in resultado.informacion_insuficiente.items}
    assert "75000004" in codes_ins


def test_el_precio_no_cambia_el_score() -> None:
    perfil = UserProfile()
    real = _catalogo_minimo().df.copy()
    demo = real.copy()
    real["price"] = 10.0
    real["price_status"] = "REAL"
    real["price_source"] = "open_prices"
    demo["price"] = 180.0
    demo["price_status"] = "SYNTHETIC"
    demo["price_source"] = "demo"
    ra = RankingService(Catalog(df=real, snapshot_id="t")).rank(RankingRequest(profile=perfil, top_n=10))
    rb = RankingService(Catalog(df=demo, snapshot_id="t")).rank(RankingRequest(profile=perfil, top_n=10))
    assert [(i.code, i.score, i.band, i.d1, i.d2, i.d3) for i in ra.ranking.items] == [
        (i.code, i.score, i.band, i.d1, i.d2, i.d3) for i in rb.ranking.items
    ]


def test_explain_incluye_detalle_a10() -> None:
    servicio = RankingService(_catalogo_minimo())
    item = servicio.explain("75000001", UserProfile(valued_labels=["en:organic"]))
    assert item.explanation is not None
    assert item.d3 == 100.0
    assert item.explanation.dimensions["D3"].subscore == 100.0
    assert item.explanation.allergy_status == "apto"
    assert "D1" in item.explanation.dimensions


def test_alternativas_solo_el_mismo_grupo_y_la_banda_de_ranking() -> None:
    servicio = RankingService(_catalogo_minimo())
    resultado = servicio.alternatives("75000001", UserProfile())
    assert resultado.reason == "ok"
    assert resultado.category == "en:breads"
    assert resultado.code == "75000001"
    # 01 es el origen. 04 solo tiene D2: cobertura < 0.5, fuera del ranking.
    assert [item.code for item in resultado.items] == ["75000002", "75000005", "75000003"]
    assert resultado.total == 3
    assert resultado.items[0].rank == 1
    assert resultado.items[0].d1 == 70.0
    assert resultado.items[0].band == "ranking"
    assert resultado.items[0].explanation is not None


def test_alternativas_ignoran_otra_categoria_y_el_precio() -> None:
    df = _catalogo_minimo().df.copy()
    df.loc[df["code"] == "75000002", "categoria_referencia"] = "en:milks"
    df["price"] = [10.0, 180.0, 12.0, 12.0, 12.0]
    df["price_status"] = "REAL"
    servicio = RankingService(Catalog(df=df, snapshot_id="test_snapshot"))
    perfil = UserProfile()
    resultado = servicio.alternatives("75000001", perfil)
    assert "75000002" not in {item.code for item in resultado.items}
    caro = df.copy()
    caro["price"] = 999.0
    caro["price_status"] = "SYNTHETIC"
    otro = RankingService(Catalog(df=caro, snapshot_id="test_snapshot")).alternatives("75000001", perfil)
    assert [(i.code, i.score) for i in resultado.items] == [(i.code, i.score) for i in otro.items]


def test_alternativas_sin_categoria_no_inventan_grupo() -> None:
    df = _catalogo_minimo().df.copy()
    df.loc[df["code"] == "75000001", "categoria_referencia"] = None
    resultado = RankingService(Catalog(df=df, snapshot_id="test_snapshot")).alternatives(
        "75000001", UserProfile()
    )
    assert resultado.reason == "sin_categoria"
    assert resultado.category is None
    assert resultado.items == []
    assert resultado.total == 0


def test_alternativas_vacias_si_el_grupo_no_entra_al_ranking() -> None:
    servicio = RankingService(_catalogo_minimo())
    perfil = UserProfile(allergen_tags=["en:gluten"], diet="vegano")
    resultado = servicio.alternatives("75000003", perfil)
    # 03 declara leche y es non-vegan: el origen no se lista. El resto del grupo
    # queda excluido o no verificable con este perfil.
    assert resultado.reason == "sin_opciones"
    assert resultado.category == "en:breads"
    assert resultado.items == []


def test_alternativas_recortan_a_cinco_sin_perder_el_total() -> None:
    filas = []
    for indice in range(7):
        filas.append(
            {
                "code": f"7500001{indice}",
                "product_name": f"Pan {indice}",
                "categoria_referencia": "en:breads",
                "d1": float(90 - indice),
                "d2": 80.0,
                "labels_tags": None,
                "allergens": "en:milk",
                "traces": None,
                "ingredients_analysis_tags": "en:vegan",
                "product_name_flag_respaldo_usado": False,
                "nova_group": 1.0,
                "additives_n": 0.0,
            }
        )
    filas.append(
        {
            "code": "75000020",
            "product_name": "Leche",
            "categoria_referencia": "en:milks",
            "d1": 99.0,
            "d2": 99.0,
            "labels_tags": None,
            "allergens": "en:milk",
            "traces": None,
            "ingredients_analysis_tags": "en:vegan",
            "product_name_flag_respaldo_usado": False,
            "nova_group": 1.0,
            "additives_n": 0.0,
        }
    )
    servicio = RankingService(Catalog(df=pd.DataFrame(filas), snapshot_id="test_snapshot"))
    resultado = servicio.alternatives("75000010", UserProfile())
    assert resultado.reason == "ok"
    assert resultado.total == 6
    assert [item.code for item in resultado.items] == [
        "75000011",
        "75000012",
        "75000013",
        "75000014",
        "75000015",
    ]
    assert "75000020" not in {item.code for item in resultado.items}
