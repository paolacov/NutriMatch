import { DecimalPipe } from '@angular/common';
import { Component, inject } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { ProductRepository } from '../core/data/product.repository';
import { GroupBucket } from '../core/models/domain';
import { PlatoDish } from '../shared/plato-dish/plato-dish';
import { ProvenanceBadge } from '../shared/provenance-badge/provenance-badge';
import { categoryLabel, displayName, formatPrice } from '../shared/format';

@Component({
  selector: 'app-cart-page',
  imports: [DecimalPipe, RouterLink, PlatoDish, ProvenanceBadge],
  template: `
    <section class="space-y-6">
      <h1 class="text-3xl font-bold">Carrito</h1>
      @if (!items().length) {
        <p>Tu carrito está vacío.</p>
        <a routerLink="/recomendaciones" class="text-brick underline">Agregar desde recomendaciones</a>
      } @else {
        <ul class="space-y-3">
          @for (p of items(); track p.code) {
            <li class="flex items-center justify-between rounded-2xl bg-paper p-4 ring-1 ring-sand">
              <div>
                <a [routerLink]="['/producto', p.code]" class="font-semibold underline">{{ displayName(p) }}</a>
                <p class="text-sm text-mute">{{ p.brand.value }} · {{ formatPrice(p) }}</p>
              </div>
              <button type="button" class="text-sm text-brick" (click)="cart.remove(p.code)">Quitar</button>
            </li>
          }
        </ul>

        <div class="flex gap-2 text-sm">
          <button type="button" class="rounded-full px-3 py-1 ring-1 ring-sand" [class.bg-paper]="tab === 'plato'" (click)="tab = 'plato'">Plato del Bien Comer</button>
          <button type="button" class="rounded-full px-3 py-1 ring-1 ring-sand" [class.bg-paper]="tab === 'cats'" (click)="tab = 'cats'">Por categorías</button>
        </div>

        @if (summary(); as s) {
          <section class="rounded-2xl bg-paper p-5 ring-1 ring-sand">
            <div class="flex flex-wrap items-center gap-2">
              <h2 class="font-semibold">Resumen agregado</h2>
              <app-provenance-badge [status]="s.status" />
            </div>
            <p class="mt-2 text-sm text-mute">{{ s.methodNote }}</p>
            <p class="text-xs text-mute">El precio no entra en este resumen.</p>

            @if (tab === 'plato') {
              <p class="mt-3 text-sm text-mute">
                Vista informativa. No es un juicio médico ni un plato prescrito. El porcentaje usa el número de productos, no los gramos.
              </p>
              <app-plato-dish class="mt-4 block" [buckets]="s.plato" />
            } @else {
              <ul class="mt-3 space-y-1 text-sm">
                @for (row of s.categories; track row.key) {
                  <li class="flex justify-between gap-3">
                    <span>{{ bucketLabel(row) }}</span>
                    <span class="text-mute">{{ row.n }} · {{ row.share * 100 | number:'1.0-0' }}%</span>
                  </li>
                }
              </ul>
            }

            <h3 class="mt-5 text-sm font-semibold">Nutrientes por 100 g</h3>
            <table class="mt-2 w-full text-left text-sm">
              <thead>
                <tr class="text-mute">
                  <th class="py-1 font-medium">Nutriente</th>
                  <th class="py-1 text-right font-medium">Valor</th>
                  <th class="py-1 text-right font-medium">Cobertura</th>
                </tr>
              </thead>
              <tbody>
                @for (n of s.nutrients; track n.key) {
                  <tr class="border-t border-sand">
                    <td class="py-1">{{ n.label }}</td>
                    <td class="py-1 text-right">
                      @if (n.value === null) { Información no disponible } @else { {{ n.value | number:'1.0-1' }} {{ n.unit }} }
                    </td>
                    <td class="py-1 text-right text-mute">{{ n.nWithData }}/{{ n.nProducts }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </section>
        }
      }
    </section>
  `,
})
export class CartPage {
  readonly cart = inject(CartStore);
  private readonly repo = inject(ProductRepository);
  readonly displayName = displayName;
  readonly formatPrice = formatPrice;
  tab: 'plato' | 'cats' = 'plato';

  readonly items = toSignal(
    toObservable(this.cart.codes).pipe(switchMap((codes) => this.repo.byCodes(codes))),
    { initialValue: [] },
  );

  readonly summary = toSignal(
    toObservable(this.cart.codes).pipe(switchMap((codes) => this.repo.cartSummary(codes))),
  );

  bucketLabel(row: GroupBucket): string {
    if (row.key === 'unclassified') {
      return 'no clasificado';
    }
    return categoryLabel(row.key);
  }
}
