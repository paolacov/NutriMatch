import { Component, inject } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { catchError, map, of, startWith, switchMap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { BUNDLE_VACIO, ProductRepository } from '../core/data/product.repository';
import { ALLERGEN_CHOICES, PRIORITY_LABELS } from '../core/models/domain';
import { ProfileStore } from '../core/data/profile.store';
import { LoadingWell } from '../shared/loading-well/loading-well';
import { OtterGuide } from '../shared/otter-guide/otter-guide';
import { ProductCard } from '../shared/product-card/product-card';

@Component({
  selector: 'app-recommendations-page',
  imports: [OtterGuide, ProductCard, LoadingWell],
  template: `
    <section class="para-ti">
      <header class="para-hero">
        <p class="page-kicker">Para ti</p>
        <h1 class="page-title">Descubre opciones para ti</h1>
        <app-otter-guide variant="result" [caption]="nutiLine" />
      </header>

      <section class="para-search" aria-label="Así estoy buscando">
        <h2>Así estoy buscando</h2>
        @if (etiquetas().length) {
          <p class="para-lead">Estoy tomando en cuenta tus preferencias:</p>
          <ul class="para-prefs">
            @for (tag of etiquetas(); track tag) {
              <li>{{ tag }}</li>
            }
          </ul>
        }
        <button type="button" class="btn btn-tide" (click)="profile.openPanel()">Editar preferencias</button>
      </section>

      @if (state(); as s) {
        @if (s.loading) {
          <app-loading-well label="Buscando opciones para ti…" />
        } @else {
          <section class="para-section">
            <h2>Opciones que encajan contigo</h2>
            <p class="para-lead">Productos con información suficiente, ordenados según tus preferencias.</p>
            @if (s.bundle.ranking.length) {
              <div class="shelf-grid">
                @for (p of s.bundle.ranking; track p.code) {
                  <app-product-card mode="discover" tone="fit" [product]="p" (add)="cart.add($event)" />
                }
              </div>
            } @else {
              <p class="para-empty">Por ahora no hay opciones con información suficiente para este perfil.</p>
            }
          </section>

          <section class="para-section">
            <h2>Algunas opciones necesitan más información</h2>
            <p class="para-lead">
              Encontramos estos productos, pero nos falta información para confirmar qué tan bien encajan contigo.
            </p>
            @if (s.bundle.noVerificable.length) {
              <div class="shelf-grid">
                @for (p of s.bundle.noVerificable; track p.code) {
                  <app-product-card mode="discover" tone="gap" [product]="p" (add)="cart.add($event)" />
                }
              </div>
            } @else {
              <p class="para-empty">Ninguna opción de esta lista necesita un dato extra.</p>
            }
          </section>

          <section class="para-section">
            <h2>Información pendiente</h2>
            <p class="para-lead">
              Estos productos tienen algunos datos incompletos. Puedes consultarlos, pero NutriMatch no puede
              confirmar su compatibilidad con tu perfil.
            </p>
            @if (s.bundle.insuficiente.length) {
              <div class="shelf-grid">
                @for (p of s.bundle.insuficiente; track p.code) {
                  <app-product-card mode="discover" tone="pending" [product]="p" (add)="cart.add($event)" />
                }
              </div>
            } @else {
              <p class="para-empty">Ningún producto de esta lista tiene información pendiente.</p>
            }
            </section>
        }
      }
    </section>
  `,
})
export class RecommendationsPage {
  readonly cart = inject(CartStore);
  readonly profile = inject(ProfileStore);
  private readonly repo = inject(ProductRepository);
  readonly nutiLine =
    '¡Encontré algunas opciones que podrían encajar contigo! Las ordené según tus preferencias para que puedas explorarlas y decidir cuál te interesa.';

  readonly state = toSignal(
    toObservable(this.profile.profile).pipe(
      switchMap((profile) =>
        this.repo.recommendations(profile).pipe(
          map((bundle) => ({ loading: false, bundle })),
          startWith({ loading: true, bundle: BUNDLE_VACIO }),
          catchError(() => of({ loading: false, bundle: BUNDLE_VACIO })),
        ),
      ),
    ),
  );

  etiquetas(): string[] {
    const perfil = this.profile.profile();
    const tags: string[] = [];
    const evitar = this.listaHumana(
      ALLERGEN_CHOICES.filter(([tag]) => perfil.allergenTags.includes(tag)).map(([, label]) => label),
    );
    if (evitar) {
      tags.push(`🚫 Evitar ${evitar}`);
    }
    if (perfil.diet === 'vegetariano') {
      tags.push('🌱 Dieta vegetariana');
    } else if (perfil.diet === 'vegano') {
      tags.push('🌱 Dieta vegana');
    }
    const orden = perfil.priorityOrder.map((key) => PRIORITY_LABELS[key].toLocaleLowerCase('es-MX'));
    if (orden.length) {
      tags.push(`⭐ Prioridad: ${orden.join(' · ')}`);
    }
    return tags;
  }

  private listaHumana(nombres: string[]): string | null {
    const bajos = nombres.map((nombre) => nombre.toLocaleLowerCase('es-MX'));
    if (!bajos.length) {
      return null;
    }
    if (bajos.length === 1) {
      return bajos[0];
    }
    if (bajos.length === 2) {
      return `${bajos[0]} y ${bajos[1]}`;
    }
    return `${bajos.slice(0, -1).join(', ')} y ${bajos[bajos.length - 1]}`;
  }
}
