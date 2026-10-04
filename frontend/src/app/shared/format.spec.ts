import { DEFAULT_PROFILE, Product } from '../core/models/domain';
import {
  allergyCaption,
  brandPriceLine,
  catalogDataCaption,
  catalogNutrientLine,
  catalogPlaceholderSrc,
  etiquetaDeSello,
  usableProductImage,
  dataQualityHeadline,
  coveragePhrase,
  d3MissingReason,
  dietCaption,
  displayName,
  flagLabel,
  formatPrice,
  historialProductName,
  priceCaption,
  priceKindLabel,
  priceSourceLine,
  resolveCatalogPrice,
  friendlyNutrientText,
  friendlyQuantity,
  nutrientSheetLabel,
  scorePhrase,
  visibleFlags,
} from './format';

function product(partial: Partial<Product> & Pick<Product, 'code'>): Product {
  return {
    name: { value: 'Cajeta', status: 'REAL' },
    brand: { value: 'Coronado', status: 'REAL' },
    quantity: '370 g',
    category: 'en:sweet-spreads',
    imageHint: '',
    imageUrl: null,
    nutrients: [],
    ingredients: [],
    allergens: [],
    traces: [],
    labels: [],
    price: { value: 115, status: 'REAL' },
    novaGroup: 4,
    dataQualityScore: null,
    dataQualityLevel: null,
    dataQualityLabel: null,
    dataQualityDetalle: null,
    fit: {
      score: 80,
      cov: 0.8,
      d1: 50,
      d2: 10,
      d3: null,
      band: 'ranking',
      allergyStatus: 'apto',
      dietStatus: 'compatible',
      highlights: [],
      warnings: ['D3_sin_dato'],
      status: 'DERIVED',
      dimensions: [],
      nutrients: [],
    },
    ...partial,
  };
}

describe('format UI copy', () => {
  it('conserva el nombre literal NAN', () => {
    const p = product({
      code: '7501058623201',
      name: { value: 'NAN', status: 'REAL' },
    });
    expect(displayName(p)).toBe('NAN');
    expect(historialProductName(p)).toBe('NAN');
  });

  it('no inventa nombre cuando falta', () => {
    const p = product({
      code: '00000285',
      name: { value: null, status: 'UNAVAILABLE' },
    });
    expect(displayName(p)).toBe('Sin nombre verificado');
    expect(historialProductName(p)).toBe('Producto sin nombre verificado');
    expect(historialProductName(undefined)).toBe('Producto sin nombre verificado');
  });

  it('marca ausente no deja un punto suelto', () => {
    const p = product({
      code: '00000285',
      brand: { value: null, status: 'UNAVAILABLE' },
      price: { value: 127, status: 'SYNTHETIC' },
    });
    expect(brandPriceLine(p)).toBe('Marca no disponible · $127.00 · Precio de demostración');
  });

  it('precio REAL no se etiqueta como demostración', () => {
    const p = product({
      code: '0074323081411',
      price: { value: 115, status: 'REAL', source: 'qqp_profeco' },
    });
    expect(formatPrice(p)).toBe('$115.00');
    expect(priceKindLabel(p)).toBe('Precio real · PROFECO');
    expect(priceSourceLine(p)).toBe('Fuente: PROFECO QQP');
    expect(priceCaption(p)).toContain('Precio real · PROFECO');
    expect(priceCaption(p)).not.toContain('demostración');
  });

  it('precio SYNTHETIC no se confunde con REAL y REAL tiene prioridad', () => {
    const demo = product({
      code: 'x',
      price: { value: 127, status: 'SYNTHETIC' },
    });
    expect(formatPrice(demo)).toBe('$127.00 · Precio de demostración');
    expect(priceKindLabel(demo)).toBe('Precio de demostración');
    expect(priceSourceLine(demo)).toBeNull();
    const apiReal = resolveCatalogPrice({
      code: '0074323081411',
      price: { value: 115, status: 'REAL', source: 'qqp_profeco' },
    });
    expect(apiReal.status).toBe('REAL');
    expect(apiReal.value).toBe(115);
    expect(apiReal.source).toBe('qqp_profeco');
    const ausente = resolveCatalogPrice({
      code: '00000285',
      price: { value: null, status: 'UNAVAILABLE' },
    });
    expect(ausente.status).toBe('UNAVAILABLE');
    expect(ausente.value).toBeNull();
    const demoApi = resolveCatalogPrice({
      code: '00000285',
      price: { value: 127, status: 'SYNTHETIC', source: 'demo' },
    });
    expect(demoApi.status).toBe('SYNTHETIC');
    expect(demoApi.value).toBe(127);
    expect(demoApi.source).toBe('demo');
    expect(formatPrice(product({ code: '00000285', price: demoApi }))).toContain('Precio de demostración');
    expect(formatPrice(product({ code: '00000285', price: demoApi }))).not.toContain('Precio real');
  });

  it('calidad de información usa etiquetas amigables', () => {
    const p = product({
      code: '1',
      dataQualityLabel: 'Alta',
      dataQualityLevel: 'alta',
      dataQualityDetalle: 'nutrition:1.0000;nova:1.0000',
    });
    expect(dataQualityHeadline(p)).toBe('Calidad de información: Alta');
    const baja = product({
      code: '2',
      dataQualityLevel: 'baja',
      dataQualityLabel: 'Información insuficiente',
    });
    expect(dataQualityHeadline(baja)).toBe('Calidad de información: Baja');
  });

  it('en catálogo un producto sin imagen no inventa foto y el precio ausente no es $0', () => {
    const p = product({
      code: 'x',
      imageUrl: null,
      price: { value: null, status: 'UNAVAILABLE' },
      nutrients: [
        { key: 'proteins', label: 'Proteína', per100g: null, unit: 'g', status: 'UNAVAILABLE' },
        { key: 'sugars', label: 'Azúcares', per100g: null, unit: 'g', status: 'UNAVAILABLE' },
      ],
    });
    expect(p.imageUrl).toBeNull();
    expect(formatPrice(p)).toBe('Precio no disponible');
    expect(catalogDataCaption(p)).toBe('Información nutricional no disponible');
    expect(catalogNutrientLine(p)).toBeNull();
    expect(catalogPlaceholderSrc(null)).toBe('/placeholders/shelf.jpg');
    expect(catalogPlaceholderSrc('en:breads')).toBe('/placeholders/cereal.jpg');
    expect(catalogPlaceholderSrc('en:milks')).toBe('/placeholders/dairy.jpg');
  });

  it('una foto marcada como invalid no se usa y los sellos salen en español', () => {
    expect(
      usableProductImage('https://images.openfoodfacts.org/images/products/invalid/front_fr.4.200.jpg'),
    ).toBeNull();
    expect(
      usableProductImage('https://images.openfoodfacts.org/images/products/750/302/573/7362/front_fr.8.200.jpg'),
    ).toContain('front_fr');
    expect(etiquetaDeSello('en:low-or-no-sugar')).toBe('Bajo o sin azúcar');
    expect(etiquetaDeSello('en:no-preservatives')).toBe('Sin conservadores');
    expect(etiquetaDeSello('en:no-hydrogenated-fats')).toBe('Sin grasas hidrogenadas');
    expect(etiquetaDeSello('en:no-lactose')).toBe('Sin lactosa');
    expect(etiquetaDeSello('en:no-cholesterol')).toBe('Sin colesterol');
    expect(etiquetaDeSello('en:vegetarian')).toBe('Vegetariano');
    expect(etiquetaDeSello('en:vegan')).toBe('Vegano');
    expect(etiquetaDeSello('es:exceso-azucares')).toBe('Exceso de azúcares');
    expect(etiquetaDeSello('es:contiene-edulcorantes-no-recomendable-en-ninos')).toBe(
      'Contiene edulcorantes, no recomendable en niños',
    );
  });

  it('en catálogo muestra nutrientes solo cuando hay dato', () => {
    const p = product({
      code: 'y',
      nutrients: [
        { key: 'proteins', label: 'Proteína', per100g: 8, unit: 'g', status: 'REAL' },
        { key: 'sugars', label: 'Azúcares', per100g: null, unit: 'g', status: 'UNAVAILABLE' },
      ],
    });
    expect(catalogNutrientLine(p)).toBe('Proteína 8.0 g');
    expect(catalogDataCaption(p)).toBe('Información nutricional parcial');
  });

  it('precio ausente no es $0', () => {
    const p = product({
      code: 'x',
      price: { value: null, status: 'UNAVAILABLE' },
    });
    expect(formatPrice(p)).toBe('Precio no disponible');
  });

  it('no afirma apto ni compatible sin restricción en el perfil', () => {
    expect(allergyCaption('apto', [])).toBeNull();
    expect(dietCaption('compatible', null)).toBeNull();
    expect(allergyCaption('no_verificable', ['en:milk'])).toBe('Alergia: no se puede determinar');
    expect(dietCaption('incompatible', 'vegano')).toBe('Dieta: incompatible');
  });

  it('distingue D3 sin etiquetas del usuario vs del producto', () => {
    expect(d3MissingReason([], ['en:organic'])).toContain('No elegiste etiquetas');
    expect(d3MissingReason(['en:organic'], [])).toContain('no tiene etiquetas registradas');
    expect(flagLabel('D3_sin_dato', { valuedLabels: [], productLabels: [] })).toContain(
      'No elegiste etiquetas',
    );
  });

  it('oculta banderas de alergia o dieta si el perfil no las declaró', () => {
    const flags = visibleFlags(
      ['D3_sin_dato', 'alergia_no_verificable', 'dieta_no_verificable'],
      DEFAULT_PROFILE,
    );
    expect(flags).toEqual(['D3_sin_dato']);
  });

  it('la frase del score respeta la banda y no inventa razones', () => {
    const alto = product({
      code: 'a',
      fit: {
        ...product({ code: 'a' }).fit,
        score: 95,
        band: 'ranking',
      },
    });
    expect(scorePhrase(alto)).toContain('puntuación alta');
    const insuficiente = product({
      code: 'b',
      fit: {
        ...product({ code: 'b' }).fit,
        score: null,
        band: 'informacion_insuficiente',
        cov: 0.3,
      },
    });
    expect(scorePhrase(insuficiente)).toContain('información suficiente');
    expect(coveragePhrase(0.8)).toContain('información suficiente');
    expect(coveragePhrase(0.3)).toContain('más de la mitad');
  });

  it('redondea la ficha sin cambiar el significado del dato', () => {
    expect(friendlyNutrientText(214.285714285714, 'kcal')).toBe('214 kcal');
    expect(friendlyNutrientText(11.5384615384615, 'g')).toBe('11.5 g');
    expect(friendlyNutrientText(0.192307692307692, 'g')).toBe('0.2 g');
    expect(friendlyNutrientText(0, 'g')).toBe('0 g');
    expect(friendlyNutrientText(null, 'g')).toBe('No disponible');
    expect(friendlyQuantity('20 oz (567 g)')).toBe('567 g');
    expect(friendlyQuantity('370 g')).toBe('370 g');
    expect(nutrientSheetLabel('energy', 'Energía (kcal)')).toBe('Energía');
    expect(nutrientSheetLabel('saturated-fat', 'Grasa saturada')).toBe('Grasas saturadas');
  });
});
