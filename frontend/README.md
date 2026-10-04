# NutriMatch — interfaz Angular

Interfaz del sistema. Habla con FastAPI para el catálogo, la búsqueda, la ficha, el ranking, el resumen del carrito, el historial y la capa de lenguaje. El perfil, el carrito y la comparación se guardan en el navegador.

```bash
# En una terminal
make api

# En otra
make ui
```

Abre `http://127.0.0.1:4200`. El proxy de `proxy.conf.json` reenvía `/meta`, `/search`, `/catalog`, `/ranking`, `/products`, `/cart`, `/events` y `/ai` a `http://127.0.0.1:8000`.

En Vercel, `vercel.json` publica esta interfaz y la API en el mismo dominio. Las llamadas usan rutas relativas, así que el navegador no cruza orígenes.

Un precio sin observación de mercado llega desde la API con procedencia `SYNTHETIC` y un monto de demostración. La interfaz no inventa ese monto y no lo presenta como un precio de anaquel. El subpuntaje es un valor derivado del motor. Una ausencia nutricional permanece vacía.
