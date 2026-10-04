"""Traduce la pregunta a un intent validado. No calcula."""

from __future__ import annotations

import re

from nutrimatch.ai.schemas import Intent

_FUERA = re.compile(
    r"\b(clima|f[uú]tbol|futbol|pol[ií]tica|elecciones|bitcoin|cripto|programar|"
    r"python script|chiste|novela|viaje a|hotel|cine)\b",
    re.IGNORECASE,
)
_MEDICO = re.compile(
    r"\b(diabetes|c[aá]ncer|embarazo|dieta para (bajar|subir) de peso|"
    r"me duele|receta m[eé]dica|qu[eé] medicina)\b",
    re.IGNORECASE,
)

_REGLAS: tuple[tuple[re.Pattern[str], Intent], ...] = (
    (re.compile(r"qu[eé] puedo (preparar|cocinar)|receta|platillo", re.I), "recipe"),
    (
        re.compile(
            r"plato del (bien|buen) comer|nom-?043|grupo (del plato|alimentario)|no clasificado",
            re.I,
        ),
        "plato",
    ),
    (re.compile(r"dato curioso|sab[ií]as que|curiosidad", re.I), "fun_fact"),
    (re.compile(r"cu[aá]l (tiene|trae) m[aá]s|compara|comparaci[oó]n|qu[eé] diferencias", re.I), "compare"),
    (re.compile(r"alerta|sello|al[eé]rgen|no verificable|no apto", re.I), "alerts"),
    (re.compile(r"qu[eé] significa|significa (este|esta|la|el)|informaci[oó]n nutricional", re.I), "nutrition"),
    (re.compile(r"prote[ií]na|az[uú]car|fibra|kcal|calor[ií]as|nutriente|por 100", re.I), "nutrition"),
    (re.compile(r"por qu[eé]|aparece este producto|banda|score|cobertura|cov|ranking|nova", re.I), "explain"),
)


def planear_intent(intent: Intent, message: str | None, *, n_codes: int) -> Intent:
    texto = (message or "").strip()
    if intent != "ask":
        if intent == "compare" and n_codes < 2:
            return "explain" if n_codes == 1 else "reject"
        if intent == "recipe" and n_codes < 1:
            return "reject"
        if intent == "normalize_product" and n_codes < 1:
            return "reject"
        return intent
    if not texto:
        if n_codes >= 2:
            return "compare"
        if n_codes == 1:
            return "explain"
        return "plato"
    if _FUERA.search(texto) or _MEDICO.search(texto):
        return "reject"
    for patron, elegido in _REGLAS:
        if patron.search(texto):
            if elegido == "compare" and n_codes < 2:
                return "nutrition" if n_codes == 1 else "reject"
            if elegido == "recipe" and n_codes < 1:
                return "reject"
            if elegido == "normalize_product" and n_codes < 1:
                return "reject"
            return elegido
    if n_codes >= 2:
        return "compare"
    if n_codes == 1:
        return "explain"
    return "reject"
