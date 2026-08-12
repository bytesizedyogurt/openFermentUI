// Host organisms and the reference molecule's source species (OF-COR-001 §20).
// Replaces the four synthetic strains with the real host-comparison set.
// The collection itself now comes from the adapter; this module keeps only
// the derived views built on top of it.
import { STRAINS } from '@/data/source';

export { STRAINS };

import type { Strain } from './types';

/**
 * Strain alias table (OF-COR-001 §19, third trap).
 *
 * "Cell wall deficient" spans several distinct genotypes, and the literature
 * uses the names inconsistently: cw15, cw15-302, CC-4350, cwd mt+ arg7,
 * Elow47, UVM4 and UVM11 are related but NOT interchangeable. Normalising on
 * ingest prevents the platform from silently merging measurements made on
 * different organisms.
 */
export const STRAIN_ALIASES: Record<string, string> = {
  cw15: 'cw15',
  'cw15-302': 'cw15',
  'cc-4350': 'cw15',
  cc4350: 'cw15',
  'cwd mt+ arg7': 'cw15',
  'cell-wall-deficient': 'cw15',
  elow47: 'uvm4',
  uvm4: 'uvm4',
  uvm11: 'uvm4',
  'cc-137c': 'creinhardtii-wt',
  '137c': 'creinhardtii-wt',
  cc124: 'creinhardtii-wt',
  cc1690: 'creinhardtii-wt',
  wt12: 'creinhardtii-wt',
  gs115: 'gs115',
  'k. phaffii': 'gs115',
  'p. pastoris': 'gs115',
  'komagataella phaffii': 'gs115',
  'pichia pastoris': 'gs115',
  treesei: 'treesei',
  't. reesei': 'treesei',
  'trichoderma reesei': 'treesei',
  ecoli: 'ecoli',
  'e. coli': 'ecoli',
  bl21: 'ecoli',
  bovine: 'bovine',
  'bos taurus': 'bovine',
};

/** Normalise a strain name found in prose to a canonical id, or null. */
export function normalizeStrain(raw: string): string | null {
  return STRAIN_ALIASES[raw.trim().toLowerCase()] ?? null;
}


export const STRAINS_BY_ID: Record<string, Strain> = Object.fromEntries(
  STRAINS.map((s) => [s.id, s]),
);
