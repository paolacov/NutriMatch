"""Catálogo de figuras del dataset operativo.

Las tres primeras describen el universo de 13 093 productos (EDA). Las dos
últimas describen las variables que entran a D1 en el universo puntuable
(ingeniería). Ninguna figura recalcula percentiles, D2 ni el score.

El precio sintético no se lee de una columna: el Parquet solo guarda REAL o
UNAVAILABLE. La figura de precios cuenta la capa SYNTHETIC con la misma regla
que la ficha (UNAVAILABLE con GTIN), sin generar montos.
"""

from __future__ import annotations

from collections.abc import Callable

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure

NUTRIENTES_D1: tuple[str, ...] = (
    "sugars_100g",
    "salt_100g",
    "saturated-fat_100g",
    "fiber_100g",
    "proteins_100g",
)

ETIQUETA_NUTRIENTE: dict[str, str] = {
    "sugars_100g": "Azúcares",
    "salt_100g": "Sal",
    "saturated-fat_100g": "Grasa saturada",
    "fiber_100g": "Fibra",
    "proteins_100g": "Proteína",
}

ORDEN_CALIDAD: tuple[str, ...] = ("insuficiente", "baja", "media", "alta")

COLORES = ("#1F4E79", "#5B8FA8", "#C4A35A", "#8C4A3A", "#3E6B4F")


def catalogo(df: pd.DataFrame, *, dataset_id: str) -> dict[str, Figure]:
    """Construye las cinco figuras sobre el marco ya cargado."""
    _validar_columnas(df)
    return {nombre: funcion(df, dataset_id=dataset_id) for nombre, funcion in FIGURAS.items()}


def figura_calidad_informacion(df: pd.DataFrame, *, dataset_id: str) -> Figure:
    """Distribución de `data_quality_level` en el universo operativo.

    El indicador es DERIVED y no entra al score.
    """
    niveles = df["data_quality_level"].astype("string").str.strip().str.lower()
    desconocidos = sorted(set(niveles.dropna().unique()) - set(ORDEN_CALIDAD))
    if niveles.isna().any() or desconocidos:
        raise ValueError(f"Nivel de calidad no previsto: {desconocidos or ['nulo']}")
    conteo = niveles.value_counts().reindex(list(ORDEN_CALIDAD), fill_value=0)
    total = int(conteo.sum())
    figura, eje = _lienzo(f"Calidad de información · {dataset_id}", "EDA")
    sns.barplot(
        x=list(conteo.index),
        y=conteo.to_numpy(),
        hue=list(conteo.index),
        palette=list(COLORES[:4]),
        legend=False,
        ax=eje,
    )
    eje.set_xlabel("Nivel")
    eje.set_ylabel("Productos")
    for indice, valor in enumerate(conteo.to_numpy()):
        eje.text(indice, valor, f"{int(valor):,}".replace(",", " "), ha="center", va="bottom")
    eje.set_title(f"n = {_miles(total)} productos del universo operativo")
    return figura


def figura_universo_puntuable(df: pd.DataFrame, *, dataset_id: str) -> Figure:
    """Desglose del umbral A22: al menos 4 percentiles válidos y D2 calculable."""
    grupos = _grupos_puntuables(df)
    figura, eje = _lienzo(f"Universo puntuable · {dataset_id}", "EDA")
    sns.barplot(
        x=list(grupos.index),
        y=grupos.to_numpy(),
        hue=list(grupos.index),
        palette=list(COLORES[: len(grupos)]),
        legend=False,
        ax=eje,
    )
    eje.set_xlabel("")
    eje.set_ylabel("Productos")
    eje.tick_params(axis="x", rotation=15)
    for indice, valor in enumerate(grupos.to_numpy()):
        eje.text(indice, valor, _miles(int(valor)), ha="center", va="bottom")
    puntuables = int(grupos.iloc[0])
    eje.set_title(f"Puntuables: {_miles(puntuables)} de {_miles(len(df))} (A22)")
    return figura


def figura_precios(df: pd.DataFrame, *, dataset_id: str) -> Figure:
    """Precios REAL almacenados y capa SYNTHETIC emitida al responder.

    QQP permanece como coincidencia de texto revisada. No se grafican montos
    sintéticos: no son observaciones de mercado.
    """
    estado = df["price_status"].astype("string").str.strip().str.upper()
    fuente = df["price_source"].astype("string").str.strip()
    codigo = df["code"].map(_codigo_presente)
    real_open = int(((estado == "REAL") & (fuente == "open_prices")).sum())
    real_qqp = int(((estado == "REAL") & (fuente == "qqp_profeco")).sum())
    no_disponible = int((estado == "UNAVAILABLE").sum())
    sintetico = int(((estado == "UNAVAILABLE") & codigo).sum())
    sin_precio = int(((estado == "UNAVAILABLE") & ~codigo).sum())
    otros_reales = int((estado == "REAL").sum()) - real_open - real_qqp
    if otros_reales:
        raise ValueError(f"Hay {otros_reales} precios REAL con una fuente no prevista")

    almacenado = pd.Series(
        {
            "Open Prices\nexact_gtin": real_open,
            "QQP\ntext_reviewed": real_qqp,
            "Sin precio\nalmacenado": no_disponible,
        }
    )
    emitido = pd.Series(
        {
            "REAL": real_open + real_qqp,
            "SYNTHETIC\n(demostración)": sintetico,
            "UNAVAILABLE": sin_precio,
        }
    )
    figura, ejes = plt.subplots(1, 2, figsize=(11.2, 4.8), layout="constrained")
    _titulo(figura, f"Procedencia del precio · {dataset_id}", "EDA")
    _barras(ejes[0], almacenado, "En el Parquet")
    _barras(ejes[1], emitido, "En la respuesta de la API")
    figura.supxlabel(
        "SYNTHETIC se calcula al responder y no se escribe en el dataset. No es un precio de mercado.",
        fontsize=8,
    )
    return figura


def figura_grasa_saturada(df: pd.DataFrame, *, dataset_id: str) -> Figure:
    """Grasa saturada saneada y su percentil, la variable de signo negativo en D1."""
    columna = "saturated-fat_100g_saneado"
    percentil = "percentil_saturated-fat_100g"
    valor = pd.to_numeric(df[columna], errors="coerce")
    puntuable = _bandera(df["universo_puntuable"])
    largo = pd.DataFrame(
        {
            "g_por_100g": valor,
            "universo": puntuable.map({True: "Puntuable", False: "No puntuable"}),
        }
    ).dropna()
    techo = float(largo["g_por_100g"].quantile(0.99)) if not largo.empty else 0.0
    visible = largo[largo["g_por_100g"] <= techo]
    figura, ejes = plt.subplots(1, 2, figsize=(11.2, 4.8), layout="constrained")
    _titulo(figura, f"Grasa saturada · {dataset_id}", "Ingeniería de variables")
    sns.histplot(
        data=visible,
        x="g_por_100g",
        hue="universo",
        stat="density",
        common_norm=False,
        element="step",
        fill=True,
        alpha=0.35,
        palette=list(COLORES[:2]),
        ax=ejes[0],
    )
    ejes[0].set_xlabel("g / 100 g, valor saneado")
    ejes[0].set_ylabel("Densidad")
    ejes[0].set_title(f"Hasta el percentil 99 ({techo:.1f} g). n = {_miles(len(largo))}")
    pct = pd.to_numeric(df.loc[puntuable, percentil], errors="coerce").dropna()
    sns.histplot(x=pct, bins=20, color=COLORES[0], ax=ejes[1])
    ejes[1].set_xlabel("Percentil en la categoría de referencia")
    ejes[1].set_ylabel("Productos puntuables")
    ejes[1].set_title(f"Entra a D1 con signo −1. n = {_miles(len(pct))}")
    return figura


def figura_correlacion_d1(df: pd.DataFrame, *, dataset_id: str) -> Figure:
    """Correlación de Spearman de los cinco nutrientes que puntúan en D1.

    Se restringe al universo puntuable y a casos completos. Spearman se
    calcula como Pearson sobre rangos, sin añadir SciPy.
    """
    columnas = [f"{nutriente}_saneado" for nutriente in NUTRIENTES_D1]
    puntuable = _bandera(df["universo_puntuable"])
    matriz = df.loc[puntuable, columnas].apply(pd.to_numeric, errors="coerce").dropna()
    rangos = matriz.rank(method="average")
    correlacion = rangos.corr(method="pearson")
    correlacion.index = [ETIQUETA_NUTRIENTE[c.removesuffix("_saneado")] for c in correlacion.index]
    correlacion.columns = list(correlacion.index)
    figura, eje = _lienzo(f"Correlación de nutrientes de D1 · {dataset_id}", "Ingeniería de variables")
    sns.heatmap(
        correlacion,
        annot=True,
        fmt=".2f",
        vmin=-1,
        vmax=1,
        cmap="vlag",
        square=True,
        annot_kws={"size": 11},
        cbar_kws={"label": "Spearman"},
        ax=eje,
    )
    # Grasa saturada (fila 2) y proteína (fila 4): coeficiente 0,46 en este corte.
    for fila, columna in ((2, 4), (4, 2)):
        eje.add_patch(
            plt.Rectangle(
                (columna, fila),
                1,
                1,
                fill=False,
                edgecolor="#1F4E79",
                linewidth=2.2,
            )
        )
    eje.set_title(
        f"Universo puntuable, casos completos. n = {_miles(len(matriz))}. "
        "Grasa saturada y proteína: 0,46."
    )
    return figura


FIGURAS: dict[str, Callable[..., Figure]] = {
    "eda_calidad_informacion": figura_calidad_informacion,
    "eda_universo_puntuable": figura_universo_puntuable,
    "eda_precios_real_sintetico": figura_precios,
    "ingenieria_grasa_saturada": figura_grasa_saturada,
    "ingenieria_correlacion_d1": figura_correlacion_d1,
}


def _grupos_puntuables(df: pd.DataFrame) -> pd.Series:
    d2_ok = df["d2"].notna()
    percentiles = pd.to_numeric(df["n_percentiles_validos"], errors="coerce").fillna(0) >= 4
    puntuable = _bandera(df["universo_puntuable"])
    esperado = d2_ok & percentiles
    if not bool((puntuable == esperado).all()):
        raise ValueError("universo_puntuable no coincide con el umbral A22")
    return pd.Series(
        {
            "Puntuable": int(puntuable.sum()),
            "Solo sin D2": int((~puntuable & ~d2_ok & percentiles).sum()),
            "Solo <4 percentiles": int((~puntuable & d2_ok & ~percentiles).sum()),
            "Sin D2 y <4 percentiles": int((~puntuable & ~d2_ok & ~percentiles).sum()),
        }
    )


def _validar_columnas(df: pd.DataFrame) -> None:
    requeridas = {
        "code",
        "d2",
        "universo_puntuable",
        "n_percentiles_validos",
        "price_status",
        "price_source",
        "data_quality_level",
        "saturated-fat_100g_saneado",
        "percentil_saturated-fat_100g",
        *(f"{nutriente}_saneado" for nutriente in NUTRIENTES_D1),
    }
    faltan = sorted(requeridas - set(df.columns))
    if faltan:
        raise ValueError(f"Faltan columnas para las figuras: {faltan}")


def _bandera(serie: pd.Series) -> pd.Series:
    if serie.dtype == bool:
        return serie.fillna(False)
    texto = serie.astype("string").str.strip().str.lower()
    return texto.isin(("true", "1", "verdadero"))


def _codigo_presente(valor: object) -> bool:
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return False
    texto = str(valor).strip()
    return texto not in ("", "nan", "None", "<NA>")


def _lienzo(titulo: str, etapa: str) -> tuple[Figure, plt.Axes]:
    figura, eje = plt.subplots(figsize=(8.4, 4.8), layout="constrained")
    _titulo(figura, titulo, etapa)
    return figura, eje


def _titulo(figura: Figure, titulo: str, etapa: str) -> None:
    figura.suptitle(f"{etapa} · {titulo}", fontsize=13)


def _barras(eje: plt.Axes, serie: pd.Series, titulo: str) -> None:
    sns.barplot(
        x=list(serie.index),
        y=serie.to_numpy(),
        hue=list(serie.index),
        palette=list(COLORES[: len(serie)]),
        legend=False,
        ax=eje,
    )
    eje.set_xlabel("")
    eje.set_ylabel("Productos")
    eje.set_title(titulo)
    for indice, valor in enumerate(serie.to_numpy()):
        eje.text(indice, valor, _miles(int(valor)), ha="center", va="bottom")


def _miles(valor: int) -> str:
    return f"{valor:,}".replace(",", " ")
