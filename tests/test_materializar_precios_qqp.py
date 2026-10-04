"""Pruebas de la Fase B de QQP (`scripts/materializar_precios_qqp.py`), con un CSV sintético.

No hay revisión manual real todavía (A35: "solo una muestra pequeña con match revisado a
mano"): estas pruebas fijan el comportamiento del script contra una fixture inventada,
**nunca** contra `datos/procesados/piloto_qqp_candidatos_*.csv` real (que además no existe
todavía revisado).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from materializar_precios_qqp import cargar_csv_revisado, construir_tabla_precios


def _csv_sintetico() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "qqp_producto": "Café Soluble",
                "qqp_presentacion": "Frasco 120 Gr.",
                "qqp_marca": "Nescafé. Clásico",
                "qqp_precio": 89.5,
                "qqp_fecha": "2026-07-15",
                "code_candidato": "7501055310209",
                "product_name_homologated": "Nescafe Clasico 120g",
                "brand_original": "Nescafe",
                "score": 92.3,
                "revisado": "correcto",
            },
            {
                "qqp_producto": "Agua con Gas",
                "qqp_presentacion": "Botella 600 Ml.",
                "qqp_marca": "Peñafiel",
                "qqp_precio": 15.0,
                "qqp_fecha": "2026-07-10",
                "code_candidato": "7501055300000",
                "product_name_homologated": "Agua Mineral",
                "brand_original": "Peñafiel",
                "score": 61.0,
                "revisado": "incorrecto",
            },
            {
                "qqp_producto": "Cerveza",
                "qqp_presentacion": "Botella 940 Ml.",
                "qqp_marca": "Corona",
                "qqp_precio": 32.0,
                "qqp_fecha": "2026-07-12",
                "code_candidato": "7501064191019",
                "product_name_homologated": "Corona Extra 940ml",
                "brand_original": "Corona",
                "score": 88.0,
                "revisado": "",
            },
        ]
    )


def test_solo_materializa_filas_marcadas_correcto():
    resultado = construir_tabla_precios(_csv_sintetico(), fecha_pull="20260927")

    assert len(resultado) == 1
    fila = resultado.iloc[0]
    assert fila["code"] == "7501055310209"
    assert fila["product_code"] is None
    assert fila["price"] == 89.5
    assert fila["currency"] == "MXN"
    assert fila["match_method"] == "text_reviewed"
    assert fila["match_confidence"] == 0.923
    assert fila["price_status"] == "REAL"
    assert fila["qqp_marca"] == "Nescafé. Clásico"


def test_revisado_insensible_a_mayusculas_y_espacios():
    csv = _csv_sintetico()
    csv.loc[0, "revisado"] = "  Correcto  "

    resultado = construir_tabla_precios(csv, fecha_pull="20260927")

    assert len(resultado) == 1


def test_filas_incorrecto_o_sin_revisar_quedan_fuera():
    csv = _csv_sintetico()
    csv["revisado"] = ["incorrecto", "incorrecto", ""]

    resultado = construir_tabla_precios(csv, fecha_pull="20260927")

    assert resultado.empty


def test_revisado_con_nan_no_falla():
    import numpy as np

    csv = _csv_sintetico()
    csv.loc[2, "revisado"] = np.nan  # celda genuinamente vacía, como llegaría de un CSV real.

    resultado = construir_tabla_precios(csv, fecha_pull="20260927")

    assert len(resultado) == 1  # solo la fila 0 ("correcto"); la NaN no rompe ni se cuela.


def test_match_confidence_es_score_sobre_cien():
    resultado = construir_tabla_precios(_csv_sintetico(), fecha_pull="20260927")
    assert resultado.iloc[0]["match_confidence"] == round(92.3 / 100.0, 4)


def test_cargar_csv_revisado_preserva_cero_inicial_en_code_candidato(tmp_path):
    """Regresión de B15: un CSV real en disco con un `code_candidato` con cero inicial (GTIN
    de 13 dígitos, p. ej. '0074323081411') debe leerse como texto, nunca como BIGINT — que
    borraría el cero en silencio. El test sintético anterior nunca pasa por un CSV real (el
    DataFrame se construye directo en Python), así que no habría detectado esta trampa; por
    eso esta prueba sí escribe y relee un archivo de verdad."""
    ruta_csv = tmp_path / "candidatos.csv"
    csv_sintetico = _csv_sintetico()
    csv_sintetico.loc[0, "code_candidato"] = "0074323081411"
    csv_sintetico.to_csv(ruta_csv, index=False)

    leido = cargar_csv_revisado(ruta_csv)

    assert leido["code_candidato"].dtype == object or str(leido["code_candidato"].dtype) in (
        "object",
        "string",
        "str",
    )
    assert leido.loc[0, "code_candidato"] == "0074323081411"

    resultado = construir_tabla_precios(leido, fecha_pull="20260927")
    assert resultado.iloc[0]["code"] == "0074323081411"
