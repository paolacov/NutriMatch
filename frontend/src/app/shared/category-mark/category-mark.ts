import { Component, input } from '@angular/core';

export type CategoryGlyph =
  | 'grain'
  | 'drink'
  | 'dairy'
  | 'snack'
  | 'bakery'
  | 'nut'
  | 'protein'
  | 'produce'
  | 'sauce'
  | 'prepared'
  | 'shelf';

export function categoryGlyph(tag: string | null | undefined): CategoryGlyph {
  const k = (tag ?? '').toLowerCase();
  if (/flour|cornmeal|cereal|oat|muesli|grain|rice|quinoa|polenta|harina/.test(k)) {
    return 'grain';
  }
  if (/water|beverage|juice|soda|coffee|tea|jugo|refresco|cola|beer|wine|alcohol/.test(k)) {
    return 'drink';
  }
  if (/milk|yogurt|cheese|dairy|cream|leche|queso|yogur/.test(k)) {
    return 'dairy';
  }
  if (/gum|candy|chocolate|biscuit|sweet|dulce|chicle|jam|ice-cream/.test(k)) {
    return 'snack';
  }
  if (/snack|crisp|chip|botana/.test(k)) {
    return 'snack';
  }
  if (/pasta|bread|tortilla|toast|bakery|pan/.test(k)) {
    return 'bakery';
  }
  if (/nut|almond|peanut|cacahuate|almendra/.test(k)) {
    return 'nut';
  }
  if (/fish|meat|tuna|egg|turkey|seafood|atun|pescado|sausage/.test(k)) {
    return 'protein';
  }
  if (/fruit|vegetable|produce|verdura|fruta/.test(k)) {
    return 'produce';
  }
  if (/sauce|oil|spread|salsa|aceite|fat|condiment/.test(k)) {
    return 'sauce';
  }
  if (/soup|meal|composite|preparado|sopa|ready/.test(k)) {
    return 'prepared';
  }
  return 'shelf';
}

@Component({
  selector: 'app-category-mark',
  template: `
    <span class="category-mark" [class.category-mark-lg]="size() === 'lg'" [attr.data-glyph]="glyph()" aria-hidden="true">
      @switch (glyph()) {
        @case ('grain') {
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M14 36h20l3-18H11l3 18Z" stroke="currentColor" stroke-width="2"/>
            <path d="M18 18c0-6 6-10 6-10s6 4 6 10" stroke="currentColor" stroke-width="2"/>
            <path d="M16 28h16" stroke="currentColor" stroke-width="2"/>
          </svg>
        }
        @case ('drink') {
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M18 8h12l2 6v24a4 4 0 0 1-4 4H20a4 4 0 0 1-4-4V14l2-6Z" stroke="currentColor" stroke-width="2"/>
            <path d="M16 16h16" stroke="currentColor" stroke-width="2"/>
          </svg>
        }
        @case ('dairy') {
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M16 12h16l4 8v16a4 4 0 0 1-4 4H16a4 4 0 0 1-4-4V20l4-8Z" stroke="currentColor" stroke-width="2"/>
            <path d="M16 22h16" stroke="currentColor" stroke-width="2"/>
          </svg>
        }
        @case ('snack') {
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M12 20c6-8 18-8 24 0-2 10-6 18-12 18S14 30 12 20Z" stroke="currentColor" stroke-width="2"/>
            <path d="M20 16c2 4 6 4 8 0" stroke="currentColor" stroke-width="2"/>
          </svg>
        }
        @case ('bakery') {
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M8 30c4-10 28-10 32 0v4H8v-4Z" stroke="currentColor" stroke-width="2"/>
            <path d="M16 24v6M24 22v8M32 24v6" stroke="currentColor" stroke-width="2"/>
          </svg>
        }
        @case ('nut') {
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M24 8c8 6 10 14 8 22-4 8-12 10-16 6-6-6-4-18 8-28Z" stroke="currentColor" stroke-width="2"/>
            <path d="M22 18c2 4 6 8 8 10" stroke="currentColor" stroke-width="2"/>
          </svg>
        }
        @case ('protein') {
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M10 28c4-10 24-10 28 0-2 8-8 12-14 12S12 36 10 28Z" stroke="currentColor" stroke-width="2"/>
            <path d="M18 24c2 4 10 4 12 0" stroke="currentColor" stroke-width="2"/>
          </svg>
        }
        @case ('produce') {
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M24 38c-8-2-12-10-10-18 6-2 12 2 14 8" stroke="currentColor" stroke-width="2"/>
            <path d="M24 20c2-8 10-10 14-8-2 8-8 10-14 8Z" stroke="currentColor" stroke-width="2"/>
          </svg>
        }
        @case ('sauce') {
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M20 8h8l2 6v4H18v-4l2-6Z" stroke="currentColor" stroke-width="2"/>
            <path d="M16 18h16v18a4 4 0 0 1-4 4H20a4 4 0 0 1-4-4V18Z" stroke="currentColor" stroke-width="2"/>
          </svg>
        }
        @case ('prepared') {
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M10 26h28c-1 8-8 12-14 12S11 34 10 26Z" stroke="currentColor" stroke-width="2"/>
            <path d="M8 22h32" stroke="currentColor" stroke-width="2"/>
          </svg>
        }
        @default {
          <svg viewBox="0 0 48 48" fill="none">
            <path d="M10 18h28v18H10V18Z" stroke="currentColor" stroke-width="2"/>
            <path d="M14 18V14h20v4M24 18v18" stroke="currentColor" stroke-width="2"/>
          </svg>
        }
      }
    </span>
  `,
})
export class CategoryMark {
  readonly category = input<string | null>(null);
  readonly size = input<'sm' | 'lg'>('sm');

  glyph(): CategoryGlyph {
    return categoryGlyph(this.category());
  }
}
