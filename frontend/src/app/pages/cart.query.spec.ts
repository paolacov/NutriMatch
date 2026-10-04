import { CartSummary, Product } from '../core/models/domain';
import {
  cartAlertBoard,
  cartAmountLabel,
  cartLegend,
  cartMoney,
  cartMoneyGap,
  cartTotalLabel,
  cartNotices,
  cartVariety,
  groupSentence,
  sharePercent,
} from './cart.query';

function product(code: string, price: Product['price']): Product {
  return {
    code,
    name: { value: code, status: 'REAL' },
    brand: { value: 'Marca', status: 'REAL' },
    quantity: null,
    category: null,
    imageHint: '',
    imageUrl: null,
    nutrients: [],
    ingredients: [],
    allergens: [],
    traces: [],
    labels: [],
    price,
    novaGroup: null,
    dataQualityScore: null,
    dataQualityLevel: null,
    dataQualityLabel: null,
    dataQualityDetalle: null,
    fit: {
      score: null,
      cov: 0,
      d1: null,
      d2: null,
      d3: null,
      band: 'informacion_insuficiente',
      allergyStatus: 'no_verificable',
      dietStatus: 'no_verificable',
      highlights: [],
      warnings: [],
      status: 'UNAVAILABLE',
      dimensions: [],
      nutrients: [],
    },
  };
}

function summary(partial: Partial<CartSummary> & Pick<CartSummary, 'plato' | 'categories'>): CartSummary {
  return {
    nProducts: partial.nProducts ?? 0,
    method: 'promedio_100g',
    methodNote: '',
    status: 'DERIVED',
    nutrients: [],
    plato: partial.plato,
    categories: partial.categories,
  };
}

describe('total del carrito', () => {
  it('suma solo precios ya resueltos y separa demostración de real', () => {
    const money = cartMoney([
      product('a', { value: 10, status: 'REAL' }),
      product('b', { value: 2.5, status: 'SYNTHETIC' }),
      product('c', { value: null, status: 'UNAVAILABLE' }),
    ]);
    expect(money.amount).toBe(12.5);
    expect(money.realCount).toBe(1);
    expect(money.demoCount).toBe(1);
    expect(money.missingCount).toBe(1);
    expect(cartAmountLabel(money)).toBe('$12.50');
    expect(cartLegend(money)).toBe('Incluye precios reales y de demostración');
    expect(cartTotalLabel(money)).toBe('$12.50 · Incluye precios reales y de demostración');
    expect(cartMoneyGap(money)).toContain('no entra en el total');
  });

  it('no presenta un total de demostración como precio real', () => {
    const money = cartMoney([product('a', { value: 18, status: 'SYNTHETIC' })]);
    expect(money.amount).toBe(18);
    expect(cartTotalLabel(money)).toBe('$18.00 · Precio de demostración');
    expect(cartTotalLabel(money)).not.toContain('reales');
  });

  it('no inventa un total cuando no hay precio', () => {
    const money = cartMoney([product('a', { value: null, status: 'UNAVAILABLE' })]);
    expect(money.amount).toBeNull();
    expect(cartTotalLabel(money)).toBe('');
  });

  it('un total solo real no se llama estimado', () => {
    const money = cartMoney([product('a', { value: 10, status: 'REAL' })]);
    expect(cartTotalLabel(money)).toBe('$10.00 MXN');
  });

  it('suma la demostración y le añade un precio real sin mezclar las leyendas', () => {
    const demostracion = cartMoney([
      product('a', { value: 200, status: 'SYNTHETIC' }),
      product('b', { value: 180, status: 'SYNTHETIC' }),
      product('c', { value: 150, status: 'SYNTHETIC' }),
      product('d', { value: 96, status: 'SYNTHETIC' }),
    ]);
    expect(demostracion.amount).toBe(626);
    expect(cartAmountLabel(demostracion)).toBe('$626.00');
    expect(cartLegend(demostracion)).toBe('Precio de demostración');

    const conCajeta = cartMoney([
      product('a', { value: 200, status: 'SYNTHETIC' }),
      product('b', { value: 180, status: 'SYNTHETIC' }),
      product('c', { value: 150, status: 'SYNTHETIC' }),
      product('d', { value: 96, status: 'SYNTHETIC' }),
      product('0074323081411', { value: 115, status: 'REAL', source: 'qqp_profeco' }),
    ]);
    expect(conCajeta.amount).toBe(741);
    expect(cartAmountLabel(conCajeta)).toBe('$741.00');
    expect(cartLegend(conCajeta)).toBe('Incluye precios reales y de demostración');
  });
});

describe('variedad y alertas del plato', () => {
  const plato = [
    { key: 'frutas_verduras', label: 'Verduras y frutas', n: 2, share: 0.5, codes: ['a', 'b'] },
    { key: 'cereales', label: 'Cereales', n: 0, share: 0, codes: [] },
    { key: 'leguminosas_aoa', label: 'Leguminosas y alimentos de origen animal', n: 1, share: 0.25, codes: ['c'] },
    { key: 'unclassified', label: 'no clasificado', n: 1, share: 0.25, codes: ['d'] },
  ];

  it('cuenta grupos de la guía y categorías, sin evaluar la alimentación', () => {
    const row = summary({
      nProducts: 4,
      plato,
      categories: [
        { key: 'en:fruits', label: 'Frutas', n: 2, share: 0.5, codes: [] },
        { key: 'en:milks', label: 'Leches', n: 1, share: 0.25, codes: [] },
        { key: 'unclassified', label: 'no clasificado', n: 1, share: 0.25, codes: [] },
      ],
    });
    expect(cartVariety(row)).toEqual({ groups: 2, categories: 2, products: 4 });
    expect(groupSentence(plato[1])).toBe('Actualmente no hay productos clasificados en este grupo.');
    expect(groupSentence(plato[0])).toBe('Este grupo representa 2 productos de tu carrito.');
    expect(sharePercent(plato[0], 4)).toBe(50);
    expect(sharePercent(plato[1], 4)).toBeNull();
    const notices = cartNotices(row);
    expect(notices.some((line) => line.includes('saludable'))).toBeFalse();
    expect(notices).toContain('No hay productos clasificados actualmente en Cereales.');
    expect(notices).toContain('Existe poca variedad dentro de Leguminosas y alimentos de origen animal.');
    const board = cartAlertBoard(row);
    expect(board.headline).toBe('Tu carrito contiene productos de diferentes grupos del Plato del Buen Comer.');
    expect(board.groups.map((group) => group.label)).toEqual([
      'Verduras y frutas',
      'Cereales',
      'Leguminosas y alimentos de origen animal',
    ]);
    expect(board.groups[1].present).toBeFalse();
    expect(board.groups[1].detail).toBe('Actualmente no hay productos clasificados en este grupo.');
    expect(board.footnote).toBe('Algunos productos no cuentan con información suficiente para clasificarlos.');
    expect(board.cheer).toBeFalse();
    expect(board.headline.includes('AOA')).toBeFalse();
  });
});
