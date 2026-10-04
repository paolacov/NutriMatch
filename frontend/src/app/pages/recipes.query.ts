import { AiRecipeDraft, Product, RecipeProductContext } from '../core/models/domain';
import { catalogPlaceholderSrc, usableProductImage } from '../shared/format';
import { RecipeVisualKind, recipeScene, diversifyRecipeScenes } from './recipes.visual';

export const RECIPE_ROUTE = '/recetas';
export const MIN_RECIPE_CARDS = 3;
export const MAX_RECIPE_CARDS = 6;

export const RECIPES_COPY = {
  title: 'Recetas',
  kicker: 'Nuti Chef',
  subtitle: 'Descubre qué puedes preparar con lo que tienes en tu carrito.',
  nutiOk: 'Con lo que tienes, se me ocurren estas ideas…',
  nutiLoading: 'Estoy pensando qué podemos preparar…',
  nutiEmpty: 'Primero necesitamos algunos ingredientes.',
  nutiNone: 'Todavía no encuentro una combinación para preparar algo con lo que tienes.',
  shelfKicker: 'Lo que tienes',
  shelfHint: 'En tu carrito',
  cardsKicker: 'Ideas de Nuti',
  chefLabel: 'Nuti Chef recomienda',
  bridge: 'Veamos qué podemos preparar…',
  emptyBody: 'Agrega productos a tu carrito y aquí descubriremos qué puedes preparar.',
  noneTitle: 'Todavía no encuentro una combinación',
  noneBody: 'Prueba agregando otro producto a tu carrito.',
  explore: 'Explorar productos',
  openRecipe: 'Ver receta',
  haveKicker: 'Con lo que tienes',
  needKicker: 'También necesitas',
  needNone: 'Solo necesitas lo que ya tienes en tu carrito.',
  stepsKicker: 'Preparación',
  modalCue: '¡Vamos a prepararla!',
  close: 'Cerrar',
} as const;

export interface RecipeShelfItem {
  code: string;
  displayName: string;
  quantity: string | null;
  imageSrc: string;
  usesPlaceholder: boolean;
}

export interface RecipeIdea {
  id: string;
  codes: string[];
  products: Product[];
  contexts: RecipeProductContext[];
  title: string;
  description: string;
  usesLabel: string;
  productLine: string;
  displayNames: string[];
  extras: string[];
  steps: string[];
  usedItems: RecipeShelfItem[];
  imageSrc: string;
  imageAlt: string;
  visualKind: RecipeVisualKind;
  usesPlaceholder: boolean;
  usesAll: boolean;
}

export function shouldAskRecipes(codes: string[]): boolean {
  return codes.some((code) => Boolean(code?.trim()));
}

export function recipesAskInput(codes: string[]): { intent: 'recipe'; codes: string[] } | null {
  const limpios = [...new Set(codes.map((code) => code.trim()).filter(Boolean))];
  if (!limpios.length) {
    return null;
  }
  return { intent: 'recipe', codes: limpios };
}

export function contextByCode(
  contexts: RecipeProductContext[],
  code: string,
): RecipeProductContext | undefined {
  return contexts.find((ctx) => ctx.code === code);
}

export function visibleRecipeName(product: Product, ctx?: RecipeProductContext): string | null {
  const display = ctx?.displayName?.trim() || ctx?.culinaryName?.trim();
  if (display) {
    return display;
  }
  return product.name.value?.trim() || null;
}

export function productIsUsable(product: Product, ctx?: RecipeProductContext): boolean {
  return Boolean(visibleRecipeName(product, ctx));
}

export function usesLabel(count: number): string {
  if (count <= 1) {
    return 'Usa 1 producto de tu carrito';
  }
  return `Usa ${count} productos de tu carrito`;
}

export function recipeImage(products: Product[]): { src: string; alt: string; placeholder: boolean } {
  const conFoto = products.find((p) => usableProductImage(p.imageUrl));
  const foto = usableProductImage(conFoto?.imageUrl);
  if (conFoto && foto) {
    return { src: foto, alt: conFoto.name.value?.trim() || 'Producto', placeholder: false };
  }
  const primero = products[0];
  return {
    src: catalogPlaceholderSrc(primero?.category),
    alt: 'Sin foto',
    placeholder: true,
  };
}

export function shelfItems(products: Product[], contexts: RecipeProductContext[] = []): RecipeShelfItem[] {
  const items: RecipeShelfItem[] = [];
  for (const product of products) {
    const ctx = contextByCode(contexts, product.code);
    const displayName = visibleRecipeName(product, ctx);
    if (!displayName) {
      continue;
    }
    const visual = recipeImage([product]);
    items.push({
      code: product.code,
      displayName,
      quantity: ctx?.quantity || product.quantity,
      imageSrc: visual.src,
      usesPlaceholder: visual.placeholder,
    });
  }
  return items;
}

function normalizePiece(value: string): string {
  return value.toLowerCase().replace(/\s+/g, ' ').trim();
}

function namesOf(product: Product, ctx?: RecipeProductContext): string[] {
  return [
    product.name.value?.trim() ?? '',
    ctx?.originalName ?? '',
    ctx?.displayName ?? '',
    ctx?.culinaryName ?? '',
  ]
    .map(normalizePiece)
    .filter(Boolean);
}

export function extrasNotInCart(
  extras: string[],
  products: Product[],
  contexts: RecipeProductContext[] = [],
  usedNames: string[] = [],
): string[] {
  const observed = new Set(
    products.flatMap((p) => p.ingredients.map(normalizePiece)).filter(Boolean),
  );
  const names = [
    ...products.flatMap((p) => namesOf(p, contextByCode(contexts, p.code))),
    ...usedNames.map(normalizePiece),
  ].filter(Boolean);
  const seen = new Set<string>();
  const limpios: string[] = [];
  for (const extra of extras) {
    const pieza = normalizePiece(extra);
    if (!pieza || observed.has(pieza) || seen.has(pieza)) {
      continue;
    }
    const tokens = names.flatMap((n) => n.split(' '));
    if (pieza.length >= 3 && (tokens.includes(pieza) || names.some((n) => n.includes(pieza)))) {
      continue;
    }
    seen.add(pieza);
    limpios.push(extra.trim());
  }
  return limpios;
}

function matchProducts(used: string[], products: Product[], contexts: RecipeProductContext[]): Product[] {
  if (!used.length) {
    return products.filter((p) => productIsUsable(p, contextByCode(contexts, p.code)));
  }
  const matched: Product[] = [];
  const seen = new Set<string>();
  for (const crudo of used) {
    const pieza = normalizePiece(crudo);
    if (!pieza) {
      continue;
    }
    const hit = products.find((product) => {
      if (seen.has(product.code)) {
        return false;
      }
      const nombres = namesOf(product, contextByCode(contexts, product.code));
      return nombres.includes(pieza) || nombres.some((n) => n.split(' ').includes(pieza) || n.includes(pieza));
    });
    if (hit) {
      seen.add(hit.code);
      matched.push(hit);
    }
  }
  return matched;
}

function esPlatillo(nombre: string, displayNames: string[]): boolean {
  const clave = normalizePiece(nombre);
  if (!clave) {
    return false;
  }
  return !displayNames.some((n) => normalizePiece(n) === clave);
}

export function recipeCardsFromDrafts(
  drafts: AiRecipeDraft[],
  products: Product[],
  contexts: RecipeProductContext[] = [],
): RecipeIdea[] {
  const displayNames = products
    .map((p) => visibleRecipeName(p, contextByCode(contexts, p.code)))
    .filter((n): n is string => Boolean(n));
  const pool = products.filter((p) => productIsUsable(p, contextByCode(contexts, p.code)));
  const cards: RecipeIdea[] = [];
  const vistos = new Set<string>();
  for (const draft of drafts) {
    const title = draft.name?.trim() ?? '';
    if (!title || !draft.steps.length || !esPlatillo(title, displayNames)) {
      continue;
    }
    const clave = normalizePiece(title);
    if (vistos.has(clave)) {
      continue;
    }
    const used = matchProducts(draft.usedProducts, pool, contexts);
    const usados = used.length ? used : pool;
    const names = usados
      .map((p) => visibleRecipeName(p, contextByCode(contexts, p.code)))
      .filter((n): n is string => Boolean(n));
    const ideaContexts = usados
      .map((p) => contextByCode(contexts, p.code))
      .filter((ctx): ctx is RecipeProductContext => Boolean(ctx));
    const extras = extrasNotInCart(draft.extraSuggested, usados, ideaContexts, names);
    const steps = draft.steps.slice(0, 5);
    const description = draft.shortDescription?.trim() ?? '';
    const scene = recipeScene({
      title,
      description,
      displayNames: names,
      extras,
      steps,
    });
    vistos.add(clave);
    cards.push({
      id: `recipe:${clave}`,
      codes: usados.map((p) => p.code),
      products: usados,
      contexts: ideaContexts,
      title,
      description,
      usesLabel: usesLabel(usados.length),
      productLine: names.join(' · '),
      displayNames: names,
      extras,
      steps,
      usedItems: shelfItems(usados, ideaContexts),
      imageSrc: scene.src,
      imageAlt: scene.alt,
      visualKind: scene.kind,
      usesPlaceholder: false,
      usesAll: usados.length === pool.length && pool.length >= 2,
    });
    if (cards.length >= MAX_RECIPE_CARDS) {
      break;
    }
  }
  return diversifyRecipeScenes(cards.sort((a, b) => b.displayNames.length - a.displayNames.length));
}

export function toRecipeDraft(row: {
  name: string;
  short_description?: string;
  used_products?: string[];
  available_ingredients: string[];
  extra_suggested: string[];
  steps: string[];
  nutrition_note: string;
}): AiRecipeDraft {
  return {
    name: row.name,
    shortDescription: row.short_description ?? '',
    usedProducts: row.used_products ?? row.available_ingredients ?? [],
    availableIngredients: row.available_ingredients,
    extraSuggested: row.extra_suggested,
    steps: row.steps,
    nutritionNote: row.nutrition_note,
  };
}
