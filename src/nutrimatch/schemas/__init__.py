"""Esquemas pydantic v2 de entrada y salida: contratos validados entre motor, UI y persistencia."""

from nutrimatch.schemas.cart import CartSummary, CartSummaryRequest
from nutrimatch.schemas.event import EventCreate, EventRow
from nutrimatch.schemas.product import ExplainRequest, MetaResponse, ProductDetail
from nutrimatch.schemas.profile import UserProfile
from nutrimatch.schemas.ranking import RankingItem, RankingRequest, RankingResult

__all__ = [
    "CartSummary",
    "CartSummaryRequest",
    "EventCreate",
    "EventRow",
    "ExplainRequest",
    "MetaResponse",
    "ProductDetail",
    "RankingItem",
    "RankingRequest",
    "RankingResult",
    "UserProfile",
]
