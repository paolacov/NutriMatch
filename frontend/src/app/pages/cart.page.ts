import { Component, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, map, of, startWith, switchMap, tap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { ProductRepository } from '../core/data/product.repository';
import { ProfileStore } from '../core/data/profile.store';
import { GroupBucket } from '../core/models/domain';
import { LoadingWell } from '../shared/loading-well/loading-well';
import { OtterGuide } from '../shared/otter-guide/otter-guide';
import { PlatoDish } from '../shared/plato-dish/plato-dish';
import { CartAlternatives } from './cart-alternatives';
import { displayName, priceAmount, priceKindLabel } from '../shared/format';
import {
  cartAlertBoard,
  cartAmountLabel,
  cartLegend,
  cartMoney,
  cartMoneyGap,
  cartMoneyNote,
  cartVariety,
  groupSentence,
  groupsPresentLine,
  sharePercent,
} from './cart.query';

const GROUP_MARK: Record<string, string> = {
  frutas_verduras: '🥦',
  cereales: '🌾',
  leguminosas_aoa: '🫘',
  unclassified: '·',
};

const FACT_THIN = 'Nuti no pudo armar un dato curioso en este momento.';

type FactView = { kind: 'loading' } | { kind: 'error' } | { kind: 'ok'; text: string } | { kind: 'thin' };

@Component({
  selector: 'app-cart-page',
  imports: [RouterLink, PlatoDish, OtterGuide, LoadingWell, CartAlternatives],
  template: `
    <section class="cart-page">
      <header class="cart-intro">
        <div class="cart-intro-main">
          <app-otter-guide variant="empty_cart" size="mini" [showLine]="false" />
          <div>
            <h1 class="page-title">🛒 Mi carrito</h1>
            <p class="cart-lead">Revisa tus productos y cómo se reparten.</p>
          </div>
        </div>
        <aside class="cart-total-chip" aria-label="Total del carrito">
          <p class="cart-total-kicker">Total del carrito</p>
          @if (view(); as head) {
            @if (head.kind === 'loading') {
              <p class="cart-total">…</p>
            } @else if (head.kind === 'empty') {
              <p class="cart-total">$0.00 MXN</p>
            } @else if (money().amount === null) {
              <p class="cart-total-missing">Total no disponible.</p>
            } @else {
              <p class="cart-total">{{ amountLabel() }}</p>
              @if (legend(); as leyenda) {
                <p class="price-badge cart-total-legend" [attr.data-price-kind]="legendKind()">{{ leyenda }}</p>
              }
            }
          }
          @if (moneyNote(); as note) {
            <p class="cart-note">{{ note }}</p>
          }
          @if (moneyGap(); as gap) {
            <p class="cart-note">{{ gap }}</p>
          }
        </aside>
      </header>

      @if (view(); as v) {
        @if (v.kind === 'loading') {
          <app-loading-well label="Cargando carrito…" />
        } @else if (v.kind === 'empty') {
          <div class="empty-well">
            <app-otter-guide variant="empty_cart" size="compact" [showLine]="false" />
            <p>Tu carrito está vacío. Cuando agregues productos, vemos cómo se reparten.</p>
            <a routerLink="/recomendaciones" class="btn btn-tide">Agregar desde recomendaciones</a>
          </div>
          <section class="card-paper cart-section cart-alert">
            <div class="cart-alert-head">
              <app-otter-guide variant="alert" size="mini" [showLine]="false" />
              <div>
                <h2 class="cart-heading">Alertas de tu carrito</h2>
                <p class="cart-alert-kicker">Nuti</p>
                <p>Agrega algunos productos y aquí podrás observar cómo se distribuye tu carrito.</p>
              </div>
            </div>
          </section>
        } @else {
          <section class="card-paper cart-section">
            <ul class="cart-list">
              @for (p of v.items; track p.code) {
                <li class="cart-item">
                  <div class="cart-row">
                    <div>
                      <a [routerLink]="['/producto', p.code]" class="font-semibold underline">{{ displayName(p) }}</a>
                      <p class="text-sm text-mute cart-price-line">
                        <span>{{ p.brand.value?.trim() || 'Marca no disponible' }} · {{ priceAmount(p) ?? 'Precio no disponible' }}</span>
                        @if (p.price.status === 'REAL' || p.price.status === 'SYNTHETIC') {
                          <span class="price-badge" [attr.data-price-kind]="p.price.status">{{ priceKindLabel(p) }}</span>
                        }
                      </p>
                    </div>
                    <div class="cart-actions">
                      <button
                        type="button"
                        class="btn btn-sm"
                        [class.btn-tide]="openCode() !== p.code"
                        [class.btn-ghost]="openCode() === p.code"
                        [attr.aria-expanded]="openCode() === p.code"
                        (click)="explorar(p.code)"
                      >
                        {{ openCode() === p.code ? 'Cerrar alternativas' : 'Explorar alternativas' }}
                      </button>
                      <button type="button" class="btn btn-vest btn-sm" (click)="cart.remove(p.code)">Quitar</button>
                    </div>
                  </div>
                  @if (openCode() === p.code) {
                    <app-cart-alternatives [code]="p.code" />
                  }
                </li>
              }
            </ul>
          </section>

          @if (summary(); as s) {
            <section class="card-paper cart-section">
              <div class="cart-story-head">
                <app-otter-guide variant="explain" size="mini" [showLine]="false" />
                <div>
                  <h2 class="cart-heading">🍽️ Plato del Buen Comer</h2>
                  <p class="cart-lead">Nuti te cuenta cómo leer tu carrito.</p>
                </div>
              </div>
              <div class="cart-story">
                <p>
                  <strong>¿Cómo se compone?</strong> Verduras y frutas, cereales, y leguminosas y alimentos de origen
                  animal. El vasito de agua acompaña la guía.
                </p>
              </div>

              <div class="cart-plato-split">
                <div class="cart-plato-visual">
                  <app-plato-dish
                    [buckets]="s.plato"
                    [products]="v.items"
                    [selectedKey]="focusKey()"
                    (select)="elegirGajo($event)"
                  />
                </div>
                <div class="cart-plato-side">
                  <p class="cart-lead">{{ groupsPresentLine(variety().groups) }} El porcentaje cuenta productos, no gramos.</p>
                  <ul class="cart-groups">
                    @for (row of s.plato; track row.key) {
                      <li
                        class="cart-group"
                        [class.is-on]="focusKey() === row.key"
                        [class.is-empty]="row.n === 0"
                        [attr.data-key]="row.key"
                      >
                        <button type="button" class="cart-group-btn" (click)="elegirGajo(row.key)">
                          <span class="cart-group-mark" aria-hidden="true">{{ mark(row.key) }}</span>
                          <span class="cart-group-copy">
                            <strong>{{ groupLabel(row) }}</strong>
                            <span class="cart-group-count">{{ row.n }} {{ row.n === 1 ? 'producto' : 'productos' }}</span>
                            @if (sharePercent(row, s.nProducts); as pct) {
                              <span class="cart-group-bar" aria-hidden="true"><span [style.width.%]="pct"></span></span>
                            }
                          </span>
                          @if (sharePercent(row, s.nProducts); as pct) {
                            <span class="cart-group-share">{{ pct }}%</span>
                          }
                        </button>
                        <p>{{ groupSentence(row) }}</p>
                      </li>
                    }
                  </ul>
                  @if (focusedItems().length) {
                    <ul class="plato-focus">
                      @for (item of focusedItems(); track item.code) {
                        <li>
                          <a [routerLink]="['/producto', item.code]">{{ displayName(item) }}</a>
                        </li>
                      }
                    </ul>
                  }
                  <div class="cart-variety" aria-label="Variedad del carrito">
                    <p>{{ variety().groups }} {{ variety().groups === 1 ? 'grupo presente' : 'grupos presentes' }}</p>
                    <p>{{ variety().categories }} {{ variety().categories === 1 ? 'categoría diferente' : 'categorías diferentes' }}</p>
                    <p>{{ variety().products }} {{ variety().products === 1 ? 'producto en total' : 'productos en total' }}</p>
                  </div>
                </div>
              </div>
            </section>

            <section class="card-paper cart-section cart-fact">
              <h2 class="cart-heading">💡 ¿Sabías que...?</h2>
              <div class="cart-fact-row">
                <app-otter-guide variant="explain" size="compact" [showLine]="false" />
                <div>
                  <p class="cart-fact-kicker">Nuti</p>
                  @if (fact(); as row) {
                    @if (row.kind === 'loading') {
                      <p>Estoy preparando un dato de alimentación…</p>
                    } @else if (row.kind === 'error') {
                      <p>{{ factThin }}</p>
                    } @else if (row.kind === 'thin') {
                      <p>{{ factThin }}</p>
                    } @else {
                      <p>{{ row.text }}</p>
                    }
                  }
                  <button type="button" class="btn btn-ghost btn-sm" (click)="otroDato()">✨ Otro dato curioso</button>
                </div>
              </div>
            </section>

            @if (alertBoard(); as board) {
              <section class="card-paper cart-section cart-alert">
                <div class="cart-alert-head">
                  <app-otter-guide variant="alert" size="mini" [showLine]="false" />
                  <div>
                    <h2 class="cart-heading">Alertas de tu carrito</h2>
                    <p class="cart-alert-kicker">Nuti tiene algo que contarte</p>
                  </div>
                </div>
                <p class="cart-alert-line">{{ board.headline }}</p>
                <ul class="cart-alert-list">
                  @for (group of board.groups; track group.key) {
                    <li class="cart-alert-row" [class.is-on]="group.present">
                      <span class="cart-alert-emoji" aria-hidden="true">{{ mark(group.key) }}</span>
                      <span class="cart-alert-copy">
                        <strong>{{ group.label }}</strong>
                        <span>{{ group.detail }}</span>
                      </span>
                      <span class="cart-alert-mark" [attr.aria-label]="group.present ? 'Con productos' : 'Sin productos'">
                        {{ group.present ? '✓' : '·' }}
                      </span>
                    </li>
                  }
                </ul>
                @if (board.footnote) {
                  <p class="cart-alert-foot">{{ board.footnote }}</p>
                }
                @if (board.cheer) {
                  <p class="cart-alert-cheer">✨ ¡Sigue explorando tu carrito!</p>
                }
                <a routerLink="/alertas" class="btn btn-ghost btn-sm">Sellos y alergias</a>
              </section>
            }
          }
        }
      }
    </section>
  `,
})
export class CartPage {
  readonly cart = inject(CartStore);
  private readonly repo = inject(ProductRepository);
  private readonly profiles = inject(ProfileStore);
  readonly displayName = displayName;
  readonly priceAmount = priceAmount;
  readonly priceKindLabel = priceKindLabel;
  readonly groupSentence = groupSentence;
  readonly groupsPresentLine = groupsPresentLine;
  readonly sharePercent = sharePercent;
  readonly factThin = FACT_THIN;
  readonly focusKey = signal<string | null>(null);
  readonly factSlot = signal(0);
  readonly openCode = signal<string | null>(null);

  readonly view = toSignal(
    toObservable(this.cart.codes).pipe(
      tap(() => {
        this.focusKey.set(null);
        this.factSlot.set(0);
      }),
      switchMap((codes) => {
        if (!codes.length) {
          return of({ kind: 'empty' as const, items: [] });
        }
        return this.repo.byCodes(codes).pipe(
          map((items) => ({ kind: 'ok' as const, items })),
          startWith({ kind: 'loading' as const, items: [] }),
        );
      }),
    ),
    { initialValue: this.cart.codes().length ? { kind: 'loading' as const, items: [] } : { kind: 'empty' as const, items: [] } },
  );

  readonly summary = toSignal(
    toObservable(this.cart.codes).pipe(switchMap((codes) => (codes.length ? this.repo.cartSummary(codes) : of(null)))),
  );

  readonly money = computed(() => {
    const view = this.view();
    return cartMoney(view.kind === 'ok' ? view.items : []);
  });

  readonly moneyNote = computed(() => cartMoneyNote(this.money()));
  readonly moneyGap = computed(() => cartMoneyGap(this.money()));

  readonly variety = computed(() => {
    const summary = this.summary();
    return summary ? cartVariety(summary) : { groups: 0, categories: 0, products: 0 };
  });

  readonly alertBoard = computed(() => {
    const summary = this.summary();
    return summary ? cartAlertBoard(summary) : null;
  });

  groupLabel(row: GroupBucket): string {
    if (row.key === 'unclassified') {
      return 'No clasificado';
    }
    return row.label;
  }

  private readonly factTick = computed(() => ({
    codes: this.cart.codes(),
    slot: this.factSlot(),
  }));

  readonly fact = toSignal(
    toObservable(this.factTick).pipe(
      switchMap((tick) => {
        if (!tick.codes.length) {
          return of(null);
        }
        const start = tick.slot % tick.codes.length;
        const codes = tick.codes.slice(start).concat(tick.codes.slice(0, start));
        return this.repo
          .askAi({
            surface: 'cart',
            codes,
            profile: this.profiles.profile(),
            intent: 'fun_fact',
            message: `Dato curioso. Variante ${tick.slot}.`,
          })
          .pipe(
            map((row) => this.leerDato(row.text)),
            startWith({ kind: 'loading' } satisfies FactView),
            catchError(() => of({ kind: 'error' } satisfies FactView)),
          );
      }),
    ),
    { initialValue: null },
  );

  amountLabel(): string {
    return cartAmountLabel(this.money());
  }

  legend(): string {
    return cartLegend(this.money());
  }

  legendKind(): string {
    const money = this.money();
    if (money.realCount > 0 && money.demoCount > 0) {
      return 'MIXED';
    }
    if (money.demoCount > 0) {
      return 'SYNTHETIC';
    }
    return 'REAL';
  }

  mark(key: string): string {
    return GROUP_MARK[key] ?? '·';
  }

  focusedItems() {
    const key = this.focusKey();
    const summary = this.summary();
    const view = this.view();
    if (!key || !summary || view.kind !== 'ok') {
      return [];
    }
    const bucket = summary.plato.find((row) => row.key === key);
    if (!bucket) {
      return [];
    }
    const wanted = new Set(bucket.codes);
    return view.items.filter((item) => wanted.has(item.code));
  }

  elegirGajo(key: string): void {
    this.focusKey.update((actual) => (actual === key ? null : key));
  }

  explorar(code: string): void {
    this.openCode.update((actual) => (actual === code ? null : code));
  }

  otroDato(): void {
    this.factSlot.update((slot) => slot + 1);
  }

  private leerDato(text: string): FactView {
    const limpio = text.trim();
    if (!limpio || limpio.toLowerCase().includes('no encontró suficiente') || limpio.toLowerCase().includes('no tiene un atributo observado')) {
      return { kind: 'thin' };
    }
    return { kind: 'ok', text: limpio };
  }
}
