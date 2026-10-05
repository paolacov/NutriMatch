# Guion del video final

Duración máxima: 5 minutos. Formato MP4. La estudiante está en cámara durante todo el video, también cuando se comparte la pantalla. Las diapositivas son pocas. La mayor parte del tiempo es la interfaz, con una sola historia de compra.

No se recorren menús vacíos. No se presenta el motor como modelo de machine learning. No se dice que un alimento sea saludable.

Antes de grabar, la aplicación ya está abierta y el catálogo ya cargó. Perfil por defecto: nutrición primero, luego procesamiento, luego etiquetas; sin dieta y sin alérgenos. Si el navegador guarda otro perfil, hay que rehacer la entrada y pulsar «Ahora no» en alergias y dieta. Los números de abajo solo valen para ese perfil.

Producto de partida, existente en el corte oficial: `7501003390288`, aceitunas sin hueso, Búfalo. Primera alternativa que muestra la ficha: `8410344401326`, aceitunas negras sin hueso, La Cibeles.

## 0:00–0:30. Problema y usuario

Cámara y una diapositiva con la frase del problema.

Decir: «Quien compra un alimento empacado tiene que comparar nutrientes, procesamiento, etiquetas y alérgenos, y muchos registros no traen todo eso. Tratar el dato que falta como si fuera cero cambia el orden. NutriMatch es para esa persona: declara qué le importa y el sistema prepara la comparación. No diagnostica.»

## 0:30–1:00. Qué es NutriMatch

Misma toma, o un esquema de cuatro pasos.

Decir: «El catálogo se vuelve comparable, un motor determinista arma el orden y la interfaz lo muestra en español: nutrición, procesamiento y etiquetas. La persona no tiene que conocer los nombres internos. Ella elige, sustituye o descarta.»

## 1:00–1:40. Datos y cobertura

Diapositiva con 13 093 productos y la figura de disponibilidad.

Decir: «El corte es del 2 de octubre de 2026: 13 093 productos de Open Food Facts, más precios de Open Prices y de PROFECO cuando existen. Solo 5 864 se pueden comparar en nutrición y procesamiento antes de conocer a la persona. El precio real está en 259 productos. No imputé lo que falta.»

## 1:40–2:20. Motor

Diapositiva corta, sin fórmula.

Decir: «La nutrición se compara dentro de la categoría. El procesamiento usa el grupo NOVA y los aditivos. Las etiquetas miden lo que la persona dijo que valora. Si falta una dimensión, no se convierte en cero. Si no hay suficiente información, el producto no entra al orden. No hay aprendizaje supervisado: no existen compras ni clics que sirvan de target, y usar el propio puntaje como etiqueta sería circular.»

## 2:20–4:10. Demostración

Pantalla de la aplicación, con la estudiante visible en un recuadro.

1. En el inicio, escribir el código `7501003390288` y abrir la ficha. No buscar por el texto «aceitunas»: hay más de un producto.
2. Señalar el nombre, la marca Búfalo, el resultado 40,05, la categoría olives y el precio de 30 pesos. Ese precio es real, de Open Prices.
3. Señalar los sellos de exceso de grasas saturadas y de sodio. Decir que informan y no entran al puntaje.
4. Abrir «Explorar alternativas». La primera es aceitunas negras sin hueso, La Cibeles, con 76,48. Decir que es la primera de la misma categoría de referencia y que también tiene nutrición y procesamiento calculados. Su grupo NOVA es 1; el de Búfalo es 3.
5. Decir el precio que aparece en esa ficha: 74 pesos, marcado como precio de demostración. No es un precio de anaquel y no ordenó la lista.
6. Agregar La Cibeles al carrito. Volver y agregar también Búfalo, para que las alertas tengan los dos.
7. Abrir alertas. Búfalo debe mostrar los dos sellos de exceso. La Cibeles no trae sellos de exceso. Cerrar diciendo que la persona puede quedarse con la alternativa o conservar el producto inicial.

No abrir recomendaciones de todo el catálogo, recetas ni historial.

## 4:10–4:40. Evaluación

Volver a una diapositiva.

Decir: «De trece casos revisados a mano, doce pasan. Uno difiere en el campo del nombre, no en el puntaje. Frente a Nutri-Score, la correlación es −0,475683 en 6 035 productos: Nutri-Score no es la verdad del sistema. El orden cambia si cambia la prioridad, y repetir la misma corrida da el mismo resultado.»

## 4:40–5:00. Cierre

Cámara.

Decir: «NutriMatch no decide qué alimento es saludable. Con la información que sí está publicada, permite comparar productos parecidos, ver por qué y revisar las alertas del carrito.»
