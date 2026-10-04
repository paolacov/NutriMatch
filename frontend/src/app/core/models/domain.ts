export type ProvenanceStatus = 'REAL' | 'DERIVED' | 'IMPUTED' | 'SYNTHETIC' | 'UNAVAILABLE';
export type Band = 'ranking' | 'no_verificable' | 'informacion_insuficiente' | 'excluido';
export type AllergyStatus = 'apto' | 'no_apto' | 'no_verificable';
export type DietStatus = 'compatible' | 'incompatible' | 'no_verificable';
export type DietaDeclarada = 'vegano' | 'vegetariano';
export type DimensionPrioridad = 'D1' | 'D2' | 'D3';
export type OtterPose = 'discovering' | 'match' | 'alert' | 'explaining' | 'comparing' | 'recommend' | 'chef';
export type OtterVariant =
  | 'home'
  | 'search'
  | 'scan'
  | 'result'
  | 'explain'
  | 'compare'
  | 'alert'
  | 'recipes'
  | 'empty'
  | 'empty_cart'
  | 'empty_compare';
export type EventType = 'cart_item_added' | 'cart_item_removed' | 'ranking_run_created' | 'product_viewed';
export type AiIntent =
  | 'explain'
  | 'alerts'
  | 'nutrition'
  | 'compare'
  | 'recipe'
  | 'normalize_product'
  | 'plato'
  | 'fun_fact'
  | 'ask'
  | 'reject';
export type AiSurface =
  | 'search'
  | 'product'
  | 'compare'
  | 'cart'
  | 'alerts'
  | 'recipes'
  | 'recommendations';

export interface AiRecipeDraft {
  name: string;
  shortDescription: string;
  usedProducts: string[];
  availableIngredients: string[];
  extraSuggested: string[];
  steps: string[];
  nutritionNote: string;
}

export interface RecipeProductContext {
  code: string;
  originalName: string | null;
  displayName: string | null;
  culinaryName: string | null;
  productType: string | null;
  brand: string | null;
  quantity: string | null;
  availableIngredients: string[];
}

export interface AiAskResult {
  intent: AiIntent;
  text: string;
  source: 'llm' | 'baseline';
  fallback: boolean;
  fallbackReason: string | null;
  criticPass: boolean | null;
  recipe: AiRecipeDraft | null;
  recipes: AiRecipeDraft[];
  recipeProducts: RecipeProductContext[];
  comparison: Record<string, unknown> | null;
  platoEducation: string[];
}

export interface UsageEvent {
  id: number;
  eventType: EventType;
  payload: Record<string, string | number | null>;
  createdAt: string;
}

export interface ProvenanceField<T> {
  value: T | null;
  status: ProvenanceStatus;
  source?: string | null;
  note?: string | null;
}

export interface NutrientRow {
  key: string;
  label: string;
  per100g: number | null;
  unit: string;
  status: ProvenanceStatus;
}

export interface Product {
  code: string;
  name: ProvenanceField<string>;
  brand: ProvenanceField<string>;
  quantity: string | null;
  category: string | null;
  imageHint: string;
  imageUrl: string | null;
  nutrients: NutrientRow[];
  ingredients: string[];
  allergens: string[];
  traces: string[];
  labels: string[];
  price: ProvenanceField<number>;
  priceSource?: string | null;
  novaGroup: number | null;
  dataQualityScore: number | null;
  dataQualityLevel: string | null;
  dataQualityLabel: string | null;
  dataQualityDetalle: string | null;
  fit: ProductFit;
}

export interface DimensionExplain {
  key: DimensionPrioridad;
  subscore: number | null;
  weight: number;
  available: boolean;
  weightedContribution: number | null;
}

export interface NutrientExplain {
  key: string;
  percentile: number | null;
  sign: number;
  available: boolean;
  contribution: number | null;
}

export interface ProductFit {
  score: number | null;
  cov: number;
  d1: number | null;
  d2: number | null;
  d3: number | null;
  band: Band;
  allergyStatus: AllergyStatus;
  dietStatus: DietStatus;
  highlights: string[];
  warnings: string[];
  status: ProvenanceStatus;
  dimensions: DimensionExplain[];
  nutrients: NutrientExplain[];
}

export interface UserProfile {
  allergenTags: string[];
  diet: DietaDeclarada | null;
  valuedLabels: string[];
  priorityOrder: DimensionPrioridad[];
}

export type CartMethod = 'promedio_100g' | 'ponderado_gramos';

export interface NutrientAggregate {
  key: string;
  label: string;
  unit: string;
  value: number | null;
  status: ProvenanceStatus;
  nWithData: number;
  nProducts: number;
}

export interface GroupBucket {
  key: string;
  label: string;
  n: number;
  share: number;
  codes: string[];
}

export interface CartSummary {
  nProducts: number;
  method: CartMethod;
  methodNote: string;
  status: ProvenanceStatus;
  nutrients: NutrientAggregate[];
  plato: GroupBucket[];
  categories: GroupBucket[];
}

export const ALLERGEN_CHOICES: [string, string][] = [
  ['en:gluten', 'Gluten'],
  ['en:milk', 'Leche'],
  ['en:eggs', 'Huevo'],
  ['en:soybeans', 'Soya'],
  ['en:nuts', 'Frutos secos'],
  ['en:peanuts', 'Cacahuate'],
  ['en:sesame-seeds', 'Sésamo'],
  ['en:fish', 'Pescado'],
  ['en:crustaceans', 'Crustáceos'],
];

export const LABEL_CHOICES: [string, string][] = [
  ['en:organic', 'Orgánico'],
  ['en:no-gluten', 'Sin gluten'],
  ['en:fair-trade', 'Comercio ético'],
  ['en:vegetarian', 'Vegetariano (sello)'],
  ['en:vegan', 'Vegano (sello)'],
];

export const PRIORITY_LABELS: Record<DimensionPrioridad, string> = {
  D1: 'Nutrición',
  D2: 'Procesamiento',
  D3: 'Etiquetas',
};

export const OTTER_POSE_SRC: Record<OtterPose, string> = {
  discovering: '/otter/nuti-discovering.png',
  match: '/otter/nuti-match.png',
  alert: '/otter/nuti-alert.png',
  explaining: '/otter/nuti-explaining.png',
  comparing: '/otter/nuti-comparing.png',
  recommend: '/otter/nuti-recommend.png',
  chef: '/otter/nuti-chef.png',
};

export const OTTER_VARIANT_POSE: Record<OtterVariant, OtterPose> = {
  home: 'discovering',
  search: 'discovering',
  scan: 'discovering',
  result: 'recommend',
  explain: 'explaining',
  compare: 'comparing',
  alert: 'alert',
  recipes: 'chef',
  empty: 'match',
  empty_cart: 'match',
  empty_compare: 'match',
};

export const OTTER_LINES: Record<OtterVariant, string> = {
  home: 'Cuando quieras, empezamos por el anaquel.',
  search: 'Escribe un nombre o pega el código de barras.',
  scan: 'Escaneemos tu producto.',
  result: 'Encontré algunas opciones que podrían interesarte.',
  explain: 'Te cuento lo que el motor ya calculó. Sin inventar datos.',
  compare: 'Las vemos lado a lado. Tú eliges; yo no nombro un ganador.',
  alert: 'Hay algo importante que deberías revisar en este producto.',
  recipes: 'Con lo que tienes, se me ocurren estas ideas…',
  empty: 'Cuando haya algo que ver aquí, lo vemos juntas.',
  empty_cart: 'Cuando agregues productos, los vemos juntos aquí.',
  empty_compare: 'Puedo ayudarte a comparar estos productos. Elige hasta tres fichas.',
};

export const DEFAULT_PROFILE: UserProfile = {
  allergenTags: [],
  diet: null,
  valuedLabels: [],
  priorityOrder: ['D1', 'D2', 'D3'],
};
