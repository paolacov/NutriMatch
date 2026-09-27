import { DecimalPipe } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, map, of, switchMap, tap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { CompareStore } from '../core/data/compare.store';
import { ProductRepository } from '../core/data/product.repository';
import { ProfileStore } from '../core/data/profile.store';
import { BandChip } from '../shared/band-chip/band-chip';
import { CategoryMark } from '../shared/category-mark/category-mark';
import { OtterGuide } from '../shared/otter-guide/otter-guide';
import { ProvenanceBadge } from '../shared/provenance-badge/provenance-badge';
import { ShelfStamps } from '../shared/shelf-stamps/shelf-stamps';
import {
  allergyLabel,
  categoryLabel,
  dietLabel,
  dimensionLabel,
  displayName,
  flagLabel,
  nutrientD1Label,
  nutrientSignLabel,
  priceCaption,
  scoreCaption,
} from '../shared/format';

@Component({
  selector: 'app-product-page',
  imports: [RouterLink, OtterGuide, ProvenanceBadge, DecimalPipe, BandChip, CategoryMark, ShelfStamps],
  template: `
    @if (product(); as p) {
      <article class="space-y-6">
        <app-otter-guide variant="result" />
        <header class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p class="flex items-center gap-1.5 text-sm text-mute">
              <app-category-mark [category]="p.category" />
              {{ categoryLabel(p.category) }} · {{ p.code }}
            </p>
            <h1 class="text-3xl font-bold">{{ displayName(p) }}</h1>
            <p class="text-mute">{{ p.brand.value ?? 'Marca no disponible' }} · {{ p.quantity ?? 'Presentación no declarada' }}</p>
            <div class="mt-2 flex flex-wrap items-center gap-2">
              @if (p.fit.status === 'DERIVED') {
                <app-band-chip [band]="p.fit.band" />
              }
              <app-provenance-badge [status]="p.name.status" />
              <app-provenance-badge [status]="p.brand.status" />
            </div>
          </div>
          <div class="rounded-xl bg-paper p-4 ring-1 ring-sand">
            <p class="text-sm font-semibold">{{ priceCaption(p) }}</p>
            <app-provenance-badge [status]="p.price.status" />
          </div>
        </header>

        <div class="grid gap-4 lg:grid-cols-2">
          <section class="rounded-xl bg-paper p-5 ring-1 ring-sand">
            <h2 class="text-lg font-semibold">¿Qué tan bien encaja contigo?</h2>
            <p class="mt-2 text-4xl font-bold">
              @if (p.fit.score === null) { — } @else { {{ p.fit.score | number:'1.0-1' }} }
              <span class="text-base font-normal text-mute">/ 100</span>
            </p>
            <div class="mt-1 flex flex-wrap items-center gap-2">
              <app-provenance-badge [status]="p.fit.status" />
              <p class="text-xs text-mute">{{ scoreCaption(p) }}</p>
            </div>
            <p class="mt-2 text-sm">Cobertura {{ p.fit.cov | number:'1.0-2' }}</p>
            <p class="text-sm text-mute">
              Alergia: {{ allergyLabel(p.fit.allergyStatus) }} · Dieta: {{ dietLabel(p.fit.dietStatus) }}
            </p>
            @if (p.fit.warnings.length) {
              <ul class="mt-2 space-y-1 text-sm text-mute">
                @for (w of p.fit.warnings; track w) {
                  <li>{{ flagLabel(w) }}</li>
                }
              </ul>
            }
            <ul class="mt-3 grid grid-cols-3 gap-2 text-center text-sm">
              <li class="rounded-lg bg-cream p-2">
                {{ dimensionLabel('D1') }}<br />
                <strong>{{ p.fit.d1 === null ? '—' : (p.fit.d1 | number:'1.0-1') }}</strong>
              </li>
              <li class="rounded-lg bg-cream p-2">
                {{ dimensionLabel('D2') }}<br />
                <strong>{{ p.fit.d2 === null ? '—' : (p.fit.d2 | number:'1.0-1') }}</strong>
              </li>
              <li class="rounded-lg bg-cream p-2">
                {{ dimensionLabel('D3') }}<br />
                <strong>{{ p.fit.d3 === null ? '—' : (p.fit.d3 | number:'1.0-1') }}</strong>
              </li>
            </ul>
            @if (p.fit.dimensions.length) {
              <table class="mt-4 w-full text-left text-sm">
                <caption class="mb-2 text-left font-semibold">Peso y contribución</caption>
                <thead>
                  <tr class="text-mute">
                    <th class="py-1 font-medium">Dimensión</th>
                    <th class="py-1 text-right font-medium">Peso</th>
                    <th class="py-1 text-right font-medium">Aporta</th>
                  </tr>
                </thead>
                <tbody>
                  @for (d of p.fit.dimensions; track d.key) {
                    <tr class="border-t border-sand">
                      <td class="py-1">{{ dimensionLabel(d.key) }}</td>
                      <td class="py-1 text-right">{{ d.weight | number:'1.0-2' }}</td>
                      <td class="py-1 text-right">
                        @if (!d.available || d.weightedContribution === null) { Información no disponible }
                        @else { {{ d.weightedContribution | number:'1.0-1' }} }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            }
            @if (p.fit.nutrients.length) {
              <table class="mt-4 w-full text-left text-sm">
                <caption class="mb-2 text-left font-semibold">Nutrientes de D1</caption>
                <thead>
                  <tr class="text-mute">
                    <th class="py-1 font-medium">Nutriente</th>
                    <th class="py-1 text-right font-medium">Percentil</th>
                    <th class="py-1 text-right font-medium">Aporta</th>
                  </tr>
                </thead>
                <tbody>
                  @for (n of p.fit.nutrients; track n.key) {
                    <tr class="border-t border-sand">
                      <td class="py-1">
                        {{ nutrientD1Label(n.key) }}
                        <span class="block text-xs text-mute">{{ nutrientSignLabel(n.sign) }}</span>
                      </td>
                      <td class="py-1 text-right">
                        @if (!n.available || n.percentile === null) { Información no disponible }
                        @else { {{ n.percentile | number:'1.0-0' }} }
                      </td>
                      <td class="py-1 text-right">
                        @if (!n.available || n.contribution === null) { Información no disponible }
                        @else { {{ n.contribution | number:'1.0-1' }} }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            }
          </section>

          <section class="rounded-xl bg-paper p-5 ring-1 ring-sand">
            <div class="anaquel-photo relative flex h-64 items-center justify-center overflow-hidden rounded-lg">
              @if (p.imageUrl) {
                <img [src]="p.imageUrl" [alt]="displayName(p)" class="h-full w-full object-contain" />
              } @else {
                <app-category-mark [category]="p.category" size="lg" class="mark-float" />
              }
              <div class="pointer-events-none absolute bottom-2 left-2 right-2">
                <app-shelf-stamps [labels]="p.labels" [compact]="true" />
              </div>
            </div>
            <div class="mt-4 flex flex-wrap gap-2">
              <button type="button" class="cta-brick rounded-lg bg-brick px-4 py-2 text-white" (click)="cart.add(p.code)">
                Agregar al carrito
              </button>
              <button type="button" class="cta-shelf rounded-lg bg-ink px-4 py-2 text-cream" (click)="compare.toggle(p.code)">
                {{ compare.has(p.code) ? 'Quitar de comparación' : 'Comparar' }}
              </button>
              <a routerLink="/comparar" class="rounded-lg px-4 py-2 ring-1 ring-sand">Ver comparación</a>
            </div>
          </section>
        </div>

        <section class="rounded-xl bg-paper p-5 ring-1 ring-sand">
          <h2 class="text-lg font-semibold">Nutrición por 100 g</h2>
          <table class="mt-3 w-full text-sm">
            @for (n of p.nutrients; track n.key) {
              <tr class="border-t border-sand">
                <td class="py-2">{{ n.label }}</td>
                <td class="py-2 text-right">
                  @if (n.per100g === null) { No disponible } @else { {{ n.per100g }} {{ n.unit }} }
                </td>
                <td class="py-2 text-right"><app-provenance-badge [status]="n.status" /></td>
              </tr>
            }
          </table>
        </section>

        <section class="grid gap-4 md:grid-cols-3">
          <div class="rounded-xl bg-paper p-5 ring-1 ring-sand">
            <h3 class="font-semibold">Ingredientes</h3>
            <p class="mt-2 text-sm">{{ p.ingredients.length ? p.ingredients.join(', ') : 'No disponibles' }}</p>
          </div>
          <div class="rounded-xl bg-paper p-5 ring-1 ring-sand">
            <h3 class="font-semibold">Alérgenos</h3>
            @if (p.allergens.length) {
              <div class="mt-3">
                <app-shelf-stamps [allergens]="p.allergens" />
              </div>
            } @else {
              <p class="mt-2 text-sm">Alérgenos no disponibles en el registro · no verificable</p>
            }
          </div>
          <div class="rounded-xl bg-paper p-5 ring-1 ring-sand">
            <h3 class="font-semibold">Sellos</h3>
            @if (p.labels.length) {
              <div class="mt-3">
                <app-shelf-stamps [labels]="p.labels" />
              </div>
            } @else {
              <p class="mt-2 text-sm">Sellos no disponibles en el registro. No se puede determinar.</p>
            }
          </div>
        </section>
      </article>
    } @else if (missing()) {
      <p>No encontramos ese código en el catálogo.</p>
    } @else {
      <p class="text-mute">Cargando ficha…</p>
    }
  `,
})
export class ProductPage {
  private readonly repo = inject(ProductRepository);
  private readonly route = inject(ActivatedRoute);
  private readonly profile = inject(ProfileStore);
  readonly cart = inject(CartStore);
  readonly compare = inject(CompareStore);
  readonly displayName = displayName;
  readonly priceCaption = priceCaption;
  readonly scoreCaption = scoreCaption;
  readonly categoryLabel = categoryLabel;
  readonly allergyLabel = allergyLabel;
  readonly dietLabel = dietLabel;
  readonly dimensionLabel = dimensionLabel;
  readonly flagLabel = flagLabel;
  readonly nutrientD1Label = nutrientD1Label;
  readonly nutrientSignLabel = nutrientSignLabel;

  private readonly code = toSignal(this.route.paramMap.pipe(map((p) => p.get('code') ?? '')), {
    initialValue: '',
  });

  private readonly loaded = toSignal(
    toObservable(this.code).pipe(
      switchMap((code) =>
        this.repo.explain(code, this.profile.profile()).pipe(
          tap((product) => {
            if (product) {
              this.repo.logEvent('product_viewed', { code: product.code }).subscribe();
            }
          }),
          map((product) => ({ product, missing: !product })),
          catchError(() => of({ product: undefined, missing: true })),
        ),
      ),
    ),
    { initialValue: { product: undefined, missing: false } },
  );

  readonly product = computed(() => this.loaded().product);
  readonly missing = computed(() => this.loaded().missing);
}
