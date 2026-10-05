"""Orquestación interna: catálogo del universo México y ranking personalizado."""

from nutrimatch.services.catalog import Catalog
from nutrimatch.services.product import detalle_desde_fila
from nutrimatch.services.ranking import RankingService, asignar_banda

__all__ = ["Catalog", "RankingService", "asignar_banda", "detalle_desde_fila"]
