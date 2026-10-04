export type RecipeVisualKind =
  | 'breakfast'
  | 'bowl'
  | 'pasta'
  | 'taco'
  | 'salad'
  | 'sweet'
  | 'baked'
  | 'snack';

export const RECIPE_VISUAL_SRC: Record<RecipeVisualKind, string> = {
  breakfast: '/recipes/breakfast.jpg',
  bowl: '/recipes/bowl.jpg',
  pasta: '/recipes/pasta.jpg',
  taco: '/recipes/taco.jpg',
  salad: '/recipes/salad.jpg',
  sweet: '/recipes/sweet.jpg',
  baked: '/recipes/baked.jpg',
  snack: '/recipes/snack.jpg',
};

export const RECIPE_VISUAL_ALT: Record<RecipeVisualKind, string> = {
  breakfast: 'Preparación de desayuno',
  bowl: 'Bowl fresco',
  pasta: 'Plato completo',
  taco: 'Tortillas y tacos',
  salad: 'Ensalada',
  sweet: 'Preparación dulce',
  baked: 'Horneado',
  snack: 'Idea culinaria',
};

const CLAVES: Record<RecipeVisualKind, string[]> = {
  sweet: [
    'postre',
    'dulce',
    'chocolate',
    'cajeta',
    'flan',
    'helado',
    'brownie',
    'galleta',
    'pay',
    'cheesecake',
    'nieve',
  ],
  taco: ['taco', 'tortilla', 'quesadilla', 'burrito', 'tostada', 'sincronizada', 'flauta'],
  salad: ['ensalada', 'salad'],
  pasta: ['pasta', 'espagueti', 'spaghetti', 'tallarin', 'lasana', 'fettuccine', 'penne', 'macarron'],
  bowl: ['bowl', 'poke', 'acai'],
  baked: ['hornea', 'horno', 'muffin', 'bizcocho', 'pan dulce', 'baguette'],
  breakfast: [
    'desayuno',
    'omelette',
    'omelet',
    'hotcake',
    'pancake',
    'huevo revuelto',
    'huevos',
    'avena',
    'huevo',
  ],
  snack: ['snack', 'botana', 'aperitivo'],
};

const ORDEN: RecipeVisualKind[] = [
  'sweet',
  'taco',
  'salad',
  'pasta',
  'bowl',
  'baked',
  'breakfast',
  'snack',
];

const RESPALDO: RecipeVisualKind[] = [
  'breakfast',
  'baked',
  'snack',
  'bowl',
  'pasta',
  'salad',
  'taco',
  'sweet',
];

export function foldVisualText(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function contiene(texto: string, claves: string[]): boolean {
  return claves.some((clave) => texto.includes(clave));
}

export function recipeVisualKind(input: {
  title: string;
  description?: string;
  displayNames?: string[];
  extras?: string[];
  steps?: string[];
}): RecipeVisualKind {
  const titulo = foldVisualText(input.title);
  const todo = foldVisualText(
    [
      input.title,
      input.description ?? '',
      ...(input.displayNames ?? []),
      ...(input.extras ?? []),
      ...(input.steps ?? []),
    ].join(' '),
  );
  for (const kind of ORDEN) {
    if (contiene(titulo, CLAVES[kind])) {
      return kind;
    }
  }
  for (const kind of ORDEN) {
    if (contiene(todo, CLAVES[kind])) {
      return kind;
    }
  }
  return 'snack';
}

export function recipeScene(input: {
  title: string;
  description?: string;
  displayNames?: string[];
  extras?: string[];
  steps?: string[];
}): { kind: RecipeVisualKind; src: string; alt: string } {
  const kind = recipeVisualKind(input);
  return {
    kind,
    src: RECIPE_VISUAL_SRC[kind],
    alt: RECIPE_VISUAL_ALT[kind],
  };
}

export function diversifyRecipeScenes<
  T extends { visualKind: RecipeVisualKind; imageSrc: string; imageAlt: string },
>(cards: T[]): T[] {
  const ocupados = new Set<RecipeVisualKind>();
  return cards.map((card) => {
    let kind = card.visualKind;
    if (ocupados.has(kind)) {
      const siguiente = RESPALDO.find((item) => !ocupados.has(item));
      if (siguiente) {
        kind = siguiente;
      }
    }
    ocupados.add(kind);
    if (kind === card.visualKind) {
      return card;
    }
    return {
      ...card,
      visualKind: kind,
      imageSrc: RECIPE_VISUAL_SRC[kind],
      imageAlt: RECIPE_VISUAL_ALT[kind],
    };
  });
}
