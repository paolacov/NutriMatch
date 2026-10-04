import { AiRecipeDraft, DEFAULT_PROFILE, Product, RecipeProductContext } from '../core/models/domain';
import {
  extrasNotInCart,
  MIN_RECIPE_CARDS,
  RECIPES_COPY,
  RECIPE_ROUTE,
  recipeCardsFromDrafts,
  recipesAskInput,
  shelfItems,
  shouldAskRecipes,
  toRecipeDraft,
  usesLabel,
  visibleRecipeName,
} from './recipes.query';
import { RECIPE_VISUAL_SRC, recipeVisualKind } from './recipes.visual';

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
      warnings: [],
      status: 'DERIVED',
      dimensions: [],
      nutrients: [],
    },
    ...partial,
  };
}

function ctx(partial: Partial<RecipeProductContext> & Pick<RecipeProductContext, 'code'>): RecipeProductContext {
  return {
    originalName: partial.originalName ?? 'CAJETA DE LECHE DE CABRA 660G',
    displayName: partial.displayName ?? 'Cajeta',
    culinaryName: partial.culinaryName ?? 'cajeta',
    productType: partial.productType ?? 'cajeta',
    brand: partial.brand ?? 'Coronado',
    quantity: partial.quantity ?? '660G',
    availableIngredients: partial.availableIngredients ?? [],
    ...partial,
  };
}

function draft(partial: Partial<AiRecipeDraft> & Pick<AiRecipeDraft, 'name'>): AiRecipeDraft {
  return {
    shortDescription: 'Una opción rápida y sencilla',
    usedProducts: [],
    availableIngredients: [],
    extraSuggested: [],
    steps: ['Sirve.'],
    nutritionNote: '',
    ...partial,
  };
}

describe('Recetas desde el carrito', () => {
  it('carrito vacío no pide recetas al modelo', () => {
    expect(shouldAskRecipes([])).toBe(false);
    expect(recipesAskInput([])).toBeNull();
    expect(recipesAskInput(['', '  '])).toBeNull();
    expect(recipeCardsFromDrafts([], [])).toEqual([]);
    expect(shelfItems([])).toEqual([]);
  });

  it('un producto genera recetas basadas en ese producto', () => {
    const cajeta = product({ code: '1' });
    const cards = recipeCardsFromDrafts(
      [
        draft({
          name: 'Tostadas con cajeta',
          usedProducts: ['Cajeta'],
          extraSuggested: ['Pan'],
          steps: ['Tuesta el pan.', 'Agrega la cajeta.', 'Sirve.'],
        }),
      ],
      [cajeta],
    );
    expect(cards.length).toBe(1);
    expect(cards[0].title).toBe('Tostadas con cajeta');
    expect(cards[0].title).not.toBe('Cajeta');
    expect(cards[0].codes).toEqual(['1']);
    expect(cards[0].usesLabel).toBe('Usa 1 producto de tu carrito');
    expect(cards[0].steps.length).toBeGreaterThan(0);
  });

  it('dos productos priorizan la receta que usa ambos', () => {
    const cajeta = product({ code: '1' });
    const pan = product({
      code: '2',
      name: { value: 'Pan', status: 'REAL' },
      category: 'en:breads',
    });
    const cards = recipeCardsFromDrafts(
      [
        draft({
          name: 'Pan tostado',
          usedProducts: ['Pan'],
          steps: ['Tuesta el pan.'],
        }),
        draft({
          name: 'Tostadas con cajeta',
          usedProducts: ['Cajeta', 'Pan'],
          extraSuggested: ['Plátano'],
          steps: ['Tuesta el pan.', 'Agrega el plátano.', 'Añade la cajeta.', 'Sirve.'],
        }),
      ],
      [cajeta, pan],
    );
    expect(cards[0].title).toBe('Tostadas con cajeta');
    expect(cards[0].codes).toEqual(['1', '2']);
    expect(cards[0].usesAll).toBe(true);
    expect(cards[0].usesLabel).toBe('Usa 2 productos de tu carrito');
    expect(cards[0].usedItems.map((item) => item.displayName)).toEqual(['Cajeta', 'Pan']);
    expect(cards[1].title).toBe('Pan tostado');
    expect(usesLabel(1)).toBe('Usa 1 producto de tu carrito');
  });

  it('acepta al menos tres ideas, con uno o con los dos productos', () => {
    const tortillas = product({
      code: '1',
      name: { value: 'Tortillas de harina', status: 'REAL' },
    });
    const huevo = product({
      code: '2',
      name: { value: 'Huevo', status: 'REAL' },
    });
    const cards = recipeCardsFromDrafts(
      [
        draft({
          name: 'Tacos de huevo',
          usedProducts: ['Tortillas de harina', 'Huevo'],
          steps: ['Calienta las tortillas.', 'Cocina el huevo.', 'Arma los tacos.'],
        }),
        draft({
          name: 'Huevos revueltos',
          usedProducts: ['Huevo'],
          steps: ['Bate los huevos.', 'Cocina.'],
        }),
        draft({
          name: 'Quesadillas sencillas',
          usedProducts: ['Tortillas de harina'],
          extraSuggested: ['Queso'],
          steps: ['Calienta la tortilla.', 'Agrega queso.', 'Dobla.'],
        }),
      ],
      [tortillas, huevo],
    );
    expect(cards.length).toBeGreaterThanOrEqual(MIN_RECIPE_CARDS);
    expect(cards.map((card) => card.title)).toEqual([
      'Tacos de huevo',
      'Huevos revueltos',
      'Quesadillas sencillas',
    ]);
    expect(cards[0].displayNames).toEqual(['Tortillas de harina', 'Huevo']);
    expect(cards[1].displayNames).toEqual(['Huevo']);
    expect(cards[2].displayNames).toEqual(['Tortillas de harina']);
    expect(new Set(cards.map((card) => card.imageSrc)).size).toBe(cards.length);
  });

  it('varios productos priorizan las recetas que aprovechan más', () => {
    const cajeta = product({ code: '1' });
    const pan = product({ code: '2', name: { value: 'Pan', status: 'REAL' } });
    const yogur = product({ code: '3', name: { value: 'Yogur', status: 'REAL' } });
    const cards = recipeCardsFromDrafts(
      [
        draft({ name: 'Yogur', usedProducts: ['Yogur'], steps: ['Sirve el yogur.'] }),
        draft({
          name: 'Bowl de yogur y avena',
          usedProducts: ['Yogur'],
          extraSuggested: ['Avena'],
          steps: ['Sirve el yogur.', 'Agrega avena.'],
        }),
        draft({
          name: 'Tostadas con cajeta y yogur',
          usedProducts: ['Cajeta', 'Pan', 'Yogur'],
          steps: ['Tuesta el pan.', 'Unta cajeta.', 'Agrega yogur.', 'Sirve.'],
        }),
      ],
      [cajeta, pan, yogur],
    );
    expect(cards[0].title).toBe('Tostadas con cajeta y yogur');
    expect(cards[0].displayNames.length).toBe(3);
    expect(cards.some((card) => card.title === 'Yogur')).toBe(false);
  });

  it('RecipeDraft conserva nombre, descripción, usados, extras y pasos', () => {
    const mapped = toRecipeDraft({
      name: 'Tostadas con cajeta',
      short_description: 'Una opción rápida y sencilla',
      used_products: ['Cajeta', 'Pan'],
      available_ingredients: ['Cajeta', 'Pan'],
      extra_suggested: ['Plátano'],
      steps: ['Tuesta el pan.', 'Agrega el plátano.', 'Añade la cajeta.', 'Sirve.'],
      nutrition_note: 'No se calculó la nutrición de esta preparación.',
    });
    expect(mapped).toEqual({
      name: 'Tostadas con cajeta',
      shortDescription: 'Una opción rápida y sencilla',
      usedProducts: ['Cajeta', 'Pan'],
      availableIngredients: ['Cajeta', 'Pan'],
      extraSuggested: ['Plátano'],
      steps: ['Tuesta el pan.', 'Agrega el plátano.', 'Añade la cajeta.', 'Sirve.'],
      nutritionNote: 'No se calculó la nutrición de esta preparación.',
    });
  });

  it('no duplica un extra que ya está en el carrito', () => {
    const cajeta = product({
      code: '1',
      name: { value: 'Cajeta Coronado', status: 'REAL' },
      ingredients: ['leche', 'azúcar'],
    });
    expect(extrasNotInCart(['cajeta', 'plátano', 'leche'], [cajeta])).toEqual(['plátano']);
    const cards = recipeCardsFromDrafts(
      [
        draft({
          name: 'Tostadas con cajeta',
          usedProducts: ['Cajeta Coronado'],
          extraSuggested: ['Cajeta', 'Plátano'],
          steps: ['Unta la cajeta.', 'Agrega plátano.'],
        }),
      ],
      [cajeta],
    );
    expect(cards[0].extras).toEqual(['Plátano']);
  });

  it('un extra vacío no se muestra', () => {
    const pan = product({ code: '2', name: { value: 'Pan', status: 'REAL' } });
    expect(extrasNotInCart(['', '  '], [pan])).toEqual([]);
  });

  it('no trata el nombre del producto como si fuera una receta', () => {
    const cajeta = product({ code: '1' });
    const cards = recipeCardsFromDrafts(
      [draft({ name: 'Cajeta', usedProducts: ['Cajeta'], steps: ['Sirve.'] })],
      [cajeta],
    );
    expect(cards).toEqual([]);
  });

  it('los chips usan el nombre normalizado, no el crudo', () => {
    const crudo = product({
      code: '1',
      name: { value: 'CAJETA DE LECHE DE CABRA 660G', status: 'REAL' },
    });
    const pan = product({
      code: '2',
      name: { value: 'PAN BLANCO BIMBO GRANDE 680G', status: 'REAL' },
    });
    const contextos = [
      ctx({
        code: '1',
        originalName: 'CAJETA DE LECHE DE CABRA 660G',
        displayName: 'Cajeta',
        culinaryName: 'cajeta',
      }),
      ctx({
        code: '2',
        originalName: 'PAN BLANCO BIMBO GRANDE 680G',
        displayName: 'Pan integral',
        culinaryName: 'pan',
        brand: 'Bimbo',
      }),
    ];
    const chips = shelfItems([crudo, pan], contextos);
    expect(chips.map((item) => item.displayName)).toEqual(['Cajeta', 'Pan integral']);
    expect(visibleRecipeName(crudo, contextos[0])).toBe('Cajeta');
    expect(contextos[0].originalName).not.toBe(contextos[0].displayName);
  });

  it('la pantalla tiene título, Nuti, lista, tarjetas y detalle que se abre y se cierra', () => {
    expect(RECIPE_ROUTE).toBe('/recetas');
    expect(RECIPES_COPY.title).toBe('Recetas');
    expect(RECIPES_COPY.kicker).toBe('Nuti Chef');
    expect(RECIPES_COPY.subtitle).toContain('carrito');
    expect(RECIPES_COPY.nutiOk).toBe('Con lo que tienes, se me ocurren estas ideas…');
    expect(RECIPES_COPY.nutiLoading).toContain('pensando');
    expect(RECIPES_COPY.nutiEmpty).toContain('ingredientes');
    expect(RECIPES_COPY.nutiNone).toContain('combinación');
    expect(RECIPES_COPY.shelfKicker).toBe('Lo que tienes');
    expect(RECIPES_COPY.shelfHint).toBe('En tu carrito');
    expect(RECIPES_COPY.cardsKicker).toBe('Ideas de Nuti');
    expect(RECIPES_COPY.bridge).toContain('preparar');
    expect(RECIPES_COPY.emptyBody).toContain('carrito');
    expect(RECIPES_COPY.openRecipe).toBe('Ver receta');
    expect(RECIPES_COPY.close).toBe('Cerrar');
    expect(RECIPES_COPY.haveKicker).toBe('Con lo que tienes');
    expect(RECIPES_COPY.needKicker).toBe('También necesitas');
    expect(RECIPES_COPY.needNone).toContain('carrito');
    expect(RECIPES_COPY.modalCue).toContain('prepararla');
    expect(RECIPES_COPY.noneBody).toContain('carrito');
    expect(JSON.stringify(RECIPES_COPY)).not.toMatch(/intent|critic|baseline|LLM|OpenAI|fallback|payload/i);

    const cajeta = product({ code: '1' });
    const pan = product({ code: '2', name: { value: 'Pan', status: 'REAL' } });
    const cards = recipeCardsFromDrafts(
      [
        draft({
          name: 'Tostadas con cajeta',
          usedProducts: ['Cajeta', 'Pan'],
          extraSuggested: ['Plátano'],
          steps: ['Tuesta el pan.', 'Agrega el plátano.', 'Añade la cajeta.', 'Sirve.'],
        }),
      ],
      [cajeta, pan],
    );
    let seleccion = cards[0];
    expect(seleccion.title).toBe('Tostadas con cajeta');
    expect(seleccion.productLine).toContain('Cajeta');
    expect(seleccion.extras).toEqual(['Plátano']);
    expect(seleccion.steps.length).toBeGreaterThan(0);
    expect(seleccion.visualKind).toBe('sweet');
    expect(seleccion.imageSrc).toBe(RECIPE_VISUAL_SRC.sweet);
    seleccion = null as unknown as typeof seleccion;
    expect(seleccion).toBeNull();
    expect(DEFAULT_PROFILE.priorityOrder).toEqual(['D1', 'D2', 'D3']);
  });

  it('asigna una escena culinaria de forma determinista, sin LLM', () => {
    expect(recipeVisualKind({ title: 'Tacos de huevo', displayNames: ['Tortillas de harina', 'Huevo'] })).toBe(
      'taco',
    );
    expect(recipeVisualKind({ title: 'Huevos revueltos', displayNames: ['Huevo'] })).toBe('breakfast');
    expect(recipeVisualKind({ title: 'Ensalada verde', displayNames: ['Lechuga'] })).toBe('salad');
    expect(recipeVisualKind({ title: 'Bowl de yogur', displayNames: ['Yogur'] })).toBe('bowl');
    expect(recipeVisualKind({ title: 'Pasta al ajo', displayNames: ['Pasta'] })).toBe('pasta');
    expect(recipeVisualKind({ title: 'Tostadas con cajeta', displayNames: ['Cajeta', 'Pan'] })).toBe('sweet');
    expect(recipeVisualKind({ title: 'Pan horneado', displayNames: ['Harina'] })).toBe('baked');
    expect(recipeVisualKind({ title: 'Algo sencillo', displayNames: ['Queso'] })).toBe('snack');
    expect(RECIPE_VISUAL_SRC.taco).toBe('/recipes/taco.jpg');
  });
});
