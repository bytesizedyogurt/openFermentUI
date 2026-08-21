// The demo pool's "nothing under that id" path.
//
// Nine demo screens early-returned a bare `<EmptyState>` — no wrapper, and
// crucially no `<DemoFooter/>`. That footer carries `SEED_DISCLAIMER`, the
// sentence saying the patent numbers and citation identifiers on these screens
// are synthetic, and `check:demo-seed` exists in part to guarantee it is
// reachable. It was reachable on every path but the ones a reader hits by
// following a stale link — which is exactly when they are most likely to be
// looking at an id and wondering whether it is real.
//
// So the disclaimer is not optional on an error path. It is the error path
// that most needs it.
import { EmptyState } from '@/components/ui';
import { DemoFooter } from './DemoFooter';

export function DemoEmpty({ title, body }: { title: string; body: string }) {
  return (
    <>
      <EmptyState title={title} body={body} />
      <DemoFooter />
    </>
  );
}
