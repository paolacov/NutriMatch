"""Auditoría de cobertura funcional — solo lectura.

Lee `dataset_referencia_20260927.parquet`, no lo escribe. No imputa, no sintetiza,
no toca API/Angular/fórmulas. Escribe el CSV de matriz y deja el markdown al documento
hermano en docs/.

Uso:
    uv run python scripts/auditar_cobertura_funcional.py
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nutrimatch.engine.compatibility_score import calcular_score_compatibilidad
from nutrimatch.engine.hard_filters import evaluar_alergia, evaluar_dieta
from nutrimatch.engine.nutrition_score import NUTRIENTES_D1_SIGNO, calcular_subpuntaje_d1
from nutrimatch.engine.preference_score import calcular_d3
from nutrimatch.engine.user_weights import convertir_prioridades_a_pesos
from nutrimatch.services.ranking import asignar_banda

N = 16_851
N_PUNTUABLE = 5_864
N_PRICE_REAL = 263
PARQUET = REPO_ROOT / "datos" / "procesados" / "dataset_referencia_20260927.parquet"
CSV_OUT = REPO_ROOT / "datos" / "procesados" / "matriz_cobertura_funcionalidades_20260927.csv"
NUT_FICHA = (
    "energy-kcal_100g",
    "proteins_100g",
    "carbohydrates_100g",
    "sugars_100g",
    "fat_100g",
    "fiber_100g",
    "salt_100g",
)
PERFILES = {
    "Ana": {
        "allergen_tags": [],
        "diet": None,
        "valued_labels": ["en:organic", "en:no-gluten"],
        "priority_order": ["D1", "D3", "D2"],
    },
    "Beto": {
        "allergen_tags": [],
        "diet": None,
        "valued_labels": ["en:fair-trade"],
        "priority_order": ["D2", "D1", "D3"],
    },
    "Caro": {
        "allergen_tags": [],
        "diet": None,
        "valued_labels": [],
        "priority_order": ["D3", "D1", "D2"],
    },
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _es_nulo(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, float) and math.isnan(valor):
        return True
    if isinstance(valor, str) and valor.strip().lower() in {"", "nan", "none", "<na>"}:
        return True
    return bool(pd.isna(valor)) if not isinstance(valor, str) else False


def _tiene_texto(valor: Any) -> bool:
    return not _es_nulo(valor) and bool(str(valor).strip())


def _tiene_nutriente(fila: dict[str, Any], col: str) -> bool:
    for clave in (f"{col}_saneado", f"{col}_bruto", col):
        if not _es_nulo(fila.get(clave)):
            return True
    return False


def estado(pct: float, implementada: bool = True) -> str:
    if not implementada:
        return "NO DISPONIBLE"
    if pct >= 80:
        return "COMPLETA"
    if pct >= 40:
        return "PARCIAL"
    if pct >= 5:
        return "LIMITADA"
    return "NO DISPONIBLE"


def pct(n: int, den: int = N) -> float:
    return 100.0 * n / den if den else 0.0


def calidad_de(niveles: list[str]) -> str:
    if not niveles:
        return "n/a"
    conteo = {k: 0 for k in ("alta", "media", "baja", "insuficiente")}
    for n in niveles:
        if n in conteo:
            conteo[n] += 1
    total = sum(conteo.values()) or 1
    return (
        f"alta {100*conteo['alta']/total:.1f}% · media {100*conteo['media']/total:.1f}% · "
        f"baja {100*conteo['baja']/total:.1f}% · insuficiente {100*conteo['insuficiente']/total:.1f}%"
    )


def main() -> int:
    sha_antes = sha256(PARQUET)
    log(f"Leyendo {PARQUET.name} sha256={sha_antes}")
    df = duckdb.connect().execute(f"SELECT * FROM read_parquet('{PARQUET.as_posix()}')").df()
    cols = set(df.columns)

    assert len(df) == N, len(df)
    assert df["code"].nunique() == N
    assert len(df) - df["code"].nunique() == 0
    assert int(df["universo_puntuable"].sum()) == N_PUNTUABLE
    assert int((df["price_status"] == "REAL").sum()) == N_PRICE_REAL
    assert "d1" not in cols and "d3" not in cols and "cov" not in cols and "score_final" not in cols
    assert "SYNTHETIC" not in set(df["price_status"].dropna().astype(str))
    log("Validaciones 1–8 del parquet: ok")

    filas = df.to_dict(orient="records")
    niveles = [str(f.get("data_quality_level")) for f in filas]
    puntuable_mask = [bool(f.get("universo_puntuable")) for f in filas]

    def contar(pred) -> int:
        return sum(1 for f in filas if pred(f))

    def niveles_si(pred) -> list[str]:
        return [str(f.get("data_quality_level")) for f in filas if pred(f)]

    has_code = N
    has_nombre = contar(lambda f: _tiene_texto(f.get("product_name_homologated")) or _tiene_texto(f.get("product_name")))
    has_marca = contar(lambda f: _tiene_texto(f.get("brand_original")) or _tiene_texto(f.get("brands")))
    has_cat_ficha = contar(
        lambda f: _tiene_texto(f.get("main_category"))
        or _tiene_texto(f.get("main_category_en"))
        or _tiene_texto(f.get("categoria_referencia"))
    )
    has_ing = contar(lambda f: _tiene_texto(f.get("ingredients_text")) or _tiene_texto(f.get("ingredients_tags")))
    n_nut = []
    for f in filas:
        n_nut.append(sum(1 for col in NUT_FICHA if _tiene_nutriente(f, col)))
    has_nut1 = sum(1 for n in n_nut if n >= 1)
    has_nut7 = sum(1 for n in n_nut if n == 7)
    has_nova = contar(lambda f: not _es_nulo(f.get("nova_group")))
    has_add = contar(lambda f: not _es_nulo(f.get("additives_n")))
    has_labels = contar(lambda f: _tiene_texto(f.get("labels_tags")))
    has_exceso = contar(
        lambda f: _tiene_texto(f.get("labels_tags")) and "exceso" in str(f.get("labels_tags")).lower()
    )
    labels_sin_exceso = contar(
        lambda f: _tiene_texto(f.get("labels_tags")) and "exceso" not in str(f.get("labels_tags")).lower()
    )
    has_allergens = contar(lambda f: _tiene_texto(f.get("allergens")))
    has_traces = contar(lambda f: _tiene_texto(f.get("traces")))
    has_all_or_tr = contar(lambda f: _tiene_texto(f.get("allergens")) or _tiene_texto(f.get("traces")))
    has_diet_tags = contar(lambda f: _tiene_texto(f.get("ingredients_analysis_tags")))
    has_price = contar(lambda f: f.get("price_status") == "REAL" and not _es_nulo(f.get("price")))
    has_image = contar(lambda f: _tiene_texto(f.get("image_small_url")) or _tiene_texto(f.get("image_url")))
    has_qty = contar(lambda f: _tiene_texto(f.get("quantity")))

    d1_ok = 0
    d2_ok = contar(lambda f: not _es_nulo(f.get("d2")))
    perc_d1 = {nut: 0 for nut in NUTRIENTES_D1_SIGNO}
    for f in filas:
        percentiles = {nut: f.get(f"percentil_{nut}") for nut in NUTRIENTES_D1_SIGNO}
        d1, _ = calcular_subpuntaje_d1(percentiles)
        if d1 is not None:
            d1_ok += 1
        for nut, val in percentiles.items():
            if not _es_nulo(val):
                perc_d1[nut] += 1

    compare_completa = 0
    compare_parcial = 0
    compare_limitada = 0
    for f, n in zip(filas, n_nut, strict=True):
        d1, _ = calcular_subpuntaje_d1({nut: f.get(f"percentil_{nut}") for nut in NUTRIENTES_D1_SIGNO})
        tiene_d2 = not _es_nulo(f.get("d2"))
        if n == 7 and d1 is not None and tiene_d2:
            compare_completa += 1
        elif n >= 4 or d1 is not None or tiene_d2:
            compare_parcial += 1
        else:
            compare_limitada += 1

    # Dieta vegana: determinable vs no
    vegan_det = 0
    vegan_comp = 0
    vegan_inc = 0
    vegan_nv = 0
    for f in filas:
        est = evaluar_dieta(f.get("ingredients_analysis_tags"), "vegano")
        if est == "compatible":
            vegan_comp += 1
            vegan_det += 1
        elif est == "incompatible":
            vegan_inc += 1
            vegan_det += 1
        else:
            vegan_nv += 1

    # Alergia leche (ejemplo del catálogo de UI)
    alg_det = 0
    alg_apto = 0
    alg_no = 0
    alg_nv = 0
    for f in filas:
        est = evaluar_alergia(f.get("allergens"), f.get("traces"), ["en:milk"])
        if est == "apto":
            alg_apto += 1
            alg_det += 1
        elif est == "no_apto":
            alg_no += 1
            alg_det += 1
        else:
            alg_nv += 1

    log("Calculando bandas Ana/Beto/Caro (mismas fórmulas, solo lectura)...")
    bandas: dict[str, dict[str, int]] = {}
    for nombre, perfil in PERFILES.items():
        pesos = convertir_prioridades_a_pesos(list(perfil["priority_order"]))
        cubetas = {"ranking": 0, "no_verificable": 0, "informacion_insuficiente": 0, "excluido": 0}
        for f in filas:
            percentiles = {nut: f.get(f"percentil_{nut}") for nut in NUTRIENTES_D1_SIGNO}
            d1, _ = calcular_subpuntaje_d1(percentiles)
            d2 = None if _es_nulo(f.get("d2")) else float(f.get("d2"))
            d3 = calcular_d3(f.get("labels_tags"), perfil["valued_labels"])
            allergy = evaluar_alergia(f.get("allergens"), f.get("traces"), perfil["allergen_tags"])
            diet = "apto"
            if perfil["diet"]:
                diet = evaluar_dieta(f.get("ingredients_analysis_tags"), perfil["diet"])
            else:
                diet = "compatible"
            resultado = calcular_score_compatibilidad({"D1": d1, "D2": d2, "D3": d3}, pesos)
            banda = asignar_banda(allergy, diet if perfil["diet"] else "compatible", bool(resultado["informacion_insuficiente"]))
            cubetas[banda] += 1
        bandas[nombre] = cubetas
        log(f"  {nombre}: {cubetas}")

    calidad_puntuable = calidad_de([n for n, p in zip(niveles, puntuable_mask, strict=True) if p])
    calidad_total = calidad_de(niveles)

    filas_matriz: list[dict[str, Any]] = []

    def add(func, req, n_eval, den, calidad, limitacion, implementada=True):
        p = pct(n_eval, den)
        filas_matriz.append(
            {
                "funcionalidad": func,
                "requisitos_minimos": req,
                "productos_evaluables": n_eval,
                "denominador": den,
                "pct_universo": round(pct(n_eval, N), 2),
                "pct_denominador": round(p, 2),
                "calidad": calidad,
                "estado": estado(p if den == N else pct(n_eval, N) if den != N else p, implementada),
                "limitacion": limitacion,
            }
        )
        # Estado siempre sobre % del universo 16851, salvo que den==N (igual).
        # Recompute estado on universe % for consistency in the matrix.
        filas_matriz[-1]["estado"] = estado(pct(n_eval, N), implementada)

    add(
        "Búsqueda por GTIN/code",
        "code (siempre presente)",
        has_code,
        N,
        calidad_total,
        "La API busca contains literal en code. 100 % de los GTIN son consultables.",
    )
    add(
        "Búsqueda por nombre",
        "product_name tras _preparar_referencia (= product_name_homologated)",
        has_nombre,
        N,
        calidad_de(niveles_si(lambda f: _tiene_texto(f.get("product_name_homologated")) or _tiene_texto(f.get("product_name")))),
        "No usa generic_name ni abbreviated en el filtro. 1.679 sin nombre no salen por texto.",
    )
    add(
        "Búsqueda por marca",
        "brand_original o brands (primer columna existente)",
        has_marca,
        N,
        calidad_de(niveles_si(lambda f: _tiene_texto(f.get("brand_original")) or _tiene_texto(f.get("brands")))),
        "Implementada. 3.749 sin marca no coinciden por marca.",
    )
    add(
        "Búsqueda por categoría",
        "no implementada (ni categories_tags ni categoria_referencia)",
        0,
        N,
        "n/a",
        "filtrar_por_query no lee categoría.",
        implementada=False,
    )
    add(
        "Ficha: apertura por code",
        "code en el catálogo",
        N,
        N,
        calidad_total,
        "GET /products/{code} responde para los 16.851. Atributos pueden ir UNAVAILABLE.",
    )
    add("Ficha: nombre para mostrar", "product_name_homologated o product_name", has_nombre, N, calidad_de(niveles_si(lambda f: _tiene_texto(f.get("product_name_homologated")) or _tiene_texto(f.get("product_name")))), "NULL se muestra como hueco; no se inventa placeholder.")
    add("Ficha: marca", "brand_original o brands", has_marca, N, calidad_de(niveles_si(lambda f: _tiene_texto(f.get("brand_original")) or _tiene_texto(f.get("brands")))), "UI: «Marca no disponible».")
    add("Ficha: categoría", "main_category o main_category_en o categoria_referencia", has_cat_ficha, N, calidad_de(niveles_si(lambda f: _tiene_texto(f.get("main_category")) or _tiene_texto(f.get("main_category_en")) or _tiene_texto(f.get("categoria_referencia")))), "No es filtro de búsqueda.")
    add("Ficha: ingredientes", "ingredients_text o ingredients_tags", has_ing, N, calidad_de(niveles_si(lambda f: _tiene_texto(f.get("ingredients_text")) or _tiene_texto(f.get("ingredients_tags")))), "NULL ≠ «sin ingredientes».")
    add("Ficha: ≥1 nutriente de los 7 mostrados", "saneado/bruto/crudo de energy, proteins, carbs, sugars, fat, fiber, salt", has_nut1, N, calidad_de([niveles[i] for i, n in enumerate(n_nut) if n >= 1]), "saturated-fat puntúa D1 pero no se lista en la ficha.")
    add("Ficha: 7 nutrientes de ficha", "los 7 de NUTRIENTES_FICHA con algún valor", has_nut7, N, calidad_de([niveles[i] for i, n in enumerate(n_nut) if n == 7]), "Cero real cuenta como dato.")
    add("Ficha: NOVA", "nova_group", has_nova, N, calidad_de(niveles_si(lambda f: not _es_nulo(f.get("nova_group")))), "additives_n va a la explicación de ranking, no al schema de ficha.")
    add("Ficha: aditivos (explain, no ficha)", "additives_n en ProductExplanation", has_add, N, calidad_de(niveles_si(lambda f: not _es_nulo(f.get("additives_n")))), "0 aditivos es REAL, no missing.")
    add("Ficha: etiquetas/sellos", "labels_tags", has_labels, N, calidad_de(niveles_si(lambda f: _tiene_texto(f.get("labels_tags")))), "Sin labels ≠ «sin sellos NOM-051».")
    add("Ficha: alérgenos declarados (campo ficha)", "allergens (no traces)", has_allergens, N, calidad_de(niveles_si(lambda f: _tiene_texto(f.get("allergens")))), "La ficha no muestra traces; el filtro de alergia sí los usa.")
    add("Ficha: precio REAL", "price_status=REAL y price no nulo", has_price, N, calidad_de(niveles_si(lambda f: f.get("price_status") == "REAL")), "Overlay SYNTHETIC de Angular no cuenta. 16.588 UNAVAILABLE.")
    add("Ficha: imagen", "image_small_url o image_url", has_image, N, calidad_de(niveles_si(lambda f: _tiene_texto(f.get("image_small_url")) or _tiene_texto(f.get("image_url")))), "Sin imagen se muestra marca de categoría.")
    add(
        "Comparación completa",
        "7 nutrientes de ficha + D1 calculable + D2 calculable",
        compare_completa,
        N,
        calidad_de(
            [
                str(f.get("data_quality_level"))
                for f, n in zip(filas, n_nut, strict=True)
                if n == 7
                and calcular_subpuntaje_d1({nut: f.get(f"percentil_{nut}") for nut in NUTRIENTES_D1_SIGNO})[0] is not None
                and not _es_nulo(f.get("d2"))
            ]
        ),
        "Cualquier par se puede abrir. Completa = se pueden contrastar score D1/D2 y los 7 nutrientes.",
    )
    add("Comparación parcial", "≥4 nutrientes de ficha o D1 o D2, y no completa", compare_parcial, N, calidad_de([str(f.get("data_quality_level")) for f, n in zip(filas, n_nut, strict=True) if not (n == 7 and calcular_subpuntaje_d1({nut: f.get(f"percentil_{nut}") for nut in NUTRIENTES_D1_SIGNO})[0] is not None and not _es_nulo(f.get("d2"))) and (n >= 4 or calcular_subpuntaje_d1({nut: f.get(f"percentil_{nut}") for nut in NUTRIENTES_D1_SIGNO})[0] is not None or not _es_nulo(f.get("d2")))]), "UI pone «Sin dato» / — ; no inventa.")
    add("Comparación limitada", "solo identidad o <4 nutrientes y sin D1/D2", compare_limitada, N, calidad_de([str(f.get("data_quality_level")) for f, n in zip(filas, n_nut, strict=True) if n < 4 and calcular_subpuntaje_d1({nut: f.get(f"percentil_{nut}") for nut in NUTRIENTES_D1_SIGNO})[0] is None and _es_nulo(f.get("d2"))]), "Se puede listar el producto; no hay contraste numérico útil.")
    add("Ranking: ejecutable (asigna banda A32)", "perfil + fila de catálogo (16.851)", N, N, calidad_total, "Todos entran a exactamente una banda. No requiere universo_puntuable para existir.")
    add("Ranking: universo_puntuable (A22)", "≥4/8 percentiles + D2", N_PUNTUABLE, N, calidad_puntuable, "Filtro previo agnóstico de perfil. Confirmado 5.864.")
    add("Ranking: D1 calculable (A27)", "≥1 percentil de los 5 nutrientes con signo", d1_ok, N, calidad_de(niveles_si(lambda f: calcular_subpuntaje_d1({nut: f.get(f"percentil_{nut}") for nut in NUTRIENTES_D1_SIGNO})[0] is not None)), "No materializado. Runtime.")
    add("Ranking: D2 calculable (A23)", "d2 no nulo (= tiene NOVA)", d2_ok, N, calidad_de(niveles_si(lambda f: not _es_nulo(f.get("d2")))), "Persistido en el Parquet.")
    add(
        "Alternativas (módulo dedicado)",
        "no existe en API ni Angular",
        0,
        N,
        "n/a",
        "No hay endpoint ni pantalla de «más proteína / menos azúcar».",
        implementada=False,
    )
    add("Capacidad D1: más proteína", "percentil_proteins_100g", perc_d1["proteins_100g"], N, "derived", "Es el signo +1 de D1, no un motor de alternativas.")
    add("Capacidad D1: menos azúcar", "percentil_sugars_100g", perc_d1["sugars_100g"], N, "derived", "Signo −1 de D1.")
    add("Capacidad D1: menos sal", "percentil_salt_100g", perc_d1["salt_100g"], N, "derived", "Signo −1 de D1. Grasa total no puntúa (A27).")
    add("Capacidad D1: menos grasa saturada", "percentil_saturated-fat_100g", perc_d1["saturated-fat_100g"], N, "derived", "fat_100g es informativo en ficha, no D1.")
    add("Capacidad D1: más fibra", "percentil_fiber_100g", perc_d1["fiber_100g"], N, "derived", "Signo +1 de D1.")
    add(
        "Alertas: sello NOM-051 determinable",
        "labels_tags presente (exceso o no)",
        has_labels,
        N,
        calidad_de(niveles_si(lambda f: _tiene_texto(f.get("labels_tags")))),
        f"Con exceso: {has_exceso}. Labels sin exceso (determinado: sin sello): {labels_sin_exceso}. Sin labels: no se puede determinar.",
    )
    add(
        "Alertas: sello exceso presente",
        "labels_tags contiene 'exceso'",
        has_exceso,
        N,
        calidad_de(niveles_si(lambda f: _tiene_texto(f.get("labels_tags")) and "exceso" in str(f.get("labels_tags")).lower())),
        "Informan, no puntúan (A9). No es «no cumple» si falta labels.",
    )
    add(
        "Alertas: alergia determinable (perfil con en:milk)",
        "allergens o traces con texto",
        alg_det,
        N,
        calidad_de(niveles_si(lambda f: _tiene_texto(f.get("allergens")) or _tiene_texto(f.get("traces")))),
        f"apto={alg_apto}; no_apto={alg_no}; no_verificable={alg_nv} (no se puede determinar). NULL ≠ no cumple.",
    )
    add(
        "Alertas: dieta vegana determinable",
        "ingredients_analysis_tags con en:vegan o en:non-vegan",
        vegan_det,
        N,
        calidad_de(niveles_si(lambda f: evaluar_dieta(f.get("ingredients_analysis_tags"), "vegano") != "no_verificable")),
        f"compatible={vegan_comp}; incompatible={vegan_inc}; no_verificable={vegan_nv}.",
    )
    add(
        "Personalización (ranking con perfil Ana/Beto/Caro)",
        "priority_order + opcional alergia/dieta/labels; producto con D1/D2/D3 según cov",
        N,
        N,
        calidad_total,
        f"Ana ranking={bandas['Ana']['ranking']} insuf={bandas['Ana']['informacion_insuficiente']}; Caro ranking={bandas['Caro']['ranking']} insuf={bandas['Caro']['informacion_insuficiente']}.",
    )
    add("Precio REAL (ficha/comparar)", "price_status=REAL", has_price, N, calidad_de(niveles_si(lambda f: f.get("price_status") == "REAL")), "No puntúa. Comparar por precio solo es útil entre productos con REAL.")
    add(
        "Recetas / LLM",
        "no hay motor; /recetas lista el carrito",
        0,
        N,
        "n/a",
        "Pantalla explícita: no propone platillos. Capa LLM apagada.",
        implementada=False,
    )

    # Fix estado for compare_parcial/limitada: those are partitions, estado should reflect
    # their share of universe but the FEATURE compare exists. Keep as calculated.

    out = pd.DataFrame(filas_matriz)
    # Recalculate estado consistently on pct_universo
    out["estado"] = [
        estado(r.pct_universo, r.funcionalidad not in {"Búsqueda por categoría", "Alternativas (módulo dedicado)", "Recetas / LLM"})
        for r in out.itertuples()
    ]
    out.to_csv(CSV_OUT, index=False)

    sha_despues = sha256(PARQUET)
    if sha_despues != sha_antes:
        raise RuntimeError("el Parquet de referencia cambió durante la auditoría")

    extra = {
        "n": N,
        "n_puntuable": N_PUNTUABLE,
        "price_real": has_price,
        "price_open_prices": int(((df["price_status"] == "REAL") & (df["price_source"] == "open_prices")).sum()),
        "price_qqp": int(((df["price_status"] == "REAL") & (df["price_source"] == "qqp_profeco")).sum()),
        "sha256": sha_antes,
        "calidad_total": calidad_total,
        "calidad_puntuable": calidad_puntuable,
        "bandas": bandas,
        "has_nombre": has_nombre,
        "has_marca": has_marca,
        "has_cat": has_cat_ficha,
        "has_ing": has_ing,
        "has_nut1": has_nut1,
        "has_nut7": has_nut7,
        "has_nova": has_nova,
        "has_add": has_add,
        "has_labels": has_labels,
        "has_exceso": has_exceso,
        "labels_sin_exceso": labels_sin_exceso,
        "has_allergens": has_allergens,
        "has_traces": has_traces,
        "has_all_or_tr": has_all_or_tr,
        "has_diet_tags": has_diet_tags,
        "has_image": has_image,
        "has_qty": has_qty,
        "d1_ok": d1_ok,
        "d2_ok": d2_ok,
        "perc_d1": perc_d1,
        "compare_completa": compare_completa,
        "compare_parcial": compare_parcial,
        "compare_limitada": compare_limitada,
        "alg_apto": alg_apto,
        "alg_no": alg_no,
        "alg_nv": alg_nv,
        "vegan_comp": vegan_comp,
        "vegan_inc": vegan_inc,
        "vegan_nv": vegan_nv,
        "calidad_puntuable_counts": {
            k: sum(1 for n, p in zip(niveles, puntuable_mask, strict=True) if p and n == k)
            for k in ("alta", "media", "baja", "insuficiente")
        },
        "calidad_total_counts": {k: niveles.count(k) for k in ("alta", "media", "baja", "insuficiente")},
    }
    extra_path = REPO_ROOT / "datos" / "procesados" / "auditoria_cobertura_funcional_20260927.json"
    extra_path.write_text(json.dumps(extra, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log(f"CSV: {CSV_OUT.relative_to(REPO_ROOT)}")
    log(f"JSON: {extra_path.relative_to(REPO_ROOT)}")
    log(f"Parquet intacto sha256={sha_despues}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
