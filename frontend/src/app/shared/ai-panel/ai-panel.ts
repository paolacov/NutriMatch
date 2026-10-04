import { Component, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { inject } from '@angular/core';
import { AiAskResult, AiIntent, AiSurface } from '../../core/models/domain';
import { ProductRepository } from '../../core/data/product.repository';
import { ProfileStore } from '../../core/data/profile.store';

@Component({
  selector: 'app-ai-panel',
  imports: [FormsModule],
  template: `
    <section class="ai-panel card-paper p-5">
      <div class="ai-bubble">
        <img src="/brand/otter-avatar.png" alt="" />
        <div class="ai-bubble-copy">
          <h2>Preguntar a NutriMatch</h2>
          <p>Explica lo que el motor ya calculó. No cambia el score ni el ranking.</p>
        </div>
      </div>
      @if (suggestions().length) {
        <div class="flex flex-wrap gap-2">
          @for (s of suggestions(); track s) {
            <button type="button" class="btn btn-ghost btn-sm" (click)="usar(s)">
              {{ s }}
            </button>
          }
        </div>
      }
      <form class="flex flex-col gap-2 sm:flex-row" (ngSubmit)="enviar()">
        <label class="sr-only" for="ai-q">Pregunta</label>
        <input
          id="ai-q"
          name="aiq"
          class="field-paper flex-1 px-4 py-2"
          [placeholder]="placeholder()"
          [(ngModel)]="pregunta"
        />
        <button type="submit" class="btn btn-tide" [disabled]="cargando()">
          {{ cargando() ? 'Pensando…' : 'Preguntar' }}
        </button>
      </form>
      @if (resultado(); as r) {
        <p class="text-sm">{{ r.text }}</p>
        <p class="text-xs text-mute">
          @if (r.source === 'llm' && !r.fallback) {
            Texto de la capa de lenguaje. Los números siguen siendo del motor.
          } @else {
            Texto de respaldo (plantilla). La capa de lenguaje no sustituyó al motor.
          }
        </p>
        @if (r.recipe; as rec) {
          <div class="text-sm">
            <p class="font-semibold">{{ rec.name }}</p>
            @if (rec.availableIngredients.length) {
              <p class="mt-1"><span class="text-mute">Observados:</span> {{ rec.availableIngredients.join(', ') }}</p>
            }
            @if (rec.extraSuggested.length) {
              <p><span class="text-mute">Sugeridos (no están en el catálogo):</span> {{ rec.extraSuggested.join(', ') }}</p>
            }
            @if (rec.steps.length) {
              <ol class="mt-2 list-decimal space-y-1 pl-5">
                @for (paso of rec.steps; track $index) {
                  <li>{{ paso }}</li>
                }
              </ol>
            }
            <p class="mt-1 text-xs text-mute">{{ rec.nutritionNote }}</p>
          </div>
        }
      }
    </section>
  `,
})
export class AiPanel {
  private readonly repo = inject(ProductRepository);
  private readonly profiles = inject(ProfileStore);

  readonly surface = input.required<AiSurface>();
  readonly codes = input<string[]>([]);
  readonly intent = input<AiIntent>('ask');
  readonly placeholder = input('Pregunta sobre este contexto');
  readonly suggestions = input<string[]>([]);
  readonly culinaryGoal = input<string | undefined>(undefined);

  pregunta = '';
  readonly cargando = signal(false);
  readonly resultado = signal<AiAskResult | null>(null);

  usar(texto: string): void {
    this.pregunta = texto;
    this.enviar();
  }

  enviar(): void {
    const message = this.pregunta.trim();
    if (!message && this.intent() === 'ask') {
      return;
    }
    this.cargando.set(true);
    this.repo
      .askAi({
        surface: this.surface(),
        codes: this.codes(),
        profile: this.profiles.profile(),
        intent: this.intent(),
        message: message || undefined,
        culinaryGoal: this.culinaryGoal(),
      })
      .subscribe((row) => {
        this.resultado.set(row);
        this.cargando.set(false);
      });
  }
}
