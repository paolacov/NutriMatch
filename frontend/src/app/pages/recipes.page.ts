import { Component, HostListener, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { map, of, startWith, switchMap, tap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { ProductRepository } from '../core/data/product.repository';
import { ProfileStore } from '../core/data/profile.store';
import { OtterGuide } from '../shared/otter-guide/otter-guide';
import {
  RECIPES_COPY,
  RecipeIdea,
  RecipeShelfItem,
  recipeCardsFromDrafts,
  recipesAskInput,
  shelfItems,
} from './recipes.query';

type RecipeView =
  | { kind: 'empty' }
  | { kind: 'loading'; chips: RecipeShelfItem[] }
  | { kind: 'none'; chips: RecipeShelfItem[] }
  | { kind: 'ok'; chips: RecipeShelfItem[]; ideas: RecipeIdea[] };

@Component({
  selector: 'app-recipes-page',
  imports: [RouterLink, OtterGuide],
  template: `
    <section class="recipes-page space-y-6" [attr.inert]="seleccion() ? '' : null">
      @if (view(); as v) {
        <div class="recipes-stage" [class.recipes-stage-split]="v.kind !== 'empty' && v.chips.length">
          <header class="recipes-hero-copy">
            <p class="recipes-kicker">{{ copy.kicker }}</p>
            <h1 class="recipes-title">{{ copy.title }}</h1>
            <p class="recipes-lead">{{ copy.subtitle }}</p>
          </header>

          <div class="recipes-meet">
            <app-otter-guide variant="recipes" size="host" [showLine]="false" />
            <div class="recipes-meet-talk">
              <p class="recipes-meet-line">{{ nutiLine() }}</p>
              @if (v.kind !== 'empty' && v.chips.length) {
                <aside class="recipes-pantry" [attr.aria-label]="copy.shelfKicker">
                  <div class="recipes-pantry-head">
                    <div>
                      <h2 class="recipes-pantry-title">{{ copy.shelfKicker }}</h2>
                      <p class="recipes-pantry-hint">{{ copy.shelfHint }}</p>
                    </div>
                    <p class="recipes-pantry-count">{{ v.chips.length }}</p>
                  </div>
                  <ul class="recipe-shelf-list">
                    @for (item of v.chips; track item.code) {
                      <li class="recipe-shelf-item">
                        <span class="recipe-shelf-photo">
                          <img [src]="item.imageSrc" [alt]="" [class.catalog-ph]="item.usesPlaceholder" />
                        </span>
                        <p class="recipe-chip-name">{{ item.displayName }}</p>
                        @if (item.quantity) {
                          <p class="recipe-chip-qty">{{ item.quantity }}</p>
                        }
                      </li>
                    }
                  </ul>
                </aside>
              }
            </div>
          </div>
        </div>

        @if (v.kind === 'empty') {
          <div class="recipes-state empty-well">
            <p>{{ copy.emptyBody }}</p>
            <a routerLink="/catalogo" class="btn btn-tide">{{ copy.explore }}</a>
          </div>
        } @else {

          @if (v.kind === 'loading') {
            <p class="recipes-bridge">{{ copy.bridge }}</p>
            <div class="recipe-grid" data-count="3" aria-hidden="true">
              @for (slot of skeletons; track slot) {
                <article class="recipe-card recipe-card-skel card-paper">
                  <div class="recipe-card-photo recipe-skel-block"></div>
                  <div class="recipe-skel-line"></div>
                  <div class="recipe-skel-line recipe-skel-short"></div>
                  <div class="recipe-skel-line recipe-skel-chip"></div>
                </article>
              }
            </div>
          } @else if (v.kind === 'none') {
            <div class="recipes-state empty-well">
              <p>{{ copy.noneBody }}</p>
              <a routerLink="/catalogo" class="btn btn-tide">{{ copy.explore }}</a>
            </div>
          } @else {
            <section class="recipes-ideas" [attr.aria-label]="copy.cardsKicker">
              <div class="recipe-grid" [attr.data-count]="v.ideas.length">
                @for (idea of v.ideas; track idea.id) {
                  <article class="recipe-card card-paper">
                    <div class="recipe-card-photo">
                      <img [src]="idea.imageSrc" [alt]="idea.imageAlt" />
                    </div>
                    <h3 class="recipe-card-title">{{ idea.title }}</h3>
                    @if (idea.description) {
                      <p class="recipe-card-desc">{{ idea.description }}</p>
                    }
                    <button type="button" class="btn btn-tide recipe-card-cta" (click)="abrir(idea)">
                      {{ copy.openRecipe }}
                    </button>
                  </article>
                }
              </div>
            </section>
          }
        }
      }
    </section>

    @if (seleccion(); as idea) {
      <button
        type="button"
        class="recipe-modal-scrim"
        [attr.aria-label]="copy.close"
        (click)="cerrar()"
      ></button>
      <aside
        class="recipe-modal"
        role="dialog"
        aria-modal="true"
        [attr.aria-labelledby]="'recipe-modal-title'"
      >
        <div class="recipe-modal-toolbar">
          <button type="button" class="btn btn-ghost btn-sm" (click)="cerrar()">{{ copy.close }}</button>
        </div>
        <div class="recipe-modal-guide">
          <app-otter-guide variant="recipes" size="mini" [caption]="copy.modalCue" />
        </div>
        <div class="recipe-modal-intro">
          <h2 id="recipe-modal-title" class="recipe-modal-title">{{ idea.title }}</h2>
          @if (idea.description) {
            <p class="recipe-modal-desc">{{ idea.description }}</p>
          }
        </div>
        <section class="recipe-modal-block">
          <h3 class="recipe-detail-kicker">{{ copy.haveKicker }}</h3>
          <ul class="recipe-chip-row">
            @for (item of idea.usedItems; track item.code) {
              <li>
                <span class="recipe-chip">
                  <img [src]="item.imageSrc" [alt]="" [class.catalog-ph]="item.usesPlaceholder" />
                  <span class="recipe-chip-name">{{ item.displayName }}</span>
                </span>
              </li>
            }
          </ul>
        </section>
        <section class="recipe-modal-block">
          <h3 class="recipe-detail-kicker">{{ copy.needKicker }}</h3>
          @if (idea.extras.length) {
            <ul class="recipe-list">
              @for (extra of idea.extras; track extra) {
                <li>{{ extra }}</li>
              }
            </ul>
          } @else {
            <p class="recipe-modal-desc">{{ copy.needNone }}</p>
          }
        </section>
        <section class="recipe-modal-block">
          <h3 class="recipe-detail-kicker">{{ copy.stepsKicker }}</h3>
          <ol class="recipe-steps">
            @for (paso of idea.steps; track $index) {
              <li>{{ paso }}</li>
            }
          </ol>
        </section>
      </aside>
    }
  `,
})
export class RecipesPage {
  readonly copy = RECIPES_COPY;
  readonly cart = inject(CartStore);
  readonly skeletons = [0, 1, 2];
  private readonly repo = inject(ProductRepository);
  private readonly profiles = inject(ProfileStore);

  readonly seleccion = signal<RecipeIdea | null>(null);

  readonly view = toSignal(
    toObservable(this.cart.codes).pipe(
      switchMap((codes) => {
        const pedido = recipesAskInput(codes);
        if (!pedido) {
          return of({ kind: 'empty' } satisfies RecipeView).pipe(
            tap(() => this.seleccion.set(null)),
          );
        }
        return this.repo.byCodes(pedido.codes).pipe(
          switchMap((items) => {
            const chipsIniciales = shelfItems(items);
            const nombres = chipsIniciales.map((item) => item.displayName).join(', ');
            return this.repo
              .askAi({
                surface: 'recipes',
                codes: pedido.codes,
                profile: this.profiles.profile(),
                intent: 'recipe',
                message: nombres
                  ? `Dame al menos 3 ideas de platillo con ${nombres}. Pueden usar solo uno o varios juntos.`
                  : 'Dame al menos 3 ideas de platillo con lo que tengo en el carrito. Pueden usar solo uno o varios juntos.',
                culinaryGoal:
                  'Propón al menos 3 platillos distintos. Válido usar un producto o varios juntos. Máximo 5 pasos cortos por idea.',
              })
              .pipe(
                map((row) => {
                  const chips = shelfItems(items, row.recipeProducts);
                  const ideas = recipeCardsFromDrafts(row.recipes, items, row.recipeProducts);
                  if (!ideas.length) {
                    return { kind: 'none' as const, chips };
                  }
                  return { kind: 'ok' as const, chips, ideas };
                }),
                startWith({ kind: 'loading' as const, chips: chipsIniciales }),
              );
          }),
          startWith({ kind: 'loading' as const, chips: [] }),
        );
      }),
    ),
    {
      initialValue: this.cart.codes().length
        ? ({ kind: 'loading', chips: [] } satisfies RecipeView)
        : ({ kind: 'empty' } satisfies RecipeView),
    },
  );

  nutiLine(): string {
    const v = this.view();
    if (v.kind === 'empty') {
      return this.copy.nutiEmpty;
    }
    if (v.kind === 'loading') {
      return this.copy.nutiLoading;
    }
    if (v.kind === 'none') {
      return this.copy.nutiNone;
    }
    return this.copy.nutiOk;
  }

  abrir(idea: RecipeIdea): void {
    this.seleccion.set(idea);
  }

  cerrar(): void {
    this.seleccion.set(null);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.cerrar();
  }
}
