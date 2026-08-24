/**
 * Capture matching (OF-BLD-006 §4.3).
 *
 * The asymmetry is the whole design: a false negative costs a person one
 * reclassification, a false positive silently writes a number into a slot it
 * does not belong in and the reconciliation is quietly wrong. So the cases
 * below are half positives and half things that must NOT match.
 *
 * Two of them are here because the first implementation got them wrong:
 * "OD600 of 82" read as 600 (the unit token contains its own digits), and
 * "nothing in the logs" read as 3 grams (the single-letter alias "g" matched
 * inside a word). Both are regressions worth failing a build over.
 *
 *   pnpm check:capture
 */
import { matchToSchema } from '../src/engine/capture';
import { RUNBOOKS } from '../src/data/runbooks';
const taq = RUNBOOKS.find(r => r.id === 'rb-taq-kigali')!;
const S = taq.measurementSchema;
console.log('schema:', S.map(m => `${m.id}(${m.label}/${m.unit})`).join('  '));
const cases: [string, string | null][] = [
  ['titre came in at 7.4 g/L', 'ms-taq-titre'],
  ['harvest titre 7.4 grams per litre', 'ms-taq-titre'],
  ['OD600 of 82 at harvest', 'ms-taq-od'],
  ['overall recovery 58 percent', 'ms-taq-recovery'],
  ['endotoxin 3 EU/mg', 'ms-taq-endo'],
  ['specific activity 190000 U/mg', 'ms-taq-act'],
  ['residual host DNA 8 pg/U', 'ms-taq-dna'],
  ['it came out at about four', null],
  ['the foam was worse than usual on the second impeller', null],
  ['smelled off around 3am, nothing in the logs', null],
  ['purified mass 412 g', 'ms-taq-mass'],
];
let bad = 0;
for (const [raw, want] of cases) {
  const got = matchToSchema(raw, S);
  const id = got?.measureId ?? null;
  const ok = id === want;
  if (!ok) bad++;
  console.log(`${ok ? '✓' : '✗'} ${JSON.stringify(raw).padEnd(56)} -> ${id ?? '(observation)'}${got ? ` = ${got.value} ${got.unit}` : ''}${ok ? '' : `   WANT ${want ?? '(observation)'}`}`);
}
console.log(bad === 0 ? '\nCAPTURE MATCHING OK' : `\n${bad} wrong`);
process.exit(bad === 0 ? 0 : 1);
