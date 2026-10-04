import { Component, input } from '@angular/core';
import { ProvenanceStatus } from '../../core/models/domain';

@Component({
  selector: 'app-provenance-badge',
  template: `
    <span class="badge" [class.tag-synthetic]="status() === 'SYNTHETIC'" [attr.data-status]="status()">
      @switch (status()) {
        @case ('REAL') { Observado }
        @case ('DERIVED') { Calculado }
        @case ('IMPUTED') { Imputado · no es de anaquel }
        @case ('SYNTHETIC') { Solo demostración }
        @case ('UNAVAILABLE') { No disponible }
      }
    </span>
  `,
  styles: `
    .badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 0.15rem 0.55rem;
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.01em;
    }
    .badge[data-status='REAL'] {
      background: #1c1917;
      color: #faf6ef;
    }
    .badge[data-status='DERIVED'] {
      background: #dbe7df;
      color: #1f4a36;
    }
    .badge[data-status='IMPUTED'] {
      background: #f3e0c4;
      color: #6b4308;
    }
    .badge[data-status='SYNTHETIC'] {
      border-radius: 999px;
    }
    .badge[data-status='UNAVAILABLE'] {
      background: #ece7df;
      color: #57534e;
      border: 1px solid #d6d3d1;
    }
  `,
})
export class ProvenanceBadge {
  readonly status = input.required<ProvenanceStatus>();
}
