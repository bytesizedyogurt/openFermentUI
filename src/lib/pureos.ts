// The browser's side of pureOS's trains (OF-BLD-019 §4.1, D1).
//
// The service reads a train from one `proforma.run` artifact's stream and
// unit tables (`core/openferment_core/pureos/__init__.py`); the browser shows it and
// computes nothing of its own: every mass, recovery and cumulative share on
// the page is a field the service sent. With the service down this says so,
// and nothing stands in for a train (E.2). Shares lib/rag.ts's call.
import type { ProposeRequest, StreamRow, Train, TrainProposal, TrainSummary, TrainUnit } from '@/data/types';
import { RagDown, RagRefused, call } from './rag';

export { RagDown as PureosDown, RagRefused as PureosRefused };

/**
 * Every train on file. The page asks for archived programs' trains too and
 * filters them with the switch itself, so it can say what it hides and whose
 * (`HiddenByArchive`), as the other lists do.
 */
export const pureosTrains = (signal?: AbortSignal) =>
  call<TrainSummary[]>('/api/pureos/trains?includeArchived=true', { signal });

/** One train: the newest run of a scenario, or one run by its artifact id. */
export const pureosTrain = (key: string, signal?: AbortSignal) =>
  call<Train>(`/api/pureos/train/${encodeURIComponent(key)}`, { signal });

/** Where a train opens: by its scenario when one claims the run, else by the run. */
export const trainPath = (t: { scenarioId: string | null; artifactId: string }) =>
  `/pureos/train/${encodeURIComponent(t.scenarioId ?? t.artifactId)}`;

/** The streams that enter or leave one unit, inlets first, in the unit's own order. */
export function streamsOf(train: Train, unit: TrainUnit | null): StreamRow[] {
  if (!unit) return train.streams;
  const byId = new Map(train.streams.map((s) => [s.id, s]));
  return [...unit.ins, ...unit.outs].map((id) => byId.get(id)).filter((s): s is StreamRow => !!s);
}

/** A stream's product flow as the run's table states it, or null when the run names no product. */
export const productIn = (train: Train, s: StreamRow): number | null =>
  train.product ? (s.massFlows[train.product] ?? 0) : null;

/** A share as a percentage, or the words for why there is none. */
export function share(v: number | null, digits = 1): string {
  return v == null || !Number.isFinite(v) ? '—' : `${(v * 100).toFixed(digits)}%`;
}

/**
 * OF-BLD-020 §7.2 — a train proposed by the service's written rules
 * (`core/openferment_core/pureos/proposer.py`): ids and words go out, and the
 * proposal comes back with every unit's reason, the property it read and the
 * artifact that holds it, or what is missing. The browser decides nothing.
 */
export const proposeTrain = (ask: ProposeRequest, signal?: AbortSignal) =>
  call<TrainProposal>('/api/pureos/propose', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(ask),
    signal,
  });

/** Where a train opens in pureOS's Builder (OF-BLD-020 §5.3), by the id this browser gave it. */
export const builderPath = (trainId: string) => `/pureos/build/${encodeURIComponent(trainId)}`;

/** What a train's run was made from, in words the page shows beside its numbers. */
export const RUN_WORDS =
  'Read from the run Proforma priced: one artifact holds its stream and unit tables, and every number here is ' +
  'arithmetic over that stream table, done by the service. Nothing is typed and nothing is simulated again.';
