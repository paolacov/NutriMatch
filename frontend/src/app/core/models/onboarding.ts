import { DietaDeclarada, DimensionPrioridad } from './domain';

export type OnboardingStage = 'hello' | 'name' | 'prioridades' | 'cuidar' | 'resumen';

export type GoalId = 'cotidiana' | 'proteina' | 'azucar' | 'info' | 'preparar' | 'precio';

export type FocusCard = 'nutricion' | 'proteina' | 'azucar' | 'sodio' | 'ingredientes' | 'precio';

export interface OnboardingState {
  finished: boolean;
  displayName: string;
  goals: GoalId[];
  nutritionFocus: Array<'proteina' | 'azucar' | 'sodio'>;
  considerPrice: boolean;
  dietOther: boolean;
}

export const DEFAULT_ONBOARDING: OnboardingState = {
  finished: false,
  displayName: '',
  goals: [],
  nutritionFocus: [],
  considerPrice: false,
  dietOther: false,
};

export const GOAL_OPTIONS: { id: GoalId; title: string; hint: string }[] = [
  { id: 'cotidiana', title: 'Alimentación cotidiana', hint: 'El día a día' },
  { id: 'proteina', title: 'Mayor aporte de proteína', hint: 'Si está declarado' },
  { id: 'azucar', title: 'Menor cantidad de azúcar', hint: 'Si está declarado' },
  { id: 'info', title: 'Mejor información nutricional', hint: 'Qué hay y qué falta' },
  { id: 'preparar', title: 'Preparar comidas o postres', hint: 'Con lo que ya llevas' },
  { id: 'precio', title: 'Considerar el precio', hint: 'Se muestra en la ficha. No cambia el ranking' },
];

export const FOCUS_OPTIONS: { id: FocusCard; title: string; hint: string }[] = [
  { id: 'nutricion', title: 'Nutrición', hint: 'Por 100 g, si hay dato' },
  { id: 'proteina', title: 'Proteína', hint: 'Si está declarada' },
  { id: 'azucar', title: 'Menos azúcar', hint: 'Si está declarado' },
  { id: 'sodio', title: 'Menos sodio', hint: 'Si la sal está declarada' },
  { id: 'ingredientes', title: 'Ingredientes', hint: 'Si hay dato de procesamiento' },
  { id: 'precio', title: 'Precio', hint: 'Se muestra en la ficha. No cambia el ranking' },
];

const NUTRITION_CARDS: FocusCard[] = ['nutricion', 'proteina', 'azucar', 'sodio'];

export function toPriorityOrder(cards: FocusCard[]): DimensionPrioridad[] {
  const order: DimensionPrioridad[] = [];
  const add = (dim: DimensionPrioridad): void => {
    if (!order.includes(dim)) {
      order.push(dim);
    }
  };
  for (const card of cards) {
    if (card === 'ingredientes') {
      add('D2');
    } else if (card === 'precio') {
      continue;
    } else if (NUTRITION_CARDS.includes(card)) {
      add('D1');
    }
  }
  for (const dim of ['D1', 'D2', 'D3'] as const) {
    add(dim);
  }
  return order;
}

export function nutritionFocusFrom(cards: FocusCard[]): Array<'proteina' | 'azucar' | 'sodio'> {
  return cards.filter((card): card is 'proteina' | 'azucar' | 'sodio' => {
    return card === 'proteina' || card === 'azucar' || card === 'sodio';
  });
}

export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] ?? '';
}

export function goalTitles(ids: GoalId[]): string[] {
  return GOAL_OPTIONS.filter((opt) => ids.includes(opt.id)).map((opt) => opt.title);
}

export function focusTitles(ids: FocusCard[]): string[] {
  return FOCUS_OPTIONS.filter((opt) => ids.includes(opt.id)).map((opt) => opt.title);
}

export function dietTitle(diet: DietaDeclarada | null, other: boolean): string {
  if (other) {
    return 'Otra preferencia';
  }
  if (diet === 'vegetariano') {
    return 'Vegetariana';
  }
  if (diet === 'vegano') {
    return 'Vegana';
  }
  return 'Sin preferencia';
}

const PRIORITY_LEAD: Record<DimensionPrioridad, string> = {
  D1: 'la nutrición',
  D2: 'el procesamiento',
  D3: 'tus etiquetas de preferencia',
};

/** `null` es la opción Ninguno: ninguna restricción de alérgeno. */
export function nextAllergenTags(current: readonly string[], choice: string | null): string[] {
  if (choice === null) {
    return [];
  }
  if (current.includes(choice)) {
    return current.filter((tag) => tag !== choice);
  }
  return [...current, choice];
}

export function priorityClosing(
  name: string,
  first: DimensionPrioridad,
  diet: DietaDeclarada | null,
): string {
  let line = `${name}, voy a poner ${PRIORITY_LEAD[first]} primero`;
  if (diet === 'vegetariano') {
    line += ', con alimentación vegetariana';
  } else if (diet === 'vegano') {
    line += ', con alimentación vegana';
  }
  return `${line}.`;
}

export function avoidClosing(names: readonly string[]): string {
  if (!names.length) {
    return 'No tienes ingredientes o alérgenos que quieras evitar.';
  }
  const listed =
    names.length > 3 ? `${names[0]}, ${names[1]} y ${names.length - 2} más` : joinNames(names);
  return `También tendré en cuenta ${listed} al mostrarte los productos.`;
}

function joinNames(names: readonly string[]): string {
  if (names.length === 1) {
    return names[0] ?? '';
  }
  if (names.length === 2) {
    return `${names[0]} y ${names[1]}`;
  }
  return `${names.slice(0, -1).join(', ')} y ${names.at(-1)}`;
}

export function progressIndex(stage: OnboardingStage): number {
  switch (stage) {
    case 'name':
      return 0;
    case 'prioridades':
      return 1;
    case 'cuidar':
      return 2;
    case 'resumen':
      return 3;
    default:
      return -1;
  }
}
