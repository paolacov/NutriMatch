import {
  ALLERGEN_CHOICES,
  AllergyStatus,
  DietStatus,
  LABEL_CHOICES,
  PRIORITY_LABELS,
  Product,
} from '../core/models/domain';

const TAG_LABELS = new Map<string, string>([
  ...ALLERGEN_CHOICES,
  ...LABEL_CHOICES,
  ['es:exceso-azucares', 'Exceso de azúcares'],
  ['es:exceso-azúcares', 'Exceso de azúcares'],
  ['es:exceso-calorias', 'Exceso de calorías'],
  ['es:exceso-calorías', 'Exceso de calorías'],
  ['es:exceso-grasas-saturadas', 'Exceso de grasas saturadas'],
  ['es:exceso-grasas-trans', 'Exceso de grasas trans'],
  ['es:exceso-sodio', 'Exceso de sodio'],
]);

const FLAG_LABELS: Record<string, string> = {
  D1_sin_dato: 'Sin dato de nutrición',
  D2_sin_dato: 'Sin dato de procesamiento',
  D3_sin_dato: 'Sin dato de etiquetas',
  alergia_no_verificable: 'Alérgenos no verificables',
  dieta_no_verificable: 'Dieta no verificable',
};

export function displayName(product: Product): string {
  return product.name.value ?? 'Sin nombre verificado';
}

export function formatPrice(product: Product): string {
  if (product.price.status === 'SYNTHETIC' && product.price.value !== null) {
    return `$${product.price.value.toFixed(2)} · simulado`;
  }
  if (product.price.status === 'UNAVAILABLE' || product.price.value === null) {
    return 'Precio no disponible';
  }
  return `$${product.price.value.toFixed(2)}`;
}

export function priceCaption(product: Product): string {
  if (product.price.status === 'REAL' && product.price.value !== null) {
    const fuente = priceSourceLabel(product.price.source);
    return `Precio de referencia · $${product.price.value.toFixed(2)} · ${fuente}`;
  }
  if (product.price.status === 'SYNTHETIC' && product.price.value !== null) {
    return `Dato simulado para demostración · $${product.price.value.toFixed(2)}`;
  }
  if (product.price.status === 'IMPUTED') {
    return 'Precio imputado · no es un precio de anaquel';
  }
  return 'Precio no disponible';
}

export function priceSourceLabel(source: string | null | undefined): string {
  if (source === 'open_prices') {
    return 'Open Prices · MXN';
  }
  if (source === 'qqp_profeco') {
    return 'PROFECO QQP';
  }
  return source ?? 'fuente observada';
}

export function bandLabel(band: Product['fit']['band']): string {
  switch (band) {
    case 'ranking':
      return 'En ranking';
    case 'no_verificable':
      return 'No verificable';
    case 'informacion_insuficiente':
      return 'Información insuficiente';
    case 'excluido':
      return 'Excluido';
  }
}

export function humanizeTag(tag: string): string {
  const mapped = TAG_LABELS.get(tag);
  if (mapped) {
    return mapped;
  }
  const segmento = tag.includes(':') ? tag.slice(tag.indexOf(':') + 1) : tag;
  return segmento.replace(/-/g, ' ').trim() || tag;
}

export function flagLabel(flag: string): string {
  return FLAG_LABELS[flag] ?? humanizeTag(flag);
}

export function allergyLabel(status: AllergyStatus): string {
  switch (status) {
    case 'apto':
      return 'apto';
    case 'no_apto':
      return 'no apto';
    case 'no_verificable':
      return 'no verificable';
  }
}

export function dietLabel(status: DietStatus): string {
  switch (status) {
    case 'compatible':
      return 'compatible';
    case 'incompatible':
      return 'incompatible';
    case 'no_verificable':
      return 'no verificable';
  }
}

const CATEGORY_ES: Record<string, string> = {
  'en:groceries': 'Abarrotes',
  groceries: 'Abarrotes',
  'en:biscuits': 'Galletas',
  biscuits: 'Galletas',
  'en:sweetened-beverages': 'Bebidas endulzadas',
  'sweetened beverages': 'Bebidas endulzadas',
  'en:milks': 'Leches',
  milks: 'Leches',
  'en:cereals-and-their-products': 'Cereales',
  'cereals and their products': 'Cereales',
  'en:breakfast-cereals': 'Cereales de desayuno',
  'breakfast cereals': 'Cereales de desayuno',
  'en:crisps': 'Papas fritas',
  crisps: 'Papas fritas',
  'en:flavoured-yogurts': 'Yogures con sabor',
  'flavoured yogurts': 'Yogures con sabor',
  'en:cheeses': 'Quesos',
  cheeses: 'Quesos',
  'en:pasteurized-cheeses': 'Quesos pasteurizados',
  'pasteurized cheeses': 'Quesos pasteurizados',
  'en:greek-style-yogurts': 'Yogur griego',
  'greek style yogurts': 'Yogur griego',
  'es:jugos': 'Jugos',
  jugos: 'Jugos',
  'en:yogurts': 'Yogures',
  yogurts: 'Yogures',
  'en:refrigerated-foods': 'Alimentos refrigerados',
  'refrigerated foods': 'Alimentos refrigerados',
  'es:refrescos': 'Refrescos',
  refrescos: 'Refrescos',
  'es:refresco': 'Refresco',
  refresco: 'Refresco',
  'en:snacks': 'Botanas',
  snacks: 'Botanas',
  'en:confectioneries': 'Dulces',
  confectioneries: 'Dulces',
  'en:candies': 'Dulces',
  candies: 'Dulces',
  'en:cereal-bars': 'Barras de cereal',
  'cereal bars': 'Barras de cereal',
  'en:jams': 'Mermeladas',
  jams: 'Mermeladas',
  'en:waters': 'Aguas',
  waters: 'Aguas',
  'en:mueslis': 'Muesli',
  mueslis: 'Muesli',
  'en:tunas': 'Atún',
  tunas: 'Atún',
  'en:frozen-ready-made-meals': 'Platos congelados',
  'frozen ready made meals': 'Platos congelados',
  'en:flavored-waters': 'Aguas saborizadas',
  'flavored waters': 'Aguas saborizadas',
  'en:dehydrated-soups': 'Sopas deshidratadas',
  'dehydrated soups': 'Sopas deshidratadas',
  'en:breads': 'Panes',
  breads: 'Panes',
  'en:durum-wheat-pasta': 'Pasta de trigo durum',
  'durum wheat pasta': 'Pasta de trigo durum',
  'en:butters': 'Mantequillas',
  butters: 'Mantequillas',
  'es:sazonador': 'Sazonador',
  sazonador: 'Sazonador',
  'en:chocolates': 'Chocolates',
  chocolates: 'Chocolates',
  'en:cereal-flours': 'Harinas de cereal',
  'cereal flours': 'Harinas de cereal',
  'en:flours': 'Harinas',
  flours: 'Harinas',
  'en:cornmeal': 'Harina de maíz',
  cornmeal: 'Harina de maíz',
  'en:bars': 'Barras',
  bars: 'Barras',
  'en:salty-snacks': 'Botanas saladas',
  'salty snacks': 'Botanas saladas',
  'en:ice-creams': 'Helados',
  'ice creams': 'Helados',
  'en:instant-coffees': 'Cafés instantáneos',
  'instant coffees': 'Cafés instantáneos',
  'es:enlatados': 'Enlatados',
  enlatados: 'Enlatados',
  'en:oat': 'Avena',
  oat: 'Avena',
  'es:crema-de-cacahuate': 'Crema de cacahuate',
  'crema de cacahuate': 'Crema de cacahuate',
  'en:fruit-yogurts': 'Yogures de fruta',
  'fruit yogurts': 'Yogures de fruta',
  'en:honeys': 'Mieles',
  honeys: 'Mieles',
  'en:mayonnaises': 'Mayonesas',
  mayonnaises: 'Mayonesas',
  'en:toasts': 'Tostadas',
  toasts: 'Tostadas',
  'en:fruit-based-beverages': 'Bebidas de fruta',
  'fruit based beverages': 'Bebidas de fruta',
  'en:alcoholic-beverages': 'Bebidas alcohólicas',
  'alcoholic beverages': 'Bebidas alcohólicas',
  'en:cereal-grains': 'Granos de cereal',
  'cereal grains': 'Granos de cereal',
  'en:refried-beans': 'Frijoles refritos',
  'refried beans': 'Frijoles refritos',
  'en:popcorn': 'Palomitas',
  popcorn: 'Palomitas',
  'en:dietary-supplements': 'Suplementos',
  'dietary supplements': 'Suplementos',
  'en:almond-based-drinks': 'Bebidas de almendra',
  'almond based drinks': 'Bebidas de almendra',
  'es:pan-dulce': 'Pan dulce',
  'pan dulce': 'Pan dulce',
  'en:panela-cheeses': 'Queso panela',
  'panela cheeses': 'Queso panela',
  'en:beverages': 'Bebidas',
  beverages: 'Bebidas',
  'en:fruit-juices': 'Jugos de fruta',
  'fruit juices': 'Jugos de fruta',
  'en:potato-crisps': 'Papas fritas',
  'potato crisps': 'Papas fritas',
  'en:corn-flakes': 'Hojuelas de maíz',
  'corn flakes': 'Hojuelas de maíz',
  'en:salted-popcorn': 'Palomitas saladas',
  'salted popcorn': 'Palomitas saladas',
  'en:sodas': 'Refrescos',
  sodas: 'Refrescos',
  'en:coffees': 'Cafés',
  coffees: 'Cafés',
  'en:pastas': 'Pastas',
  pastas: 'Pastas',
  'en:marmalades': 'Mermeladas',
  marmalades: 'Mermeladas',
  'en:tabletop-sweeteners': 'Endulzantes de mesa',
  'tabletop sweeteners': 'Endulzantes de mesa',
  'en:lactose-free-milk': 'Leche deslactosada',
  'lactose free milk': 'Leche deslactosada',
  'en:peanuts': 'Cacahuates',
  peanuts: 'Cacahuates',
  'en:sweeteners': 'Endulzantes',
  sweeteners: 'Endulzantes',
  'en:dairies': 'Lácteos',
  dairies: 'Lácteos',
  'en:dried-fruits': 'Frutas secas',
  'dried fruits': 'Frutas secas',
  'es:saborizantes': 'Saborizantes',
  saborizantes: 'Saborizantes',
  'en:vegetables-based-foods': 'Alimentos de verdura',
  'vegetables based foods': 'Alimentos de verdura',
  'en:eggs': 'Huevos',
  eggs: 'Huevos',
  'en:frozen-vegetables': 'Verduras congeladas',
  'frozen vegetables': 'Verduras congeladas',
  'en:corn-chips': 'Totopos',
  'corn chips': 'Totopos',
  'en:artificially-sweetened-beverages': 'Bebidas con edulcorante',
  'artificially sweetened beverages': 'Bebidas con edulcorante',
  'en:energy-drinks': 'Bebidas energéticas',
  'energy drinks': 'Bebidas energéticas',
  'en:flavored-sparkling-waters': 'Aguas minerales saborizadas',
  'flavored sparkling waters': 'Aguas minerales saborizadas',
  'en:extruded-cereals': 'Cereales extruidos',
  'extruded cereals': 'Cereales extruidos',
  'en:rices': 'Arroces',
  rices: 'Arroces',
  'en:whole-milks': 'Leches enteras',
  'whole milks': 'Leches enteras',
  'en:sweet-snacks': 'Dulces',
  'sweet snacks': 'Dulces',
  'en:milk-powders': 'Leches en polvo',
  'milk powders': 'Leches en polvo',
  'en:peanut-butters': 'Crema de cacahuate',
  'peanut butters': 'Crema de cacahuate',
  'en:protein-powders': 'Proteínas en polvo',
  'protein powders': 'Proteínas en polvo',
  'en:colas': 'Refrescos de cola',
  colas: 'Refrescos de cola',
  'en:coconut-waters': 'Agua de coco',
  'coconut waters': 'Agua de coco',
  'en:wholemeal-breads': 'Panes integrales',
  'wholemeal breads': 'Panes integrales',
  'en:plain-yogurts': 'Yogures naturales',
  'plain yogurts': 'Yogures naturales',
  'en:olive-oils': 'Aceites de oliva',
  'olive oils': 'Aceites de oliva',
  'en:chocolate-biscuits': 'Galletas de chocolate',
  'chocolate biscuits': 'Galletas de chocolate',
  'en:plant-based-milk-alternatives': 'Bebidas vegetales',
  'plant based milk alternatives': 'Bebidas vegetales',
  'en:ice-creams-and-sorbets': 'Helados y nieves',
  'ice creams and sorbets': 'Helados y nieves',
  'es:yogurt-griego': 'Yogur griego',
  'yogurt griego': 'Yogur griego',
  'en:stacked-extruded-potato-crisps': 'Papas apiladas',
  'stacked extruded potato crisps': 'Papas apiladas',
  'en:cakes': 'Pasteles',
  cakes: 'Pasteles',
  'en:sliced-breads': 'Pan de caja',
  'sliced breads': 'Pan de caja',
  'en:coconut-milks-and-creams': 'Leches de coco',
  'coconut milks and creams': 'Leches de coco',
  'en:melted-cheese': 'Queso fundido',
  'melted cheese': 'Queso fundido',
  'fr:crema': 'Crema',
  crema: 'Crema',
  'en:crackers-appetizers': 'Galletas saladas',
  'crackers appetizers': 'Galletas saladas',
  'en:coconut-oils': 'Aceites de coco',
  'coconut oils': 'Aceites de coco',
  'en:fruits-in-syrup': 'Frutas en almíbar',
  'fruits in syrup': 'Frutas en almíbar',
  'en:teas': 'Tés',
  teas: 'Tés',
  'en:tomato-sauces': 'Salsas de tomate',
  'tomato sauces': 'Salsas de tomate',
  'es:tortilla-de-harina': 'Tortilla de harina',
  'tortilla de harina': 'Tortilla de harina',
  'en:manchego': 'Queso manchego',
  manchego: 'Queso manchego',
  'en:frozen-fruits': 'Frutas congeladas',
  'frozen fruits': 'Frutas congeladas',
  'en:hot-sauces': 'Salsas picantes',
  'hot sauces': 'Salsas picantes',
  'es:jugo': 'Jugo',
  jugo: 'Jugo',
  'en:beers': 'Cervezas',
  beers: 'Cervezas',
  'es:sustituto-de-crema-en-polvo': 'Sustituto de crema en polvo',
  'sustituto de crema en polvo': 'Sustituto de crema en polvo',
  'en:soups': 'Sopas',
  soups: 'Sopas',
  'en:canola-oils': 'Aceites de canola',
  'canola oils': 'Aceites de canola',
  'en:jelly-desserts': 'Gelatinas',
  'jelly desserts': 'Gelatinas',
  'en:energy-bars': 'Barras energéticas',
  'energy bars': 'Barras energéticas',
  'es:cremas': 'Cremas',
  cremas: 'Cremas',
  'en:cake-mixes': 'Harinas para pastel',
  'cake mixes': 'Harinas para pastel',
  'en:extra-virgin-olive-oils': 'Aceites de oliva extra virgen',
  'extra virgin olive oils': 'Aceites de oliva extra virgen',
  'en:wholemeal-sliced-breads': 'Pan de caja integral',
  'wholemeal sliced breads': 'Pan de caja integral',
  'en:vinegars': 'Vinagres',
  vinegars: 'Vinagres',
  'en:cocoa-and-hazelnuts-spreads': 'Cremas de avellana',
  'cocoa and hazelnuts spreads': 'Cremas de avellana',
  'en:dry-biscuits': 'Galletas secas',
  'dry biscuits': 'Galletas secas',
  'en:soy-based-drinks': 'Bebidas de soya',
  'soy based drinks': 'Bebidas de soya',
  'en:chocolate-powders': 'Polvos de chocolate',
  'chocolate powders': 'Polvos de chocolate',
  'en:gelatin': 'Grenetina',
  gelatin: 'Grenetina',
  'es:barras-de-cereal': 'Barras de cereal',
  'barras de cereal': 'Barras de cereal',
  'en:mexican-cheeses': 'Quesos mexicanos',
  'mexican cheeses': 'Quesos mexicanos',
  'en:unsalted-margarines': 'Margarinas sin sal',
  'unsalted margarines': 'Margarinas sin sal',
  'en:quinoa': 'Quinoa',
  quinoa: 'Quinoa',
  'en:drinkable-yogurts': 'Yogures para beber',
  'drinkable yogurts': 'Yogures para beber',
  'en:turkey-sausages': 'Salchichas de pavo',
  'turkey sausages': 'Salchichas de pavo',
  'en:chorizo': 'Chorizo',
  chorizo: 'Chorizo',
  'en:syrups': 'Jarabes',
  syrups: 'Jarabes',
  'en:sugar-free-chewing-gum': 'Chicle sin azúcar',
  'sugar free chewing gum': 'Chicle sin azúcar',
  'en:chewing-gum': 'Chicle',
  'chewing gum': 'Chicle',
  'en:sugarfree-candies': 'Dulces sin azúcar',
  'sugarfree candies': 'Dulces sin azúcar',
  'en:frozen-fishes': 'Pescados congelados',
  'frozen fishes': 'Pescados congelados',
  'en:almonds': 'Almendras',
  almonds: 'Almendras',
  'en:almond-butters': 'Crema de almendra',
  'almond butters': 'Crema de almendra',
  'en:pates-a-tartiner': 'Untables',
  'pates a tartiner': 'Untables',
  'fr:pates-a-tartiner': 'Untables',
  'en:mandarins': 'Mandarinas',
  mandarins: 'Mandarinas',
  'es:tortillas': 'Tortillas',
  tortillas: 'Tortillas',
  'es:productos-de-origen-vegetal': 'Productos de origen vegetal',
  'productos de origen vegetal': 'Productos de origen vegetal',
  'en:strawberry-jams': 'Mermelada de fresa',
  'strawberry jams': 'Mermelada de fresa',
  'en:seafood': 'Mariscos',
  seafood: 'Mariscos',
  'en:turkey-breasts': 'Pechuga de pavo',
  'turkey breasts': 'Pechuga de pavo',
  'en:sausages': 'Salchichas',
  sausages: 'Salchichas',
  'en:salad-dressings': 'Aderezos',
  'salad dressings': 'Aderezos',
  'en:fresh-eggs': 'Huevos frescos',
  'fresh eggs': 'Huevos frescos',
  'en:fruit-and-soy-beverages': 'Bebidas de fruta y soya',
  'fruit and soy beverages': 'Bebidas de fruta y soya',
  'en:meats': 'Carnes',
  meats: 'Carnes',
  'en:turkeys': 'Pavo',
  turkeys: 'Pavo',
  'en:filled-biscuits': 'Galletas rellenas',
  'filled biscuits': 'Galletas rellenas',
  'es:salchichoneria': 'Salchichonería',
  salchichoneria: 'Salchichonería',
  'en:mineral-waters': 'Aguas minerales',
  'mineral waters': 'Aguas minerales',
  'en:fresh-meats': 'Carnes frescas',
  'fresh meats': 'Carnes frescas',
  'en:caramels': 'Caramelos',
  caramels: 'Caramelos',
  'en:dairy-drinks': 'Bebidas lácteas',
  'dairy drinks': 'Bebidas lácteas',
  'fr:jugos': 'Jugos',
  'en:appetizers': 'Botanas',
  appetizers: 'Botanas',
  'en:fried-foods': 'Fritos',
  'fried foods': 'Fritos',
  'en:yogurt-drinks': 'Yogures para beber',
  'yogurt drinks': 'Yogures para beber',
  'en:evaporated-milks': 'Leches evaporadas',
  'evaporated milks': 'Leches evaporadas',
  'en:cocoa-and-chocolate-powders': 'Polvos de cacao',
  'cocoa and chocolate powders': 'Polvos de cacao',
  'en:ketchup': 'Cátsup',
  ketchup: 'Cátsup',
  'en:spaghetti': 'Espagueti',
  spaghetti: 'Espagueti',
  'en:unsweetened-beverages': 'Bebidas sin azúcar',
  'unsweetened beverages': 'Bebidas sin azúcar',
  'en:ice-pops': 'Paletas',
  'ice pops': 'Paletas',
  'en:oatmeal-cookies': 'Galletas de avena',
  'oatmeal cookies': 'Galletas de avena',
  'en:iced-teas': 'Tés fríos',
  'iced teas': 'Tés fríos',
  'en:sauces': 'Salsas',
  sauces: 'Salsas',
  'en:meals': 'Platillos',
  meals: 'Platillos',
  'en:chia': 'Chía',
  chia: 'Chía',
  'en:avocado-oils': 'Aceites de aguacate',
  'avocado oils': 'Aceites de aguacate',
  'en:frozen-strawberries': 'Fresas congeladas',
  'frozen strawberries': 'Fresas congeladas',
  'en:ice-cream-bars': 'Paletas de helado',
  'ice cream bars': 'Paletas de helado',
  'en:instant-beverages': 'Bebidas instantáneas',
  'instant beverages': 'Bebidas instantáneas',
  'es:consome': 'Consomé',
  consome: 'Consomé',
  'en:vegetable-fats': 'Grasas vegetales',
  'vegetable fats': 'Grasas vegetales',
  'en:cow-milks': 'Leche de vaca',
  'cow milks': 'Leche de vaca',
  'en:strawberry-yogurts': 'Yogures de fresa',
  'strawberry yogurts': 'Yogures de fresa',
  'en:italian-pasta': 'Pasta italiana',
  'italian pasta': 'Pasta italiana',
  'en:instant-noodle-soups': 'Sopas instantáneas',
  'instant noodle soups': 'Sopas instantáneas',
  'en:sugar-substitutes': 'Sustitutos de azúcar',
  'sugar substitutes': 'Sustitutos de azúcar',
  'en:bonbons': 'Bombones',
  bonbons: 'Bombones',
  'es:vegano': 'Vegano',
  vegano: 'Vegano',
  'en:condiments': 'Condimentos',
  condiments: 'Condimentos',
  'en:corn-semolinas-for-polenta': 'Sémola de maíz para polenta',
  'corn semolinas for polenta': 'Sémola de maíz para polenta',
  'es:mantequilla-de-mani': 'Mantequilla de maní',
  'mantequilla de mani': 'Mantequilla de maní',
  'es:saludable': 'Saludable',
  saludable: 'Saludable',
  'es:sustituto-de-sodio': 'Sustituto de sodio',
  'sustituto de sodio': 'Sustituto de sodio',
};

export function categoryLabel(category: string | null | undefined): string {
  if (!category) {
    return 'Sin categoría';
  }
  const clave = category.trim().toLowerCase();
  const mapeada = CATEGORY_ES[clave] ?? CATEGORY_ES[humanizeTag(clave)];
  if (mapeada) {
    return mapeada;
  }
  return humanizeTag(category);
}

export function dimensionLabel(key: 'D1' | 'D2' | 'D3'): string {
  return PRIORITY_LABELS[key];
}

const NUTRIENTE_D1_LABELS: Record<string, string> = {
  sugars_100g: 'Azúcares',
  salt_100g: 'Sal',
  'saturated-fat_100g': 'Grasa saturada',
  fiber_100g: 'Fibra',
  proteins_100g: 'Proteína',
};

export function nutrientD1Label(key: string): string {
  return NUTRIENTE_D1_LABELS[key] ?? humanizeTag(key);
}

export function nutrientSignLabel(sign: number): string {
  return sign < 0 ? 'Menos es mejor' : 'Más es mejor';
}

export function scoreCaption(product: Product): string {
  if (product.fit.status === 'DERIVED') {
    return 'Lo calcula el motor · no es un diagnóstico';
  }
  if (product.fit.status === 'SYNTHETIC') {
    return 'Dato simulado para demostración';
  }
  return 'Aún no se calculó el encaje';
}

export function formatCount(n: number): string {
  return n.toLocaleString('es-MX');
}

export function coverageCatalogCaption(nProducts: number, nPuntuable: number): string {
  return (
    `${formatCount(nProducts)} productos en el anaquel. ${formatCount(nPuntuable)} se pueden comparar. ` +
    'El resto se busca; no se les inventa un score.'
  );
}

export function coverageProfileCaption(params: {
  ranking: number;
  noVerificable: number;
  insuficiente: number;
  excluded: number;
}): string {
  return (
    `Con este perfil: ${formatCount(params.ranking)} en ranking · ` +
    `${formatCount(params.noVerificable)} no verificables · ` +
    `${formatCount(params.insuficiente)} con información insuficiente · ` +
    `${formatCount(params.excluded)} excluidos (no se listan). ` +
    'Información insuficiente no es un score bajo.'
  );
}
