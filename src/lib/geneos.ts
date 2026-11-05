// The browser's side of geneOS's computations (OF-BLD-014 §6.4).
//
// The shelf, and a ceiling, a frontier or a sugar mix for one model. The
// service computes and keeps each as an artifact; with it down this says so,
// and nothing stands in for a result (E.2). Shares lib/http.ts's call, so the
// two failures are the same two: down, or refused in words.
//
// Every shape the service answers is its own, generated from its models into
// src/api/types.gen.ts (ADR-007). The hosts are the project's strains, as its
// strain catalogue keeps them (lib/catalogues.ts, alpha 2.2 E.9); a scenario
// names a strain by any of the names its entry keeps (`namesStrain`).
import type { components } from '@/api/types.gen';
import { ONTOLOGY_BY_ID, type FieldId, type ParameterDef } from '@/data/ontology';
import { carbonSourceId } from '@/data/vocabulary';
import type { Strain } from './catalogues';
import type { Scenario } from './proforma';
import type { ExtractionRecord } from './review';
import { ServiceDown, ServiceRefused, call } from './http';

type S = components['schemas'];

/** One model on geneOS's shelf: its host, its scope and route, its licence, and why it cannot be loaded here, if so. */
export type GeneosModelInfo = S['GeneosModelInfo'];
/** A ceiling, a frontier or a sugar mix: an artifact and its evidence, or a finding in words with no number. */
export type GeneosResult = S['GeneosResult'];

export { ServiceDown as GeneosDown, ServiceRefused as GeneosRefused };

const post = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  call<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal });

export const geneosModels = (signal?: AbortSignal) => call<GeneosModelInfo[]>('/api/geneos/models', { signal });

export const geneosCeiling = (modelId: string, substrate: string, product = 'ethanol', signal?: AbortSignal) =>
  post<GeneosResult>('/api/geneos/ceiling', { modelId, product, substrate }, signal);

export const geneosFrontier = (modelId: string, substrate: string, product = 'ethanol', signal?: AbortSignal) =>
  post<GeneosResult>('/api/geneos/frontier', { modelId, product, substrate }, signal);

export const geneosMix = (modelId: string, a: string, b: string, product = 'ethanol', signal?: AbortSignal) =>
  post<GeneosResult>('/api/geneos/mix', { modelId, product, a, b }, signal);

/** The sugars geneOS's shelf knows, in the order a view offers them. */
export const SUBSTRATES = ['glucose', 'xylose', 'fructose'] as const;

/**
 * Each product a ceiling is computed for, and the ontology field its reported
 * yields are recorded under: an ethanol ceiling is held against ethanol
 * yields. A product with no entry has no reported yields to draw.
 */
export const YIELD_FIELD: Record<string, FieldId> = {
  ethanol: 'ethanol_yield_substrate',
};

/** How a view names each product: in the picker, in a title, on an axis. */
export interface ProductWords {
  /** The picker's option. */
  option: string;
  /** In a sentence: "How much ethanol…". */
  short: string;
  /** The ceiling's quantity, on an axis and in a table. */
  quantity: string;
  /** What the drawn records are, singular: "ethanol yield". */
  reported: string;
}

export const PRODUCT_WORDS: Record<string, ProductWords> = {
  ethanol: { option: 'Ethanol', short: 'ethanol', quantity: 'Ethanol yield on substrate', reported: 'ethanol yield' },
};

/** A product's words, or its id in each place when the map has none. */
export const productWords = (product: string): ProductWords =>
  PRODUCT_WORDS[product] ?? { option: product, short: product, quantity: `${product} yield on substrate`, reported: `${product} yield` };

/** Whether the ontology holds the field a product's reported yields carry. */
export function yieldFieldKnown(product: string): boolean {
  const field = YIELD_FIELD[product];
  return !!field && !!(ONTOLOGY_BY_ID as Record<string, ParameterDef | undefined>)[field];
}

/** The product a ceiling's basis names, `ethanol` where it names none (the service's default). */
export const productOfBasis = (inputs: { name: string; value: unknown }[]): string =>
  String(inputs.find((i) => i.name === 'product')?.value ?? 'ethanol');

/** A frontier's or a mix's points, as the worker returns them. */
export interface FrontierPointOut {
  growth: number;
  flux: number;
  gPerG: number;
}
export interface MixPointOut {
  shareA: number;
  uptakeA: number;
  uptakeB: number;
  flux: number;
  gPerG: number;
}

/**
 * The reported yields of `product` a ceiling on `sugar` can be held against:
 * those whose carbon source, in the paper's words, resolves to that sugar. The
 * rest (another feed, or none stated) are counted and not drawn, so a yield on
 * oil or glycerol is never ringed as above a glucose ceiling (§6.R). A product
 * whose yield field the ontology does not hold draws nothing.
 */
export function yieldsOnSugar(
  records: ExtractionRecord[],
  sugar: string,
  product = 'ethanol',
): { on: ExtractionRecord[]; elsewhere: number } {
  if (!yieldFieldKnown(product)) return { on: [], elsewhere: 0 };
  const field = YIELD_FIELD[product];
  const yields = records.filter((r) => r.field === field);
  const on = yields.filter((r) => r.carbonSource && carbonSourceId(r.carbonSource) === sugar);
  return { on, elsewhere: yields.length - on.length };
}

/** The names a strain goes by: its name, its species and the other names papers give it, as its entry keeps them. */
export const strainNames = (s: Pick<Strain, 'name' | 'species' | 'aliases'>): string[] =>
  [s.name, s.species ?? '', ...(s.aliases ?? [])].filter(Boolean);

/**
 * Whether a scenario names a strain: one of `names` (`strainNames`), longer than two letters, in the scenario's name,
 * description or product. The service binds a scenario's inputs to records each time it runs, and the scenario's row
 * holds its name, its description and its product, so a strain links to a scenario by name.
 */
export function namesStrain(sc: Pick<Scenario, 'name' | 'description' | 'product'>, names: string[]): boolean {
  const text = `${sc.name} ${sc.description} ${sc.product}`.toLowerCase();
  return names.some((n) => n.length > 2 && text.includes(n.toLowerCase()));
}
