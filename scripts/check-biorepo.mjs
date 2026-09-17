/**
 * BioRepo guard (OF-BLD-012 §7.4).
 *
 * core/data/biorepo.json is the one data file this increment commits: the
 * reviewers' decisions and the quotes that anchor them. `biorepo.write` is
 * the only thing that should ever change it, and this check is what makes
 * that a fact rather than a convention — a hand edit, a merge that went
 * wrong, or a decision about a record that no longer exists fails the build
 * here, in words.
 *
 * Checked against the corpus projection, which is where the seed's record ids
 * and paper identifiers are readable. THE GUARD BRINGS ITS OWN EXPORT
 * (OF-BLD-012.1 F5): it runs `export-corpus.ts` into a temp directory and
 * compares against that, so it says the same thing on a fresh clone with no
 * corpus.json as it does mid-verify, and can never report a decision as
 * unmerged when the truth is that the projection on disk is older than the
 * file. Because the export MERGES biorepo.json (§7.4), the last block checks
 * that the merge happened: a decision the corpus does not reflect is a
 * decision Postdoc will not honour.
 *
 * `OPENFERMENT_DATA_DIR` selects which biorepo.json is checked, the same
 * override the service and the exporter read, so `test:export` can point this
 * at a fixture whose merge has been broken on purpose.
 *
 * `OPENFERMENT_CORPUS_IN` names a projection to check AGAINST instead of
 * making one. Nothing in `verify` sets it; `test:export` does, because rule 4
 * asks whether a corpus reflects a decision, and a guard that always builds
 * the corpus it is about to check can only ever answer yes to that. Pointed
 * at a corpus built before the decision changed, rule 4 has something to
 * catch — which is the only way to know it still would.
 */
import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { isAbsolute, join } from 'node:path';

const DATA_DIR = process.env.OPENFERMENT_DATA_DIR?.trim() || 'core/data';
const BIOREPO = join(isAbsolute(DATA_DIR) ? DATA_DIR : join(process.cwd(), DATA_DIR), 'biorepo.json');

const errors = [];
const fail = (m) => errors.push(m);

if (!existsSync(BIOREPO)) {
  console.error(`✗ ${BIOREPO} is missing — it is committed, so this checkout is broken`);
  process.exit(1);
}

// The projection this file is checked against: one named for us, or one
// made now from this file.
const given = process.env.OPENFERMENT_CORPUS_IN?.trim();
let CORPUS = given || '';
if (!given) {
  CORPUS = join(mkdtempSync(join(tmpdir(), 'of-biorepo-')), 'corpus.json');
  const ran = spawnSync('pnpm', ['export:corpus'], {
    encoding: 'utf-8',
    shell: process.platform === 'win32',
    env: { ...process.env, OPENFERMENT_DATA_DIR: DATA_DIR, OPENFERMENT_CORPUS_OUT: CORPUS },
  });
  if (ran.status !== 0 || !existsSync(CORPUS)) {
    console.error(ran.stderr || ran.stdout);
    console.error('✗ the corpus export did not run — this guard cannot check a merge it cannot make');
    process.exit(1);
  }
} else if (!existsSync(CORPUS)) {
  console.error(`✗ OPENFERMENT_CORPUS_IN points at ${CORPUS}, which does not exist`);
  process.exit(1);
}

const repo = JSON.parse(readFileSync(BIOREPO, 'utf8'));
const corpus = JSON.parse(readFileSync(CORPUS, 'utf8'));

// ── shape ──────────────────────────────────────────────────────────────
if (repo.version !== 1) fail(`version is ${JSON.stringify(repo.version)}, expected 1`);
if (!repo.decisions || typeof repo.decisions !== 'object' || Array.isArray(repo.decisions)) {
  fail('decisions is not an object keyed by recordId');
}
if (!Array.isArray(repo.records)) fail('records is not an array');
const decisions = repo.decisions && typeof repo.decisions === 'object' ? repo.decisions : {};
const copies = new Map((Array.isArray(repo.records) ? repo.records : []).map((c) => [c.id, c]));

const seed = new Map(corpus.records.filter((r) => r.source === 'seed').map((r) => [r.id, r]));
const exported = new Map(corpus.records.map((r) => [r.id, r]));
const papers = new Map(corpus.papers.map((p) => [p.id, p]));

const STATUSES = new Set(['unverified', 'verified', 'rejected']);

// ── every decision ─────────────────────────────────────────────────────
for (const [id, d] of Object.entries(decisions)) {
  if (d.recordId !== id) fail(`decision ${id} is keyed under a different recordId (${d.recordId})`);
  if (!STATUSES.has(d.status)) fail(`decision ${id} has status ${JSON.stringify(d.status)}`);
  if (!(d.reviewer ?? '').trim()) fail(`decision ${id} has no reviewer`);

  // 1. every recordId resolves — to the seed, or to a candidate the file
  //    itself keeps a copy of.
  const rec = seed.get(id) ?? copies.get(id);
  if (!rec) {
    fail(`decision ${id} resolves to nothing — not a seed record, not a candidate in records[]`);
    continue;
  }

  // 2. every gold decision has a quote.
  const gold = d.provenance === 'gold' || d.gold != null;
  if (gold && !(d.quote ?? '').trim()) fail(`gold decision ${id} has no quote`);

  // 3. no decision names a paper without an identifier.
  const paper = papers.get(rec.paperId);
  if (!paper) fail(`decision ${id} names ${rec.paperId}, which is not in the corpus`);
  else if (!paper.pmcid && !paper.doi && !paper.pmid) {
    fail(`decision ${id} names ${rec.paperId}, a paper with no PMCID, DOI or PMID`);
  }

  // 4. the export reflects the decision (§7.4).
  const out = exported.get(id);
  if (d.status === 'verified' && !out) fail(`${id} is verified in biorepo.json and absent from corpus.json`);
  if (out && out.status !== d.status) {
    fail(`corpus.json has ${id} as ${out.status}; biorepo.json says ${d.status} — the export did not merge`);
  }
  if (out && d.quote && out.quote !== d.quote) fail(`corpus.json did not take the re-anchored quote for ${id}`);
  if (out && d.corrected && (out.value !== d.corrected.value || out.unit !== d.corrected.unit)) {
    fail(`corpus.json has ${id} as ${out.value} ${out.unit}; the decision corrected it to ${d.corrected.value} ${d.corrected.unit}`);
  }
}

// ── every copied candidate ─────────────────────────────────────────────
for (const c of copies.values()) {
  if (!decisions[c.id]) fail(`records[] holds ${c.id} with no decision about it`);
  if (seed.has(c.id)) fail(`records[] holds ${c.id}, which is a seed record, not a candidate`);
  if (c.extractorRun !== 'haiku-1') fail(`records[] holds ${c.id} from run ${JSON.stringify(c.extractorRun)}`);
}

// ── report ─────────────────────────────────────────────────────────────
const list = Object.values(decisions);
console.log('\nopenFerment BioRepo check');
console.log('─────────────────────────');
console.log(`  decisions   ${list.length} (${list.filter((d) => d.status === 'verified').length} verified, ${list.filter((d) => d.status === 'rejected').length} rejected, ${list.filter((d) => d.provenance === 'gold' || d.gold != null).length} gold)`);
console.log(`  candidates  ${copies.size} kept beside their decisions; ${corpus.records.filter((r) => r.source === 'biorepo').length} appended to the corpus as accepted new records`);
console.log(`  resolved    against ${seed.size} seed records and ${papers.size} papers`);

if (errors.length) {
  console.error(`\n✗ ${errors.length} error(s):`);
  for (const e of errors.slice(0, 40)) console.error(`  - ${e}`);
  if (errors.length > 40) console.error(`  … and ${errors.length - 40} more`);
  process.exit(1);
}
console.log('\n✓ biorepo.json is sound and the corpus reflects it.\n');
