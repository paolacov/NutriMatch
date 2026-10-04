"""Capa /ai/ask: sin red real. OpenAI se mockea."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from nutrimatch.ai.baseline import TEXTO_RECHAZO, narrar_baseline, narrar_plato
from nutrimatch.ai.client import llm_disponible, narrar_llm, sin_secretos
from nutrimatch.ai.facts import comparar_nutriente
from nutrimatch.ai.guardrails import auditar
from nutrimatch.ai.planner import planear_intent
from nutrimatch.ai.resolver import elegir_texto_final
from nutrimatch.ai.schemas import AskRequest
from nutrimatch.ai.service import preguntar
from nutrimatch.api.app import create_app
from nutrimatch.core.config import get_settings
from nutrimatch.schemas.product import NutrientRow, ProductDetail, ProvenanceValue
from nutrimatch.schemas.profile import UserProfile
from nutrimatch.services.ranking import RankingService
from tests.test_api import _catalogo_con_ficha


def _aislar_sin_clave(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Evita que el `.env` real de la raíz recargue la clave en pruebas de baseline."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("nutrimatch.core.config.project_root", lambda: tmp_path)
    get_settings.cache_clear()


def _detalle(code: str, name: str, protein: float | None) -> ProductDetail:
    return ProductDetail(
        code=code,
        name=ProvenanceValue(value=name, status="REAL"),
        brand=ProvenanceValue(value="Marca", status="REAL"),
        nutrients=[
            NutrientRow(key="proteins", label="Proteína", per100g=protein, unit="g", status="REAL" if protein is not None else "UNAVAILABLE"),
        ],
        allergens=[],
        labels=[],
        price=ProvenanceValue(value=None, status="UNAVAILABLE"),
    )


def test_sin_clave_no_llama_red(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _aislar_sin_clave(monkeypatch, tmp_path)
    llamado = MagicMock()
    monkeypatch.setattr("nutrimatch.ai.client._nuevo_cliente", llamado)
    assert llm_disponible() is False
    resultado = narrar_llm({"product": {"code": "1"}}, intent="explain", message=None)
    assert resultado["ok"] is False
    assert resultado["error_kind"] == "missing_key"
    llamado.assert_not_called()


def test_clave_lee_dotenv_en_la_raiz_del_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-test-dotenv-file-never-call\n", encoding="utf-8")
    monkeypatch.setattr("nutrimatch.core.config.project_root", lambda: tmp_path)
    from nutrimatch.ai.client import _clave_desde_entorno

    assert _clave_desde_entorno() == "sk-test-dotenv-file-never-call"
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    get_settings.cache_clear()


def test_planner_rechaza_fuera_de_nutrimatch() -> None:
    assert planear_intent("ask", "¿cómo va el fútbol hoy?", n_codes=1) == "reject"
    assert planear_intent("ask", "¿qué medicina tomo para el dolor?", n_codes=1) == "reject"


def test_planner_normaliza_producto_explicito() -> None:
    assert planear_intent("normalize_product", None, n_codes=1) == "normalize_product"
    assert planear_intent("normalize_product", None, n_codes=0) == "reject"


def test_comparacion_numerica_en_backend() -> None:
    a = _detalle("1", "A", 10.0)
    b = _detalle("2", "B", 4.0)
    tabla = comparar_nutriente([a, b], "proteins")
    assert tabla["complete"] is True
    assert tabla["highest_code"] == "1"
    c = _detalle("3", "C", None)
    incompleta = comparar_nutriente([a, c], "proteins")
    assert incompleta["complete"] is False
    assert incompleta["highest_code"] is None


def test_critic_fail_usa_baseline() -> None:
    from nutrimatch.ai.payload import construir_payload
    from nutrimatch.schemas.ranking import (
        DimensionExplanation,
        NutrientExplanation,
        ProductExplanation,
        RankingItem,
    )

    expl = ProductExplanation(
        score=None,
        cov=0.0,
        dimensions={
            "D1": DimensionExplanation(subscore=None, weight=0.5, available=False, weighted_contribution=None),
            "D2": DimensionExplanation(subscore=None, weight=0.33, available=False, weighted_contribution=None),
            "D3": DimensionExplanation(subscore=None, weight=0.17, available=False, weighted_contribution=None),
        },
        d1_nutrients={"sugars_100g": NutrientExplanation(percentile=None, sign=-1, available=False, contribution=None)},
        allergy_status="apto",
        diet_status="compatible",
        missing_flags=["D1_sin_dato"],
    )
    item = RankingItem(
        code="00000285",
        product_name=None,
        category=None,
        band="informacion_insuficiente",
        score=None,
        d1=None,
        d2=None,
        d3=None,
        cov=0.0,
        allergy_status="apto",
        diet_status="compatible",
        explanation=expl,
    )
    payload = construir_payload(
        detalle=_detalle("00000285", None, None),  # type: ignore[arg-type]
        item=item,
        profile=UserProfile(),
    )
    payload["product"]["name"] = {"value": None, "status": "UNAVAILABLE", "available": False}
    texto_malo = "Este producto es saludable y cuesta $49.00."
    hallazgos = auditar(texto_malo, payload)
    assert hallazgos
    eleccion = elegir_texto_final(
        baseline="baseline seguro",
        llm={"ok": True, "text": texto_malo, "source": "openai"},
        critic_llm=hallazgos,
    )
    assert eleccion["final_text"] == "baseline seguro"
    assert eleccion["fallback_reason"] == "critic_fail"


def test_variante_de_dato_curioso_cambia_el_tema() -> None:
    from nutrimatch.ai.prompts.base import tema_fun_fact, user_prompt

    assert tema_fun_fact("Dato curioso. Variante 0.") == "la fibra"
    assert tema_fun_fact("Dato curioso. Variante 5.") == "la hidratación"
    cero = user_prompt({}, intent="fun_fact", message="Dato curioso. Variante 0.")
    cinco = user_prompt({}, intent="fun_fact", message="Dato curioso. Variante 5.")
    assert "Tema obligatorio: la fibra" in cero
    assert "Tema obligatorio: la hidratación" in cinco


def test_fun_fact_no_descarta_un_numero_ajeno_al_producto() -> None:
    payload = {
        "intent": "fun_fact",
        "product": {"code": "1", "nutrients": []},
        "decision": {"score": None, "band": "ranking"},
        "constraints": {},
        "availability": {},
        "price": {},
    }
    limpio = auditar("Las leguminosas aportan proteína. El grupo no indica una cantidad personal.", payload)
    assert limpio == []
    salud = auditar("Este alimento es saludable.", payload)
    assert any(h["code"] == "F" for h in salud)


def test_receta_no_afirma_ingrediente_ausente() -> None:
    payload = {
        "intent": "recipe",
        "recipe_context": {
            "observed_ingredients": ["maíz"],
            "claimed_product_ingredients": ["lenteja"],
            "nutrition_available": False,
        },
        "product": {"code": "1", "name": {"value": "Tostada"}},
        "decision": {"score": None, "band": None},
        "constraints": {"allergy_evaluable": False, "diet_evaluable": False},
        "price": {"value": None, "status": "UNAVAILABLE"},
        "availability": {},
    }
    codes = {h["code"] for h in auditar("Usa lenteja del producto.", payload)}
    assert "L" in codes


def test_narrar_plato_resumen_no_receta() -> None:
    texto = narrar_plato(
        {
            "intent": "plato",
            "message": "Resume mi carrito frente a la guía",
            "cart_summary": {
                "n_products": 2,
                "plato": [
                    {"key": "frutas_verduras", "label": "Verduras y frutas", "n": 0, "share": 0},
                    {"key": "cereales", "label": "Cereales", "n": 1, "share": 0.5},
                    {"key": "leguminosas_aoa", "label": "Leguminosas y alimentos de origen animal", "n": 0, "share": 0},
                    {"key": "unclassified", "label": "no clasificado", "n": 1, "share": 0.5},
                ],
            },
            "plato_groups": [
                {"code": "1", "name": "X", "group": "unclassified", "label": "no clasificado"},
            ],
        }
    )
    bajo = texto.lower()
    assert "no clasificado" in bajo
    assert "más espacio" in bajo
    assert "gramos" in bajo
    assert "te recomiendo" not in bajo
    assert "saludable" not in bajo


def test_plato_unclassified_no_se_asigna_grupo() -> None:
    payload = {
        "intent": "plato",
        "plato_groups": [{"code": "1", "name": "X", "group": "unclassified", "label": "no clasificado"}],
        "product": {"code": "1", "name": {"value": "X"}},
        "decision": {"score": None, "band": None},
        "constraints": {"allergy_evaluable": False, "diet_evaluable": False},
        "price": {"value": None, "status": "UNAVAILABLE"},
        "availability": {},
    }
    codes = {h["code"] for h in auditar("Este producto pertenece al grupo cereales.", payload)}
    assert "M" in codes
    limpio = auditar("X: no clasificado. Los datos no permiten asignar un grupo.", payload)
    assert limpio == []


def test_ask_sin_clave_devuelve_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _aislar_sin_clave(monkeypatch, tmp_path)
    catalogo = _catalogo_con_ficha()
    servicio = RankingService(catalogo)
    respuesta = preguntar(
        AskRequest(surface="product", codes=["75000001"], intent="explain"),
        catalogo=catalogo,
        servicio=servicio,
    )
    assert respuesta.source == "baseline"
    assert respuesta.fallback is True
    assert "75000001" in respuesta.text or "Pan" in respuesta.text
    assert "OPENAI" not in respuesta.text
    assert "sk-" not in respuesta.text


def test_ask_respuesta_valida_mock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-never-call")
    get_settings.cache_clear()
    texto = (
        "Pan integral quedó en ranking. El score es 84 sobre 100. "
        "El perfil no declaró alergias."
    )
    monkeypatch.setattr(
        "nutrimatch.ai.service.narrar_llm",
        lambda payload, intent, message: {
            "ok": True,
            "text": texto,
            "error_kind": None,
            "model": "gpt-4o-mini",
            "latency_ms": 12,
            "source": "openai",
        },
    )
    catalogo = _catalogo_con_ficha()
    respuesta = preguntar(
        AskRequest(surface="product", codes=["75000001"], intent="explain"),
        catalogo=catalogo,
        servicio=RankingService(catalogo),
    )
    assert respuesta.source == "llm"
    assert respuesta.fallback is False
    assert respuesta.text == texto


def test_ask_error_api_cae_a_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "nutrimatch.ai.service.narrar_llm",
        lambda payload, intent, message: {
            "ok": False,
            "text": None,
            "error_kind": "timeout",
            "model": "gpt-4o-mini",
            "latency_ms": 30,
        },
    )
    catalogo = _catalogo_con_ficha()
    respuesta = preguntar(
        AskRequest(surface="product", codes=["75000001"], intent="explain"),
        catalogo=catalogo,
        servicio=RankingService(catalogo),
    )
    assert respuesta.source == "baseline"
    assert respuesta.fallback_reason == "timeout"


def test_ask_pregunta_libre_rechazada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _aislar_sin_clave(monkeypatch, tmp_path)
    catalogo = _catalogo_con_ficha()
    respuesta = preguntar(
        AskRequest(surface="search", codes=[], intent="ask", message="¿quién gana el fútbol?"),
        catalogo=catalogo,
        servicio=RankingService(catalogo),
    )
    assert respuesta.intent == "reject"
    assert respuesta.text == TEXTO_RECHAZO


def test_endpoint_ai_ask_y_clave_ausente_en_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _aislar_sin_clave(monkeypatch, tmp_path)
    cliente = TestClient(create_app(catalog=_catalogo_con_ficha(), db_path=tmp_path / "ai.db"))
    cuerpo = cliente.post(
        "/ai/ask",
        json={
            "surface": "product",
            "codes": ["75000001"],
            "intent": "explain",
            "profile": {"priority_order": ["D1", "D2", "D3"]},
        },
    )
    assert cuerpo.status_code == 200
    data = cuerpo.json()
    assert data["source"] == "baseline"
    serial = str(data)
    assert "sk-" not in serial
    assert "OPENAI_API_KEY" not in serial
    assert sin_secretos({"k": "sk-test-abc"})["k"] == "[redactado]"


def test_baseline_reject_constante() -> None:
    assert "fuera de NutriMatch" in narrar_baseline({"intent": "reject"}, intent="reject")


def test_planner_preguntas_contextuales() -> None:
    assert planear_intent("ask", "¿Por qué aparece este producto?", n_codes=1) == "explain"
    assert planear_intent("ask", "¿Qué significa esta información?", n_codes=1) == "nutrition"
    assert planear_intent("ask", "Dato curioso", n_codes=1) == "fun_fact"
    assert planear_intent("ask", "¿Qué diferencias hay?", n_codes=2) == "compare"
    assert planear_intent("ask", "¿Qué puedo preparar con estos productos?", n_codes=2) == "recipe"
    assert planear_intent("ask", "¿Por qué un producto queda no clasificado?", n_codes=2) == "plato"
    assert planear_intent("plato", "¿Por qué un producto queda no clasificado?", n_codes=2) == "plato"
    assert planear_intent("ask", "¿Por qué aparece este producto?", n_codes=1) == "explain"


def test_ask_nutrition_null_y_fun_fact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _aislar_sin_clave(monkeypatch, tmp_path)
    catalogo = _catalogo_con_ficha()
    servicio = RankingService(catalogo)
    nutri = preguntar(
        AskRequest(surface="product", codes=["75000004"], intent="nutrition"),
        catalogo=catalogo,
        servicio=servicio,
    )
    assert nutri.intent == "nutrition"
    assert "información no disponible" in nutri.text.lower() or "no hay valores" in nutri.text.lower()
    assert nutri.observability is not None
    assert nutri.observability.fallback is True
    curioso = preguntar(
        AskRequest(surface="product", codes=["75000001"], intent="fun_fact"),
        catalogo=catalogo,
        servicio=servicio,
    )
    assert curioso.intent == "fun_fact"
    assert "saludable" not in curioso.text.lower()
    assert "nova" not in curioso.text.lower()
    otro = preguntar(
        AskRequest(
            surface="product",
            codes=["75000001"],
            intent="fun_fact",
            message="Dato curioso. Variante 1.",
        ),
        catalogo=catalogo,
        servicio=servicio,
    )
    assert otro.text != curioso.text
    assert "75000001" not in otro.text


def test_ask_alergia_dieta_y_receta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _aislar_sin_clave(monkeypatch, tmp_path)
    catalogo = _catalogo_con_ficha()
    servicio = RankingService(catalogo)
    perfil = UserProfile(allergen_tags=["en:gluten"], diet="vegano", priority_order=["D1", "D2", "D3"])
    alertas = preguntar(
        AskRequest(surface="alerts", codes=["75000001"], intent="alerts", profile=perfil),
        catalogo=catalogo,
        servicio=servicio,
    )
    assert alertas.intent == "alerts"
    assert "apto" in alertas.text.lower() or "alérgen" in alertas.text.lower()
    receta = preguntar(
        AskRequest(surface="recipes", codes=["75000001"], intent="recipe"),
        catalogo=catalogo,
        servicio=servicio,
    )
    assert receta.intent == "recipe"
    assert receta.recipe is not None
    assert receta.recipe.extra_suggested == []
    assert receta.recipe.steps == []
    assert receta.recipes == []
    assert receta.recipe_products
    assert receta.recipe_products[0].display_name
    assert "saludable" not in receta.text.lower()
    assert "sin un modelo" in receta.text.lower()


def test_ask_comparacion_y_no_cambia_ranking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _aislar_sin_clave(monkeypatch, tmp_path)
    catalogo = _catalogo_con_ficha()
    servicio = RankingService(catalogo)
    perfil = UserProfile()
    antes = servicio.explain("75000001", perfil)
    respuesta = preguntar(
        AskRequest(surface="compare", codes=["75000001", "75000002"], intent="compare"),
        catalogo=catalogo,
        servicio=servicio,
    )
    despues = servicio.explain("75000001", perfil)
    assert respuesta.intent == "compare"
    assert respuesta.comparison is not None
    assert antes.score == despues.score
    assert antes.d1 == despues.d1
    assert antes.d2 == despues.d2
    assert antes.d3 == despues.d3
    assert antes.cov == despues.cov
    assert antes.band == despues.band


def test_ask_respuesta_invalida_cae_a_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake")
    get_settings.cache_clear()
    monkeypatch.setattr(
        "nutrimatch.ai.service.narrar_llm",
        lambda payload, intent, message: {
            "ok": False,
            "text": None,
            "error_kind": "schema",
            "model": "gpt-4o-mini",
            "latency_ms": 8,
            "usage": {"prompt_tokens": 10, "completion_tokens": 0, "total_tokens": 10},
        },
    )
    respuesta = preguntar(
        AskRequest(surface="product", codes=["75000001"], intent="explain"),
        catalogo=_catalogo_con_ficha(),
        servicio=RankingService(_catalogo_con_ficha()),
    )
    assert respuesta.source == "baseline"
    assert respuesta.fallback_reason == "schema"
    assert respuesta.observability is not None
    assert respuesta.observability.total_tokens == 10
    assert "sk-" not in str(respuesta.model_dump())


def test_ask_plato_no_cae_a_explain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _aislar_sin_clave(monkeypatch, tmp_path)
    catalogo = _catalogo_con_ficha()
    respuesta = preguntar(
        AskRequest(
            surface="cart",
            codes=["75000001"],
            intent="plato",
            message="¿Por qué un producto queda no clasificado?",
        ),
        catalogo=catalogo,
        servicio=RankingService(catalogo),
    )
    assert respuesta.intent == "plato"
    assert "no clasificado" in respuesta.text.lower() or "plato" in respuesta.text.lower()


def test_receta_llm_llena_extras_y_pasos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-never-call")
    get_settings.cache_clear()
    catalogo = _catalogo_con_ficha()
    catalogo.df = catalogo.df.copy()
    catalogo.df["ingredients_text"] = ["harina de trigo, agua, sal", None, None, None, None]
    monkeypatch.setattr(
        "nutrimatch.ai.service.narrar_llm",
        lambda payload, intent, message: {
            "ok": True,
            "text": (
                "Preparación con harina de trigo observada. "
                "Adicionales: cilantro. No se calculó nutrición de la receta."
            ),
            "error_kind": None,
            "model": "gpt-4o-mini",
            "latency_ms": 9,
            "source": "openai",
            "extra_suggested": ["sal", "cilantro"],
            "steps": ["Mezcla la harina con agua.", "Añade cilantro y sirve."],
            "recipe_name": "Tostada rápida",
        },
    )
    respuesta = preguntar(
        AskRequest(surface="recipes", codes=["75000001"], intent="recipe"),
        catalogo=catalogo,
        servicio=RankingService(catalogo),
    )
    assert respuesta.source == "llm"
    assert respuesta.recipe is not None
    assert respuesta.recipe.name == "Tostada rápida"
    assert "cilantro" in respuesta.recipe.extra_suggested
    assert "sal" not in {e.lower() for e in respuesta.recipe.extra_suggested}
    assert respuesta.recipe.steps == ["Mezcla la harina con agua.", "Añade cilantro y sirve."]
    assert any("pan" in x.lower() for x in respuesta.recipe.available_ingredients)
    assert len(respuesta.recipes) == 1
    assert respuesta.recipes[0].name == "Tostada rápida"
    assert respuesta.recipes[0].used_products
    assert respuesta.recipes[0].steps


def test_extra_no_duplica_nombre_de_producto_ni_excede_pasos() -> None:
    from nutrimatch.ai.service import ensamblar_receta

    hechos = {
        "recipe_context": {
            "observed_ingredients": ["leche", "azúcar"],
            "product_names": ["Cajeta Coronado", "Pan integral"],
        }
    }
    receta = ensamblar_receta(
        hechos,
        "Pasos cortos.",
        source="llm",
        extras=["cajeta", "plátano", "leche"],
        pasos=[
            "Tuesta el pan.",
            "Agrega cajeta.",
            "Añade plátano.",
            "Corta en rebanadas.",
            "Sirve.",
            "Guarda el resto.",
        ],
        nombre="Tostadas con cajeta",
    )
    assert receta is not None
    assert receta.name == "Tostadas con cajeta"
    assert receta.short_description == ""
    assert receta.used_products
    assert "plátano" in receta.extra_suggested
    assert "cajeta" not in {e.lower() for e in receta.extra_suggested}
    assert "leche" not in {e.lower() for e in receta.extra_suggested}
    assert receta.steps == [
        "Tuesta el pan.",
        "Agrega cajeta.",
        "Añade plátano.",
        "Corta en rebanadas.",
        "Sirve.",
    ]


def test_receta_dos_productos_no_cambia_ranking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _aislar_sin_clave(monkeypatch, tmp_path)
    catalogo = _catalogo_con_ficha()
    servicio = RankingService(catalogo)
    perfil = UserProfile()
    antes = servicio.explain("75000001", perfil)
    respuesta = preguntar(
        AskRequest(
            surface="recipes",
            codes=["75000001", "75000002"],
            intent="recipe",
            message="¿Qué puedo preparar con Pan integral y Avena?",
        ),
        catalogo=catalogo,
        servicio=servicio,
    )
    despues = servicio.explain("75000001", perfil)
    assert respuesta.intent == "recipe"
    assert respuesta.source == "baseline"
    assert respuesta.recipe is not None
    assert respuesta.recipe.extra_suggested == []
    assert respuesta.recipe.steps == []
    assert respuesta.recipes == []
    assert antes.score == despues.score
    assert antes.d1 == despues.d1
    assert antes.cov == despues.cov


def test_critic_receta_extra_como_producto_y_dieta() -> None:
    payload = {
        "intent": "recipe",
        "recipe_context": {
            "observed_ingredients": ["maíz"],
            "llm_extra_suggested": ["cilantro"],
            "nutrition_available": False,
        },
        "product": {"code": "1", "name": {"value": "Tostada"}},
        "decision": {"score": None, "band": None},
        "constraints": {"allergy_evaluable": False, "diet_evaluable": False},
        "price": {"value": None, "status": "UNAVAILABLE"},
        "availability": {},
    }
    extra_como_dato = auditar(
        "El cilantro observado en el registro completa la receta.",
        payload,
    )
    assert "L" in {h["code"] for h in extra_como_dato}
    dieta = auditar("La receta es vegana y libre de alérgenos.", payload)
    assert "L" in {h["code"] for h in dieta}


def test_lote_recetas_prioriza_varios_y_omite_nombre_de_producto() -> None:
    from nutrimatch.ai.service import ensamblar_lote_recetas

    hechos = {
        "recipe_context": {
            "observed_ingredients": ["leche", "azúcar"],
            "product_names": ["Cajeta", "Pan"],
            "display_names": ["Cajeta", "Pan"],
        }
    }
    lote = ensamblar_lote_recetas(
        hechos,
        "Ideas de platillo.",
        source="llm",
        ideas=[
            {
                "recipe_name": "Cajeta",
                "short_description": "El producto del carrito.",
                "used_products": ["Cajeta"],
                "extra_suggested": [],
                "steps": ["Sirve."],
            },
            {
                "recipe_name": "Pan tostado",
                "short_description": "Una base simple.",
                "used_products": ["Pan"],
                "extra_suggested": [],
                "steps": ["Tuesta el pan."],
            },
            {
                "recipe_name": "Tostadas con cajeta",
                "short_description": "Una opción rápida y sencilla",
                "used_products": ["Cajeta", "Pan"],
                "extra_suggested": ["cajeta", "plátano"],
                "steps": ["Tuesta el pan.", "Agrega el plátano.", "Añade la cajeta.", "Sirve."],
            },
        ],
    )
    assert [r.name for r in lote] == ["Tostadas con cajeta", "Pan tostado"]
    primero = lote[0]
    assert primero.short_description == "Una opción rápida y sencilla"
    assert primero.used_products == ["Cajeta", "Pan"]
    assert "plátano" in primero.extra_suggested
    assert "cajeta" not in {e.lower() for e in primero.extra_suggested}
    assert 1 <= len(lote) <= 6


def test_lote_acepta_tres_ideas_con_uno_o_varios() -> None:
    from nutrimatch.ai.prompts.base import addenda_intent
    from nutrimatch.ai.service import MIN_RECETAS, ensamblar_lote_recetas

    addenda = addenda_intent("recipe")
    assert "Mínimo 3" in addenda
    assert "un solo producto o varios juntos" in addenda

    hechos = {
        "recipe_context": {
            "observed_ingredients": ["huevo", "harina"],
            "product_names": ["Tortillas de harina", "Huevo"],
            "display_names": ["Tortillas de harina", "Huevo"],
        }
    }
    lote = ensamblar_lote_recetas(
        hechos,
        "Tres ideas con lo que hay en el carrito.",
        source="llm",
        ideas=[
            {
                "recipe_name": "Tacos de huevo",
                "short_description": "Los dos juntos.",
                "used_products": ["Tortillas de harina", "Huevo"],
                "extra_suggested": [],
                "steps": ["Calienta las tortillas.", "Cocina el huevo.", "Arma los tacos."],
            },
            {
                "recipe_name": "Huevos revueltos",
                "short_description": "Solo el huevo.",
                "used_products": ["Huevo"],
                "extra_suggested": [],
                "steps": ["Bate los huevos.", "Cocina."],
            },
            {
                "recipe_name": "Quesadillas sencillas",
                "short_description": "Solo la tortilla.",
                "used_products": ["Tortillas de harina"],
                "extra_suggested": ["queso"],
                "steps": ["Calienta la tortilla.", "Agrega queso.", "Dobla."],
            },
        ],
    )
    assert len(lote) >= MIN_RECETAS
    assert [r.name for r in lote] == [
        "Tacos de huevo",
        "Huevos revueltos",
        "Quesadillas sencillas",
    ]
    assert lote[0].used_products == ["Tortillas de harina", "Huevo"]
    assert lote[1].used_products == ["Huevo"]
    assert lote[2].used_products == ["Tortillas de harina"]


def test_lote_baseline_sin_clave_no_inventa_recetas() -> None:
    from nutrimatch.ai.service import ensamblar_lote_recetas

    lote = ensamblar_lote_recetas(
        {"recipe_context": {"display_names": ["Cajeta"], "product_names": ["Cajeta"]}},
        "Sin un modelo de lenguaje no se proponen recetas.",
        source="baseline",
        ideas=[
            {
                "recipe_name": "Tostadas con cajeta",
                "steps": ["Tuesta.", "Unta."],
                "used_products": ["Cajeta"],
            }
        ],
    )
    assert lote == []


def test_lote_llm_varios_productos_no_cambia_ranking(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-fake-never-call")
    get_settings.cache_clear()
    catalogo = _catalogo_con_ficha()
    servicio = RankingService(catalogo)
    perfil = UserProfile()
    antes = servicio.explain("75000001", perfil)
    monkeypatch.setattr(
        "nutrimatch.ai.service.narrar_llm",
        lambda payload, intent, message: {
            "ok": True,
            "text": "Ideas con pan y avena. No se calculó nutrición de la receta.",
            "error_kind": None,
            "model": "gpt-4o-mini",
            "latency_ms": 11,
            "source": "openai",
            "recipes": [
                {
                    "recipe_name": "Bowl de avena",
                    "short_description": "Desayuno simple.",
                    "used_products": ["Avena"],
                    "extra_suggested": ["leche"],
                    "steps": ["Calienta la avena.", "Sirve."],
                },
                {
                    "recipe_name": "Tostada de avena",
                    "short_description": "Aprovecha ambos.",
                    "used_products": ["Pan integral", "Avena"],
                    "extra_suggested": ["miel"],
                    "steps": ["Tuesta el pan.", "Agrega avena.", "Sirve."],
                },
            ],
        },
    )
    respuesta = preguntar(
        AskRequest(
            surface="recipes",
            codes=["75000001", "75000002"],
            intent="recipe",
        ),
        catalogo=catalogo,
        servicio=servicio,
    )
    despues = servicio.explain("75000001", perfil)
    assert respuesta.source == "llm"
    assert [r.name for r in respuesta.recipes][0] == "Tostada de avena"
    assert len(respuesta.recipes[0].used_products) >= len(respuesta.recipes[-1].used_products)
    assert "miel" in respuesta.recipes[0].extra_suggested
    assert antes.score == despues.score
    assert antes.d1 == despues.d1
    assert antes.cov == despues.cov

