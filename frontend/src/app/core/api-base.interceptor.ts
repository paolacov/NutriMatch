import { HttpInterceptorFn } from '@angular/common/http';

import { environment } from '../../environments/environment';

/** Antepone el origen del backend cuando el build de producción lo definió. */
export const apiBaseInterceptor: HttpInterceptorFn = (req, next) => {
  const base = environment.apiBaseUrl.trim().replace(/\/$/, '');
  if (!base || /^https?:\/\//i.test(req.url)) {
    return next(req);
  }
  const path = req.url.startsWith('/') ? req.url : `/${req.url}`;
  return next(req.clone({ url: `${base}${path}` }));
};
