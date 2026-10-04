import { Component, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { catchError, map, of, startWith, switchMap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { CatalogPageResult, ProductRepository } from '../core/data/product.repository';
import { CategoryMark } from '../shared/category-mark/category-mark';
import { LoadingWell } from '../shared/loading-well/loading-well';
import { OtterGuide } from '../shared/otter-guide/otter-guide';
import { ProductCard } from '../shared/product-card/product-card';
import { formatCount } from '../shared/format';
import {
  CATALOG_COPY,
  CATALOG_PAGE_SIZE,
  catalogCanGoBack,
  catalogCanGoNext,
  catalogQueryParams,
  parseCatalogQuery,
} from './catalog.query';

type CatalogView =
  | { kind: 'loading'; query: ReturnType<typeof parseCatalogQuery> }
  | { kind: 'error'; query: ReturnType<typeof parseCatalogQuery> }
  | { kind: 'ok'; query: ReturnType<typeof parseCatalogQuery>; page: CatalogPageResult };

@Component({
  selector: 'app-catalog-page',
  imports: [FormsModule, CategoryMark, LoadingWell, OtterGuide, ProductCard],
  template: `
    <section class="catalog">
      <header class="catalog-hero">
        <p class="catalog-kicker">{{ copy.kicker }}</p>
        <h1 class="catalog-title">{{ copy.title }}</h1>
      </header>

      <div class="catalog-meet">
        <app-otter-guide variant="search" size="compact" [caption]="copy.nuti" />
        @if (view(); as s) {
          @if (s.kind === 'ok') {
            <p class="catalog-count">
              <strong>{{ formatCount(s.page.total) }}</strong>
              {{ countSuffix(s.page.total) }}
            </p>
          }
        }
      </div>

      <form class="catalog-search" (ngSubmit)="aplicarBusqueda()">
        <label class="sr-only" for="catalog-search">{{ copy.searchLabel }}</label>
        <input
          id="catalog-search"
          name="catalogSearch"
          class="catalog-search-field"
          [placeholder]="copy.searchPlaceholder"
          [(ngModel)]="searchDraft"
        />
        <button type="submit" class="btn btn-tide">{{ copy.search }}</button>
      </form>

      <section class="catalog-cats" [attr.aria-label]="copy.categories">
        <h2 class="catalog-cats-kicker">{{ copy.categories }}</h2>
        <div class="catalog-facets">
          @for (cat of categories(); track cat.id) {
            <button
              type="button"
              class="choice-chip catalog-facet"
              [attr.aria-pressed]="query().category === cat.id"
              (click)="elegirCategoria(cat.id)"
            >
              @if (cat.id) {
                <app-category-mark [category]="facetMark(cat.id)" />
              }
              {{ cat.name }}
            </button>
          }
        </div>
      </section>

      @if (view(); as s) {
        @if (s.kind === 'loading') {
          <app-loading-well [label]="copy.loading" />
          <div class="catalog-grid" aria-hidden="true">
            @for (slot of skeletons; track slot) {
              <div class="catalog-skel card-paper"></div>
            }
          </div>
        } @else if (s.kind === 'error') {
          <div class="empty-well">
            <p>{{ copy.error }}</p>
            <button type="button" class="btn btn-tide" (click)="reintentar()">{{ copy.errorAction }}</button>
          </div>
        } @else if (!s.page.items.length) {
          <div class="empty-well">
            <p>{{ copy.empty }}</p>
            <button type="button" class="btn btn-tide" (click)="verTodos()">{{ copy.emptyAction }}</button>
          </div>
        } @else {
          <div class="catalog-grid">
            @for (p of s.page.items; track p.code) {
              <app-product-card mode="catalog" [product]="p" (add)="cart.add($event)" />
            }
          </div>
          <nav class="catalog-pager" aria-label="Paginación del catálogo">
            <button
              type="button"
              class="btn btn-ghost"
              [disabled]="!canBack()"
              (click)="irPagina(query().page - 1)"
            >{{ copy.prev }}</button>
            <p class="catalog-page-mark">
              Página <strong>{{ s.page.page }}</strong> de {{ formatCount(s.page.totalPages) }}
            </p>
            <button
              type="button"
              class="btn btn-ghost"
              [disabled]="!canNext()"
              (click)="irPagina(query().page + 1)"
            >{{ copy.next }}</button>
          </nav>
        }
      }
    </section>
  `,
})
export class CatalogPage {
  private readonly repo = inject(ProductRepository);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  readonly cart = inject(CartStore);
  readonly copy = CATALOG_COPY;
  readonly formatCount = formatCount;
  readonly skeletons = [1, 2, 3, 4, 5, 6, 7, 8];

  searchDraft = this.route.snapshot.queryParamMap.get('q') ?? '';
  readonly retryTick = signal(0);

  readonly query = toSignal(
    this.route.queryParamMap.pipe(
      map((q) =>
        parseCatalogQuery({
          q: q.get('q'),
          categoria: q.get('categoria'),
          page: q.get('page'),
        }),
      ),
    ),
    {
      initialValue: parseCatalogQuery({
        q: this.route.snapshot.queryParamMap.get('q'),
        categoria: this.route.snapshot.queryParamMap.get('categoria'),
        page: this.route.snapshot.queryParamMap.get('page'),
      }),
    },
  );

  readonly categories = toSignal(
    this.repo.catalogCategories().pipe(catchError(() => of([]))),
    { initialValue: [{ id: '', name: 'Todas', count: 0 }] },
  );

  readonly view = toSignal(
    toObservable(computed(() => ({ query: this.query(), retry: this.retryTick() }))).pipe(
      switchMap(({ query }) =>
        this.repo
          .catalogProducts({
            search: query.search,
            category: query.category,
            page: query.page,
            pageSize: CATALOG_PAGE_SIZE,
          })
          .pipe(
            map((page) => ({ kind: 'ok' as const, query, page })),
            startWith({ kind: 'loading' as const, query }),
            catchError(() => of({ kind: 'error' as const, query })),
          ),
      ),
    ),
    { initialValue: { kind: 'loading', query: this.query() } satisfies CatalogView },
  );

  readonly canBack = computed(() => catalogCanGoBack(this.query().page));
  readonly canNext = computed(() => {
    const s = this.view();
    if (!s || s.kind !== 'ok') {
      return false;
    }
    return catalogCanGoNext(s.page.page, s.page.totalPages);
  });

  countSuffix(total: number): string {
    const cat = this.query().category;
    const name = this.categories().find((item) => item.id === cat)?.name;
    if (cat && name) {
      return `en ${name}`;
    }
    return total === 1 ? 'producto' : 'productos';
  }

  facetMark(id: string): string {
    return id.startsWith('__') ? '' : id;
  }

  aplicarBusqueda(): void {
    this.navegar({ ...this.query(), search: this.searchDraft.trim(), page: 1 });
  }

  elegirCategoria(id: string): void {
    this.navegar({ ...this.query(), category: id, page: 1 });
  }

  irPagina(page: number): void {
    this.navegar({ ...this.query(), page });
  }

  verTodos(): void {
    this.searchDraft = '';
    this.navegar({ search: '', category: '', page: 1 });
  }

  reintentar(): void {
    this.retryTick.update((n) => n + 1);
  }

  private navegar(query: ReturnType<typeof parseCatalogQuery>): void {
    void this.router.navigate(['/catalogo'], {
      queryParams: catalogQueryParams(query),
    });
  }
}
