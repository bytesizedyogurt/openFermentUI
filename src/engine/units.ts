// Purpose-built unit engine for the openFerment ontology (OF-DES-001 §7.5).
// Linear families use factor-to-base; temperature is affine.
//
// THE SERVICE HOLDS THE SAME TABLES (OF-BLD-012 §5.3). `core/openferment_core/
// units.py` normalises and converts from core/openferment_core/schema/
// units.json, and this file is the browser's mirror of it, held to it by test:
// `scripts/export-unit-fixtures.ts` records what these functions answer for a
// fixed set of inputs, and test_units.py asserts the service answers the same
// on every pair. A disagreement fails the test and names the pair.

export interface UnitDef {
  family: string;
  factor: number; // multiply by this to get family base
  offset?: number; // affine (temperature): base = value * factor + offset
  label: string; // canonical display form
}

// Family base units: rate=h⁻¹, time=h, massConc=g L⁻¹, mass=g, volume=L,
// percent=%, yield=g g⁻¹, volProd=g L⁻¹ h⁻¹, specProd=mg g⁻¹ h⁻¹,
// odDcw=g L⁻¹ OD⁻¹, temp=°C, light=µmol m⁻² s⁻¹, ph=(none), molar=mol L⁻¹,
// percentCdw=% CDW, molarMass=g mol⁻¹, costUSDVolume=USD gal⁻¹,
// specMolarRate=mmol g⁻¹ h⁻¹
export const U: Record<string, UnitDef> = {
  'h⁻¹': { family: 'rate', factor: 1, label: 'h⁻¹' },
  'd⁻¹': { family: 'rate', factor: 1 / 24, label: 'd⁻¹' },
  'min⁻¹': { family: 'rate', factor: 60, label: 'min⁻¹' },
  // OF-BLD-020 §3.2: a kLa is as often written per second as per hour.
  's⁻¹': { family: 'rate', factor: 3600, label: 's⁻¹' },
  h: { family: 'time', factor: 1, label: 'h' },
  min: { family: 'time', factor: 1 / 60, label: 'min' },
  d: { family: 'time', factor: 24, label: 'd' },
  s: { family: 'time', factor: 1 / 3600, label: 's' },
  'g L⁻¹': { family: 'massConc', factor: 1, label: 'g L⁻¹' },
  'mg L⁻¹': { family: 'massConc', factor: 0.001, label: 'mg L⁻¹' },
  'µg L⁻¹': { family: 'massConc', factor: 0.000001, label: 'µg L⁻¹' },
  'kg m⁻³': { family: 'massConc', factor: 1, label: 'kg m⁻³' },
  'mg mL⁻¹': { family: 'massConc', factor: 1, label: 'mg mL⁻¹' },
  'µg mL⁻¹': { family: 'massConc', factor: 0.001, label: 'µg mL⁻¹' },
  'mg dL⁻¹': { family: 'massConc', factor: 0.01, label: 'mg dL⁻¹' },
  'g 100mL⁻¹': { family: 'massConc', factor: 10, label: 'g 100 mL⁻¹' },
  g: { family: 'mass', factor: 1, label: 'g' },
  mg: { family: 'mass', factor: 0.001, label: 'mg' },
  µg: { family: 'mass', factor: 0.000001, label: 'µg' },
  kg: { family: 'mass', factor: 1000, label: 'kg' },
  L: { family: 'volume', factor: 1, label: 'L' },
  mL: { family: 'volume', factor: 0.001, label: 'mL' },
  µL: { family: 'volume', factor: 0.000001, label: 'µL' },
  'm³': { family: 'volume', factor: 1000, label: 'm³' },
  '%': { family: 'percent', factor: 1, label: '%' },
  '% DW': { family: 'percent', factor: 1, label: '% DW' },
  '% v/v': { family: 'percent', factor: 1, label: '% v/v' },
  '% w/v': { family: 'percent', factor: 1, label: '% w/v' },
  'g g⁻¹': { family: 'yield', factor: 1, label: 'g g⁻¹' },
  'mg g⁻¹': { family: 'yield', factor: 0.001, label: 'mg g⁻¹' },
  'g L⁻¹ h⁻¹': { family: 'volProd', factor: 1, label: 'g L⁻¹ h⁻¹' },
  'mg L⁻¹ h⁻¹': { family: 'volProd', factor: 0.001, label: 'mg L⁻¹ h⁻¹' },
  'g L⁻¹ d⁻¹': { family: 'volProd', factor: 1 / 24, label: 'g L⁻¹ d⁻¹' },
  'mg g⁻¹ h⁻¹': { family: 'specProd', factor: 1, label: 'mg g⁻¹ h⁻¹' },
  'g g⁻¹ h⁻¹': { family: 'specProd', factor: 1000, label: 'g g⁻¹ h⁻¹' },
  'mg g⁻¹ d⁻¹': { family: 'specProd', factor: 1 / 24, label: 'mg g⁻¹ d⁻¹' },
  'g L⁻¹ OD⁻¹': { family: 'odDcw', factor: 1, label: 'g L⁻¹ OD⁻¹' },
  '°C': { family: 'temp', factor: 1, offset: 0, label: '°C' },
  K: { family: 'temp', factor: 1, offset: -273.15, label: 'K' },
  '°F': { family: 'temp', factor: 5 / 9, offset: -160 / 9, label: '°F' },
  'µmol m⁻² s⁻¹': { family: 'light', factor: 1, label: 'µmol m⁻² s⁻¹' },
  'µE m⁻² s⁻¹': { family: 'light', factor: 1, label: 'µE m⁻² s⁻¹' },
  '': { family: 'ph', factor: 1, label: '' },
  'mol L⁻¹': { family: 'molar', factor: 1, label: 'mol L⁻¹' },
  'mmol L⁻¹': { family: 'molar', factor: 0.001, label: 'mmol L⁻¹' },
  'µmol L⁻¹': { family: 'molar', factor: 0.000001, label: 'µmol L⁻¹' },
  'vvm': { family: 'vvm', factor: 1, label: 'vvm' },
  rpm: { family: 'rpm', factor: 1, label: 'rpm' },
  'µm': { family: 'length', factor: 0.000001, label: 'µm' },
  cm: { family: 'length', factor: 0.01, label: 'cm' },
  m: { family: 'length', factor: 1, label: 'm' },
  nm: { family: 'length', factor: 1e-9, label: 'nm' },
  mm: { family: 'length', factor: 0.001, label: 'mm' },

  // ── OF-COR-001 §17 ontology v1 ──────────────────────────────────────
  // Expression share. Deliberately its OWN family, not `percent`: a share of
  // total soluble protein is not interconvertible with a concentration, and
  // keeping it separate makes the engine refuse by construction (Rule 2).
  '% TSP': { family: 'proteinShare', factor: 1, label: '% TSP' },
  '% TCP': { family: 'proteinShare', factor: 1, label: '% TCP' },
  '% of native sites': { family: 'percent', factor: 1, label: '% of native sites' },
  '% sedimentable': { family: 'percent', factor: 1, label: '% sedimentable' },
  '% of total expressed': { family: 'percent', factor: 1, label: '% of total expressed' },
  '% of total protein': { family: 'percent', factor: 1, label: '% of total protein' },

  'mol mol⁻¹': { family: 'stoichiometry', factor: 1, label: 'mol mol⁻¹' },
  '×': { family: 'fold', factor: 1, label: '×' },
  'colonies µg⁻¹': { family: 'transformationEff', factor: 1, label: 'colonies µg⁻¹ DNA' },
  residue: { family: 'position', factor: 1, label: 'residue' },
  'kWh kg⁻¹': { family: 'energyPerMass', factor: 1, label: 'kWh kg⁻¹' },
  'MJ kg⁻¹': { family: 'energyPerMass', factor: 1 / 3.6, label: 'MJ kg⁻¹' },

  // Currency is per-family on purpose. Converting EUR/kg to USD/kg needs an
  // exchange rate with a date, which a unit engine has no business inventing —
  // and OF-COR-001 §16 carries costs in both (Acién 69 €/kg, GFI $4–6/kg).
  'USD kg⁻¹': { family: 'costUSD', factor: 1, label: 'USD kg⁻¹' },
  'EUR kg⁻¹': { family: 'costEUR', factor: 1, label: 'EUR kg⁻¹' },

  // ── OF-BLD-014 §2.1 — the polymer family ───────────────────────────
  // A polymer's share of dry cell mass. Its OWN family, not `percent`, for the
  // reason `% TSP` has one: a share of biomass is not a concentration, and a
  // separate family makes the engine refuse by construction.
  '% CDW': { family: 'percentCdw', factor: 1, label: '% CDW' },
  // Molar mass. A dalton is one gram per mole, so kg mol⁻¹ is the kDa.
  'g mol⁻¹': { family: 'molarMass', factor: 1, label: 'g mol⁻¹' },
  Da: { family: 'molarMass', factor: 1, label: 'Da' },
  kDa: { family: 'molarMass', factor: 1000, label: 'kDa' },

  // ── the yeast-ethanol program (thread Q) ────────────────────────────
  // A price per US gallon, as ethanol techno-economic analyses quote one.
  // Its OWN family, not `costUSD`: a gallon is a volume and a kilogram a
  // mass, and between them stands the product's density, which a unit
  // engine has no business assuming. `gal` is read as the US gallon.
  'USD gal⁻¹': { family: 'costUSDVolume', factor: 1, label: 'USD gal⁻¹' },

  // ── OF-BLD-020 §3.2 — an oxygen uptake per gram of cells ─────────────
  // Moles per gram per hour. Its OWN family, not `specProd`: between a
  // mole and a gram stands the molar mass of what is taken up, which a unit
  // engine has no business assuming.
  'mmol g⁻¹ h⁻¹': { family: 'specMolarRate', factor: 1, label: 'mmol g⁻¹ h⁻¹' },
  'µmol g⁻¹ h⁻¹': { family: 'specMolarRate', factor: 0.001, label: 'µmol g⁻¹ h⁻¹' },
  'mol g⁻¹ h⁻¹': { family: 'specMolarRate', factor: 1000, label: 'mol g⁻¹ h⁻¹' },
};

/**
 * Conversions the engine refuses *with an explanation* rather than a bare
 * dimension error (OF-COR-001 §17 Rule 2). Dimensional analysis already blocks
 * these; the point of this table is that the UI can say why, turning the unit
 * engine from a convenience into an epistemic guardrail.
 */
export const REFUSALS: { a: string; b: string; because: string }[] = [
  {
    a: 'proteinShare',
    b: 'massConc',
    because:
      'A share of total soluble protein and a concentration are not interconvertible without the cell density and the total-protein fraction of the biomass. Record those two values and the conversion becomes possible; guessing them would fabricate a titer.',
  },
  {
    a: 'proteinShare',
    b: 'percent',
    because:
      'Both are percentages but of different denominators — % of total soluble protein is not % of dry weight or % of native phosphorylation sites. Comparing them directly is a category error.',
  },
  {
    a: 'costUSD',
    b: 'costEUR',
    because:
      'Currency conversion needs an exchange rate with a date attached. The engine will not invent one — record the rate and the date as an explicit assumption.',
  },
  {
    // OF-BLD-014 §2.1: a PHA content and a PHA titre.
    a: 'percentCdw',
    b: 'massConc',
    because:
      'A share of dry cell mass and a concentration are not interconvertible without the biomass density of that culture. Record the dry cell weight per litre the paper reports for it and the conversion becomes possible; guessing it would fabricate a titre.',
  },
  {
    // OF-BLD-020 §3.2: a specific oxygen uptake and a specific rate in grams.
    a: 'specMolarRate',
    b: 'specProd',
    because:
      'A rate in moles per gram per hour and one in grams per gram per hour differ by the molar mass of what is taken up or made. Record which substance it is and convert by its molar mass as a stated step; the engine will not assume it.',
  },
  {
    // Thread Q: a minimum ethanol selling price and minimum_selling_price.
    a: 'costUSDVolume',
    b: 'costUSD',
    because:
      'A price per gallon and a price per kilogram are not interconvertible without the density of the product. Record the density the analysis assumes for it and the conversion becomes possible; guessing it would fabricate a price.',
  },
];

/**
 * Narrow a record value to a number, or null if it is categorical. Call sites
 * that convert or compute MUST go through this rather than casting — a
 * categorical value silently coerced to NaN would poison a median.
 */
export function asNumber(v: number | string): number | null {
  return typeof v === 'number' && isFinite(v) ? v : null;
}

/** If a refusal is a known trap, explain it; otherwise return null. */
export function explainRefusal(fromUnit: string, toUnit: string): string | null {
  const f = U[normalizeUnit(fromUnit) ?? ''];
  const t = U[normalizeUnit(toUnit) ?? ''];
  if (!f || !t || f.family === t.family) return null;
  for (const r of REFUSALS) {
    if ((r.a === f.family && r.b === t.family) || (r.b === f.family && r.a === t.family))
      return r.because;
  }
  return null;
}

// The SI/canonical display unit chosen per family for the "SI twin".
export const SI_UNIT: Record<string, string> = {
  proteinShare: '% TSP',
  stoichiometry: 'mol mol⁻¹',
  fold: '×',
  transformationEff: 'colonies µg⁻¹',
  position: 'residue',
  energyPerMass: 'kWh kg⁻¹',
  costUSD: 'USD kg⁻¹',
  costEUR: 'EUR kg⁻¹',
  rate: 'h⁻¹',
  time: 'h',
  massConc: 'kg m⁻³',
  mass: 'g',
  volume: 'L',
  percent: '%',
  yield: 'g g⁻¹',
  volProd: 'g L⁻¹ h⁻¹',
  specProd: 'mg g⁻¹ h⁻¹',
  odDcw: 'g L⁻¹ OD⁻¹',
  temp: '°C',
  light: 'µmol m⁻² s⁻¹',
  ph: '',
  molar: 'mol L⁻¹',
  vvm: 'vvm',
  rpm: 'rpm',
  length: 'm',
  percentCdw: '% CDW',
  // The kDa is numerically the SI kg mol⁻¹.
  molarMass: 'kDa',
  costUSDVolume: 'USD gal⁻¹',
  specMolarRate: 'mmol g⁻¹ h⁻¹',
};

// Alias normalization: accept human/ASCII notations.
export const ALIASES: Record<string, string> = {
  '1/h': 'h⁻¹',
  'h-1': 'h⁻¹',
  '/h': 'h⁻¹',
  'per hour': 'h⁻¹',
  '1/d': 'd⁻¹',
  'd-1': 'd⁻¹',
  '/d': 'd⁻¹',
  '/day': 'd⁻¹',
  'per day': 'd⁻¹',
  'g/l': 'g L⁻¹',
  'g/L': 'g L⁻¹',
  'mg/l': 'mg L⁻¹',
  'mg/L': 'mg L⁻¹',
  'ug/l': 'µg L⁻¹',
  'µg/L': 'µg L⁻¹',
  'kg/m3': 'kg m⁻³',
  'kg/m³': 'kg m⁻³',
  'mg/ml': 'mg mL⁻¹',
  'mg/mL': 'mg mL⁻¹',
  'ug/ml': 'µg mL⁻¹',
  'µg/mL': 'µg mL⁻¹',
  'mg/dl': 'mg dL⁻¹',
  'mg/dL': 'mg dL⁻¹',
  'g/100ml': 'g 100mL⁻¹',
  'g/100 mL': 'g 100mL⁻¹',
  'g/g': 'g g⁻¹',
  'mg/g': 'mg g⁻¹',
  'g/l/h': 'g L⁻¹ h⁻¹',
  'g/L/h': 'g L⁻¹ h⁻¹',
  'mg/l/h': 'mg L⁻¹ h⁻¹',
  'mg/L/h': 'mg L⁻¹ h⁻¹',
  'g/l/d': 'g L⁻¹ d⁻¹',
  'g/L/d': 'g L⁻¹ d⁻¹',
  'mg/g/h': 'mg g⁻¹ h⁻¹',
  'g/g/h': 'g g⁻¹ h⁻¹',
  'mg/g/d': 'mg g⁻¹ d⁻¹',
  // OF-BLD-020 §3.2: an oxygen uptake per gram of cells, and a kLa per second.
  'mmol/g/h': 'mmol g⁻¹ h⁻¹',
  'mmol/gdw/h': 'mmol g⁻¹ h⁻¹',
  'mmol gdw-1 h-1': 'mmol g⁻¹ h⁻¹',
  '1/s': 's⁻¹',
  '/s': 's⁻¹',
  'g/l/od': 'g L⁻¹ OD⁻¹',
  'g/L/OD': 'g L⁻¹ OD⁻¹',
  c: '°C',
  '°c': '°C',
  degc: '°C',
  'deg c': '°C',
  f: '°F',
  '°f': '°F',
  k: 'K',
  'umol/m2/s': 'µmol m⁻² s⁻¹',
  'µmol/m²/s': 'µmol m⁻² s⁻¹',
  'ue/m2/s': 'µE m⁻² s⁻¹',
  '%dw': '% DW',
  '% dw': '% DW',
  '%v/v': '% v/v',
  '% vv': '% v/v',
  '%w/v': '% w/v',
  // No-space forms of the expression-share units. Papers write "15%TSP" at
  // least as often as "15 % TSP", and the superscript-insensitive fallback
  // below cannot bridge a missing space.
  '%tsp': '% TSP',
  '%tcp': '% TCP',
  // OF-BLD-014 §2.1. '%CDW' reaches the first through the lower-cased lookup;
  // 'wt%' and '% (w/w)' are how PHA papers write a polymer's share of the
  // dry cells.
  '%cdw': '% CDW',
  '% cdw': '% CDW',
  'wt%': '% CDW',
  '% (w/w)': '% CDW',
  kda: 'kDa',
  'kg/mol': 'kDa',
  // Thread Q. How techno-economic analyses write a price per gallon or per
  // kilogram; every spelling names its currency and its denominator.
  '$/gal': 'USD gal⁻¹',
  'USD/gal': 'USD gal⁻¹',
  '$ gal-1': 'USD gal⁻¹',
  '$ gal⁻¹': 'USD gal⁻¹',
  // The minus sign journals print: the fallback below compares table keys,
  // not aliases, so the spelling with U+2212 needs its own entry.
  '$ gal−1': 'USD gal⁻¹',
  'US$/gal': 'USD gal⁻¹',
  '$/gallon': 'USD gal⁻¹',
  '$ per gallon': 'USD gal⁻¹',
  'usd per gallon': 'USD gal⁻¹',
  '$/kg': 'USD kg⁻¹',
  'USD/kg': 'USD kg⁻¹',
  // Thread Q's papers. A dot or nothing between the factors, and an hour
  // written out; each spelling is one unit and no other.
  'g.l-1': 'g L⁻¹',
  'g.l−1': 'g L⁻¹',
  'g l-1h-1': 'g L⁻¹ h⁻¹',
  'g l−1h−1': 'g L⁻¹ h⁻¹',
  'g/l hr': 'g L⁻¹ h⁻¹',
  'g/l/hr': 'g L⁻¹ h⁻¹',
  m: 'mol L⁻¹',
  mm: 'mmol L⁻¹',
  um: 'µmol L⁻¹',
  µm: 'µmol L⁻¹',
  'mol/l': 'mol L⁻¹',
  'mmol/l': 'mmol L⁻¹',
  ml: 'mL',
  ul: 'µL',
  'µl': 'µL',
  l: 'L',
  'm3': 'm³',
};

/**
 * Grams per gram with each gram labelled by what it weighs — g EtOH/g glucose,
 * gx/g, gDW gglucose⁻¹, g biomass [g glucose]⁻¹. The labels name the yield,
 * which the field already says; the unit is grams per gram. Each gram must
 * stand alone after its separator, so g kg⁻¹ and mg g⁻¹ never match. Read
 * against the stripped spelling; units.py holds the same two patterns.
 */
export const LABELLED_MASS_RATIO = [
  /^g(?:\s*[a-z]+)?\s*\/\s*g(?:\s*[a-z]+)?$/,
  /^g(?:\s*[a-z]+)?(?:\s*\[\s*|\s+)g(?:\s*[a-z]+)?\s*\]?\s*-1$/,
];

export function normalizeUnit(raw: string): string | null {
  const t = raw.trim();
  if (t in U) return t;
  const lower = t.toLowerCase();
  if (ALIASES[t]) return ALIASES[t];
  if (ALIASES[lower]) return ALIASES[lower];
  // Try unicode-superscript-insensitive match
  // The middot separators (mg·L⁻¹, mg⋅L⁻¹) are read as the space the table
  // uses — Python mirrors this exact sequence of replacements, so change it
  // in both places or the fixture test will say which one you forgot.
  const strip = (s: string) =>
    s.replace(/[·⋅]/g, ' ').replace(/[\u2212\u2013]/g, '-').replace(/⁻¹/g, '-1').replace(/⁻²/g, '-2').replace(/⁻³/g, '-3').replace(/³/g, '3').replace(/²/g, '2').replace(/\s+/g, ' ').toLowerCase();
  const target = strip(t);
  for (const key of Object.keys(U)) {
    if (strip(key) === target) return key;
  }
  if (LABELLED_MASS_RATIO.some((re) => re.test(target.trim()))) return 'g g⁻¹';
  return null;
}

export function unitFamily(unit: string): string | null {
  const n = normalizeUnit(unit);
  return n === null ? null : U[n].family;
}

export function sameFamily(a: string, b: string): boolean {
  const fa = unitFamily(a);
  const fb = unitFamily(b);
  return fa !== null && fa === fb;
}

/** Convert value between two units of the same family. Throws on mismatch. */
export function convert(value: number, from: string, to: string): number {
  const nf = normalizeUnit(from);
  const nt = normalizeUnit(to);
  if (nf === null) throw new Error(`Unknown unit: ${from}`);
  if (nt === null) throw new Error(`Unknown unit: ${to}`);
  const uf = U[nf];
  const ut = U[nt];
  if (uf.family !== ut.family)
    throw new Error(`Incompatible units: ${from} (${uf.family}) vs ${to} (${ut.family})`);
  const base = value * uf.factor + (uf.offset ?? 0);
  return (base - (ut.offset ?? 0)) / ut.factor;
}

/** SI-normalized twin per §7.5 (family's designated SI display unit). */
export function toSI(value: number, unit: string): { value: number; unit: string } {
  const n = normalizeUnit(unit);
  if (n === null) return { value, unit };
  const si = SI_UNIT[U[n].family];
  return { value: convert(value, n, si), unit: si };
}

/** Parse free text like "2 g/L", "0.15 h⁻¹", "200 mg/dL", "25 °C". */
export function parseQuantity(text: string): { value: number; unit: string } | null {
  const m = text.trim().match(/^(-?\d+(?:[.,]\d+)?(?:[eE]-?\d+)?)\s*(.*)$/);
  if (!m) return null;
  const value = parseFloat(m[1].replace(',', '.'));
  if (!isFinite(value)) return null;
  const rawUnit = m[2].trim();
  if (rawUnit === '') return { value, unit: '' };
  const unit = normalizeUnit(rawUnit);
  if (unit === null) return null;
  return { value, unit };
}

/** Format a number for display: sensible significant digits, no trailing noise. */
/**
 * Format a value for display. Categorical records (kinase_identity,
 * glycan_species) carry a string, and the right rendering for those is the
 * string itself — so this passes them through rather than producing NaN.
 */
export function fmt(value: number | string, maxDecimals = 3): string {
  if (typeof value === 'string') return value;
  if (!isFinite(value)) return '—';
  if (value === 0) return '0';
  const abs = Math.abs(value);
  if (abs >= 10000 || abs < 0.001) {
    return value.toExponential(2).replace('e', '×10^').replace('×10^+', '×10^');
  }
  let decimals = maxDecimals;
  if (abs >= 100) decimals = Math.min(1, maxDecimals);
  else if (abs >= 10) decimals = Math.min(2, maxDecimals);
  const s = value.toFixed(decimals);
  return s.replace(/\.?0+$/, '');
}

/** Round to a precision increment (e.g. 0.1 g) for pipettable recipes. */
export function roundToPrecision(value: number, increment: number): number {
  if (increment <= 0) return value;
  const rounded = Math.round(value / increment) * increment;
  const decimals = Math.max(0, -Math.floor(Math.log10(increment)) + 1);
  return parseFloat(rounded.toFixed(decimals));
}

/** Are two quantities equivalent within a tolerance (for checkpoint grading)? */
export function quantityEquals(
  a: { value: number; unit: string },
  b: { value: number; unit: string },
  tolerancePct = 2,
): boolean {
  if (!sameFamily(a.unit, b.unit)) return false;
  try {
    const av = convert(a.value, a.unit, b.unit);
    if (b.value === 0) return Math.abs(av) < 1e-12;
    return Math.abs(av - b.value) / Math.abs(b.value) <= tolerancePct / 100;
  } catch {
    return false;
  }
}
