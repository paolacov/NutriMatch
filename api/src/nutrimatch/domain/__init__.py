"""Modelos de dominio: el contrato validado vive en `nutrimatch.schemas` (pydantic v2).

No se duplica aquí una segunda representación del perfil o del ranking. Regla invariable: un
dato faltante se representa como NULL más una bandera explícita, NUNCA como cero.
"""
