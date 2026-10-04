import { Component } from '@angular/core';
import { BarcodeScan } from '../shared/barcode-scan/barcode-scan';

@Component({
  selector: 'app-home-page',
  imports: [BarcodeScan],
  template: `
    <section class="home-enter">
      <section class="entry entry-home" data-stage="hello" aria-labelledby="nuti-hello">
        <div class="entry-layout">
          <aside class="entry-stage" aria-hidden="true">
            <div class="entry-nuti-halo"></div>
            <picture>
              <source type="image/webp" srcset="/otter/nuti.webp" />
              <img class="entry-nuti" src="/otter/nuti.png" alt="" decoding="async" />
            </picture>
          </aside>
          <div class="entry-copy">
            <h1 id="nuti-hello" class="entry-title">Hola, soy Nuti</h1>
            <p class="entry-body">
              Estoy aquí para ayudarte a conocer tus opciones. Juntos podemos descubrir qué tiene
              cada producto y encontrar alternativas que se ajusten a tus preferencias.
            </p>
            <app-barcode-scan />
          </div>
        </div>
      </section>
    </section>
  `,
})
export class HomePage {}
