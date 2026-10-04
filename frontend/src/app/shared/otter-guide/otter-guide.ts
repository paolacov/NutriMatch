import { Component, computed, input } from '@angular/core';
import { OTTER_LINES, OTTER_POSE_SRC, OTTER_VARIANT_POSE, OtterVariant } from '../../core/models/domain';

@Component({
  selector: 'app-otter-guide',
  template: `
    <aside class="otter-guide" [attr.data-size]="size()">
      <img
        [src]="src()"
        alt="Nuti, la nutria guía de NutriMatch"
        class="otter-guide-pose"
      />
      @if (showLine()) {
        <p class="otter-guide-line">{{ line() }}</p>
      }
    </aside>
  `,
})
export class OtterGuide {
  readonly variant = input<OtterVariant>('home');
  readonly size = input<'guide' | 'compact' | 'mini' | 'host'>('guide');
  readonly caption = input<string | undefined>(undefined);
  readonly showLine = input(true);

  readonly src = computed(() => OTTER_POSE_SRC[OTTER_VARIANT_POSE[this.variant()]]);

  line(): string {
    const extra = this.caption()?.trim();
    return extra || OTTER_LINES[this.variant()];
  }
}
