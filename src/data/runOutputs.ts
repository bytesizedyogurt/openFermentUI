// Extractor runs in the SEED (OF-DES-001 §8.8, OF-BLD-012 §6.4).
//
// EMPTY, AND IT STAYS EMPTY.
//
// The synthetic corpus once shipped three seeded extractor runs with authored
// confusion data. The real corpus never did: no extractor had read these
// papers, so there was nothing to score, and the validation screen showed an
// honest empty state instead of a fabricated F1.
//
// Now one has. OF-BLD-012 §6 fetches the open-access papers' full text, runs
// Claude Opus 5.5 once per paper for one structured response (Sonnet 5.5 where
// Opus declines), anchors every candidate
// to a verbatim quote, and scores the run against the curated records
// (`match_run`, core/openferment_core/witness.py). That run — `claude-1` — does
// NOT land in this file. It arrives through the service's overlay,
// `GET /api/biorepo/overlay` → `overlay.runs`, recomputed from
// core/data/candidates/ on every request, and the store merges it into
// `runOutputs` at load. Witness scores it live, in provisional mode until a
// reviewer flags real gold in Guild.
//
// So this array is what the app has with the service down, and it is empty
// because a run is a measurement and a measurement is not seed data. With the
// service up, Witness shows the run that ran.
import type { RunOutput } from './types';

export const RUN_OUTPUTS: RunOutput[] = [];
