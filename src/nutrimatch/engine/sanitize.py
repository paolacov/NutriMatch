"""Saneamiento del núcleo nutricional (decisión A18, AGENTS.md).

Detecta valores fuera de un rango físicamente plausible y los marca con una
bandera de calidad, sin eliminarlos ni corregirlos en silencio: el valor
bruto se conserva siempre en su propia columna, y el valor saneado (el único
que se usa para percentiles y `category_stats`) se anula solo para ese
nutriente y ese producto, nunca para toda la fila.
"""

from __future__ import annotations

import pandas as pd

from nutrimatch.engine.constants import CORE8_NUTRIENTES, RANGO_VALIDO


def parsear_numerico(serie: pd.Series) -> pd.Series:
    """Convierte una columna de texto (posiblemente vacía) a float.

    El snapshot se ingirió con `all_varchar=true` (ver scripts/ingesta_off.py),
    así que todas las columnas llegan como texto. Las cadenas vacías se tratan
    como ausencia de dato, nunca como cero (decisión A2).
    """
    limpia = serie.astype("string").str.strip().replace("", pd.NA)
    return pd.to_numeric(limpia, errors="coerce")


def sanear_nucleo_nutricional(df: pd.DataFrame) -> pd.DataFrame:
    """Sanea los ocho nutrientes de CORE8_NUTRIENTES.

    Por cada nutriente añade tres columnas:
    - ``<nutriente>_bruto``: valor numérico parseado tal cual venía en el
      snapshot (o NaN si faltaba). Es el dato original transformado solo en
      tipo, nunca en valor.
    - ``<nutriente>_flag_fuera_de_rango``: True si el valor existe pero cae
      fuera de RANGO_VALIDO. False si está dentro de rango. NUNCA True cuando
      falta el dato (eso es un caso distinto: ausencia, no mala calidad).
    - ``<nutriente>_saneado``: igual al bruto, pero NaN si está fuera de rango
      o si faltaba. Es la única columna que debe alimentar percentiles y
      `category_stats`.

    No modifica `df`; devuelve un DataFrame nuevo con el mismo índice.
    """
    columnas = {}
    for nutriente in CORE8_NUTRIENTES:
        minimo, maximo = RANGO_VALIDO[nutriente]
        bruto = parsear_numerico(df[nutriente])
        fuera_de_rango = bruto.notna() & ((bruto < minimo) | (bruto > maximo))
        saneado = bruto.where(~fuera_de_rango)

        columnas[f"{nutriente}_bruto"] = bruto
        columnas[f"{nutriente}_flag_fuera_de_rango"] = fuera_de_rango
        columnas[f"{nutriente}_saneado"] = saneado

    return pd.DataFrame(columnas, index=df.index)


def corregir_escala_sal_por_sodio(
    df_original: pd.DataFrame,
    df_saneado: pd.DataFrame,
    tolerancia_ratio: float = 0.02,
) -> pd.DataFrame:
    """Corrige `salt_100g` cuando está fuera de rango por un error sistemático de escala.

    Hallazgo del 2026-09-20 (notebooks/03_transformacion_score.ipynb, sección 1):
    55 de los 56 productos con `salt_100g` fuera de rango mantienen la razón
    sal ≈ sodio × 2,5 (fórmula química estándar, no una coincidencia del
    dataset), y al dividir el valor entre 1000 caen en un rango de sal
    perfectamente normal para su tipo de producto. Es compatible con una
    captura en miligramos donde el sistema esperaba gramos, no con una
    corrupción aleatoria.

    Un producto se corrige solo si, estando fuera de rango, su razón
    `salt_100g / sodium_100g` es ≈2,5 (dentro de `tolerancia_ratio`) y el valor
    reescalado (÷1000) cae dentro de RANGO_VALIDO. El caso atípico detectado
    (razón ≈2500, un error de otra naturaleza) queda deliberadamente fuera de
    esta regla y sigue marcado como fuera de rango sin corregir.

    Devuelve una copia de `df_saneado` con:
    - ``salt_100g_saneado`` actualizado con el valor corregido en los casos
      que califican (deja de ser NaN para ellos).
    - ``salt_100g_flag_correccion_escala_aplicada``: True donde se aplicó la
      corrección. Es información de trazabilidad: permite distinguir un
      producto con dato saneado "tal cual vino" de uno con dato saneado
      "corregido por esta regla".

    Requiere `sodium_100g` en `df_original` (no forma parte del núcleo core8;
    se usa únicamente como apoyo para esta corrección puntual).
    """
    sodio = parsear_numerico(df_original["sodium_100g"])
    sal_bruta = df_saneado["salt_100g_bruto"]
    fuera_de_rango = df_saneado["salt_100g_flag_fuera_de_rango"]

    razon = sal_bruta / sodio
    sal_reescalada = sal_bruta / 1000.0
    minimo, maximo = RANGO_VALIDO["salt_100g"]

    es_candidato = (
        fuera_de_rango
        & sodio.notna()
        & (sodio > 0)
        & ((razon - 2.5).abs() <= tolerancia_ratio)
        & sal_reescalada.between(minimo, maximo)
    )

    resultado = df_saneado.copy()
    resultado["salt_100g_flag_correccion_escala_aplicada"] = es_candidato
    resultado.loc[es_candidato, "salt_100g_saneado"] = sal_reescalada[es_candidato]
    return resultado


def flag_suma_macros_excede_100(df_saneado: pd.DataFrame) -> pd.Series:
    """Bandera a nivel de fila: grasa + carbohidratos + proteína (saneados) > 100,5 g.

    Es informativa y no anula ningún nutriente individual por sí sola (cada
    uno ya tiene su propio flag de rango en `sanear_nucleo_nutricional`).
    Señala un problema de consistencia interna del producto que conviene
    mostrar en su ficha, tal como se detectó en el EDA (0,71 % del universo
    con dato en los tres macronutrientes).
    """
    grasa = df_saneado["fat_100g_saneado"]
    carbohidratos = df_saneado["carbohydrates_100g_saneado"]
    proteina = df_saneado["proteins_100g_saneado"]

    todos_presentes = grasa.notna() & carbohidratos.notna() & proteina.notna()
    suma = grasa.fillna(0) + carbohidratos.fillna(0) + proteina.fillna(0)
    return todos_presentes & (suma > 100.5)
