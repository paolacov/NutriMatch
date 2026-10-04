import { Component, computed, input } from '@angular/core';
import { etiquetaDeSello } from '../format';

interface Stamp {
  tag: string;
  label: string;
  short: string;
  kind: 'exceso' | 'sello' | 'alergeno';
  highlight: boolean;
}

const SELLOS_OCULTOS = new Set([
  'es:sistema-de-etiquetado-frontal-de-alimentos-y-bebidas',
]);

export function etiquetasDeSelloVisibles(tags: string[]): string[] {
  return tags.filter((tag) => !SELLOS_OCULTOS.has(tag) && etiquetaDeSello(tag).trim());
}

const EXCESO_CORTO: Record<string, string> = {
  'es:exceso-azucares': 'AZÚCARES',
  'es:exceso-azúcares': 'AZÚCARES',
  'es:exceso-calorias': 'CALORÍAS',
  'es:exceso-calorías': 'CALORÍAS',
  'es:exceso-grasas-saturadas': 'GRASAS SAT.',
  'es:exceso-grasas-trans': 'GRASAS TRANS',
  'es:exceso-sodio': 'SODIO',
  'es:exceso-en-calorias': 'CALORÍAS',
  'es:exceso-en-azucares': 'AZÚCARES',
  'es:exceso-en-grasas-saturadas': 'GRASAS SAT.',
  'es:exceso-en-grasas-totales': 'GRASAS',
};

function selloKind(tag: string): Stamp['kind'] {
  return tag.includes('exceso') ? 'exceso' : 'sello';
}

function corto(tag: string): string {
  return EXCESO_CORTO[tag] ?? etiquetaDeSello(tag).toLocaleUpperCase('es-MX');
}

@Component({
  selector: 'app-shelf-stamps',
  template: `
    @if (stamps().length) {
      <ul class="shelf-stamps" [class.shelf-stamps-compact]="compact()">
        @for (s of stamps(); track s.tag) {
          <li
            class="stamp"
            [attr.data-kind]="s.kind"
            [attr.data-highlight]="s.highlight ? 'perfil' : null"
            [title]="s.label"
          >
            @if (s.kind === 'exceso') {
              <span class="stamp-kicker">EXCESO</span>
              <span class="stamp-short">{{ s.short }}</span>
            } @else if (s.highlight) {
              <span class="stamp-kicker">en tu perfil</span>
              <span class="stamp-short">{{ s.label }}</span>
            } @else {
              <span class="stamp-short">{{ s.label }}</span>
            }
          </li>
        }
      </ul>
    }
  `,
})
export class ShelfStamps {
  readonly labels = input<string[]>([]);
  readonly allergens = input<string[]>([]);
  readonly highlightAllergens = input<string[]>([]);
  readonly compact = input(false);

  readonly stamps = computed<Stamp[]>(() => {
    const perfil = new Set(this.highlightAllergens());
    const sellos = etiquetasDeSelloVisibles(this.labels()).map((tag) => ({
        tag,
        label: etiquetaDeSello(tag),
        short: corto(tag),
        kind: selloKind(tag),
        highlight: false,
      }));
    const alergenos = this.allergens()
      .filter((tag) => etiquetaDeSello(tag).trim())
      .map((tag) => ({
      tag: `a-${tag}`,
      label: etiquetaDeSello(tag),
      short: etiquetaDeSello(tag),
      kind: 'alergeno' as const,
      highlight: perfil.has(tag),
    }));
    const todos = [...sellos, ...alergenos];
    return this.compact() ? todos.filter((s) => s.kind === 'exceso').slice(0, 3) : todos;
  });
}
