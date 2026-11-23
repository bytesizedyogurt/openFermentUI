// How the bench's capture box files a decimal comma and a thousands separator (src/engine/capture.ts matchToSchema).
//   npx tsx capture_comma.ts   (from the repository root's node_modules)
import { matchToSchema } from '../../../../src/engine/capture';
const schema = [{ id: 'm1', label: 'Titre at harvest', unit: 'g/L', timepoint: 'harvest' }] as never;
for (const raw of ['titre came in at 7.4 g/L', 'titre came in at 7,4 g/L', 'titre came in at 1,250 g/L', 'titre 7.4 g/L, 48 h']) {
  console.log(JSON.stringify(raw), '->', JSON.stringify(matchToSchema(raw, schema)));
}
