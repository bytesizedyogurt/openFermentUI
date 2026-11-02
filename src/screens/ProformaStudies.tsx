// A project's studies (execution prompt §7.2, §9.1 step 5): /proforma/studies.
//
// What the project asked of its plants and kept of the answers, each list as
// the service holds it (studies/):
//
//   engine runs   every run of a library plant or a flowsheet, newest first,
//                 each a link to its page; two or more chosen are set side by
//                 side as a comparison (POST /api/studies/comparisons);
//   scenarios     a plant, its configuration and the values it sets, each a
//                 person's assumption or a model's estimate with its author,
//                 and the runs made of it; Run makes one more
//                 (POST /api/studies/scenarios/{id}/run);
//   comparisons   each a link to its page;
//   runbooks      the runbooks studies made from a run's outputs, each a link
//                 to the runbook's page, where it is locked;
//   the package   the export: study.json, study.md, each run's SFF file and the
//                 versions, one zip that opens without the service.
//
// Nothing here is typed as a number: a scenario's values are made where a
// person or Postdoc sets them, through the service.
import { useEffect, useState } from 'react';
import { BookOpen, Download, GitCompare, Play } from 'lucide-react';
import type { EngineRun, Runbook, StudyComparison, StudyScenario } from '@/data/types';
import { href, navigate } from '@/router';
import { useStore } from '@/store';
import { stamp } from '@/lib/proforma';
import {
  StudiesDown,
  compareRuns,
  downloadExport,
  listComparisons,
  listRuns,
  listScenarios,
  listStudyRunbooks,
  runScenario,
} from '@/lib/studies';
import { Button, Callout, Card, EmptyState, LinkButton, PageHeader } from '@/components/ui';
import { ProvenanceBadge } from '@/components/Provenance';
import { ORIGIN_WORDS } from '@/screens/ProformaRun';

const problemOf = (e: unknown) => (e instanceof StudiesDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

interface Held {
  runs: EngineRun[];
  scenarios: StudyScenario[];
  comparisons: StudyComparison[];
  runbooks: Runbook[];
}

const where = (plant: string, configuration: string | null) => plant + (configuration ? ` (${configuration})` : '');

function Runs({ runs, scenarios }: { runs: EngineRun[]; scenarios: StudyScenario[] }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const [chosen, setChosen] = useState<string[]>([]);
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const titles = new Map(scenarios.map((s) => [s.id, s.title]));
  const done = runs.filter((r) => r.status === 'done');
  const compare = () => {
    setBusy(true);
    setProblem(null);
    compareRuns({ title: title.trim(), runIds: chosen, by: reviewer })
      .then((rep) => navigate(`/proforma/comparisons/${rep.comparison.id}`))
      .catch((e: unknown) => setProblem(problemOf(e)))
      .finally(() => setBusy(false));
  };
  return (
    <Card className="p-4" data-testid="studies-runs">
      <h2 className="font-serif text-section-title font-semibold mb-1">Engine runs</h2>
      {runs.length === 0 ? (
        <EmptyState
          title="No engine run yet"
          body={
            <>
              A run is one library plant or openFerment flowsheet run whole by BioSTEAM, kept with its basis, its artifact and its SFF file. Running a scenario
              below makes one; so does the service&rsquo;s <span className="font-num">POST /api/library/&#123;plant&#125;/run</span>, and Postdoc runs the scenarios
              it proposes.
            </>
          }
        />
      ) : (
        <>
          <p className="text-caption text-ink-soft mb-2">Newest first. Choose two or more in the order a comparison should read them: each change is reckoned from the first chosen.</p>
          <div className="overflow-x-auto">
            <table className="w-full text-caption">
              <thead>
                <tr className="border-b border-line text-ink-soft">
                  {['', 'Run', 'Plant', 'Status', 'Provenance', 'Scenario', 'By', 'At'].map((h) => (
                    <th key={h} className="text-left py-1 pr-2 font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id} className="border-b border-line/50 align-top" data-testid="studies-run" data-status={r.status}>
                    <td className="py-1 pr-2">
                      {r.status === 'done' && (
                        <input
                          type="checkbox"
                          aria-label={`Compare run ${r.id}`}
                          checked={chosen.includes(r.id)}
                          onChange={(e) => setChosen((c) => (e.target.checked ? [...c, r.id] : c.filter((x) => x !== r.id)))}
                        />
                      )}
                      {chosen.includes(r.id) && <span className="font-num text-ink-soft ml-1">{chosen.indexOf(r.id) + 1}</span>}
                    </td>
                    <td className="py-1 pr-2">
                      <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/proforma/runs/${r.id}`)}>
                        {r.id}
                      </a>
                    </td>
                    <td className="py-1 pr-2">{where(r.plant, r.configuration)}</td>
                    <td className="py-1 pr-2">{r.status === 'done' ? 'done' : `refused: ${r.refused ?? ''}`}</td>
                    <td className="py-1 pr-2">{r.provenance ? <ProvenanceBadge p={r.provenance} compact /> : '—'}</td>
                    <td className="py-1 pr-2">{r.scenarioId ? (titles.get(r.scenarioId) ?? r.scenarioId) : '—'}</td>
                    <td className="py-1 pr-2">{r.by}</td>
                    <td className="py-1 pr-2 font-num">{stamp(r.at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {done.length >= 2 && (
            <div className="flex flex-wrap items-center gap-2 mt-2">
              <input className="input text-body" aria-label="The comparison's title" placeholder="What the comparison asks" value={title} onChange={(e) => setTitle(e.target.value)} />
              <Button variant="primary" disabled={busy || !reviewer || chosen.length < 2 || !title.trim()} onClick={compare} data-testid="studies-compare">
                <GitCompare size={14} /> Compare the {chosen.length >= 2 ? chosen.length : ''} chosen runs
              </Button>
              {!reviewer && <span className="text-caption text-ink-soft">A comparison is made in a person&rsquo;s name: set yours in Settings first.</span>}
            </div>
          )}
          {problem && <p className="text-caption text-signal-warn mt-1">{problem}</p>}
        </>
      )}
    </Card>
  );
}

function Scenarios({ scenarios }: { scenarios: StudyScenario[] }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const [busy, setBusy] = useState<string | null>(null);
  const [problem, setProblem] = useState<{ id: string; words: string } | null>(null);
  const run = (s: StudyScenario) => {
    setBusy(s.id);
    setProblem(null);
    runScenario(s.id, reviewer)
      .then((rep) => navigate(`/proforma/runs/${rep.run.id}`))
      .catch((e: unknown) => setProblem({ id: s.id, words: problemOf(e) }))
      .finally(() => setBusy(null));
  };
  return (
    <Card className="p-4" data-testid="studies-scenarios">
      <h2 className="font-serif text-section-title font-semibold mb-1">Scenarios</h2>
      {scenarios.length === 0 ? (
        <EmptyState
          title="No study scenario yet"
          body={
            <>
              A scenario names a plant, its configuration and the values it sets, each a named person&rsquo;s assumption or a model&rsquo;s estimate, checked
              against the plant&rsquo;s parameters. The service makes one (<span className="font-num">POST /api/studies/scenarios</span>), and Postdoc proposes
              them with each estimate labelled.
            </>
          }
        />
      ) : (
        <div className="space-y-3">
          {scenarios.map((s) => (
            <section key={s.id} className="border-t border-line/50 pt-2" data-testid="studies-scenario">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <div className="font-medium">{s.title}</div>
                  <div className="text-caption text-ink-soft">
                    <span className="font-num">{s.id}</span> · on {where(s.plant, s.configuration)} · made by {s.by}, {stamp(s.at)}
                    {s.note && <> · {s.note}</>}
                  </div>
                </div>
                <Button size="sm" disabled={!!busy || !reviewer} onClick={() => run(s)} data-testid="studies-scenario-run">
                  <Play size={12} /> {busy === s.id ? 'Running…' : 'Run'}
                </Button>
              </div>
              <table className="w-full text-caption mt-1">
                <tbody>
                  {s.values.map((v) => (
                    <tr key={v.key} className="border-b border-line/40 align-top" data-origin={v.quantity.origin?.kind}>
                      <td className="py-0.5 pr-2 font-num">{v.key}</td>
                      <td className="py-0.5 pr-2 font-num">
                        {String(v.quantity.value)} {v.quantity.unit}
                      </td>
                      <td className="py-0.5 pr-2">{ORIGIN_WORDS[v.quantity.origin?.kind ?? ''] ?? '—'}</td>
                      <td className="py-0.5 pr-2">{v.quantity.origin?.by ?? '—'}</td>
                      <td className="py-0.5 pr-2 text-ink-soft">{v.quantity.origin?.note ?? ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="text-caption text-ink-soft mt-1">
                Its runs:{' '}
                {s.runIds.length === 0
                  ? 'none yet'
                  : s.runIds.map((id, i) => (
                      <span key={id}>
                        {i > 0 && ', '}
                        <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/proforma/runs/${id}`)}>
                          {id}
                        </a>
                      </span>
                    ))}
                .{!reviewer && ' A run is asked for in a person’s name: set yours in Settings first.'}
              </p>
              {problem?.id === s.id && <p className="text-caption text-signal-warn mt-1">{problem.words}</p>}
            </section>
          ))}
        </div>
      )}
    </Card>
  );
}

export default function ProformaStudies() {
  const reviewer = useStore((s) => s.reviewer).trim();
  const [held, setHeld] = useState<Held | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportProblem, setExportProblem] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    Promise.all([listRuns(ctrl.signal), listScenarios(ctrl.signal), listComparisons(ctrl.signal), listStudyRunbooks(ctrl.signal)])
      .then(([runs, scenarios, comparisons, runbooks]) => setHeld({ runs, scenarios, comparisons, runbooks }))
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, []);

  const exportPackage = () => {
    setExporting(true);
    setExportProblem(null);
    downloadExport(reviewer)
      .catch((e: unknown) => setExportProblem(problemOf(e)))
      .finally(() => setExporting(false));
  };

  return (
    <div data-testid="proforma-studies">
      <PageHeader
        eyebrow="Proforma · studies"
        title="Studies"
        subtitle="What this project asked of its plants and kept of the answers: engine runs, the scenarios that asked for them, comparisons and runbooks, each as the service holds it."
        actions={
          <>
            <Button onClick={exportPackage} disabled={exporting} data-testid="studies-export">
              <Download size={14} /> {exporting ? 'Packing…' : 'The export package'}
            </Button>
            <LinkButton to="/proforma">
              <BookOpen size={14} /> Proforma
            </LinkButton>
          </>
        }
      />
      {exportProblem && (
        <div className="mb-4">
          <Callout kind="warn">{exportProblem}</Callout>
        </div>
      )}
      {problem && (
        <div className="mb-4">
          <Callout kind="warn">
            <span data-testid="studies-problem">{problem}</span>
          </Callout>
        </div>
      )}
      {held && (
        <div className="space-y-4">
          <Runs runs={held.runs} scenarios={held.scenarios} />
          <Scenarios scenarios={held.scenarios} />
          <Card className="p-4" data-testid="studies-comparisons">
            <h2 className="font-serif text-section-title font-semibold mb-1">Comparisons</h2>
            {held.comparisons.length === 0 ? (
              <p className="text-body text-ink-soft">No comparison yet: choose two or more runs above and compare them.</p>
            ) : (
              <ul className="space-y-1 text-body">
                {held.comparisons.map((c) => (
                  <li key={c.id} className="flex flex-wrap items-center gap-2" data-testid="studies-comparison">
                    <a className="underline underline-offset-2 hover:text-accent" href={href(`/proforma/comparisons/${c.id}`)}>
                      {c.title}
                    </a>
                    <ProvenanceBadge p={c.provenance} compact />
                    <span className="text-caption text-ink-soft">
                      {c.runIds.length} runs · {c.by || 'this browser'}, {stamp(c.at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card className="p-4" data-testid="studies-runbooks">
            <h2 className="font-serif text-section-title font-semibold mb-1">Runbooks</h2>
            {held.runbooks.length === 0 ? (
              <p className="text-body text-ink-soft">No study has made a runbook: a run&rsquo;s page makes one from its numbers.</p>
            ) : (
              <ul className="space-y-1 text-body">
                {held.runbooks.map((b) => (
                  <li key={b.id} className="flex flex-wrap items-center gap-2" data-testid="studies-runbook" data-locked={b.lockedAt ? 'true' : 'false'}>
                    <a className="underline underline-offset-2 hover:text-accent" href={href(`/runbooks/${b.id}`)}>
                      {b.title}
                    </a>
                    <span className="text-caption text-ink-soft">
                      {b.predictions.length} prediction{b.predictions.length === 1 ? '' : 's'} ·{' '}
                      {b.lockedAt ? (
                        <>
                          locked {stamp(b.lockedAt)} under <span className="font-num">{b.lockHash}</span>
                        </>
                      ) : (
                        'a draft, not locked'
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
