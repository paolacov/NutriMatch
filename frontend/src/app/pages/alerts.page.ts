import { Component, computed, inject } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, combineLatest, forkJoin, map, of, switchMap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { ProductRepository } from '../core/data/product.repository';
import { ProfileStore } from '../core/data/profile.store';
import { Product } from '../core/models/domain';
import { allergyLabel, dietLabel, displayName } from '../shared/format';
import { OtterGuide } from '../shared/otter-guide/otter-guide';
import { ShelfStamps } from '../shared/shelf-stamps/shelf-stamps';

function excesoLabels(labels: string[]): string[] {
  return labels.filter((tag) => tag.includes('exceso'));
}

@Component({
  selector: 'app-alerts-page',
  imports: [RouterLink, OtterGuide, ShelfStamps],
  template: `
    <section class="space-y-6">
      <h1 class="text-3xl font-bold">Alertas</h1>
      <p class="text-sm text-mute">
        Los sellos son etiquetado frontal NOM-051. Informan; no diagnostican ni puntúan.
      </p>
      <app-otter-guide variant="alert" />

      @if (!cart.codes().length) {
        <p>El carrito está vacío. Aquí verás sellos de advertencia y el estado de alergia o dieta de cada producto.</p>
        <a routerLink="/carrito" class="text-brick underline">Ir al carrito</a>
      } @else if (!products().length) {
        <p class="text-mute">Cargando alertas…</p>
      } @else {
        <ul class="alert-summary">
          <li>{{ summary().conSellos }} con sellos NOM-051</li>
          <li>{{ summary().noApto }} no apto por alergia</li>
          <li>{{ summary().noVerificable }} alergia no verificable</li>
        </ul>

        <ul class="space-y-3">
          @for (p of products(); track p.code) {
            <li class="alert-card" [attr.data-alert]="cardTone(p)">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <a [routerLink]="['/producto', p.code]" class="font-semibold underline">
                    {{ displayName(p) }}
                  </a>
                  <p class="text-sm text-mute">{{ p.brand.value ?? 'Marca no disponible' }}</p>
                </div>
                <button type="button" class="text-sm text-brick" (click)="cart.remove(p.code)">
                  Quitar
                </button>
              </div>

              <div class="mt-3 flex flex-wrap gap-2">
                <span class="alert-state" [attr.data-state]="p.fit.allergyStatus">
                  Alergia: {{ allergyLabel(p.fit.allergyStatus) }}
                </span>
                @if (profile.profile().diet) {
                  <span class="alert-state" [attr.data-state]="p.fit.dietStatus">
                    Dieta: {{ dietLabel(p.fit.dietStatus) }}
                  </span>
                }
              </div>
              @if (!profile.profile().allergenTags.length) {
                <p class="mt-1 text-xs text-mute">Sin alergia en el perfil: no hay nada que filtrar.</p>
              }
              @if (!profile.profile().diet) {
                <p class="text-xs text-mute">Sin dieta en el perfil: no se afirma compatibilidad.</p>
              }

              @if (excesoLabels(p.labels).length || p.allergens.length) {
                <div class="mt-3">
                  <app-shelf-stamps
                    [labels]="excesoLabels(p.labels)"
                    [allergens]="p.allergens"
                    [highlightAllergens]="profile.profile().allergenTags"
                  />
                </div>
              } @else if (p.labels.length) {
                <p class="mt-3 text-sm text-mute">
                  Sin sellos de exceso NOM-051 en las etiquetas registradas.
                  Alérgenos no disponibles en el registro · no verificable.
                </p>
              } @else {
                <p class="mt-3 text-sm text-mute">
                  Sellos y alérgenos no disponibles en el registro. No se puede determinar.
                </p>
              }
            </li>
          }
        </ul>
      }
    </section>
  `,
})
export class AlertsPage {
  readonly cart = inject(CartStore);
  readonly profile = inject(ProfileStore);
  private readonly repo = inject(ProductRepository);
  readonly displayName = displayName;
  readonly allergyLabel = allergyLabel;
  readonly dietLabel = dietLabel;
  readonly excesoLabels = excesoLabels;

  readonly products = toSignal(
    combineLatest([toObservable(this.cart.codes), toObservable(this.profile.profile)]).pipe(
      switchMap(([codes, profile]) => {
        if (!codes.length) {
          return of([]);
        }
        return forkJoin(
          codes.map((code) => this.repo.explain(code, profile).pipe(catchError(() => of(undefined)))),
        ).pipe(map((rows) => rows.filter((p): p is Product => !!p)));
      }),
    ),
    { initialValue: [] },
  );

  readonly summary = computed(() => {
    const rows = this.products();
    return {
      conSellos: rows.filter((p) => excesoLabels(p.labels).length).length,
      noApto: rows.filter((p) => p.fit.allergyStatus === 'no_apto').length,
      noVerificable: rows.filter((p) => p.fit.allergyStatus === 'no_verificable').length,
    };
  });

  cardTone(product: Product): string {
    const diet = this.profile.profile().diet;
    if (product.fit.allergyStatus === 'no_apto' || (diet && product.fit.dietStatus === 'incompatible')) {
      return 'no_apto';
    }
    if (
      product.fit.allergyStatus === 'no_verificable' ||
      (diet && product.fit.dietStatus === 'no_verificable')
    ) {
      return 'no_verificable';
    }
    if (excesoLabels(product.labels).length) {
      return 'sello';
    }
    return 'ok';
  }
}
