// H3-07's browser half: src/engine/units.ts on the same spellings, and the Primer's grading call
// (src/screens/PrimerLesson.tsx:51-54: parseQuantity, then quantityEquals against the lesson's answer).
// Run from the repository root: node_modules/.bin/tsx bughunt/repro/H3-07/browser.ts
const { normalizeUnit, convert, parseQuantity, quantityEquals } = await import('../../../src/engine/units');
const probes = ['Mg', 'MG', 'ML', 'Mm', 'MM', 'S', 'G'];
let folded = 0;
for (const s of ['Mg/d', 'G L-1', 'KDa']) console.log(`BROWSER control normalizeUnit(${JSON.stringify(s)}) = ${JSON.stringify(normalizeUnit(s))}`);
for (const s of probes) {
  const n = normalizeUnit(s);
  if (n !== null) folded++;
  console.log(`BROWSER probe   normalizeUnit(${JSON.stringify(s)}) = ${JSON.stringify(n)}`);
}
for (const [v, a, b] of [[1, 'Mg', 'kg'], [1, 'ML', 'L']] as const) {
  try { console.log(`BROWSER convert(${v}, ${JSON.stringify(a)}, ${JSON.stringify(b)}) = ${convert(v, a, b)}`); }
  catch (e) { console.log(`BROWSER convert(${v}, ${JSON.stringify(a)}, ${JSON.stringify(b)}) throws ${(e as Error).message}`); }
}
const answer = { value: 2, unit: 'Mg', tolerancePct: 5 };
for (const typed of ['2000 kg', '2 mg']) {
  const parsed = parseQuantity(typed);
  const ok = parsed ? quantityEquals(parsed, answer, answer.tolerancePct) : false;
  console.log(`BROWSER Primer grade: a learner types ${JSON.stringify(typed)} against the answer 2 Mg -> ${ok ? 'correct' : 'wrong'}`);
}
console.log(`BROWSER_FOLDED ${folded} of ${probes.length}`);
