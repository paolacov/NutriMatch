"""Pruebas de validación de UserProfile."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from nutrimatch.schemas.profile import UserProfile


def test_perfil_por_defecto_es_valido() -> None:
    perfil = UserProfile()
    assert perfil.priority_order == ["D1", "D2", "D3"]
    assert perfil.diet is None
    assert perfil.allergen_tags == []


def test_priority_order_invalido_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        UserProfile(priority_order=["D1", "D1", "D2"])


def test_dieta_desconocida_se_rechaza() -> None:
    with pytest.raises(ValidationError):
        UserProfile(diet="cetogenica")  # type: ignore[arg-type]
