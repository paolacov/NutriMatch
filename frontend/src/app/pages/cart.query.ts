import { CartSummary, GroupBucket, Product } from '../core/models/domain';

const GRUPOS_GUIA = ['frutas_verduras', 'cereales', 'leguminosas_aoa'] as const;

export interface CartMoney {
  amount: number | null;
  realCount: number;
  demoCount: number;
  missingCount: number;
}

export function cartMoney(products: Product[]): CartMoney {
  let amount = 0;
  let realCount = 0;
  let demoCount = 0;
  let missingCount = 0;
  for (const product of products) {
    const value = product.price.value;
    if (product.price.status === 'REAL' && value !== null) {
      amount += value;
      realCount += 1;
    } else if (product.price.status === 'SYNTHETIC' && value !== null) {
      amount += value;
      demoCount += 1;
    } else {
      missingCount += 1;
    }
  }
  const priced = realCount + demoCount;
  return {
    amount: priced ? Math.round(amount * 100) / 100 : null,
    realCount,
    demoCount,
    missingCount,
  };
}

export function cartAmountLabel(money: CartMoney): string {
  if (money.amount === null) {
    return '';
  }
  return `$${money.amount.toFixed(2)}`;
}

export function cartLegend(money: CartMoney): string {
  if (money.amount === null) {
    return '';
  }
  if (money.realCount > 0 && money.demoCount > 0) {
    return 'Incluye precios reales y de demostración';
  }
  if (money.demoCount > 0) {
    return 'Precio de demostración';
  }
  return 'Precio real';
}

export function cartTotalLabel(money: CartMoney): string {
  const monto = cartAmountLabel(money);
  const leyenda = cartLegend(money);
  if (!monto) {
    return '';
  }
  if (leyenda === 'Precio real') {
    return `${monto} MXN`;
  }
  return `${monto} · ${leyenda}`;
}

export function cartMoneyNote(_money: CartMoney): string | null {
  return null;
}

export function cartMoneyGap(money: CartMoney): string | null {
  if (money.missingCount <= 0) {
    return null;
  }
  return money.missingCount === 1
    ? '1 producto no tiene precio disponible y no entra en el total.'
    : `${money.missingCount} productos no tienen precio disponible y no entran en el total.`;
}

export function guideBuckets(summary: CartSummary): GroupBucket[] {
  return summary.plato.filter((row) => (GRUPOS_GUIA as readonly string[]).includes(row.key));
}

export function cartVariety(summary: CartSummary): { groups: number; categories: number; products: number } {
  const groups = guideBuckets(summary).filter((row) => row.n > 0).length;
  const categories = summary.categories.filter((row) => row.key !== 'unclassified' && row.n > 0).length;
  return { groups, categories, products: summary.nProducts };
}

export function groupSentence(row: GroupBucket): string {
  if (row.n <= 0) {
    return 'Actualmente no hay productos clasificados en este grupo.';
  }
  if (row.n === 1) {
    return 'Este grupo representa 1 producto de tu carrito.';
  }
  return `Este grupo representa ${row.n} productos de tu carrito.`;
}

export function groupsPresentLine(groups: number): string {
  if (groups <= 0) {
    return 'Tu carrito no tiene productos en los grupos de la guía.';
  }
  if (groups === 1) {
    return 'Tu carrito contiene productos de 1 grupo.';
  }
  return `Tu carrito contiene productos de ${groups} grupos.`;
}

export interface CartAlertGroup {
  key: string;
  label: string;
  present: boolean;
  detail: string;
}

export interface CartAlertBoard {
  headline: string;
  groups: CartAlertGroup[];
  footnote: string | null;
  cheer: boolean;
}

export function cartAlertBoard(summary: CartSummary): CartAlertBoard {
  const guide = guideBuckets(summary);
  const present = guide.filter((row) => row.n > 0);
  let headline: string;
  if (present.length === guide.length && guide.length > 0) {
    headline = 'Tu carrito incluye productos de los tres grupos principales.';
  } else if (present.length > 1) {
    headline = 'Tu carrito contiene productos de diferentes grupos del Plato del Buen Comer.';
  } else if (present.length === 1) {
    headline = 'Tu carrito contiene productos de 1 grupo del Plato del Buen Comer.';
  } else {
    headline = 'Actualmente no hay productos clasificados en los grupos de la guía.';
  }
  const groups = guide.map((row) => ({
    key: row.key,
    label: row.label,
    present: row.n > 0,
    detail:
      row.n > 0
        ? row.n === 1
          ? '1 producto'
          : `${row.n} productos`
        : 'Actualmente no hay productos clasificados en este grupo.',
  }));
  const sinGrupo = summary.plato.find((row) => row.key === 'unclassified');
  return {
    headline,
    groups,
    footnote:
      sinGrupo && sinGrupo.n > 0
        ? 'Algunos productos no cuentan con información suficiente para clasificarlos.'
        : null,
    cheer: present.length === guide.length && guide.length > 0,
  };
}

export function cartNotices(summary: CartSummary): string[] {
  const guide = guideBuckets(summary);
  const present = guide.filter((row) => row.n > 0);
  const lines: string[] = [];
  if (present.length === guide.length && guide.length > 0) {
    lines.push('Tu carrito contiene productos de los tres grupos principales.');
  } else if (present.length > 0) {
    lines.push(groupsPresentLine(present.length));
  } else {
    lines.push('No hay productos clasificados actualmente en los grupos de la guía.');
  }
  for (const row of guide) {
    if (row.n === 0) {
      lines.push(`No hay productos clasificados actualmente en ${row.label}.`);
    } else if (row.n === 1 && summary.nProducts >= 3) {
      lines.push(`Existe poca variedad dentro de ${row.label}.`);
    }
  }
  const sinGrupo = summary.plato.find((row) => row.key === 'unclassified');
  if (sinGrupo && sinGrupo.n > 0) {
    const n = sinGrupo.n;
    lines.push(
      n === 1
        ? '1 producto no tiene grupo en la guía y queda como no clasificado.'
        : `${n} productos no tienen grupo en la guía y quedan como no clasificado.`,
    );
  }
  return lines;
}

export function sharePercent(row: GroupBucket, products: number): number | null {
  if (products <= 0 || row.n <= 0) {
    return null;
  }
  return Math.round(row.share * 100);
}
