import { Component, ElementRef, OnDestroy, effect, inject, input, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ProductRepository } from '../../core/data/product.repository';

type DetectedBarcode = { rawValue?: string };
type CodeDetector = { detect: (source: HTMLVideoElement) => Promise<DetectedBarcode[]> };

function soloDigitos(value: string): string {
  return value.replace(/\D/g, '');
}

function comoGtin(value: string): string | null {
  const digits = soloDigitos(value);
  return /^\d{8,14}$/.test(digits) ? digits : null;
}

function crearDetector(): CodeDetector | null {
  const Detector = (
    globalThis as {
      BarcodeDetector?: new (options?: { formats?: string[] }) => CodeDetector;
    }
  ).BarcodeDetector;
  if (!Detector) {
    return null;
  }
  try {
    return new Detector({ formats: ['ean_13', 'ean_8', 'upc_a', 'upc_e', 'code_128'] });
  } catch {
    return null;
  }
}

@Component({
  selector: 'app-barcode-scan',
  imports: [FormsModule, RouterLink],
  template: `
    <div class="scan-block">
      <p class="action-kicker">Código de barras</p>
      @if (!live()) {
        <div class="entry-actions">
          <button type="button" class="btn btn-tide" (click)="abrir()">Escanear</button>
          @if (showNameSearch()) {
            <a routerLink="/buscar" class="entry-back">Buscar por nombre</a>
          }
        </div>
      } @else {
        <div class="scan-well">
          <video #video autoplay muted playsinline></video>
          <div class="scan-shade" aria-hidden="true"></div>
          <div class="scan-reticle" aria-hidden="true">
            <span></span><span></span><span></span><span></span>
            <i class="scan-beam"></i>
          </div>
        </div>
      }
      @if (live() || falla()) {
        <p class="scan-status" aria-live="polite">{{ live() ? aviso() : falla() }}</p>
        <form class="scan-manual" (ngSubmit)="usarEscrito()">
          <label class="sr-only" for="scan-digits">Código de barras</label>
          <input
            id="scan-digits"
            name="scanDigits"
            class="field-paper"
            inputmode="numeric"
            autocomplete="off"
            placeholder="Escribe el código"
            [ngModel]="escrito()"
            (ngModelChange)="escrito.set(soloDigitos($event))"
          />
          <button type="submit" class="btn btn-vest">Abrir ficha</button>
        </form>
      }
      @if (live()) {
        <button type="button" class="entry-back" (click)="cerrar()">Cerrar cámara</button>
      }
    </div>
  `,
})
export class BarcodeScan implements OnDestroy {
  private readonly repo = inject(ProductRepository);
  private readonly router = inject(Router);
  private readonly videoRef = viewChild<ElementRef<HTMLVideoElement>>('video');
  private detector: CodeDetector | null = crearDetector();
  private timer = 0;
  private loop = 0;
  private ocupado = false;

  readonly showNameSearch = input(true);
  readonly live = signal(false);
  readonly aviso = signal('Acerca el código al recuadro.');
  readonly falla = signal('');
  readonly escrito = signal('');
  readonly soloDigitos = soloDigitos;
  private readonly stream = signal<MediaStream | null>(null);

  constructor() {
    effect(() => {
      const video = this.videoRef()?.nativeElement;
      const stream = this.stream();
      if (!video || !stream) {
        return;
      }
      const loop = this.loop;
      video.srcObject = stream;
      const suave = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      video.closest('.scan-block')?.scrollIntoView({
        block: 'center',
        behavior: suave ? 'smooth' : 'auto',
      });
      void video.play().finally(() => {
        if (loop === this.loop) {
          this.vigilar(video);
        }
      });
    });
  }

  ngOnDestroy(): void {
    this.cerrar();
  }

  abrir(): void {
    this.falla.set('');
    if (!navigator.mediaDevices?.getUserMedia) {
      this.falla.set('Este navegador no abre la cámara. Escribe el código.');
      return;
    }
    void navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false })
      .then((stream) => {
        this.stream.set(stream);
        this.live.set(true);
        this.aviso.set(
          this.detector
            ? 'Acerca el código al recuadro.'
            : 'Te muestro la cámara. Escribe los números del código.',
        );
      })
      .catch(() => {
        this.falla.set('Para escanear, permite la cámara. También puedes escribir el código.');
      });
  }

  cerrar(): void {
    this.loop += 1;
    window.clearTimeout(this.timer);
    this.timer = 0;
    for (const track of this.stream()?.getTracks() ?? []) {
      track.stop();
    }
    const video = this.videoRef()?.nativeElement;
    if (video) {
      video.srcObject = null;
    }
    this.stream.set(null);
    this.live.set(false);
    this.ocupado = false;
  }

  usarEscrito(): void {
    const gtin = comoGtin(this.escrito());
    if (!gtin) {
      this.decir('El código tiene entre 8 y 14 números.');
      return;
    }
    this.buscar(gtin);
  }

  private decir(texto: string): void {
    if (this.live()) {
      this.aviso.set(texto);
      return;
    }
    this.falla.set(texto);
  }

  private vigilar(video: HTMLVideoElement): void {
    window.clearTimeout(this.timer);
    const loop = ++this.loop;
    const detector = this.detector;
    if (!detector || !this.live()) {
      return;
    }
    const paso = () => {
      if (loop !== this.loop || !this.live() || this.ocupado) {
        return;
      }
      if (video.readyState < 2) {
        this.timer = window.setTimeout(paso, 250);
        return;
      }
      void detector
        .detect(video)
        .then((codes) => {
          if (loop !== this.loop || !this.live() || this.ocupado) {
            return;
          }
          const gtin = codes
            .map((code) => comoGtin(code.rawValue ?? ''))
            .find((value): value is string => Boolean(value));
          if (gtin) {
            this.buscar(gtin);
            return;
          }
          this.timer = window.setTimeout(paso, 280);
        })
        .catch(() => {
          if (loop === this.loop && this.live()) {
            this.timer = window.setTimeout(paso, 400);
          }
        });
    };
    this.timer = window.setTimeout(paso, 280);
  }

  private buscar(gtin: string): void {
    if (this.ocupado) {
      return;
    }
    this.ocupado = true;
    window.clearTimeout(this.timer);
    this.decir('Buscando el producto…');
    this.repo.byCode(gtin).subscribe({
      next: (product) => {
        if (product) {
          this.cerrar();
          void this.router.navigate(['/producto', product.code]);
          return;
        }
        this.ocupado = false;
        this.decir('Este código no está en el catálogo.');
        const video = this.videoRef()?.nativeElement;
        if (video) {
          this.vigilar(video);
        }
      },
      error: () => {
        this.ocupado = false;
        this.decir('No pude consultar el catálogo. Inténtalo de nuevo.');
      },
    });
  }
}
