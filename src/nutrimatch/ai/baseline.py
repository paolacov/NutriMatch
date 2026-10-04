"""Narraciones deterministas por intent. Sin modelo generativo."""

from __future__ import annotations

import re
from typing import Any

from nutrimatch.schemas.profile import PRIORITY_LABELS

_FLAG_ES = {
    "D1_sin_dato": "no hay subpuntaje de nutrición",
    "D2_sin_dato": "no hay subpuntaje de procesamiento",
    "D3_sin_dato": "no hay subpuntaje de etiquetas",
    "alergia_no_verificable": "el estado de alergia no se puede determinar",
    "dieta_no_verificable": "el estado de dieta no se puede determinar",
}

TEXTO_RECHAZO = (
    "Esa pregunta queda fuera de NutriMatch. Puedo explicar un resultado ya calculado, "
    "una alerta, un nutriente observado, una comparación de lo seleccionado, "
    "una preparación con esos productos o el Plato del Bien Comer."
)


def _fmt_num(valor: float | None) -> str:
    if valor is None:
        return "información no disponible"
    if abs(valor - round(valor)) < 1e-9:
        return str(int(round(valor)))
    return f"{valor:.1f}"


def _nombre(payload: dict[str, Any]) -> str:
    product = payload.get("product") or {}
    nombre = (product.get("name") or {}).get("value")
    return "Producto sin nombre verificado" if nombre is None else str(nombre)


def narrar_explain(payload: dict[str, Any]) -> str:
    product = payload["product"]
    decision = payload["decision"]
    constraints = payload["constraints"]
    price = payload["price"]
    profile = payload["profile"]
    availability = payload["availability"]
    partes: list[str] = []
    if decision.get("band_label"):
        partes.append(
            f"{_nombre(payload)} (código {product['code']}) quedó en la banda «{decision['band_label']}»."
        )
    else:
        partes.append(f"{_nombre(payload)} (código {product['code']}). No hay banda calculada en este contexto.")

    if decision.get("score") is None:
        partes.append("El motor no emitió un score final: no hay encaje numérico que citar.")
    else:
        partes.append(
            f"El score calculado es {_fmt_num(decision['score'])} sobre 100, "
            f"con cobertura {_fmt_num(decision.get('cov'))}."
        )

    banda = decision.get("band")
    if banda == "excluido":
        partes.append("No entra a la comparación porque una restricción del perfil lo excluye.")
    elif banda == "no_verificable":
        partes.append("No se mezcla con el ranking: falta información verificable de alergia o de dieta.")
    elif banda == "informacion_insuficiente":
        partes.append("No se compara en el ranking: falta información en más de la mitad de lo que pesa el perfil.")
    elif banda == "ranking":
        partes.append("Entra al ranking con la información disponible para este perfil.")

    dim_bits = []
    for clave in ("D1", "D2", "D3"):
        dim = (decision.get("dimensions") or {}).get(clave)
        if not dim:
            continue
        etiqueta = PRIORITY_LABELS[clave]
        if not dim.get("available") or dim.get("subscore") is None:
            dim_bits.append(f"{etiqueta}: información no disponible")
        else:
            dim_bits.append(f"{etiqueta}: {_fmt_num(dim['subscore'])}")
    if dim_bits:
        partes.append("Dimensiones: " + "; ".join(dim_bits) + ".")

    if constraints.get("allergy_evaluable"):
        estado = constraints.get("allergy_status")
        if estado == "no_apto":
            partes.append("Alergia: no apto respecto de los alérgenos declarados en el perfil.")
        elif estado == "no_verificable":
            partes.append("Alergia: no se puede determinar; el registro de alérgenos está incompleto.")
        else:
            partes.append("Alergia: el motor no encontró los alérgenos declarados en el registro.")
    else:
        partes.append("El perfil no declaró alergias: no se afirma apto ni ausencia de alérgenos.")

    if constraints.get("diet_evaluable"):
        estado = constraints.get("diet_status")
        dieta = profile.get("diet")
        if estado == "incompatible":
            partes.append(f"Dieta ({dieta}): incompatible.")
        elif estado == "no_verificable":
            partes.append(f"Dieta ({dieta}): no se puede determinar.")
        else:
            partes.append(f"Dieta ({dieta}): compatible según las etiquetas de análisis disponibles.")
    else:
        partes.append("El perfil no declaró dieta: no se afirma compatibilidad.")

    if price.get("available"):
        partes.append(
            f"Precio de referencia observado: {price['value']} ({price.get('source') or 'fuente observada'}). No puntúa."
        )
    else:
        partes.append("Precio no disponible. No se afirma un importe.")

    flags = [f for f in (decision.get("missing_flags") or []) if f in _FLAG_ES]
    if flags:
        partes.append("Banderas del motor: " + "; ".join(_FLAG_ES[f] for f in flags) + ".")
    if availability.get("d3") and not profile.get("valued_labels"):
        partes.append("No hay etiquetas valoradas en el perfil; la dimensión de etiquetas no se evalúa.")

    partes.append("Estos hechos los calculó el motor; esta frase no cambia el orden ni el score.")
    return " ".join(partes)


def narrar_alerts(payload: dict[str, Any]) -> str:
    constraints = payload["constraints"]
    product = payload["product"]
    sellos = [t for t in product.get("labels") or [] if "exceso" in t]
    partes = [f"Alertas de {_nombre(payload)} (código {product['code']})."]
    if not constraints.get("allergy_evaluable"):
        partes.append("Alergia no evaluable: el perfil no declaró alérgenos. No se afirma que el producto esté libre de ellos.")
    elif constraints.get("allergy_status") == "no_verificable":
        partes.append(
            "No fue posible determinar completamente la información de alérgenos de este producto."
        )
    elif constraints.get("allergy_status") == "no_apto":
        partes.append("El motor marcó no apto por un alérgeno declarado en el perfil.")
    else:
        partes.append("El motor no encontró los alérgenos del perfil en el registro de este producto.")
    if not constraints.get("diet_evaluable"):
        partes.append("Dieta no evaluable: el perfil no declaró dieta.")
    elif constraints.get("diet_status") == "no_verificable":
        partes.append("La compatibilidad dietética no se puede determinar.")
    elif constraints.get("diet_status") == "incompatible":
        partes.append("La dieta declarada resulta incompatible según las etiquetas de análisis.")
    if sellos:
        partes.append("Sellos NOM-051 observados: " + ", ".join(sellos) + ". Informan; no diagnostican ni puntúan.")
    else:
        partes.append("No hay sellos de exceso registrados en este producto. Eso no afirma que no existan.")
    return " ".join(partes)


def narrar_nutrition(payload: dict[str, Any]) -> str:
    product = payload["product"]
    partes = [f"Nutrientes observados de {_nombre(payload)}, por 100 g."]
    hubo = False
    for n in product.get("nutrients") or []:
        if n.get("available") and n.get("per100g") is not None:
            partes.append(f"{n['label']}: {_fmt_num(n['per100g'])} {n.get('unit') or ''}".strip() + ".")
            hubo = True
        else:
            partes.append(f"{n.get('label', n.get('key'))}: información no disponible. No equivale a cero.")
    if not hubo:
        partes.append("No hay valores nutrimentales observados para explicar.")
    partes.append("Estos números vienen del catálogo. No son un juicio de salud ni una porción inventada.")
    return " ".join(partes)


def narrar_compare(payload: dict[str, Any]) -> str:
    comparacion = payload.get("comparison") or {}
    filas = comparacion.get("rows") or []
    if not filas:
        return "No hay suficientes productos con dato observado para comparar ese nutriente."
    label = comparacion.get("label") or comparacion.get("nutrient") or "nutriente"
    partes = [f"Comparación de {label} por 100 g (valores ya leídos del catálogo)."]
    for fila in filas:
        if fila.get("value") is None:
            partes.append(f"{fila.get('name')}: información no disponible.")
        else:
            partes.append(f"{fila.get('name')}: {_fmt_num(fila['value'])} {fila.get('unit') or ''}".strip() + ".")
    ganador = comparacion.get("highest_name")
    if ganador and comparacion.get("complete"):
        partes.append(f"El valor más alto observado es {ganador}.")
    elif not comparacion.get("complete"):
        partes.append("Falta al menos un valor: no se declara un ganador.")
    partes.append("Esta comparación no cambia el ranking ni el score.")
    return " ".join(partes)


def narrar_recipe(payload: dict[str, Any]) -> str:
    ctx = payload.get("recipe_context") or {}
    nombres = ctx.get("product_names") or []
    observados = ctx.get("observed_ingredients") or []
    restricciones = ctx.get("restrictions") or []
    partes = [
        "Preparación a partir de los productos seleccionados. No es consejo médico ni una receta con nutrición calculada."
    ]
    if nombres:
        partes.append("Productos: " + ", ".join(nombres) + ".")
    if observados:
        partes.append("Ingredientes observados en los registros: " + ", ".join(observados[:20]) + ".")
    else:
        partes.append("No hay ingredientes observados en los registros. No se inventan.")
    if restricciones:
        partes.append("Restricciones declaradas: " + ", ".join(restricciones) + ".")
    partes.append(
        "Sin un modelo de lenguaje, no se propone una receta inventada: solo se listan los datos disponibles."
    )
    partes.append("Cualquier ingrediente extra sería una sugerencia, no un dato del catálogo.")
    return " ".join(partes)


def narrar_plato(payload: dict[str, Any]) -> str:
    grupos = payload.get("plato_groups") or []
    resumen = payload.get("cart_summary") or {}
    cubetas = resumen.get("plato") if isinstance(resumen, dict) else None
    n_productos = int(resumen.get("n_products") or 0) if isinstance(resumen, dict) else 0
    pregunta = str(payload.get("message") or "").lower()
    partes = [
        "El Plato del Bien Comer es una guía educativa (NOM-043), no un diagnóstico ni un menú prescrito."
    ]
    partes.append(
        "La guía dibuja más espacio para verduras y frutas. El conteo del carrito usa número de productos, no gramos."
    )
    if cubetas:
        for cubeta in cubetas:
            clave = cubeta.get("key")
            etiqueta = cubeta.get("label") or clave
            n_gajo = int(cubeta.get("n") or 0)
            if clave == "unclassified":
                if n_gajo:
                    partes.append(
                        f"Hay {n_gajo} no clasificado(s): los datos no permiten asignar un grupo."
                    )
                elif "no clasificado" in pregunta:
                    partes.append("En este carrito no hay productos no clasificados.")
                continue
            if n_gajo:
                denom = n_productos if n_productos else n_gajo
                partes.append(f"En {etiqueta} hay {n_gajo} de {denom} productos.")
            else:
                partes.append(f"En {etiqueta} no hay productos de este carrito.")
    elif grupos:
        no_clasificados = [g for g in grupos if g.get("group") == "unclassified"]
        if no_clasificados:
            partes.append("Hay productos no clasificados: los datos no permiten asignar un grupo.")
        for g in grupos:
            nombre = g.get("name") or g.get("code")
            if g.get("group") == "unclassified":
                partes.append(f"{nombre}: no clasificado. Los datos no permiten asignar un grupo.")
            else:
                partes.append(
                    f"{nombre}: grupo observado «{g.get('label')}». Es clasificación del catálogo, no una receta."
                )
    else:
        partes.append("No hay productos en este contexto para relacionar con un grupo.")
    return " ".join(partes)


def _slot_curioso(message: str | None) -> int:
    if not message:
        return 0
    hallado = re.search(r"variante\s+(\d+)", message, re.IGNORECASE)
    if hallado is None:
        return 0
    return max(int(hallado.group(1)), 0)


_DATOS_GENERALES: tuple[str, ...] = (
    (
        "La fibra está en verduras, frutas, leguminosas y cereales de grano entero. "
        "Forma parte de esos alimentos; no es una indicación para una persona en particular."
    ),
    (
        "La proteína está en leguminosas y en alimentos de origen animal, como frijol, lenteja, huevo o pescado. "
        "Nombrar el grupo no dice cuál conviene más."
    ),
    "Las grasas son un nutrimento. Decir que existen no indica cuánta necesita cada persona.",
    (
        "Los carbohidratos aportan energía. Cereales como el maíz, el trigo, el arroz y la avena, "
        "y tubérculos como la papa, son ejemplos de ese grupo."
    ),
    "El agua acompaña la alimentación. Cuánta le hace falta a alguien no se calcula aquí.",
    (
        "Verduras y frutas aportan vitaminas, minerales, agua y fibra. "
        "La guía del Plato del Bien Comer las incluye en las comidas como orientación general, "
        "no como un menú prescrito."
    ),
    (
        "Leguminosas y cereales son grupos distintos: unas se asocian sobre todo con proteína "
        "y los otros con energía. La guía no los declara mejores o peores entre sí."
    ),
    (
        "Variar los grupos de alimentos a lo largo del día es un hábito general. "
        "No dice qué le corresponde a una persona en concreto."
    ),
)


def narrar_fun_fact(payload: dict[str, Any]) -> str:
    """Educación general. No usa el producto del carrito."""
    return _DATOS_GENERALES[_slot_curioso(payload.get("message")) % len(_DATOS_GENERALES)]


def narrar_normalize(payload: dict[str, Any]) -> str:
    fuentes = payload.get("normalize_sources") or payload.get("recipe_products") or []
    n = len(fuentes)
    if n == 1:
        return "Nombre culinario derivado del registro. No se inventó una receta."
    return f"Nombres culinarios derivados de {n} registros. No se inventó una receta."


def narrar_baseline(payload: dict[str, Any], *, intent: str) -> str:
    if intent == "reject":
        return TEXTO_RECHAZO
    if intent == "alerts":
        return narrar_alerts(payload)
    if intent == "nutrition":
        return narrar_nutrition(payload)
    if intent == "compare":
        return narrar_compare(payload)
    if intent == "recipe":
        return narrar_recipe(payload)
    if intent == "normalize_product":
        return narrar_normalize(payload)
    if intent == "plato":
        return narrar_plato(payload)
    if intent == "fun_fact":
        return narrar_fun_fact(payload)
    if "product" in payload:
        return narrar_explain(payload)
    return TEXTO_RECHAZO
