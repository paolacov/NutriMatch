import { NgTemplateOutlet } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { toObservable, toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { catchError, combineLatest, forkJoin, map, of, switchMap } from 'rxjs';
import { CartStore } from '../core/data/cart.store';
import { ProductRepository } from '../core/data/product.repository';
import { ProfileStore } from '../core/data/profile.store';
import { ALLERGEN_CHOICES, Product } from '../core/models/domain';
import { displayName, etiquetaDeSello } from '../shared/format';
import { ProductPhoto } from '../shared/product-photo/product-photo';
import { LoadingWell } from '../shared/loading-well/loading-well';
import { OtterGuide } from '../shared/otter-guide/otter-guide';
import { ShelfStamps } from '../shared/shelf-stamps/shelf-stamps';
import { CartAlternatives } from './cart-alternatives';

function excesoLabels(labels: string[]): string[] {
  return labels.filter((tag) => tag.includes('exceso'));
}

const EXCESO_NOMBRE: Record<string, string> = {
  'es:exceso-azucares': 'azúcares',
  'es:exceso-azúcares': 'azúcares',
  'es:exceso-calorias': 'calorías',
  'es:exceso-calorías': 'calorías',
  'es:exceso-grasas-saturadas': 'grasas saturadas',
  'es:exceso-grasas-trans': 'grasas trans',
  'es:exceso-sodio': 'sodio',
};

function lista(nombres: string[]): string {
  if (nombres.length <= 1) {
    return nombres[0] ?? '';
  }
  if (nombres.length === 2) {
    return `${nombres[0]} y ${nombres[1]}`;
  }
  return `${nombres.slice(0, -1).join(', ')} y ${nombres[nombres.length - 1]}`;
}

function nombreAlergeno(tag: string): string {
  const choice = ALLERGEN_CHOICES.find(([value]) => value === tag);
  return (choice?.[1] ?? etiquetaDeSello(tag)).toLocaleLowerCase('es-MX');
}

function nombreSello(tag: string): string {
  return EXCESO_NOMBRE[tag] ?? etiquetaDeSello(tag).toLocaleLowerCase('es-MX');
}

type Bucket = 'revisar' | 'verificar' | 'limpio';

@Component({
  selector: 'app-alerts-page',
  imports: [NgTemplateOutlet, RouterLink, OtterGuide, ShelfStamps, LoadingWell, CartAlternatives, ProductPhoto],
  template: `
    <section class="alertas">
      <p class="page-kicker">Revisar</p>
      <h1 class="page-title">Alertas</h1>
      <p class="text-sm text-mute">
        Los sellos son etiquetado frontal NOM-051. Informan; no diagnostican ni puntúan.
      </p>
      @if (!cart.codes().length) {
        <div class="empty-well">
          <app-otter-guide variant="empty" size="compact" />
          <p>El carrito está vacío. Cuando agregues productos, aquí te cuento si tienen sellos o si no encajan con tus alergias y tu dieta.</p>
          <a routerLink="/carrito" class="btn btn-tide">Ir al carrito</a>
        </div>
      } @else if (!products().length) {
        <app-loading-well label="Cargando alertas…" />
      } @else {
        <app-otter-guide variant="alert" [caption]="nutiLine()" />

        <div class="alert-ribbon" aria-label="Resumen">
          @for (chip of chips(); track chip.kind) {
            <p class="alert-count" [attr.data-kind]="chip.kind">
              <strong>{{ chip.n }}</strong>
              <span>{{ chip.label }}</span>
            </p>
          }
        </div>

        @if (revisar().length) {
          <section class="alert-block" data-block="revisar">
            <h2>Conviene revisar</h2>
            <p class="alert-block-note">
              @if (declaro()) {
                Tienen un sello de exceso o no encajan con lo que declaraste.
              } @else {
                Tienen un sello de exceso. Aún no hay alergias ni dieta para comparar.
              }
            </p>
            <ul class="alert-list">
              @for (p of revisar(); track p.code) {
                <li class="alert-card" [attr.data-alert]="visualTone(p)">
                  <div class="alert-main">
                    <span class="alert-photo">
                      <app-product-photo [imageUrl]="p.imageUrl" [category]="p.category" alt="" />
                    </span>
                    <div class="alert-body">
                      <a [routerLink]="['/producto', p.code]" class="alert-name">{{ displayName(p) }}</a>
                      <p class="alert-brand">{{ p.brand.value ?? 'Marca no disponible' }}</p>
                      <p class="alert-headline" [attr.data-tone]="visualTone(p)">{{ titulo(p) }}</p>
                    </div>
                  </div>
                  @for (motivo of motivos(p); track motivo) {
                    <p class="mt-1 text-sm">{{ motivo }}</p>
                  }
                  @if (faltaLine(p); as falta) {
                    <p class="mt-1 text-sm text-mute">{{ falta }}</p>
                  }
                  @if (excesoLabels(p.labels).length || p.allergens.length) {
                    <div class="mt-3">
                      <app-shelf-stamps
                        [labels]="excesoLabels(p.labels)"
                        [allergens]="p.allergens"
                        [highlightAllergens]="profile.profile().allergenTags"
                      />
                    </div>
                  }
                  <div class="alert-actions">
                    <a class="btn btn-ghost btn-sm" [routerLink]="['/producto', p.code]">Ver producto</a>
                    <button
                      type="button"
                      class="btn btn-sm"
                      [class.btn-tide]="openCode() !== p.code"
                      [class.btn-ghost]="openCode() === p.code"
                      [attr.aria-expanded]="openCode() === p.code"
                      (click)="explorar(p.code)"
                    >
                      {{ openCode() === p.code ? 'Cerrar alternativas' : 'Explorar alternativas' }}
                    </button>
                    <button type="button" class="btn btn-vest btn-sm" (click)="cart.remove(p.code)">
                      Quitar del carrito
                    </button>
                  </div>
                  @if (openCode() === p.code) {
                    <app-cart-alternatives [code]="p.code" />
                  }
                </li>
              }
            </ul>
          </section>
        }

        @if (verificar().length) {
          @if (revisar().length) {
            <details class="alert-fold">
              <summary>{{ fraseConteo(verificar().length, 'sin dato suficiente', 'sin dato suficiente') }}</summary>
              <ng-container *ngTemplateOutlet="verificarBloque" />
            </details>
          } @else {
            <ng-container *ngTemplateOutlet="verificarBloque" />
          }
        }

        @if (limpios().length) {
          @if (revisar().length || verificar().length) {
            <details class="alert-fold">
              <summary>{{ fraseLimpios(limpios().length) }}</summary>
              <ng-container *ngTemplateOutlet="limpioBloque" />
            </details>
          } @else {
            <ng-container *ngTemplateOutlet="limpioBloque" />
          }
        }

        <ng-template #verificarBloque>
          <section class="alert-block" data-block="verificar">
            <h2>Falta información</h2>
            <p class="alert-block-note">
              El registro no trae el dato de alérgenos o de dieta. No se puede afirmar que encajen.
            </p>
            <ul class="alert-list">
              @for (p of verificar(); track p.code) {
                <li class="alert-card" data-alert="no_verificable">
                  <div class="alert-main">
                    <span class="alert-photo">
                      <app-product-photo [imageUrl]="p.imageUrl" [category]="p.category" alt="" />
                    </span>
                    <div class="alert-body">
                      <a [routerLink]="['/producto', p.code]" class="alert-name">{{ displayName(p) }}</a>
                      <p class="alert-brand">{{ p.brand.value ?? 'Marca no disponible' }}</p>
                      <p class="alert-headline" data-tone="no_verificable">{{ faltaLine(p) }}</p>
                    </div>
                  </div>
                  <div class="alert-actions">
                    <a class="btn btn-ghost btn-sm" [routerLink]="['/producto', p.code]">Ver producto</a>
                  </div>
                </li>
              }
            </ul>
          </section>
        </ng-template>

        <ng-template #limpioBloque>
          <section class="alert-block" data-block="limpio">
            <h2>{{ declaro() ? 'Sin alerta con tu perfil' : 'Sin sello de exceso' }}</h2>
            <p class="alert-block-note">
              @if (declaro()) {
                Se pueden comprobar con lo que declaraste y no tienen sello de exceso.
              } @else {
                No traen un sello NOM-051 de exceso.
              }
            </p>
            <ul class="alert-list">
              @for (p of limpios(); track p.code) {
                <li class="alert-card" data-alert="ok">
                  <div class="alert-main">
                    <span class="alert-photo">
                      <app-product-photo [imageUrl]="p.imageUrl" [category]="p.category" alt="" />
                    </span>
                    <div class="alert-body">
                      <a [routerLink]="['/producto', p.code]" class="alert-name">{{ displayName(p) }}</a>
                      <p class="alert-brand">{{ p.brand.value ?? 'Marca no disponible' }}</p>
                      <p class="alert-headline" data-tone="ok">{{ titulo(p) }}</p>
                    </div>
                  </div>
                  <div class="alert-actions">
                    <a class="btn btn-ghost btn-sm" [routerLink]="['/producto', p.code]">Ver producto</a>
                  </div>
                </li>
              }
            </ul>
          </section>
        </ng-template>
      }
    </section>
  `,
})
export class AlertsPage {
  readonly cart = inject(CartStore);
  readonly profile = inject(ProfileStore);
  private readonly repo = inject(ProductRepository);
  readonly displayName = displayName;
  readonly excesoLabels = excesoLabels;
  readonly openCode = signal<string | null>(null);

  readonly products = toSignal(
    combineLatest([toObservable(this.cart.codes), toObservable(this.profile.profile)]).pipe(
      switchMap(([codes, profile]) => {
        if (!codes.length) {
          return of([]);
        }
        return forkJoin(
          codes.map((code) => this.repo.explain(code, profile).pipe(catchError(() => of(undefined)))),
        ).pipe(map((rows) => rows.filter((p): p is Product => !!p)));
      }),
    ),
    { initialValue: [] },
  );

  readonly declaro = computed(
    () => this.profile.profile().allergenTags.length > 0 || !!this.profile.profile().diet,
  );

  readonly revisar = computed(() =>
    this.products()
      .filter((p) => this.bucket(p) === 'revisar')
      .sort((a, b) => Number(this.cardTone(a) !== 'no_apto') - Number(this.cardTone(b) !== 'no_apto')),
  );

  readonly verificar = computed(() => this.products().filter((p) => this.bucket(p) === 'verificar'));

  readonly limpios = computed(() => this.products().filter((p) => this.bucket(p) === 'limpio'));

  readonly chips = computed(() => {
    const revisar = this.revisar().length;
    const verificar = this.verificar().length;
    const limpios = this.limpios().length;
    if (!this.declaro()) {
      return [
        revisar ? { kind: 'revisar', n: revisar, label: 'con sello de exceso' } : null,
        limpios ? { kind: 'limpio', n: limpios, label: 'sin sello de exceso' } : null,
      ].filter((chip): chip is { kind: string; n: number; label: string } => !!chip);
    }
    return [
      { kind: 'revisar', n: revisar, label: 'para revisar' },
      { kind: 'verificar', n: verificar, label: 'sin dato suficiente' },
      { kind: 'limpio', n: limpios, label: 'sin alerta' },
    ].filter((chip) => chip.n > 0);
  });

  explorar(code: string): void {
    this.openCode.update((actual) => (actual === code ? null : code));
  }

  fraseConteo(n: number, uno: string, varios: string): string {
    return n === 1 ? `1 producto ${uno}` : `${n} productos ${varios}`;
  }

  fraseLimpios(n: number): string {
    if (this.declaro()) {
      return this.fraseConteo(n, 'sin alerta con tu perfil', 'sin alerta con tu perfil');
    }
    return this.fraseConteo(n, 'sin sello de exceso', 'sin sello de exceso');
  }

  nutiLine(): string {
    const revisar = this.revisar().length;
    const verificar = this.verificar().length;
    const limpios = this.limpios().length;
    if (!this.declaro()) {
      if (!revisar) {
        return 'Ningún producto del carrito trae un sello de exceso. Si declaras alergias o dieta, también las reviso aquí.';
      }
      const sello =
        revisar === 1 ? '1 producto tiene sello de exceso' : `${revisar} productos tienen sello de exceso`;
      return `${sello}. Aún no declaraste alergias ni dieta, así que eso no lo puedo revisar.`;
    }
    if (!revisar && !verificar) {
      return limpios === 1
        ? 'Este producto se puede comprobar con tu perfil y no tiene una alerta.'
        : 'Estos productos se pueden comprobar con tu perfil y no tienen una alerta.';
    }
    const partes: string[] = [];
    if (revisar === 1) {
      partes.push('Hay 1 producto que conviene revisar');
    } else if (revisar > 1) {
      partes.push(`Hay ${revisar} productos que conviene revisar`);
    }
    if (verificar === 1) {
      partes.push('en 1 falta información para verificarlo');
    } else if (verificar > 1) {
      partes.push(`en ${verificar} falta información para verificarlos`);
    }
    if (!revisar && limpios === 1) {
      partes.push('1 no tiene alerta con tu perfil');
    } else if (!revisar && limpios > 1) {
      partes.push(`${limpios} no tienen alerta con tu perfil`);
    }
    const texto = partes
      .map((parte) => `${parte.charAt(0).toUpperCase()}${parte.slice(1)}`)
      .join('. ');
    return `${texto}.`;
  }

  titulo(product: Product): string {
    if (this.cardTone(product) === 'no_apto') {
      return 'Conviene revisarlo';
    }
    if (excesoLabels(product.labels).length) {
      return 'Tiene sello de exceso';
    }
    if (this.bucket(product) === 'verificar') {
      return this.faltaLine(product) ?? 'Falta información para verificarlo';
    }
    if (this.declaro()) {
      return 'Sin alerta con tu perfil';
    }
    return 'Sin sello de exceso';
  }

  motivos(product: Product): string[] {
    const profile = this.profile.profile();
    const motivos: string[] = [];
    if (profile.allergenTags.length && product.fit.allergyStatus === 'no_apto') {
      const confirmados = profile.allergenTags
        .filter((tag) => product.allergens.includes(tag))
        .map(nombreAlergeno);
      const posibles = profile.allergenTags
        .filter((tag) => product.traces.includes(tag) && !product.allergens.includes(tag))
        .map(nombreAlergeno);
      if (confirmados.length && posibles.length) {
        motivos.push(`Incluye ${lista(confirmados)} y puede contener ${lista(posibles)}.`);
      } else if (confirmados.length) {
        motivos.push(`Incluye ${lista(confirmados)}.`);
      } else if (posibles.length) {
        motivos.push(`Puede contener ${lista(posibles)}.`);
      } else {
        motivos.push('No encaja con una alergia de tu perfil.');
      }
    }
    if (profile.diet && product.fit.dietStatus === 'incompatible') {
      motivos.push(
        profile.diet === 'vegano' ? 'No encaja con una dieta vegana.' : 'No encaja con una dieta vegetariana.',
      );
    }
    const sellos = excesoLabels(product.labels).map(nombreSello);
    if (sellos.length === 1) {
      motivos.push(`Tiene sello de exceso de ${sellos[0]}.`);
    } else if (sellos.length > 1) {
      motivos.push(`Tiene sellos de exceso de ${lista(sellos)}.`);
    }
    return motivos;
  }

  faltaLine(product: Product): string | null {
    const profile = this.profile.profile();
    const alergia = profile.allergenTags.length > 0 && product.fit.allergyStatus === 'no_verificable';
    const dieta = !!profile.diet && product.fit.dietStatus === 'no_verificable';
    if (alergia && dieta) {
      return 'Falta información de alérgenos y de dieta.';
    }
    if (alergia) {
      return 'Falta información de alérgenos.';
    }
    if (dieta) {
      return 'Falta información de dieta.';
    }
    return null;
  }

  visualTone(product: Product): string {
    if (this.cardTone(product) === 'no_apto') {
      return 'no_apto';
    }
    if (excesoLabels(product.labels).length) {
      return 'sello';
    }
    if (this.bucket(product) === 'verificar') {
      return 'no_verificable';
    }
    return 'ok';
  }

  bucket(product: Product): Bucket {
    if (this.cardTone(product) === 'no_apto' || excesoLabels(product.labels).length) {
      return 'revisar';
    }
    if (this.cardTone(product) === 'no_verificable') {
      return 'verificar';
    }
    return 'limpio';
  }

  cardTone(product: Product): string {
    const diet = this.profile.profile().diet;
    if (product.fit.allergyStatus === 'no_apto' || (diet && product.fit.dietStatus === 'incompatible')) {
      return 'no_apto';
    }
    if (product.fit.allergyStatus === 'no_verificable' || (diet && product.fit.dietStatus === 'no_verificable')) {
      return 'no_verificable';
    }
    if (excesoLabels(product.labels).length) {
      return 'sello';
    }
    return 'ok';
  }
}
