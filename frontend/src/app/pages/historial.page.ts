import { DatePipe } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { map, of, switchMap } from 'rxjs';
import { ProductRepository } from '../core/data/product.repository';
import { EventType, Product, UsageEvent } from '../core/models/domain';
import { catalogPlaceholderSrc, historialProductName, usableProductImage } from '../shared/format';
import { LoadingWell } from '../shared/loading-well/loading-well';
import { OtterGuide } from '../shared/otter-guide/otter-guide';

const EVENT_LABELS: Record<EventType, string> = {
  cart_item_added: 'Agregaste al carrito',
  cart_item_removed: 'Quitaste del carrito',
  ranking_run_created: 'Viste recomendaciones',
  product_viewed: 'Consultaste un producto',
};

interface HistorialRow {
  event: UsageEvent;
  code: string | null;
  product: Product | undefined;
}

interface HistorialDay {
  key: string;
  label: string;
  rows: HistorialRow[];
}

@Component({
  selector: 'app-historial-page',
  imports: [DatePipe, RouterLink, LoadingWell, OtterGuide],
  template: `
    <section class="historial">
      <header class="historial-hero">
        <p class="historial-kicker">Lo que hiciste</p>
        <h1 class="historial-title">Historial</h1>
        <p class="historial-lead">Lo que viste, agregaste o quitaste. Esto no cambia cómo te recomendamos.</p>
      </header>

      @if (rows(); as list) {
        @if (!list.length) {
          <div class="empty-well">
            <app-otter-guide variant="empty" size="compact" />
            <p>Todavía no hay nada aquí. Abre un producto o agrégalo al carrito y aparece.</p>
            <a routerLink="/recomendaciones" class="btn btn-tide">Ver recomendaciones</a>
          </div>
        } @else {
          <div class="historial-meet">
            <app-otter-guide
              variant="explain"
              size="compact"
              caption="Esto es lo que has hecho. No cambia cómo te recomendamos."
            />
            <p class="historial-count"><strong>{{ list.length }}</strong> {{ list.length === 1 ? 'acción' : 'acciones' }}</p>
          </div>
          @for (day of days(); track day.key) {
            <section class="historial-day">
              <h2 class="historial-day-title">{{ day.label }}</h2>
              <ol class="historial-list">
                @for (row of day.rows; track row.event.id) {
                  <li class="historial-row" [attr.data-kind]="row.event.eventType">
                    <span class="historial-photo">
                      @if (rowImage(row); as img) {
                        <img
                          [src]="img.src"
                          [alt]=""
                          [class.catalog-ph]="img.placeholder"
                          [class.historial-pose]="img.pose"
                        />
                      } @else {
                        <img src="/brand/mark-compact.svg" alt="" />
                      }
                    </span>
                    <div class="historial-body">
                      <p class="historial-kind">{{ eventLabel(row.event.eventType) }}</p>
                      @if (row.code) {
                        <a [routerLink]="['/producto', row.code]" class="historial-name">
                          {{ historialProductName(row.product) }}
                        </a>
                        <p class="historial-meta">Código: {{ row.code }}</p>
                      } @else {
                        <p class="historial-name">{{ rowHeadline(row) }}</p>
                      }
                    </div>
                    <time class="historial-when" [attr.datetime]="row.event.createdAt">
                      {{ row.event.createdAt | date:'H:mm' }}
                    </time>
                  </li>
                }
              </ol>
            </section>
          }
        }
      } @else {
        <app-loading-well label="Cargando tu historial…" />
      }
    </section>
  `,
})
export class HistorialPage {
  private readonly repo = inject(ProductRepository);
  readonly historialProductName = historialProductName;

  readonly rows = toSignal(
    this.repo.listEvents().pipe(
      switchMap((events) => {
        const codes = [
          ...new Set(events.map((event) => this.eventCode(event)).filter((code): code is string => !!code)),
        ];
        const asRows = (products: Product[]): HistorialRow[] => {
          const byCode = new Map(products.map((product) => [product.code, product]));
          return events.map((event) => {
            const code = this.eventCode(event);
            return {
              event,
              code,
              product: code ? byCode.get(code) : undefined,
            };
          });
        };
        if (!codes.length) {
          return of(asRows([]));
        }
        return this.repo.byCodes(codes).pipe(map(asRows));
      }),
    ),
  );

  readonly days = computed(() => groupHistorialDays(this.rows() ?? []));

  eventLabel(type: EventType): string {
    return EVENT_LABELS[type];
  }

  eventCode(event: UsageEvent): string | null {
    const code = event.payload['code'];
    return typeof code === 'string' && code ? code : null;
  }

  rowHeadline(row: HistorialRow): string {
    if (row.event.eventType === 'ranking_run_created') {
      return 'Con lo que te importa';
    }
    return 'Sin un producto concreto';
  }

  rowImage(row: HistorialRow): { src: string; placeholder: boolean; pose: boolean } | null {
    if (row.event.eventType === 'ranking_run_created') {
      return { src: '/otter/nuti-recommend.png', placeholder: false, pose: true };
    }
    if (!row.code) {
      return null;
    }
    const foto = usableProductImage(row.product?.imageUrl);
    if (foto) {
      return { src: foto, placeholder: false, pose: false };
    }
    return { src: catalogPlaceholderSrc(row.product?.category), placeholder: true, pose: false };
  }
}

export function groupHistorialDays(rows: HistorialRow[]): HistorialDay[] {
  const groups = new Map<string, HistorialRow[]>();
  for (const row of rows) {
    const day = new Date(row.event.createdAt);
    const key = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, '0')}-${String(day.getDate()).padStart(2, '0')}`;
    const list = groups.get(key) ?? [];
    list.push(row);
    groups.set(key, list);
  }
  return [...groups.entries()].map(([key, dayRows]) => ({
    key,
    label: historialDayLabel(dayRows[0].event.createdAt),
    rows: dayRows,
  }));
}

export function historialDayLabel(iso: string, now = new Date()): string {
  const day = new Date(iso);
  if (sameCalendarDay(day, now)) {
    return 'Hoy';
  }
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (sameCalendarDay(day, yesterday)) {
    return 'Ayer';
  }
  return day.toLocaleDateString('es-MX', { day: 'numeric', month: 'long' });
}

function sameCalendarDay(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();
}
