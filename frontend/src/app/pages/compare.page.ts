import { DecimalPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { combineLatest, forkJoin, of } from 'rxjs';
import { catchError, map, switchMap } from 'rxjs';
import { CompareStore } from '../core/data/compare.store';
import { ProductRepository } from '../core/data/product.repository';
import { ProfileStore } from '../core/data/profile.store';
import { Product } from '../core/models/domain';
import { BandChip } from '../shared/band-chip/band-chip';
import { CategoryMark } from '../shared/category-mark/category-mark';
import { ProvenanceBadge } from '../shared/provenance-badge/provenance-badge';
import { ShelfStamps } from '../shared/shelf-stamps/shelf-stamps';
import {
  allergyLabel,
  categoryLabel,
  dietLabel,
  dimensionLabel,
  displayName,
  priceCaption,
} from '../shared/format';

type Tone = 'hi' | 'lo' | null;

@Component({
  selector: 'app-compare-page',
  imports: [DecimalPipe, RouterLink, BandChip, CategoryMark, ProvenanceBadge, ShelfStamps],
  template: `
    <section class="space-y-6">
      <h1 class="text-3xl font-bold">Comparar</h1>
      <p class="text-sm text-mute">
        Hasta 3 productos. Las diferencias son visuales; no hay un algoritmo de comparación ni un ganador.
      </p>
      @if (!compare.codes().length) {
        <p>Aún no hay productos en comparación. Ábrelos desde una ficha y pulsa Comparar.</p>
        <a routerLink="/recomendaciones" class="text-brick underline">Ir a recomendaciones</a>
      } @else if (!products().length) {
        <p class="text-mute">Cargando comparación…</p>
      } @else {
        <div class="overflow-x-auto">
          <div class="compare-grid" [style.--n]="products().length">
            @for (p of products(); track p.code) {
              <article class="rounded-2xl bg-paper p-4 ring-1 ring-sand">
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
                  <app-provenance-badge [status]="p.fit.status" />
                </div>
                <div class="mt-3">
                  <app-shelf-stamps [labels]="p.labels" [compact]="true" />
                </div>

                <p class="compare-metric mt-4" [attr.data-tone]="tone(scores(), p.fit.score)">
                  <span class="text-xs text-mute">Score</span>
                  <strong>
                    @if (p.fit.score === null) { — } @else { {{ p.fit.score | number:'1.0-1' }} }
                  </strong>
                </p>
                <ul class="mt-2 grid grid-cols-3 gap-1 text-center text-xs">
                  <li class="compare-metric" [attr.data-tone]="tone(d1s(), p.fit.d1)">
                    {{ dimensionLabel('D1') }}<br />
                    <strong>{{ p.fit.d1 === null ? '—' : (p.fit.d1 | number:'1.0-1') }}</strong>
                  </li>
                  <li class="compare-metric" [attr.data-tone]="tone(d2s(), p.fit.d2)">
                    {{ dimensionLabel('D2') }}<br />
                    <strong>{{ p.fit.d2 === null ? '—' : (p.fit.d2 | number:'1.0-1') }}</strong>
                  </li>
                  <li class="compare-metric" [attr.data-tone]="tone(d3s(), p.fit.d3)">
                    {{ dimensionLabel('D3') }}<br />
                    <strong>{{ p.fit.d3 === null ? '—' : (p.fit.d3 | number:'1.0-1') }}</strong>
                  </li>
                </ul>
                <p class="mt-2 text-xs text-mute">
                  Alergia: {{ allergyLabel(p.fit.allergyStatus) }} · Dieta: {{ dietLabel(p.fit.dietStatus) }}
                </p>
                <p class="mt-3 text-sm">{{ priceCaption(p) }}</p>
                <app-provenance-badge [status]="p.price.status" />

                <h3 class="mt-4 text-sm font-semibold">Por 100 g</h3>
                <ul class="mt-1 text-sm">
                  @for (key of nutrientKeys; track key) {
                    <li class="compare-row" [attr.data-tone]="tone(nutrientValues(key), nutrientValue(p, key))">
                      <span>{{ nutrientLabel(key) }}</span>
                      <span>
                        @if (nutrientValue(p, key) === null) { Información no disponible }
                        @else { {{ nutrientValue(p, key) | number:'1.0-1' }} }
                      </span>
                    </li>
                  }
                </ul>

                <button type="button" class="mt-4 text-sm text-brick" (click)="compare.remove(p.code)">
                  Quitar
                </button>
              </article>
            }
          </div>
        </div>
        <app-provenance-badge status="DERIVED" />
      }
    </section>
  `,
})
export class ComparePage {
  readonly compare = inject(CompareStore);
  private readonly repo = inject(ProductRepository);
  private readonly profile = inject(ProfileStore);
  readonly displayName = displayName;
  readonly priceCaption = priceCaption;
  readonly categoryLabel = categoryLabel;
  readonly allergyLabel = allergyLabel;
  readonly dietLabel = dietLabel;
  readonly dimensionLabel = dimensionLabel;
  readonly nutrientKeys = ['energy', 'proteins', 'carbohydrates', 'sugars', 'fat', 'fiber', 'salt'];

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

  nutrientValue(product: Product, key: string): number | null {
    return product.nutrients.find((n) => n.key === key)?.per100g ?? null;
  }

  nutrientValues(key: string): (number | null)[] {
    return this.products().map((p) => this.nutrientValue(p, key));
  }

  nutrientLabel(key: string): string {
    return this.products()[0]?.nutrients.find((n) => n.key === key)?.label ?? key;
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
