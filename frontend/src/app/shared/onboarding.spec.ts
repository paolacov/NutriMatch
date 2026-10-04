import {
  avoidClosing,
  dietTitle,
  firstName,
  nextAllergenTags,
  nutritionFocusFrom,
  priorityClosing,
  progressIndex,
  toPriorityOrder,
} from '../core/models/onboarding';

describe('onboarding mapping', () => {
  it('pone nutrición primero si el primer toque es proteína o azúcar', () => {
    expect(toPriorityOrder(['proteina', 'ingredientes'])).toEqual(['D1', 'D2', 'D3']);
  });

  it('pone ingredientes primero si se eligen antes que nutrición', () => {
    expect(toPriorityOrder(['ingredientes', 'azucar'])).toEqual(['D2', 'D1', 'D3']);
  });

  it('el precio no entra al orden que usa el motor', () => {
    expect(toPriorityOrder(['precio'])).toEqual(['D1', 'D2', 'D3']);
  });

  it('completa las tres dimensiones aunque solo se elija una', () => {
    expect(toPriorityOrder(['nutricion'])).toEqual(['D1', 'D2', 'D3']);
  });

  it('guarda el énfasis nutricional sin crear dimensiones nuevas', () => {
    expect(nutritionFocusFrom(['proteina', 'precio', 'sodio'])).toEqual(['proteina', 'sodio']);
  });

  it('agrupa el progreso en cuatro pasos de entrada', () => {
    expect(progressIndex('hello')).toBe(-1);
    expect(progressIndex('name')).toBe(0);
    expect(progressIndex('prioridades')).toBe(1);
    expect(progressIndex('cuidar')).toBe(2);
    expect(progressIndex('resumen')).toBe(3);
  });

  it('toma solo el primer nombre para el saludo', () => {
    expect(firstName('Paola Covarrubias')).toBe('Paola');
    expect(dietTitle('vegetariano', false)).toBe('Vegetariana');
  });

  it('cierra con nutrición y sin restricciones', () => {
    expect(priorityClosing('Paola', 'D1', null)).toBe('Paola, voy a poner la nutrición primero.');
    expect(avoidClosing([])).toBe('No tienes ingredientes o alérgenos que quieras evitar.');
  });

  it('cierra con procesamiento, vegetariana y un alérgeno', () => {
    expect(priorityClosing('Paola', 'D2', 'vegetariano')).toBe(
      'Paola, voy a poner el procesamiento primero, con alimentación vegetariana.',
    );
    expect(avoidClosing(['Leche'])).toBe('También tendré en cuenta Leche al mostrarte los productos.');
  });

  it('cierra con etiquetas, vegana y dos alérgenos', () => {
    expect(priorityClosing('Paola', 'D3', 'vegano')).toBe(
      'Paola, voy a poner tus etiquetas de preferencia primero, con alimentación vegana.',
    );
    expect(avoidClosing(['Gluten', 'Soya'])).toBe(
      'También tendré en cuenta Gluten y Soya al mostrarte los productos.',
    );
  });

  it('Ninguno borra los alérgenos y un alérgeno desmarca Ninguno', () => {
    expect(nextAllergenTags(['en:milk'], null)).toEqual([]);
    expect(nextAllergenTags([], 'en:milk')).toEqual(['en:milk']);
    expect(nextAllergenTags(['en:milk'], 'en:eggs')).toEqual(['en:milk', 'en:eggs']);
    expect(nextAllergenTags(['en:milk', 'en:eggs'], null)).toEqual([]);
    expect(nextAllergenTags(['en:milk'], 'en:milk')).toEqual([]);
  });
});
