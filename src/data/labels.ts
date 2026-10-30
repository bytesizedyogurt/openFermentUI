// Labels and orders the screens read: words for an enum, never a value.
// alpha 2.0 kept these when it deleted the seed files they lived in
// (src/data/products.ts and runbooks.ts at tag alpha-1.0; ADR-010).
import type { ProductCategory, RunbookStatus } from './types';

export const PRODUCT_CATEGORY_LABEL: Record<ProductCategory, string> = {
  molecular_biology_enzyme: 'Molecular biology enzyme',
  diagnostic: 'Diagnostic antigen',
  research_protein: 'Research protein',
  food_protein: 'Food protein',
  hmo: 'Human milk oligosaccharide',
  sweet_protein: 'Sweet protein',
  structural_protein: 'Structural protein',
  terpene: 'Terpene',
  glycoside: 'Glycoside',
  industrial_enzyme: 'Industrial enzyme',
  therapeutic_protein: 'Therapeutic protein',
};

export const RUNBOOK_STATUS_ORDER: RunbookStatus[] = [
  'running',
  'blocked_unverified',
  'needs_review',
  'awaiting_budget',
  'complete',
  'cache_hit',
  'draft',
];

export const RUNBOOK_STATUS_LABEL: Record<RunbookStatus, string> = {
  running: 'Running',
  blocked_unverified: 'Blocked · unverified input',
  needs_review: 'Held for review',
  awaiting_budget: 'Awaiting budget',
  complete: 'Complete',
  cache_hit: 'Resolved from cache',
  draft: 'Draft',
};

/** One line saying what the state means, shown under each board column. */
export const RUNBOOK_STATUS_NOTE: Record<RunbookStatus, string> = {
  running: 'Compute is in flight. Stages fill in as they resolve.',
  blocked_unverified:
    'A stage tried to consume a value with no source. Attach one, or mark the value an explicit assumption, and the cascade continues.',
  needs_review: 'A person, not a model, should rule on what this found.',
  awaiting_budget: 'Priced but not authorised. Nothing runs until someone says yes.',
  complete: 'Every stage resolved. The outputs are the deliverable.',
  cache_hit: 'Resolved from prior artifacts in BioRepo at near-zero cost.',
  draft: 'Scoped but not started.',
};
