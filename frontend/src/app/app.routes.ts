import { Routes } from '@angular/router';
import { requireOnboarding } from './core/data/onboarding.guard';
import { AlertsPage } from './pages/alerts.page';
import { CartPage } from './pages/cart.page';
import { ComparePage } from './pages/compare.page';
import { HistorialPage } from './pages/historial.page';
import { HomePage } from './pages/home.page';
import { OnboardingPage } from './pages/onboarding.page';
import { ProductPage } from './pages/product.page';
import { RecipesPage } from './pages/recipes.page';
import { RecommendationsPage } from './pages/recommendations.page';
import { CatalogPage } from './pages/catalog.page';
import { SearchPage } from './pages/search.page';

const app = [requireOnboarding];

export const routes: Routes = [
  { path: 'onboarding', component: OnboardingPage },
  { path: 'bienvenida', redirectTo: 'onboarding', pathMatch: 'full' },
  { path: 'dashboard', redirectTo: '', pathMatch: 'full' },
  { path: '', component: HomePage, canActivate: app },
  { path: 'buscar', component: SearchPage, canActivate: app },
  { path: 'catalogo', component: CatalogPage, canActivate: app },
  { path: 'producto/:code', component: ProductPage, canActivate: app },
  { path: 'recomendaciones', component: RecommendationsPage, canActivate: app },
  { path: 'comparar', component: ComparePage, canActivate: app },
  { path: 'carrito', component: CartPage, canActivate: app },
  { path: 'alertas', component: AlertsPage, canActivate: app },
  { path: 'recetas', component: RecipesPage, canActivate: app },
  { path: 'historial', component: HistorialPage, canActivate: app },
  { path: '**', redirectTo: '' },
];
