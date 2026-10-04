"""Piloto de match QQP por texto — Fase A del paso 6b del plan de trabajo.

Ver `docs/diagnostico_calidad_datos.md` (sección H, fila 6, parte b) y las decisiones
A35/A36/A41 de `AGENTS.md`. **No hace ningún join automático `QQP → code`** (A35 lo prohíbe
explícitamente): genera candidatos de coincidencia por texto con `rapidfuzz`, toma una muestra
pequeña estratificada por score, y escribe un **CSV** (no Parquet) para que Paola lo revise a
mano marcando la columna `revisado` con `"correcto"`/`"incorrecto"`. La materialización del
Parquet final (`price_*`) es un paso aparte, `scripts/materializar_precios_qqp.py` (Fase B), que
solo corre sobre ese CSV ya revisado.

Deliberadamente acotado:

- Solo el recurso de julio 2026 de QQP (las dos partes), no el histórico completo.
- Solo una lista curada de `categoria` de alimentos/bebidas envasados con marca — excluye
  frescos sin marca (p. ej. "Hortalizas Frescas", casi siempre `marca="S/M"`), medicamentos,
  electrodomésticos, artículos escolares, etc. Vocabulario completo de `categoria` verificado
  en vivo el 2026-09-26 (A41).
- Un tope de filas por (recurso, categoría) vía `datastore_search` con `filters` exacto — nunca
  se descarga una categoría completa ni el recurso completo (665.909 filas).
- El precio **no puntúa** (A5): este script no toca `score_final`, D1/D2/D3, `cov`, bandas de
  ranking ni ningún Parquet existente.

Uso:
    python scripts/piloto_precios_qqp.py                # pull completo, caché activa
    python scripts/piloto_precios_qqp.py --no-cache      # repite todas las peticiones
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from pathlib import Path

import duckdb
import httpx
import pandas as pd
from rapidfuzz import fuzz

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from nutrimatch.engine.identity_homologation import homologar_marca
from nutrimatch.providers.qqp_api import RECURSOS_JULIO_2026, buscar_por_categoria

# Vocabulario real de `categoria` en el recurso de julio 2026 (primera parte), verificado en
# vivo el 2026-09-26 muestreando 40.000 de 665.909 filas ordenadas: 42 categorías distintas.
# Selección de las que corresponden a alimentos/bebidas **envasados con marca** — las que
# comparten espacio semántico con `off_mexico_20260919.parquet` (productos con GTIN, casi
# siempre marcados). Se excluyen a propósito: frescos sin marca (Hortalizas/Frutas Frescas,
# Carne/Pescado/Huevo sin conserva, casi siempre `marca="S/M"`, verificado en la muestra),
# no-alimentos (Medicamentos, Material Escolar, Aparatos Eléctricos/Electrónicos, Arts. de
# Cuidado Personal/Papel Higiénico, Detergentes, Juguetes, Accesorios/Utensilios Domésticos,
# Cigarrillos) y una categoría mixta ambigua (Productos de Temporada Navideños).
CATEGORIAS_ALIMENTOS_BEBIDAS: tuple[str, ...] = (
    "Refrescos Envasados",
    "Derivados de Leche",
    "Condimentos",
    "Carnes Frías Secas y Embutidos",
    "Chocolates y Golosinas",
    "Galletas Pastas y Harinas de Trigo",
    "Pan",
    "Frutas y Legumbres Procesadas",
    "Leche Procesada",
    "Arroz y Cereales Preparados",
    "Legumbres Secas",
    "Aceites y Grasas Veg. Comestibles",
    "Botanas y Bebidas",
    "Pescados y Mariscos en Conserva",
    "Tortillas y Derivados del Maíz",
    "Cerveza",
    "Azúcar",
    "Café",
    "Vinos y Licores",
    "Té",
)

FILAS_POR_CATEGORIA_Y_RECURSO = 150  # tope de trabajo por (recurso, categoría); ver docstring.
UMBRAL_MINIMO_SCORE = 60.0  # piso "a calibrar" (plan, paso 6b) — la muestra estratificada sirve
# precisamente para que la revisión manual diga si este piso es correcto.
TAMANO_MUESTRA = 40
SEMILLA_MUESTRA = 20260926  # reproducible, mismo patrón que A39.


def log(mensaje: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {mensaje}", flush=True)


def _es_nulo(valor: object) -> bool:
    """Cubre `None` y `NaN` de pandas (trampa B13) para texto proveniente de un Parquet."""
    if valor is None:
        return True
    if isinstance(valor, float) and pd.isna(valor):
        return True
    return bool(isinstance(valor, str) and not valor.strip())


def cargar_catalogo(ruta_identidad: Path) -> list[dict]:
    """Carga `identidad_homologada_*.parquet` como lista de dicts (Python puro, evita B13)."""
    con = duckdb.connect()
    df = con.execute(
        f"""
        SELECT code, product_name_homologated, brand_original, brand_homologated
        FROM '{ruta_identidad.as_posix()}'
        """
    ).df()

    filas: list[dict] = []
    for code, nombre, marca_original, marca_homologada in zip(
        df["code"].tolist(),
        df["product_name_homologated"].tolist(),
        df["brand_original"].tolist(),
        df["brand_homologated"].tolist(),
        strict=True,
    ):
        if _es_nulo(marca_homologada) or _es_nulo(nombre):
            continue  # sin marca o sin nombre: no hay texto suficiente para un match confiable.
        filas.append(
            {
                "code": code,
                "product_name_homologated": nombre,
                "brand_original": marca_original,
                "brand_homologated": marca_homologada,
            }
        )
    return filas


def construir_indices(catalogo: list[dict]) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    """Dos índices sobre `brand_homologated`: exacto y por primera palabra (fallback)."""
    indice_exacto: dict[str, list[int]] = {}
    indice_primera_palabra: dict[str, list[int]] = {}
    for i, fila in enumerate(catalogo):
        marca = fila["brand_homologated"]
        indice_exacto.setdefault(marca, []).append(i)
        primera_palabra = marca.split(" ")[0]
        indice_primera_palabra.setdefault(primera_palabra, []).append(i)
    return indice_exacto, indice_primera_palabra


def mejor_candidato(
    marca_qqp: str,
    producto_qqp: str,
    presentacion_qqp: str,
    catalogo: list[dict],
    indice_exacto: dict[str, list[int]],
    indice_primera_palabra: dict[str, list[int]],
) -> tuple[dict, float] | None:
    """Acota candidatos por marca homologada (exacta, si no por primera palabra) y puntúa con
    `rapidfuzz.fuzz.WRatio` el texto completo (marca+producto+presentación vs. marca+nombre).

    Sin esta acotación, comparar cada fila de QQP contra las ~16.851 filas del catálogo sería
    un producto cruzado inviable para un piloto; con ella, solo se comparan candidatos que ya
    comparten una marca homologada (A38) plausible.
    """
    primer_segmento = (marca_qqp or "").split(".")[0].strip()
    marca_homologada_qqp = homologar_marca(primer_segmento)
    if _es_nulo(marca_homologada_qqp):
        return None

    indices_candidatos = indice_exacto.get(marca_homologada_qqp)
    if not indices_candidatos:
        primera_palabra = marca_homologada_qqp.split(" ")[0]
        indices_candidatos = indice_primera_palabra.get(primera_palabra)
    if not indices_candidatos:
        return None

    texto_qqp = f"{marca_qqp} {producto_qqp} {presentacion_qqp}"
    mejor_fila: dict | None = None
    mejor_score = -1.0
    for i in indices_candidatos:
        fila = catalogo[i]
        texto_catalogo = f"{fila['brand_original']} {fila['product_name_homologated']}"
        score = fuzz.WRatio(texto_qqp, texto_catalogo)
        if score > mejor_score:
            mejor_score = score
            mejor_fila = fila
    if mejor_fila is None:
        return None
    return mejor_fila, mejor_score


def recolectar_filas_qqp(cliente: httpx.Client, *, usar_cache: bool) -> list[dict]:
    """Trae filas de las categorías curadas, en ambos recursos de julio 2026, y las dedupea."""
    vistas: set[tuple[str, str, str]] = set()
    filas: list[dict] = []
    for resource_id in RECURSOS_JULIO_2026:
        for categoria in CATEGORIAS_ALIMENTOS_BEBIDAS:
            crudas = buscar_por_categoria(
                resource_id,
                categoria,
                cliente=cliente,
                limite_filas=FILAS_POR_CATEGORIA_Y_RECURSO,
                usar_cache=usar_cache,
            )
            nuevas = 0
            for fila in crudas:
                marca = fila.get("marca")
                producto = fila.get("producto")
                presentacion = fila.get("presentacion")
                if _es_nulo(marca) or _es_nulo(producto):
                    continue
                llave = (marca, producto, presentacion or "")
                if llave in vistas:
                    continue
                vistas.add(llave)
                filas.append(fila)
                nuevas += 1
            log(f"  {resource_id[:8]}… · {categoria}: {len(crudas)} filas, {nuevas} nuevas tras dedupe")
    return filas


def generar_candidatos(filas_qqp: list[dict], catalogo: list[dict]) -> pd.DataFrame:
    indice_exacto, indice_primera_palabra = construir_indices(catalogo)
    registros: list[dict] = []
    for fila in filas_qqp:
        resultado = mejor_candidato(
            fila.get("marca") or "",
            fila.get("producto") or "",
            fila.get("presentacion") or "",
            catalogo,
            indice_exacto,
            indice_primera_palabra,
        )
        if resultado is None:
            continue
        candidato, score = resultado
        if score < UMBRAL_MINIMO_SCORE:
            continue
        registros.append(
            {
                "qqp_producto": fila.get("producto"),
                "qqp_presentacion": fila.get("presentacion"),
                "qqp_marca": fila.get("marca"),
                "qqp_precio": fila.get("precio"),
                "qqp_fecha": fila.get("fecha_registro"),
                "code_candidato": candidato["code"],
                "product_name_homologated": candidato["product_name_homologated"],
                "brand_original": candidato["brand_original"],
                "score": round(score, 1),
                "revisado": "",
            }
        )
    return pd.DataFrame(registros)


def muestrear_estratificado(candidatos: pd.DataFrame, *, tamano: int, semilla: int) -> pd.DataFrame:
    """Muestra estratificada por rango de score: [60,70) [70,80) [80,90) [90,100]."""
    if candidatos.empty:
        return candidatos

    cortes = [60, 70, 80, 90, 100.01]
    etiquetas = ["60-70", "70-80", "80-90", "90-100"]
    baldes: dict[str, list[int]] = {etiqueta: [] for etiqueta in etiquetas}
    for idx, score in zip(candidatos.index.tolist(), candidatos["score"].tolist(), strict=True):
        for etiqueta, limite_inferior, limite_superior in zip(
            etiquetas, cortes[:-1], cortes[1:], strict=True
        ):
            if limite_inferior <= score < limite_superior:
                baldes[etiqueta].append(idx)
                break

    rng = random.Random(semilla)
    objetivo_por_balde = tamano // len(etiquetas)
    elegidos: list[int] = []
    sobrantes: list[int] = []
    for etiqueta in etiquetas:
        indices_balde = baldes[etiqueta][:]
        rng.shuffle(indices_balde)
        elegidos.extend(indices_balde[:objetivo_por_balde])
        sobrantes.extend(indices_balde[objetivo_por_balde:])

    faltante = tamano - len(elegidos)
    if faltante > 0 and sobrantes:
        rng.shuffle(sobrantes)
        elegidos.extend(sobrantes[:faltante])

    rng.shuffle(elegidos)  # orden final aleatorio, no agrupado por rango de score.
    return candidatos.loc[elegidos[:tamano]].reset_index(drop=True)


def reportar(filas_qqp: list[dict], candidatos: pd.DataFrame, muestra: pd.DataFrame) -> None:
    log(f"Filas de QQP recolectadas (deduplicadas): {len(filas_qqp)}")
    log(f"Candidatos con score >= {UMBRAL_MINIMO_SCORE}: {len(candidatos)}")
    if not candidatos.empty:
        log(f"  score: min={candidatos['score'].min():.1f} max={candidatos['score'].max():.1f} "
            f"promedio={candidatos['score'].mean():.1f}")
        log(f"  codes candidatos únicos: {candidatos['code_candidato'].nunique()}")
    log(f"Muestra final para revisión manual: {len(muestra)} filas")
    if not muestra.empty:
        distribucion = pd.cut(
            muestra["score"], bins=[60, 70, 80, 90, 100.01], right=False,
            labels=["60-70", "70-80", "80-90", "90-100"],
        ).value_counts().sort_index()
        for rango, n in distribucion.items():
            log(f"    {rango}: {n}")
        log("  ejemplos:")
        for _, fila in muestra.head(5).iterrows():
            log(
                f"    [{fila['score']}] QQP «{fila['qqp_marca']} · {fila['qqp_producto']}» "
                f"→ code {fila['code_candidato']} «{fila['brand_original']} "
                f"{fila['product_name_homologated']}»"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fecha-identidad", default="20260919", help="fecha del Parquet de identidad homologada"
    )
    parser.add_argument("--no-cache", action="store_true", help="ignora la caché local en disco")
    args = parser.parse_args()

    fecha_pull = time.strftime("%Y%m%d")  # fecha local, citable (ver piloto_precios_open_prices.py)
    ruta_identidad = REPO_ROOT / "datos" / "procesados" / f"identidad_homologada_{args.fecha_identidad}.parquet"
    ruta_salida = REPO_ROOT / "datos" / "procesados" / f"piloto_qqp_candidatos_{fecha_pull}.csv"

    if not ruta_identidad.exists():
        log(f"ERROR: no existe {ruta_identidad}. Corre `scripts/homologar_identidad.py` primero.")
        return 1

    log(f"Leyendo catálogo homologado: {ruta_identidad.relative_to(REPO_ROOT)}")
    catalogo = cargar_catalogo(ruta_identidad)
    log(f"Catálogo con marca y nombre disponibles: {len(catalogo):,} productos")

    usar_cache = not args.no_cache
    log(f"Consultando QQP (julio 2026, {len(CATEGORIAS_ALIMENTOS_BEBIDAS)} categorías, "
        f"caché: {'activa' if usar_cache else 'desactivada'})")
    with httpx.Client() as cliente:
        filas_qqp = recolectar_filas_qqp(cliente, usar_cache=usar_cache)

    log("")
    log("Generando candidatos con rapidfuzz.fuzz.WRatio…")
    candidatos = generar_candidatos(filas_qqp, catalogo)
    muestra = muestrear_estratificado(candidatos, tamano=TAMANO_MUESTRA, semilla=SEMILLA_MUESTRA)

    log("")
    reportar(filas_qqp, candidatos, muestra)

    muestra.to_csv(ruta_salida, index=False, encoding="utf-8")
    log("")
    log(f"Escrito: {ruta_salida.relative_to(REPO_ROOT)} ({ruta_salida.stat().st_size:,} bytes)")
    log("Columna 'revisado' vacía: marca cada fila 'correcto'/'incorrecto' a mano (A35) antes de "
        "correr scripts/materializar_precios_qqp.py.")
    log("El precio no puntúa (A5): no se tocó score_final, D1/D2/D3, cov ni ningún Parquet existente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
