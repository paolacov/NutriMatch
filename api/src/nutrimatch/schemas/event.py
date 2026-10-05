"""Contrato del event_log: trazas de uso, no puntúan (A11)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

EventType = Literal[
    "cart_item_added",
    "cart_item_removed",
    "ranking_run_created",
    "product_viewed",
]


class EventCreate(BaseModel):
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)


class EventRow(BaseModel):
    id: int
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: str
