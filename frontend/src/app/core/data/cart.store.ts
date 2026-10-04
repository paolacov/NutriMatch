import { computed, inject, Injectable, signal } from '@angular/core';
import { ProductRepository } from './product.repository';

const KEY = 'nutrimatch.cart';

@Injectable({ providedIn: 'root' })
export class CartStore {
  private readonly repo = inject(ProductRepository);
  readonly codes = signal<string[]>(this.load());
  readonly count = computed(() => this.codes().length);

  add(code: string): void {
    if (this.codes().includes(code)) {
      return;
    }
    this.persist([...this.codes(), code]);
    this.repo.logEvent('cart_item_added', { code }).subscribe();
  }

  remove(code: string): void {
    if (!this.codes().includes(code)) {
      return;
    }
    this.persist(this.codes().filter((c) => c !== code));
    this.repo.logEvent('cart_item_removed', { code }).subscribe();
  }

  replace(from: string, to: string): void {
    if (!to || from === to) {
      return;
    }
    const codes = this.codes();
    const fromIndex = codes.indexOf(from);
    if (fromIndex < 0) {
      this.add(to);
      return;
    }
    if (codes.includes(to)) {
      this.remove(from);
      return;
    }
    const next = codes.slice();
    next[fromIndex] = to;
    this.persist(next);
    this.repo.logEvent('cart_item_removed', { code: from }).subscribe();
    this.repo.logEvent('cart_item_added', { code: to, replaced: from }).subscribe();
  }

  has(code: string): boolean {
    return this.codes().includes(code);
  }

  private persist(next: string[]): void {
    this.codes.set(next);
    localStorage.setItem(KEY, JSON.stringify(next));
  }

  private load(): string[] {
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }
}
