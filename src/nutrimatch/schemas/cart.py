"""Contrato del resumen de carrito (A12). No incluye score ni precio."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from nutrimatch.schemas.product import ProvenanceStatus

MetodoAgregacion = Literal["promedio_100g", "ponderado_gramos"]


class CartSummaryRequest(BaseModel):
    codes: list[str] = Field(default_factory=list)


class NutrientAggregate(BaseModel):
    key: str
    label: str
    unit: str
    value: float | None
    status: ProvenanceStatus
    n_with_data: int
    n_products: int


class GroupBucket(BaseModel):
    key: str
    label: str
    n: int
    share: float


class CartSummary(BaseModel):
    n_products: int
    method: MetodoAgregacion
    method_note: str
    status: ProvenanceStatus
    nutrients: list[NutrientAggregate] = Field(default_factory=list)
    plato: list[GroupBucket] = Field(default_factory=list)
    categories: list[GroupBucket] = Field(default_factory=list)
