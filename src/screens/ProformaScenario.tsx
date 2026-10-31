// Scenario workspace (OF-DES-001 §8.13). Read it like an instrument: every
// assumption ticked, the waterfall always summing to the headline, and
// simulation treated as work rather than magic.
//
// OF-BLD-019 §3.2 (D1, D5, D6): the BioSTEAM page is THE scenario page. A
// held BioSTEAM scenario and one a person made here with New scenario open
// the same page (BiosteamScenario, below): header, inputs with their sources,
// Run with the worker's status line, and every section of the newest run read
// from its one artifact (ProformaBiosteam.tsx).
import { useEffect, useMemo, useState } from 'react';
import { Download, GitCompare, Pin, PinOff, Play, Route } from 'lucide-react';
import { overrideEnds, overridesFor, proformaScope, useStore } from '@/store';
import { href, navigate, useRoute } from '@/router';
import type { Artifact, BasisInput, CeilingCheck, CeilingRow, FermosFitInfo, FlowsheetInfo, ParamScope, ProformaScenarioInfo, Scenario, ScenarioInput } from '@/data/types';
import { durableAvailable } from '@/lib/durable';
import {
  FIT_TOOL_WORDS,
  ProformaDown,
  SIMULATOR_SAYS,
  ceilingCheck,
  fermosFits,
  fitsFrom,
  modellerQuestions,
  newestRunId,
  partsOf,
  proformaArtifact,
  proformaNewestRun,
  proformaBind,
  proformaScenarios,
  proformaShelf,
  proformaStatus,
  questionsText,
  scenarioRunOverrides,
  runProformaScenario,
  runViewOfArtifact,
  runViewOfResult,
  stamp,
  trainRunPath,
  vesselDesignPath,
  type RunView,
  type SimulatorStatus,
} from '@/lib/proforma';
import { trainPath } from '@/lib/pureos';
import { paramScope } from '@/lib/params';
import { ParameterPanel } from '@/components/ParameterPanel';
import { TOUCH_CHIP } from '@/components/ParameterRow';
import { inputSourceWords } from '@/components/NewScenarioDialog';
import { fmt } from '@/engine/units';
import { exportText } from '@/lib/csv';
import { PageHeader, Card, Button, Callout, cx, EmptyState } from '@/components/ui';
import { CitationChip } from '@/components/Chip';
import { ProvenanceBadge } from '@/components/Provenance';
import { CEILING_NOTES } from '@/components/figures';
import { RunReport, inputLabels } from './ProformaBiosteam';


// ── The BioSTEAM scenario page (OF-BLD-014 §8.4; OF-BLD-019 §3.2) ───────
//
// ONE page for a held BioSTEAM scenario and for one a person made here with
// New scenario (D6). It reads, and never types:
//
//   the shelf       the flowsheet's title, source and each input's
//                   dimension (GET /api/proforma/shelf);
//   the binding     a held scenario from GET /api/proforma/scenarios, one
//                   made here from GET /api/proforma/bind?flowsheet= (the
//                   scenario run contract, src/lib/proforma.ts), each input
//                   bound to records, an artifact, a named person's
//                   assumption, or waiting: its host list, what it leaves
//                   out, and the questions for a modeller read it;
//   the inputs      OF-BLD-020 §2.2: the parameter panel over scope
//                   `proforma:<scenario id>` (GET /api/params/{scope}, a
//                   scenario made here naming its flowsheet), every input
//                   with its value and source, a slider inside its bounds,
//                   Reset to source and Why. A person's change is an
//                   Override in this browser under the reviewer name, the
//                   one thing a run carries of a person (`overrides`), and it
//                   wins over the records and any fermOS fit for its input,
//                   here and in the service alike;
//   the parts       OF-BLD-020 §6.1: a scenario on `custom_train_v1` names
//                   the vessel design and the train run it is built from
//                   (`partsOf`), sent with every binding, panel read and run,
//                   and named here with links (the design's artifact, the
//                   train run in pureOS); its panel adds the group Finance,
//                   the TEA's parameters, each the package's own default
//                   until a person sets one;
//   the run         POST /api/proforma/run, one `proforma.run` artifact
//                   (D1); after a run the store keeps its id
//                   (recordScenarioRun), and on load the page reads the newest
//                   run back from GET /api/biorepo/artifacts/{id}. Every
//                   section under the Run (ProformaBiosteam.tsx) reads that
//                   one run.
//
// A binding the service refuses is said in its words, and the inputs the
// flowsheet takes are still listed from the shelf.

const problemOf = (e: unknown) => (e instanceof ProformaDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

/**
 * The records an input binds, as the binding lists them: each a citation
 * chip on its paper, with the organism, the carbon source and its value in
 * the input's unit. The parameter panel opens it from the input's
 * `record ×N` chip (OF-BLD-020 §2.2: the records chooser this page had
 * became the panel's record link). Rendered inside the panel, its chips are
 * the panel's 44 px touch targets (§2.R, finding 11).
 */
function RecordsChooser({ input }: { input: ScenarioInput | undefined }) {
  if (!input || input.records.length === 0) return null;
  return (
    <div className="flex flex-col gap-1" data-testid="source-records">
      {input.source?.note && <span className="text-caption text-ink-soft">{input.source.note}</span>}
      {input.records.map((r) => (
        <span key={r.id} className="inline-flex flex-wrap items-center gap-1">
          <CitationChip recordId={r.id} paperId={r.paperId} className={TOUCH_CHIP} />
          <span className="text-caption text-ink-soft">
            {r.organism ?? 'organism not stated'} · {r.carbonSource ?? 'carbon source not stated'} ·{' '}
            <span className="font-num">{fmt(r.value, 3)}</span>
          </span>
        </span>
      ))}
    </div>
  );
}

/**
 * Who a run's basis names for each assumption it rests on, read from the
 * run (OF-BLD-020 §2.2): the panel's chip says who typed a value here, and
 * this line says whose values the run that is shown was made with.
 */
function BasisAssumptions({ inputs, labels }: { inputs: BasisInput[]; labels: Record<string, string> }) {
  const named = inputs.filter((i) => i.source.kind === 'assumption' && !/ (low|high)$/.test(i.name));
  if (named.length === 0) return null;
  return (
    <p className="text-caption text-ink-soft mt-2" data-testid="run-basis-assumptions">
      The run shown rests on{' '}
      {named.map((i, n) => (
        <span key={i.name}>
          {n > 0 && (n === named.length - 1 ? ' and ' : ', ')}
          {labels[i.name] ?? i.name} as an assumption by {i.source.by ?? 'nobody named'}
        </span>
      ))}
      , as its basis names them.
    </p>
  );
}

/**
 * Use a fermOS fit (OF-BLD-019 §5.1, D10). A source, not a copy: the fits
 * fermOS keeps (GET /api/fermos/fits) are listed with their provenance, the
 * run each was fitted to and what each can feed this flowsheet's titre,
 * yield and productivity, each value as the service computed it from the
 * artifact, or why not, in its words. Choosing one keeps which artifact
 * feeds which input (`proformaFits`, Durable, like assumptions), and the
 * binding then names it as the inputs' source. A fit sent from fermOS →
 * Forecast arrives as `?fit=` and is attached here, once, for the inputs it
 * can feed. With no fit on file it says how one gets made. A value a person
 * typed for an input wins over a fit chosen for it (OF-BLD-020 D3), so a
 * card never says it is in use for that input: it says whose value wins
 * there (§2.R, findings 8 and 12).
 */
function FermosFitSlot({
  flowsheetId,
  chosen,
  overridden,
  onChoose,
  onStop,
}: {
  flowsheetId: string;
  chosen: Record<string, string>;
  /** The inputs a person's value overrides, each with the person's name: no fit feeds them. */
  overridden: Record<string, string>;
  onChoose: (fits: Record<string, string>) => void;
  /** Stop using these artifacts: only the inputs each feeds are cleared (§5.R). */
  onStop: (artifactIds: string[]) => void;
}) {
  const route = useRoute();
  const sent = route.query.get('fit');
  const [fits, setFits] = useState<FermosFitInfo[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [arrived, setArrived] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setFits(null);
    setProblem(null);
    fermosFits(flowsheetId, ctrl.signal)
      .then(setFits)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [flowsheetId]);

  // A fit sent from fermOS → Forecast: attached once, for the inputs it can
  // feed, then the address loses its ?fit= so a reload attaches nothing.
  useEffect(() => {
    if (!sent || !fits) return;
    const found = fits.find((f) => f.artifactId === sent);
    const feeds = found ? fitsFrom(found) : {};
    if (Object.keys(feeds).length > 0) onChoose(feeds);
    setArrived(
      !found
        ? `${sent} was sent from fermOS, but it is not a kinetic fit or forecast on file here.`
        : Object.keys(feeds).length > 0
          ? `${FIT_TOOL_WORDS[found.tool] ?? found.tool} ${sent}, sent from fermOS, now feeds ${Object.keys(feeds).join(', ')}.`
          : `${FIT_TOOL_WORDS[found.tool] ?? found.tool} ${sent} was sent from fermOS, but it feeds nothing here: ${found.refused ?? found.feeds.map((f) => `${f.key}: ${f.refused}`).join('; ')}`,
    );
    navigate(route.path, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sent, fits]);

  const using = new Set(Object.values(chosen));
  const missing = [...using].filter((id) => fits && !fits.some((f) => f.artifactId === id));
  return (
    <div className="mt-4 border-t border-line/60 pt-3" data-testid="fermos-fit-slot">
      <h3 className="font-medium text-body">Use a fermOS fit</h3>
      <p className="text-caption text-ink-soft mb-2">
        A fit of a deposited run can give the fermenter its titre, its yield on sugar and its batch time. The service computes each
        from the fit&rsquo;s forecast, drawn again to the hour its median sugar runs out (found between the forecast&rsquo;s points, so
        the length it was asked to run does not move them): titre from the final product, yield from product made over sugar used,
        and productivity as that titre over that hour. A simulation fermOS keeps gives its own end state instead, computed and never
        measured: titre at harvest, the yield it achieved, and its harvest hour as the batch time. A productivity feeds the fermenter
        only beside titre from the same fit or simulation, since the batch time is the titre over the productivity. The run then names
        the fit or simulation as the source of each input it feeds; a value a person types in the panel wins over it for that input.
      </p>
      {arrived && (
        <p className="text-caption mb-2" data-testid="fermos-fit-arrived">
          {arrived}
        </p>
      )}
      {problem && <p className="text-caption text-signal-warn">The fits fermOS keeps could not be read: {problem}</p>}
      {!problem && fits === null && <p className="text-caption text-ink-soft">Reading the fits fermOS keeps…</p>}
      {fits !== null && fits.length === 0 && (
        <p className="text-caption" data-testid="fermos-fit-none">
          No fermOS fit is on file yet. One is made from a run: deposit its readings in{' '}
          <a className="text-accent hover:underline" href={href('/runbooks/depositions')}>
            Runbooks → Depositions
          </a>{' '}
          (the time of each sample, biomass at four or more times, product and sugar at the same times), then fit it in{' '}
          <a className="text-accent hover:underline" href={href('/fermos')}>
            fermOS
          </a>
          . A forecast on{' '}
          <a className="text-accent hover:underline" href={href('/fermos/forecast')}>
            fermOS → Forecast
          </a>{' '}
          run until the sugar is spent gives the batch time as well.
        </p>
      )}
      {missing.length > 0 && (
        <p className="text-caption text-signal-warn">
          The fit this scenario uses, {missing.join(', ')}, is not on file here any more.{' '}
          <button className="underline hover:text-accent" onClick={() => onStop(missing)}>
            Stop using it
          </button>
        </p>
      )}
      {fits !== null && fits.length > 0 && (
        <ul className="space-y-2">
          {fits.map((f) => {
            const feeds = fitsFrom(f);
            const inUse = using.has(f.artifactId);
            const mine = Object.entries(chosen)
              .filter(([, id]) => id === f.artifactId)
              .map(([k]) => k);
            const used = mine.filter((k) => !(k in overridden));
            const beaten = mine.filter((k) => k in overridden);
            return (
              <li key={f.artifactId} className="card p-3" data-testid="fermos-fit-option" data-artifact={f.artifactId} data-feeds={Object.keys(feeds).length}>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium">{FIT_TOOL_WORDS[f.tool] ?? f.tool}</span>
                  <a className="font-num text-caption hover:text-accent underline underline-offset-2" href={href(`/biorepo/artifacts/${f.artifactId}`)}>
                    {f.artifactId}
                  </a>
                  <ProvenanceBadge p={f.provenance} />
                  <span className="text-caption text-ink-soft">
                    {f.tool === 'fermos.simulation' ? 'computed, not measured' : `run ${f.depositionId ?? 'not named'}`}
                    {f.productSeries && <> · product: {f.productSeries}</>}
                    {f.substrateSeries && <> · sugar: {f.substrateSeries}</>}
                  </span>
                </div>
                <ul className="text-caption mt-1">
                  {f.feeds.map((x) => (
                    <li key={x.key} data-testid="fermos-fit-feed" data-key={x.key}>
                      <span className="font-medium">{x.key}</span>:{' '}
                      {x.refused || x.value == null ? (
                        <span className="text-ink-soft">{x.refused}</span>
                      ) : (
                        <>
                          <span className="font-num">{fmt(x.value, 4)}</span> {x.unit} (
                          <span className="font-num">
                            {fmt(x.low ?? Number.NaN, 4)}–{fmt(x.high ?? Number.NaN, 4)}
                          </span>
                          )
                        </>
                      )}
                    </li>
                  ))}
                </ul>
                {f.batchTimeH != null && (
                  <div className="text-caption text-ink-soft">
                    {/* §8.R: the words of the tool that kept it (a forecast's grid, a simulation's harvest), never one tool's for all. */}
                    Batch time <span className="font-num">{fmt(f.batchTimeH, 4)}</span> h: {f.batchTimeNote ?? 'the hour its sugar runs out'}.
                  </div>
                )}
                {f.flags.map((w) => (
                  <div key={w} className="text-caption text-signal-warn">
                    {w}
                  </div>
                ))}
                <div className="mt-2">
                  {inUse ? (
                    <span className="text-caption">
                      {used.length > 0 ? `In use for ${used.join(', ')}.` : 'In use for no input: a person’s value wins wherever it was chosen.'}{' '}
                      {beaten.length > 0 && (
                        <span data-testid="fermos-fit-overridden">
                          Chosen for {beaten.map((k) => `${k}, where ${overridden[k]}’s value wins`).join('; ')}: the run does not use the fit
                          there.{' '}
                        </span>
                      )}
                      <button className="underline hover:text-accent" onClick={() => onStop([f.artifactId])} data-testid="fermos-fit-stop">
                        Stop using this fit
                      </button>
                    </span>
                  ) : (
                    <Button onClick={() => onChoose(feeds)} disabled={Object.keys(feeds).length === 0} data-testid="fermos-fit-use">
                      Use this fit for {Object.keys(feeds).join(', ') || 'nothing it can feed'}
                    </Button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

/** How a ceiling-check row's flag reads in its chip. */
const CEILING_FLAG_WORDS: Record<CeilingRow['flag'], string> = {
  above: 'Above the ceiling: check the basis',
  within: 'At or under the ceiling',
  'no-yield': 'No yield to read yet',
};

/** A g g⁻¹ or mol mol⁻¹ value, or a dash where there is none. */
const ceilingNum = (v: number | null | undefined, digits = 4) => (v == null ? '—' : fmt(v, digits));

/** The scenario's yield as the check read it: where it comes from. */
function CeilingYieldSource({ check }: { check: CeilingCheck }) {
  const src = check.yieldSource;
  if (check.yieldBinding === 'records')
    return (
      <span className="chip" data-testid="ceiling-yield-source" data-binding="records">
        {check.yieldRecords} record{check.yieldRecords === 1 ? '' : 's'}
      </span>
    );
  if (check.yieldBinding === 'assumption')
    return (
      <span className="chip" data-testid="ceiling-yield-source" data-binding="assumption">
        assumption by {src?.by ?? 'a named person'}
      </span>
    );
  if (check.yieldBinding === 'artifact' && src?.id)
    return (
      <a className="chip hover:text-accent" href={href(`/biorepo/artifacts/${src.id}`)} data-testid="ceiling-yield-source" data-binding="artifact">
        fermOS {(check.yieldTool && FIT_TOOL_WORDS[check.yieldTool]) || 'fit'} {src.id}
      </a>
    );
  return (
    <span className="chip" data-testid="ceiling-yield-source" data-binding={check.yieldBinding}>
      waiting
    </span>
  );
}

/**
 * The ceiling check (OF-BLD-019 §5.2, D11): the fermenter's yield, as this
 * scenario binds it, beside the newest stored geneOS ceiling of each shelf
 * model of its organism, on its flowsheet's sugar, both on the ceiling's own
 * footing (g per g, and mol per mol at its conventions), as the service
 * computes it on read. A yield above a ceiling is flagged in words for a
 * reviewer; nothing is clamped and the run keeps the yield as bound. With no
 * ceiling on file it says so and links to where one is computed.
 */
function CeilingCheckSlot({ check, problem }: { check: CeilingCheck | null; problem: string | null }) {
  if (!check && !problem) return null;
  return (
    <Card className={cx('p-4', check?.flagged && 'border-signal-warn/50')} data-testid="ceiling-check" data-flagged={check?.flagged ? 'true' : 'false'}>
      <h2 className="font-serif text-section-title font-semibold mb-1">Ceiling check</h2>
      <p className="text-caption text-ink-soft mb-2">
        The fermenter&rsquo;s yield beside the most a published reaction network of its organism can make from its sugar, as geneOS
        computed and kept it. A flag, never a bound: a yield above a ceiling is marked for a reviewer to check its basis, and the run
        keeps the yield as bound.
      </p>
      {problem && (
        <p className="text-caption text-signal-warn" data-testid="ceiling-problem">
          The ceiling check could not be read: {problem}
        </p>
      )}
      {check && (
        <div className="space-y-3">
          <div className="text-body" data-testid="ceiling-yield">
            <span className="font-medium">The scenario&rsquo;s yield: </span>
            {check.yieldValue == null ? (
              <span className="text-ink-soft">none yet</span>
            ) : (
              <>
                <span className="font-num">{fmt(check.yieldValue, 4)}</span>
                {check.yieldLow != null && check.yieldHigh != null && check.yieldLow !== check.yieldHigh && (
                  <span className="font-num">
                    {' '}
                    ({fmt(check.yieldLow, 4)}–{fmt(check.yieldHigh, 4)})
                  </span>
                )}{' '}
                <span className="font-num">{check.yieldUnit}</span>
              </>
            )}{' '}
            <CeilingYieldSource check={check} /> <span className="text-caption text-ink-soft">{check.yieldWords}.</span>
          </div>
          <p className="text-caption text-ink-soft" data-testid="ceiling-organism">
            Organism: {check.organismWords}. Sugar: {check.sugarWords}.
          </p>
          {check.rows.length === 0 && check.empty && (
            <p className="text-body" data-testid="ceiling-empty">
              {check.empty}{' '}
              <a className="text-accent hover:underline" href={href(check.computeAt)} data-testid="ceiling-compute">
                Open geneOS → Model
              </a>
            </p>
          )}
          {check.rows.map((r) => (
            <div
              key={r.artifactId}
              className={cx('rounded-card border p-3', r.flag === 'above' ? 'border-signal-warn/45 bg-signal-warn/[0.06]' : 'border-line')}
              data-testid="ceiling-row"
              data-model={r.modelId}
              data-flag={r.flag}
            >
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <span className="font-medium">{r.modelName}</span>
                <span className={cx('chip', r.flag === 'above' && 'text-signal-warn')} data-testid="ceiling-flag">
                  {CEILING_FLAG_WORDS[r.flag]}
                </span>
              </div>
              <table className="w-full text-body">
                <thead>
                  <tr className="text-caption text-ink-soft text-left">
                    <th className="py-1 pr-2 font-medium" />
                    <th className="py-1 pr-2 font-medium">g {r.product} per g {r.substrate}</th>
                    <th className="py-1 pr-2 font-medium">mol per mol</th>
                    <th className="py-1 font-medium">Its basis</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-t border-line/60 align-top" data-testid="ceiling-ceiling">
                    <td className="py-1.5 pr-2">Ceiling, {r.modelId} on {r.substrate}</td>
                    <td className="py-1.5 pr-2 font-num" data-testid="ceiling-value">
                      {fmt(r.ceilingGPerG, 4)}
                    </td>
                    <td className="py-1.5 pr-2 font-num">{ceilingNum(r.ceilingMolPerMol)}</td>
                    <td className="py-1.5 text-caption">
                      <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/biorepo/artifacts/${r.artifactId}`)} data-testid="ceiling-artifact">
                        {r.artifactId}
                      </a>{' '}
                      <ProvenanceBadge p={r.provenance} /> {r.modelBasis}, kept {stamp(r.createdAt)}
                      {r.older > 0 && `; the newest of ${r.older + 1} on file`}
                    </td>
                  </tr>
                  <tr className="border-t border-line/60 align-top" data-testid="ceiling-scenario">
                    <td className="py-1.5 pr-2">This scenario&rsquo;s yield</td>
                    <td className="py-1.5 pr-2 font-num">
                      {ceilingNum(r.yieldGPerG)}
                      {r.yieldLowGPerG != null && r.yieldHighGPerG != null && r.yieldLowGPerG !== r.yieldHighGPerG && (
                        <span className="text-caption">
                          {' '}
                          ({fmt(r.yieldLowGPerG, 4)}–{fmt(r.yieldHighGPerG, 4)})
                        </span>
                      )}
                    </td>
                    <td className="py-1.5 pr-2 font-num">{ceilingNum(r.yieldMolPerMol)}</td>
                    <td className="py-1.5 text-caption">{check.yieldWords}, at the ceiling&rsquo;s conventions</td>
                  </tr>
                </tbody>
              </table>
              <p className="text-body mt-2" data-testid="ceiling-words">
                {r.words}
              </p>
              {r.recordsAbove.length > 0 && (
                <ul className="text-caption mt-1 space-y-0.5">
                  {r.recordsAbove.map((id) => (
                    <li key={id} data-testid="ceiling-record-above">
                      <span className="font-num">{id}</span> is above this ceiling.{' '}
                      <a className="text-accent hover:underline" href={href(`/guild?record=${id}`)}>
                        Ask a reviewer to check its basis
                      </a>
                      .
                    </li>
                  ))}
                </ul>
              )}
              <p className="text-caption text-ink-soft mt-1">{r.matchWords}.</p>
              {r.conventions.length > 0 && (
                <details className="mt-1">
                  <summary className="text-caption text-ink-soft cursor-pointer hover:text-accent">The conventions the ceiling&rsquo;s basis names</summary>
                  <ul className="text-caption text-ink-soft mt-1">
                    {r.conventions.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          ))}
          {check.otherSugars.length > 0 && (
            <p className="text-caption text-ink-soft">
              Ceilings of {check.models.join(', ')} on {check.otherSugars.join(', ')} are on file too; this scenario&rsquo;s sugar is{' '}
              {check.substrate}, so they are left aside.
            </p>
          )}
          <ul className="text-caption text-ink-soft space-y-0.5">
            {check.rows.length > 0 && CEILING_NOTES.map((n) => <li key={n}>{n}</li>)}
            {check.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
}

/** The worker's status in words, with the seconds a run in hand has taken. */
function StatusLine({ status, problem, running, elapsed }: { status: SimulatorStatus | null; problem: string | null; running: boolean; elapsed: number }) {
  return (
    <span className="text-caption text-ink-soft" data-testid="run-status" data-status={status?.status ?? 'unknown'}>
      {status ? SIMULATOR_SAYS[status.status] : problem ? `The simulator's status could not be read: ${problem}` : "Asking the service for the simulator's status."}
      {status?.error && ` ${status.error}`}
      {running && (
        <>
          {' '}
          Running for <span className="font-num">{elapsed}</span> s.
        </>
      )}
    </span>
  );
}

function BiosteamScenario({ scenario, madeHere }: { scenario: Scenario; madeHere: boolean }) {
  // OF-BLD-020 §2.2 (D3): a person's changes to this scenario's inputs, kept
  // in this browser under the scenario's scope and sent with the run.
  const scope = proformaScope(scenario.id);
  const overrides = useStore(overridesFor(scope));
  const chosenFits = useStore((s) => s.proformaFits[scenario.id]) ?? EMPTY_FITS;
  const setFits = useStore((s) => s.setProformaFits);
  const clearFit = useStore((s) => s.clearProformaFit);
  const togglePin = useStore((s) => s.togglePin);
  const recordScenarioRun = useStore((s) => s.recordScenarioRun);
  const flowsheetId = scenario.flowsheetId ?? scenario.modelId;
  // OF-BLD-020 §6.1: what a scenario on custom_train_v1 is built from.
  const parts = partsOf(scenario);
  const vesselId = parts?.vessel ?? null;
  const trainRunId = parts?.trainRun ?? null;

  const [shelf, setShelf] = useState<FlowsheetInfo[] | null>(null);
  const [shelfProblem, setShelfProblem] = useState<string | null>(null);
  const [host, setHost] = useState<string | null>(null);
  const [info, setInfo] = useState<ProformaScenarioInfo | null>(null);
  const [bindProblem, setBindProblem] = useState<string | null>(null);
  const [status, setStatus] = useState<SimulatorStatus | null>(null);
  const [statusProblem, setStatusProblem] = useState<string | null>(null);
  const [view, setView] = useState<RunView | null>(null);
  const [loadProblem, setLoadProblem] = useState<string | null>(null);
  const [runProblem, setRunProblem] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [ceiling, setCeiling] = useState<CeilingCheck | null>(null);
  const [ceilingProblem, setCeilingProblem] = useState<string | null>(null);
  const [panel, setPanel] = useState<ParamScope | null>(null);
  // §8.R: a fermOS source is named as what the service bound it as (the
  // scope is read with no override, so an overridden key keeps its source's
  // origin): a kept simulation is a simulation, never a fit.
  const fitWord = (key: string) => (panel?.values.find((v) => v.key === key)?.origin === 'simulation' ? 'simulation' : 'fit');
  const [panelProblem, setPanelProblem] = useState<string | null>(null);
  // The service's refusal of the scope's overrides as they stand: the panel
  // binds them as a run binds them, so a run of them would be refused in
  // the same words, and Run waits until they stand (OF-BLD-020 §2.R).
  const [refused, setRefused] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    proformaShelf(ctrl.signal)
      .then(setShelf)
      .catch((e: unknown) => !ctrl.signal.aborted && setShelfProblem(problemOf(e)));
    proformaStatus(ctrl.signal)
      .then(setStatus)
      .catch((e: unknown) => !ctrl.signal.aborted && setStatusProblem(problemOf(e)));
    return () => ctrl.abort();
  }, []);

  // The binding: a held scenario by (b), one made here by its flowsheet (c);
  // with a fermOS fit chosen, either by (c) with the fits (OF-BLD-019 §5.1),
  // which binds a held scenario's flowsheet exactly as (b) does.
  const fitsKey = JSON.stringify(Object.entries(chosenFits).sort());
  useEffect(() => {
    const ctrl = new AbortController();
    setInfo(null);
    setBindProblem(null);
    const fits = Object.fromEntries(JSON.parse(fitsKey) as [string, string][]);
    const ask = { host };
    const bound =
      madeHere || Object.keys(fits).length > 0
        ? proformaBind(flowsheetId, { ...ask, fits, vessel: vesselId, trainRun: trainRunId }, ctrl.signal)
        : proformaScenarios(ask, ctrl.signal).then((all) => {
            const found = all.find((x) => x.id === scenario.id);
            if (!found) throw new Error(`The service binds no scenario ${scenario.id}: it is not among the BioSTEAM scenarios this service holds.`);
            return found;
          });
    bound.then(setInfo).catch((e: unknown) => !ctrl.signal.aborted && setBindProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [madeHere, flowsheetId, scenario.id, host, fitsKey, vesselId, trainRunId]);

  // The inputs as the parameter panel shows them (OF-BLD-020 §2.2): the
  // scenario's scope, bound by the service as a run binds it, a scenario made
  // here naming its flowsheet, with the host and the fits chosen.
  const ask = useMemo(
    () => ({
      flowsheet: madeHere ? flowsheetId : null,
      host,
      fits: Object.fromEntries(JSON.parse(fitsKey) as [string, string][]),
      // A composite's parts, as the run names them (OF-BLD-020 §6.1).
      ...(vesselId || trainRunId ? { vessel: vesselId, trainRun: trainRunId } : {}),
    }),
    [madeHere, flowsheetId, host, fitsKey, vesselId, trainRunId],
  );
  useEffect(() => {
    const ctrl = new AbortController();
    setPanel(null);
    setPanelProblem(null);
    paramScope(scope, ask, ctrl.signal)
      .then(setPanel)
      .catch((e: unknown) => !ctrl.signal.aborted && setPanelProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [scope, ask]);

  // The ceiling check (OF-BLD-019 §5.2, D11): the yield as this page binds
  // it (host, fits, and the yield's override when a person typed one),
  // read by the service against the newest stored geneOS ceilings.
  const yieldTyped = JSON.stringify(overrides.filter((o) => o.key === 'yield'));
  useEffect(() => {
    const ctrl = new AbortController();
    setCeiling(null);
    setCeilingProblem(null);
    const fits = Object.fromEntries(JSON.parse(fitsKey) as [string, string][]);
    ceilingCheck(
      { scenarioId: scenario.id, flowsheet: madeHere ? flowsheetId : null, host, fits, overrides: JSON.parse(yieldTyped) as typeof overrides },
      ctrl.signal,
    )
      .then(setCeiling)
      .catch((e: unknown) => !ctrl.signal.aborted && setCeilingProblem(problemOf(e)));
    return () => ctrl.abort();
  }, [madeHere, flowsheetId, scenario.id, host, fitsKey, yieldTyped]);


  // The newest run: the service's, which holds every run any browser, the
  // API or Postdoc made of this scenario (§3.R, findings 8 and 21), else the
  // one this browser kept (D6), read back from its artifact. `served` is
  // undefined until the service answers.
  const [served, setServed] = useState<Artifact | null | undefined>(undefined);
  useEffect(() => {
    const ctrl = new AbortController();
    proformaNewestRun(scenario.id, ctrl.signal)
      .then(setServed)
      .catch(() => !ctrl.signal.aborted && setServed(null));
    return () => ctrl.abort();
  }, [scenario.id]);
  const runId = newestRunId(served, scenario.lastRunId);
  useEffect(() => {
    setLoadProblem(null);
    if (!runId) return;
    if (served && served.id === runId) {
      const v = runViewOfArtifact(served);
      if (v) setView(v);
      else setLoadProblem(`${runId} is not a scenario run: it was kept by ${served.tool}.`);
      return;
    }
    const ctrl = new AbortController();
    proformaArtifact(runId, ctrl.signal)
      .then((art) => {
        const v = runViewOfArtifact(art);
        if (v) setView(v);
        else setLoadProblem(`${runId} is not a scenario run: it was kept by ${art.tool}.`);
      })
      .catch((e: unknown) => !ctrl.signal.aborted && setLoadProblem(problemOf(e)));
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, served]);

  // While a run is in hand: its seconds.
  useEffect(() => {
    if (!running) return;
    const t0 = Date.now();
    setElapsed(0);
    const tick = window.setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 1000);
    return () => window.clearInterval(tick);
  }, [running]);

  // While a run is in hand, or the simulator is starting, the worker's
  // status every few seconds: Run waits while it starts (§3.R, finding 7),
  // and comes back when it is ready.
  const starting = status?.status === 'starting';
  useEffect(() => {
    if (!running && !starting) return;
    const poll = window.setInterval(() => {
      proformaStatus()
        .then(setStatus)
        .catch(() => {
          /* the line keeps the last status it read */
        });
    }, 3000);
    return () => window.clearInterval(poll);
  }, [running, starting]);

  const flowsheet = shelf?.find((f) => f.id === flowsheetId) ?? null;

  // What the service bound, with this browser's overrides laid over every
  // input they name, records and fits included (OF-BLD-020 D3); the service
  // applies the same rule on the run, and the panel shows its own answer.
  const bound = useMemo<ProformaScenarioInfo | null>(() => {
    if (!info) return null;
    const by = new Map(overrides.filter((o) => typeof o.value === 'number').map((o) => [o.key, o]));
    const inputs = info.inputs.map((i): ScenarioInput => {
      const o = by.get(i.key);
      if (!o || typeof o.value !== 'number') return i;
      // One end typed, the other is the value; neither, held at the value (overrideEnds, as the service reads it).
      const ends = overrideEnds(o);
      const low = ends.low ?? o.value;
      const high = ends.high ?? o.value;
      return {
        ...i,
        binding: 'assumption',
        value: o.value,
        low,
        high,
        sampling: low === high ? 'fixed' : 'uniform',
        source: { kind: 'assumption', id: null, by: o.by, note: `typed on ${o.at}${o.note ? `: ${o.note}` : ''}` },
        records: [],
        recordIds: [],
      };
    });
    return { ...info, id: scenario.id, name: scenario.name, inputs, waiting: inputs.filter((i) => i.binding === 'waiting').map((i) => i.key) };
  }, [info, overrides, scenario.id, scenario.name]);

  // The inputs a person's value overrides, with the person: a fit chosen for one does not feed it (D3).
  const overridden = useMemo(
    () => Object.fromEntries(overrides.filter((o) => typeof o.value === 'number').map((o) => [o.key, o.by])) as Record<string, string>,
    [overrides],
  );

  const priceBasis = bound?.priceBasis || flowsheet?.priceBasis || 'on the basis its flowsheet states';
  const labels = inputLabels(bound?.inputs ?? null, flowsheet);
  const unitLabels = inputLabels(bound?.inputs ?? null, flowsheet, true);

  const go = () => {
    if (!bound) return;
    setRunning(true);
    setRunProblem(null);
    // The run carries the scope's overrides of the inputs its flowsheet
    // takes, and the fits of the inputs no override names (OF-BLD-020 D3).
    // A composite's Finance group is the scope's too (OF-BLD-020 §6.1): its
    // run carries every override of its scope, whether or not the panel has
    // answered, so a Finance value is never dropped while the scope loads or
    // after it failed (§6.R, main-15/26); the service splits and checks them.
    const finance = (panel?.specs ?? []).filter((sp) => sp.group === 'Finance').map((sp) => sp.key);
    const sent = scenarioRunOverrides(overrides, { inputs: bound.inputs.map((i) => i.key), finance, composite: !!parts });
    const fits = Object.fromEntries(Object.entries(chosenFits).filter(([k]) => bound.inputs.find((i) => i.key === k)?.binding === 'artifact'));
    runProformaScenario({
      scenarioId: scenario.id,
      flowsheet: madeHere ? flowsheetId : null,
      overrides: sent,
      host,
      fits,
      ...(parts ? { vessel: parts.vessel, trainRun: parts.trainRun } : {}),
    })
      .then((r) => {
        setView(runViewOfResult(r));
        // The index and this page read the newest run from its artifact (D6).
        recordScenarioRun(scenario.id, r.artifactId);
      })
      .catch((e: unknown) => setRunProblem(problemOf(e)))
      .finally(() => {
        setRunning(false);
        proformaStatus()
          .then(setStatus)
          .catch(() => {
            /* the line keeps the last status it read */
          });
      });
  };

  const questions = bound ? modellerQuestions(bound.inputs, view, flowsheetId) : [];

  return (
    <div data-testid="proforma-biosteam">
      <PageHeader
        eyebrow={`${flowsheetId} · BioSTEAM scenario`}
        title={scenario.name}
        subtitle={scenario.description || (flowsheet ? `${flowsheet.title}, from ${flowsheet.source}` : `Flowsheet ${flowsheetId}`)}
        actions={
          <>
            <Button onClick={() => togglePin(scenario.id)} title="Pin to compare" data-testid="scenario-pin" aria-pressed={scenario.pinned}>
              {scenario.pinned ? <Pin size={14} /> : <PinOff size={14} />}
              {scenario.pinned ? 'Pinned' : 'Pin'}
            </Button>
            <a className="btn" href={href('/biorepo/compare')} data-testid="compare-link">
              <GitCompare size={14} /> Compare
            </a>
            {view && (
              <a className="btn" href={href(trainPath({ scenarioId: null, artifactId: view.artifactId }))} data-testid="train-link">
                <Route size={14} /> pureOS train
              </a>
            )}
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2 mb-4 text-caption text-ink-soft" data-testid="scenario-meta">
        <span>
          Flowsheet: <span className="text-ink">{flowsheet ? flowsheet.title : flowsheetId}</span>
          {flowsheet && <>, from {flowsheet.source}</>}
        </span>
        <span>· {madeHere ? `made in this browser${scenario.createdAt ? ` ${stamp(scenario.createdAt)}` : ''}` : 'shipped with openFerment'}</span>
        {view ? <ProvenanceBadge p={view.provenance} /> : <span className="chip">not run yet</span>}
      </div>
      {parts && (
        <p className="mb-4 text-caption text-ink-soft" data-testid="scenario-parts" data-vessel={parts.vessel} data-train-run={parts.trainRun}>
          Built from a vessel and a train: the fermenter is vessel design{' '}
          <a className="font-num text-accent hover:underline" href={href(vesselDesignPath(parts.vessel))} data-testid="scenario-vessel-link">
            {parts.vessel}
          </a>
          , rebuilt as BioSTEAM&rsquo;s same class with every design parameter as the design holds it; the train is train run{' '}
          <a className="font-num text-accent hover:underline" href={href(trainRunPath(parts.trainRun))} data-testid="scenario-train-link">
            {parts.trainRun}
          </a>
          , its units with the values that run held, on the fermenter&rsquo;s beer (the train&rsquo;s own inlet is not an input).
        </p>
      )}

      {(shelfProblem || (shelf && !flowsheet)) && (
        <div className="mb-4">
          {shelfProblem && <Callout kind="warn">The shelf could not be read: {shelfProblem}</Callout>}
          {shelf && !flowsheet && (
            <Callout kind="warn">The service&rsquo;s shelf holds no flowsheet {flowsheetId}, so this scenario cannot run on it.</Callout>
          )}
        </div>
      )}

      <div className="space-y-4">
        {!view && !runId && served !== undefined && (
          <Card className="p-4" data-testid="scenario-not-run">
            <h2 className="font-serif text-section-title font-semibold mb-1">This scenario has not run yet</h2>
            <p className="text-body text-ink-soft">
              {madeHere
                ? `Made in this browser${scenario.createdAt ? ` on ${stamp(scenario.createdAt)}` : ''}. `
                : ''}
              Neither this browser nor the service holds a run of it. It holds no input value of its own: a run binds its process inputs to
              records and takes every other input from a named person&rsquo;s assumption. Give every input that waits a source, then run it.
            </p>
          </Card>
        )}

        <Card className="p-4">
          <div className="flex flex-wrap items-end justify-between gap-3 mb-2">
            <h2 className="font-serif text-section-title font-semibold">Inputs, and where each came from</h2>
            {bound && bound.hosts.length > 0 && (
              <label className="text-caption text-ink-soft">
                <span className="block mb-0.5">Host</span>
                <select className="input" aria-label="Host" value={host ?? ''} onChange={(e) => setHost(e.target.value || null)}>
                  <option value="">Every organism the binding reads</option>
                  {bound.hosts.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
          {flowsheet && <p className="text-caption text-ink-soft mb-2">{flowsheet.description}</p>}
          <p className="text-caption text-ink-soft mb-3">
            Records of an input&rsquo;s field pass the same gate statistics pass. Three or more give their median and range, sampled
            triangular; two a pair, sampled uniform; one is held fixed. Every other input is a named person&rsquo;s assumption, or a
            convention the run states.
          </p>
          {bindProblem && (
            <Callout kind="warn">
              <span data-testid="bind-problem">The service could not bind this scenario&rsquo;s inputs: {bindProblem}</span>
            </Callout>
          )}
          {panelProblem && (
            <Callout kind="warn">
              <span data-testid="panel-problem">The service could not serve this scenario&rsquo;s parameters: {panelProblem}</span>
            </Callout>
          )}
          {panel ? (
            <div data-testid="proforma-inputs">
              <ParameterPanel
                scope={scope}
                data={panel}
                request={ask}
                onRefused={setRefused}
                groups={PROFORMA_GROUPS}
                recordsOf={(key) => <RecordsChooser input={info?.inputs.find((i) => i.key === key)} />}
              />
              {Object.keys(chosenFits).length > 0 && (
                <p className="text-caption text-ink-soft">
                  {Object.entries(chosenFits).map(([key, id]) =>
                    key in overridden ? (
                      <span key={key} className="mr-3" data-testid="fit-line" data-key={key} data-overridden="true">
                        {labels[key] ?? key}: {overridden[key]}&rsquo;s value replaces the fermOS {fitWord(key)} <span className="font-num">{id}</span>, and the run
                        does not use the {fitWord(key)} here:{' '}
                        <button className="underline hover:text-accent min-h-[44px]" onClick={() => clearFit(scenario.id, key)} data-testid="fit-stop-input" data-key={key}>
                          stop using it here
                        </button>
                      </span>
                    ) : (
                      <span key={key} className="mr-3" data-testid="fit-line" data-key={key} data-overridden="false">
                        {labels[key] ?? key} from the fermOS {fitWord(key)} <span className="font-num">{id}</span>:{' '}
                        <button className="underline hover:text-accent min-h-[44px]" onClick={() => clearFit(scenario.id, key)} data-testid="fit-stop-input" data-key={key}>
                          stop using it here
                        </button>
                      </span>
                    ),
                  )}
                </p>
              )}
            </div>
          ) : (
            flowsheet &&
            (bindProblem || panelProblem) && (
              <table className="w-full text-body mt-2" data-testid="shelf-inputs">
                <thead>
                  <tr className="text-caption text-ink-soft text-left">
                    <th className="py-1 pr-2 font-medium">Input the flowsheet takes</th>
                    <th className="py-1 pr-2 font-medium">Dimension</th>
                    <th className="py-1 pr-2 font-medium">Unit</th>
                    <th className="py-1 font-medium">Where it comes from</th>
                  </tr>
                </thead>
                <tbody>
                  {flowsheet.inputs.map((i) => (
                    <tr key={i.key} className="border-t border-line/60 align-top">
                      <td className="py-1.5 pr-2">{i.name}</td>
                      <td className="py-1.5 pr-2 text-caption">{i.dimension}</td>
                      <td className="py-1.5 pr-2 font-num text-caption">{i.unit || 'share'}</td>
                      <td className="py-1.5 text-caption">{inputSourceWords(i)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          )}
          {flowsheet && flowsheet.inputs.some((i) => FIT_INPUTS.includes(i.key)) && (
            <FermosFitSlot
              flowsheetId={flowsheetId}
              chosen={chosenFits}
              overridden={overridden}
              onChoose={(fits) => setFits(scenario.id, fits)}
              onStop={(ids) =>
                Object.entries(chosenFits)
                  .filter(([, id]) => ids.includes(id))
                  .forEach(([key]) => clearFit(scenario.id, key))
              }
            />
          )}
          <div className="mt-3 text-caption text-ink-soft">
            <div>The price is {priceBasis}.</div>
            {(bound?.leavesOut ?? flowsheet?.leavesOut ?? []).length > 0 && (
              <div>What this flowsheet leaves out: {(bound?.leavesOut ?? flowsheet?.leavesOut ?? []).join('; ')}.</div>
            )}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button variant="primary" onClick={go} disabled={running || starting || !bound || bound.waiting.length > 0 || refused !== null}>
              <Play size={14} /> {running ? 'Simulating…' : view ? 'Run the scenario again' : 'Run the scenario'}
            </Button>
            <StatusLine status={status} problem={statusProblem} running={running} elapsed={elapsed} />
            {starting && !running && (
              <span className="text-caption text-ink-soft" data-testid="run-waits">
                Run waits until it has started; this line asks again every few seconds.
              </span>
            )}
          </div>
          {refused !== null && (
            <p className="text-caption text-signal-warn mt-2" data-testid="run-held">
              Run waits until the service takes these values, since a run of them would be refused in the same words: {refused}
            </p>
          )}
          {bound && bound.waiting.length > 0 && (
            <p className="text-caption text-signal-warn mt-2" data-testid="proforma-waiting">
              Waiting for a source: {bound.waiting.map((k) => bound.inputs.find((i) => i.key === k)?.label ?? k).join(', ')}.
            </p>
          )}
          {runProblem && (
            <div className="mt-2">
              <Callout kind="warn">
                <span data-testid="run-problem">The run was refused: {runProblem}</span>
              </Callout>
            </div>
          )}
          {view && <BasisAssumptions inputs={view.basis.inputs} labels={labels} />}
        </Card>

        <CeilingCheckSlot check={ceiling} problem={ceilingProblem} />

        {runId && loadProblem && !view && (
          <Callout kind="warn">
            Its newest run, {runId}, could not be read: {loadProblem}
          </Callout>
        )}

        {view && (
          <RunReport view={view} priceBasis={priceBasis} labels={labels} unitLabels={unitLabels} scenarioId={scenario.id} csvName={scenario.id} flowsheet={flowsheet} />
        )}

        {view && (
          <p className="text-caption text-ink-soft">
            pureOS reads this run&rsquo;s train, unit by unit:{' '}
            <a className="text-accent hover:underline" href={href(trainPath({ scenarioId: null, artifactId: view.artifactId }))}>
              pureOS → Train
            </a>
            .
          </p>
        )}

        {bound && (
          <Card className="p-4" data-testid="modeller-questions">
            <div className="flex items-center justify-between gap-2 mb-1">
              <h2 className="font-serif text-section-title font-semibold">Questions for a process modeller</h2>
              <Button onClick={() => exportText(`${scenario.id}-questions.txt`, questionsText(bound, view))}>
                <Download size={14} /> Export as text
              </Button>
            </div>
            <p className="text-caption text-ink-soft mb-2">
              The inputs that rest on an assumption, the strongest mover first once a run has ranked them, and what the flowsheet leaves out.
            </p>
            <ol className="list-decimal pl-5 space-y-1 text-body">
              {questions.map((q) => (
                <li key={q.key}>
                  <span className="font-medium">{q.label}</span>
                  {q.rho != null && <span className="font-num text-caption text-ink-soft"> (ρ {fmt(q.rho, 2)})</span>}: {q.question}
                </li>
              ))}
            </ol>
            <ul className="list-disc pl-5 mt-2 text-caption text-ink-soft">
              {bound.leavesOut.map((l) => (
                <li key={l}>left out: {l}</li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </div>
  );
}

/** The order the panel shows a scenario's inputs in: the shelf's kinds (params._GROUPS). */
// OF-BLD-020 §6.1: a composite's TEA parameters follow, as the group Finance.
const PROFORMA_GROUPS = ['Process', 'Economics', 'Conventions', 'Finance'];
const EMPTY_FITS: Record<string, string> = {};
/** The inputs a fermOS fit can feed (proforma.FIT_KEYS). */
const FIT_INPUTS = ['titre', 'yield', 'productivity'];

/** A BioSTEAM scenario the service simulates, by its id. */
export default function ProformaScenario({ scenarioId }: { scenarioId: string }) {
  const scenario = useStore((s) => s.scenarios.find((x) => x.id === scenarioId));
  const madeHere = useStore((s) => s.createdScenarioIds.includes(scenarioId));
  const durableReady = useStore((s) => s.durableReady);
  // A scenario made here lives in this browser's Durable tier, which is read
  // just after the page loads: a deep link waits for it rather than say the
  // scenario does not exist.
  if (!scenario && !durableReady && durableAvailable())
    return <p className="text-body text-ink-soft">Reading the scenarios kept in this browser…</p>;
  if (scenario?.kind !== 'biosteam')
    return (
      <EmptyState
        title="Scenario not found"
        body={`No BioSTEAM scenario with id ${scenarioId} exists in this session.`}
        action={<Button onClick={() => navigate('/proforma')}>Back to Proforma</Button>}
      />
    );
  return <BiosteamScenario key={scenario.id} scenario={scenario} madeHere={madeHere} />;
}
