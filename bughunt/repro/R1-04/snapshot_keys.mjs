// R1-04: what the browser's Durable snapshot writes, read from the source with the TypeScript compiler's parser.
// usage: node snapshot_keys.mjs <store.ts> <durable.ts>   (copies of src/store.ts and src/lib/durable.ts at a commit)
// Prints one line per finding:
//   WRITES <key>          a key of the object snapshotOf (src/store.ts) returns, nested keys as guild.actingId,
//                         keys of the pre-2.0 rows' conditional spread marked [legacy rows]
//   FIELD <name> <LEGACY|kept>  a member of the DurableSnapshot interface (src/lib/durable.ts), LEGACY when its
//                         doc comment opens with LEGACY
//   DOC learnProgress <text>  the doc comment of the learnProgress member
import { createRequire } from 'node:module';
import { readFileSync } from 'node:fs';
const require = createRequire('/home/user/openFermentUI/package.json');
const ts = require('typescript');

const [storePath, durablePath] = process.argv.slice(2);
const parse = (p) => ts.createSourceFile(p, readFileSync(p, 'utf8'), ts.ScriptTarget.Latest, true);
const store = parse(storePath);
const durable = parse(durablePath);

function find(node, pred) {
  let hit = null;
  const walk = (n) => { if (hit) return; if (pred(n)) { hit = n; return; } ts.forEachChild(n, walk); };
  walk(node);
  return hit;
}
const nameOf = (n) => (n.name && (ts.isIdentifier(n.name) || ts.isStringLiteral(n.name)) ? n.name.text : '?');

const empty = find(durable, (n) => ts.isVariableDeclaration(n) && nameOf(n) === 'EMPTY_SNAPSHOT');
function keys(obj, prefix, mark, out) {
  for (const p of obj.properties) {
    if (ts.isPropertyAssignment(p) || ts.isShorthandPropertyAssignment(p)) {
      const k = prefix + nameOf(p);
      out.push(k + mark);
      if (ts.isPropertyAssignment(p) && ts.isObjectLiteralExpression(p.initializer)) keys(p.initializer, k + '.', mark, out);
    } else if (ts.isSpreadAssignment(p)) {
      let e = p.expression;
      while (ts.isParenthesizedExpression(e)) e = e.expression;
      if (ts.isIdentifier(e) && e.text === 'EMPTY_SNAPSHOT' && empty && ts.isObjectLiteralExpression(empty.initializer)) {
        keys(empty.initializer, prefix, mark, out);
      } else if (ts.isConditionalExpression(e)) {
        for (const b of [e.whenTrue, e.whenFalse]) if (ts.isObjectLiteralExpression(b)) keys(b, prefix, ' [legacy rows]', out);
      } else {
        out.push(prefix + '(spread of ' + e.getText() + ')' + mark);
      }
    }
  }
}
const fn = find(store, (n) => ts.isFunctionDeclaration(n) && n.name && n.name.text === 'snapshotOf');
if (!fn) { console.log('NOFUNCTION snapshotOf'); process.exit(0); }
const ret = find(fn.body, (n) => ts.isReturnStatement(n) && n.expression && ts.isObjectLiteralExpression(n.expression));
const out = [];
if (ret) keys(ret.expression, '', '', out);
for (const k of [...new Set(out)]) console.log('WRITES ' + k);

const iface = find(durable, (n) => ts.isInterfaceDeclaration(n) && n.name.text === 'DurableSnapshot');
for (const m of iface ? iface.members : []) {
  const doc = (ts.getJSDocCommentsAndTags(m)[0]?.getText() ?? '').replace(/^\/\*\*|\*\/$/g, '').replace(/\n\s*\*\s?/g, ' ').replace(/\s+/g, ' ').trim();
  console.log(`FIELD ${nameOf(m)} ${doc.startsWith('LEGACY') ? 'LEGACY' : 'kept'}`);
  if (nameOf(m) === 'learnProgress') console.log('DOC learnProgress ' + doc);
}
