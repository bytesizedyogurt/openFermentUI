// H3-16: the browser's normalizeUnit (src/engine/units.ts) on the same spellings, read only.
import { normalizeUnit } from '../../../src/engine/units.ts';
for (const tail of ['g/mL', 'L', 'M']) {
  const a = 'µ' + tail, b = 'μ' + tail;
  console.log(`  browser normalizeUnit: micro sign ${JSON.stringify(a)} -> ${JSON.stringify(normalizeUnit(a))}   Greek mu ${JSON.stringify(b)} -> ${JSON.stringify(normalizeUnit(b))}`);
}
