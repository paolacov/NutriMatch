import { Component, input } from '@angular/core';
import { Band } from '../../core/models/domain';
import { bandLabel } from '../format';

@Component({
  selector: 'app-band-chip',
  template: `
    <span class="band-chip" [attr.data-band]="band()">{{ bandLabel(band()) }}</span>
  `,
})
export class BandChip {
  readonly band = input.required<Band>();
  readonly bandLabel = bandLabel;
}
