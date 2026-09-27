"""Contratos de ranking: petición, ítem con explicación (A10) y resultado por bandas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from nutrimatch.schemas.profile import UserProfile

Band = Literal["ranking", "no_verificable", "informacion_insuficiente", "excluido"]
AllergyStatus = Literal["apto", "no_apto", "no_verificable"]
DietStatus = Literal["compatible", "incompatible", "no_verificable"]


class NutrientExplanation(BaseModel):
    percentile: float | None
    sign: int
    available: bool
    contribution: float | None


class DimensionExplanation(BaseModel):
    subscore: float | None
    weight: float
    available: bool
    weighted_contribution: float | None


class ProductExplanation(BaseModel):
    """Hechos calculados para la ficha (A10). La UI solo los muestra; no recalcula."""

    score: float | None
    cov: float
    dimensions: dict[str, DimensionExplanation]
    d1_nutrients: dict[str, NutrientExplanation]
    allergy_status: AllergyStatus
    diet_status: DietStatus
    missing_flags: list[str] = Field(default_factory=list)
    category: str | None = None
    nova_group: float | None = None
    additives_n: float | None = None
    name_used_fallback: bool = False


class RankingItem(BaseModel):
    code: str
    product_name: str | None
    category: str | None
    band: Band
    score: float | None
    d1: float | None
    d2: float | None
    d3: float | None
    cov: float
    allergy_status: AllergyStatus
    diet_status: DietStatus
    rank: int | None = None
    explanation: ProductExplanation | None = None


class BandSlice(BaseModel):
    """Top-N de una banda más el conteo total de esa banda (el resto no se materializa)."""

    items: list[RankingItem]
    total: int


class RankingRequest(BaseModel):
    profile: UserProfile
    query: str = ""
    top_n: int = 25


class RankingResult(BaseModel):
    snapshot_id: str
    engine_version: str
    query: str
    weights: dict[str, float]
    ranking: BandSlice
    no_verificable: BandSlice
    informacion_insuficiente: BandSlice
    excluded_count: int
    n_matched: int
