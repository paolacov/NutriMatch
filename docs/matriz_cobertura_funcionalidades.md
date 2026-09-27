# Matriz de cobertura funcional — auditoría 2026-09-27

Solo lectura. Fuente: `datos/procesados/dataset_referencia_20260927.parquet`.  
Script: `scripts/auditar_cobertura_funcional.py`. CSV: `datos/procesados/matriz_cobertura_funcionalidades_20260927.csv`.

**No se modificó el Parquet** (sha256 `8e19c4b97bad38bc93a29981cbade9bed2616a7adcac7f9879b47cac0ee9713e`).  
No se generaron sintéticos. No se imputó. No se tocaron API, Angular ni fórmulas de ranking.

Los requisitos de cada fila salen del código actual (`filtrar_por_query`, `detalle_desde_fila`, `RankingService`, pantallas Angular). No se inventaron reglas.

---

## Validaciones obligatorias

| # | Comprobación | Resultado |
| --- | --- | --- |
| 1 | Filas | 16.851 |
| 2 | GTIN únicos | 16.851 |
| 3 | Duplicados | 0 |
| 4 | `universo_puntuable` | 5.864 |
| 5 | Precio REAL | 263 (242 Open Prices + 21 QQP) |
| 6 | Precio SYNTHETIC en Parquet | 0 |
| 7 | IMPUTED en Parquet | 0 |
| 8 | Columnas `d1` / `d3` / `cov` / `score_final` | no materializadas |
| 9–12 | Parquet / API / Angular / fórmulas | no modificados en este paso |

La API lee `dataset_referencia_20260927.parquet` (`Settings.referencia_filename`, recableado el 2026-09-27). El 20260926 queda como predecesor intacto. No se modificó el ranking.

---

## Umbrales de estado (objetivos)

Calculados sobre **% de los 16.851** que cumplen el requisito mínimo de esa fila.

| Estado | Umbral |
| --- | --- |
| **COMPLETA** | cobertura ≥ 80 % |
| **PARCIAL** | 40 % ≤ cobertura < 80 % |
| **LIMITADA** | 5 % ≤ cobertura < 40 % |
| **NO DISPONIBLE** | cobertura < 5 %, **o** la función no está implementada |

NULL no es 0. NULL no es «no cumple». Un cero nutricional o `additives_n = 0` es dato REAL.

Calidad: se reutilizan `data_quality_level` ya materializados (`alta` / `media` / `baja` / `insuficiente`). No hay una segunda lógica de calidad.

---

## Qué exige realmente el código

| Función | Dónde | Campos que usa de verdad |
| --- | --- | --- |
| Búsqueda | `GET /search` → `filtrar_por_query` | `code`; `product_name` **después** de que el catálogo lo pisa con `product_name_homologated`; `brand_original` o `brands`. **No** categoría. |
| Escaneo UI | `/buscar?scan=` | GTIN 8–14 dígitos → ficha. |
| Ficha | `detalle_desde_fila` | nombre homologado/`product_name`; marca; `main_category` / `_en` / `categoria_referencia`; 7 nutrientes (sin grasa saturada); ingredientes; `allergens` (no `traces`); `labels_tags`; `price` solo si `price_status=REAL`; `nova_group`; imagen. |
| Comparar | Angular `/comparar` | Hasta 3 fichas + `explain` (score, D1/D2/D3, alergia/dieta, 7 nutrientes, precio). **No hay algoritmo de ganador.** |
| Ranking | `POST /ranking` | D1 runtime sobre percentiles; `d2` persistido; D3 sobre `labels_tags` y el perfil; alergia (`allergens`+`traces`); dieta (`ingredients_analysis_tags`); `cov` → banda A32. |
| Alternativas | — | **No existe** módulo ni endpoint. |
| Alertas | `/alertas` sobre el carrito | Sellos `labels` que contienen `exceso`; estado de alergia/dieta de `explain`. |
| Personalización | perfil Angular + `UserProfile` | `allergen_tags`, `diet`, `valued_labels`, `priority_order`. Ana/Beto/Caro viven en `scripts/confirmar_ranking_v1.py`. |
| Precio | ficha / card / comparar | API solo envía REAL. Overlay SYNTHETIC en Angular **no** es cobertura. |
| Recetas | `/recetas` | Lista el carrito. Texto: «No hay motor de recetas». |

---

## Matriz

| Funcionalidad | Requisitos mínimos | Productos evaluables | % universo | Calidad (entre evaluables) | Estado | Limitación |
| --- | --- | ---: | ---: | --- | --- | --- |
| Búsqueda por GTIN | `code` | 16.851 | 100,0 | alta 36,2 · med 9,0 · baja 12,6 · insuf. 42,2 | **COMPLETA** | `contains` literal. |
| Búsqueda por nombre | `product_name_homologated` (API) | 15.172 | 90,0 | alta 39,5 · med 9,2 · baja 10,8 · insuf. 40,5 | **COMPLETA** | 1.679 no salen por texto. Ficha también acepta `product_name` crudo (unión 15.184). |
| Búsqueda por marca | `brand_original` / `brands` | 13.102 | 77,8 | alta 44,7 · med 9,9 · baja 11,5 · insuf. 33,8 | **PARCIAL** | 3.749 sin marca. |
| Búsqueda por categoría | no implementada | 0 | 0 | n/a | **NO DISPONIBLE** | Ni `categories_tags` ni `categoria_referencia` entran al filtro. |
| Ficha: se abre | `code` | 16.851 | 100,0 | (catálogo) | **COMPLETA** | Atributos pueden ser UNAVAILABLE. |
| Ficha: nombre | homologado o `product_name` | 15.184 | 90,1 | alta 39,5 · med 9,2 · baja 10,8 · insuf. 40,5 | **COMPLETA** | Sin placeholder inventado. |
| Ficha: marca | original o `brands` | 13.102 | 77,8 | alta 44,7 · med 9,9 · baja 11,5 · insuf. 33,8 | **PARCIAL** | Copy «Marca no disponible». |
| Ficha: categoría | `main_category` / `_en` / ref. A16 | 8.728 | 51,8 | alta 69,9 · med 14,5 · baja 13,8 · insuf. 1,7 | **PARCIAL** | |
| Ficha: ingredientes | texto o tags | 7.650 | 45,4 | alta 79,8 · med 16,3 · baja 3,9 · insuf. 0 | **PARCIAL** | NULL ≠ «sin ingredientes». |
| Ficha: ≥1 nutriente (7 de UI) | saneado/bruto/crudo | 12.315 | 73,1 | alta 48,8 · med 8,0 · baja 8,6 · insuf. 34,6 | **PARCIAL** | Grasa saturada puntúa D1 y **no** se lista en ficha. |
| Ficha: 7 nutrientes UI | los 7 con algún valor | 8.695 | 51,6 | alta 64,2 · med 8,7 · baja 6,8 · insuf. 20,3 | **PARCIAL** | 0 real = dato. |
| Ficha: NOVA | `nova_group` | 6.781 | 40,2 | alta 86,9 · med 12,2 · baja 0,9 · insuf. 0 | **PARCIAL** | |
| Aditivos (explain, no ficha) | `additives_n` | 7.650 | 45,4 | alta 79,8 · med 16,3 · baja 3,9 · insuf. 0 | **PARCIAL** | 0 = cero aditivos REAL. No está en `ProductDetail`. |
| Ficha: etiquetas | `labels_tags` | 4.266 | 25,3 | alta 65,0 · med 13,0 · baja 21,8 · insuf. 0,2 | **LIMITADA** | Sin labels ≠ sin sellos. |
| Ficha: alérgenos (campo) | `allergens` | 2.793 | 16,6 | alta 89,7 · med 8,3 · baja 2,0 · insuf. 0 | **LIMITADA** | `traces` no se pinta en ficha. |
| Ficha: precio REAL | `price_status=REAL` | 263 | 1,56 | alta 90,1 · med 4,6 · baja 1,9 · insuf. 3,4 | **NO DISPONIBLE** | Overlay UI no cuenta. |
| Ficha: imagen | URL OFF | 13.041 | 77,4 | alta 45,8 · med 10,8 · baja 14,3 · insuf. 29,1 | **PARCIAL** | |
| Comparación **completa** | 7 nut. UI + D1 + D2 | 5.457 | 32,4 | alta 98,7 · med 1,3 | **LIMITADA** | Cualquier par se abre; completa = contraste numérico D1/D2 + tabla. |
| Comparación **parcial** | ≥4 nut. o D1 o D2, no completa | 7.134 | 42,3 | alta 10,1 · med 17,6 · baja 15,2 · insuf. 57,1 | **PARCIAL** | «Sin dato» / — |
| Comparación **limitada** | resto | 4.260 | 25,3 | alta 0 · med 4,3 · baja 24,3 · insuf. 71,3 | **LIMITADA** | Solo identidad. |
| Ranking ejecutable (banda A32) | perfil + fila | 16.851 | 100,0 | (catálogo) | **COMPLETA** | Todos caen en una banda. |
| `universo_puntuable` | ≥4/8 percentiles + D2 | 5.864 | 34,8 | **alta 98,5 · media 1,5 · baja 0 · insuf. 0** | **LIMITADA** | 5.864 idénticos a A22/A44. |
| D1 calculable | ≥1 de 5 percentiles con signo | 7.040 | 41,8 | alta 85,1 · med 7,7 · baja 7,2 | **PARCIAL** | Runtime. |
| D2 calculable | `d2` no nulo | 6.781 | 40,2 | alta 86,9 · med 12,2 · baja 0,9 | **PARCIAL** | Persistido. |
| Alternativas (módulo) | no existe | 0 | 0 | n/a | **NO DISPONIBLE** | No hay «más proteína / menos azúcar» como feature. |
| Capacidad D1: más proteína | `percentil_proteins_100g` | 6.949 | 41,2 | derived | **PARCIAL** | Signo +1 dentro de D1. |
| Capacidad D1: menos azúcar | `percentil_sugars_100g` | 6.743 | 40,0 | derived | **PARCIAL** | Signo −1. |
| Capacidad D1: menos sal | `percentil_salt_100g` | 6.734 | 40,0 | derived | **LIMITADA** | 39,96 % (umbral 40). |
| Capacidad D1: menos sat. | `percentil_saturated-fat_100g` | 6.690 | 39,7 | derived | **LIMITADA** | `fat_100g` no puntúa (A27). |
| Capacidad D1: más fibra | `percentil_fiber_100g` | 6.549 | 38,9 | derived | **LIMITADA** | |
| Alerta sello **determinable** | `labels_tags` presente | 4.266 | 25,3 | alta 65,0 · med 13,0 · baja 21,8 | **LIMITADA** | 1.204 con `exceso`; 3.062 labels sin exceso (determinado: sin sello); **12.585 no se puede determinar**. |
| Alerta sello `exceso` presente | tag contiene `exceso` | 1.204 | 7,1 | alta 53,7 · med 14,0 · baja 31,8 | **LIMITADA** | Informa, no puntúa (A9). |
| Alerta alergia **determinable** (ej. `en:milk`) | `allergens` o `traces` | 3.489 | 20,7 | alta 88,1 · med 9,5 · baja 2,4 | **LIMITADA** | apto 1.661 · no_apto 1.828 · **no_verificable 13.362**. |
| Alerta dieta vegana **determinable** | tag `en:vegan` o `en:non-vegan` | 3.905 | 23,2 | alta 87,1 · med 10,4 · baja 2,4 | **LIMITADA** | compatible 917 · incompatible 2.988 · **no_verificable 12.946**. 7.716 tienen `ingredients_analysis_tags`; el resto es «tal vez» / desconocido → no verificable. |
| Personalización (Ana/Beto/Caro) | perfil + catálogo | 16.851 | 100,0 | (catálogo) | **COMPLETA** | La función corre. El **orden** útil es menor (abajo). |
| Precio REAL | `price_status=REAL` | 263 | 1,56 | alta 90,1 | **NO DISPONIBLE** | Comparar por precio REAL es residual. |
| Recetas / LLM | no hay motor | 0 | 0 | n/a | **NO DISPONIBLE** | Fuera del MVP de datos. |

---

## 1. Búsqueda

Funciona. El anaquel es localizable por **GTIN al 100 %**. Por nombre, ~90 % (API usa el homologado). Por marca, 77,8 %. **Por categoría no se puede buscar**: no es un hueco de datos, es ausencia de código.

Cuello de botella de datos: 1.679 sin nombre, 3.749 sin marca. No justifica sintetizar nombres (A37).

---

## 2. Ficha

Se abre para los 16.851. Lo que «se ve bien» depende del atributo (tabla). Procedencia:

| Atributo | REAL / DERIVED / UNAVAILABLE (aprox.) |
| --- | --- |
| `code` | REAL 16.851 |
| Nombre | DERIVED/REAL 15.184 · UNAVAILABLE 1.667 |
| Marca | REAL/DERIVED 13.102 · UNAVAILABLE 3.749 |
| Categoría mostrada | REAL/DERIVED 8.728 · UNAVAILABLE 8.123 |
| Ingredientes | REAL 7.650 · UNAVAILABLE 9.201 |
| ≥1 nutriente UI | REAL/DERIVED 12.315 · UNAVAILABLE 4.536 |
| NOVA | REAL 6.781 · UNAVAILABLE 10.070 |
| Etiquetas | REAL 4.266 · UNAVAILABLE 12.585 |
| Alérgenos (campo ficha) | REAL 2.793 · UNAVAILABLE 14.058 |
| Precio | REAL 263 · UNAVAILABLE 16.588 · SYNTHETIC parquet 0 |

Hallazgo de implementación (no se corrige aquí): la ficha **omite** `saturated-fat_100g` y `additives_n`, que sí usa el motor.

---

## 3. Comparación

Reglas cuantitativas (no opinión):

- **Completa** (5.457, 32,4 %): 7 nutrientes de UI + D1 + D2.
- **Parcial** (7.134, 42,3 %): al menos 4 nutrientes o D1 o D2, sin llegar a completa.
- **Limitada** (4.260, 25,3 %): el resto.

La pantalla acepta cualquier `code`. El contraste visual de score solo es informativo si hay D1/D2. Precio en comparar: solo 263 REAL; el overlay SYNTHETIC no se auditó como cobertura.

---

## 4. Ranking personalizado

Fórmulas **no cambiadas**. Reproducción sobre 20260927:

| Perfil | ranking | no_verificable | insuficiente (`cov<0,5`) | excluido |
| --- | ---: | ---: | ---: | ---: |
| Ana | 7.334 | 0 | **9.517** | 0 |
| Beto | 7.219 | 0 | 9.632 | 0 |
| Caro | 5.877 | 0 | **10.974** | 0 |

9.517 y 10.974 coinciden con A31/A44. Ana/Beto/Caro **no declaran alergia ni dieta**, por eso excluido/no_verificable = 0.

`universo_puntuable` = **5.864**, mismos códigos en magnitud que el baseline. Calidad **dentro** de esos 5.864:

| `data_quality_level` | n | % de 5.864 |
| --- | ---: | ---: |
| alta | 5.775 | 98,5 |
| media | 89 | 1,5 |
| baja | 0 | 0 |
| insuficiente | 0 | 0 |

El universo puntuable es, casi por definición, de calidad alta: el score de calidad reutiliza percentiles, categoría y NOVA.

D3: si el perfil no pide etiquetas (Caro), D3 es NULL para el 100 % y el score se renormaliza (A26). Si pide `en:organic`, D3 solo tiene dato cuando `labels_tags` existe (4.266).

---

## 5. Alternativas

No hay feature. La única vía existente es **D1** (percentil en categoría, signo fijo). Cobertura ~39–41 % según nutriente. «Menos grasa total» **no** es una regla del motor (A27). Inventar un ranking de alternativas sería código nuevo; no se hizo.

---

## 6. Alertas (MVP)

Tres reglas reales. En todas se separa **no cumple** vs **no se puede determinar**.

### Sellos NOM-051 (`exceso` en `labels_tags`)

| Caso | n | % de 16.851 | Interpretación |
| --- | ---: | ---: | --- |
| Labels presentes y hay `exceso` | 1.204 | 7,1 | Alerta de sello (hecho REAL) |
| Labels presentes y no hay `exceso` | 3.062 | 18,2 | Determinado: sin sello en el registro |
| `labels_tags` NULL | 12.585 | 74,7 | **No se puede determinar** |

Sobre `universo_puntuable` (5.864): los sellos siguen siendo un subconjunto (la mayoría del puntuable tiene calidad alta, no necesariamente labels).

### Alergia (ejemplo `en:milk`, tag de la UI)

| Estado | n | Significado |
| --- | ---: | --- |
| no_apto | 1.828 | Cumple el fail-safe: leche en `allergens` o `traces` |
| apto | 1.661 | Hay dato y no coincide |
| no_verificable | 13.362 | **No se puede determinar** (ambos campos vacíos) |

Sin alergia en el perfil, el código marca `apto` para todos: no hay nada que filtrar. Eso no es evidencia de «sin alérgenos».

### Dieta vegana

| Estado | n | Significado |
| --- | ---: | --- |
| compatible | 917 | Tag `en:vegan` |
| incompatible | 2.988 | Tag `en:non-vegan` |
| no_verificable | 12.946 | **No se puede determinar** (incluye «maybe» / unknown) |

NULL de análisis ≠ «no vegano».

---

## 7. Personalización

Campos del perfil (ya implementados): `allergen_tags`, `diet` (`vegano`/`vegetariano`), `valued_labels`, `priority_order` (permutación D1/D2/D3).

Campos del producto: percentiles D1, `d2`, `labels_tags`, `allergens`, `traces`, `ingredients_analysis_tags`.

Ana/Beto/Caro: tres diccionarios de evaluación, no una tabla de usuarios. No se crearon usuarios nuevos.

Productos «fuera» del ranking útil = banda insuficiente o no_verificable/excluido cuando el perfil declara alergia/dieta. Con Ana (sin alergia): 9.517 insuficientes (56,5 %). Si se declara una alergia, ~79 % del catálogo pasa a no_verificable (A15): es el dato, no un bug.

---

## 8. Precio

| | n | % |
| --- | ---: | ---: |
| REAL Open Prices | 242 | 1,44 |
| REAL QQP (`price_source=qqp_profeco`) | 21 | 0,12 |
| UNAVAILABLE | 16.588 | 98,44 |
| SYNTHETIC en Parquet | 0 | 0 |

`price_source` = proveedor. `price_status` = procedencia. El overlay Angular ($12–$180, hash de GTIN) **no** entra en estos conteos.

Comparar o filtrar por precio con evidencia REAL está en estado **NO DISPONIBLE** (< 5 %). El ranking v1 no usa precio (A5).

---

## 9. Recetas / LLM

Opcional/futuro. `/recetas` no calcula combinaciones. Sin clave LLM, no hay planner/narrate en producción. No se implementó nada aquí.

---

## Respuestas al objetivo

1. **Ya funcionan con datos reales:** búsqueda GTIN/nombre, apertura de ficha, ranking que asigna bandas, personalización de pesos, comparación visual (con huecos), alertas **cuando el dato existe**.
2. **Porcentajes:** tabla de arriba. Útiles para ranking comparativo: 34,8 % puntuable; 43,5 % (Ana) / 34,9 % (Caro) en banda ranking.
3. **Parciales por falta de dato:** marca, categoría, ingredientes, NOVA, D1/D2, comparación completa, sellos, alergia, dieta.
4. **Cuellos de botella:** `labels_tags` (74,7 % vacío), `allergens`+`traces` (79,3 % ambos vacíos), `ingredients_analysis_tags` determinables (solo 23,2 %), precio (98,4 % UNAVAILABLE), nombre/marca en menor medida.
5. **No vale sintetizar:** nutrientes, NOVA, ingredientes, alérgenos, sellos, dieta, nombres. Cambiarían score o seguridad (A2/A36).
6. **Sintético demo, solo después y fuera del Parquet analítico:** precio de vitrina (ya está en UI, no en datos); quizá 3 perfiles JSON versionados (Ana/Beto/Caro ya existen en código).
7. **Deben quedarse limitadas por transparencia:** precio de mercado, «apto para alérgicos» sin dato, «sin sellos» cuando no hay `labels_tags`, alternativas de nutriente como feature aparte.
8. **Antes de ML/LLM:** recablear API a 20260927 (paso aparte); decidir si el overlay de precio se documenta solo como demo; no entrenar nada sobre 263 precios sesgados.

---

## Datos faltantes que podrían requerir una capa sintética/demo

No se genera nada aquí. Solo si la **ausencia impide demostrar** la pantalla, no porque el % de NULL sea alto.

| Dato que falta | Productos afectados | Función que limita | ¿Justificable sintético académico? | ¿Fuera del Parquet analítico? | Cómo separarlo |
| --- | ---: | --- | --- | --- | --- |
| Precio REAL | 16.588 | Comparar/mostrar precio en anaquel | **Sí, solo demo de UI** (ya hay overlay). No como precio de mercado. | **Sí** | `price_status=SYNTHETIC` en cliente o Parquet `*_demo`; nunca pisar REAL. |
| `labels_tags` | 12.585 | Sellos + D3 | **No** | — | NULL = no determinable. |
| `allergens`/`traces` | 13.362 | Alerta alergia verificable | **No** (seguridad) | — | Banda no_verificable. |
| Tags de dieta determinantes | 12.946 | Alerta/filtro vegano | **No** | — | no_verificable. |
| CORE8 / NOVA | ~10.000 | Ranking D1/D2 | **No** | — | `cov`, banda insuficiente. |
| Nombre | 1.679 | Búsqueda por texto | **No** (A37) | — | Buscar por GTIN. |
| Categoría en el buscador | n/a (código) | Búsqueda por categoría | No es un dato: falta **implementación** | — | Paso de producto, no de sintéticos. |
| Usuarios / interacciones | 0 tablas | ML futuro | Solo fixtures SYNTHETIC si hay experimento | Sí | Nunca como comportamiento observado. |
| Recetas LLM | 0 | `/recetas` | Solo si se abre A13 | Sí | `llm_generated`, no catálogo. |

---

## Pendientes explícitos (no hechos)

- Apuntar la API a `dataset_referencia_20260927.parquet`.
- Cualquier capa SYNTHETIC de precio en datos.
- ML / LLM.
- Motor de alternativas.
- Búsqueda por categoría.
