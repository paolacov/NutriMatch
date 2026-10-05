// Producción. Cadena vacía: mismo origen. vercel.json reenvía
// /meta, /search, /products, /catalog, /ranking, /cart, /events y /ai
// a FastAPI. El build de Vercel sustituye este valor con API_BASE_URL
// solo si esa variable está definida.
export const environment = {
  production: true,
  apiBaseUrl: '',
};
