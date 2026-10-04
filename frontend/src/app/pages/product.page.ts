import { DecimalPipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, combineLatest, map, of, switchMap, tap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { CompareStore } from '../core/data/compare.store';
import { ProductRepository } from '../core/data/product.repository';
import { ProfileStore } from '../core/data/profile.store';
import { Product } from '../core/models/domain';
import { BandChip } from '../shared/band-chip/band-chip';
import { CategoryMark } from '../shared/category-mark/category-mark';
import { LoadingWell } from '../shared/loading-well/loading-well';
import { OtterGuide } from '../shared/otter-guide/otter-guide';
import { ProductPhoto } from '../shared/product-photo/product-photo';
import { ShelfStamps, etiquetasDeSelloVisibles } from '../shared/shelf-stamps/shelf-stamps';
import {
  categoryLabel,
  dataQualityLevelName,
  displayName,
  friendlyNutrientText,
  friendlyQuantity,
  nutrientSheetLabel,
  priceAmount,
  priceKindLabel,
} from '../shared/format';
import { CartAlternatives } from './cart-alternatives';

type PerfilMarca = { tone: 'bad' | 'ok' | 'unknown'; label: string };

@Component({
  selector: 'app-product-page',
  imports: [RouterLink, OtterGuide, DecimalPipe, BandChip, CategoryMark, ShelfStamps, LoadingWell, CartAlternatives, ProductPhoto],
  template: `
    @if (product(); as p) {
      <article class="ficha">
        <div class="ficha-intro">
          <div class="ficha-welcome">
            <app-otter-guide
              variant="explain"
              size="compact"
              caption="Mira cómo encaja este producto contigo."
            />
          </div>
          <header class="card-paper ficha-identity">
            <p class="ficha-kicker">
              <app-category-mark [category]="p.category" />
              <span>{{ categoryLabel(p.category) }}</span>
            </p>
            <h1 class="page-title">{{ displayName(p) }}</h1>
            <div class="ficha-identity-meta">
              <span class="ficha-identity-brand">{{ p.brand.value ?? 'Marca no disponible' }}</span>
              @if (presentacion(p); as cant) {
                <span class="ficha-identity-pill">{{ cant }}</span>
              }
              <span class="ficha-identity-pill ficha-identity-code">{{ p.code }}</span>
              @if (p.fit.status === 'DERIVED') {
                <app-band-chip [band]="p.fit.band" />
              }
            </div>
          </header>
        </div>
        <div class="ficha-pair">
          <aside class="card-paper ficha-offer">
            <div class="ficha-offer-visual">
              <div class="ficha-photo anaquel-photo">
                <app-product-photo [imageUrl]="p.imageUrl" [category]="p.category" [alt]="displayName(p)" />
                <div class="ficha-photo-stamps">
                  <app-shelf-stamps [labels]="p.labels" [compact]="true" />
                </div>
              </div>
              <div class="ficha-price" [attr.data-price-kind]="p.price.status">
                @if (priceAmount(p); as monto) {
                  <p class="ficha-price-amount">{{ monto }}</p>
                  <p class="price-badge" [attr.data-price-kind]="p.price.status">{{ priceKindLabel(p) }}</p>
                } @else {
                  <p class="ficha-price-missing">Precio no disponible</p>
                }
              </div>
            </div>
            <div class="ficha-actions">
              <button
                type="button"
                class="btn btn-tide"
                [disabled]="cart.has(p.code)"
                (click)="cart.add(p.code)"
              >
                {{ cart.has(p.code) ? 'En el carrito' : 'Agregar al carrito' }}
              </button>
              <button
                type="button"
                class="btn btn-ghost"
                [attr.aria-expanded]="abiertas() === p.code"
                (click)="explorar(p.code)"
              >
                {{ abiertas() === p.code ? 'Cerrar alternativas' : 'Explorar alternativas' }}
              </button>
              <button type="button" class="btn btn-quiet" (click)="compare.toggle(p.code)">
                {{ compare.has(p.code) ? 'Quitar de comparación' : 'Comparar' }}
              </button>
            </div>
          </aside>
          <section class="card-paper ficha-fit">
              <h2>¿Cómo encaja contigo?</h2>
              <div class="ficha-fit-head">
                <div class="ficha-score-block">
                  <p class="ficha-score">
                    @if (p.fit.score === null) {
                      <strong>—</strong>
                    } @else {
                      <strong>{{ p.fit.score | number:'1.0-1' }}</strong>
                      <span>/ 100</span>
                    }
                  </p>
                  <p class="text-sm text-mute">
                    {{ p.fit.score === null ? 'Sin resultado disponible' : 'Según tus preferencias' }}
                  </p>
                </div>
                @if (razones(p).length) {
                  <ul class="ficha-reasons">
                    @for (razon of razones(p); track razon.text) {
                      <li [attr.data-tone]="razon.tone">{{ razon.text }}</li>
                    }
                  </ul>
                }
              </div>
          <ul class="ficha-dims">
            @for (dim of dimensiones(p); track dim.key) {
              <li>
                <span>{{ dim.label }}</span>
                <strong>{{ dim.value }}</strong>
                @if (dim.note) {
                  <small>{{ dim.note }}</small>
                }
              </li>
            }
          </ul>
          <div class="ficha-meta">
            @if (p.fit.cov >= 0.5) {
              <span class="ficha-meta-chip" data-tone="ok">✓ Información suficiente</span>
            } @else {
              <span class="ficha-meta-chip">Información parcial</span>
            }
            @if (calidadChip(p); as calidad) {
              <span class="ficha-meta-chip" [attr.data-level]="p.dataQualityLevel">{{ calidad }}</span>
            }
            @if (p.fit.status === 'DERIVED') {
              <span class="ficha-meta-note">ⓘ Score calculado por NutriMatch</span>
            }
          </div>
          </section>
        </div>
        @if (abiertas() === p.code) {
          <app-cart-alternatives [code]="p.code" />
        }

        <div class="ficha-duo">
        <section class="card-paper ficha-block ficha-nutrition">
          <h2>Información nutricional</h2>
          <p class="ficha-block-kicker">Por 100 g</p>
          <ul class="ficha-nutrients">
            @for (n of p.nutrients; track n.key) {
              <li>
                <span>{{ nutrientSheetLabel(n.key, n.label) }}</span>
                <strong [class.is-missing]="n.per100g === null">{{ nutrientText(n.per100g, n.unit) }}</strong>
              </li>
            }
          </ul>
        </section>

        <section class="card-paper ficha-block">
          <h2>Tu perfil</h2>
          <ul class="ficha-profile">
            <li>
              <span>Alergia</span>
              <strong [attr.data-tone]="marcaAlergia(p).tone">{{ marcaAlergia(p).label }}</strong>
            </li>
            <li>
              <span>Dieta</span>
              <strong [attr.data-tone]="marcaDieta(p).tone">{{ marcaDieta(p).label }}</strong>
            </li>
          </ul>
        </section>
        </div>

        <section class="ficha-facts">
          <div class="card-paper ficha-block">
            <h2>Ingredientes</h2>
            @if (!p.ingredients.length) {
              <p class="text-sm">Información no disponible</p>
            } @else {
              <p class="text-sm">{{ p.ingredients.join(', ') }}</p>
            }
          </div>
          <div class="card-paper ficha-block">
            <h2>Alérgenos</h2>
            @if (p.allergens.length) {
              <app-shelf-stamps [allergens]="p.allergens" />
            } @else {
              <p class="text-sm">Información de alérgenos no disponible</p>
            }
          </div>
          <div class="card-paper ficha-block">
            <h2>Puede contener</h2>
            @if (p.traces.length) {
              <app-shelf-stamps [allergens]="p.traces" />
            } @else {
              <p class="text-sm">Información de alérgenos no disponible</p>
            }
          </div>
          <div class="card-paper ficha-block">
            <h2>Sellos</h2>
            @if (etiquetasDeSelloVisibles(p.labels).length) {
              <app-shelf-stamps [labels]="p.labels" />
            } @else {
              <p class="text-sm">Información de sellos no disponible</p>
            }
          </div>
          <p class="ficha-facts-note">
            Si un sello o un alérgeno no aparece, el registro no lo trae. No se afirma que el producto no lo tenga.
          </p>
        </section>
      </article>
    } @else if (missing()) {
      <div class="empty-well">
        <app-otter-guide variant="empty" size="compact" />
        <p>No encontramos ese código en el catálogo.</p>
        <a routerLink="/buscar" class="btn btn-tide">Buscar producto</a>
      </div>
    } @else {
      <app-loading-well label="Cargando ficha…" />
    }
  `,
})
export class ProductPage {
  private readonly repo = inject(ProductRepository);
  private readonly route = inject(ActivatedRoute);
  readonly profile = inject(ProfileStore);
  readonly cart = inject(CartStore);
  readonly compare = inject(CompareStore);
  readonly displayName = displayName;
  readonly etiquetasDeSelloVisibles = etiquetasDeSelloVisibles;
  readonly priceAmount = priceAmount;
  readonly priceKindLabel = priceKindLabel;
  readonly categoryLabel = categoryLabel;
  readonly nutrientSheetLabel = nutrientSheetLabel;
  readonly nutrientText = friendlyNutrientText;
  readonly abiertas = signal<string | null>(null);
  private lastLoggedCode = '';

  private readonly code = toSignal(this.route.paramMap.pipe(map((p) => p.get('code') ?? '')), {
    initialValue: '',
  });

  private readonly loaded = toSignal(
    combineLatest([toObservable(this.code), toObservable(this.profile.profile)]).pipe(
      switchMap(([code, profile]) => {
        if (!code) {
          return of({ product: undefined, missing: false });
        }
        return this.repo.explain(code, profile).pipe(
          tap((product) => {
            if (product && product.code !== this.lastLoggedCode) {
              this.lastLoggedCode = product.code;
              this.repo.logEvent('product_viewed', { code: product.code }).subscribe();
            }
          }),
          map((product) => ({ product, missing: !product })),
          catchError(() => of({ product: undefined, missing: true })),
        );
      }),
    ),
    { initialValue: { product: undefined, missing: false } },
  );

  readonly product = computed(() => this.loaded().product);
  readonly missing = computed(() => this.loaded().missing);

  explorar(code: string): void {
    this.abiertas.update((actual) => (actual === code ? null : code));
  }

  presentacion(product: Product): string | null {
    return friendlyQuantity(product.quantity);
  }

  razones(product: Product): { tone: 'bad' | 'muted'; text: string }[] {
    const profile = this.profile.profile();
    const razones: { tone: 'bad' | 'muted'; text: string }[] = [];
    if (profile.allergenTags.length && product.fit.allergyStatus === 'no_apto') {
      razones.push({ tone: 'bad', text: '⚠ No apto por alergia' });
    }
    if (profile.diet && product.fit.dietStatus === 'incompatible') {
      razones.push({ tone: 'bad', text: '⚠ No apto por dieta' });
    }
    if (profile.allergenTags.length && product.fit.allergyStatus === 'no_verificable') {
      razones.push({ tone: 'muted', text: 'Alergia: no verificable' });
    }
    if (profile.diet && product.fit.dietStatus === 'no_verificable') {
      razones.push({ tone: 'muted', text: 'Dieta: no verificable' });
    }
    return razones;
  }

  dimensiones(product: Product): { key: string; label: string; value: string; note: string | null }[] {
    const sinPreferencias = this.profile.profile().valuedLabels.length === 0;
    const valor = (n: number) => n.toFixed(1);
    return [
      { key: 'D1', label: 'Nutrición', value: product.fit.d1 === null ? 'No evaluado' : valor(product.fit.d1), note: null },
      { key: 'D2', label: 'Procesamiento', value: product.fit.d2 === null ? 'No evaluado' : valor(product.fit.d2), note: null },
      {
        key: 'D3',
        label: 'Etiquetas',
        value: product.fit.d3 === null ? 'No evaluado' : valor(product.fit.d3),
        note: product.fit.d3 === null && sinPreferencias ? 'Sin preferencias' : null,
      },
    ];
  }

  marcaAlergia(product: Product): PerfilMarca {
    if (!this.profile.profile().allergenTags.length) {
      return { tone: 'unknown', label: 'Sin información' };
    }
    if (product.fit.allergyStatus === 'no_apto') {
      return { tone: 'bad', label: 'No apto' };
    }
    if (product.fit.allergyStatus === 'no_verificable') {
      return { tone: 'unknown', label: 'No verificable' };
    }
    return { tone: 'ok', label: 'Compatible' };
  }

  marcaDieta(product: Product): PerfilMarca {
    if (!this.profile.profile().diet) {
      return { tone: 'unknown', label: 'Sin información' };
    }
    if (product.fit.dietStatus === 'incompatible') {
      return { tone: 'bad', label: 'No apto' };
    }
    if (product.fit.dietStatus === 'no_verificable') {
      return { tone: 'unknown', label: 'No verificable' };
    }
    return { tone: 'ok', label: 'Compatible' };
  }

  calidadChip(product: Product): string | null {
    const level = product.dataQualityLevel?.trim().toLowerCase();
    if (level === 'alta') {
      return 'Información: Alta';
    }
    if (level === 'media' || level === 'baja') {
      return 'Información: Parcial';
    }
    if (level === 'insuficiente') {
      return 'Información: Insuficiente';
    }
    const nombre = dataQualityLevelName(product);
    return nombre ? `Información: ${nombre}` : null;
  }
}
