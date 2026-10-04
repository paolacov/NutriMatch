import { Component, ElementRef, afterNextRender, computed, inject, input } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, map, of, startWith, switchMap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { AlternativesBundle, ProductRepository } from '../core/data/product.repository';
import { ProfileStore } from '../core/data/profile.store';
import { Product } from '../core/models/domain';
import { BandChip } from '../shared/band-chip/band-chip';
import { LoadingWell } from '../shared/loading-well/loading-well';
import {
  categoryLabel,
  dimensionLabel,
  displayName,
  priceAmount,
  priceKindLabel,
} from '../shared/format';

type AltView =
  | { kind: 'loading'; bundle: null }
  | { kind: 'error'; bundle: null }
  | { kind: 'ready'; bundle: AlternativesBundle };

@Component({
  selector: 'app-cart-alternatives',
  imports: [RouterLink, BandChip, LoadingWell],
  template: `
    <div class="alt-panel">
      @if (state(); as view) {
        @if (view.kind === 'loading') {
          <app-loading-well label="Buscando opciones del mismo grupo…" />
        } @else if (view.kind === 'error') {
          <p class="alt-note">No pude traer las alternativas. Tu carrito sigue igual.</p>
        } @else if (view.bundle.reason === 'sin_categoria') {
          <p class="alt-note">Este producto no tiene un grupo de referencia, así que no hay un conjunto comparable.</p>
        } @else if (view.bundle.reason === 'sin_opciones') {
          <p class="alt-note">
            En el grupo {{ categoryLabel(view.bundle.category) }} ninguna otra opción entra al ranking con tu perfil.
          </p>
        } @else {
          <div>
            <p class="alt-lead">Explora otras opciones</p>
            <p class="alt-note">
              Encontramos productos del grupo {{ categoryLabel(view.bundle.category) }} que puedes considerar según tus preferencias.
            </p>
            @if (view.bundle.total > view.bundle.items.length) {
              <p class="alt-note">Estas son las primeras {{ view.bundle.items.length }} de {{ view.bundle.total }}.</p>
            }
            <p class="alt-note">El precio se muestra y queda fuera del orden.</p>
            <p class="alt-note">Sustituir quita este producto del carrito y pone el de la tarjeta.</p>
          </div>
          <ul class="alt-grid">
            @for (item of view.bundle.items; track item.code; let first = $first) {
              <li class="alt-card" [class.is-first]="first">
                @if (first) {
                  <p class="alt-kicker">Según tus preferencias</p>
                }
                <div>
                  <a [routerLink]="['/producto', item.code]" class="font-semibold underline">{{ displayName(item) }}</a>
                  <p class="text-sm text-mute">{{ item.brand.value?.trim() || 'Marca no disponible' }}</p>
                </div>
                <p class="cart-price-line text-sm">
                  <span>{{ priceAmount(item) ?? 'Precio no disponible' }}</span>
                  @if (item.price.status === 'REAL' || item.price.status === 'SYNTHETIC') {
                    <span class="price-badge" [attr.data-price-kind]="item.price.status">{{ priceKindLabel(item) }}</span>
                  }
                </p>
                <div class="alt-score">
                  <p>
                    @if (item.fit.score === null) {
                      <strong>—</strong>
                    } @else {
                      <strong>{{ scoreText(item.fit.score) }}</strong>
                      <span>/100</span>
                    }
                  </p>
                  <app-band-chip [band]="item.fit.band" />
                </div>
                @if (item.fit.score !== null && !first) {
                  <p class="text-sm text-mute">Según tus preferencias</p>
                }
                <ul class="alt-dims">
                  @for (key of dims; track key) {
                    <li>
                      <span>{{ dimensionLabel(key) }}</span>
                      @if (dimValue(item, key) === null) {
                        <strong>Dato no disponible</strong>
                      } @else {
                        <strong class="alt-marks" [attr.aria-label]="scoreText(dimValue(item, key))">{{ marcas(dimValue(item, key)) }}</strong>
                      }
                    </li>
                  }
                </ul>
                <div class="alt-actions">
                  @if (cart.has(item.code)) {
                    <button type="button" class="btn btn-ghost btn-sm" disabled>En el carrito</button>
                  } @else {
                    <button type="button" class="btn btn-tide btn-sm" (click)="sustituir(item.code)">Sustituir</button>
                    <button type="button" class="btn btn-ghost btn-sm" (click)="cart.add(item.code)">Agregar</button>
                  }
                  <a class="btn btn-ghost btn-sm" [routerLink]="['/producto', item.code]">Ver producto</a>
                </div>
              </li>
            }
          </ul>
        }
      }
    </div>
  `,
})
export class CartAlternatives {
  readonly code = input.required<string>();
  readonly cart = inject(CartStore);
  private readonly repo = inject(ProductRepository);
  private readonly profiles = inject(ProfileStore);
  private readonly host = inject(ElementRef<HTMLElement>);
  readonly displayName = displayName;
  readonly priceAmount = priceAmount;
  readonly priceKindLabel = priceKindLabel;
  readonly categoryLabel = categoryLabel;
  readonly dimensionLabel = dimensionLabel;
  readonly dims = ['D1', 'D2', 'D3'] as const;

  private readonly query = computed(() => ({
    code: this.code(),
    profile: this.profiles.profile(),
  }));

  readonly state = toSignal(
    toObservable(this.query).pipe(
      switchMap(({ code, profile }) =>
        this.repo.alternatives(code, profile).pipe(
          map((bundle) => ({ kind: 'ready', bundle }) satisfies AltView),
          startWith({ kind: 'loading', bundle: null } satisfies AltView),
          catchError(() => of({ kind: 'error', bundle: null } satisfies AltView)),
        ),
      ),
    ),
    { initialValue: { kind: 'loading', bundle: null } satisfies AltView },
  );

  constructor() {
    afterNextRender(() => {
      this.host.nativeElement.scrollIntoView({ block: 'nearest' });
    });
  }

  sustituir(code: string): void {
    if (this.cart.has(code)) {
      return;
    }
    this.cart.replace(this.code(), code);
  }

  scoreText(value: number | null): string {
    if (value === null) {
      return '—';
    }
    return value.toLocaleString('es-MX', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  }

  marcas(value: number | null): string {
    if (value === null) {
      return '';
    }
    const filled = Math.min(5, Math.max(0, Math.round(value / 20)));
    return `${'●'.repeat(filled)}${'○'.repeat(5 - filled)}`;
  }

  dimValue(item: Product, key: 'D1' | 'D2' | 'D3'): number | null {
    if (key === 'D1') {
      return item.fit.d1;
    }
    if (key === 'D2') {
      return item.fit.d2;
    }
    return item.fit.d3;
  }
}
