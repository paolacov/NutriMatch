import { Injectable, signal } from '@angular/core';

const KEY = 'nutrimatch.compare';
const MAX = 3;

@Injectable({ providedIn: 'root' })
export class CompareStore {
  readonly codes = signal<string[]>(this.load());

  toggle(code: string): void {
    const current = this.codes();
    if (current.includes(code)) {
      this.persist(current.filter((c) => c !== code));
      return;
    }
    if (current.length >= MAX) {
      this.persist([...current.slice(1), code]);
      return;
    }
    this.persist([...current, code]);
  }

  has(code: string): boolean {
    return this.codes().includes(code);
  }

  remove(code: string): void {
    if (!this.has(code)) {
      return;
    }
    this.toggle(code);
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
