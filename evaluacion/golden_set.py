"""Golden set: casos revisados a mano sobre productos reales (decisión A8/A29, AGENTS.md).

Snapshot de referencia: ``off_csv_20260919``. Cada caso fija el ``code`` de un producto real y una
descripción de qué se espera y por qué, verificada a mano contra los valores crudos del snapshot en
el momento de escribir este módulo (ver AGENTS.md, decisión A29, para el detalle de cada caso).

Si el snapshot se regenera y un producto cambia legítimamente en OFF (p. ej. un contribuidor
corrige sus alérgenos), el caso correspondiente puede empezar a fallar: es una señal de que hay que
revisar el caso (¿sigue siendo válido con el nuevo dato? ¿hay que sustituir el `code`?), no
necesariamente un bug del motor. Esto es coherente con el resto del proyecto: todo dato lleva
`snapshot_id` (Sección C, AGENTS.md).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from nutrimatch.engine.constants import CORE8_NUTRIENTES
from nutrimatch.engine.hard_filters import evaluar_alergia, evaluar_dieta
from nutrimatch.engine.nutrition_score import calcular_subpuntaje_d1
from nutrimatch.engine.preference_score import calcular_d3
from nutrimatch.engine.product_naming import resolver_nombre_producto

SNAPSHOT_ID = "off_csv_20260919"

# Columnas que `evaluar()` necesita encontrar en el DataFrame que se le pase, además de `code`.
COLUMNAS_REQUERIDAS: tuple[str, ...] = (
    *(f"percentil_{n}" for n in CORE8_NUTRIENTES),
    "d2",
    "allergens",
    "traces",
    "ingredients_analysis_tags",
    "labels_tags",
    "product_name_bruto",
    "generic_name",
    "abbreviated_product_name",
)


def _d1_de_fila(fila: pd.Series) -> float | None:
    percentiles = {n: fila[f"percentil_{n}"] for n in CORE8_NUTRIENTES}
    d1, _ = calcular_subpuntaje_d1(percentiles)
    return d1


def _es_nulo(valor: object) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor))


@dataclass(frozen=True)
class CasoGoldenSet:
    code: str
    descripcion: str
    verificar: Callable[[pd.Series], list[str]]


def _verificar_d1_d2_malos(fila: pd.Series) -> list[str]:
    fallos = []
    d1 = _d1_de_fila(fila)
    if d1 is None or d1 > 20:
        fallos.append(f"D1 esperado <= 20, obtenido {d1}")
    if _es_nulo(fila["d2"]) or fila["d2"] > 15:
        fallos.append(f"D2 esperado <= 15, obtenido {fila['d2']}")
    return fallos


def _verificar_d1_d2_buenos(fila: pd.Series) -> list[str]:
    fallos = []
    d1 = _d1_de_fila(fila)
    if d1 is None or d1 < 80:
        fallos.append(f"D1 esperado >= 80, obtenido {d1}")
    if _es_nulo(fila["d2"]) or fila["d2"] < 95:
        fallos.append(f"D2 esperado >= 95, obtenido {fila['d2']}")
    return fallos


def _verificar_alergia_gluten_confirmado(fila: pd.Series) -> list[str]:
    estado = evaluar_alergia(fila["allergens"], fila["traces"], ["en:gluten"])
    return [] if estado == "no_apto" else [f"esperado no_apto, obtenido {estado}"]


def _verificar_alergia_gluten_en_traces(fila: pd.Series) -> list[str]:
    estado = evaluar_alergia(fila["allergens"], fila["traces"], ["en:gluten"])
    return [] if estado == "no_apto" else [f"esperado no_apto (fail-safe por traces, A15), obtenido {estado}"]


def _verificar_alergia_sin_dato(fila: pd.Series) -> list[str]:
    estado = evaluar_alergia(fila["allergens"], fila["traces"], ["en:gluten"])
    return [] if estado == "no_verificable" else [f"esperado no_verificable, obtenido {estado}"]


def _verificar_dieta_vegano_compatible(fila: pd.Series) -> list[str]:
    estado = evaluar_dieta(fila["ingredients_analysis_tags"], "vegano")
    return [] if estado == "compatible" else [f"esperado compatible, obtenido {estado}"]


def _verificar_dieta_vegano_incompatible(fila: pd.Series) -> list[str]:
    estado = evaluar_dieta(fila["ingredients_analysis_tags"], "vegano")
    return [] if estado == "incompatible" else [f"esperado incompatible, obtenido {estado}"]


def _verificar_dieta_maybe_no_verificable(fila: pd.Series) -> list[str]:
    estado = evaluar_dieta(fila["ingredients_analysis_tags"], "vegano")
    return [] if estado == "no_verificable" else [f"esperado no_verificable ('tal vez' no es 'sí', A1), obtenido {estado}"]


def _verificar_d1_none_d2_presente(fila: pd.Series) -> list[str]:
    fallos = []
    d1 = _d1_de_fila(fila)
    if d1 is not None:
        fallos.append(f"D1 esperado None (sin categoria_referencia), obtenido {d1}")
    if _es_nulo(fila["d2"]):
        fallos.append("D2 esperado disponible (tiene NOVA), obtenido NaN")
    return fallos


def _verificar_d2_none_d1_presente(fila: pd.Series) -> list[str]:
    fallos = []
    d1 = _d1_de_fila(fila)
    if d1 is None:
        fallos.append("D1 esperado disponible (tiene categoria_referencia y dato nutricional), obtenido None")
    if not _es_nulo(fila["d2"]):
        fallos.append(f"D2 esperado None (sin NOVA), obtenido {fila['d2']}")
    return fallos


def _verificar_nombre_con_respaldo(fila: pd.Series) -> list[str]:
    nombre, se_uso_respaldo = resolver_nombre_producto(
        fila["product_name_bruto"], fila["generic_name"], fila["abbreviated_product_name"]
    )
    fallos = []
    if nombre != "Organic Smooth Almond Butter":
        fallos.append(f"nombre esperado 'Organic Smooth Almond Butter', obtenido {nombre!r}")
    if not se_uso_respaldo:
        fallos.append("se_uso_respaldo esperado True (viene de generic_name)")
    return fallos


def _verificar_d3_organic(fila: pd.Series) -> list[str]:
    fallos = []
    d3_una_etiqueta = calcular_d3(fila["labels_tags"], ["en:organic"])
    if d3_una_etiqueta != 100.0:
        fallos.append(f"D3 esperado 100.0 con ['en:organic'], obtenido {d3_una_etiqueta}")
    d3_dos_etiquetas = calcular_d3(fila["labels_tags"], ["en:organic", "en:no-gluten"])
    if d3_dos_etiquetas != 50.0:
        fallos.append(f"D3 esperado 50.0 con ['en:organic', 'en:no-gluten'], obtenido {d3_dos_etiquetas}")
    return fallos


def _verificar_score_completo_regresion(fila: pd.Series) -> list[str]:
    fallos = []
    d1 = _d1_de_fila(fila)
    if d1 is None or not math.isclose(d1, 52.2072, abs_tol=0.01):
        fallos.append(f"D1 esperado ≈52,2072 (ver notebook 04, Sección 8), obtenido {d1}")
    if _es_nulo(fila["d2"]) or not math.isclose(fila["d2"], 13.8889, abs_tol=0.01):
        fallos.append(f"D2 esperado ≈13,8889, obtenido {fila['d2']}")
    return fallos


CASOS: list[CasoGoldenSet] = [
    CasoGoldenSet(
        "7501000112425",
        "Donitas espolvoreadas: azúcar/sal/grasa saturada en percentiles altos dentro de su "
        "categoría, fibra/proteína bajas, NOVA 4. D1 y D2 deben ser bajos.",
        _verificar_d1_d2_malos,
    ),
    CasoGoldenSet(
        "7501030473022",
        "TOSTIS CON FIBRA: azúcar/sal/grasa saturada en percentiles bajos, fibra/proteína altas, "
        "NOVA 1 sin aditivos. D1 y D2 deben ser altos.",
        _verificar_d1_d2_buenos,
    ),
    CasoGoldenSet(
        "0000654193184",
        "Milton's Galletas Saladas Multigrano: allergens='en:gluten' confirmado. Alérgica a gluten "
        "debe salir no_apto.",
        _verificar_alergia_gluten_confirmado,
    ),
    CasoGoldenSet(
        "0010248765159",
        "Fideo mediano: gluten SOLO en traces ('puede contener'), no en allergens. El fail-safe "
        "(A15) debe marcarlo no_apto igual que si estuviera confirmado.",
        _verificar_alergia_gluten_en_traces,
    ),
    CasoGoldenSet(
        "00000140",
        "tisane saveur lunaire: allergens y traces ambos vacíos. Sin ningún dato de alérgenos debe "
        "ser no_verificable, nunca apto sin evidencia.",
        _verificar_alergia_sin_dato,
    ),
    CasoGoldenSet(
        "0000880688789",
        "Mister Natural - Datil Premium: ingredients_analysis_tags trae 'en:vegan' confirmado. "
        "Dieta vegana debe salir compatible.",
        _verificar_dieta_vegano_compatible,
    ),
    CasoGoldenSet(
        "0000182602460",
        "Isabar: ingredients_analysis_tags trae 'en:non-vegan' confirmado. Dieta vegana debe salir "
        "incompatible.",
        _verificar_dieta_vegano_incompatible,
    ),
    CasoGoldenSet(
        "0010248765135",
        "Yemina Semilla de melón: ingredients_analysis_tags trae 'en:maybe-vegan' ('tal vez'). "
        "Dieta vegana debe salir no_verificable, nunca compatible sin evidencia.",
        _verificar_dieta_maybe_no_verificable,
    ),
    CasoGoldenSet(
        "00000154",
        "Mct Oil Powder: sin categoria_referencia resoluble, pero SÍ tiene nova_group. D1 debe ser "
        "None; D2 debe seguir siendo calculable (son independientes entre sí).",
        _verificar_d1_none_d2_presente,
    ),
    CasoGoldenSet(
        "0000880688787",
        "Mister Natural - Chabacano Deshidratado: tiene categoria_referencia (en:dried-fruits) y "
        "dato nutricional, pero SIN nova_group. D1 debe ser calculable; D2 debe ser None.",
        _verificar_d2_none_d1_presente,
    ),
    CasoGoldenSet(
        "5060323907641",
        "product_name vacío en el export, pero generic_name = 'Organic Smooth Almond Butter' "
        "(decisión A28). resolver_nombre_producto debe usar el respaldo.",
        _verificar_nombre_con_respaldo,
    ),
    CasoGoldenSet(
        "0009663393983",
        "Kirkland Signature - Jarabe de Maple: labels_tags = 'en:organic' exacto. D3 debe ser 100% "
        "si la usuaria valora solo esa etiqueta, y 50% si valora dos y el producto solo tiene una.",
        _verificar_d3_organic,
    ),
    CasoGoldenSet(
        "7501030457626",
        "Pan con Centeno: caso de regresión con las 5 dimensiones de D1 y NOVA disponibles, "
        "auditado a mano en notebooks/04_modelo_recomendacion.ipynb (Sección 8). "
        "D1 ≈ 52,2072, D2 ≈ 13,8889.",
        _verificar_score_completo_regresion,
    ),
]


def evaluar(df: pd.DataFrame) -> pd.DataFrame:
    """Corre todos los `CASOS` del golden set contra `df` y devuelve un reporte, un caso por fila.

    `df` debe tener `code` como columna e incluir, para cada `code` de los `CASOS`, las columnas
    de `COLUMNAS_REQUERIDAS`: percentiles de CORE8, `d2` (paso 6), los campos crudos de alergia y
    dieta, `labels_tags`, y las tres columnas de nombre SIN resolver (`product_name_bruto` es el
    `product_name` tal cual viene del snapshot, antes del fallback de A28).

    El resultado trae, por caso: `code`, `descripcion`, `paso` (booleano) y `fallos` (lista de
    mensajes; vacía si `paso` es `True`). Un `code` de un caso que no aparezca en `df` cuenta como
    fallo explícito, no se ignora en silencio.
    """
    df_indexado = df.set_index("code", drop=False)
    filas_reporte = []
    for caso in CASOS:
        if caso.code not in df_indexado.index:
            filas_reporte.append(
                {
                    "code": caso.code,
                    "descripcion": caso.descripcion,
                    "paso": False,
                    "fallos": ["code no encontrado en el DataFrame proporcionado"],
                }
            )
            continue
        fila = df_indexado.loc[caso.code]
        fallos = caso.verificar(fila)
        filas_reporte.append(
            {"code": caso.code, "descripcion": caso.descripcion, "paso": len(fallos) == 0, "fallos": fallos}
        )
    return pd.DataFrame(filas_reporte)
