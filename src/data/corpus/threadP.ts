// openFerment corpus — Thread P: PHA from waste cellulosic sugars, program two
// (OF-BLD-014 Phase 2).
//
// THE PAPER LIST IS WRITTEN BY A SCRIPT. `pnpm thread:apply` (OF-BLD-014 §2.3)
// writes THREAD_P_PAPERS from the rows of `core/data/thread-p-proposed.tsv`
// that a named person approved, filled from Europe PMC's metadata and from
// nothing else. Do not edit the list by hand.
//
// THE RECORD LIST IS EMPTY BY DESIGN. No curator reads these papers. Every
// number about a thread P paper arrives through Intake — fetched full text,
// an anchored extraction candidate — and a Guild decision. A record typed
// here would be a quantity that bypassed both.
import type { ExtractionRecord, Paper } from '../types';

export const THREAD_P_PAPERS: Paper[] = [];

export const THREAD_P_RECORDS: ExtractionRecord[] = [];
