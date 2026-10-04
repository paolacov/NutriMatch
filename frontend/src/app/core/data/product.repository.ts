import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, of, switchMap } from 'rxjs';
import {
  AiAskResult,
  AiIntent,
  AiSurface,
  AllergyStatus,
  Band,
  CartSummary,
  DietStatus,
  EventType,
  GroupBucket,
  Product,
  ProvenanceStatus,
  AiRecipeDraft,
  RecipeProductContext,
  UsageEvent,
  UserProfile,
} from '../models/domain';
import { resolveCatalogPrice, usableProductImage } from '../../shared/format';
interface ApiProvenance {
  value: string | number | null;
  status: ProvenanceStatus;
  source?: string | null;
  note?: string | null;
}

interface ApiProduct {
  code: string;
  name: ApiProvenance;
  brand: ApiProvenance;
  quantity: string | null;
  category: string | null;
  image_url: string | null;
  image_hint: string;
  nutrients: Product['nutrients'];
  ingredients: string[];
  allergens: string[];
  traces?: string[];
  labels: string[];
  price: ApiProvenance;
  nova_group: number | null;
  data_quality_score?: number | null;
  data_quality_level?: string | null;
  data_quality_label?: string | null;
  data_quality_detalle?: string | null;
}

interface ApiNutrientExplain {
  percentile: number | null;
  sign: number;
  available: boolean;
  contribution: number | null;
}

interface ApiDimensionExplain {
  subscore: number | null;
  weight: number;
  available: boolean;
  weighted_contribution: number | null;
}

interface ApiRankingItem {
  code: string;
  band: Band;
  score: number | null;
  d1: number | null;
  d2: number | null;
  d3: number | null;
  cov: number;
  allergy_status: AllergyStatus;
  diet_status: DietStatus;
  explanation: {
    missing_flags: string[];
    dimensions?: Record<string, ApiDimensionExplain>;
    d1_nutrients?: Record<string, ApiNutrientExplain>;
  } | null;
}

interface ApiBandSlice {
  items: ApiRankingItem[];
  total: number;
}

interface ApiRankingResult {
  ranking: ApiBandSlice;
  no_verificable: ApiBandSlice;
  informacion_insuficiente: ApiBandSlice;
  excluded_count: number;
}

interface ApiAlternatives {
  code: string;
  category: string | null;
  reason: 'ok' | 'sin_categoria' | 'sin_opciones';
  total: number;
  items: ApiRankingItem[];
}

export interface AlternativesBundle {
  code: string;
  category: string | null;
  reason: 'ok' | 'sin_categoria' | 'sin_opciones';
  total: number;
  items: Product[];
}

export interface RecommendationBundle {
  ranking: Product[];
  noVerificable: Product[];
  insuficiente: Product[];
  rankingTotal: number;
  noVerificableTotal: number;
  insuficienteTotal: number;
  excluded: number;
}

export interface CatalogMeta {
  snapshotId: string;
  engineVersion: string;
  nProducts: number;
  nPuntuable: number;
}

export interface CatalogCategory {
  id: string;
  name: string;
  count: number;
}

export interface CatalogPageResult {
  items: Product[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export const BUNDLE_VACIO: RecommendationBundle = {
  ranking: [],
  noVerificable: [],
  insuficiente: [],
  rankingTotal: 0,
  noVerificableTotal: 0,
  insuficienteTotal: 0,
  excluded: 0,
};

const FIT_VACIO: Product['fit'] = {
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
};

function asText(value: string | number | null): string | null {
  return typeof value === 'string' ? value : null;
}

function asNumber(value: string | number | null): number | null {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === 'string' && value.trim()) {
    const numero = Number(value);
    return Number.isFinite(numero) ? numero : null;
  }
  return null;
}

function toProduct(api: ApiProduct): Product {
  return {
    code: api.code,
    name: {
      value: asText(api.name.value),
      status: api.name.status,
      source: api.name.source,
    },
    brand: { value: asText(api.brand.value), status: api.brand.status },
    quantity: api.quantity,
    category: api.category,
    imageHint: api.image_hint,
    imageUrl: usableProductImage(api.image_url),
    nutrients: api.nutrients,
    ingredients: api.ingredients,
    allergens: api.allergens,
    traces: api.traces ?? [],
    labels: api.labels,
    price: resolveCatalogPrice({
      code: api.code,
      price: {
        value: asNumber(api.price.value),
        status: api.price.status,
        source: api.price.source,
        note: api.price.note,
      },
    }),
    novaGroup: api.nova_group,
    dataQualityScore: api.data_quality_score ?? null,
    dataQualityLevel: api.data_quality_level ?? null,
    dataQualityLabel: api.data_quality_label ?? null,
    dataQualityDetalle: api.data_quality_detalle ?? null,
    fit: { ...FIT_VACIO },
  };
}

function round1(value: number | null): number | null {
  return value === null ? null : Math.round(value * 10) / 10;
}

function applyFit(product: Product, item: ApiRankingItem): Product {
  return {
    ...product,
    fit: {
      score: round1(item.score),
      cov: round1(item.cov) ?? 0,
      d1: round1(item.d1),
      d2: round1(item.d2),
      d3: round1(item.d3),
      band: item.band,
      allergyStatus: item.allergy_status,
      dietStatus: item.diet_status,
      highlights: [],
      warnings: item.explanation?.missing_flags ?? [],
      status: 'DERIVED',
      dimensions: (['D1', 'D2', 'D3'] as const).map((key) => {
        const dim = item.explanation?.dimensions?.[key];
        return {
          key,
          subscore: round1(dim?.subscore ?? null),
          weight: dim?.weight ?? 0,
          available: dim?.available ?? false,
          weightedContribution: round1(dim?.weighted_contribution ?? null),
        };
      }),
      nutrients: Object.entries(item.explanation?.d1_nutrients ?? {}).map(([key, n]) => ({
        key,
        percentile: round1(n.percentile),
        sign: n.sign,
        available: n.available,
        contribution: round1(n.contribution),
      })),
    },
  };
}

interface ApiNutrientAggregate {
  key: string;
  label: string;
  unit: string;
  value: number | null;
  status: ProvenanceStatus;
  n_with_data: number;
  n_products: number;
}

interface ApiGroupBucket {
  key: string;
  label: string;
  n: number;
  share: number;
  codes?: string[];
}

interface ApiUsageEvent {
  id: number;
  event_type: EventType;
  payload: Record<string, string | number | null>;
  created_at: string;
}

interface ApiCartSummary {
  n_products: number;
  method: CartSummary['method'];
  method_note: string;
  status: ProvenanceStatus;
  nutrients: ApiNutrientAggregate[];
  plato: ApiGroupBucket[];
  categories: ApiGroupBucket[];
}

function toGroupBucket(row: ApiGroupBucket): GroupBucket {
  return {
    key: row.key,
    label: row.label,
    n: row.n,
    share: row.share,
    codes: row.codes ?? [],
  };
}

function toCartSummary(row: ApiCartSummary): CartSummary {
  return {
    nProducts: row.n_products,
    method: row.method,
    methodNote: row.method_note,
    status: row.status,
    nutrients: row.nutrients.map((n) => ({
      key: n.key,
      label: n.label,
      unit: n.unit,
      value: n.value,
      status: n.status,
      nWithData: n.n_with_data,
      nProducts: n.n_products,
    })),
    plato: row.plato.map(toGroupBucket),
    categories: row.categories.map(toGroupBucket),
  };
}

function toApiProfile(profile: UserProfile) {
  return {
    allergen_tags: profile.allergenTags,
    diet: profile.diet,
    valued_labels: profile.valuedLabels,
    priority_order: profile.priorityOrder,
  };
}

function toRecipeDraft(row: {
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
    usedProducts: row.used_products ?? [],
    availableIngredients: row.available_ingredients,
    extraSuggested: row.extra_suggested,
    steps: row.steps,
    nutritionNote: row.nutrition_note,
  };
}

function toRecipeProductContext(row: {
  code: string;
  original_name: string | null;
  display_name: string | null;
  culinary_name: string | null;
  product_type: string | null;
  brand: string | null;
  quantity: string | null;
  available_ingredients?: string[];
}): RecipeProductContext {
  return {
    code: row.code,
    originalName: row.original_name,
    displayName: row.display_name,
    culinaryName: row.culinary_name,
    productType: row.product_type,
    brand: row.brand,
    quantity: row.quantity,
    availableIngredients: row.available_ingredients ?? [],
  };
}

@Injectable({ providedIn: 'root' })
export class ProductRepository {
  private readonly http = inject(HttpClient);
  private readonly recipeNameCache = new Map<string, RecipeProductContext>();

  meta(): Observable<CatalogMeta> {
    return this.http
      .get<{
        snapshot_id: string;
        engine_version: string;
        n_products: number;
        n_puntuable: number;
      }>('/meta')
      .pipe(
        map((row) => ({
          snapshotId: row.snapshot_id,
          engineVersion: row.engine_version,
          nProducts: row.n_products,
          nPuntuable: row.n_puntuable,
        })),
      );
  }

  search(query: string): Observable<Product[]> {
    return this.http
      .get<ApiProduct[]>('/search', { params: { q: query, limit: '40' } })
      .pipe(map((rows) => rows.map(toProduct)));
  }

  catalogCategories(): Observable<CatalogCategory[]> {
    return this.http.get<CatalogCategory[]>('/catalog/categories');
  }

  catalogProducts(input: {
    search?: string;
    category?: string;
    page?: number;
    pageSize?: number;
  }): Observable<CatalogPageResult> {
    return this.http
      .get<{
        items: ApiProduct[];
        total: number;
        page: number;
        page_size: number;
        total_pages: number;
      }>('/catalog/products', {
        params: {
          search: input.search ?? '',
          category: input.category ?? '',
          page: String(input.page ?? 1),
          page_size: String(input.pageSize ?? 24),
        },
      })
      .pipe(
        map((row) => ({
          items: row.items.map(toProduct),
          total: row.total,
          page: row.page,
          pageSize: row.page_size,
          totalPages: row.total_pages,
        })),
      );
  }

  byCode(code: string): Observable<Product | undefined> {
    if (!code) {
      return of(undefined);
    }
    return this.http.get<ApiProduct>(`/products/${encodeURIComponent(code)}`).pipe(
      map(toProduct),
      catchError(() => of(undefined)),
    );
  }

  byCodes(codes: string[]): Observable<Product[]> {
    if (!codes.length) {
      return of([]);
    }
    return this.http
      .get<ApiProduct[]>('/products', { params: { codes: codes.join(',') } })
      .pipe(map((rows) => rows.map(toProduct)));
  }

  cartSummary(codes: string[]): Observable<CartSummary> {
    return this.http.post<ApiCartSummary>('/cart/summary', { codes }).pipe(map(toCartSummary));
  }

  alternatives(code: string, profile: UserProfile): Observable<AlternativesBundle> {
    return this.http
      .post<ApiAlternatives>('/ranking/alternatives', {
        code,
        profile: toApiProfile(profile),
      })
      .pipe(
        switchMap((row) => {
          const vacio: AlternativesBundle = {
            code: row.code,
            category: row.category,
            reason: row.reason,
            total: row.total,
            items: [],
          };
          if (!row.items.length) {
            return of(vacio);
          }
          return this.byCodes(row.items.map((item) => item.code)).pipe(
            map((products) => {
              const porCode = new Map(products.map((product) => [product.code, product]));
              return {
                ...vacio,
                items: row.items
                  .map((item) => {
                    const base = porCode.get(item.code);
                    return base ? applyFit(base, item) : undefined;
                  })
                  .filter((product): product is Product => !!product),
              };
            }),
          );
        }),
      );
  }

  explain(code: string, profile: UserProfile): Observable<Product | undefined> {
    return this.byCode(code).pipe(
      switchMap((product) => {
        if (!product) {
          return of(undefined);
        }
        return this.http
          .post<ApiRankingItem>('/ranking/explain', { code, profile: toApiProfile(profile) })
          .pipe(map((item) => applyFit(product, item)));
      }),
    );
  }

  logEvent(eventType: EventType, payload: Record<string, string | number>): Observable<void> {
    return this.http.post('/events', { event_type: eventType, payload }).pipe(
      map(() => undefined),
      catchError(() => of(undefined)),
    );
  }

  listEvents(): Observable<UsageEvent[]> {
    return this.http.get<ApiUsageEvent[]>('/events', { params: { limit: '50' } }).pipe(
      map((rows) =>
        rows.map((row) => ({
          id: row.id,
          eventType: row.event_type,
          payload: row.payload,
          createdAt: row.created_at,
        })),
      ),
      catchError(() => of([])),
    );
  }

  askAi(input: {
    surface: AiSurface;
    codes: string[];
    profile: UserProfile;
    intent?: AiIntent;
    message?: string;
    culinaryGoal?: string;
  }): Observable<AiAskResult> {
    return this.http
      .post<{
        intent: AiIntent;
        text: string;
        source: 'llm' | 'baseline';
        fallback: boolean;
        fallback_reason: string | null;
        critic_pass: boolean | null;
        recipe: {
          name: string;
          short_description?: string;
          used_products?: string[];
          available_ingredients: string[];
          extra_suggested: string[];
          steps: string[];
          nutrition_note: string;
        } | null;
        recipes?: Array<{
          name: string;
          short_description?: string;
          used_products?: string[];
          available_ingredients: string[];
          extra_suggested: string[];
          steps: string[];
          nutrition_note: string;
        }>;
        recipe_products?: Array<{
          code: string;
          original_name: string | null;
          display_name: string | null;
          culinary_name: string | null;
          product_type: string | null;
          brand: string | null;
          quantity: string | null;
          available_ingredients?: string[];
        }>;
        comparison: Record<string, unknown> | null;
        plato_education: string[];
      }>('/ai/ask', {
        surface: input.surface,
        codes: input.codes,
        profile: toApiProfile(input.profile),
        intent: input.intent ?? 'ask',
        message: input.message ?? null,
        culinary_goal: input.culinaryGoal ?? null,
      })
      .pipe(
        map((row) => {
          const recipeProducts = (row.recipe_products ?? []).map(toRecipeProductContext);
          for (const ctx of recipeProducts) {
            if (ctx.code) {
              this.recipeNameCache.set(ctx.code, ctx);
            }
          }
          return {
            intent: row.intent,
            text: row.text,
            source: row.source,
            fallback: row.fallback,
            fallbackReason: row.fallback_reason,
            criticPass: row.critic_pass,
            recipe: row.recipe ? toRecipeDraft(row.recipe) : null,
            recipes: (row.recipes ?? []).map(toRecipeDraft),
            recipeProducts,
            comparison: row.comparison,
            platoEducation: row.plato_education ?? [],
          };
        }),
        catchError(() =>
          of({
            intent: 'ask' as const,
            text: 'No se pudo consultar la capa de lenguaje. Los números del motor no cambian.',
            source: 'baseline' as const,
            fallback: true,
            fallbackReason: 'network',
            criticPass: null,
            recipe: null,
            recipes: [],
            recipeProducts: [],
            comparison: null,
            platoEducation: [],
          }),
        ),
      );
  }

  normalizeRecipeProducts(codes: string[], profile: UserProfile): Observable<RecipeProductContext[]> {
    const unicos = [...new Set(codes.filter(Boolean))];
    if (!unicos.length) {
      return of([]);
    }
    const pending = unicos.filter((code) => !this.recipeNameCache.has(code));
    if (!pending.length) {
      return of(unicos.map((code) => this.recipeNameCache.get(code)!));
    }
    return this.askAi({
      surface: 'recipes',
      codes: unicos,
      profile,
      intent: 'normalize_product',
    }).pipe(
      map((row) => {
        for (const ctx of row.recipeProducts) {
          if (ctx.code) {
            this.recipeNameCache.set(ctx.code, ctx);
          }
        }
        return unicos.map((code) => this.recipeNameCache.get(code)).filter((ctx): ctx is RecipeProductContext => Boolean(ctx));
      }),
    );
  }

  recommendations(profile: UserProfile): Observable<RecommendationBundle> {
    return this.http
      .post<ApiRankingResult>('/ranking', {
        profile: toApiProfile(profile),
        query: '',
        top_n: 12,
      })
      .pipe(
        switchMap((resultado) => {
          const slices = [
            resultado.ranking.items,
            resultado.no_verificable.items,
            resultado.informacion_insuficiente.items,
          ];
          const codes = [...new Set(slices.flat().map((i) => i.code))];
          return this.byCodes(codes).pipe(
            map((products) => {
              const porCode = new Map(products.map((p) => [p.code, p]));
              const fitSlice = (items: ApiRankingItem[]) =>
                items
                  .map((item) => {
                    const base = porCode.get(item.code);
                    return base ? applyFit(base, item) : undefined;
                  })
                  .filter((p): p is Product => !!p);
              return {
                ranking: fitSlice(resultado.ranking.items),
                noVerificable: fitSlice(resultado.no_verificable.items),
                insuficiente: fitSlice(resultado.informacion_insuficiente.items),
                rankingTotal: resultado.ranking.total,
                noVerificableTotal: resultado.no_verificable.total,
                insuficienteTotal: resultado.informacion_insuficiente.total,
                excluded: resultado.excluded_count,
              };
            }),
          );
        }),
      );
  }
}
