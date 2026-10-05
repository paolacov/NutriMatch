# Speech de la presentación

Duración: unos 9 minutos. Sigue las 12 láminas de `presentacion_nutrimatch.pdf`. Las cifras son las del corte del 2 de octubre de 2026.

No se llama al motor modelo de machine learning. No se dice que un alimento sea saludable. Los pesos no se presentan como parámetros aprendidos. El caso de las aceitunas no es el perfil de los 113 productos.

## 1. Portada

Soy Paola Castañeda. Este es NutriMatch, el trabajo del Diplomado en Ciencia de Datos.

Es un sistema de apoyo a la decisión para comprar alimentos empacados. Parte de un catálogo heterogéneo y lo convierte en una comparación comprensible. No diagnostica.

## 2. El problema

Elegir un empacado obliga a juntar nutrición, procesamiento, etiquetas, alérgenos, precio y, muchas veces, huecos. La figura muestra esa cobertura desigual.

Un dato ausente no es un cero. Si lo trato como cero, el orden premia el silencio del registro. Si lo conservo como ausente, esa señal no entra. Si la cobertura baja de 0,5, no hay puntaje.

## 3. De los datos a la decisión

Quien lo usa compra alimentos empacados. Puede ordenar tres prioridades y, si quiere, declarar dieta y alérgenos. No hay usuarias observadas.

El recorrido es persona, prioridades, catálogo, preparación, motor, alternativas, carrito y alertas. En pantalla las dimensiones se llaman nutrición, procesamiento y etiquetas. El sistema apoya la decisión. No determina si un alimento es saludable.

## 4. Los datos

Hay tres fuentes. Open Food Facts aporta la ficha. Open Prices aporta el precio cuando el código coincide: 239. PROFECO solo entra si la coincidencia por texto quedó revisada: 20.

El filtro de México tenía 16 851 productos. Ese número es el punto de partida, no el universo que evalúo. Tres candados lo dejan en 13 093: salen 3 no alimentarios, 3 737 por integridad y 18 por el nombre. El archivo tiene 273 columnas y cero códigos duplicados.

De precio real hay 259. Sin precio, 12 834. En el archivo hay cero imputados y cero sintéticos. Si la ficha dice precio de demostración, ese monto no ordena.

## 5. EDA

La exploración cambió el diseño. Estas barras no son una cadena. Son coberturas del mismo catálogo. El universo puntuable es la intersección: procesamiento disponible y al menos cuatro de ocho percentiles. Son 5 864 productos, el 44,79 por ciento.

Eso no es un producto recomendado. Es el conjunto con información suficiente para aplicar esas dimensiones, antes de conocer a la persona.

## 6. Ingeniería

La nutrición compara cinco nutrientes dentro de la categoría. Azúcares, sal y grasa saturada bajan. Fibra y proteína suben. Las distribuciones están pegadas a cero, así que la comparación es el percentil, no los gramos crudos.

El procesamiento usa el grupo NOVA y los aditivos. Sin grupo, esa dimensión no se calcula. Las preferencias miden qué proporción de las etiquetas valoradas presenta el producto. Si no hay etiquetas que comparar, queda vacía.

No imputé nutrientes, alérgenos, etiquetas, NOVA ni precio.

## 7. El motor

El motor es determinista. La persona ordena tres prioridades: la primera pesa la mitad, la segunda un tercio y la tercera un sexto. En la lámina el ejemplo es nutrición, preferencias y procesamiento. Esos pesos se declaran. No se aprenden.

El resultado es el promedio de las dimensiones que sí tienen dato. Un faltante no entra como cero. Si la cobertura queda bajo 0,5, no hay puntaje. Cada producto cae en una sola banda: excluido, no verificable, información insuficiente o ranking.

Nutri-Score, los sellos y el precio se muestran. No entran al puntaje.

## 8. Modelación

NutriMatch no utiliza aprendizaje supervisado porque el catálogo no contiene un target observado que permita entrenar y evaluar de manera científicamente válida un modelo de recomendación.

No hay compras, clics, favoritos ni conversiones. Usar el puntaje, o las tres dimensiones, como etiqueta sería circular.

## 9. Resultados

De trece casos revisados a mano, doce pasan. El que no pasa difiere en el nombre, no en el puntaje. Frente a Nutri-Score, Spearman es −0,475683, con 6 035 productos. El signo es negativo porque aquí un valor alto es mejor y en Nutri-Score un valor alto es peor. El promedio baja de la A, 59,68, a la E, 41,57. Nutri-Score no es la verdad del sistema.

## 10. Arquitectura

La misma función puntúa en el cuaderno y en la aplicación. El Parquet es el catálogo. El engine decide. FastAPI entrega el resultado. Angular lo muestra y no vuelve a calcular las tres dimensiones. La pantalla redondea; el valor medido está en el caso.

El recorrido en pantalla es buscar, evaluar la ficha, sustituir dentro de la misma categoría y decidir en el carrito. El carrito de la captura es el que ya estaba guardado en el navegador. No es el caso de las aceitunas. La pantalla titula Plato del Buen Comer. Los sellos informan y no diagnostican.

## 11. El caso

Este caso usa el perfil por defecto: nutrición, procesamiento y etiquetas, sin dieta y sin alérgenos. No es el perfil de los 113 productos.

Se busca el código 7501003390288. Aceitunas sin hueso, Búfalo. Resultado medido 40,05. La pantalla muestra 40. Precio real de 30 pesos. NOVA 3 y sellos de exceso.

La primera alternativa es 8410344401326, La Cibeles. Resultado medido 76,48. La pantalla muestra 76,5. NOVA 1. Los 74 pesos son precio de demostración y no ordenaron la lista.

Con este perfil, la alternativa obtiene una mayor puntuación. No significa que sea más saludable.

## 12. Cierre

Trece mil noventa y tres productos integrados. Cinco mil ochocientos sesenta y cuatro en el universo puntuable. Un motor reproducible conectado a una interfaz.

NutriMatch transforma un catálogo heterogéneo en información para decidir. No decide por la persona qué alimento es saludable.
