// Home (OF-DES-001 §8.1) — orient any persona in five seconds: what is in the
// corpus, where you left off, and what to do next. Three bands plus a rail.
import React, { useMemo, useState, type ReactNode } from 'react';
import {
  AlertTriangle,
  ArrowUpRight,
  Award,
  BookOpen,
  Check,
  CircleDot,
  ClipboardList,
  Clock,
  Compass,
  Download,
  FileText,
  FlaskConical,
  GraduationCap,
  LineChart,
  MessagesSquare,
  Pencil,
  Pin,
  Play,
  Search,
  Table2,
  Upload,
  type LucideIcon,
} from 'lucide-react';
import { useStore, provenanceOf } from '@/store';
import { href } from '@/router';
import { Bar, Card, EmptyState, Explain, PageHeader, SectionTitle } from '@/components/ui';
import { ProvDot, ProvenanceLegend, Tick, type ProvKind } from '@/components/Provenance';
import { DemoSuiteBand } from '@/components/demo/DemoSuiteBand';
import { blastRadius } from '@/engine/stale';
// Two adapters, not one, because the two tiles below are answered by two
// subsystems. The gold-set plan is BioRepo's — every row of it is a paper id,
// an ontology field list and a record count, and Audit owns the SCORE rather
// than the SET (`CorpusAdapter.getGoldSetPlan`). Designs are fermOS's, because
// a design is the output of the tier cascade (`DesignDetail`).
import { adapters } from '@/adapters';
import { useAdapterData } from '@/adapters/react';

// ── helpers ────────────────────────────────────────────────────────────

/** Most common provenance in a list — the tick a summary tile should wear. */
function dominant(list: ProvKind[], fallback: ProvKind): ProvKind {
  const counts = new Map<ProvKind, number>();
  for (const p of list) counts.set(p, (counts.get(p) ?? 0) + 1);
  const ranked = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  return ranked.length > 0 ? ranked[0][0] : fallback;
}

/** A failing tile degrades to a labelled error card; the page never dies (§9.7). */
class TileBoundary extends React.Component<
  { label: string; children: ReactNode },
  { error: Error | null }
> {
  constructor(props: { label: string; children: ReactNode }) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div className="card p-3 border-signal-error/40">
          <div className="text-caption uppercase tracking-wide text-ink-soft">
            {this.props.label}
          </div>
          <div className="mt-1 flex items-start gap-1.5 text-body text-signal-error">
            <AlertTriangle size={14} className="mt-[3px] shrink-0" />
            <span>This tile could not be computed.</span>
          </div>
          <div className="text-caption text-ink-soft mt-1 break-words">
            {this.state.error.message}
          </div>
          <button className="btn btn-sm mt-2" onClick={() => this.setState({ error: null })}>
            Retry
          </button>
        </div>
      );
    }
    return <>{this.props.children}</>;
  }
}

function VitalTile({
  to,
  label,
  prov,
  tickTitle,
  children,
  sub,
}: {
  to: string;
  label: string;
  prov: ProvKind;
  tickTitle?: string;
  children: ReactNode;
  sub?: ReactNode;
}) {
  return (
    <a
      href={href(to)}
      className="card p-3 block transition-colors hover:border-accent/45 hover:bg-accent-wash/40"
    >
      <Tick p={prov} title={tickTitle} className="h-full">
        <div className="flex items-start justify-between gap-2">
          <div className="text-caption uppercase tracking-wide text-ink-soft">{label}</div>
          <ArrowUpRight size={13} className="text-ink-soft shrink-0" aria-hidden />
        </div>
        <div className="mt-1">{children}</div>
        {sub && <div className="text-caption text-ink-soft mt-1.5">{sub}</div>}
      </Tick>
    </a>
  );
}

function ResumeCard({
  to,
  kicker,
  title,
  meta,
  prov,
  children,
}: {
  to: string;
  kicker: string;
  title: string;
  meta?: ReactNode;
  prov: ProvKind;
  children?: ReactNode;
}) {
  return (
    <a
      href={href(to)}
      className="card p-3 block transition-colors hover:border-accent/45 hover:bg-accent-wash/40"
    >
      <Tick p={prov} className="h-full">
        <div className="flex items-start justify-between gap-2">
          <div className="text-caption uppercase tracking-wide text-ink-soft">{kicker}</div>
          <ArrowUpRight size={13} className="text-ink-soft shrink-0" aria-hidden />
        </div>
        <div className="text-body font-medium mt-0.5 leading-snug">{title}</div>
        {meta && <div className="text-caption text-ink-soft mt-0.5">{meta}</div>}
        {children && <div className="mt-2">{children}</div>}
      </Tick>
    </a>
  );
}

const ACTIVITY_ICONS: Record<string, LucideIcon> = {
  download: Download,
  export: Download,
  upload: Upload,
  ingest: Upload,
  check: Check,
  verified: Check,
  review: Check,
  edit: Pencil,
  pencil: Pencil,
  gold: Award,
  award: Award,
  star: Award,
  flask: FlaskConical,
  organism: FlaskConical,
  protocol: ClipboardList,
  run: Play,
  play: Play,
  table: Table2,
  extract: Table2,
  paper: FileText,
  file: FileText,
  book: BookOpen,
  learn: GraduationCap,
  lesson: GraduationCap,
  message: MessagesSquare,
  ask: MessagesSquare,
  chat: MessagesSquare,
  chart: LineChart,
  simulate: LineChart,
  search: Search,
  clock: Clock,
  timer: Clock,
  alert: AlertTriangle,
  warn: AlertTriangle,
  pin: Pin,
};

const ENTRY_CARDS: { to: string; title: string; desc: string; Icon: LucideIcon }[] = [
  {
    to: '/ask',
    title: 'Ask a question',
    desc: 'Get a cited answer with the plan, tool calls and retrieved passages shown.',
    Icon: MessagesSquare,
  },
  {
    to: '/extract/review',
    title: 'Review extractions',
    desc: 'Triage machine-extracted parameters against the span they came from.',
    Icon: Table2,
  },
  {
    to: '/protocols',
    title: 'Run a protocol',
    desc: 'Scale a verified procedure to your batch size and execute it at the bench.',
    Icon: ClipboardList,
  },
  {
    to: '/simulate',
    title: 'Model a process',
    desc: 'Sweep a scenario and see where the cost per kilogram actually goes.',
    Icon: LineChart,
  },
];

const COLD_START_QUESTIONS = [
  'What specific growth rate does Chlorella vulgaris reach in mixotrophic culture?',
  'Which strain in the corpus has the highest reported protein content, and how was it measured?',
  'How does harvest recovery differ between centrifugation and membrane filtration?',
];

// ── screen ─────────────────────────────────────────────────────────────

export default function Home() {
  const papers = useStore((s) => s.papers);
  const records = useStore((s) => s.records);
  const contradictions = useStore((s) => s.contradictions);
  const disputed = papers.filter((p) => p.coverageDisputed).length;

  // Both reads feed COUNTS inside two tiles, not the page's structure, so
  // Home does not gate on them — the corpus vitals, the work rail and the
  // contradictions are all live while these are in flight. A count that has
  // not arrived renders as an em dash, which is this design system's mark for
  // a value that is not known. It is NOT rendered as `0`: zero designs and
  // zero planned gold records are both statements this build would be making
  // falsely, and they are exactly the statements these tiles exist to get
  // right. The tiles already sit inside `TileBoundary`, so a rejected read
  // degrades this section and never the page.
  const designs = useAdapterData(() => adapters.process.listDesigns(), []);
  const goldSet = useAdapterData(() => adapters.corpus.getGoldSetPlan(), []);
  const designCount = designs.status === 'ready' ? designs.data.length : null;
  const goldPlan = goldSet.status === 'ready' ? goldSet.data : null;
  /** An unknown count, spelled the way the rest of the build spells one. */
  const UNKNOWN = '—';

  // Executable-layer coverage (OF-FE-004 §1.2). A true statement about the
  // corpus that belongs on the screen: hiding it would be the same error as
  // fabricating an F1.
  const protocols = useStore((s) => s.protocols);
  const scenarios = useStore((s) => s.scenarios);

  const { wiredRecords, wiredFields } = useMemo(() => {
    const src = { protocols, scenarios };
    const ids = records.filter((r) => blastRadius(r.id, src) > 0).map((r) => r.id);
    const fields = new Set(
      records.filter((r) => ids.includes(r.id)).map((r) => r.field),
    );
    return { wiredRecords: ids.length, wiredFields: fields.size };
  }, [records, protocols, scenarios]);
  const sessions = useStore((s) => s.sessions);
  const activity = useStore((s) => s.activity);
  const runs = useStore((s) => s.runs);
  const activeRunId = useStore((s) => s.activeRunId);
  const reviewQueue = useStore((s) => s.reviewQueue);
  const reviewIndex = useStore((s) => s.reviewIndex);

  const [showAllActivity, setShowAllActivity] = useState(false);

  // ── band 1 numbers ───────────────────────────────────────────────────
  const ingested = useMemo(() => papers.filter((p) => p.ingest === 'complete'), [papers]);

  const status = useMemo(() => {
    let verified = 0;
    let unverified = 0;
    let rejected = 0;
    for (const r of records) {
      if (r.status === 'verified') verified++;
      else if (r.status === 'rejected') rejected++;
      else unverified++;
    }
    return { verified, unverified, rejected, total: records.length };
  }, [records]);

  const recordProv = useMemo(
    () => dominant(records.map((r) => provenanceOf(r) as ProvKind), 'unverified'),
    [records],
  );

  const goldRecords = useMemo(() => records.filter((r) => r.gold), [records]);
  const goldPapers = useMemo(
    () => new Set(goldRecords.map((r) => r.paperId)).size,
    [goldRecords],
  );

  const versionCount = useMemo(
    () => protocols.reduce((n, p) => n + p.versions.length, 0),
    [protocols],
  );

  // Protocols inherit the provenance of the records their materials are bound to.
  const protocolProv = useMemo(() => {
    const byId = new Map(records.map((r) => [r.id, r]));
    const provs: ProvKind[] = [];
    for (const p of protocols) {
      const v = p.versions.find((x) => x.version === p.currentVersion) ?? p.versions[0];
      if (!v) continue;
      for (const m of v.materials) {
        const rec = m.sourceRecordId ? byId.get(m.sourceRecordId) : undefined;
        provs.push(rec ? (provenanceOf(rec) as ProvKind) : 'demo');
      }
    }
    return dominant(provs, 'demo');
  }, [protocols, records]);

  // ── band 2 state ─────────────────────────────────────────────────────
  const lastSession = sessions.length > 0 ? sessions[0] : null;
  const pinnedScenarios = useMemo(() => scenarios.filter((x) => x.pinned), [scenarios]);
  const activeRun = activeRunId ? (runs[activeRunId] ?? null) : null;
  const activeProtocol = activeRun
    ? (protocols.find((p) => p.id === activeRun.protocolId) ?? null)
    : null;
  const activeVersion = activeProtocol
    ? (activeProtocol.versions.find((v) => v.version === activeRun!.version) ??
      activeProtocol.versions[activeProtocol.versions.length - 1])
    : null;
  const runDone = activeRun ? Object.keys(activeRun.completed).length : 0;
  const runTotal = activeVersion ? activeVersion.steps.length : 0;

  const unverifiedCount = status.unverified;
  const queueRemaining = Math.max(0, reviewQueue.length - reviewIndex);

  const hasWork =
    lastSession !== null ||
    reviewQueue.length > 0 ||
    activeRun !== null ||
    pinnedScenarios.length > 0;

  const shownActivity = showAllActivity ? activity : activity.slice(0, 12);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0">
        <PageHeader
          eyebrow="openFerment"
          title="Bioprocess literature you can operate on"
          subtitle="Ask questions against a curated corpus, verify every extracted number against its source span, turn verified parameters into runnable protocols, and model what they cost at scale."
        />

        {/* ── Band 1 · Corpus vitals ─────────────────────────────────── */}
        <section aria-labelledby="home-vitals" className="mb-7">
          <SectionTitle
            right={
              <Explain label="What do the tick marks mean?">
                Every number in openFerment carries a provenance tick: a solid gold bar for
                curated gold-set values, green for human-verified extractions, grey for
                unverified machine output, and a dashed amber bar for demonstration data with
                no literature ancestry. The tiles below wear the dominant tick of the data
                behind them.
              </Explain>
            }
          >
            <span id="home-vitals">Corpus vitals</span>
          </SectionTitle>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <TileBoundary label="Papers catalogued">
              <VitalTile
                to="/trawl"
                label="Papers catalogued"
                prov="curated"
                tickTitle="Real literature, curated by hand — metadata and a curator note, no full text retrieved"
                sub={
                  papers.length === 0 ? (
                    'No corpus loaded'
                  ) : (
                    <>
                      <span className="font-num">{ingested.length}</span> of{' '}
                      <span className="font-num">{papers.length}</span> have full text
                    </>
                  )
                }
              >
                {/* The headline is what the label says it is. Showing 0/132 under
                    "Papers catalogued" read as "none catalogued", when in fact
                    all 132 are catalogued and none has full text — the opposite
                    of the intended claim. */}
                <div className="font-num text-display leading-tight">{papers.length}</div>
              </VitalTile>
            </TileBoundary>

            <TileBoundary label="Extraction records">
              <VitalTile
                to="/extract"
                label="Extraction records"
                prov={recordProv}
                sub={
                  <span className="flex flex-wrap items-center gap-x-3 gap-y-0.5">
                    <span className="inline-flex items-center gap-1.5">
                      <ProvDot p="verified" />
                      verified <span className="font-num">{status.verified}</span>
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <ProvDot p="unverified" />
                      unverified <span className="font-num">{status.unverified}</span>
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <ProvDot p="rejected" />
                      rejected <span className="font-num">{status.rejected}</span>
                    </span>
                  </span>
                }
              >
                <div className="font-num text-display leading-tight">{status.total}</div>
                <div
                  className="mt-1.5 flex h-2 w-full overflow-hidden rounded-full bg-ink-soft/15"
                  role="img"
                  aria-label={`${status.total} extraction records: ${status.verified} verified, ${status.unverified} unverified, ${status.rejected} rejected`}
                >
                  {status.total > 0 && (
                    <>
                      <div
                        className="h-full bg-accent"
                        style={{ width: `${(status.verified / status.total) * 100}%` }}
                      />
                      <div
                        className="h-full bg-ink-soft/55"
                        style={{ width: `${(status.unverified / status.total) * 100}%` }}
                      />
                      <div
                        className="h-full bg-signal-error"
                        style={{ width: `${(status.rejected / status.total) * 100}%` }}
                      />
                    </>
                  )}
                </div>
              </VitalTile>
            </TileBoundary>

            <TileBoundary label="Gold set">
              <VitalTile
                to="/extract/validation"
                label="Gold set"
                prov="gold"
                sub={
                  goldRecords.length === 0 ? (
                    'No curated values yet — flag records with g in review'
                  ) : (
                    <>
                      across <span className="font-num">{goldPapers}</span>{' '}
                      {goldPapers === 1 ? 'paper' : 'papers'} · the evaluation baseline
                    </>
                  )
                }
              >
                <div className="font-num text-display leading-tight">{goldRecords.length}</div>
              </VitalTile>
            </TileBoundary>

            <TileBoundary label="Protocols published">
              <VitalTile
                to="/protocols"
                label="Protocols published"
                prov={protocolProv}
                sub={
                  <>
                    <span className="font-num">{versionCount}</span>{' '}
                    {versionCount === 1 ? 'version' : 'versions'} in total
                  </>
                }
              >
                <div className="font-num text-display leading-tight">{protocols.length}</div>
              </VitalTile>
            </TileBoundary>
          </div>

          <div className="mt-3">
            <ProvenanceLegend />
          </div>
        </section>

        {/* ── Band 1b · Trust and contradictions (OF-FE-003 §8.1) ────── */}
        <section aria-labelledby="home-trust" className="mb-7">
          <SectionTitle>
            <span id="home-trust">Trust</span>
          </SectionTitle>
          <p className="text-caption text-ink-soft mb-2.5 max-w-3xl">
            What this build has not measured, on the face of the screen rather than behind a
            click. Leading with the weakness is what makes the rest of it credible.
          </p>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <Card className="p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft">
                Extraction quality
              </div>
              <div className="mt-1.5 text-body">
                <span className="text-signal-warn font-medium">Unmeasured.</span> No extractor has
                been run against this corpus, so there is no precision, recall or F1 to report.
              </div>
              <div className="text-caption text-ink-soft mt-1.5">
                <span className="font-num">
                  {goldPlan ? goldPlan.entries.reduce((n, g) => n + g.records, 0) : UNKNOWN}
                </span>{' '}
                records are planned for the gold set across{' '}
                <span className="font-num">{goldPlan ? goldPlan.entries.length : UNKNOWN}</span>{' '}
                sources, and{' '}
                <span className="font-num">
                  {goldPlan ? goldPlan.difficultyCases.length : UNKNOWN}
                </span>{' '}
                cases were chosen to be hard.{' '}
                <a href={href('/assay')} className="text-accent hover:underline">
                  Open Assay
                </a>
              </div>
              <div className="text-caption text-ink-soft mt-1.5 pt-1.5 border-t border-line">
                <span className="font-num text-ink">{wiredRecords}</span> of{' '}
                <span className="font-num">{records.length}</span> records feed something
                executable — a protocol or a scenario.{' '}
                <span className="font-num text-ink">{wiredFields}</span> of{' '}
                <span className="font-num">24</span> parameters are wired; the rest are
                catalogued only. The corpus is broad and the executable layer is narrow, and
                that gap is the work.
              </div>
              <div className="text-caption text-ink-soft mt-1.5">
                Recall is the harder half and is not measured at all: nothing counts what was
                never extracted. The only signal is a reader filing{' '}
                <span className="text-ink">“Something’s missing”</span> on a source
                {disputed > 0 ? (
                  <>
                    {' '}— <span className="font-num text-signal-warn">{disputed}</span> filed so
                    far.
                  </>
                ) : (
                  <>, and none has been filed yet.</>
                )}
              </div>
            </Card>

            <Card className="p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft">
                Contradictions
              </div>
              {contradictions.length === 0 ? (
                <div className="mt-1.5 text-body text-ink-soft">
                  The referee found no set of records that violates a constraint. That is a
                  statement about the checks that exist, not a claim the corpus agrees with itself.
                </div>
              ) : (
                <>
                  <div className="mt-1.5 text-body">
                    <span className="font-num text-signal-error">{contradictions.length}</span> open
                    — sets of records that cannot all be true.
                  </div>
                  <div className="mt-2 space-y-1.5">
                    {contradictions.slice(0, 2).map((c) => (
                      <div key={c.id} className="text-caption border-l-2 border-signal-error pl-2">
                        {c.statement}
                      </div>
                    ))}
                  </div>
                  <div className="text-caption text-ink-soft mt-2">
                    <a href={href('/ledger/contradictions')} className="text-accent hover:underline">
                      Open the queue
                    </a>
                  </div>
                </>
              )}
              <div className="text-caption text-ink-soft mt-2.5 pt-2 border-t border-line">
                Designs and scope are not built in this build, so the Bench has no panel for
                them rather than an empty one.
              </div>
            </Card>
          </div>
        </section>

        {/* ── Band 1c · Designs and Scope (OF-FE-004 §4) ─────────────── */}
        <section aria-labelledby="home-designs" className="mb-7">
          <SectionTitle>
            <span id="home-designs">Designs and scope</span>
          </SectionTitle>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <Card className="p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft">Designs</div>
              <div className="mt-1.5 text-body">
                <span className="font-num text-ink">{designCount ?? UNKNOWN}</span> points from
                the authored sweep grids, each carrying a four-tier cascade.
              </div>
              <div className="text-caption text-ink-soft mt-1.5">
                Every one reads <span className="font-mono">T0 ✓ · T1 — · T2 — · T3 ✓</span>: the
                economics were modelled and the biology was not checked. T1 needs a genome-scale
                model and T2 a reactor model, and neither is in this build, so both render absent
                rather than passed.{' '}
                <a href={href('/fermos/d')} className="text-accent hover:underline">
                  Open designs
                </a>
              </div>
            </Card>

            <Card className="p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft">Scope</div>
              <div className="mt-1.5 text-body">
                <span className="font-num text-signal-warn">0</span> of{' '}
                <span className="font-num">{designCount ?? UNKNOWN}</span> designs have been
                evaluated against a patent claim.
              </div>
              <div className="text-caption text-ink-soft mt-1.5">
                Parchment holds six real patents and no parsed claim bounds, so nothing can be
                tested yet. A design showing <span className="font-mono">clear</span> means
                unevaluated, not unencumbered — the field to read is{' '}
                <span className="font-mono">scopeEvaluated</span>.{' '}
                <a href={href('/parchment')} className="text-accent hover:underline">
                  Open Parchment
                </a>
              </div>
            </Card>
          </div>
        </section>

        {/* ── Band 2 · Your work / cold start ────────────────────────── */}
        <section aria-labelledby="home-work" className="mb-7">
          <SectionTitle>
            <span id="home-work">{hasWork ? 'Your work' : 'Three good first questions'}</span>
          </SectionTitle>

          {hasWork ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {lastSession && (
                <ResumeCard
                  to={`/ask/${lastSession.id}`}
                  kicker="Last conversation"
                  title={lastSession.title}
                  prov="user"
                  meta={
                    <>
                      <span className="font-num">{lastSession.messages.length}</span>{' '}
                      {lastSession.messages.length === 1 ? 'message' : 'messages'} ·{' '}
                      <span className="font-num">{lastSession.startedAt}</span>
                      {lastSession.scope && ` · scoped to ${lastSession.scope.label}`}
                    </>
                  }
                />
              )}

              {reviewQueue.length > 0 ? (
                <ResumeCard
                  to="/extract/review"
                  kicker="Review queue"
                  title={`${queueRemaining} of ${reviewQueue.length} remaining`}
                  prov="user"
                  meta="Pick up where you stopped — a accept, r reject, e edit, g gold"
                >
                  <Bar value={reviewIndex} max={Math.max(1, reviewQueue.length)} />
                </ResumeCard>
              ) : (
                <ResumeCard
                  to="/extract/review"
                  kicker="Review queue"
                  title={
                    unverifiedCount === 0
                      ? 'Nothing left unverified'
                      : `${unverifiedCount} unverified records waiting`
                  }
                  prov="unverified"
                  meta={
                    unverifiedCount === 0
                      ? 'Every extraction has been decided. Open the queue to re-check any of them.'
                      : 'Start a queue and triage them one span at a time.'
                  }
                />
              )}

              {activeRun && activeProtocol && (
                <ResumeCard
                  to={`/runbook/${activeRun.protocolId}/run/${activeRun.id}`}
                  kicker="Run in progress"
                  title={activeProtocol.title}
                  prov="user"
                  meta={
                    <>
                      step <span className="font-num">{Math.min(runDone + 1, runTotal || 1)}</span>{' '}
                      of <span className="font-num">{runTotal}</span> · v
                      <span className="font-num">{activeRun.version}</span> ·{' '}
                      <span className="font-num">{activeRun.scale}×</span> batch
                    </>
                  }
                >
                  <Bar value={runDone} max={Math.max(1, runTotal)} />
                </ResumeCard>
              )}

              {pinnedScenarios.length > 0 && (
                <ResumeCard
                  to="/simulate/compare"
                  kicker="Pinned scenarios"
                  title={pinnedScenarios.map((s) => s.name).join(' · ')}
                  prov="demo"
                  meta={
                    <>
                      <span className="font-num">{pinnedScenarios.length}</span> pinned — open the
                      comparison. Demo model v0 — illustrative economics, not validated.
                    </>
                  }
                />
              )}
            </div>
          ) : (
            <>
              <p className="text-body text-ink-soft mb-3 max-w-2xl">
                Nothing is in progress yet. These three questions each land on evidence the
                corpus can actually answer, and every number in the answer resolves to a source
                span.
              </p>
              <ul className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {COLD_START_QUESTIONS.map((q) => (
                  <li key={q}>
                    <a
                      href={href(`/ask?q=${encodeURIComponent(q)}`)}
                      className="card p-3 h-full flex flex-col gap-2 transition-colors hover:border-accent/45 hover:bg-accent-wash/40"
                    >
                      <MessagesSquare size={15} className="text-accent shrink-0" aria-hidden />
                      <span className="font-serif text-reading leading-snug">{q}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        {/* ── Band 3 · Start something ───────────────────────────────── */}
        <section aria-labelledby="home-start">
          <SectionTitle>
            <span id="home-start">Start something</span>
          </SectionTitle>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {ENTRY_CARDS.map((c) => (
              <a
                key={c.to}
                href={href(c.to)}
                className="card p-4 flex items-start gap-3 transition-colors hover:border-accent/45 hover:bg-accent-wash/40"
              >
                <span className="w-9 h-9 rounded-btn bg-accent/10 border border-accent/25 grid place-items-center shrink-0">
                  <c.Icon size={17} className="text-accent" aria-hidden />
                </span>
                <span className="min-w-0">
                  <span className="block font-serif text-section-title font-semibold leading-snug">
                    {c.title}
                  </span>
                  <span className="block text-body text-ink-soft mt-0.5">{c.desc}</span>
                </span>
              </a>
            ))}
          </div>

          <button
            className="mt-3 inline-flex items-center gap-1.5 text-body text-ink-soft hover:text-accent"
            onClick={() => useStore.getState().setUI({ tourStop: 0 })}
          >
            <Compass size={14} aria-hidden />
            What is this platform?
          </button>
        </section>

        {/* The second pool. A component rather than a section written here,
            because `Home` reads the corpus through the adapter seam and the
            demo pool reads its modules directly. */}
        <DemoSuiteBand />
      </div>

      {/* ── Right rail · recent activity ─────────────────────────────── */}
      <aside className="min-w-0" aria-labelledby="home-activity">
        <SectionTitle>
          <span id="home-activity">Recent activity</span>
        </SectionTitle>
        <Card className="p-0 overflow-hidden">
          {activity.length === 0 ? (
            <EmptyState
              title="No activity yet"
              body="Ingests, review decisions, runs and exports land here as you work. Nothing is recorded outside this browser session."
              icon={<Clock size={20} aria-hidden />}
            />
          ) : (
            <>
              <ul className="divide-y divide-line">
                {shownActivity.map((e, i) => {
                  const Icon = ACTIVITY_ICONS[e.icon] ?? CircleDot;
                  const link = e.href
                    ? e.href.startsWith('#')
                      ? e.href
                      : `#${e.href}`
                    : undefined;
                  return (
                    <li key={`${e.at}-${e.text}-${i}`} className="px-3 py-2">
                      <Tick p={e.provenance}>
                        <div className="flex items-start gap-2">
                          <Icon
                            size={13}
                            className="text-ink-soft mt-[3px] shrink-0"
                            aria-hidden
                          />
                          <div className="min-w-0 flex-1">
                            {link ? (
                              <a
                                href={link}
                                className="text-body leading-snug hover:text-accent hover:underline"
                              >
                                {e.text}
                              </a>
                            ) : (
                              <span className="text-body leading-snug">{e.text}</span>
                            )}
                            <div className="text-caption text-ink-soft font-num mt-0.5">
                              {e.at}
                            </div>
                          </div>
                        </div>
                      </Tick>
                    </li>
                  );
                })}
              </ul>
              {activity.length > 12 && (
                <div className="border-t border-line px-3 py-2">
                  <button
                    className="text-caption text-accent hover:underline"
                    onClick={() => setShowAllActivity((v) => !v)}
                    aria-expanded={showAllActivity}
                  >
                    {showAllActivity
                      ? 'Show recent 12'
                      : `Show all ${activity.length} events`}
                  </button>
                </div>
              )}
            </>
          )}
        </Card>
        <p className="text-caption text-ink-soft mt-2">
          Activity is session-only and resets on refresh.
        </p>
      </aside>
    </div>
  );
}
