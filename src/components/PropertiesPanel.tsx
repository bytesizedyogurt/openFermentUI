// What thermosteam says of one mixture on file (OF-BLD-019 §4.2, D9), for
// pureOS → Train and fermOS.
//
// The panel names a question, never a number: a run's stream, or a preset the
// service fills. On mount it reads the answer stored for that question
// (`GET /api/thermo/props`, which starts no simulator); with none stored it
// offers to ask (`POST`), which runs in the Proforma worker. Every number on
// it is the service's, from one `thermo_props` artifact, in the library's own
// units, beside the library's version, the answer's provenance and a link to
// the artifact. A chemical the library lacks comes back as the service's
// words, and with the service down the panel says so; nothing stands in.
//
// ONE QUESTION, ONE ANSWER (§4.R). An ask belongs to the question it was made
// for: a new question, or the panel leaving, aborts it, and an answer that
// arrives after that is dropped, so one record's numbers never show under
// another's title. A caller whose question names a different thing also keys
// the panel by it, so a new thing mounts a new panel.
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ExternalLink, FlaskConical } from 'lucide-react';
import type { Artifact, ThermoPropsRequest } from '@/data/types';
import { PROPERTY_ROWS, ThermoDown, ThermoRefused, propsOf, thermoAsk, thermoStored } from '@/lib/thermo';
import { fmt } from '@/engine/units';
import { href } from '@/router';
import { ProvenanceBadge } from '@/components/Provenance';

type State =
  | { kind: 'reading' }
  | { kind: 'none' }
  | { kind: 'asking' }
  | { kind: 'answer'; art: Artifact }
  | { kind: 'refused'; text: string }
  | { kind: 'down'; text: string };

// A 503 is the simulator not answering (still starting, timed out, crashed):
// the service's words, and the button stays, since a second ask on a worker
// that is ready answers. Any other refusal is the question's, and final.
const said = (e: unknown): State =>
  e instanceof ThermoDown
    ? { kind: 'down', text: `${e.message} ${e.remedy}` }
    : e instanceof ThermoRefused
      ? e.status === 503
        ? { kind: 'down', text: `${e.message.replace(/\.?\s*$/, '.')} Ask again once the simulator is ready.` }
        : { kind: 'refused', text: e.message }
      : { kind: 'down', text: String(e) };

/** Mass fractions, largest first, as the service wrote them. */
function composition(fractions: Record<string, number>, shown = 4): string {
  const sorted = Object.entries(fractions).sort((a, b) => b[1] - a[1]);
  const head = sorted.slice(0, shown).map(([k, v]) => `${k} ${fmt(v, 4)}`);
  return head.join(', ') + (sorted.length > shown ? `, and ${sorted.length - shown} more` : '');
}

export function PropertiesPanel({ title, question }: { title: ReactNode; question: ThermoPropsRequest }) {
  const [state, setState] = useState<State>({ kind: 'reading' });
  const key = JSON.stringify(question);
  /** The ask in flight, for the question this panel shows now. */
  const asking = useRef<AbortController | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setState({ kind: 'reading' });
    thermoStored(question, ctrl.signal)
      .then((art) => !ctrl.signal.aborted && setState(art ? { kind: 'answer', art } : { kind: 'none' }))
      .catch((e) => !ctrl.signal.aborted && setState(said(e)));
    return () => {
      ctrl.abort();
      asking.current?.abort();
      asking.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const ask = () => {
    asking.current?.abort();
    const ctrl = new AbortController();
    asking.current = ctrl;
    setState({ kind: 'asking' });
    thermoAsk(question, ctrl.signal)
      .then((art) => !ctrl.signal.aborted && setState({ kind: 'answer', art }))
      .catch((e) => !ctrl.signal.aborted && setState(said(e)));
  };

  return (
    <div
      className="border border-line rounded-md p-3"
      data-testid="thermo-panel"
      data-stream={question.streamId ?? ''}
      data-preset={question.preset ?? ''}
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
        <div className="text-body font-medium">{title}</div>
        {(state.kind === 'none' || state.kind === 'down') && (
          <button className="chip" onClick={ask}>
            <FlaskConical size={12} aria-hidden /> Ask thermosteam
          </button>
        )}
      </div>
      {state.kind === 'reading' && <p className="text-caption text-ink-soft">Reading what is stored…</p>}
      {state.kind === 'none' && (
        <p className="text-caption text-ink-soft">
          Not asked here yet. thermosteam computes it in the Proforma simulator, which takes a minute to start the
          first time.
        </p>
      )}
      {state.kind === 'asking' && <p className="text-caption text-ink-soft">Asking thermosteam…</p>}
      {state.kind === 'refused' && (
        <p className="text-caption text-ink" data-testid="thermo-refused">
          thermosteam did not answer: {state.text}
        </p>
      )}
      {state.kind === 'down' && (
        <p className="text-caption text-signal-warn" data-testid="thermo-down">
          {state.text}
        </p>
      )}
      {state.kind === 'answer' && <Answer art={state.art} />}
    </div>
  );
}

function Answer({ art }: { art: Artifact }) {
  const p = propsOf(art);
  return (
    <div data-testid="thermo-props">
      <table className="w-full text-caption">
        <tbody>
          {PROPERTY_ROWS.map(({ key, label }) => (
            <tr key={key} className="border-b border-line/60" data-testid="thermo-row" data-key={key}>
              <td className="py-1 pr-2 text-ink-soft">{label}</td>
              <td className="py-1 pr-2 font-num text-right text-ink">{p[key] == null ? '—' : fmt(p[key] as number, 4)}</td>
              <td className="py-1 font-num text-ink-soft">{p[key] == null ? 'not computed' : p.units[key]}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-caption text-ink-soft mt-1.5">
        At <span className="font-num">{fmt(p.T, 2)} {p.units.T ?? 'K'}</span> ({p.TSource}) and{' '}
        <span className="font-num">{p.P.toFixed(0)} {p.units.P ?? 'Pa'}</span> ({p.PSource}), phase{' '}
        <span className="font-num">{p.phase}</span>; mass fractions{' '}
        <span className="font-num">{composition(p.massFractions)}</span>.
      </p>
      {typeof p.solved?.how === 'string' && <p className="text-caption text-ink-soft mt-1">Composition: {p.solved.how}.</p>}
      {p.notes.length > 0 && (
        <ul className="text-caption text-ink-soft mt-1 list-disc pl-4">
          {p.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
      <div className="flex flex-wrap items-center gap-2 mt-1.5 text-caption">
        <ProvenanceBadge p={art.provenance} compact />
        <span className="text-ink-soft" data-testid="thermo-library">
          Computed by {p.library}
        </span>
        <a className="inline-flex items-center gap-1 text-ink-soft hover:text-accent" href={href(`/biorepo/artifacts/${art.id}`)}>
          <span>
            Artifact <span className="font-num">{art.id}</span>
          </span>
          <ExternalLink size={10} aria-hidden />
        </a>
      </div>
    </div>
  );
}
