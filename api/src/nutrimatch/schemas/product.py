"""Contrato de ficha de anaquel: identidad, nutrientes, precio y procedencia (A33)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from nutrimatch.schemas.profile import UserProfile

ProvenanceStatus = Literal["REAL", "DERIVED", "IMPUTED", "SYNTHETIC", "UNAVAILABLE"]


class ProvenanceValue(BaseModel):
    value: str | float | None = None
    status: ProvenanceStatus
    source: str | None = None
    note: str | None = None


class NutrientRow(BaseModel):
    key: str
    label: str
    per100g: float | None
    unit: str
    status: ProvenanceStatus


class ProductDetail(BaseModel):
    """Lo que la ficha muestra. No incluye el score personalizado (eso es RankingItem)."""

    code: str
    name: ProvenanceValue
    brand: ProvenanceValue
    quantity: str | None = None
    category: str | None = None
    image_url: str | None = None
    image_hint: str = "?"
    nutrients: list[NutrientRow] = Field(default_factory=list)
    ingredients: list[str] = Field(default_factory=list)
    allergens: list[str] = Field(default_factory=list)
    traces: list[str] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    price: ProvenanceValue
    nova_group: float | None = None
    data_quality_score: float | None = None
    data_quality_level: str | None = None
    data_quality_label: str | None = None
    data_quality_detalle: str | None = None


class MetaResponse(BaseModel):
    snapshot_id: str
    engine_version: str
    n_products: int
    n_puntuable: int = 0


class ExplainRequest(BaseModel):
    code: str
    profile: UserProfile
