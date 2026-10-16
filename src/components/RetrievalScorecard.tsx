// Witness → Retrieval (OF-BLD-014 §4.4): every search lane scored on the same
// questions, the lane in use marked. Read from the service's last
// `pnpm rag:eval`; with none, it says so and names the command.
import { useEffect, useState } from 'react';
import type { RagReport } from '@/data/types';
import { RagDown, RagRefused, ragReport, ragStatus } from '@/lib/rag';
import { Callout, Card, SectionTitle, cx } from '@/components/ui';

const METRICS: { key: 'recall5' | 'recall10' | 'recall20' | 'mrr10' | 'ndcg10'; label: string }[] = [
  { key: 'recall5', label: 'R@5' },
  { key: 'recall10', label: 'R@10' },
  { key: 'recall20', label: 'R@20' },
  { key: 'mrr10', label: 'MRR@10' },
  { key: 'ndcg10', label: 'nDCG@10' },
];

export function RetrievalScorecard() {
  const [report, setReport] = useState<RagReport | null>(null);
  const [said, setSaid] = useState<string | null>(null);
  const [indexHash, setIndexHash] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    ragStatus(ctrl.signal).then((s) => setIndexHash(s.manifestHash), () => undefined);
    ragReport(ctrl.signal).then(setReport, (e: unknown) => {
      if (ctrl.signal.aborted) return;
      if (e instanceof RagRefused) setSaid(e.message);
      else if (e instanceof RagDown) setSaid(`${e.message} The scorecard is kept by the service. ${e.remedy}`);
      else setSaid(String(e));
    });
    return () => ctrl.abort();
  }, []);

  return (
    <section className="mt-8" aria-labelledby="retrieval-heading" data-testid="retrieval-scorecard">
      <SectionTitle>
        <span id="retrieval-heading">Retrieval</span>
      </SectionTitle>
      <p className="text-body text-ink-soft mb-3 max-w-3xl">
        How often each way of searching the papers&rsquo; own words put a relevant passage near the top,
        measured on the same questions. K is built from records whose quote sits in the text, S is
        written by a model from sampled passages, F is the authored flows.
      </p>
      {said && <Callout kind="info">{said}</Callout>}
      {report && (
        <>
          <p className="text-caption text-ink-soft mb-2">
            Scored {report.date.slice(0, 10)} over {report.passages.toLocaleString()} passages from{' '}
            {report.papersIndexed} papers · in use: <strong>{report.chosenLane}</strong> ·{' '}
            {report.sets.map((s) => `${s.name}: ${s.note}`).join(' · ')}
          </p>
          {indexHash && indexHash !== report.manifestHash && (
            <div className="mb-2">
              <Callout kind="warn">
                These scores were measured on an earlier cut of the papers&rsquo; text than the index the
                service holds now. Run pnpm rag:eval to score the current one.
              </Callout>
            </div>
          )}
          <Card className="overflow-x-auto">
            <table className="w-full border-collapse text-body" data-testid="retrieval-table">
              <thead>
                <tr className="border-b border-line text-caption text-ink-soft">
                  <th className="text-left font-medium px-3 py-2">Lane</th>
                  <th className="text-left font-medium px-3 py-2">Set</th>
                  <th className="text-right font-medium px-3 py-2">n</th>
                  {METRICS.map((m) => (
                    <th key={m.key} className="text-right font-medium px-3 py-2">
                      {m.label}
                    </th>
                  ))}
                  <th className="text-right font-medium px-3 py-2">$ / question</th>
                </tr>
              </thead>
              <tbody>
                {report.lanes.map((l) =>
                  !l.available || Object.keys(l.sets).length === 0 ? (
                    <tr key={l.lane} className="border-b border-line last:border-0 text-ink-soft">
                      <td className="px-3 py-2 font-mono">{l.lane}</td>
                      <td className="px-3 py-2" colSpan={METRICS.length + 3}>
                        not scored: {l.why ?? ((l.refused ?? 0) > 0 ? `the helper model declined all ${l.refused} questions` : 'no question set to score it on')}
                      </td>
                    </tr>
                  ) : (
                    Object.entries(l.sets).map(([set, m], i) => (
                      <tr
                        key={`${l.lane}-${set}`}
                        className={cx('border-b border-line last:border-0', l.lane === report.chosenLane && 'bg-accent-wash')}
                      >
                        <td className="px-3 py-2 font-mono">
                          {i === 0 ? l.lane : ''}
                          {i === 0 && l.lane === report.chosenLane && <span className="chip ml-2">in use</span>}
                          {i === 0 && (l.refused ?? 0) > 0 && (
                            <div className="text-caption text-ink-soft font-sans">{l.refused} unscored: the helper model declined them</div>
                          )}
                        </td>
                        <td className="px-3 py-2">{set}</td>
                        <td className="px-3 py-2 text-right font-num">{m.questions}</td>
                        {METRICS.map((k) => (
                          <td key={k.key} className="px-3 py-2 text-right font-num">
                            {m[k.key].toFixed(3)}
                          </td>
                        ))}
                        <td className="px-3 py-2 text-right font-num">{m.costPerQuestion.toFixed(4)}</td>
                      </tr>
                    ))
                  ),
                )}
              </tbody>
            </table>
          </Card>
          <p className="text-caption text-ink-soft mt-2">{report.rule}</p>
        </>
      )}
    </section>
  );
}
