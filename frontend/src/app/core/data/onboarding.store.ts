import { Injectable, computed, signal } from '@angular/core';
import { DEFAULT_ONBOARDING, OnboardingState, firstName } from '../models/onboarding';

const KEY = 'nutrimatch.onboarding.v2';

@Injectable({ providedIn: 'root' })
export class OnboardingStore {
  readonly state = signal<OnboardingState>(this.load());
  readonly displayName = computed(() => this.state().displayName.trim());
  readonly firstName = computed(() => firstName(this.state().displayName));

  finished(): boolean {
    return this.state().finished;
  }

  save(next: OnboardingState): void {
    this.state.set(next);
    localStorage.setItem(KEY, JSON.stringify(next));
  }

  patch(partial: Partial<OnboardingState>): void {
    this.save({ ...this.state(), ...partial });
  }

  complete(partial: Partial<OnboardingState>): void {
    this.save({
      ...this.state(),
      ...partial,
      finished: true,
    });
  }

  setDisplayName(name: string): void {
    this.patch({ displayName: name.trim() });
  }

  private load(): OnboardingState {
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? { ...DEFAULT_ONBOARDING, ...JSON.parse(raw) } : DEFAULT_ONBOARDING;
    } catch {
      return DEFAULT_ONBOARDING;
    }
  }
}
