"""Smoke opt-in contra OpenAI. Se omite sin OPENAI_API_KEY real."""

from __future__ import annotations

import pytest

from nutrimatch.ai.client import _clave_desde_entorno
from nutrimatch.ai.schemas import AskRequest
from nutrimatch.ai.service import preguntar
from nutrimatch.core.config import get_settings
from nutrimatch.schemas.profile import UserProfile
from nutrimatch.services.ranking import RankingService
from tests.test_api import _catalogo_con_ficha

_INTENTS = (
    ("explain", "product", ["75000001"], "¿Por qué aparece este producto?"),
    ("nutrition", "product", ["75000001"], "¿Qué significa esta información nutricional?"),
    ("alerts", "alerts", ["75000001"], None),
    ("fun_fact", "product", ["75000001"], "Dato curioso"),
    ("compare", "compare", ["75000001", "75000002"], "¿Qué diferencias hay?"),
    ("recipe", "recipes", ["75000001"], "¿Qué puedo preparar con estos productos?"),
    ("plato", "cart", ["75000001"], "¿Por qué un producto queda no clasificado?"),
    ("ask", "product", ["75000001"], "¿Por qué aparece este producto?"),
)


def _openai_real_disponible() -> bool:
    clave = (_clave_desde_entorno() or "").strip()
    if not clave or clave.startswith("sk-test"):
        return False
    try:
        import openai  # noqa: F401
    except ImportError:
        return False
    return True


@pytest.mark.openai
@pytest.mark.skipif(
    not _openai_real_disponible(),
    reason="OPENAI_API_KEY real ausente o extra llm no instalado",
)
def test_smoke_openai_ocho_intents() -> None:
    get_settings.cache_clear()
    catalogo = _catalogo_con_ficha()
    catalogo.df = catalogo.df.copy()
    catalogo.df["ingredients_text"] = ["harina de trigo, agua, sal", None, None, None, None]
    servicio = RankingService(catalogo)
    perfil = UserProfile(
        allergen_tags=["en:gluten"],
        diet="vegano",
        priority_order=["D1", "D2", "D3"],
    )
    antes = servicio.explain("75000001", perfil)
    vistos: list[str] = []
    for intent, surface, codes, message in _INTENTS:
        respuesta = preguntar(
            AskRequest(
                surface=surface,  # type: ignore[arg-type]
                codes=codes,
                intent=intent,  # type: ignore[arg-type]
                message=message,
                profile=perfil,
            ),
            catalogo=catalogo,
            servicio=servicio,
        )
        serial = str(respuesta.model_dump())
        assert "sk-" not in serial
        assert "OPENAI_API_KEY" not in serial
        assert respuesta.text
        assert respuesta.observability is not None
        kind = respuesta.observability.error_kind
        if kind in {"timeout", "rate_limit", "network"}:
            pytest.skip(f"{intent}: OpenAI no disponible ({kind})")
        assert kind not in {"missing_key", "sdk_missing"}
        if intent == "plato":
            assert respuesta.intent == "plato"
        if intent == "recipe":
            assert respuesta.recipe is not None
            assert respuesta.recipe.nutrition_note
            if respuesta.source == "llm":
                assert respuesta.recipes
                assert all(r.name.strip() and r.steps for r in respuesta.recipes)
        if respuesta.source == "llm":
            assert respuesta.critic_pass is True
        vistos.append(f"{intent}:{respuesta.source}:{respuesta.fallback_reason}")
    despues = servicio.explain("75000001", perfil)
    assert antes.score == despues.score
    assert antes.d1 == despues.d1
    assert antes.d2 == despues.d2
    assert antes.d3 == despues.d3
    assert antes.cov == despues.cov
    assert antes.band == despues.band
    assert any(item.split(":")[1] == "llm" for item in vistos), vistos
