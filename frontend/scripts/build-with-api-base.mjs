/**
 * Build de producción para Vercel.
 * API_BASE_URL vacía deja las llamadas en el mismo origen.
 * Si tiene valor, se escribe solo durante este proceso y el archivo se restaura.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const frontendRoot = fileURLToPath(new URL('..', import.meta.url));
const envFile = path.join(frontendRoot, 'src/environments/environment.production.ts');
const original = readFileSync(envFile, 'utf8');
const raw = (process.env.API_BASE_URL ?? '').trim().replace(/\/$/, '');

if (raw && !/^https?:\/\//i.test(raw)) {
  console.error('API_BASE_URL debe ser una URL http(s) absoluta, o quedar vacía.');
  process.exit(1);
}

let changed = false;
try {
  if (raw) {
    const next = original.replace(
      /apiBaseUrl:\s*(?:'[^']*'|"[^"]*")/,
      `apiBaseUrl: ${JSON.stringify(raw)}`,
    );
    if (next === original) {
      console.error('No se encontró apiBaseUrl en environment.production.ts');
      process.exit(1);
    }
    writeFileSync(envFile, next);
    changed = true;
    console.log('API_BASE_URL aplicada al build de producción.');
  } else {
    console.log('API_BASE_URL vacía: el frontend usará el mismo origen.');
  }

  const ng = path.join(frontendRoot, 'node_modules', '.bin', 'ng');
  const result = spawnSync(ng, ['build', '--configuration', 'production'], {
    cwd: frontendRoot,
    stdio: 'inherit',
  });
  process.exitCode = result.status ?? 1;
} finally {
  if (changed) {
    writeFileSync(envFile, original);
  }
}
