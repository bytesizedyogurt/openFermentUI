// openFerment corpus — Thread Q: ethanol from glucose by wild-type Saccharomyces
// cerevisiae, program three.
//
// THE PAPER LIST IS WRITTEN BY A SCRIPT. `pnpm thread:apply:q` writes
// THREAD_Q_PAPERS from the rows of `core/data/thread-q-proposed.tsv` that a
// named person approved, and from the sources `docs/thread-q-include.txt`
// names, filled from the metadata Europe PMC, OSTI or the Saccharomyces Genome
// Database returned and from nothing else. Do not edit the list by hand.
//
// THE RECORD LIST IS EMPTY BY DESIGN. No curator reads these papers. Every
// number about a thread Q paper arrives through Intake — fetched full text,
// an anchored extraction candidate — and a Guild decision. A record typed
// here would be a quantity that bypassed both.
import type { ExtractionRecord, Paper } from '../types';

export const THREAD_Q_PAPERS: Paper[] = [];

export const THREAD_Q_RECORDS: ExtractionRecord[] = [];
