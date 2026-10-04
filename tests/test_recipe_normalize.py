"""Normalización culinaria de nombres: solo para recetas, no toca el catálogo."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from nutrimatch.ai.recipe_normalize import (
    aplicar_refinamiento_llm,
    limpiar_cache_normalizacion,
    normalizar_nombre_culinario,
)
from nutrimatch.ai.schemas import AskRequest
from nutrimatch.ai.service import ensamblar_receta, preguntar
from nutrimatch.services.ranking import RankingService
from tests.test_api import _catalogo_con_ficha


def setup_function() -> None:
    limpiar_cache_normalizacion()


def test_marca_producto_cantidad() -> None:
    ctx = normalizar_nombre_culinario(
        original_name="Danone Yogur Griego Natural 150g",
        brand="Danone",
        quantity="150g",
    )
    assert ctx.original_name == "Danone Yogur Griego Natural 150g"
    assert ctx.display_name == "Yogur griego"
    assert ctx.culinary_name == "yogur"
    assert ctx.original_name != ctx.display_name


def test_prefijo_idioma() -> None:
    ctx = normalizar_nombre_culinario(
        original_name="FR: Yaourt nature entier 4x125g Carrefour",
        brand="Carrefour",
    )
    assert ctx.original_name == "FR: Yaourt nature entier 4x125g Carrefour"
    assert ctx.display_name == "Yogur natural"
    assert ctx.culinary_name == "yogur"


def test_todo_mayusculas() -> None:
    ctx = normalizar_nombre_culinario(original_name="CAJETA DE LECHE DE CABRA 660G")
    assert ctx.original_name == "CAJETA DE LECHE DE CABRA 660G"
    assert ctx.display_name == "Cajeta"
    assert ctx.culinary_name == "cajeta"


def test_descripcion_comercial_larga() -> None:
    ctx = normalizar_nombre_culinario(
        original_name="Delicioso Yogur Natural Entero Con Cultivos Lácticos Premium Edición Limitada 125g",
        brand=None,
    )
    assert ctx.original_name.startswith("Delicioso")
    assert ctx.display_name == "Yogur natural"
    assert ctx.original_name != ctx.display_name


def test_sin_product_name_con_generic_name() -> None:
    ctx = normalizar_nombre_culinario(
        original_name=None,
        generic_name="Yogur natural",
    )
    assert ctx.original_name is None
    assert ctx.display_name == "Yogur natural"
    assert ctx.culinary_name == "yogur"


def test_nombre_nulo() -> None:
    ctx = normalizar_nombre_culinario(original_name=None, generic_name=None)
    assert ctx.original_name is None
    assert ctx.display_name is None
    assert ctx.culinary_name is None
    assert ctx.confidence == "low"


def test_nan_float_es_nulo_y_literal_nan_se_conserva() -> None:
    nulo = normalizar_nombre_culinario(original_name=math.nan)  # type: ignore[arg-type]
    assert nulo.original_name is None
    assert nulo.display_name is None
    literal = normalizar_nombre_culinario(original_name="NAN")
    assert literal.original_name == "NAN"
    assert literal.display_name == "NAN"


def test_producto_ambiguo_conservador() -> None:
    ctx = normalizar_nombre_culinario(original_name="Producto especial de la casa edición limitada")
    assert ctx.original_name == "Producto especial de la casa edición limitada"
    assert ctx.display_name is not None
    assert ctx.confidence == "low"
    assert "Producto" in ctx.display_name


def test_producto_ya_limpio() -> None:
    ctx = normalizar_nombre_culinario(original_name="Avena")
    assert ctx.original_name == "Avena"
    assert ctx.display_name == "Avena"
    assert ctx.culinary_name == "avena"


def test_aceptacion_marca_x_yogur() -> None:
    ctx = normalizar_nombre_culinario(
        original_name="MARCA X YOGUR NATURAL ENTERO 125G",
        brand="MARCA X",
    )
    assert ctx.display_name == "Yogur natural"
    assert ctx.culinary_name == "yogur"
    assert ctx.original_name == "MARCA X YOGUR NATURAL ENTERO 125G"


def test_cuenta_y_prefijo_corto() -> None:
    tortillas = normalizar_nombre_culinario(original_name="12 Tortillas de Harina")
    assert tortillas.display_name == "Tortillas de harina"
    assert tortillas.culinary_name == "tortillas de harina"
    huevo = normalizar_nombre_culinario(original_name="AU huevo 30pz")
    assert huevo.display_name == "Huevo"
    assert huevo.culinary_name == "huevo"
    avena = normalizar_nombre_culinario(
        original_name="Member's Mark Avena Vainilla",
        brand="Member's Mark",
    )
    assert avena.display_name == "Avena"
    assert avena.culinary_name == "avena"
    dulce = normalizar_nombre_culinario(
        original_name="Dulce de leche caramel topping sweet cajeta saucespread",
    )
    assert dulce.display_name == "Dulce de leche"
    assert dulce.culinary_name == "dulce de leche"
    pasta = normalizar_nombre_culinario(original_name="PASTA DE TRIGO SEMOLA DURUM 500 G")
    assert pasta.display_name == "Pasta"
    avena = normalizar_nombre_culinario(
        original_name="Great Value Avena Integral 1kg",
        brand="Great Value",
    )
    assert avena.display_name == "Avena integral"
    assert avena.culinary_name == "avena"


def test_llm_no_inventa_tokens_ajenos() -> None:
    base = normalizar_nombre_culinario(original_name="Yogur natural")
    rechazado = aplicar_refinamiento_llm(
        base,
        {
            "display_name": "Yogur vegano sin gluten",
            "culinary_name": "yogur",
            "confidence": "high",
        },
        {"original_name": "Yogur natural", "ingredients": ["leche"]},
    )
    assert rechazado.display_name == "Yogur natural"
    assert "vegano" not in (rechazado.display_name or "").lower()


def test_normalizacion_alimenta_receta() -> None:
    hechos = {
        "recipe_context": {
            "observed_ingredients": ["leche"],
            "product_names": ["Yogur natural", "Avena integral"],
            "display_names": ["Yogur natural", "Avena integral"],
            "culinary_names": ["yogur", "avena"],
        }
    }
    receta = ensamblar_receta(
        hechos,
        "Bowl breve.",
        source="llm",
        extras=["yogur", "avena", "fruta"],
        pasos=["Mezcla el yogur con la avena.", "Agrega la fruta.", "Sirve."],
        nombre="Bowl de yogur y avena",
    )
    assert receta is not None
    assert receta.name == "Bowl de yogur y avena"
    assert receta.available_ingredients == ["Yogur natural", "Avena integral"]
    assert receta.extra_suggested == ["fruta"]
    assert receta.steps == ["Mezcla el yogur con la avena.", "Agrega la fruta.", "Sirve."]


def test_intent_normalize_product_baseline_y_no_cambia_ranking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from nutrimatch.core.config import get_settings
    from nutrimatch.schemas.profile import UserProfile

    monkeypatch.setattr("nutrimatch.core.config.project_root", lambda: tmp_path)
    get_settings.cache_clear()
    catalogo = _catalogo_con_ficha()
    servicio = RankingService(catalogo)
    perfil = UserProfile()
    perfil_antes = servicio.explain("75000001", perfil)
    respuesta = preguntar(
        AskRequest(surface="recipes", codes=["75000001"], intent="normalize_product"),
        catalogo=catalogo,
        servicio=servicio,
    )
    perfil_despues = servicio.explain("75000001", perfil)
    assert respuesta.intent == "normalize_product"
    assert respuesta.recipe is None
    assert respuesta.recipe_products
    primero = respuesta.recipe_products[0]
    assert primero.original_name == "Pan integral"
    assert primero.display_name == "Pan integral"
    assert primero.culinary_name == "pan"
    assert "inventó una receta" in respuesta.text.lower() or "culinario" in respuesta.text.lower()
    assert perfil_antes.score == perfil_despues.score
    assert perfil_antes.d1 == perfil_despues.d1
