import { platoVisibleCodes } from './plato-dish';

describe('plato chips', () => {
  it('muestra hasta 4 y el resto como extra', () => {
    expect(platoVisibleCodes(['a', 'b', 'c'])).toEqual({ shown: ['a', 'b', 'c'], extra: 0 });
    expect(platoVisibleCodes(['a', 'b', 'c', 'd', 'e', 'f'])).toEqual({
      shown: ['a', 'b', 'c', 'd'],
      extra: 2,
    });
  });
});
