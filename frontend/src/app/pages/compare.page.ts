import { DecimalPipe } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { combineLatest, forkJoin, of } from 'rxjs';
import { catchError, map, startWith, switchMap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { CompareStore } from '../core/data/compare.store';
import { ProductRepository } from '../core/data/product.repository';
import { ProfileStore } from '../core/data/profile.store';
import { Product } from '../core/models/domain';
import { LoadingWell } from '../shared/loading-well/loading-well';
import { OtterGuide } from '../shared/otter-guide/otter-guide';
import { BandChip } from '../shared/band-chip/band-chip';
import { CategoryMark } from '../shared/category-mark/category-mark';
import { ShelfStamps } from '../shared/shelf-stamps/shelf-stamps';
import {
  allergyCaption,
  categoryLabel,
  dietCaption,
  dimensionLabel,
  displayName,
  percentilePlace,
  priceAmount,
  priceKindLabel,
  priceLine,
} from '../shared/format';

type Tone = 'hi' | 'lo' | null;

type HitView =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'error' }
  | { kind: 'empty'; query: string }
  | { kind: 'ok'; query: string; items: Product[] };

const COMPARE_MAX = 3;

@Component({
  selector: 'app-compare-page',
  imports: [DecimalPipe, RouterLink, BandChip, CategoryMark, ShelfStamps, OtterGuide, LoadingWell],
  template: `
    <section class="compare-page">
      <header class="ink-bar">
        <h1 class="page-title">Comparar</h1>
        <img src="/brand/mark-compact.svg" alt="" />
      </header>

      <div class="compare-intro">
        <app-otter-guide
          [variant]="compare.codes().length ? 'compare' : 'empty_compare'"
          size="compact"
          [caption]="compare.codes().length ? '' : 'Busca un producto y lo miramos juntos.'"
        />
        <div>
          <p class="compare-count">Llevas {{ compare.codes().length }} de 3.</p>
          <p class="text-sm text-mute">Tres lugares. El score lo calcula el motor y tú decides.</p>
        </div>
      </div>

      <section class="card-paper compare-finder" aria-labelledby="compare-finder-title">
        <div>
          <h2 id="compare-finder-title">Busca un producto</h2>
          <p class="text-sm text-mute">Puedes mandarlo a la comparación o directo al carrito.</p>
        </div>
        <form class="compare-search" (submit)="$event.preventDefault(); buscar()">
          <input
            class="field-paper flex-1 px-5 py-3"
            placeholder="Nombre o código de barras"
            [value]="draft()"
            (input)="draft.set(valor($event))"
          />
          <button type="submit" class="btn btn-tide">Buscar</button>
        </form>
        @if (compare.codes().length >= max) {
          <p class="text-sm text-mute">La comparación está llena. Quita uno para agregar otro.</p>
        }

        @if (hits(); as busca) {
          @if (busca.kind === 'loading') {
            <app-loading-well label="Buscando…" />
          } @else if (busca.kind === 'error') {
            <p class="text-sm text-mute">No pude buscar en el catálogo. La comparación sigue igual.</p>
          } @else if (busca.kind === 'empty') {
            <p class="text-sm text-mute">Sin resultados para «{{ busca.query }}».</p>
          } @else if (busca.kind === 'ok') {
            @if (busca.items.length > 6) {
              <p class="text-sm text-mute">
                Hay {{ busca.items.length }} resultados. Aquí van los primeros 6.
              </p>
            }
            <ul class="compare-hits">
              @for (item of visibles(busca.items); track item.code) {
                <li class="compare-hit">
                  <div>
                    <a [routerLink]="['/producto', item.code]" class="font-semibold underline">{{ displayName(item) }}</a>
                    <p class="text-sm text-mute">
                      {{ item.brand.value?.trim() || 'Marca no disponible' }} · {{ categoryLabel(item.category) }}
                    </p>
                    <p class="compare-hit-price">{{ priceLine(item) }}</p>
                  </div>
                  <div class="compare-hit-actions">
                    <button
                      type="button"
                      class="btn btn-sm"
                      [class.btn-tide]="puedeAgregar(item.code)"
                      [class.btn-ghost]="!puedeAgregar(item.code)"
                      [disabled]="!puedeAgregar(item.code)"
                      (click)="agregar(item.code)"
                    >
                      {{ etiquetaAgregar(item.code) }}
                    </button>
                    <button
                      type="button"
                      class="btn btn-sm"
                      [class.btn-ember]="!cart.has(item.code)"
                      [class.btn-ghost]="cart.has(item.code)"
                      [disabled]="cart.has(item.code)"
                      (click)="cart.add(item.code)"
                    >
                      {{ cart.has(item.code) ? 'En el carrito' : 'Al carrito' }}
                    </button>
                  </div>
                </li>
              }
            </ul>
          }
        }
      </section>

      <section class="compare-stage" aria-labelledby="compare-stage-title">
        <h2 id="compare-stage-title">En comparación</h2>
      @if (!compare.codes().length) {
        <div class="empty-well">
          <p>Los tres lugares están libres. El primero que agregues aparece aquí.</p>
        </div>
      } @else if (!products().length) {
        <app-loading-well label="Cargando comparación…" />
      } @else {
        <p class="text-sm text-mute">
          El tono marca el mayor y el menor valor entre estos productos. Tú decides cuál te conviene.
        </p>
        <div class="overflow-x-auto">
          <div class="compare-grid">
            @for (p of products(); track p.code) {
              <article class="card-paper p-4">
                <p class="flex items-center gap-1.5 text-xs text-mute">
                  <app-category-mark [category]="p.category" />
                  {{ categoryLabel(p.category) }}
                </p>
                <a [routerLink]="['/producto', p.code]" class="mt-1 block font-semibold underline">
                  {{ displayName(p) }}
                </a>
                <p class="text-sm text-mute">{{ p.brand.value ?? 'Marca no disponible' }}</p>
                <div class="mt-2 flex flex-wrap items-center gap-2">
                  @if (p.fit.status === 'DERIVED') {
                    <app-band-chip [band]="p.fit.band" />
                  }
                </div>
                <div class="mt-3">
                  <app-shelf-stamps [labels]="p.labels" [compact]="true" />
                </div>
                @if (priceAmount(p); as monto) {
                  <p class="mt-3 text-sm font-semibold">{{ monto }}</p>
                  <p class="price-badge" [attr.data-price-kind]="p.price.status">{{ priceKind(p) }}</p>
                } @else {
                  <p class="mt-3 text-sm font-semibold">Precio no disponible</p>
                }

                <h3 class="mt-4 text-sm font-semibold">Tu perfil</h3>
                @if (allergyCaption(p.fit.allergyStatus, profile.profile().allergenTags); as alergia) {
                  <p class="mt-1 text-xs">{{ alergia }}</p>
                }
                @if (dietCaption(p.fit.dietStatus, profile.profile().diet); as dieta) {
                  <p class="text-xs">{{ dieta }}</p>
                }
                @if (!profile.profile().allergenTags.length && !profile.profile().diet) {
                  <p class="mt-1 text-xs text-mute">No declaraste alergias ni dieta.</p>
                }

                <h3 class="mt-4 text-sm font-semibold">Según tus preferencias</h3>
                <p class="compare-metric mt-2" [attr.data-tone]="tone(scores(), p.fit.score)">
                  <strong>
                    @if (p.fit.score === null) { — } @else { {{ p.fit.score | number:'1.0-1' }}/100 }
                  </strong>
                  <span class="compare-tone">{{ marca(tone(scores(), p.fit.score)) }}</span>
                </p>
                <ul class="mt-2 grid grid-cols-3 gap-1 text-center text-xs">
                  <li class="compare-metric" [attr.data-tone]="tone(d1s(), p.fit.d1)">
                    {{ dimensionLabel('D1') }}<br />
                    <strong>{{ p.fit.d1 === null ? '—' : (p.fit.d1 | number:'1.0-1') }}</strong>
                    <span class="compare-tone">{{ marca(tone(d1s(), p.fit.d1)) }}</span>
                  </li>
                  <li class="compare-metric" [attr.data-tone]="tone(d2s(), p.fit.d2)">
                    {{ dimensionLabel('D2') }}<br />
                    <strong>{{ p.fit.d2 === null ? '—' : (p.fit.d2 | number:'1.0-1') }}</strong>
                    <span class="compare-tone">{{ marca(tone(d2s(), p.fit.d2)) }}</span>
                  </li>
                  <li class="compare-metric" [attr.data-tone]="tone(d3s(), p.fit.d3)">
                    {{ dimensionLabel('D3') }}<br />
                    <strong>{{ p.fit.d3 === null ? '—' : (p.fit.d3 | number:'1.0-1') }}</strong>
                    <span class="compare-tone">{{ marca(tone(d3s(), p.fit.d3)) }}</span>
                  </li>
                </ul>

                <section class="compare-sat mt-4" aria-label="Grasa saturada">
                  <h3 class="text-sm font-semibold">Grasa saturada</h3>
                  <p class="compare-row compare-sat-row" [attr.data-tone]="tone(saturatedValues(), saturatedGrams(p))">
                    <span>g/100 g</span>
                    <strong>
                      @if (saturatedGrams(p) === null) { Dato no disponible }
                      @else { {{ saturatedGrams(p) | number:'1.0-1' }} }
                    </strong>
                  </p>
                  <p class="compare-tone">{{ marca(tone(saturatedValues(), saturatedGrams(p))) }}</p>
                  @if (saturatedExplain(p); as fila) {
                    <p class="mt-1 text-xs text-mute">
                      @if (fila.percentile === null) {
                        No hay una posición de este valor entre productos de su grupo.
                      } @else {
                        {{ lugar(fila.percentile) }} Menos es mejor.
                      }
                    </p>
                  }
                </section>

                <h3 class="mt-4 text-sm font-semibold">Por 100 g</h3>
                <ul class="mt-1 text-sm">
                  @for (key of nutrientKeys; track key) {
                    <li class="compare-row" [attr.data-tone]="tone(nutrientValues(key), nutrientValue(p, key))">
                      <span>{{ nutrientLabel(key) }}</span>
                      <span>
                        @if (nutrientValue(p, key) === null) { Dato no disponible }
                        @else { {{ nutrientValue(p, key) | number:'1.0-1' }} }
                      </span>
                      <span class="compare-tone">{{ marca(tone(nutrientValues(key), nutrientValue(p, key))) }}</span>
                    </li>
                  }
                </ul>

                <div class="compare-card-actions">
                  <button
                    type="button"
                    class="btn btn-sm"
                    [class.btn-ember]="!cart.has(p.code)"
                    [class.btn-ghost]="cart.has(p.code)"
                    [disabled]="cart.has(p.code)"
                    (click)="cart.add(p.code)"
                  >
                    {{ cart.has(p.code) ? 'En el carrito' : 'Al carrito' }}
                  </button>
                  <button type="button" class="btn btn-vest btn-sm" (click)="compare.remove(p.code)">
                    Quitar
                  </button>
                </div>
              </article>
            }
            @for (hueco of huecos(); track hueco) {
              <article class="compare-slot">
                <p>Lugar libre</p>
                <p>Búscalo arriba y agrégalo.</p>
              </article>
            }
          </div>
        </div>
        @if (huecos().length) {
          <p class="compare-room text-sm text-mute">Te caben {{ huecos().length }} más.</p>
        }
        <p class="text-xs text-mute">Los scores los calcula el motor. Tú eliges cuál te conviene.</p>
      }
      </section>
    </section>
  `,
})
export class ComparePage {
  readonly compare = inject(CompareStore);
  readonly cart = inject(CartStore);
  private readonly repo = inject(ProductRepository);
  readonly profile = inject(ProfileStore);
  readonly max = COMPARE_MAX;
  readonly draft = signal('');
  private readonly lookup = signal('');
  readonly displayName = displayName;
  readonly priceAmount = priceAmount;
  readonly priceKind = priceKindLabel;
  readonly priceLine = priceLine;
  readonly categoryLabel = categoryLabel;
  readonly allergyCaption = allergyCaption;
  readonly dietCaption = dietCaption;
  readonly dimensionLabel = dimensionLabel;
  readonly nutrientKeys = [
    'energy',
    'proteins',
    'carbohydrates',
    'sugars',
    'fat',
    'fiber',
    'salt',
  ];

  readonly hits = toSignal(
    toObservable(this.lookup).pipe(
      switchMap((raw) => {
        const query = raw.trim();
        if (query.length < 2) {
          return of({ kind: 'idle' } satisfies HitView);
        }
        return this.repo.search(query).pipe(
          map((items) =>
            items.length
              ? ({ kind: 'ok', query, items } satisfies HitView)
              : ({ kind: 'empty', query } satisfies HitView),
          ),
          startWith({ kind: 'loading' } satisfies HitView),
          catchError(() => of({ kind: 'error' } satisfies HitView)),
        );
      }),
    ),
    { initialValue: { kind: 'idle' } satisfies HitView },
  );

  readonly products = toSignal(
    combineLatest([toObservable(this.compare.codes), toObservable(this.profile.profile)]).pipe(
      switchMap(([codes, profile]) => {
        if (!codes.length) {
          return of([]);
        }
        return forkJoin(
          codes.map((code) =>
            this.repo.explain(code, profile).pipe(catchError(() => of(undefined))),
          ),
        ).pipe(map((rows) => rows.filter((p): p is Product => !!p)));
      }),
    ),
    { initialValue: [] },
  );

  valor(event: Event): string {
    return (event.target as HTMLInputElement).value;
  }

  buscar(): void {
    this.lookup.set(this.draft().trim());
  }

  puedeAgregar(code: string): boolean {
    return !this.compare.has(code) && this.compare.codes().length < COMPARE_MAX;
  }

  etiquetaAgregar(code: string): string {
    if (this.compare.has(code)) {
      return 'En la comparación';
    }
    if (this.compare.codes().length >= COMPARE_MAX) {
      return 'Quita uno';
    }
    return 'Agregar';
  }

  agregar(code: string): void {
    if (!this.puedeAgregar(code)) {
      return;
    }
    this.compare.toggle(code);
  }

  visibles(items: Product[]): Product[] {
    return items.slice(0, 6);
  }

  huecos(): number[] {
    const libres = COMPARE_MAX - this.compare.codes().length;
    return Array.from({ length: Math.max(0, libres) }, (_, indice) => indice);
  }

  scores(): (number | null)[] {
    return this.products().map((p) => p.fit.score);
  }

  d1s(): (number | null)[] {
    return this.products().map((p) => p.fit.d1);
  }

  d2s(): (number | null)[] {
    return this.products().map((p) => p.fit.d2);
  }

  d3s(): (number | null)[] {
    return this.products().map((p) => p.fit.d3);
  }

  saturatedGrams(product: Product): number | null {
    return this.nutrientValue(product, 'saturated-fat');
  }

  saturatedValues(): (number | null)[] {
    return this.products().map((product) => this.saturatedGrams(product));
  }

  saturatedExplain(product: Product): Product['fit']['nutrients'][number] | null {
    return product.fit.nutrients.find((row) => row.key === 'saturated-fat_100g') ?? null;
  }

  nutrientValue(product: Product, key: string): number | null {
    return product.nutrients.find((n) => n.key === key)?.per100g ?? null;
  }

  nutrientValues(key: string): (number | null)[] {
    return this.products().map((p) => this.nutrientValue(p, key));
  }

  nutrientLabel(key: string): string {
    return this.products()[0]?.nutrients.find((n) => n.key === key)?.label ?? key;
  }

  marca(tono: Tone): string {
    if (tono === 'hi') {
      return 'Mayor valor';
    }
    if (tono === 'lo') {
      return 'Menor valor';
    }
    return '';
  }

  lugar(percentil: number): string {
    return percentilePlace(percentil);
  }

  tone(values: (number | null)[], value: number | null): Tone {
    if (value === null) {
      return null;
    }
    const nums = values.filter((v): v is number => v !== null);
    if (nums.length < 2) {
      return null;
    }
    const min = Math.min(...nums);
    const max = Math.max(...nums);
    if (min === max) {
      return null;
    }
    if (value === max) {
      return 'hi';
    }
    if (value === min) {
      return 'lo';
    }
    return null;
  }
}
