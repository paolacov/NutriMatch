import { Component, input } from '@angular/core';

@Component({
  selector: 'app-loading-well',
  template: `
    <div class="load-well card-paper" role="status">
      <img class="load-nuti" src="/otter/nuti-discovering.png" alt="" />
      <p class="load-well-copy">
        <span class="brand-scan"><img src="/brand/mark-compact.svg" alt="" /></span>
        {{ label() }}
      </p>
    </div>
  `,
})
export class LoadingWell {
  readonly label = input('Cargando…');
}
