import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { OnboardingStore } from '../core/data/onboarding.store';
import { ProfileStore } from '../core/data/profile.store';
import {
  ALLERGEN_CHOICES,
  DietaDeclarada,
  DimensionPrioridad,
  PRIORITY_LABELS,
  UserProfile,
} from '../core/models/domain';
import {
  OnboardingStage,
  avoidClosing,
  firstName,
  nextAllergenTags,
  priorityClosing,
  progressIndex,
} from '../core/models/onboarding';

const STAGE_ORDER: OnboardingStage[] = ['hello', 'name', 'prioridades', 'cuidar', 'resumen'];

const POSE: Record<OnboardingStage, string> = {
  hello: '/otter/nuti.png',
  name: '/otter/nuti.png',
  prioridades: '/otter/nuti.png',
  cuidar: '/otter/nuti.png',
  resumen: '/otter/nuti.png',
};

const SAY: Record<OnboardingStage, string> = {
  hello: '¡Qué gusto tenerte aquí!',
  name: '¿Cómo te llamo?',
  prioridades: 'Ahora dime qué quieres que tenga más importancia para ti.',
  cuidar: 'También puedo ayudarte a tener en cuenta lo que prefieres evitar.',
  resumen: '¡Ya puedo acompañarte!',
};

const MARK: Record<DimensionPrioridad, string> = {
  D1: '🥗',
  D2: '🧪',
  D3: '🏷️',
};

const DIMENSION_HINT: Record<DimensionPrioridad, string> = {
  D1: 'Qué tan dulce, salado o grasoso es un producto y cuánto aporta de fibra o proteína. Se compara con productos de referencia similares.',
  D2: 'Considera qué tan procesado está el alimento y la cantidad de aditivos registrada.',
  D3: 'Considera los sellos o características que tú valoras, como orgánico, sin gluten, vegetariano o vegano.',
};

@Component({
  selector: 'app-onboarding-page',
  imports: [FormsModule],
  template: `
    <section class="entry" [attr.data-stage]="stage()">
      <div class="entry-layout">
        <aside class="entry-stage" aria-hidden="true">
          <div class="entry-nuti-halo"></div>
          <img class="entry-nuti" [src]="pose()" alt="" decoding="async" />
          <p class="entry-say">{{ say() }}</p>
        </aside>

        <div class="entry-copy">
          @if (showsProgress()) {
            <ol class="entry-dots" aria-label="Progreso, paso {{ progressIndex(stage()) + 1 }} de 4">
              @for (dot of dots; track dot; let i = $index) {
                <li [attr.data-state]="progressState(i)">
                  <span class="sr-only">Paso {{ i + 1 }}</span>
                </li>
              }
            </ol>
          }

          @switch (stage()) {
            @case ('hello') {
              <div class="entry-step entry-hello">
                <div class="entry-lines">
                  <h1 class="entry-title">¡Hola! Soy Nuti y seré tu guía.</h1>
                  <p class="entry-ask">¿Qué es NutriMatch?</p>
                  <p class="entry-body">
                    NutriMatch es una herramienta que te ayuda a conocer, comparar y elegir productos
                    alimenticios de forma más sencilla.
                  </p>
                  <p class="entry-body">
                    Cuando buscas un producto, NutriMatch reúne información como su contenido
                    nutricional, nivel de procesamiento, ingredientes, etiquetas y otros datos
                    disponibles para que puedas compararlo con productos similares.
                  </p>
                  <p class="entry-body">
                    Tú eliges qué aspectos son más importantes para ti y NutriMatch los organiza para
                    ayudarte a interpretar la información.
                  </p>
                  <p class="entry-body">
                    No tienes que revisar todos los datos por tu cuenta: yo te ayudo a encontrar lo
                    esencial y te indico cuando la información de un producto es limitada.
                  </p>
                </div>
                <p class="entry-cue">Primero vamos a personalizar tu experiencia.</p>
                <div class="entry-actions">
                  <button type="button" class="btn btn-tide" (click)="go('name')">Empezar</button>
                </div>
              </div>
            }
            @case ('name') {
              <div class="entry-step">
                <h1 class="entry-title">Ahora quiero conocerte</h1>
                <p class="entry-hint">Tu nombre me ayudará a hacer la experiencia más cercana.</p>
                <label class="entry-field">
                  <span class="sr-only">Tu nombre</span>
                  <input
                    class="entry-name"
                    name="displayName"
                    autocomplete="given-name"
                    placeholder="Tu nombre"
                    [(ngModel)]="nameDraft"
                  />
                </label>
                @if (nameDraft.trim()) {
                  <p class="entry-greeting">Mucho gusto, {{ greetingName() }}.</p>
                }
                <div class="entry-actions">
                  <button type="button" class="entry-back" (click)="atras()">Atrás</button>
                  <button
                    type="button"
                    class="btn btn-tide"
                    [disabled]="!nameDraft.trim()"
                    (click)="continuarNombre()"
                  >
                    Continuar
                  </button>
                </div>
              </div>
            }
            @case ('prioridades') {
              <div class="entry-step">
                <h1 class="entry-title">¿Qué te importa más?</h1>
                <p class="entry-hint">Toca una tarjeta para ponerla primero.</p>
                <p class="entry-hint">La que esté arriba tendrá mayor peso en tu resultado.</p>
                <div class="entry-order">
                  @for (dim of priorityOrder(); track dim; let i = $index) {
                    <button
                      type="button"
                      class="entry-order-card"
                      [attr.data-lead]="i === 0 ? 'true' : null"
                      (click)="promover(dim)"
                    >
                      <span class="entry-order-n">{{ i + 1 }}</span>
                      <span>
                        <span class="choice-title"><span aria-hidden="true">{{ marks[dim] }}</span> {{ labels[dim] }}</span>
                        @if (i === 0) {
                          <span class="entry-order-lead">Pesa más</span>
                        }
                        <span class="choice-hint">{{ hints[dim] }}</span>
                      </span>
                    </button>
                  }
                </div>
                <div class="entry-folds">
                  <details class="entry-fold">
                    <summary>¿Qué significa procesamiento?</summary>
                    <p>
                      NOVA indica el nivel de procesamiento del alimento. El grupo 1 corresponde a
                      alimentos poco o nada procesados, mientras que el grupo 4 corresponde a
                      productos ultraprocesados.
                    </p>
                    <p>
                      Los aditivos son sustancias que pueden utilizarse, por ejemplo, para conservar,
                      dar color o modificar el sabor.
                    </p>
                    <p>Dentro de esta dimensión, una menor cantidad de aditivos favorece el resultado.</p>
                  </details>
                  <details class="entry-fold">
                    <summary>¿Qué son las etiquetas de preferencia?</summary>
                    <p>
                      Son sellos o características declaradas en el producto, como orgánico, sin
                      gluten, comercio ético, vegetariano o vegano.
                    </p>
                    <p>
                      Solo se consideran cuando el producto registra esa información y tú la has
                      elegido como preferencia.
                    </p>
                  </details>
                </div>
                <div class="entry-actions">
                  <button type="button" class="entry-back" (click)="atras()">Atrás</button>
                  <button type="button" class="btn btn-tide" (click)="go('cuidar')">Continuar</button>
                </div>
              </div>
            }
            @case ('cuidar') {
              <div class="entry-step">
                <h1 class="entry-title">¿Hay algo que quieras evitar o considerar?</h1>
                <p class="entry-kicker entry-group-label">Alimentación</p>
                <div class="entry-cards entry-cards-3">
                  <button type="button" class="choice-card" [attr.aria-pressed]="diet() === null" (click)="setDiet(null)">
                    <span class="choice-title">Sin preferencia</span>
                  </button>
                  <button type="button" class="choice-card" [attr.aria-pressed]="diet() === 'vegetariano'" (click)="setDiet('vegetariano')">
                    <span class="choice-title">Vegetariana</span>
                  </button>
                  <button type="button" class="choice-card" [attr.aria-pressed]="diet() === 'vegano'" (click)="setDiet('vegano')">
                    <span class="choice-title">Vegana</span>
                  </button>
                </div>
                <p class="entry-kicker entry-group-label">Evitar</p>
                <p class="entry-hint">Selecciona los ingredientes o alérgenos que quieras tener en cuenta:</p>
                <div class="entry-chips">
                  <button
                    type="button"
                    class="choice-chip"
                    [attr.aria-pressed]="allergenTags().length === 0"
                    (click)="elegirNinguno()"
                  >
                    Ninguno
                  </button>
                  @for (opt of allergens; track opt[0]) {
                    <button
                      type="button"
                      class="choice-chip choice-chip-avoid"
                      [attr.aria-pressed]="allergenTags().includes(opt[0])"
                      (click)="toggleAllergen(opt[0])"
                    >
                      {{ opt[1] }}
                    </button>
                  }
                </div>
                <p class="entry-note">
                  Si el registro de un producto no contiene información suficiente, te lo indicaré en
                  su ficha. No asumiré que un producto es apto cuando el dato no esté disponible.
                </p>
                <div class="entry-actions">
                  <button type="button" class="entry-back" (click)="atras()">Atrás</button>
                  <button type="button" class="entry-back" (click)="ahoraNo()">Ahora no</button>
                  <button type="button" class="btn btn-tide" (click)="go('resumen')">Continuar</button>
                </div>
              </div>
            }
            @case ('resumen') {
              <div class="entry-step">
                <h1 class="entry-title">Listo, {{ greetingName() }}.</h1>
                <p class="entry-body">
                  Con tus preferencias puedo organizar la información de los productos de acuerdo con
                  lo que te importa.
                </p>
                <p class="entry-invite">{{ priorityLine() }}</p>
                <p class="entry-body">{{ avoidLine() }}</p>
                <div class="entry-actions">
                  <button type="button" class="entry-back" (click)="atras()">Atrás</button>
                  <button type="button" class="btn btn-tide" (click)="entrar()">Entrar a NutriMatch</button>
                </div>
              </div>
            }
          }
        </div>
      </div>
    </section>
  `,
})
export class OnboardingPage {
  private readonly router = inject(Router);
  private readonly onboarding = inject(OnboardingStore);
  private readonly profiles = inject(ProfileStore);

  readonly allergens = ALLERGEN_CHOICES;
  readonly labels = PRIORITY_LABELS;
  readonly hints = DIMENSION_HINT;
  readonly marks = MARK;
  readonly dots = [0, 1, 2, 3];
  readonly progressIndex = progressIndex;

  readonly stage = signal<OnboardingStage>('hello');
  readonly diet = signal<DietaDeclarada | null>(null);
  readonly allergenTags = signal<string[]>([]);
  readonly priorityOrder = signal<DimensionPrioridad[]>(['D1', 'D2', 'D3']);
  private readonly valuedLabels = signal<string[]>([]);
  nameDraft = '';

  readonly showsProgress = computed(() => progressIndex(this.stage()) >= 0);
  readonly pose = computed(() => POSE[this.stage()]);
  readonly say = computed(() => SAY[this.stage()]);

  constructor() {
    const profile = this.profiles.profile();
    const saved = this.onboarding.state();
    this.nameDraft = saved.displayName;
    this.diet.set(profile.diet);
    this.allergenTags.set([...profile.allergenTags]);
    this.valuedLabels.set([...profile.valuedLabels]);
    if (profile.priorityOrder.length === 3) {
      this.priorityOrder.set([...profile.priorityOrder]);
    }
  }

  greetingName(): string {
    return firstName(this.nameDraft) || 'tú';
  }

  priorityLine(): string {
    return priorityClosing(this.greetingName(), this.priorityOrder()[0] ?? 'D1', this.diet());
  }

  avoidLine(): string {
    return avoidClosing(this.allergenNames());
  }

  allergenNames(): string[] {
    const selected = this.allergenTags();
    return ALLERGEN_CHOICES.filter(([tag]) => selected.includes(tag)).map(([, label]) => label);
  }

  progressState(index: number): 'done' | 'active' | 'todo' {
    const current = progressIndex(this.stage());
    if (index < current) {
      return 'done';
    }
    return index === current ? 'active' : 'todo';
  }

  go(stage: OnboardingStage): void {
    this.stage.set(stage);
  }

  atras(): void {
    const index = STAGE_ORDER.indexOf(this.stage());
    this.stage.set(STAGE_ORDER[Math.max(0, index - 1)] ?? 'hello');
  }

  continuarNombre(): void {
    if (!this.nameDraft.trim()) {
      return;
    }
    this.go('prioridades');
  }

  promover(dim: DimensionPrioridad): void {
    this.priorityOrder.update((order) => [dim, ...order.filter((item) => item !== dim)]);
  }

  setDiet(value: DietaDeclarada | null): void {
    this.diet.set(value);
  }

  elegirNinguno(): void {
    this.allergenTags.set(nextAllergenTags(this.allergenTags(), null));
  }

  toggleAllergen(tag: string): void {
    this.allergenTags.set(nextAllergenTags(this.allergenTags(), tag));
  }

  ahoraNo(): void {
    this.diet.set(null);
    this.allergenTags.set([]);
    this.go('resumen');
  }

  entrar(): void {
    const profile: UserProfile = {
      allergenTags: this.allergenTags(),
      diet: this.diet(),
      valuedLabels: this.valuedLabels(),
      priorityOrder: this.priorityOrder(),
    };
    this.profiles.save(profile);
    this.onboarding.complete({
      displayName: this.nameDraft.trim(),
      goals: [],
      nutritionFocus: [],
      considerPrice: false,
      dietOther: false,
    });
    void this.router.navigateByUrl('/');
  }
}
