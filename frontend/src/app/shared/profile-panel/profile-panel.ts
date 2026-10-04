import { Component, effect, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { OnboardingStore } from '../../core/data/onboarding.store';
import { ProfileStore } from '../../core/data/profile.store';
import {
  ALLERGEN_CHOICES,
  DietaDeclarada,
  DimensionPrioridad,
  LABEL_CHOICES,
  PRIORITY_LABELS,
  UserProfile,
} from '../../core/models/domain';

@Component({
  selector: 'app-profile-panel',
  imports: [FormsModule, RouterLink],
  host: { class: 'pref-panel' },
  template: `
    <form class="pref-form" (ngSubmit)="guardar()">
      <div class="pref-form-scroll">
        <label class="pref-block">
          <span class="pref-block-title">Nombre</span>
          <input
            class="field-paper mt-2 w-full px-3 py-2"
            name="displayName"
            autocomplete="given-name"
            [(ngModel)]="draftName"
          />
        </label>
        <fieldset class="pref-block">
          <legend class="pref-block-title">Alergias</legend>
          <div class="pref-chips">
            @for (opt of allergens; track opt[0]) {
              <button
                type="button"
                class="choice-chip choice-chip-avoid"
                [attr.aria-pressed]="draft.allergenTags.includes(opt[0])"
                (click)="toggle(draft.allergenTags, opt[0])"
              >
                {{ opt[1] }}
              </button>
            }
          </div>
          <p class="pref-note">
            Si falta dato de alérgenos, el producto va a no verificable, no a apto.
          </p>
        </fieldset>
        <fieldset class="pref-block">
          <legend class="pref-block-title">Dieta</legend>
          <div class="pref-chips">
            <button
              type="button"
              class="choice-chip"
              [attr.aria-pressed]="draft.diet === null"
              (click)="setDiet(null)"
            >
              Ninguna
            </button>
            <button
              type="button"
              class="choice-chip"
              [attr.aria-pressed]="draft.diet === 'vegetariano'"
              (click)="setDiet('vegetariano')"
            >
              Vegetariano
            </button>
            <button
              type="button"
              class="choice-chip"
              [attr.aria-pressed]="draft.diet === 'vegano'"
              (click)="setDiet('vegano')"
            >
              Vegano
            </button>
          </div>
        </fieldset>
        <fieldset class="pref-block">
          <legend class="pref-block-title">Etiquetas que valoras</legend>
          <div class="pref-chips">
            @for (opt of labels; track opt[0]) {
              <button
                type="button"
                class="choice-chip"
                [attr.aria-pressed]="draft.valuedLabels.includes(opt[0])"
                (click)="toggle(draft.valuedLabels, opt[0])"
              >
                {{ opt[1] }}
              </button>
            }
          </div>
        </fieldset>
        <fieldset class="pref-block">
          <legend class="pref-block-title">Qué te importa más</legend>
          <p class="pref-hint">
            Arriba pesa más. El orden decide cuál dimensión cuenta más; no se eligen números a mano.
          </p>
          <ol class="prio-stack">
            @for (dim of draft.priorityOrder; track dim; let i = $index) {
              <li class="prio-row" [attr.data-rank]="i + 1">
                <span class="prio-rank" aria-hidden="true">{{ i + 1 }}</span>
                <div class="min-w-0 flex-1">
                  <p class="prio-name">{{ labelsOf[dim] }}</p>
                  <p class="prio-hint">{{ hints[dim] }}</p>
                </div>
                <div class="prio-move">
                  <button
                    type="button"
                    class="prio-btn"
                    [disabled]="i === 0"
                    [attr.aria-label]="'Subir ' + labelsOf[dim]"
                    (click)="mover(i, -1)"
                  >↑</button>
                  <button
                    type="button"
                    class="prio-btn"
                    [disabled]="i === draft.priorityOrder.length - 1"
                    [attr.aria-label]="'Bajar ' + labelsOf[dim]"
                    (click)="mover(i, 1)"
                  >↓</button>
                </div>
              </li>
            }
          </ol>
        </fieldset>
      </div>
      <div class="pref-form-foot">
        <div class="flex flex-wrap gap-2">
          <button type="submit" class="btn btn-tide">Guardar</button>
          <button type="button" class="btn btn-ghost" (click)="restablecer()">
            Restablecer
          </button>
        </div>
        <p class="pref-foot-note">Se guarda en este navegador. No es una cuenta.</p>
        <a routerLink="/onboarding" class="pref-welcome">Ver la bienvenida</a>
      </div>
    </form>
  `,
})
export class ProfilePanel {
  private readonly store = inject(ProfileStore);
  private readonly onboarding = inject(OnboardingStore);
  readonly allergens = ALLERGEN_CHOICES;
  readonly labels = LABEL_CHOICES;
  readonly labelsOf = PRIORITY_LABELS;
  readonly hints: Record<DimensionPrioridad, string> = {
    D1: 'Nutrientes por 100 g',
    D2: 'NOVA y aditivos',
    D3: 'Etiquetas que valoras',
  };
  draft: UserProfile = structuredClone(this.store.profile());
  draftName = this.onboarding.displayName();

  constructor() {
    effect(() => {
      this.draft = structuredClone(this.store.profile());
      this.draftName = this.onboarding.displayName();
    });
  }

  toggle(list: string[], tag: string): void {
    const i = list.indexOf(tag);
    if (i >= 0) {
      list.splice(i, 1);
    } else {
      list.push(tag);
    }
  }

  setDiet(diet: DietaDeclarada | null): void {
    this.draft = { ...this.draft, diet };
  }

  mover(index: number, delta: number): void {
    const next = index + delta;
    const order = this.draft.priorityOrder;
    if (next < 0 || next >= order.length) {
      return;
    }
    const copy = [...order];
    const [item] = copy.splice(index, 1);
    copy.splice(next, 0, item);
    this.draft = { ...this.draft, priorityOrder: copy };
  }

  guardar(): void {
    this.store.save(this.draft);
    this.onboarding.setDisplayName(this.draftName);
  }

  restablecer(): void {
    this.store.reset();
  }
}
