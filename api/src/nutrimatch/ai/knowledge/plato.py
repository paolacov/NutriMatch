"""Texto controlado del Plato del Bien Comer (NOM-043). Educativo, no diagnóstico."""

from __future__ import annotations

from nutrimatch.engine.cart_summary import NO_CLASIFICADO, PLATO_LABELS

GRUPOS: tuple[dict[str, str], ...] = (
    {
        "key": "frutas_verduras",
        "label": PLATO_LABELS["frutas_verduras"],
        "text": (
            "Verduras y frutas aportan vitaminas, minerales, agua y fibra. "
            "La guía oficial recomienda incluirlas en cada comida. "
            "Esto es educación alimentaria, no un menú prescrito."
        ),
    },
    {
        "key": "cereales",
        "label": PLATO_LABELS["cereales"],
        "text": (
            "Cereales (maíz, trigo, arroz, avena y tubérculos como la papa) aportan energía. "
            "La guía prefiere cereales de grano entero cuando hay información para distinguirlos. "
            "Si el registro no lo dice, no se afirma."
        ),
    },
    {
        "key": "leguminosas_aoa",
        "label": PLATO_LABELS["leguminosas_aoa"],
        "text": (
            "Leguminosas y alimentos de origen animal aportan proteína. "
            "Frijol, lenteja, huevo, leche, pescado o carne caen aquí cuando el dato lo permite. "
            "No se mezclan con un juicio de «mejor» o «peor» proteína."
        ),
    },
    {
        "key": NO_CLASIFICADO,
        "label": PLATO_LABELS[NO_CLASIFICADO],
        "text": (
            "Si el producto no tiene una etiqueta de grupo reconocible, NutriMatch lo deja "
            "como no clasificado. No se inventa el grupo."
        ),
    },
)

CAVEATS: tuple[str, ...] = (
    "El Plato del Bien Comer es una guía educativa (NOM-043), no un diagnóstico.",
    "La clasificación de un producto en NutriMatch sale de etiquetas observadas del catálogo.",
    "Sin etiqueta mapeable el producto queda no clasificado.",
    "El porcentaje del carrito usa número de productos, no gramos.",
)


def texto_educativo() -> list[str]:
    lineas = [f"{g['label']}: {g['text']}" for g in GRUPOS]
    lineas.extend(CAVEATS)
    return lineas


def como_dict() -> dict[str, object]:
    return {"groups": [dict(g) for g in GRUPOS], "caveats": list(CAVEATS)}
