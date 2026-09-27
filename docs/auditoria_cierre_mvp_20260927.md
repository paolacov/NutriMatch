# Auditoría y cierre funcional del MVP — 2026-09-27

Catálogo: `datos/procesados/dataset_referencia_20260927.parquet`  
(sha256 `8e19c4b97bad38bc93a29981cbade9bed2616a7adcac7f9879b47cac0ee9713e`).  
Pruebas: `tests/test_cierre_mvp.py` + regresión existente. Suite completa: **247 PASS / 0 FAIL**.

No se modificó el Parquet. No se cambiaron fórmulas de D1/D2/D3/`cov`/`score_final`.  
No se imputó. No se generaron sintéticos. No se entrenó ML. No se integró LLM.

---

## 1. Objetivo

Determinar si el MVP funciona de extremo a extremo y corregir **solo bugs de implementación** (clase A). Las limitaciones de Open Food Facts se documentan (clase B). El comportamiento ya especificado se conserva (clase C), incluido `00000140` (A26/A32/A44).

---

## 2. Arquitectura validada

```
Usuario (Angular, frontend/)
  → GET /search | GET /products/{code} | POST /ranking | POST /ranking/explain
  → FastAPI (nutrimatch.api)
  → Catalog.from_referencia()  → dataset_referencia_20260927.parquet
  → RankingService             → D1 / D3 / cov / score_final en runtime
                                 D2 persistido en el Parquet
```

- Única UI: Angular. Streamlit no está en el flujo (retirado el 2026-09-27; AGENTS A14 solo lo menciona como antecedente).
- Perfil, carrito y comparación viven en el cliente (`ProfileStore`, `CartStore`, `CompareStore`).
- Ana / Beto / Caro **no** son una tabla de usuarios ni un selector de la UI. Son perfiles de evaluación (`scripts/confirmar_ranking_v1.py`) que la API acepta como `UserProfile`. La personalización del MVP es el panel de perfil (alergias, dieta, etiquetas valoradas, orden 3/2/1).
- `data_quality_score` / `data_quality_level` / `data_quality_detalle` están en el Parquet y los consume el catálogo interno; **no** forman parte de `ProductDetail`. Angular no los pide. No es un quiebre de contrato.

---

## 3. Funcionalidades auditadas

| # | Función | API | Angular | Servicio / reglas | Fuente | Estado |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Búsqueda | `GET /search` | `search.page.ts` | `filtrar_por_query`: `code` + `product_name` (homologado) + marca; casefold; sin categoría | Parquet 20260927 | **OK** |
| 2 | Ficha | `GET /products/{code}` | `product.page.ts` | `detalle_desde_fila`; abre todo GTIN | idem | **OK** (copy de faltantes corregido) |
| 3 | Personalización | cuerpo `UserProfile` en ranking/explain | `profile-panel.ts`, `profile.store.ts` | A25 pesos 0,50/0,33/0,17 | localStorage + API | **OK** (sin tabla de usuarios) |
| 4 | Ranking | `POST /ranking` | `recommendations.page.ts` | A26/A32/A44; bandas exclusivas | runtime + `d2` | **OK** (fórmulas intactas) |
| 5 | Explicación | `POST /ranking/explain` | ficha / comparar / alertas | `ProductExplanation`: score, cov, D1–D3, `available` | runtime | **OK** |
| 6 | Alternativas | — | — | no existe módulo | — | **fuera de alcance** |
| 7 | Alertas | `explain` sobre el carrito | `alerts.page.ts` | sellos `exceso`; alergia/dieta de 3 estados (A15) | labels + allergens/traces + dieta | **OK** (copy NULL corregido) |
| 8 | Comparación | `GET /products` + `explain` | `compare.page.ts` | hasta 3 fichas; sin ganador | mismas fichas | **OK** (NULL ≠ 0 g) |
| 9 | Precio REAL | campo `price` de la ficha | `format.ts`, overlay en `product.repository.ts` | API solo envía REAL; overlay SYNTHETIC es demo | 263 REAL | **OK** (limitación de datos) |
| 10 | Faltantes | `UNAVAILABLE` / `available: false` / bandas | ficha, comparar, carrito, alertas | A2: NULL + bandera, nunca 0 | OFF | **OK** (copy alineado) |

---

## 4. Pruebas realizadas

| Caso | Código / perfil | Resultado |
| --- | --- | --- |
| 1. Completo + precio REAL | `0074323081411` Cajeta, QQP | nombre, ingredientes, `en:milk`, precio REAL, score |
| 2. Completo + sin precio | `0000103227240` (puntuable) | `price=NULL`, `UNAVAILABLE`, score calculable, D3 NULL |
| 3. No puntuable | `00000140` | `universo_puntuable=False` |
| 4. Score fuera de universo | `00000140` + Ana | D1 NULL, D2 presente, score ≈ 41,67, cov ≥ 0,5 (A26, **conservado**) |
| 5. Sin nombre | `00000285` | `name.value=NULL`, `UNAVAILABLE` |
| 6. Sin nutrición | `00000285` | 7 nutrientes UI en NULL, status `UNAVAILABLE` (no 0) |
| 7. Sin ingredientes | `00000285` | lista vacía |
| 8. Sin alérgenos | `00000285` + leche | `allergy_status=no_verificable` |
| 9. Sin labels | Cajeta + Ana | `labels=[]`, D3 NULL / no disponible |
| 10. D3 NULL | Caro sobre Pop-Tarts; Ana sobre `0000103227240` | D3 no disponible; score no se rompe |
| 11. cov insuficiente | `00000285` + Ana | score NULL, cov < 0,5, banda `informacion_insuficiente` |
| 12. Inexistente | `no-existe-xyz` | HTTP 404 en ficha y explain |
| 13. GTIN inválido | `12`, `abc`, `!!!` | HTTP 404 |
| 14. Búsqueda vacía | `zzzxxxyyynutrimatch_no_hit_999` | `[]` |

Además: cobertura GTIN 16.851 / 16.851; nombre homologado 15.172 / 16.851; mayúsculas/espacios en «Cajeta»; literal `"NAN"` (`7501058623201`); Ana 7.334 / Caro 5.877; Beto no rompe; alergia apto / no_apto / no_verificable; dieta vegana compatible / incompatible / no_verificable.

---

## 5. Errores encontrados

Clasificación pedida: **A** bug de implementación · **B** limitación de datos · **C** comportamiento diseñado.

| Hallazgo | Clase | Decisión |
| --- | --- | --- |
| Ficha convertía el nombre literal `"NAN"` a NULL (`_texto` trataba la cadena `nan` como sentinel B13) | **A** | Corregido |
| Alertas: «Sin sellos de advertencia ni alérgenos declarados» cuando ambos campos están vacíos | **A** | Corregido |
| Ficha: «Ninguno en el registro» / «Sin dato o no declarados» afirmaba ausencia | **A** | Corregido |
| Copy de precio UNAVAILABLE («Sin precio verificado») no coincidía con «Precio no disponible» | **A** (copy) | Corregido |
| Comparar / explicación / carrito: NULL mostrado como «Sin dato» (equivalente, se unificó a «Información no disponible») | **A** (copy) | Corregido |
| `00000140` tiene score sin ser `universo_puntuable` | **C** | Conservado (A26) |
| Overlay SYNTHETIC de precio en Angular cuando la API manda UNAVAILABLE | **C** | Conservado; no entra al ranking ni al Parquet |
| 1.679 productos sin nombre homologado; 1.588 sin precio REAL; alérgenos/sellos/dieta incompletos | **B** | Documentado |
| Búsqueda por categoría no implementada | **C** / fuera de alcance | No se añadió |
| Alternativas («más proteína», etc.) no existen | **C** / fuera de alcance | No se implementó |
| Ficha no lista grasa saturada ni `traces` (sí los usa el motor: D1 y alergia) | **B** / hueco de UI ya existente | No se añadió como feature nueva |
| Ana/Beto/Caro no aparecen como presets en el panel | **C** | El panel envía el perfil vivo; los tres se validaron por API |

---

## 6. Correcciones realizadas

1. **`_texto_nombre` en `detalle_desde_fila`**: el nombre literal `NAN` se muestra; el float NaN de pandas sigue siendo NULL.
2. **Alertas**: si no hay `labels` ni `allergens`, el texto dice que **no se puede determinar**. Si hay etiquetas pero no sellos `exceso`, no se afirma «sin alérgenos».
3. **Ficha**: alérgenos/sellos vacíos → «no disponibles / no se puede determinar», no «sin / ninguno».
4. **Precio UNAVAILABLE** (cuando el overlay no aplica): «Precio no disponible». Nunca `$0`.
5. **Missingness en comparar, ficha (tablas de explicación) y carrito**: «Información no disponible».

---

## 7. Casos límite

Los 14 casos de la sección 4 terminan en comportamiento controlado (200 con NULL/banderas, 404, o lista vacía). El motor no inventa nombre, precio, alérgeno, sello ni score cuando `cov < 0,5`.

---

## 8. Limitaciones reales del dataset

No son bugs. Provienen de OFF / del cruce de precio, no del MVP.

- Nombre buscable: 15.172 / 16.851 (90,0 %). 1.679 no salen por texto.
- Un producto se llama literalmente `NAN` (`7501058623201`). Se conserva.
- `universo_puntuable`: 5.864 (34,8 %). El resto es consultable (A19).
- Precio REAL: 263 / 16.851 (1,56 %). El resto es `NULL` + `UNAVAILABLE`.
- Comparación «completa» (7 nutrientes UI + D1 + D2): 32,4 % (auditoría de cobertura previa).
- Alergia determinable (p. ej. leche): minoría; la banda dominante es `no_verificable`.
- Dieta vegana determinable: 3.905 productos (auditoría previa).
- Sellos NOM-051: solo si `labels_tags` trae `exceso-*`.
- Calidad materializada: 7.114 `insuficiente`, 2.123 `baja` (indicadores DERIVED; no imputan).

---

## 9. Funcionalidades fuera de alcance

- Módulo de alternativas.
- Búsqueda por categoría.
- Tabla de usuarios / más perfiles además del panel.
- ML supervisado, embeddings, targets sintéticos.
- LLM (planner / critic / narrate).
- Imputación de nutrientes, alérgenos, NOVA, precio o nombres.
- Ampliar el overlay SYNTHETIC de precio.
- JWT, Docker, recetas con motor.

---

## 10. Estado final del MVP

El MVP está **funcionalmente cerrado** según el criterio de esta auditoría:

búsqueda, ficha, personalización, ranking, explicación, alertas de tres estados, comparación con missingness visible, precio REAL sin falsear `$0`, errores HTTP controlados, contrato API ↔ Angular alineado (`score`, `cov`, `d1`/`d2`/`d3`, `price`, `price_status`, `price_source`), casos límite con salida definida.

No se exige cobertura completa del catálogo.

---

## 11. Pendientes posteriores al MVP

- Revisión humana independiente de QQP (A41) si se quiere más precio de referencia.
- Recuperación de nombres por API OFF a escala (A39: hit 7,5 %, no se escaló).
- Mostrar grasa saturada y `traces` en ficha si se reabre el contrato de UI.
- Exponer `data_quality_*` en la ficha si se quiere transparencia de calidad en pantalla.
- Capa LLM opcional (A13) y recetas, cuando se pidan.
- ML solo si aparece un target observado (ver `docs/auditoria_preparacion_ml_20260927.md`).

---

## Tabla de cierre

| Funcionalidad | Estado | Evidencia/prueba | Limitación |
| --- | --- | --- | --- |
| Búsqueda GTIN | Cerrada | `test_cobertura_busqueda_gtin_y_nombre`, `test_busqueda_gtin_exacto` | `contains` literal, no checksum GS1 |
| Búsqueda nombre | Cerrada | case/espacios; `NAN` literal; 15.172/16.851 | 1.679 sin nombre homologado; no hay búsqueda por categoría |
| Ficha | Cerrada | casos 1–9, 12–13; copy de faltantes | Atributos pueden ser UNAVAILABLE; sin grasa saturada/`traces` en UI |
| Personalización | Cerrada | Ana/Beto/Caro por API; panel local | No hay selector de personas ni tabla de usuarios |
| Ranking | Cerrada | Ana 7.334 / Caro 5.877; `00000140` ≈ 41,67 | 34,8 % universo puntuable; cov < 0,5 → sin score |
| Explicación | Cerrada | `dimensions.*.available`; D3 NULL ≠ 0 | Lo que falta se marca, no se inventa |
| Alertas | Cerrada | tres estados alergia/dieta; copy NULL | Sin dato de alérgenos/sellos → no determinable |
| Comparación | Cerrada | NULL → «Información no disponible» | 32,4 % comparación completa |
| Precio real | Cerrada | 263 REAL; UNAVAILABLE nunca 0 | 1,56 %; overlay Angular es DEMO/SYNTHETIC |

---

## Fuera de alcance (confirmado)

| Tema | ¿Se hizo? |
| --- | --- |
| ML | NO |
| LLM | NO |
| Nuevos datos sintéticos | NO |
| Imputación | NO |
| Nuevas funcionalidades | NO |
| Cambio de ranking | NO |
| Cambio del Parquet | NO |
