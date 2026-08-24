/**
 * Secret containment (OF-BLD-007 §11).
 *
 * The first stage of `pnpm verify`, because everything after it is worthless if
 * a key has already leaked. Three separate things can go wrong and this checks
 * all three rather than trusting one:
 *
 *   1. The gitignore rule stops matching. A rule that silently stops matching
 *      is worse than no rule, because nobody re-reads a file they believe is
 *      handled. Asked of git itself, not by string-matching .gitignore.
 *   2. A key reaches the browser. Anything under src/ ships to the client, so
 *      src/ must never name ANTHROPIC_API_KEY and must never read a .env. The
 *      whole reason the service is a service is that the key stays server-side.
 *   3. A key is committed anywhere. Scans every tracked file for the key
 *      prefix — a leaked key in a test fixture is as leaked as one in main.
 *
 * Runs offline, needs no key, and passes whether or not core/.env exists.
 */
import { execFileSync } from 'node:child_process';
import { readFileSync, existsSync } from 'node:fs';

const errors = [];
const fail = (m) => errors.push(m);

const git = (args) => {
  try {
    return execFileSync('git', args, { encoding: 'utf8' });
  } catch (e) {
    // check-ignore exits 1 when nothing matches; that is a result, not a crash.
    return e.stdout ?? '';
  }
};

// ── 1. the gitignore rules hold ────────────────────────────────────────
// Asked of git rather than read out of .gitignore, so a rule that is present
// but shadowed by a later negation still fails here.
const MUST_IGNORE = ['core/.env', 'core/.env.local', 'core/.env.production'];
for (const path of MUST_IGNORE) {
  if (!git(['check-ignore', path]).trim()) {
    fail(`${path} is NOT gitignored — the key would be committable`);
  }
}
// The example file is the one thing in that family that must stay committable,
// or the next person has nothing to copy.
if (git(['check-ignore', 'core/.env.example']).trim()) {
  fail('core/.env.example IS gitignored — it is the template and must be committed');
}

// ── 2. nothing under src/ knows about the key ──────────────────────────
// src/ is the browser bundle. There is no safe way for it to hold a key, so
// the rule is absence rather than care.
const tracked = git(['ls-files', 'src']).split('\n').filter(Boolean);
const BROWSER_FORBIDDEN = [
  { re: /ANTHROPIC_API_KEY/, why: 'names the API key variable' },
  { re: /sk-ant-[A-Za-z0-9_-]{4}/, why: 'contains something shaped like a key' },
  { re: /\bapi[_-]?key\s*[:=]\s*['"][^'"]{8,}/i, why: 'assigns a literal-looking key' },
  { re: /from\s+['"]dotenv['"]|require\(['"]dotenv['"]\)/, why: 'loads a .env file' },
  { re: /api\.anthropic\.com/, why: 'calls the Anthropic API directly from the browser' },
];
for (const file of tracked) {
  if (!existsSync(file)) continue;
  const text = readFileSync(file, 'utf8');
  for (const { re, why } of BROWSER_FORBIDDEN) {
    if (re.test(text)) fail(`${file} ${why} — src/ ships to the browser`);
  }
}

// ── 3. no key in any tracked file, anywhere ────────────────────────────
// `git grep` searches the working tree but only files git knows about, which
// is exactly the set that can leave this machine.
const leaked = git(['grep', '-l', '-E', 'sk-ant-[A-Za-z0-9_-]{16}', '--', '.'])
  .split('\n')
  .filter(Boolean);
for (const file of leaked) fail(`${file} contains a live-looking API key`);

// A key pasted into a committed env file is the classic version of this.
for (const f of git(['ls-files']).split('\n').filter(Boolean)) {
  if (/(^|\/)\.env(\.|$)/.test(f) && !f.endsWith('.example')) {
    fail(`${f} is tracked — env files other than .example must never be committed`);
  }
}

console.log('\nopenFerment secret check');
console.log('────────────────────────');
console.log(`  ignore rules      ${MUST_IGNORE.length} env paths ignored, .env.example kept`);
console.log(`  browser surface   ${tracked.length} tracked files under src/ scanned, none name a key`);
console.log(`  tracked files     no key-shaped string in any file git tracks`);
console.log(
  `  core/.env         ${existsSync('core/.env') ? 'present locally and ignored' : 'absent — the service will refuse to start rather than guess'}`,
);

if (errors.length) {
  console.error(`\n✗ ${errors.length} error(s):`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}
console.log('\n✓ No secret can reach the browser or a commit.');
