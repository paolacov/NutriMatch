import { Injectable, signal } from '@angular/core';
import { DEFAULT_PROFILE, UserProfile } from '../models/domain';

const KEY = 'nutrimatch.profile.v2';

@Injectable({ providedIn: 'root' })
export class ProfileStore {
  readonly profile = signal<UserProfile>(this.load());
  readonly panelOpen = signal(false);

  openPanel(): void {
    this.panelOpen.set(true);
  }

  closePanel(): void {
    this.panelOpen.set(false);
  }

  togglePanel(): void {
    this.panelOpen.update((open) => !open);
  }

  save(next: UserProfile): void {
    this.profile.set(next);
    localStorage.setItem(KEY, JSON.stringify(next));
  }

  reset(): void {
    this.save({ ...DEFAULT_PROFILE, priorityOrder: [...DEFAULT_PROFILE.priorityOrder] });
  }

  private load(): UserProfile {
    try {
      const raw = localStorage.getItem(KEY);
      return raw ? { ...DEFAULT_PROFILE, ...JSON.parse(raw) } : DEFAULT_PROFILE;
    } catch {
      return DEFAULT_PROFILE;
    }
  }
}
