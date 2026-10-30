// One parameter panel for the whole platform (OF-BLD-020 §2.2, D2–D4).
//
// Every model family, vessel design, catalogue unit and shelf flowsheet
// declares its parameters once, in Python (`core/openferment_core/params.py`),
// and this panel renders any scope the same way: Proforma's scenarios
// (`proforma:<scenario id>`) now, fermOS's Simulate and Vessel and pureOS's
// Builder in later steps, unchanged. A screen never hand-writes a form for a
// parameter, and `check:seed` (E.1‴) fails on a numeric control in a
// module's screens outside this file and ParameterRow.tsx.
//
//   the caller   fetches the scope (`GET /api/params/{scope}`, lib/params.ts)
//                and passes it in as `data`, with what it binds by (a
//                scenario made in a browser names its flowsheet; host, fits);
//   the person   types a value, a low, a high and what it rests on: each
//                change is an `Override` under the reviewer name, at now,
//                kept in the open project's rows (`setOverride`;
//                lib/projectState.ts); Reset to source drops it
//                (`clearOverride`). With no
//                reviewer name every edit control is disabled and the row
//                says where to set one;
//   the service  is asked after each change, debounced, to lay the scope's
//                overrides on (`POST /api/params/{scope}/resolve`), and its
//                answer, its out-of-bounds warnings included, is what each
//                row shows. A value outside the bounds is kept, never clamped.
//                The service binds the scope with the overrides as a run of
//                it binds them, so a refusal here is the run's refusal, in
//                its words: the caller hears it (`onRefused`) and holds Run
//                (OF-BLD-020 §2.R). With the service down the panel says so,
//                and the override is still kept and still sent with the run.
//
// The panel COMPUTES NOTHING: every value, source and warning it shows came
// from the service or the person. A model never sets an override.
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import type { Override, ParameterSpec, ParameterValue, ParamResolveResult, ParamScope } from '@/data/types';
import { overrideEnds, overridesFor, useStore } from '@/store';
import { ParamsDown, resolveParams, type ParamAsk } from '@/lib/params';
import { ParameterRow, type ParameterChange } from './ParameterRow';

export interface ParameterPanelProps {
  /** The scope the specs and overrides belong to: `proforma:<id>`, `fermos:family:<id>`, `fermos:vessel:<id>`, `pureos:unit:<train>:<unit>`. */
  scope: string;
  /** The scope as the caller fetched it (`GET /api/params/{scope}`); null while it is asked or when it could not be. */
  data: ParamScope | null;
  /** What the resolve request carries besides the overrides: a scenario made in a browser names its flowsheet; host and fits bind as the caller binds. */
  request?: ParamAsk;
  /** After a person's change, with the scope's overrides as they now stand: the caller refetches or reruns. */
  onChange?: (overrides: Override[]) => void;
  /** The service's answer to the latest resolve, or null when there is none to read (no override, or no answer). */
  onResolved?: (result: ParamResolveResult | null) => void;
  /** The service's words when it refuses the scope's overrides as they stand (a run of them would be refused alike), else null. */
  onRefused?: (words: string | null) => void;
  /** The order the groups are shown in; groups it does not name follow in the specs' order. */
  groups?: string[];
  /** Show every value and its source, and offer no edit. */
  readOnly?: boolean;
  /** What a record-bound value's link opens, by key (Proforma passes the records chooser it had); by default the records as citation chips. */
  recordsOf?: (key: string, value: ParameterValue) => ReactNode;
}

/** How long the panel waits after a change before asking the service to resolve it. */
const RESOLVE_AFTER_MS = 350;

/** A person's override as the row shows it while the service has not answered: their value, its interval as the service reads it (`overrideEnds`), their name. */
function asTyped(o: Override, served: ParameterValue | undefined): ParameterValue {
  const ends = overrideEnds(o);
  return {
    key: o.key,
    value: o.value,
    low: ends.low,
    high: ends.high,
    source: { kind: 'assumption', id: null, by: o.by, note: o.note },
    origin: 'assumption',
    identified: null,
    overriddenBy: o.by,
    libraryDefault: served?.libraryDefault ?? null,
    recordIds: [],
    detail: null,
    outOfBounds: null,
  };
}

/** The groups in the caller's order, then any the caller did not name, in the specs' order. */
export function groupOrder(specs: ParameterSpec[], groups: string[] = []): string[] {
  const present = [...new Set(specs.map((s) => s.group))];
  return [...groups.filter((g) => present.includes(g)), ...present.filter((g) => !groups.includes(g))];
}

/** The time an override is kept at: now, to the second, in UTC. */
const nowStamp = () => `${new Date().toISOString().slice(0, 19)}Z`;

export function ParameterPanel({ scope, data, request, onChange, onResolved, onRefused, groups, readOnly, recordsOf }: ParameterPanelProps) {
  const overrides = useStore(overridesFor(scope));
  const reviewer = useStore((s) => s.reviewer).trim();
  const setOverride = useStore((s) => s.setOverride);
  const clearOverride = useStore((s) => s.clearOverride);
  const [resolved, setResolved] = useState<{ asked: string; result: ParamResolveResult } | null>(null);
  const [problem, setProblem] = useState<{ down: boolean; words: string } | null>(null);
  const resolvedRef = useRef(onResolved);
  resolvedRef.current = onResolved;
  const refusedRef = useRef(onRefused);
  refusedRef.current = onRefused;

  const askKey = JSON.stringify(request ?? {});
  const overridesKey = JSON.stringify(overrides);
  const asked = `${scope}|${askKey}|${overridesKey}`;

  // After each change, debounced: the service lays the scope's overrides on.
  useEffect(() => {
    setProblem(null);
    refusedRef.current?.(null);
    if (!data || overrides.length === 0) {
      setResolved(null);
      resolvedRef.current?.(null);
      return;
    }
    const ctrl = new AbortController();
    const timer = window.setTimeout(() => {
      resolveParams(scope, overrides, JSON.parse(askKey) as ParamAsk, ctrl.signal)
        .then((result) => {
          setResolved({ asked, result });
          resolvedRef.current?.(result);
        })
        .catch((e: unknown) => {
          if (ctrl.signal.aborted) return;
          setResolved(null);
          resolvedRef.current?.(null);
          const down = e instanceof ParamsDown;
          const words = down ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e);
          setProblem({ down, words });
          if (!down) refusedRef.current?.(words);
        });
    }, RESOLVE_AFTER_MS);
    return () => {
      window.clearTimeout(timer);
      ctrl.abort();
    };
    // `asked` names the scope, the request and the overrides; data starts it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [asked, data]);

  const fresh = resolved && resolved.asked === asked ? resolved.result : null;
  const served = useMemo(() => new Map((data?.values ?? []).map((v) => [v.key, v])), [data]);
  const answered = useMemo(() => new Map((fresh?.values ?? []).map((v) => [v.key, v])), [fresh]);
  const byKey = useMemo(() => new Map(overrides.map((o) => [o.key, o])), [overrides]);

  if (!data) return null;

  const change = (spec: ParameterSpec, c: ParameterChange) => {
    if (!reviewer) return;
    setOverride({ scope, key: spec.key, value: c.value, low: c.low, high: c.high, by: reviewer, at: nowStamp(), note: c.note });
    onChange?.(useStore.getState().parameterOverrides[scope] ?? []);
  };
  const reset = (spec: ParameterSpec) => {
    clearOverride(scope, spec.key);
    onChange?.(useStore.getState().parameterOverrides[scope] ?? []);
  };

  return (
    <div data-testid="parameter-panel" data-scope={scope} data-resolved={fresh ? 'true' : 'false'}>
      {problem && (
        <p className="text-caption text-signal-warn mb-2" role="status" data-testid="param-problem" data-down={problem.down ? 'true' : 'false'}>
          {problem.down
            ? `The service could not check these values: ${problem.words} Your changes are kept in the project and go with the run.`
            : `The service refused these values: ${problem.words}`}
        </p>
      )}
      {groupOrder(data.specs, groups).map((g) => (
        <section key={g} className="mb-3" aria-label={g} data-testid="param-group" data-group={g}>
          <h3 className="text-caption uppercase tracking-wide text-ink-soft mb-0.5">{g}</h3>
          {data.specs
            .filter((s) => s.group === g)
            .map((spec) => {
              const o = byKey.get(spec.key) ?? null;
              const value = answered.get(spec.key) ?? (o ? asTyped(o, served.get(spec.key)) : served.get(spec.key) ?? null);
              return (
                <ParameterRow
                  key={spec.key}
                  spec={spec}
                  value={value}
                  override={o}
                  reviewer={reviewer}
                  readOnly={readOnly}
                  warning={value?.outOfBounds ?? null}
                  records={value && value.origin === 'record' && recordsOf ? recordsOf(spec.key, value) : undefined}
                  onSet={(c) => change(spec, c)}
                  onReset={() => reset(spec)}
                />
              );
            })}
        </section>
      ))}
      {data.notes.length > 0 && (
        <ul className="text-caption text-ink-soft space-y-0.5 mt-2" data-testid="param-notes">
          {data.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
