import {
  CATALOG_COPY,
  catalogCanGoBack,
  catalogCanGoNext,
  catalogQueryParams,
  catalogTotalPages,
  parseCatalogQuery,
  productHref,
} from './catalog.query';

describe('catálogo de exploración', () => {
  it('parte los query params de carga inicial', () => {
    expect(parseCatalogQuery({ q: ' avena ', categoria: 'en:milk-and-dairy-products', page: '2' })).toEqual({
      search: 'avena',
      category: 'en:milk-and-dairy-products',
      page: 2,
    });
    expect(parseCatalogQuery({})).toEqual({ search: '', category: '', page: 1 });
    expect(parseCatalogQuery({ page: '0' }).page).toBe(1);
  });

  it('arma la búsqueda y la categoría sin mandar página 1', () => {
    expect(catalogQueryParams({ search: 'avena', category: '', page: 1 })).toEqual({ q: 'avena' });
    expect(catalogQueryParams({ search: '', category: 'en:cereals-and-potatoes', page: 3 })).toEqual({
      categoria: 'en:cereals-and-potatoes',
      page: '3',
    });
  });

  it('pagina sin pedir todos los productos', () => {
    expect(catalogTotalPages(16851, 24)).toBe(703);
    expect(catalogTotalPages(0)).toBe(0);
    expect(catalogCanGoBack(1)).toBe(false);
    expect(catalogCanGoBack(2)).toBe(true);
    expect(catalogCanGoNext(1, 3)).toBe(true);
    expect(catalogCanGoNext(3, 3)).toBe(false);
  });

  it('el estado vacío y el de error tienen acciones distintas', () => {
    expect(CATALOG_COPY.empty).not.toBe(CATALOG_COPY.error);
    expect(CATALOG_COPY.emptyAction).not.toBe(CATALOG_COPY.errorAction);
  });

  it('la ficha reutiliza la ruta actual de producto', () => {
    expect(productHref('0074323081411')).toEqual(['/producto', '0074323081411']);
  });
});
