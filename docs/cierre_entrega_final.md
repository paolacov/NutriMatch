# Cierre de la entrega

Auditoría del 3 de octubre de 2026. El PDF no se modificó.

## Estado general

## Documento

COMPLETO

`docs/documento_final/main.pdf` sigue siendo el documento oficial. No se reescribió, no se agregaron secciones y no se cambiaron cifras.

Cada punto de la rúbrica tiene evidencia en ese PDF:

| Punto | Dónde está | Lectura |
| --- | --- | --- |
| Resumen e introducción | Secciones 1 y 2 | El problema y el alcance no médico quedan en la primera página |
| Planteamiento | Sección 3 | Información fragmentada y faltante distinto de cero |
| Estrategia | Sección 4, con usuarios, necesidad, accionables, propuesta y usabilidad | No está escondida en la arquitectura |
| Descripción de datos | Sección 5 | Fuentes, candados, calidad, precio y límites |
| Análisis exploratorio | Sección 6 | Pregunta, hallazgo y decisión, con las figuras del cuaderno |
| Procesamiento | Secciones 7 y 8 | Limpieza, sin imputación, percentiles, universo y bandas |
| Modelación | Sección 9 | Motor determinista. La negativa al aprendizaje supervisado está escrita |
| Resolución | Sección 11 | De la ficha al carrito y a las alertas |
| Conclusiones | Sección 14 | Atadas a los resultados del corte |
| Referencias APA | Bibliografía | Seis fuentes verificadas. No se inventaron otras |
| Escritura y presentación | 19 páginas, índice, tablas y figuras con pie | Legible. No incluye capturas de la interfaz |
| Accionables | Sección 4.3 y sección 11 | Elegir, sustituir, leer la banda, revisar alertas |
| Usuarios y necesidad | Secciones 4.1 y 4.2 | Persona que compra empacados. No hay usuarias observadas |
| Usabilidad | Secciones 4.5 y 11 | La pantalla usa nutrición, procesamiento y etiquetas |

La usabilidad visible no está en el PDF. Queda para el video y la demo. Eso no obliga a reabrir el documento.

## Notebook

COMPLETO

`notebooks/06_notebook_maestro_nutrimatch.ipynb` ya se ejecutó en local, sobre el Parquet oficial, y comprueba las cifras del PDF. No usa una ruta de Mac en el código. La salida guardada sí imprime la ruta de aquella corrida; al ejecutarlo de nuevo, esa línea cambia.

No se modificó el cuaderno en esta fase.

## Colab

PENDIENTE

Las instrucciones están en `docs/reproducibilidad_colab_final.md`. No hay remoto de Git, así que no existe un `git clone` real. La vía escrita es un zip con el Parquet, la instalación `pip install -e .` y el directorio de trabajo en la raíz antes de ejecutar todo. Esa pasada todavía no se hizo dentro de Google Colab.

## Presentación

PENDIENTE

La estructura de doce diapositivas está en `docs/presentacion_final/estructura_presentacion.md`. Las diapositivas todavía no están armadas.

## Video

PENDIENTE

El guion de cinco minutos está en `docs/video_final/guion_video.md`. El MP4 no existe.

## Demo

PENDIENTE

El guion está en `docs/demo_final/guion_demo.md`, con un código medido en el catálogo oficial. La pasada en el navegador de esta fase no se hizo.

# Riesgos de evaluación

## P0 — bloqueadores

Ninguno sobre el PDF ni sobre el motor. No hay una cifra del documento que contradiga el corte oficial, ni un fallo que obligue a cambiar el sistema para poder entregarlo.

## P1 — importantes

- Google Colab no se ha ejecutado. Hasta esa pasada, la reproducibilidad en Colab está escrita y no demostrada.
- El repositorio no tiene remoto. Clonar no es un paso disponible. El zip de la guía sí lo es.
- La celda que busca la raíz solo mira el directorio de trabajo y su padre. En Colab hay que situar ese directorio antes de «Ejecutar todo». El cambio mínimo sería subir por los directorios padres. No se aplicó.
- La rúbrica nombra modelación supervisada o no supervisada. El riesgo frente al comité está explicado abajo. No se entrenó nada para cubrir el nombre.
- La presentación, el video y la demo todavía no están producidos. Los guiones ya fijan la historia y las cifras.

## P2 — mejoras

- El PDF no trae capturas de Angular. El video las sustituye. No vale la pena reabrir el LaTeX por eso.
- El carrito titula «Plato del Buen Comer». El PDF cita la NOM-043 como Plato del Bien Comer. Los grupos que se muestran son los de la norma. No se cambió la interfaz.
- El diccionario de datos todavía describe el percentil en escala 0–1. El cuaderno y el PDF usan 0–100.
- Un comentario de código conserva la correlación histórica −0,4747. El PDF ya la marca como histórica.
- La salida guardada del cuaderno muestra una ruta local. Se actualiza al reejecutar.

# Modelación

## Riesgo de evaluación: modelación

La rúbrica pide modelación supervisada y/o no supervisada.

Hoy existe un motor determinista de compatibilidad y ranking por preferencias y características del producto. Recibe el catálogo y un perfil. Aplica alergia y dieta. Calcula nutrición, procesamiento y etiquetas. Pondera con 0,50, 0,33 y 0,17. Normaliza por el peso de las dimensiones que sí tienen dato. Si la cobertura queda bajo 0,5, el resultado es nulo. Asigna una sola banda y devuelve el orden, las alternativas y la explicación.

Ese motor es válido para el problema porque la decisión es una comparación reproducible con datos publicados y preferencias declaradas, no la predicción de una compra.

NutriMatch no utiliza aprendizaje supervisado porque el catálogo no contiene un target observado que permita entrenar y evaluar de manera científicamente válida un modelo de recomendación. No hay compras, clics, favoritos ni conversiones. El resultado, las tres dimensiones y las bandas los calcula el propio sistema. Entrenar contra ellos sería circular.

Tampoco hay análisis no supervisado. Un agrupamiento, un PCA o una segmentación hechos solo para que el trabajo mencione la técnica no responderían una pregunta del proyecto y no son el mecanismo que ordena la compra. Incorporarlos ahora sería artificial.

Antes de agregar un análisis no supervisado habría que fijar cuatro cosas: la pregunta que responde, las variables observadas que usaría, el criterio para leer los grupos y la separación explícita entre esa salida y el orden del motor. Esta fase no lo implementó.

# Cifras oficiales

Los documentos de esta fase usan el corte `datos/procesados/dataset_referencia_20261002.parquet`.

El PDF ya cerrado cita 13 093 productos, 273 columnas, 5 864 puntuables (44,79 %), la calidad 6 102 / 1 511 / 1 274 / 4 206, 259 precios reales y 12 834 sin precio, Spearman −0,475683 con n = 6 035, y los promedios 59,68, 54,80, 50,87, 49,00 y 41,57. El caso de oro que no pasa sigue siendo el contrato del nombre de `5060323907641`.

La presentación, el video y la demo repiten esas cifras. El ejemplo en vivo añade dos códigos de ese mismo archivo, calculados con el perfil por defecto de la interfaz. No sustituyen las cifras del PDF.

El 16 851 y el Spearman −0,4747 siguen siendo contexto del 19 de septiembre de 2026.

# Próximo paso recomendado

Ejecutar el notebook maestro en Google Colab con `docs/reproducibilidad_colab_final.md`, antes de grabar el video. Es la única comprobación que todavía puede fallar y que el guion no puede sustituir.
