"""Contratos del endpoint ``POST /ai/ask``. No incluyen la clave de API."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from nutrimatch.schemas.profile import UserProfile

Intent = Literal[
    "explain",
    "alerts",
    "nutrition",
    "compare",
    "recipe",
    "normalize_product",
    "plato",
    "fun_fact",
    "ask",
    "reject",
]
Surface = Literal[
    "search",
    "product",
    "compare",
    "cart",
    "alerts",
    "recipes",
    "recommendations",
]


class RecipeProductContext(BaseModel):
    """Nombre culinario derivado. No pisa product_name del catálogo."""

    code: str = ""
    original_name: str | None = None
    display_name: str | None = None
    culinary_name: str | None = None
    product_type: str | None = None
    confidence: Literal["high", "medium", "low"] = "low"
    brand: str | None = None
    quantity: str | None = None
    available_ingredients: list[str] = Field(default_factory=list)


class RecipeDraft(BaseModel):
    name: str
    short_description: str = ""
    used_products: list[str] = Field(default_factory=list)
    available_ingredients: list[str] = Field(default_factory=list)
    extra_suggested: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    nutrition_note: str = "No se calculó la nutrición de esta preparación."


class AskRequest(BaseModel):
    surface: Surface
    codes: list[str] = Field(default_factory=list)
    profile: UserProfile = Field(default_factory=UserProfile)
    intent: Intent = "ask"
    message: str | None = None
    culinary_goal: str | None = None


class AskObservability(BaseModel):
    """Métricas de la consulta. Nunca incluye claves ni secretos."""

    intent: Intent
    model: str | None = None
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    ok: bool
    fallback: bool
    fallback_reason: str | None = None
    error_kind: str | None = None


class AskResponse(BaseModel):
    intent: Intent
    text: str
    source: Literal["llm", "baseline"]
    fallback: bool
    fallback_reason: str | None = None
    critic_pass: bool | None = None
    recipe: RecipeDraft | None = None
    recipes: list[RecipeDraft] = Field(default_factory=list)
    recipe_products: list[RecipeProductContext] = Field(default_factory=list)
    comparison: dict[str, Any] | None = None
    plato_education: list[str] = Field(default_factory=list)
    facts_summary: dict[str, Any] = Field(default_factory=dict)
    observability: AskObservability | None = None
