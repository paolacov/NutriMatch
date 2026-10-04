/** Nombre visible de un sello. La taxonomía de Open Food Facts llega en inglés. */

const SELLO_ES: Record<string, string> = {
  'en:no-gluten': 'Sin gluten',
  'en:made-in-mexico': 'Hecho en México',
  'en:kosher': 'Kosher',
  'en:vegetarian': 'Vegetariano',
  'en:vegan': 'Vegano',
  'en:no-colorings': 'Sin colorantes',
  'en:no-preservatives': 'Sin conservadores',
  'en:no-gmos': 'Sin transgénicos',
  'en:green-dot': 'Punto verde',
  'en:organic': 'Orgánico',
  'en:no-added-sugar': 'Sin azúcar añadida',
  'en:non-gmo-project': 'Proyecto Non-GMO',
  'en:no-lactose': 'Sin lactosa',
  'en:low-or-no-sugar': 'Bajo o sin azúcar',
  'en:fsc': 'FSC',
  'en:no-sugar': 'Sin azúcar',
  'en:natural-colorings': 'Colorantes naturales',
  'en:fsc-mix': 'FSC mixto',
  'en:orthodox-union-kosher': 'Kosher (Unión Ortodoxa)',
  'en:usda-organic': 'Orgánico USDA',
  'en:made-in-spain': 'Hecho en España',
  'en:halal': 'Halal',
  'en:kosher-parve': 'Kosher parve',
  'en:eu-organic': 'Orgánico de la UE',
  'en:no-artificial-flavors': 'Sin saborizantes artificiales',
  'en:100-natural': '100 % natural',
  'en:low-or-no-fat': 'Bajo o sin grasa',
  'en:source-of-fibre': 'Fuente de fibra',
  'en:source-of-fiber': 'Fuente de fibra',
  'en:new': 'Nuevo',
  'en:low-fat': 'Bajo en grasa',
  'en:no-artificial-colors': 'Sin colorantes artificiales',
  'en:keto': 'Keto',
  'en:made-in-italy': 'Hecho en Italia',
  'en:high-fibres': 'Alto en fibra',
  'en:high-in-fibre': 'Alto en fibra',
  'en:no-soy': 'Sin soya',
  'en:family-owned-business': 'Empresa familiar',
  'en:no-cholesterol': 'Sin colesterol',
  'en:source-of-proteins': 'Fuente de proteína',
  'en:no-palm-oil': 'Sin aceite de palma',
  'en:no-bisphenol-a': 'Sin bisfenol A',
  'en:eu-agriculture': 'Agricultura de la UE',
  'en:vegan-action': 'Vegan Action',
  'en:fair-trade': 'Comercio justo',
  'en:non-eu-agriculture': 'Agricultura fuera de la UE',
  'en:low-or-no-salt': 'Bajo o sin sal',
  'en:eu-non-eu-agriculture': 'Agricultura de la UE y fuera de la UE',
  'en:no-salt-added': 'Sin sal añadida',
  'en:carbon-footprint': 'Huella de carbono',
  'en:no-artificial-preservatives': 'Sin conservadores artificiales',
  'en:pasteurized': 'Pasteurizado',
  'en:eac': 'EAC',
  'en:no-trans-fat': 'Sin grasas trans',
  'en:no-additives': 'Sin aditivos',
  'en:contains-milk': 'Contiene leche',
  'en:no-milk': 'Sin leche',
  'en:new-recipe': 'Nueva receta',
  'en:contains-gluten': 'Contiene gluten',
  'en:contains-gmos': 'Contiene transgénicos',
  'en:award-winning': 'Premiado',
  'en:european-vegetarian-union': 'Unión Vegetariana Europea',
  'en:with-sweeteners': 'Con edulcorantes',
  'en:fairtrade-international': 'Fairtrade International',
  'en:paleo': 'Paleo',
  'en:mk-kosher': 'Kosher MK',
  'en:the-vegan-society': 'The Vegan Society',
  'en:no-artificial-colours-or-flavours': 'Sin colorantes ni saborizantes artificiales',
  'en:no-artificial-colours-flavours': 'Sin colorantes ni saborizantes artificiales',
  'en:no-artificial-colours-and-preservatives': 'Sin colorantes ni conservadores artificiales',
  'en:bpa-free-lining': 'Revestimiento sin BPA',
  'en:100-italian-wheat': '100 % trigo italiano',
  'en:low-or-no-sodium': 'Bajo o sin sodio',
  'en:low-sodium': 'Bajo en sodio',
  'en:certified-gluten-free': 'Certificado sin gluten',
  'en:reduced-fat': 'Reducido en grasa',
  'en:reduced-salt': 'Reducido en sal',
  'en:reduced-sugar': 'Reducido en azúcar',
  'en:no-salt': 'Sin sal',
  'en:european-vegetarian-union-vegan': 'Vegano (Unión Vegetariana Europea)',
  'en:natural-flavors': 'Saborizantes naturales',
  'en:not-advised-for-specific-people': 'No recomendado para algunas personas',
  'en:no-caffeine': 'Sin cafeína',
  'en:nutriscore': 'Nutri-Score',
  'en:rainforest-alliance': 'Rainforest Alliance',
  'en:no-flavour-enhancer': 'Sin potenciadores de sabor',
  'en:no-msg': 'Sin glutamato monosódico',
  'en:no-added-msg': 'Sin glutamato monosódico añadido',
  'en:crossed-grain-trademark': 'Espiga barrada',
  'en:with-sunflower-oil': 'Con aceite de girasol',
  'en:100-italian': '100 % italiano',
  'en:high-proteins': 'Alto en proteína',
  'en:made-in-usa': 'Hecho en Estados Unidos',
  'en:bronze-die-extrusion': 'Extrusión con dado de bronce',
  'en:slow-dried-at-low-temperature': 'Secado lento a baja temperatura',
  'en:small-batch-production': 'Producción en lotes pequeños',
  'en:100-vegetable': '100 % vegetal',
  'en:omega-3': 'Omega 3',
  'en:iso-22000': 'ISO 22000',
  'en:iso-9001': 'ISO 9001',
  'en:dolphin-safe': 'Atún seguro para delfines',
  'en:verified': 'Verificado',
  'en:coeliac': 'Apto para celíacos',
  'en:no-sweeteners': 'Sin edulcorantes',
  'en:glutenvrij': 'Sin gluten',
  'en:no-added-sulphites': 'Sin sulfitos añadidos',
  'en:low-sugar': 'Bajo en azúcar',
  'en:no-added-salt': 'Sin sal añadida',
  'en:hecho-en-mexico': 'Hecho en México',
  'en:calcium-source': 'Fuente de calcio',
  'en:iron-source': 'Fuente de hierro',
  'en:pgi': 'IGP',
  'en:pdo': 'DOP',
  'en:tsg': 'ETG',
  'en:no-wheat': 'Sin trigo',
  'en:no-fat': 'Sin grasa',
  'en:recycle': 'Recicla',
  'en:un-filtered': 'Sin filtrar',
  'en:unfiltered': 'Sin filtrar',
  'en:filtered': 'Filtrado',
  'en:low-saturated-fat': 'Bajo en grasa saturada',
  'en:saturated-fat-free': 'Sin grasa saturada',
  'en:no-eggs': 'Sin huevo',
  'en:limited-edition': 'Edición limitada',
  'en:soil-organic': 'Orgánico Soil Association',
  'en:soil-association-organic': 'Orgánico Soil Association',
  'en:100-italian-tomatoes': '100 % tomate italiano',
  'en:un-pasteurized': 'Sin pasteurizar',
  'en:un-pasteurised': 'Sin pasteurizar',
  'en:not-advised-for-pregnant-women': 'No recomendado en el embarazo',
  'en:not-advised-for-children-and-pregnant-women': 'No recomendado en niños ni en el embarazo',
  'en:sin-azucar': 'Sin azúcar',
  'en:sin-azucar-anadida': 'Sin azúcar añadida',
  'en:no-added-fat': 'Sin grasa añadida',
  'en:canada-organic': 'Orgánico de Canadá',
  'en:excessive-consumption-can-have-laxative-effects': 'El consumo excesivo puede tener efectos laxantes',
  'en:sustainable': 'Sostenible',
  'en:sustainable-fishery': 'Pesca sostenible',
  'en:sustainable-seafood-msc': 'Pesca sostenible MSC',
  'en:made-in-france': 'Hecho en Francia',
  'en:made-in-germany': 'Hecho en Alemania',
  'en:made-in-belgium': 'Hecho en Bélgica',
  'en:made-in-argentina': 'Hecho en Argentina',
  'en:made-in-colombia': 'Hecho en Colombia',
  'en:made-in-brazil': 'Hecho en Brasil',
  'en:made-in-the-eu': 'Hecho en la UE',
  'en:certified-b-corporation': 'Empresa B certificada',
  'en:low-salt': 'Bajo en sal',
  'en:ecoce': 'ECOCE',
  'en:nutriscore-grade-a': 'Nutri-Score A',
  'en:nutriscore-grade-b': 'Nutri-Score B',
  'en:nutriscore-grade-c': 'Nutri-Score C',
  'en:nutriscore-grade-e': 'Nutri-Score E',
  'en:plastic-free': 'Sin plástico',
  'en:100-italian-olives': '100 % aceitunas italianas',
  'en:100-italian-eggs': '100 % huevo italiano',
  'en:100-italian-vinegar': '100 % vinagre italiano',
  'en:100-italian-rice': '100 % arroz italiano',
  'en:100-nuts': '100 % frutos secos',
  'en:artisanally-cured-in-brine': 'Curado artesanal en salmuera',
  'en:artisanally-made': 'Elaboración artesanal',
  'en:no-dyes-or-preservatives': 'Sin colorantes ni conservadores',
  'en:rich-in-vitamin-b9': 'Rico en vitamina B9',
  'en:rich-in-vitamin-d': 'Rico en vitamina D',
  'en:rich-in-iron': 'Rico en hierro',
  'en:rich-in-vegetable-protein': 'Rico en proteína vegetal',
  'en:high-content-of-unsaturated-fat': 'Alto contenido de grasa insaturada',
  'en:no-flavors': 'Sin saborizantes',
  'en:gmos': 'Transgénicos',
  'en:no-peanuts': 'Sin cacahuate',
  'en:no-nuts': 'Sin frutos secos',
  'en:no-gelatin': 'Sin grenetina',
  'en:no-alcohol': 'Sin alcohol',
  'en:no-vegan': 'No vegano',
  'en:contains-alcohol': 'Contiene alcohol',
  'en:contains-soy': 'Contiene soya',
  'en:contains-lactose': 'Contiene lactosa',
  'en:contains-palm-oil': 'Contiene aceite de palma',
  'en:free-range': 'De libre pastoreo',
  'en:free-range-eggs': 'Huevo de libre pastoreo',
  'en:aged-in-wood': 'Añejado en madera',
  'en:1-for-the-planet': '1% para el planeta',
  'en:na': '',
  'en:unknown': '',
  'en:fr-bio-01': 'Orgánico FR-BIO-01',
  'en:sin-conservadores': 'Sin conservadores',
  'en:high-in-calcium': 'Alto en calcio',
  'en:high-in-omega-3': 'Alto en omega 3',
  'en:with-olive-oil': 'Con aceite de oliva',
  'en:with-fructose': 'Con fructosa',
  'en:with-sourdough': 'Con masa madre',
  'en:no-hydrogenated-fats': 'Sin grasas hidrogenadas',
  'en:not-recommended-for-children-under-3-years': 'No recomendado para menores de 3 años',
  'en:superior-quality': 'Calidad superior',
  'en:no-artificial-sweeteners': 'Sin edulcorantes artificiales',
  'en:no-artificial-additives': 'Sin aditivos artificiales',
  'en:without-sweeteners': 'Sin edulcorantes',
  'en:without-oil': 'Sin aceite',
  'en:without-vegetable-oils': 'Sin aceites vegetales',
  'en:without-modified-starches': 'Sin almidones modificados',
  'en:without-pesticide-residues': 'Sin residuos de pesticidas',
  'en:without-antibiotics-since-birth': 'Sin antibióticos desde el nacimiento',
  'en:no-antibiotics': 'Sin antibióticos',
  'en:no-high-fructose-corn-syrup': 'Sin jarabe de maíz de alta fructosa',
  'en:no-fructose-syrup': 'Sin jarabe de fructosa',
  'en:no-starch-added': 'Sin almidón añadido',
  'en:no-firming-agents-added': 'Sin agentes endurecedores añadidos',
  'en:additive-free': 'Sin aditivos',
  'en:unsweetened': 'Sin endulzar',
  'en:non-dairy': 'Sin lácteos',
  'en:whole-grain': 'Grano entero',
  'en:low-glycemic': 'Bajo índice glucémico',
  'en:low-gi': 'Bajo índice glucémico',
  'en:glyphosate-residue-free': 'Sin residuos de glifosato',
  'en:biodegradable': 'Biodegradable',
  'en:natural-product': 'Producto natural',
  'en:real-food': 'Comida real',
  'en:pure-cocoa-butter': 'Manteca de cacao pura',
  'en:genuine-chocolate': 'Chocolate genuino',
  'en:vegetarian-society-approved': 'Aprobado por la Vegetarian Society',
  'en:fair-trade-organic': 'Comercio justo y orgánico',
  'en:contains-bioengineered-food-ingredients': 'Contiene ingredientes biotecnológicos',
  'en:vitamin-b12-source': 'Fuente de vitamina B12',
  'en:phosphore-source': 'Fuente de fósforo',
  'en:carbon-compensated-product': 'Producto con carbono compensado',
  'en:50-less-fat': '50 % menos grasa',
  'en:96-less-salt': '96 % menos sal',
  'en:zero-calories': 'Cero calorías',
  'en:easy-to-digest': 'Fácil de digerir',
  'en:gut-friendly': 'Cuida la digestión',
  'en:raw': 'Crudo',
  'en:enriched-with-vitamins': 'Enriquecido con vitaminas',
  'en:artificial-flavors': 'Saborizantes artificiales',
  'en:with-artificial-flavors': 'Con saborizantes artificiales',
  'en:sulphur-dioxide-and-sulphites': 'Sulfitos',
  'en:mustard': 'Mostaza',
  'en:celery': 'Apio',
  'en:molluscs': 'Moluscos',
  'es:contiene-edulcorantes-no-recomendable-en-ninos': 'Contiene edulcorantes, no recomendable en niños',
  'es:alto-en-calorias': 'Alto en calorías',
  'es:alto-en-grasas-saturadas': 'Alto en grasas saturadas',
  'es:alto-en-azucares': 'Alto en azúcares',
  'es:alto-en-sodio': 'Alto en sodio',
  'es:exceso-en-calorias': 'Exceso en calorías',
  'es:exceso-en-azucares': 'Exceso en azúcares',
  'es:exceso-en-grasas-saturadas': 'Exceso en grasas saturadas',
  'es:exceso-en-grasas-totales': 'Exceso en grasas totales',
  'es:empresa-socialmente-responsable': 'Empresa socialmente responsable',
  'es:cereal-integral-garantizado': 'Cereal integral garantizado',
  'es:proteina-vegetal': 'Proteína vegetal',
  'es:energia': 'Energía',
  'es:sin-tacc': 'Sin TACC',
  'es:empaque-degradable': 'Empaque degradable',
  'es:endulzado-con-splenda': 'Endulzado con Splenda',
  'es:cero-conservadores': 'Cero conservadores',
  'es:grano-entero': 'Grano entero',
  'es:granos-enteros': 'Granos enteros',
  'es:no-vegano': 'No vegano',
  'es:organico-sagarpa-mexico': 'Orgánico SAGARPA México',
  'es:empaque-bioamigable': 'Empaque bioamigable',
  'es:producto-de-italia': 'Producto de Italia',
  'es:100-natural': '100 % natural',
  'es:baja-en-grasa': 'Baja en grasa',
  'es:baja-en-sodio': 'Baja en sodio',
  'es:mantenga-limpia-la-ciudad': 'Mantenga limpia la ciudad',
  'es:manten-limpia-tu-ciudad': 'Mantén limpia tu ciudad',
  'es:conserve-el-ambiente': 'Conserve el ambiente',
  'es:limpiemos-nuestro-mexico': 'Limpiemos nuestro México',
  'fr:triman': 'Triman',
  'fr:a-votre-service': 'A su servicio',
  'fr:tidy-man': 'Tidyman',
  'fr:ab-agriculture-biologique': 'Agricultura ecológica (AB)',
  'fr:certifie-ecosocial-par-ibd': 'Certificado ecosocial por IBD',
  'fr:entrepreneurs-engages': 'Emprendedores comprometidos',
};

const PAISES: Record<string, string> = {
  mexico: 'México',
  spain: 'España',
  italy: 'Italia',
  france: 'Francia',
  germany: 'Alemania',
  belgium: 'Bélgica',
  argentina: 'Argentina',
  colombia: 'Colombia',
  brazil: 'Brasil',
  usa: 'Estados Unidos',
  switzerland: 'Suiza',
  swiss: 'Suiza',
  canada: 'Canadá',
  'the-eu': 'la UE',
  eu: 'la UE',
};

const PALABRAS: Record<string, string> = {
  sugar: 'azúcar',
  sugars: 'azúcares',
  fat: 'grasa',
  fats: 'grasas',
  salt: 'sal',
  sodium: 'sodio',
  milk: 'leche',
  gluten: 'gluten',
  lactose: 'lactosa',
  cholesterol: 'colesterol',
  preservatives: 'conservadores',
  preservative: 'conservador',
  colorings: 'colorantes',
  colours: 'colorantes',
  colors: 'colorantes',
  coloring: 'colorante',
  colouring: 'colorante',
  colourings: 'colorantes',
  flavors: 'saborizantes',
  flavours: 'saborizantes',
  flavor: 'saborizante',
  flavour: 'saborizante',
  sweeteners: 'edulcorantes',
  sweetener: 'edulcorante',
  additives: 'aditivos',
  additive: 'aditivo',
  additived: 'aditivos',
  gmos: 'transgénicos',
  gmo: 'transgénico',
  soy: 'soya',
  eggs: 'huevo',
  egg: 'huevo',
  wheat: 'trigo',
  peanuts: 'cacahuate',
  peanut: 'cacahuate',
  nuts: 'frutos secos',
  palm: 'palma',
  oil: 'aceite',
  oils: 'aceites',
  fibre: 'fibra',
  fiber: 'fibra',
  fibres: 'fibra',
  fibers: 'fibra',
  proteins: 'proteína',
  protein: 'proteína',
  hydrogenated: 'hidrogenadas',
  saturated: 'saturada',
  unsaturated: 'insaturada',
  artificial: 'artificiales',
  natural: 'natural',
  caffeine: 'cafeína',
  msg: 'glutamato monosódico',
  bisphenol: 'bisfenol',
  italian: 'italiano',
  vegetable: 'vegetal',
  tomatoes: 'tomates',
  tomato: 'tomate',
  olives: 'aceitunas',
  vinegar: 'vinagre',
  rice: 'arroz',
  calcium: 'calcio',
  iron: 'hierro',
  vitamin: 'vitamina',
  vitamins: 'vitaminas',
  organic: 'orgánico',
  sustainable: 'sostenible',
  children: 'niños',
  pregnant: 'embarazadas',
  women: 'mujeres',
  people: 'personas',
  sunflower: 'girasol',
  olive: 'oliva',
  alcohol: 'alcohol',
  starch: 'almidón',
  starches: 'almidones',
  modified: 'modificados',
  antibiotics: 'antibióticos',
  fructose: 'fructosa',
  syrup: 'jarabe',
  corn: 'maíz',
  whole: 'entero',
  grain: 'grano',
  dyes: 'colorantes',
  enhancer: 'potenciador',
  sulphites: 'sulfitos',
  sulfites: 'sulfitos',
  added: 'añadido',
  free: 'libre',
  content: 'contenido',
  and: 'y',
  or: 'o',
  of: 'de',
  with: 'con',
  without: 'sin',
  from: 'de',
  for: 'para',
  in: 'en',
  no: 'sin',
  low: 'bajo',
  high: 'alto',
  not: 'no',
  under: 'menores de',
  years: 'años',
  azucar: 'azúcar',
  azucares: 'azúcares',
  calorias: 'calorías',
  ninos: 'niños',
  proteina: 'proteína',
  anadida: 'añadida',
  anadidas: 'añadidas',
  anadido: 'añadido',
  mexico: 'México',
  organico: 'orgánico',
  lacteos: 'lácteos',
  sodio: 'sodio',
  grasa: 'grasa',
  grasas: 'grasas',
  conservadores: 'conservadores',
};

const ACENTOS: Record<string, string> = {
  azucares: 'azúcares',
  azucar: 'azúcar',
  calorias: 'calorías',
  caloria: 'caloría',
  ninos: 'niños',
  proteina: 'proteína',
  proteinas: 'proteínas',
  energia: 'energía',
  organico: 'orgánico',
  organica: 'orgánica',
  lacteo: 'lácteo',
  lacteos: 'lácteos',
  anadida: 'añadida',
  anadidas: 'añadidas',
  anadido: 'añadido',
  mas: 'más',
  mexico: 'México',
  espanol: 'español',
  quimicos: 'químicos',
  acido: 'ácido',
  rapido: 'rápido',
  facil: 'fácil',
  cafe: 'café',
};

function frase(texto: string): string {
  const limpio = texto.replace(/\s+/g, ' ').trim();
  if (!limpio) {
    return limpio;
  }
  return limpio.charAt(0).toLocaleUpperCase('es-MX') + limpio.slice(1);
}

function acentuar(texto: string): string {
  return texto
    .split(' ')
    .map((palabra) => ACENTOS[palabra] ?? palabra)
    .join(' ');
}

function traducirPalabras(slug: string): string {
  const partes = slug
    .split('-')
    .map((palabra) => PALABRAS[palabra] ?? palabra)
    .filter((palabra) => palabra && palabra !== 'the' && palabra !== 'a');
  return partes.join(' ');
}

function pareceEspanol(slug: string): boolean {
  return /^(sin|con|bajo|alto|hecho|libre|deslactos|organico|exceso|producto|contiene|puede|certificacion|avalado|de-|no-contiene|no-vegano)/.test(
    slug,
  );
}

function traducirSlug(slug: string): string {
  const acidez = slug.match(/^(\d+)-acidity$/);
  if (acidez) {
    return `Acidez ${acidez[1]}`;
  }
  if (/^[a-z]{2}-(bio|eco|org)-/.test(slug)) {
    return `Orgánico ${slug.toUpperCase()}`;
  }
  if (slug.startsWith('made-in-')) {
    const lugar = slug.slice('made-in-'.length);
    return `Hecho en ${PAISES[lugar] ?? frase(traducirPalabras(lugar)).toLocaleLowerCase('es-MX')}`;
  }
  if (slug.startsWith('no-added-')) {
    return frase(`sin ${traducirPalabras(slug.slice('no-added-'.length))} añadido`);
  }
  if (slug.startsWith('no-artificial-')) {
    return frase(`sin ${traducirPalabras(slug.slice('no-artificial-'.length))} artificiales`);
  }
  if (slug.startsWith('low-or-no-')) {
    return frase(`bajo o sin ${traducirPalabras(slug.slice('low-or-no-'.length))}`);
  }
  if (slug.startsWith('contains-')) {
    return frase(`contiene ${traducirPalabras(slug.slice('contains-'.length))}`);
  }
  if (slug.startsWith('source-of-') || slug.endsWith('-source')) {
    const resto = slug.startsWith('source-of-') ? slug.slice('source-of-'.length) : slug.slice(0, -'-source'.length);
    return frase(`fuente de ${traducirPalabras(resto)}`);
  }
  if (slug.startsWith('rich-in-')) {
    return frase(`rico en ${traducirPalabras(slug.slice('rich-in-'.length))}`);
  }
  if (slug.startsWith('high-in-') || slug.startsWith('high-')) {
    const resto = slug.startsWith('high-in-') ? slug.slice('high-in-'.length) : slug.slice('high-'.length);
    return frase(`alto en ${traducirPalabras(resto)}`);
  }
  if (slug.startsWith('with-')) {
    return frase(`con ${traducirPalabras(slug.slice('with-'.length))}`);
  }
  if (slug.startsWith('without-')) {
    return frase(`sin ${traducirPalabras(slug.slice('without-'.length))}`);
  }
  if (slug.startsWith('100-')) {
    return frase(`100 % ${traducirPalabras(slug.slice('100-'.length))}`);
  }
  if (slug.startsWith('no-')) {
    return frase(`sin ${traducirPalabras(slug.slice('no-'.length))}`);
  }
  if (slug.startsWith('low-')) {
    return frase(`bajo en ${traducirPalabras(slug.slice('low-'.length))}`);
  }
  if (slug.startsWith('reduced-')) {
    return frase(`reducido en ${traducirPalabras(slug.slice('reduced-'.length))}`);
  }
  if (pareceEspanol(slug)) {
    return frase(acentuar(slug.replace(/-/g, ' ')));
  }
  return frase(acentuar(traducirPalabras(slug)));
}

export function selloLabel(tag: string): string {
  if (Object.prototype.hasOwnProperty.call(SELLO_ES, tag)) {
    return SELLO_ES[tag];
  }
  const slug = tag.includes(':') ? tag.slice(tag.indexOf(':') + 1) : tag;
  const limpio = slug.replace(/-/g, ' ').trim();
  if (!limpio) {
    return tag;
  }
  if (tag.startsWith('es:') || tag.startsWith('fr:') || pareceEspanol(slug)) {
    return frase(acentuar(limpio));
  }
  return traducirSlug(slug);
}
