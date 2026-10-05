# Estructura de la presentación final

Doce diapositivas para defender NutriMatch, no para leer el PDF. Las cifras son las del corte `dataset_referencia_20261002` (2 de octubre de 2026). El motor se nombra como motor determinista de compatibilidad y ranking. No se llama modelo de machine learning.

Las figuras ya están en `docs/documento_final/figuras/`. No hace falta recalcularlas.

## 1. Portada

- **Objetivo.** Identificar el trabajo y el alcance.
- **Mensaje.** NutriMatch apoya la decisión de compra de alimentos empacados. No diagnostica ni declara que un alimento sea saludable para todos.
- **Evidencia.** Portada del PDF.
- **Figura.** Ninguna.
- **Decir.** «Soy Paola Castañeda. NutriMatch ordena alternativas a partir de lo que la persona declara y de la información que el producto sí tiene.»

## 2. Problema

- **Objetivo.** Dejar claro qué se resuelve.
- **Mensaje.** La información de un empacado está fragmentada: nutrientes, procesamiento, etiquetas, alérgenos y, a veces, precio. Comparar «a ojo» mezcla lo que el producto declara con lo que el registro no trae.
- **Evidencia.** Sección 3 del PDF.
- **Figura.** Ninguna. Una frase basta.
- **Decir.** «Un dato ausente no es un cero. Si lo trato como cero, el orden premia el silencio del registro.»

## 3. Usuario y necesidad

- **Objetivo.** Cubrir usuarios, necesidad y la decisión que la persona toma.
- **Mensaje.** Quien lo usa compra alimentos empacados y puede ordenar tres prioridades, declarar dieta vegana o vegetariana y marcar alérgenos. No hay una muestra de usuarias observadas. El perfil de ejemplo del cuaderno no es una persona real.
- **Evidencia.** Sección 4 del PDF.
- **Figura.** Ninguna.
- **Decir.** «La persona elige, sustituye dentro de la misma categoría o descarta. El sistema prepara la comparación.»

## 4. Datos

- **Objetivo.** Nombrar fuentes, tamaño y el problema de cobertura.
- **Mensaje.** Open Food Facts, Open Prices y PROFECO. 13 093 productos, 273 columnas, 0 códigos duplicados. Calidad: 6 102 alta, 1 511 media, 1 274 baja, 4 206 insuficiente. Precio real: 259. Sin precio: 12 834. Imputados: 0. Sintéticos en el archivo: 0.
- **Evidencia.** Tablas 1 y 2 del PDF. El 16 851 es el filtro de México antes de los candados, no el universo evaluado.
- **Figura.** `figuras/calidad.png` y `figuras/precios.png`.
- **Decir.** «El precio de demostración que a veces muestra la ficha no está en el Parquet y no entra al orden.»

## 5. Exploración

- **Objetivo.** Mostrar que el análisis cambió decisiones.
- **Mensaje.** Solo 5 864 productos (44,79 %) tienen procesamiento y al menos cuatro percentiles. El grupo NOVA 4 concentra a la mayoría de quienes tienen grupo. Las etiquetas, los alérgenos y el precio cubren mucho menos.
- **Evidencia.** Sección 6 del PDF. Catálogo, puntuable y recomendado son tres conjuntos distintos.
- **Figura.** `figuras/disponibilidad.png` y `figuras/universo.png`. Si hace falta una tercera, `figuras/nova.png`.
- **Decir.** «Por eso no imputé nutrientes, alérgenos, etiquetas, NOVA ni precio.»

## 6. Solución

- **Objetivo.** Mostrar el recorrido, no la lista de carpetas.
- **Mensaje.** Datos observados, variables comparables, motor, interfaz. Parquet es la fuente del catálogo. SQLite solo guarda uso regenerable. FastAPI entrega el resultado. Angular lo muestra y no vuelve a calcular las tres dimensiones.
- **Evidencia.** Sección 12 del PDF.
- **Figura.** Un esquema de cuatro cajas: catálogo, procesamiento, motor, interfaz. Sin colores extra.
- **Decir.** «La misma función puntúa en el cuaderno y en la aplicación.»

## 7. Motor de decisión

- **Objetivo.** Explicar el motor sin llamarlo aprendizaje automático.
- **Mensaje.** Nutrición: azúcar, sal y grasa saturada bajan; fibra y proteína suben; se compara dentro de la categoría. Procesamiento: banda NOVA afinada con aditivos. Etiquetas: proporción de las preferencias declaradas que el producto presenta. Pesos 0,50, 0,33 y 0,17. Si falta una dimensión, no se vuelve cero. Si la cobertura queda bajo 0,5, el resultado es nulo. Bandas: excluido, no verificable, información insuficiente, ranking.
- **Evidencia.** Secciones 8 y 9 del PDF.
- **Figura.** Ninguna fórmula larga. Cuatro bandas en una lista.
- **Decir.** «NutriMatch no utiliza aprendizaje supervisado porque el catálogo no contiene un target observado que permita entrenar y evaluar de manera científicamente válida un modelo de recomendación.»

## 8. Evaluación

- **Objetivo.** Separar lo que se midió de lo que no existe.
- **Mensaje.** Trece casos revisados, doce pasan. El caso `5060323907641` difiere en el nombre, no en el puntaje. Spearman −0,475683, n = 6 035. Promedios de la dimensión nutricional: A 59,68, B 54,80, C 50,87, D 49,00, E 41,57. Nutri-Score no es la meta ni la verdad. Con el perfil de ejemplo del cuaderno, el orden pasa de 113 a 114 productos al cambiar la prioridad. La regla experimental de 665 y 640 no es esa banda. Dos pasadas iguales dan el mismo orden.
- **Evidencia.** Sección 10 del PDF.
- **Figura.** `figuras/d1_nutriscore.png`.
- **Decir.** «La correlación es negativa porque aquí un valor alto es mejor y en Nutri-Score un valor alto es peor.»

## 9. Interfaz

- **Objetivo.** Mostrar que la persona no necesita los nombres D1, D2 y D3.
- **Mensaje.** En pantalla se llaman nutrición, procesamiento y etiquetas. El recorrido de la decisión es búsqueda, ficha, alternativas de la misma categoría, carrito y alertas. La vista que ordena el catálogo completo no sustituye esa comparación.
- **Evidencia.** Sección 11 del PDF. La demostración en vivo recorre esa ruta.
- **Figura.** No hace falta una captura en la diapositiva si la demo va justo después. Si se usa una, debe ser de la aplicación actual, no de un prototipo anterior.
- **Decir.** «Los sellos informan. No diagnostican y no entran al puntaje.»

## 10. Ejemplo de decisión

- **Objetivo.** Una historia concreta, medida en el catálogo oficial, con el perfil por defecto de la interfaz: nutrición, procesamiento y etiquetas, sin dieta y sin alérgenos.
- **Mensaje.** Se busca el código `7501003390288`, aceitunas sin hueso, marca Búfalo. Entra al orden con 40,05. Tiene precio real de 30 pesos, grupo NOVA 3 y sellos de exceso de grasas saturadas y de sodio. La primera alternativa de la misma categoría es `8410344401326`, aceitunas negras sin hueso, La Cibeles, con 76,48, grupo NOVA 1 y sin sellos de exceso. Su precio en pantalla es de demostración: 74 pesos. No es un precio observado y no ordena la lista.
- **Evidencia.** Calculado con el motor y el perfil por defecto sobre el Parquet oficial. No es un usuario observado.
- **Figura.** Ninguna gráfica. El código de barras y los dos resultados bastan.
- **Decir.** «No digo que unas aceitunas sean saludables. Digo que, con este perfil, la segunda es más compatible y trae procesamiento calculado. La categoría en pantalla se lee olives: es el grupo de referencia, no un consejo de sustitución médica.»

## 11. Limitaciones

- **Objetivo.** Anticipar las preguntas del comité.
- **Mensaje.** Faltan compras, clics y favoritos, así que no hay precisión contra un desenlace. No hay análisis no supervisado: agregarlo solo para el nombre de la rúbrica sería artificial. El precio real es escaso. Muchos registros no alcanzan para afirmar alergia o dieta. El contraste con Nutri-Score no es validación clínica.
- **Evidencia.** Secciones 9 y 13 del PDF.
- **Figura.** Ninguna.
- **Decir.** «Si el comité pide un agrupamiento, primero hay que definir la pregunta y dejar claro que esa salida no alimenta el orden. Hoy no existe.»

## 12. Conclusiones

- **Objetivo.** Cerrar con la decisión que el sistema permite.
- **Mensaje.** NutriMatch convierte atributos heterogéneos en un orden explicable. La evidencia es el corte de 13 093 productos, el universo de 5 864, los doce casos, la correlación de −0,475683 y un orden que cambia cuando cambia la prioridad. La persona compara, sustituye o descarta.
- **Evidencia.** Sección 14 del PDF.
- **Figura.** Ninguna.
- **Decir.** «El sistema no decide por ella qué alimento es saludable.»
