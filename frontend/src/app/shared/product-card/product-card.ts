import { Component, inject, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { CartStore } from '../../core/data/cart.store';
import { Product } from '../../core/models/domain';
import { BandChip } from '../band-chip/band-chip';
import { CategoryMark } from '../category-mark/category-mark';
import { ProductPhoto } from '../product-photo/product-photo';
import { ShelfStamps } from '../shelf-stamps/shelf-stamps';
import {
  catalogDataCaption,
  categoryLabel,
  displayName,
  friendlyNutrientText,
  priceAmount,
  priceKindLabel,
} from '../format';

@Component({
  selector: 'app-product-card',
  imports: [RouterLink, BandChip, CategoryMark, ShelfStamps, ProductPhoto],
  template: `
    @if (mode() === 'discover') {
      <article class="product-card product-card-discover card-paper" [attr.data-tone]="tone()">
        <div class="anaquel-photo relative flex items-center justify-center overflow-hidden">
          <app-product-photo
            [imageUrl]="product().imageUrl"
            [category]="product().category"
            [alt]="displayName(product())"
            [contain]="true"
          />
          <div class="pointer-events-none absolute bottom-1 left-1 right-1">
            <app-shelf-stamps [labels]="product().labels" [compact]="true" />
          </div>
          @if (tone() === 'fit' && product().fit.score !== null) {
            <p class="discover-score">
              <strong>{{ product().fit.score }}</strong><span>/100</span>
            </p>
          }
        </div>
        <h3>{{ displayName(product()) }}</h3>
        <p class="discover-brand">{{ product().brand.value ?? 'Marca no disponible' }}</p>
        <p class="discover-category">
          <app-category-mark [category]="product().category" />
          {{ categoryLabel(product().category) }}
        </p>
        @if (tone() === 'fit') {
          @if (product().fit.score !== null) {
            <p class="discover-why">Según tus preferencias</p>
          }
          @if (atributos().length) {
            <ul class="discover-chips">
              @for (chip of atributos(); track chip) {
                <li>{{ chip }}</li>
              }
            </ul>
          }
        } @else if (tone() === 'gap') {
          @if (huecos().length) {
            <ul class="discover-chips discover-chips-gap">
              @for (chip of huecos(); track chip) {
                <li>{{ chip }}</li>
              }
            </ul>
          }
        } @else if (pendientes().length) {
          <ul class="discover-chips">
            @for (chip of pendientes(); track chip) {
              <li>{{ chip }}</li>
            }
          </ul>
        }
        <div class="discover-price">
          @if (priceAmount(product()); as monto) {
            <p>{{ monto }}</p>
            <p class="price-badge" [attr.data-price-kind]="product().price.status">{{ priceKindLabel(product()) }}</p>
          } @else {
            <p>Precio no disponible</p>
          }
        </div>
        <div class="discover-actions">
          <a class="btn btn-ghost btn-sm" [routerLink]="['/producto', product().code]">Ver producto</a>
          <button
            type="button"
            class="btn btn-sm"
            [class.btn-tide]="!cart.has(product().code)"
            [class.btn-ghost]="cart.has(product().code)"
            [disabled]="cart.has(product().code)"
            (click)="add.emit(product().code)"
          >
            {{ cart.has(product().code) ? 'En el carrito' : 'Agregar' }}
          </button>
        </div>
      </article>
    } @else {
    <article
      class="product-card card-paper flex flex-col p-4"
      [class.product-card-catalog]="mode() === 'catalog'"
    >
      <div class="anaquel-photo relative mb-3 flex h-36 items-center justify-center overflow-hidden rounded-lg">
        <app-product-photo
          [imageUrl]="product().imageUrl"
          [category]="product().category"
          [alt]="displayName(product())"
          [contain]="true"
        />
        <div class="pointer-events-none absolute bottom-1 left-1 right-1">
          <app-shelf-stamps [labels]="product().labels" [compact]="true" />
        </div>
      </div>
      <h3 class="text-base font-semibold leading-snug">{{ displayName(product()) }}</h3>
      <p class="text-sm text-mute">{{ product().brand.value ?? 'Marca no disponible' }}</p>
      <p class="mt-1 flex items-center gap-1.5 text-xs text-mute">
        <app-category-mark [category]="product().category" />
        {{ categoryLabel(product().category) }}
      </p>

      @if (ranked()) {
        <div class="mt-3">
          <p class="text-2xl font-bold">
            @if (product().fit.score === null) {
              —
            } @else {
              {{ product().fit.score }}<span class="text-sm font-normal text-mute">/100</span>
            }
          </p>
          @if (product().fit.score !== null) {
            <p class="text-sm text-mute">Según tus preferencias</p>
          }
          <div class="mt-2">
            <app-band-chip [band]="product().fit.band" />
          </div>
        </div>
      } @else if (mode() === 'catalog') {
        <div class="mt-3">
          @if (porCien().length) {
            <p class="text-xs font-semibold text-mute">Por 100 g</p>
            @for (row of porCien(); track row.label) {
              <p class="text-sm">{{ row.label }}: {{ row.text }}</p>
            }
          }
          <p class="mt-1 text-xs text-mute">{{ catalogDataCaption(product()) }}</p>
        </div>
      } @else {
        <p class="mt-3 text-sm text-mute">Abre la ficha para ver cómo encaja con tus preferencias.</p>
      }

      <div class="mt-3">
        @if (priceAmount(product()); as monto) {
          <p class="text-sm font-semibold">{{ monto }}</p>
          <p class="price-badge" [attr.data-price-kind]="product().price.status">{{ priceKindLabel(product()) }}</p>
        } @else {
          <p class="text-sm font-semibold">Precio no disponible</p>
        }
      </div>

      <div class="mt-4 flex flex-wrap gap-2">
        <a class="btn btn-ghost btn-sm" [routerLink]="['/producto', product().code]">Ver producto</a>
        <button
          type="button"
          class="btn btn-sm"
          [class.btn-tide]="!cart.has(product().code)"
          [class.btn-ghost]="cart.has(product().code)"
          [disabled]="cart.has(product().code)"
          (click)="add.emit(product().code)"
        >
          {{ cart.has(product().code) ? 'En el carrito' : 'Agregar' }}
        </button>
      </div>
    </article>
    }
  `,
})
export class ProductCard {
  readonly product = input.required<Product>();
  readonly mode = input<'default' | 'catalog' | 'discover'>('default');
  readonly tone = input<'fit' | 'gap' | 'pending'>('fit');
  readonly add = output<string>();
  readonly cart = inject(CartStore);
  readonly displayName = displayName;
  readonly priceAmount = priceAmount;
  readonly priceKindLabel = priceKindLabel;
  readonly categoryLabel = categoryLabel;
  readonly catalogDataCaption = catalogDataCaption;

  porCien(): { label: string; text: string }[] {
    const wanted = new Set(['proteins', 'sugars']);
    return this.product().nutrients
      .filter((row) => wanted.has(row.key) && row.per100g !== null)
      .map((row) => ({
        label: row.label,
        text: `${Number(row.per100g).toFixed(1)} ${row.unit}`,
      }));
  }

  ranked(): boolean {
    return this.product().fit.status === 'DERIVED';
  }

  atributos(): string[] {
    const orden = ['proteins', 'fiber', 'sugars'];
    return orden
      .map((key) => this.product().nutrients.find((row) => row.key === key && row.per100g !== null))
      .filter((row): row is NonNullable<typeof row> => !!row)
      .slice(0, 3)
      .map((row) => `${row.label} ${friendlyNutrientText(row.per100g, row.unit)}`);
  }

  huecos(): string[] {
    const faltan: string[] = [];
    if (this.product().fit.allergyStatus === 'no_verificable') {
      faltan.push('Falta información de alérgenos');
    }
    if (this.product().fit.dietStatus === 'no_verificable') {
      faltan.push('Falta información de dieta');
    }
    return faltan;
  }

  pendientes(): string[] {
    const texto: Record<string, string> = {
      D1_sin_dato: 'Falta información nutricional',
      D2_sin_dato: 'Falta información de procesamiento',
      D3_sin_dato: 'Falta información de etiquetas',
      alergia_no_verificable: 'Falta información de alérgenos',
      dieta_no_verificable: 'Falta información de dieta',
    };
    return this.product().fit.warnings.map((flag) => texto[flag]).filter((label): label is string => !!label);
  }
}
