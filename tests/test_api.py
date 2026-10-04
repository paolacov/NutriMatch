"""Pruebas HTTP de FastAPI: catálogo sintético, no el Parquet de 16.851 filas."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from nutrimatch.api.app import create_app
from nutrimatch.engine.demo_price import precio_demostracion_mxn
from nutrimatch.schemas.profile import UserProfile
from nutrimatch.services.catalog import Catalog
from nutrimatch.services.product import detalle_desde_fila
from tests.test_ranking_service import _catalogo_minimo


def _catalogo_con_ficha() -> Catalog:
    base = _catalogo_minimo().df.copy()
    base["product_name_homologated"] = base["product_name"]
    base["product_name_status"] = "DERIVED"
    base["brand_original"] = ["Bimbo", "Quaker", "Gamesa", None, "Capullo"]
    base["brand_status"] = ["DERIVED", "DERIVED", "DERIVED", "UNAVAILABLE", "DERIVED"]
    base["quantity"] = "100 g"
    base["price"] = ["20.50", None, None, None, "15"]
    base["price_status"] = ["REAL", "UNAVAILABLE", "UNAVAILABLE", "UNAVAILABLE", "REAL"]
    base["price_source"] = ["open_prices", None, None, None, "qqp_profeco"]
    base["sugars_100g_saneado"] = [1.2, None, None, None, 0.0]
    return Catalog(df=base, snapshot_id="test_snapshot")


def _client(tmp_path: Path, catalog: Catalog | None = None) -> TestClient:
    app = create_app(catalog=catalog or _catalogo_con_ficha(), db_path=tmp_path / "api.db")
    return TestClient(app)


def test_meta(tmp_path: Path) -> None:
    respuesta = _client(tmp_path).get("/meta")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["snapshot_id"] == "test_snapshot"
    assert cuerpo["n_products"] == 5
    assert cuerpo["n_puntuable"] == 0
    assert cuerpo["engine_version"]


def test_meta_cuenta_universo_puntuable(tmp_path: Path) -> None:
    catalogo = _catalogo_con_ficha()
    catalogo.df["universo_puntuable"] = [True, False, True, False, False]
    cuerpo = _client(tmp_path, catalogo).get("/meta").json()
    assert cuerpo["n_puntuable"] == 2


def test_search_por_nombre_y_tope(tmp_path: Path) -> None:
    cliente = _client(tmp_path)
    pan = cliente.get("/search", params={"q": "pan"})
    assert pan.status_code == 200
    assert [p["code"] for p in pan.json()] == ["75000001"]
    assert pan.json()[0]["name"]["value"] == "Pan integral"
    limitado = cliente.get("/search", params={"q": "", "limit": 2})
    assert len(limitado.json()) == 2


def test_product_precio_real_y_demostracion_no_se_confunden(tmp_path: Path) -> None:
    cliente = _client(tmp_path)
    real = cliente.get("/products/75000001").json()
    assert real["price"]["status"] == "REAL"
    assert real["price"]["value"] == 20.5
    assert real["price"]["source"] == "open_prices"
    demo = cliente.get("/products/75000002").json()
    assert demo["price"]["status"] == "SYNTHETIC"
    assert demo["price"]["source"] == "demo"
    assert demo["price"]["value"] == float(precio_demostracion_mxn("75000002"))
    assert demo["price"]["value"] != 0


def test_product_404(tmp_path: Path) -> None:
    respuesta = _client(tmp_path).get("/products/no-existe")
    assert respuesta.status_code == 404


def test_products_por_codes(tmp_path: Path) -> None:
    respuesta = _client(tmp_path).get("/products", params={"codes": "75000001,75000002,nope"})
    assert [p["code"] for p in respuesta.json()] == ["75000001", "75000002"]


def test_alternativas_por_http(tmp_path: Path) -> None:
    cliente = _client(tmp_path)
    perfil = UserProfile().model_dump()
    respuesta = cliente.post("/ranking/alternatives", json={"code": "75000001", "profile": perfil})
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["reason"] == "ok"
    assert cuerpo["category"] == "en:breads"
    assert [item["code"] for item in cuerpo["items"]] == ["75000002", "75000005", "75000003"]
    assert cuerpo["items"][0]["explanation"]["dimensions"]["D1"]["subscore"] == 70.0
    assert cliente.get("/events").json() == []
    faltante = cliente.post("/ranking/alternatives", json={"code": "no-existe", "profile": perfil})
    assert faltante.status_code == 404


def test_ranking_y_explain(tmp_path: Path) -> None:
    cliente = _client(tmp_path)
    perfil = UserProfile().model_dump()
    ranking = cliente.post("/ranking", json={"profile": perfil, "query": "Avena", "top_n": 5})
    assert ranking.status_code == 200
    cuerpo = ranking.json()
    assert cuerpo["n_matched"] == 1
    assert cuerpo["snapshot_id"] == "test_snapshot"
    ficha = cliente.post("/ranking/explain", json={"code": "75000001", "profile": perfil})
    assert ficha.status_code == 200
    assert ficha.json()["explanation"] is not None
    assert ficha.json()["code"] == "75000001"


def test_events_acepta_cart_y_rechaza_tipo_inventado(tmp_path: Path) -> None:
    cliente = _client(tmp_path)
    creado = cliente.post("/events", json={"event_type": "cart_item_added", "payload": {"code": "75000001"}})
    assert creado.status_code == 200
    assert creado.json()["event_type"] == "cart_item_added"
    assert creado.json()["payload"]["code"] == "75000001"
    lista = cliente.get("/events").json()
    assert len(lista) == 1
    inventado = cliente.post("/events", json={"event_type": "score_hacked", "payload": {}})
    assert inventado.status_code == 400
    assert cliente.get("/events").json()[0]["event_type"] == "cart_item_added"


def test_ranking_escribe_event_log_sin_cambiar_score(tmp_path: Path) -> None:
    cliente = _client(tmp_path)
    perfil = UserProfile().model_dump()
    primero = cliente.post("/ranking", json={"profile": perfil, "query": "Avena", "top_n": 5}).json()
    segundo = cliente.post("/ranking", json={"profile": perfil, "query": "Avena", "top_n": 5}).json()
    assert primero["ranking"] == segundo["ranking"]
    assert primero["n_matched"] == segundo["n_matched"]
    tipos = [e["event_type"] for e in cliente.get("/events").json()]
    assert tipos.count("ranking_run_created") == 2


def test_perfil_invalido_400(tmp_path: Path) -> None:
    respuesta = _client(tmp_path).post(
        "/ranking",
        json={"profile": {"priority_order": ["D1", "D1", "D1"]}, "query": ""},
    )
    assert respuesta.status_code == 400


def test_from_referencia_frame_usa_nombre_homologado() -> None:
    df = pd.DataFrame(
        [
            {
                "code": "75000001",
                "product_name": None,
                "product_name_homologated": "Pan de caja",
                "product_name_status": "DERIVED",
                "d2": 80.0,
                "percentil_sugars_100g": 0.2,
                "percentil_salt_100g": 0.3,
                "percentil_saturated-fat_100g": 0.1,
                "percentil_fiber_100g": 0.8,
                "percentil_proteins_100g": 0.7,
            }
        ]
    )
    cat = Catalog.from_referencia_frame(df, "test_ref")
    assert cat.df.iloc[0]["product_name"] == "Pan de caja"
    assert cat.df.iloc[0]["d1"] is not None


def test_from_referencia_frame_conserva_nombre_crudo_si_homologado_falta() -> None:
    df = pd.DataFrame(
        [
            {
                "code": "75000002",
                "product_name": "Leche entera",
                "product_name_homologated": None,
            }
        ]
    )
    cat = Catalog.from_referencia_frame(df, "test_ref")
    assert cat.df.iloc[0]["product_name"] == "Leche entera"


def test_detalle_conserva_nombre_literal_nan() -> None:
    """El dataset guarda el nombre real ``NAN``; no es el NaN de pandas (B13)."""
    detalle = detalle_desde_fila(
        pd.Series(
            {
                "code": "7501058623201",
                "product_name_homologated": "NAN",
                "product_name": "NAN",
                "product_name_status": "DERIVED",
                "price": None,
                "price_status": "UNAVAILABLE",
            }
        )
    )
    assert detalle.name.value == "NAN"
    assert detalle.name.status == "DERIVED"

    ausente = detalle_desde_fila(
        pd.Series(
            {
                "code": "2",
                "product_name_homologated": float("nan"),
                "product_name": None,
                "price": None,
                "price_status": "UNAVAILABLE",
            }
        )
    )
    assert ausente.name.value is None
    assert ausente.name.status == "UNAVAILABLE"


def test_detalle_precio_texto_b14_y_ausencia() -> None:
    fila = pd.Series(
        {
            "code": "1",
            "product_name_homologated": "X",
            "product_name_status": "DERIVED",
            "price": "19.0",
            "price_status": "REAL",
            "price_source": "qqp_profeco",
        }
    )
    detalle = detalle_desde_fila(
        pd.Series(
            {
                **fila.to_dict(),
                "main_category": "en:flours",
                "main_category_en": "Flours",
                "categoria_referencia": "en:cereal-flours",
            }
        )
    )
    assert detalle.price.value == 19.0
    assert detalle.category == "en:flours"
    assert detalle.image_hint == "Anaquel"
    vacio = detalle_desde_fila(
        pd.Series({"code": "2", "price": None, "price_status": "UNAVAILABLE"})
    )
    assert vacio.price.status == "SYNTHETIC"
    assert vacio.price.source == "demo"
    assert vacio.price.value == float(precio_demostracion_mxn("2"))
