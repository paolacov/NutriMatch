import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, map, startWith } from 'rxjs';
import { CartStore } from './core/data/cart.store';
import { OnboardingStore } from './core/data/onboarding.store';
import { ProfileStore } from './core/data/profile.store';
import { ProfilePanel } from './shared/profile-panel/profile-panel';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ProfilePanel],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  private readonly router = inject(Router);
  readonly cart = inject(CartStore);
  readonly onboarding = inject(OnboardingStore);
  readonly profile = inject(ProfileStore);
  readonly onboardingChrome = toSignal(
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      map((event) => event.urlAfterRedirects.startsWith('/onboarding')),
      startWith(this.router.url.startsWith('/onboarding')),
    ),
    { initialValue: this.router.url.startsWith('/onboarding') },
  );

  prefTitle(): string {
    const name = this.onboarding.firstName();
    return name ? `Hola, ${name}` : 'Tus preferencias';
  }

  cartAriaLabel(): string {
    const n = this.cart.count();
    if (n === 1) {
      return 'Carrito, 1 producto';
    }
    return `Carrito, ${n} productos`;
  }

  readonly links = [
    { path: '/', label: 'Inicio', exact: true },
    { path: '/buscar', label: 'Buscar' },
    { path: '/catalogo', label: 'Catálogo' },
    { path: '/recomendaciones', label: 'Para ti' },
    { path: '/comparar', label: 'Comparar' },
    { path: '/alertas', label: 'Alertas' },
    { path: '/recetas', label: 'Recetas' },
    { path: '/historial', label: 'Historial' },
  ];

  readonly dock = [
    { path: '/', label: 'Inicio', exact: true },
    { path: '/buscar', label: 'Buscar' },
    { path: '/catalogo', label: 'Catálogo' },
    { path: '/recomendaciones', label: 'Para ti' },
    { path: '/carrito', label: 'Carrito' },
  ];
}
