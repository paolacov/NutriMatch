# Capa de lenguaje

La explicación en lenguaje natural vive en `src/nutrimatch/ai/` y se consulta con `POST /ai/ask`. El motor sigue siendo la única fuente de los números. El texto narra hechos ya calculados.

## Papel de cada pieza

```
catálogo + perfil
  → operación determinista (búsqueda, ficha, ranking, carrito o explicación)
  → hechos calculados
  → narración
  → critic determinista
  → texto final
```

- El planner elige la operación. No calcula subpuntajes.
- El critic comprueba que el texto esté respaldado por esos hechos. No es un modelo juzgando a otro modelo.
- Si el critic no acepta el texto, o si no hay `OPENAI_API_KEY`, la respuesta sale de plantillas deterministas.
- El identificador de la persona se anonimiza antes de una llamada externa.

## Qué puede ver el texto

| Cubeta | Contenido |
| --- | --- |
| Observado | Código, nombre, marca, cantidad, categoría, NOVA, sellos, alérgenos, ingredientes, nutrientes y precio real |
| Calculado | Resultado, banda, cobertura, subpuntajes, pesos, percentiles y estados de alergia y dieta |
| No disponible | Ausencias explícitas. Un hueco no se narra como cero |
| Demostración | Si el precio llega como `SYNTHETIC`, el texto lo llama precio de demostración |

El perfil que viaja son las alergias, la dieta, las etiquetas valoradas y el orden de prioridades.

## Qué permanece fuera del texto

Las fórmulas internas más allá de los subpuntajes ya calculados, y cualquier cifra que el motor no haya producido. El ranking no depende del párrafo: el orden ya está cerrado cuando empieza la narración.

`src/nutrimatch/agents/` describe los tres roles. La implementación que ejecuta la API es `nutrimatch.ai`.
