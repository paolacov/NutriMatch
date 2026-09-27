"""Cierre funcional del MVP: casos límite sobre el Parquet 20260927.

No toca fórmulas. No imputa. No genera sintéticos. Comprueba que los huecos
del dataset se comportan como NULL + bandera, no como 0 ni como «no cumple».
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nutrimatch.api.app import create_app
from nutrimatch.core.config import Settings, get_settings
from nutrimatch.services.catalog import Catalog
from nutrimatch.services.ranking import filtrar_por_query

from tests.test_catalog_referencia_api import ANA, CARO, CODE_NO_PUNTUABLE, CODE_PRECIO_REAL, CODE_PUNTUABLE, CODE_SIN_NOMBRE

REPO_ROOT = Path(__file__).resolve().parents[1]
N = 16_851
N_NOMBRE_HOMOLOGADO = 15_172
N_PUNTUABLE = 5_864

CODE_NOMBRE_LITERAL_NAN = "7501058623201"
CODE_PUNTUABLE_SIN_PRECIO = "0000103227240"
CODE_VEGANO = "0000880688789"

BETO = {
    "profile": {
        "allergen_tags": [],
        "diet": None,
        "valued_labels": ["en:fair-trade"],
        "priority_order": ["D2", "D1", "D3"],
    },
    "query": "",
    "top_n": 3,
}

PERFIL_LECHE = {
    **ANA["profile"],
    "allergen_tags": ["en:milk"],
}
PERFIL_GLUTEN = {
    **ANA["profile"],
    "allergen_tags": ["en:gluten"],
}
PERFIL_VEGANO = {
    **ANA["profile"],
    "diet": "vegano",
}


@pytest.fixture(scope="module")
def settings_api() -> Settings:
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture(scope="module")
def catalogo(settings_api: Settings) -> Catalog:
    return Catalog.from_referencia(settings_api)


@pytest.fixture(scope="module")
def cliente(catalogo: Catalog, tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    db = tmp_path_factory.mktemp("cierre_mvp") / "api.db"
    return TestClient(create_app(catalog=catalogo, db_path=db))


def _explain(cliente: TestClient, code: str, profile: dict) -> dict:
    respuesta = cliente.post("/ranking/explain", json={"code": code, "profile": profile})
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _ficha(cliente: TestClient, code: str) -> dict:
    respuesta = cliente.get(f"/products/{code}")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def _nutrientes_nulos_no_son_cero(ficha: dict) -> None:
    for fila in ficha["nutrients"]:
        if fila["per100g"] is None:
            assert fila["status"] == "UNAVAILABLE"
        else:
            assert fila["status"] in {"REAL", "DERIVED"}


def test_cobertura_busqueda_gtin_y_nombre(catalogo: Catalog) -> None:
    assert len(catalogo.df) == N
    assert catalogo.df["code"].nunique() == N
    assert int(catalogo.n_puntuable()) == N_PUNTUABLE
    con_nombre = catalogo.df["product_name"].map(
        lambda v: isinstance(v, str) and bool(v.strip())
    )
    assert int(con_nombre.sum()) == N_NOMBRE_HOMOLOGADO


def test_busqueda_gtin_exacto(cliente: TestClient) -> None:
    hits = cliente.get("/search", params={"q": CODE_PRECIO_REAL, "limit": 20}).json()
    assert any(p["code"] == CODE_PRECIO_REAL for p in hits)


def test_busqueda_nombre_case_y_espacios(cliente: TestClient) -> None:
    for q in ("Cajeta", "cajeta", " CAJETA "):
        hits = cliente.get("/search", params={"q": q, "limit": 20}).json()
        assert CODE_PRECIO_REAL in [p["code"] for p in hits]


def test_busqueda_conserva_nombre_literal_nan(cliente: TestClient, catalogo: Catalog) -> None:
    fila = catalogo.df.loc[catalogo.df["code"] == CODE_NOMBRE_LITERAL_NAN].iloc[0]
    assert fila["product_name"] == "NAN"
    ficha = _ficha(cliente, CODE_NOMBRE_LITERAL_NAN)
    assert ficha["name"]["value"] == "NAN"
    hits = cliente.get("/search", params={"q": "NAN", "limit": 100}).json()
    assert CODE_NOMBRE_LITERAL_NAN in [p["code"] for p in hits]
    assert any(p["name"]["value"] == "NAN" for p in hits if p["code"] == CODE_NOMBRE_LITERAL_NAN)


def test_caso_1_completo_precio_real(cliente: TestClient) -> None:
    ficha = _ficha(cliente, CODE_PRECIO_REAL)
    assert ficha["name"]["value"]
    assert ficha["price"]["status"] == "REAL"
    assert ficha["price"]["value"] is not None
    assert ficha["price"]["source"] == "qqp_profeco"
    assert ficha["ingredients"]
    assert ficha["allergens"] == ["en:milk"]
    item = _explain(cliente, CODE_PRECIO_REAL, ANA["profile"])
    assert item["score"] is not None
    assert item["d1"] is not None
    assert item["d2"] is not None


def test_caso_2_completo_sin_precio(cliente: TestClient) -> None:
    ficha = _ficha(cliente, CODE_PUNTUABLE_SIN_PRECIO)
    assert ficha["price"]["status"] == "UNAVAILABLE"
    assert ficha["price"]["value"] is None
    item = _explain(cliente, CODE_PUNTUABLE_SIN_PRECIO, ANA["profile"])
    assert item["score"] is not None
    assert item["d3"] is None


def test_caso_3_y_4_no_puntuable_con_score_a26(cliente: TestClient, catalogo: Catalog) -> None:
    fila = catalogo.df.loc[catalogo.df["code"] == CODE_NO_PUNTUABLE].iloc[0]
    assert not bool(fila["universo_puntuable"])
    ficha = _ficha(cliente, CODE_NO_PUNTUABLE)
    assert ficha["price"]["value"] is None
    _nutrientes_nulos_no_son_cero(ficha)
    item = _explain(cliente, CODE_NO_PUNTUABLE, ANA["profile"])
    assert item["d1"] is None
    assert item["d2"] is not None
    assert item["score"] == pytest.approx(41.67, abs=0.05)
    assert item["cov"] >= 0.5
    assert item["explanation"]["dimensions"]["D1"]["available"] is False
    assert item["explanation"]["dimensions"]["D1"]["subscore"] is None


def test_caso_5_sin_nombre(cliente: TestClient) -> None:
    ficha = _ficha(cliente, CODE_SIN_NOMBRE)
    assert ficha["name"]["value"] is None
    assert ficha["name"]["status"] == "UNAVAILABLE"


def test_caso_6_sin_nutricion(cliente: TestClient) -> None:
    ficha = _ficha(cliente, CODE_SIN_NOMBRE)
    assert all(n["per100g"] is None for n in ficha["nutrients"])
    _nutrientes_nulos_no_son_cero(ficha)


def test_caso_7_sin_ingredientes(cliente: TestClient) -> None:
    ficha = _ficha(cliente, CODE_SIN_NOMBRE)
    assert ficha["ingredients"] == []


def test_caso_8_sin_alergenos_es_no_verificable(cliente: TestClient) -> None:
    ficha = _ficha(cliente, CODE_SIN_NOMBRE)
    assert ficha["allergens"] == []
    leche = _explain(cliente, CODE_SIN_NOMBRE, PERFIL_LECHE)
    assert leche["allergy_status"] == "no_verificable"
    assert leche["explanation"]["allergy_status"] == "no_verificable"


def test_caso_9_sin_labels_d3_none(cliente: TestClient) -> None:
    ficha = _ficha(cliente, CODE_PRECIO_REAL)
    assert ficha["labels"] == []
    item = _explain(cliente, CODE_PRECIO_REAL, ANA["profile"])
    assert item["d3"] is None
    assert item["explanation"]["dimensions"]["D3"]["available"] is False
    assert item["explanation"]["dimensions"]["D3"]["subscore"] is None


def test_caso_10_d3_null_caro_y_producto_sin_labels(cliente: TestClient) -> None:
    caro = _explain(cliente, CODE_PUNTUABLE, CARO["profile"])
    assert caro["d3"] is None
    assert caro["explanation"]["dimensions"]["D3"]["available"] is False
    assert caro["explanation"]["score"] is not None

    ana_sin_labels = _explain(cliente, CODE_PUNTUABLE_SIN_PRECIO, ANA["profile"])
    assert ana_sin_labels["d3"] is None
    assert ana_sin_labels["score"] is not None


def test_caso_11_cov_insuficiente(cliente: TestClient) -> None:
    item = _explain(cliente, CODE_SIN_NOMBRE, ANA["profile"])
    assert item["score"] is None
    assert item["cov"] < 0.5
    assert item["band"] == "informacion_insuficiente"


def test_caso_12_producto_inexistente(cliente: TestClient) -> None:
    respuesta = cliente.get("/products/no-existe-xyz")
    assert respuesta.status_code == 404
    explain = cliente.post(
        "/ranking/explain",
        json={"code": "no-existe-xyz", "profile": ANA["profile"]},
    )
    assert explain.status_code == 404


def test_caso_13_gtin_invalido(cliente: TestClient) -> None:
    for code in ("12", "abc", "!!!", "123"):
        assert cliente.get(f"/products/{code}").status_code == 404


def test_caso_14_busqueda_sin_resultados(cliente: TestClient) -> None:
    hits = cliente.get("/search", params={"q": "zzzxxxyyynutrimatch_no_hit_999"}).json()
    assert hits == []


def test_personalizacion_ana_beto_caro(cliente: TestClient) -> None:
    ana = cliente.post("/ranking", json=ANA).json()
    beto = cliente.post("/ranking", json=BETO).json()
    caro = cliente.post("/ranking", json=CARO).json()
    assert ana["ranking"]["total"] == 7_334
    assert caro["ranking"]["total"] == 5_877
    assert beto["ranking"]["items"][0]["score"] is not None
    assert caro["ranking"]["items"][0]["d3"] is None
    for cuerpo in (ana, beto, caro):
        item = cuerpo["ranking"]["items"][0]
        expl = item["explanation"]
        assert expl is not None
        assert "score" in expl
        assert "cov" in expl
        assert set(expl["dimensions"]) == {"D1", "D2", "D3"}


def test_alertas_tres_estados_alergia_y_dieta(cliente: TestClient) -> None:
    assert _explain(cliente, CODE_PRECIO_REAL, PERFIL_LECHE)["allergy_status"] == "no_apto"
    assert _explain(cliente, CODE_PRECIO_REAL, PERFIL_GLUTEN)["allergy_status"] == "apto"
    assert _explain(cliente, CODE_SIN_NOMBRE, PERFIL_LECHE)["allergy_status"] == "no_verificable"

    assert _explain(cliente, CODE_VEGANO, PERFIL_VEGANO)["diet_status"] == "compatible"
    assert _explain(cliente, CODE_PRECIO_REAL, PERFIL_VEGANO)["diet_status"] == "incompatible"
    assert _explain(cliente, CODE_SIN_NOMBRE, PERFIL_VEGANO)["diet_status"] == "no_verificable"


def test_precio_unavailable_nunca_cero(cliente: TestClient) -> None:
    for code in (CODE_NO_PUNTUABLE, CODE_SIN_NOMBRE, CODE_PUNTUABLE_SIN_PRECIO):
        ficha = _ficha(cliente, code)
        assert ficha["price"]["value"] is None
        assert ficha["price"]["status"] == "UNAVAILABLE"


def test_filtrar_por_query_no_convierte_nan_literal_en_nulo(catalogo: Catalog) -> None:
    hits = filtrar_por_query(catalogo.df, "NAN")
    assert CODE_NOMBRE_LITERAL_NAN in set(hits["code"].astype(str))
    vacios = filtrar_por_query(catalogo.df, "zzzxxxyyynutrimatch_no_hit_999")
    assert vacios.empty
