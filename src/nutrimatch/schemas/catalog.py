"""Contrato HTTP del catálogo de exploración. No incluye score ni bandas de ranking."""

from __future__ import annotations

from pydantic import BaseModel, Field

from nutrimatch.schemas.product import ProductDetail

FACETA_TODAS = ""
FACETA_SIN_CATEGORIA = "__none__"
FACETA_OTROS = "__other__"


class CatalogCategory(BaseModel):
    id: str
    name: str
    count: int


class CatalogPage(BaseModel):
    items: list[ProductDetail] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    total_pages: int
