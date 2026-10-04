import { DecimalPipe } from '@angular/common';
import { Component, computed, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { GroupBucket, Product } from '../../core/models/domain';
import { catalogPlaceholderSrc, displayName, usableProductImage } from '../format';

export const PLATO_CHIP_MAX = 4;

export const PLATO_GUIDE_KEYS = ['frutas_verduras', 'cereales', 'leguminosas_aoa'] as const;

const GUIDE_LABELS: Record<string, string> = {
  frutas_verduras: 'Verduras y frutas',
  cereales: 'Cereales',
  leguminosas_aoa: 'Leguminosas y alimentos de origen animal',
};

export interface PlatoChip {
  code: string;
  src: string;
  placeholder: boolean;
  name: string;
}

export function platoVisibleCodes(codes: string[], max = PLATO_CHIP_MAX): { shown: string[]; extra: number } {
  const shown = codes.slice(0, max);
  return { shown, extra: Math.max(0, codes.length - shown.length) };
}

export function platoChipsFor(codes: string[], byCode: Map<string, Product>): PlatoChip[] {
  return platoVisibleCodes(codes).shown.map((code) => {
    const product = byCode.get(code);
    return {
      code,
      src: usableProductImage(product?.imageUrl) || catalogPlaceholderSrc(product?.category),
      placeholder: !usableProductImage(product?.imageUrl),
      name: product ? displayName(product) : 'Producto sin nombre verificado',
    };
  });
}

@Component({
  selector: 'app-plato-dish',
  imports: [DecimalPipe, RouterLink],
  template: `
    <div class="plato-stage">
      <div class="plato-board">
        <div class="plato-plate" role="img" [attr.aria-label]="ariaLabel()">
          @for (wedge of wedges(); track wedge.key) {
            <div
              class="plato-wedge"
              [attr.data-key]="wedge.key"
              [class.plato-wedge-on]="selectedKey() === wedge.key"
              [attr.aria-pressed]="selectedKey() === wedge.key"
              role="button"
              tabindex="0"
              (click)="select.emit(wedge.key)"
              (keydown.enter)="select.emit(wedge.key)"
            >
              <span class="plato-wedge-label">{{ wedge.label }}</span>
              <span class="plato-wedge-chips">
                @for (chip of wedge.chips; track chip.code) {
                  <a
                    class="plato-chip"
                    [routerLink]="['/producto', chip.code]"
                    (click)="$event.stopPropagation()"
                    [title]="chip.name"
                  >
                    <img [src]="chip.src" [alt]="chip.name" [class.catalog-ph]="chip.placeholder" />
                  </a>
                }
                @if (wedge.extra) {
                  <span class="plato-chip-more">+{{ wedge.extra }}</span>
                }
              </span>
            </div>
          }
        </div>
        <aside class="plato-water" aria-hidden="true">
          <span class="plato-glass"></span>
          <p>Agua · guía</p>
        </aside>
      </div>
      <aside class="plato-bowl">
        <div
          class="plato-bowl-btn"
          [class.plato-wedge-on]="selectedKey() === 'unclassified'"
          [attr.aria-pressed]="selectedKey() === 'unclassified'"
          role="button"
          tabindex="0"
          (click)="select.emit('unclassified')"
          (keydown.enter)="select.emit('unclassified')"
        >
          <p class="plato-bowl-kicker">No clasificado</p>
          <p class="plato-bowl-hint">Estos productos no tienen un grupo en la guía.</p>
          <span class="plato-wedge-chips">
            @for (chip of unclassified().chips; track chip.code) {
              <a
                class="plato-chip"
                [routerLink]="['/producto', chip.code]"
                (click)="$event.stopPropagation()"
                [title]="chip.name"
              >
                <img [src]="chip.src" [alt]="chip.name" [class.catalog-ph]="chip.placeholder" />
              </a>
            }
            @if (unclassified().extra) {
              <span class="plato-chip-more">+{{ unclassified().extra }}</span>
            }
          </span>
          <p class="plato-bowl-count">
            {{ unclassified().n }}
            @if (unclassified().n > 0) {
              · {{ unclassified().share * 100 | number:'1.0-0' }}%
            }
          </p>
        </div>
      </aside>
    </div>
  `,
})
export class PlatoDish {
  readonly buckets = input.required<GroupBucket[]>();
  readonly products = input<Product[]>([]);
  readonly selectedKey = input<string | null>(null);
  readonly select = output<string>();

  private readonly byCode = computed(() => new Map(this.products().map((product) => [product.code, product])));

  readonly wedges = computed(() => {
    const byCode = this.byCode();
    const buckets = this.buckets();
    return PLATO_GUIDE_KEYS.map((key) => {
      const bucket = buckets.find((row) => row.key === key);
      const codes = bucket?.codes ?? [];
      const visible = platoVisibleCodes(codes);
      return {
        key,
        label: GUIDE_LABELS[key] ?? bucket?.label ?? key,
        n: bucket?.n ?? 0,
        share: bucket?.share ?? 0,
        chips: platoChipsFor(codes, byCode),
        extra: visible.extra,
      };
    });
  });

  readonly unclassified = computed(() => {
    const bucket = this.buckets().find((row) => row.key === 'unclassified');
    const codes = bucket?.codes ?? [];
    const visible = platoVisibleCodes(codes);
    return {
      n: bucket?.n ?? 0,
      share: bucket?.share ?? 0,
      chips: platoChipsFor(codes, this.byCode()),
      extra: visible.extra,
    };
  });

  ariaLabel(): string {
    const parts = this.wedges()
      .filter((wedge) => wedge.n > 0)
      .map((wedge) => `${wedge.label}: ${wedge.n}`);
    const extra = this.unclassified().n;
    if (extra) {
      parts.push(`no clasificado: ${extra}`);
    }
    return parts.length ? `Plato del Bien Comer. ${parts.join('. ')}.` : 'Plato del Bien Comer sin productos en los gajos.';
  }
}
