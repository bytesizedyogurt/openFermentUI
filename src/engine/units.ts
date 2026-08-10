// Purpose-built unit engine for the openFerment ontology (OF-DES-001 §7.5).
// Linear families use factor-to-base; temperature is affine.

export interface UnitDef {
  family: string;
  factor: number; // multiply by this to get family base
  offset?: number; // affine (temperature): base = value * factor + offset
  label: string; // canonical display form
}

// Family base units: rate=h⁻¹, time=h, massConc=g L⁻¹, mass=g, volume=L,
// percent=%, yield=g g⁻¹, volProd=g L⁻¹ h⁻¹, specProd=mg g⁻¹ h⁻¹,
// odDcw=g L⁻¹ OD⁻¹, temp=°C, light=µmol m⁻² s⁻¹, ph=(none), molar=mol L⁻¹
const U: Record<string, UnitDef> = {
  'h⁻¹': { family: 'rate', factor: 1, label: 'h⁻¹' },
  'd⁻¹': { family: 'rate', factor: 1 / 24, label: 'd⁻¹' },
  'min⁻¹': { family: 'rate', factor: 60, label: 'min⁻¹' },
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
};

// The SI/canonical display unit chosen per family for the "SI twin".
const SI_UNIT: Record<string, string> = {
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
};

// Alias normalization: accept human/ASCII notations.
const ALIASES: Record<string, string> = {
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

export function normalizeUnit(raw: string): string | null {
  const t = raw.trim();
  if (t in U) return t;
  const lower = t.toLowerCase();
  if (ALIASES[t]) return ALIASES[t];
  if (ALIASES[lower]) return ALIASES[lower];
  // Try unicode-superscript-insensitive match
  const strip = (s: string) =>
    s.replace(/⁻¹/g, '-1').replace(/⁻²/g, '-2').replace(/⁻³/g, '-3').replace(/³/g, '3').replace(/²/g, '2').replace(/\s+/g, ' ').toLowerCase();
  const target = strip(t);
  for (const key of Object.keys(U)) {
    if (strip(key) === target) return key;
  }
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
export function fmt(value: number, maxDecimals = 3): string {
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
