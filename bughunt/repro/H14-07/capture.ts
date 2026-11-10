// H14-07: the bench's capture matcher over the tree's own src/engine/capture.ts, read-only.
// The schema is the one a runbook made from a run carries (studies/runbooks.py:136): a labelled measure in g/L
// at harvest. Each line is what an operator types into the Deposition capture box; the output is what the box
// previews ("files as ... = ...") and what captureDeposition files as the entry's value (store.ts:2136).
//   node_modules/.bin/tsx bughunt/repro/H14-07/capture.ts
import { matchToSchema, readBackText } from '../../../src/engine/capture';

const schema = [
  { id: 'm1', label: 'Ethanol titre', unit: 'g/L', timepoint: 'harvest', predictionId: 'p1' },
] as Parameters<typeof matchToSchema>[1];

const lines = [
  'titre came in at 7.4 g/L',
  'titre came in at 7,4 g/L',
  'titre came in at 0,74 g/L',
  'titre came in at 1,250 g/L',
];
for (const raw of lines) {
  const m = matchToSchema(raw, schema);
  console.log(JSON.stringify({ raw, match: m, readBack: m ? readBackText(m) : null }));
}
