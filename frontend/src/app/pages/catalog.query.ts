export const CATALOG_PAGE_SIZE = 24;

export const CATALOG_COPY = {
  kicker: 'El anaquel',
  title: 'Catálogo',
  nuti: 'Explora los productos disponibles, conoce sus características y descubre cuáles coinciden con tus preferencias.',
  searchLabel: 'Buscar en el anaquel',
  searchPlaceholder: 'Nombre o código de barras',
  search: 'Buscar',
  categories: 'Categorías',
  loading: 'Cargando el anaquel…',
  empty: 'No encontramos productos con eso.',
  emptyAction: 'Ver todo el anaquel',
  error: 'No pudimos cargar el catálogo.',
  errorAction: 'Intentar de nuevo',
  prev: 'Anterior',
  next: 'Siguiente',
};

export interface CatalogQuery {
  search: string;
  category: string;
  page: number;
}

export function parseCatalogQuery(params: {
  q?: string | null;
  categoria?: string | null;
  page?: string | null;
}): CatalogQuery {
  const page = Number(params.page ?? '1');
  return {
    search: (params.q ?? '').trim(),
    category: params.categoria ?? '',
    page: Number.isFinite(page) && page >= 1 ? Math.floor(page) : 1,
  };
}

export function catalogQueryParams(query: CatalogQuery): Record<string, string> {
  const params: Record<string, string> = {};
  if (query.search) {
    params['q'] = query.search;
  }
  if (query.category) {
    params['categoria'] = query.category;
  }
  if (query.page > 1) {
    params['page'] = String(query.page);
  }
  return params;
}

export function catalogTotalPages(total: number, pageSize = CATALOG_PAGE_SIZE): number {
  if (total <= 0) {
    return 0;
  }
  return Math.ceil(total / pageSize);
}

export function catalogCanGoBack(page: number): boolean {
  return page > 1;
}

export function catalogCanGoNext(page: number, totalPages: number): boolean {
  return totalPages > 0 && page < totalPages;
}

export function productHref(code: string): string[] {
  return ['/producto', code];
}
