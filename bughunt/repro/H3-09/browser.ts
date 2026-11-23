// H3-09's browser half: src/engine/units.ts convert, explainRefusal and quantityEquals on the same pairs.
// Run from the repository root: node_modules/.bin/tsx bughunt/repro/H3-09/browser.ts
const { convert, explainRefusal, quantityEquals } = await import('../../../src/engine/units');
try {
  console.log(`BROWSER control convert(5, "% TSP", "% DW") = ${convert(5, '% TSP', '% DW')}`);
} catch (e) {
  console.log(`BROWSER control convert(5, "% TSP", "% DW") throws; explainRefusal = ${JSON.stringify(explainRefusal('% TSP', '% DW'))}`);
}
const pairs: [string, string][] = [
  ['% DW', '% of native sites'], ['% v/v', '% DW'], ['% DW', '% of total protein'],
  ['% of native sites', '% of total protein'], ['% sedimentable', '% v/v'], ['% v/v', '% of total expressed'],
];
let converted = 0;
for (const [a, b] of pairs) {
  try {
    const out = convert(5, a, b);
    converted++;
    console.log(`BROWSER probe   convert(5, ${JSON.stringify(a)}, ${JSON.stringify(b)}) = ${out}; explainRefusal = ${JSON.stringify(explainRefusal(a, b))}`);
  } catch (e) {
    console.log(`BROWSER probe   convert(5, ${JSON.stringify(a)}, ${JSON.stringify(b)}) throws ${(e as Error).message}`);
  }
}
console.log(`BROWSER probe   quantityEquals({5, "% DW"}, {5, "% of native sites"}) = ${quantityEquals({ value: 5, unit: '% DW' }, { value: 5, unit: '% of native sites' })}`);
console.log(`BROWSER_CONVERTED ${converted} of ${pairs.length}`);
