import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { OnboardingStore } from './onboarding.store';

export const requireOnboarding: CanActivateFn = () => {
  const onboarding = inject(OnboardingStore);
  const router = inject(Router);
  return onboarding.finished() ? true : router.parseUrl('/onboarding');
};

export const skipIfOnboarded: CanActivateFn = () => {
  const onboarding = inject(OnboardingStore);
  const router = inject(Router);
  return onboarding.finished() ? router.parseUrl('/') : true;
};
