import { Component, computed, input, signal } from '@angular/core';
import { catalogPlaceholderSrc, usableProductImage } from '../format';

@Component({
  selector: 'app-product-photo',
  host: { class: 'product-photo' },
  styles: `
    :host {
      display: contents;
    }
  `,
  template: `
    <img
      [src]="src()"
      [alt]="alt()"
      [class.h-full]="contain()"
      [class.w-full]="contain()"
      [class.object-contain]="contain() && !placeholder()"
      [class.catalog-ph]="placeholder()"
      (error)="onError()"
    />
  `,
})
export class ProductPhoto {
  readonly imageUrl = input<string | null>(null);
  readonly category = input<string | null>(null);
  readonly alt = input('');
  readonly contain = input(false);
  private readonly failed = signal<string | null>(null);

  readonly placeholder = computed(() => this.resolved() === null);

  readonly src = computed(() => this.resolved() ?? catalogPlaceholderSrc(this.category()));

  private resolved(): string | null {
    const url = usableProductImage(this.imageUrl());
    if (!url || this.failed() === url) {
      return null;
    }
    return url;
  }

  onError(): void {
    const url = usableProductImage(this.imageUrl());
    if (url) {
      this.failed.set(url);
    }
  }
}
