"""Contrato del perfil de usuaria (entrada validada de la UI y de `ranking_run`)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from nutrimatch.engine.user_weights import DIMENSIONES

DietaDeclarada = Literal["vegano", "vegetariano"]
DimensionPrioridad = Literal["D1", "D2", "D3"]

# Catálogo de opciones de la UI: identificador OFF (inglés) + etiqueta para mostrar (español).
# No es exhaustivo: cubre los alérgenos y sellos más usados en el snapshot México. La usuaria
# no escribe tags a mano (A6: decisiones humanas razonables, no controles técnicos).
ALLERGEN_CHOICES: tuple[tuple[str, str], ...] = (
    ("en:gluten", "Gluten"),
    ("en:milk", "Leche"),
    ("en:eggs", "Huevo"),
    ("en:soybeans", "Soya"),
    ("en:nuts", "Frutos secos"),
    ("en:peanuts", "Cacahuate"),
    ("en:sesame-seeds", "Sésamo"),
    ("en:fish", "Pescado"),
    ("en:crustaceans", "Crustáceos"),
)

LABEL_CHOICES: tuple[tuple[str, str], ...] = (
    ("en:organic", "Orgánico"),
    ("en:no-gluten", "Sin gluten"),
    ("en:fair-trade", "Comercio ético"),
    ("en:vegetarian", "Vegetariano (sello)"),
    ("en:vegan", "Vegano (sello)"),
)

PRIORITY_LABELS: dict[str, str] = {
    "D1": "Nutrición",
    "D2": "Procesamiento",
    "D3": "Etiquetas",
}

# Presets de UI: solo rellenan `priority_order`. No hay sliders (A6).
PRIORITY_PRESETS: dict[str, list[DimensionPrioridad]] = {
    "equilibrado": ["D1", "D2", "D3"],
    "nutricion_primero": ["D1", "D3", "D2"],
    "minimo_procesado": ["D2", "D1", "D3"],
}


class UserProfile(BaseModel):
    """Perfil declarado por la usuaria: filtros duros + orden de prioridades + etiquetas D3."""

    allergen_tags: list[str] = Field(default_factory=list)
    diet: DietaDeclarada | None = None
    valued_labels: list[str] = Field(default_factory=list)
    priority_order: list[DimensionPrioridad] = Field(default_factory=lambda: ["D1", "D2", "D3"])

    @model_validator(mode="after")
    def priority_order_es_permutacion(self) -> UserProfile:
        if sorted(self.priority_order) != sorted(DIMENSIONES):
            raise ValueError(
                f"priority_order debe ser una permutación de {DIMENSIONES}, "
                f"recibido: {self.priority_order!r}"
            )
        return self
