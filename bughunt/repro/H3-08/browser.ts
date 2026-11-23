// H3-08's browser half: src/engine/units.ts normalizeUnit and convert on the same spellings.
// Run from the repository root: node_modules/.bin/tsx bughunt/repro/H3-08/browser.ts
const { normalizeUnit, convert } = await import('../../../src/engine/units');
const controls = ['g EtOH/g glucose', 'gx/g', 'gal', 'gmol', 'g/furlong'];
const probes = ['g/gal', 'gal/g', 'g/gmol', 'gmol/g', 'g gal-1', 'gal g-1', 'g/gallon', 'gpm/gpm', 'g/gpm'];
for (const s of controls) console.log(`BROWSER control normalizeUnit(${JSON.stringify(s)}) = ${JSON.stringify(normalizeUnit(s))}`);
let misread = 0;
for (const s of probes) {
  const n = normalizeUnit(s);
  if (n === 'g g⁻¹') misread++;
  console.log(`BROWSER probe   normalizeUnit(${JSON.stringify(s)}) = ${JSON.stringify(n)}`);
}
for (const [v, a, b] of [[180.16, 'g/gmol', 'g g⁻¹'], [1, 'gal/g', 'kg kg⁻¹']] as const) {
  try { console.log(`BROWSER convert(${v}, ${JSON.stringify(a)}, ${JSON.stringify(b)}) = ${convert(v, a, b)}`); }
  catch (e) { console.log(`BROWSER convert(${v}, ${JSON.stringify(a)}, ${JSON.stringify(b)}) throws ${(e as Error).message}`); }
}
console.log(`BROWSER_MISREAD ${misread} of ${probes.length}`);
