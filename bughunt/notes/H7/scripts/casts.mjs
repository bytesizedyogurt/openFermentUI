// H7: list every `as` cast (other than `as const`) and every non-null `!` in src/, by parsing each file with the
// repository's TypeScript. One line a node: file:line, the kind, the cast's text.
//   node casts.mjs > casts.txt
import ts from 'typescript';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const ROOT = '/home/user/openFermentUI';
const files = [];
(function walk(d) {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(ts|tsx)$/.test(n) && !n.endsWith('types.gen.ts')) files.push(p);
  }
})(join(ROOT, 'src'));

let counts = { as: 0, nonNull: 0 };
for (const f of files) {
  const text = readFileSync(f, 'utf8');
  const sf = ts.createSourceFile(f, text, ts.ScriptTarget.Latest, true, f.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const visit = (node) => {
    if (ts.isAsExpression(node) || ts.isTypeAssertionExpression(node)) {
      const t = node.type.getText(sf);
      if (t !== 'const') {
        counts.as++;
        const { line } = sf.getLineAndCharacterOfPosition(node.getStart(sf));
        console.log(`${relative(ROOT, f)}:${line + 1}\tas\t${t.replace(/\s+/g, ' ').slice(0, 80)}\t${node.expression.getText(sf).replace(/\s+/g, ' ').slice(0, 100)}`);
      }
    }
    if (ts.isNonNullExpression(node)) {
      counts.nonNull++;
      const { line } = sf.getLineAndCharacterOfPosition(node.getStart(sf));
      console.log(`${relative(ROOT, f)}:${line + 1}\t!\t\t${node.getText(sf).replace(/\s+/g, ' ').slice(0, 100)}`);
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
}
console.error(JSON.stringify(counts));
