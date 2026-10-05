# Mapa de rúbrica del documento final

Auditoría del 3 de octubre de 2026, antes de cerrar el PDF. La fuente reproducible de las cifras actuales es `notebooks/06_notebook_maestro_nutrimatch.ipynb`, ejecutado sobre `datos/procesados/dataset_referencia_20261002.parquet` (13 093 filas, 273 columnas, SHA-256 `a621d471a2f47aa09ba481408d95a7a808fe84bd2fa7205c56fa050e1c66045b`).

El corte del 19 de septiembre de 2026 (16 851 productos, universo naive 5 856, Spearman −0,4747) solo puede citarse como histórico.

No se modificó el dataset, el motor, FastAPI ni Angular.

| Criterio | Evidencia disponible | Archivo o fuente | Sección propuesta | Figura o tabla | Estado | Faltante |
| --- | --- | --- | --- | --- | --- | --- |
| Introducción y resumen | Problema de compra, alcance no médico, motor determinista y cifras del corte | Notebook maestro, secciones 0 y 12 | 1 y 2 | Ninguna | COMPLETO | — |
| Planteamiento del problema | Información fragmentada, comparación entre productos parecidos, datos incompletos | Notebook, sección 0; `AGENTS.md` | 3 | Ninguna | COMPLETO | — |
| Estrategia | Perfil declarado, ranking, alternativas, carrito y alertas | `frontend/src/app/app.routes.ts`, `docs/mapa_proyecto.md`, notebook sección 12 | 4 | Tabla de accionables | COMPLETO | No hay estudio con usuarias observadas. El documento no inventa personas |
| Usuarios | Persona que compra empacados y declara prioridades, dieta y alergias | Onboarding en `frontend/src/app/pages/onboarding.page.ts` | 4.1 y 4.2 | Ninguna | COMPLETO | No hay segmentos demográficos medidos |
| Accionables | Elegir, sustituir dentro de la categoría, leer la banda, revisar alertas y el plato | Ficha, `cart-alternatives.ts`, `alerts.page.ts`, `cart.page.ts` | 4.3 y 11 | Ninguna | COMPLETO | — |
| Usabilidad | Etiquetas en español (nutrición, procesamiento, etiquetas). El cálculo permanece en el motor | `frontend/src/app/shared/format.ts`, ficha de producto | 4.5 y 11 | Ninguna | PARCIAL | El PDF no incluye capturas de la interfaz. La usabilidad visible queda para el demo y el video |
| Fuentes de datos | Open Food Facts, Open Prices, PROFECO. Citas ya redactadas en el repositorio | `docs/ATTRIBUTION.md` | 5.1 | Tabla de fuentes | COMPLETO | El texto legal de las licencias no está copiado en el repositorio |
| Integración | Tres candados de 16 851 a 13 093, documentados en el metadato del archivo oficial | `dataset_referencia_20261002_metadata.json` | 5.2 | Tabla de candados | COMPLETO | El export CSV no viaja en Git. Reconstruir desde cero no es el camino del notebook |
| Estructura y calidad | 273 columnas, 0 duplicados, calidad 6 102 / 1 511 / 1 274 / 4 206, precios 259 y 12 834 | Notebook, secciones 2, 3.3 y 3.8 | 5.3 y 5.4 | Figuras de calidad y precio; tablas | COMPLETO | — |
| EDA con decisión | Cobertura, faltantes, categorías, cinco nutrientes, NOVA, etiquetas, precio | Notebook, sección 3 y 4 | 6 | Seis figuras extraídas de la ejecución del notebook | COMPLETO | — |
| Limpieza y faltantes | NULL distinto de cero; 55 correcciones de sal; 1 sal fuera de rango sin corrección; sin imputación | Notebook, sección 5; `engine/sanitize.py` | 7 | Tabla de reglas | COMPLETO | — |
| Ingeniería de variables | Percentiles, categoría de referencia, D2, D3 en consulta, universo puntuable, calidad y precio fuera del score | Notebook, sección 6; diccionario | 8 | Tabla de variables | COMPLETO | El diccionario aún describe el percentil como escala 0–1. El notebook mide escala 0–100. No se corrigió el diccionario en esta fase |
| Modelación supervisada o no supervisada | No hay modelo entrenado. La justificación está en el notebook y en `docs/decisiones.md` | Notebook, secciones 8 y 11 | 9 | Tabla del motor | REQUIERE DECISIÓN | No existe un algoritmo no supervisado. Agregarlo solo para la rúbrica sería artificial. Queda como P1 |
| Funcionamiento del motor | D1, D2, D3, pesos 3/6, 2/6 y 1/6, cobertura 0,5, cuatro bandas | `engine/` y notebook, sección 8 | 9 | Tabla de bandas del perfil de ejemplo | COMPLETO | El perfil de ejemplo no es una usuaria observada |
| Evaluación | 5 864 puntuables; 12 de 13 casos de oro; Spearman −0,475683 (n = 6 035); sensibilidad 113/114 y, aparte, 665/640; determinismo | Notebook, secciones 9 y 10 | 10 | Figura D1 por letra; figura de scores; tablas | COMPLETO | El caso `5060323907641` falla por contrato de nombre, no por el score. No se ocultó |
| Resolución | Catálogo, señales, ranking, alternativas de la misma categoría, carrito y alertas | Servicios de ranking y rutas de Angular | 11 | Ninguna captura | PARCIAL | Falta la secuencia visual de la interfaz |
| Arquitectura | Parquet, motor, FastAPI, Angular, SQLite regenerable, lenguaje opcional | `docs/mapa_proyecto.md` | 12 | Ninguna | COMPLETO | — |
| Capa de lenguaje | El motor decide. `POST /ai/ask` narra hechos ya calculados. Sin clave hay plantillas | `src/nutrimatch/ai/` | 12 | Ninguna | COMPLETO | `AiPanel` no está montado en una ruta. El lenguaje visible está en el carrito y en recetas |
| Conclusiones | Ocho respuestas del notebook, con cifras del corte actual | Notebook, sección 12 | 14 | Ninguna | COMPLETO | — |
| Referencias APA | Open Food Facts, Open Prices, PROFECO, NOVA, Nutri-Score y NOM-043, con ficha verificada | `docs/ATTRIBUTION.md` y fuentes primarias comprobadas el 3 de octubre de 2026 | 15 | Bibliografía | PARCIAL | No se añadió un ensayo general de sistemas de recomendación: no había una cita verificada que el proyecto ya usara, y no se inventó |
| Reproducibilidad en Colab | El notebook localiza la raíz sin rutas de Mac y documenta `pip install -e .` | Notebook, secciones 1 y 13 | 13 | Ninguna | PARCIAL | Esa corrida se hizo en el entorno local. No se repitió dentro de Google Colab |
| Presentación del PDF | Estructura LaTeX con figuras del notebook, tablas y bibliografía. Compilado el 3 de octubre de 2026 | `docs/documento_final/main.pdf` | Todo el PDF | Nueve figuras y cuatro tablas | COMPLETO | Regenerar el PDF exige Tectonic 0.17 o un TeX con BibTeX. El comando está en `docs/documento_final/COMPILAR.md` |

## Hueco de modelación

NutriMatch no utiliza aprendizaje supervisado porque el catálogo no contiene un target observado que permita entrenar y evaluar de manera científicamente válida un modelo de recomendación. No hay compras, clics, favoritos ni conversiones. Usar el score del propio motor como etiqueta sería circular.

Tampoco hay un análisis no supervisado. Un clúster de productos no es hoy el mecanismo que ordena la compra. Implementarlo solo para nombrar la rúbrica cambiaría el relato del sistema. El documento explica el motor determinista y deja esta decisión marcada. No se entrenó ningún modelo en esta fase.

## Prioridad de lo que sigue fuera del PDF

| Prioridad | Qué falta | Por qué no se inventó |
| --- | --- | --- |
| P1 | Decidir con el comité si hace falta una técnica no supervisada de apoyo, sin convertirla en el ranking | No existe ese análisis en el repositorio |
| P1 | Una pasada real del notebook en Google Colab | El procedimiento está escrito; la ejecución de esta entrega fue local |
| P1 | Citas adicionales de evaluación de recomendadores, solo si se verifican autor, año y URL o DOI | No se fabricaron referencias |
| P2 | Capturas de la interfaz dentro del PDF | El flujo está en el código. Las capturas pertenecen al demo |
| P2 | Ajustar el diccionario del percentil y el comentario histórico de Spearman | Son documentos distintos. Esta fase no los reescribió |
