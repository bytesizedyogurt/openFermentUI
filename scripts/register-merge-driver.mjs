/**
 * Teach this clone to merge core/data/biorepo.json by record (OF-BLD-012 §B.8).
 *
 * Runs as `prepare`, so every `pnpm install` on every clone does it, the
 * laptop as much as the Mini. .gitattributes names the driver; without this
 * the name means nothing to git, it falls back to a text merge, and two
 * machines' decisions collide as conflict markers in the file the service
 * reads. scripts/host/lib.sh registers the same driver for deploys.
 *
 * Never fails an install: outside a git checkout, or with no git, it says so
 * and stops.
 */
import { execFileSync } from 'node:child_process';

const git = (...args) => execFileSync('git', args, { stdio: ['ignore', 'pipe', 'ignore'] });

try {
  git('rev-parse', '--git-dir');
  git('config', 'merge.biorepo.name', 'BioRepo decisions, merged by record');
  // scripts/host/merge-biorepo picks the Python at merge time.
  git('config', 'merge.biorepo.driver', 'sh scripts/host/merge-biorepo %O %A %B');
} catch {
  console.log('register-merge-driver: not a git checkout, nothing to register');
}
