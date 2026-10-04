import { groupHistorialDays, historialDayLabel } from './historial.page';
import { EventType, UsageEvent } from '../core/models/domain';

function event(id: number, createdAt: string, type: EventType = 'product_viewed'): {
  event: UsageEvent;
  code: string | null;
  product: undefined;
} {
  return {
    event: { id, eventType: type, payload: { code: '1' }, createdAt },
    code: '1',
    product: undefined,
  };
}

describe('historial grouping', () => {
  it('agrupa por día y etiqueta hoy y ayer', () => {
    const now = new Date('2026-09-29T18:00:00');
    expect(historialDayLabel('2026-09-29T10:00:00', now)).toBe('Hoy');
    expect(historialDayLabel('2026-09-28T10:00:00', now)).toBe('Ayer');
    expect(historialDayLabel('2026-09-20T10:00:00', now)).toBe('20 de septiembre');
  });

  it('conserva el orden de las trazas dentro del día', () => {
    const days = groupHistorialDays([
      event(2, '2026-09-29T12:00:00'),
      event(1, '2026-09-29T08:00:00'),
      event(3, '2026-09-28T18:00:00'),
    ]);
    expect(days.map((day) => day.key)).toEqual(['2026-09-29', '2026-09-28']);
    expect(days[0].rows.map((row) => row.event.id)).toEqual([2, 1]);
  });
});
