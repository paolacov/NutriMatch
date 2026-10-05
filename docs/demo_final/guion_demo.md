# Guion de la demostración en vivo

Unos cinco minutos. Una sola historia. El reloj empieza cuando la ficha ya puede abrirse: la API y la interfaz están corriendo, y el catálogo ya hizo su primera carga.

```bash
make api
make ui
```

La interfaz queda en `http://127.0.0.1:4200`.

## Respuestas que la demo tiene que dejar

1. **Problema.** La información del empacado está fragmentada y a menudo incompleta. Un faltante no es un cero.
2. **Quién.** Una persona que compra alimentos empacados y puede declarar prioridades. En la demo no hay dieta ni alérgenos, para no mezclar la historia con la banda de no verificable.
3. **Qué hace NutriMatch.** Convierte esos atributos en un orden explicable y en alternativas de la misma categoría.
4. **Motor.** Motor determinista. Nutrición, procesamiento y etiquetas. La dimensión ausente no vale cero. Cobertura bajo 0,5: el producto no entra al orden.
5. **Qué ve la persona.** Nombre, resultado, banda, sellos, precio con su procedencia y alternativas. Los nombres en pantalla son nutrición, procesamiento y etiquetas.
6. **Qué decisión toma.** Quedarse con el producto, sustituirlo por la alternativa o descartarlo. Las alertas muestran los sellos; no diagnostican.
7. **Cómo sabemos que funciona.** Doce de trece casos, correlación −0,475683 con n = 6 035, y el mismo orden si se repite la corrida. Se dice en una frase, no se recalcula en vivo.

## Perfil que tiene que estar activo

El perfil por defecto de la interfaz:

- primera prioridad: nutrición;
- segunda: procesamiento;
- tercera: etiquetas;
- alimentación: sin preferencia;
- alérgenos: ninguno.

En la entrada, no tocar el orden de las tarjetas. En el paso de evitar, pulsar «Ahora no». Si el navegador ya tiene otro perfil guardado, los números de abajo no aplican. Conviene usar una ventana de incógnito.

Este perfil no es una usuaria observada. Los resultados salen del motor sobre `dataset_referencia_20261002.parquet`.

## Ruta

### 1. Buscar (30 segundos)

En el inicio, en «Escribe el código», capturar `7501003390288` y abrir la ficha.

No escribir «aceitunas» ni «Búfalo». Esas búsquedas devuelven varios productos.

### 2. Leer la ficha (1 minuto)

Lo que debe verse:

| Dato | Valor en este perfil |
| --- | --- |
| Código | `7501003390288` |
| Nombre | Aceitunas sin hueso |
| Marca | Búfalo |
| Categoría en pantalla | olives |
| Resultado | 40,05 |
| Precio | $30.00, real, Open Prices |
| Sellos | exceso de grasas saturadas y exceso de sodio |
| Grupo NOVA | 3 |

Decir: «Este precio sí es una observación. Los sellos se muestran y no suman ni restan al resultado.»

### 3. Alternativa (1 minuto 30 segundos)

Pulsar «Explorar alternativas». La primera fila debe ser:

| Dato | Valor |
| --- | --- |
| Código | `8410344401326` |
| Nombre | Aceitunas Negras Sin Hueso |
| Marca | La Cibeles |
| Resultado | 76,48 |
| Nutrición y procesamiento | ambos calculados |
| Grupo NOVA | 1 |
| Sellos de exceso | ninguno registrado |
| Precio | $74.00, con la leyenda «Precio de demostración» |

Elegir esa primera alternativa. Decir: «Es el mismo grupo de referencia. El 74 no es un precio de tienda: el archivo no tiene precio para este código, y ese entero no entra al orden.»

No elegir una fila de más abajo. La primera es la que tiene las dos dimensiones y el resultado más alto.

### 4. Carrito y alertas (1 minuto)

Agregar La Cibeles. Volver a Búfalo y agregarlo también. Abrir el carrito y después alertas.

En alertas, Búfalo queda con los dos sellos de exceso. La Cibeles no. El encabezado del carrito dice «Plato del Buen Comer». Si preguntan por la norma, la cita del PDF es la NOM-043, Plato del Bien Comer. Los grupos que se leen en pantalla son verduras y frutas, cereales, y leguminosas y alimentos de origen animal.

### 5. Cierre (30 segundos)

«Puedo quedarme con Búfalo, pasar a La Cibeles o sacar los dos. El sistema no me dice que unas aceitunas sean saludables. Me muestra compatibilidad, sellos y qué dato falta.»

Una frase de evaluación: doce de trece casos y Spearman −0,475683 en 6 035 productos. Nutri-Score no es el target.

## Qué no hacer

- No activar dieta vegana ni un alérgeno en esta pasada. Casi todo el catálogo cae en no verificable y la historia se rompe.
- No abrir «Para ti» ni el orden de todo el catálogo. Esa vista no es la comparación entre parecidos.
- No llamar al 74 un precio real.
- No decir que La Cibeles es más saludable. Decir que es más compatible con este perfil y que su procesamiento sí está calculado.
- No improvisar otro código si la ficha tarda. Esperar la carga. El código de respaldo, si la red local fallara, es el mismo: volver a escribir `7501003390288`.

## Por qué este caso y no otro

Se buscó en el catálogo oficial, con el perfil por defecto, un producto con precio real, sellos de exceso y las dos primeras dimensiones, cuya primera alternativa también tuviera esas dos dimensiones, un resultado más alto y menos sellos de exceso. Este par cumple eso. Otros pares de la misma búsqueda ponen primero un producto con procesamiento ausente y cobertura justo en 0,5. Esos sirven para explicar el faltante, no para la demo de cinco minutos.
