import { Component, computed, inject } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { catchError, map, of, startWith, switchMap, tap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { ProductRepository } from '../core/data/product.repository';
import { BarcodeScan } from '../shared/barcode-scan/barcode-scan';
import { LoadingWell } from '../shared/loading-well/loading-well';
import { OtterGuide } from '../shared/otter-guide/otter-guide';
import { ProductCard } from '../shared/product-card/product-card';

function onlyDigits(value: string): string {
  return value.replace(/\D/g, '');
}

function asGtin(value: string): string | null {
  const digits = onlyDigits(value);
  return /^\d{8,14}$/.test(digits) ? digits : null;
}

@Component({
  selector: 'app-search-page',
  imports: [FormsModule, RouterLink, OtterGuide, ProductCard, LoadingWell, BarcodeScan],
  template: `
    <section class="space-y-6">
      <p class="page-kicker">Descubrir</p>
      <h1 class="page-title">Buscar o escanear</h1>
      @if (scanMode()) {
        <app-otter-guide variant="scan" />
        <app-barcode-scan [showNameSearch]="false" />
      } @else {
        <app-otter-guide variant="search" />
      }

      @if (!scanMode()) {
        <form class="flex flex-col gap-3 sm:flex-row" (ngSubmit)="aplicar()">
          <input
            class="field-paper flex-1 px-5 py-3"
            placeholder="Nombre o código de barras"
            [(ngModel)]="query"
            name="q"
          />
          <button type="submit" class="btn btn-tide">Buscar</button>
        </form>
      }

      @if (state(); as s) {
        @if (s.kind === 'idle') {
          @if (!scanMode()) {
            <p class="text-mute">Escribe un nombre o código para buscar en el anaquel.</p>
          }
        } @else if (s.kind === 'loading') {
          <app-loading-well label="Buscando…" />
        } @else if (s.kind === 'miss') {
          <div class="empty-well">
            <app-otter-guide variant="empty" size="compact" />
            <p>Este código no está en el snapshot México.</p>
            <a routerLink="/buscar" class="btn btn-tide">Buscar por nombre</a>
          </div>
        } @else if (s.kind === 'empty') {
          <div class="empty-well">
            <app-otter-guide variant="empty" size="compact" />
            <p>Sin resultados para «{{ s.query }}».</p>
          </div>
        } @else {
          <div class="shelf-grid">
            @for (p of s.items; track p.code) {
              <app-product-card [product]="p" (add)="cart.add($event)" />
            }
          </div>
        }
      }
    </section>
  `,
})
export class SearchPage {
  private readonly repo = inject(ProductRepository);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  readonly cart = inject(CartStore);

  private readonly params = toSignal(
    this.route.queryParamMap.pipe(
      map((q) => ({
        q: q.get('q') ?? '',
        modo: q.get('modo') ?? '',
      })),
    ),
    { initialValue: { q: '', modo: '' } },
  );

  query = this.params().q;
  readonly scanMode = computed(() => this.params().modo === 'escanear');
  readonly state = toSignal(
    toObservable(computed(() => this.params().q)).pipe(
      switchMap((q) => {
        const query = q.trim();
        if (!query) {
          return of({ kind: 'idle' as const, items: [], query });
        }
        const gtin = asGtin(query);
        if (gtin) {
          return this.repo.byCode(gtin).pipe(
            tap((product) => {
              if (product) {
                void this.router.navigate(['/producto', product.code]);
              }
            }),
            map((product) =>
              product
                ? { kind: 'ok' as const, items: [product], query: gtin }
                : { kind: 'miss' as const, items: [], query: gtin },
            ),
            startWith({ kind: 'loading' as const, items: [], query: gtin }),
            catchError(() => of({ kind: 'miss' as const, items: [], query: gtin })),
          );
        }
        return this.repo.search(query).pipe(
          map((items) =>
            items.length
              ? { kind: 'ok' as const, items, query }
              : { kind: 'empty' as const, items, query },
          ),
          startWith({ kind: 'loading' as const, items: [], query }),
          catchError(() => of({ kind: 'empty' as const, items: [], query })),
        );
      }),
    ),
    { initialValue: { kind: 'idle' as const, items: [], query: '' } },
  );

  aplicar(): void {
    const gtin = asGtin(this.query);
    void this.router.navigate([], {
      queryParams: { q: gtin ?? this.query.trim() },
      queryParamsHandling: 'merge',
    });
  }
}
