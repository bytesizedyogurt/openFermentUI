// The Bench (OF-DES-001 §8.1) — the front door.
//
// WHAT IT USED TO DO AND WHY THAT WAS WRONG. It opened with four "Corpus
// vitals" tiles, the first of which read "132 · 0 of 132 have full text". A
// stranger's first fact about this software was therefore a ratio of zero, on a
// dimension nobody had asked about; its own code comment conceded the tile "read
// as 'none catalogued'". Below it sat four bands of hedging, and the only
// introduction — "What is this platform?" — was a text button at the very
// bottom, under everything. Meanwhile the thirteen parts, which are the actual
// architecture, appeared nowhere on the page at all: a reader could not learn
// from this product what its parts were, only that it had a lot of screens.
//
// WHAT IT DOES NOW. It teaches by demonstration and then hands over the map, in
// that order, and it is SHORTER than what it replaced.
//
//   1. one real quantity, walked through its whole address — including the step
//      in the middle that has not happened, drawn the same size as the ones that
//      have, because that hole is the product's central claim;
//   2. the thirteen parts, grouped by movement, with what each owns and how much
//      of its upstream is code rather than intention;
//   3. the two object pools, side by side, with the rule that nothing crosses;
//   4. and only then what this build has not measured.
//
// Status is present, specific and never the lead. The right rail is the only
// part of the page that is about YOU, which is what lets the main column be the
// same for everyone and lets the page stop calling a seeded, back-dated,
// zero-message conversation "your work".
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
import { Bar, Card, EmptyState, PageHeader, SectionTitle, Skeleton, cx } from '@/components/ui';
import { Tick, type ProvKind } from '@/components/Provenance';
import { DemoPoolCard } from '@/components/demo/DemoPoolCard';
import { DemoFooter } from '@/components/demo/DemoFooter';
import { PartsMap } from '@/components/PartsMap';
import { ONTOLOGY, ONTOLOGY_BY_ID } from '@/data/ontology';
// The six flow triggers verbatim. A prompt on the front door must PLAY — the
// three questions that used to sit here scored zero against the matcher and
// were all declined, under a heading promising the opposite.
import { SUGGESTED_PROMPTS } from '@/sim/prompts';
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

/**
 * One step of the Bench's worked example.
 *
 * The heading names the OBJECT — the source, the record, the check, the model —
 * and the owning part sits under it as a label rather than as the link text.
 * Naming the step after a part would be a lie of navigation: boxes 01 and 02
 * both resolve to the paper reader under Intake, so a box labelled "Ledger"
 * would light the Intake rail entry and teach the reader that the parts are
 * decoration.
 *
 * `dashed` is for the step that has not happened. It gets no tick, because
 * there is no datum to carry one, and it does NOT get `.held` — that class
 * means "in the record and out of the statistic", which is a different claim.
 */
function TraceStep({
  n,
  what,
  part,
  to,
  prov,
  dashed,
  children,
}: {
  n: string;
  what: string;
  part: string;
  to: string;
  prov?: ProvKind;
  dashed?: boolean;
  children: ReactNode;
}) {
  const body = (
    <>
      <div className="flex items-baseline gap-1.5">
        <span className="font-num text-caption text-ink-soft">{n}</span>
        <span className="text-caption uppercase tracking-wide text-ink-soft">{what}</span>
        <ArrowUpRight size={12} className="text-ink-soft shrink-0 ml-auto" aria-hidden />
      </div>
      <div className="text-caption text-ink-soft">{part}</div>
      <div className="mt-1.5 text-body">{children}</div>
    </>
  );
  return (
    <a
      href={href(to)}
      className={cx(
        'card p-3 block transition-colors hover:border-accent/45 hover:bg-accent-wash/40',
        dashed && 'border-dashed',
      )}
    >
      {prov ? <Tick p={prov} className="h-full">{body}</Tick> : body}
    </a>
  );
}

/** A parameter's display name, or its id when the ontology has no entry. */
function fieldName(field: string): string {
  return ONTOLOGY_BY_ID[field as keyof typeof ONTOLOGY_BY_ID]?.name ?? field;
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

// ── screen ─────────────────────────────────────────────────────────────

export default function Home() {
  const papers = useStore((s) => s.papers);
  const records = useStore((s) => s.records);
  const contradictions = useStore((s) => s.contradictions);

  // Both reads feed COUNTS inside two tiles, not the page's structure, so
  // Home does not gate on them — the corpus vitals, the work rail and the
  // contradictions are all live while these are in flight. A count that has
  // not arrived renders as an em dash, which is this design system's mark for
  // a value that is not known. It is NOT rendered as `0`: zero designs and
  // zero planned gold records are both statements this build would be making
  // falsely, and they are exactly the statements these tiles exist to get
  // right. The tiles already sit inside `TileBoundary`, so a rejected read
  // degrades this section and never the page.
  const goldSet = useAdapterData(() => adapters.corpus.getGoldSetPlan(), []);
  const goldPlan = goldSet.status === 'ready' ? goldSet.data : null;

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

  // Protocols inherit the provenance of the records their materials are bound to.

  // ── band 2 state ─────────────────────────────────────────────────────
  const lastSession = sessions.length > 0 ? sessions[0] : null;
  // Only a conversation you actually had. The seeded sessions are back-dated
  // and empty, and offering one as "where you left off" tells a first-time
  // reader they did something they did not.
  const resumableSession = lastSession && lastSession.messages.length > 0 ? lastSession : null;
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
    resumableSession !== null ||
    reviewQueue.length > 0 ||
    activeRun !== null ||
    pinnedScenarios.length > 0;

  // ── the worked example ───────────────────────────────────────────────
  //
  // CHOSEN, NOT DERIVED, and said so on the page. An earlier draft claimed a
  // rule selected this chain; the rule, implemented, returns a different record
  // whose story has no range in it. A fabricated derivation on the page whose
  // thesis is that every number has an address would be the worst available
  // error, so the ids are named here and the copy calls it a teaching example.
  //
  // WHY THIS ONE. r-H4-2 carries a range the curator did not flatten (0.7–1.0,
  // recorded as its midpoint 0.85), which teaches what a record is; it is
  // `curated` and unverified, which is the state the whole corpus is in; and a
  // scenario cites it, so the last box is real rather than aspirational.
  const TRACE = { paperId: 'H4', recordId: 'r-H4-2', scenarioId: 'sc-s2' };
  const tracePaper = useMemo(() => papers.find((p) => p.id === TRACE.paperId), [papers]);
  const traceRecord = useMemo(() => records.find((r) => r.id === TRACE.recordId), [records]);
  const traceScenario = useMemo(
    () => scenarios.find((x) => x.id === TRACE.scenarioId),
    [scenarios],
  );
  const traceAssumption = useMemo(
    () =>
      traceScenario?.assumptions?.find(
        (a) => a.basis?.kind === 'record' && a.basis.recordId === TRACE.recordId,
      ),
    [traceScenario],
  );
  const traceProv = traceRecord ? (provenanceOf(traceRecord) as ProvKind) : 'unverified';
  const onSameField = useMemo(
    () => (traceRecord ? records.filter((r) => r.field === traceRecord.field).length : 0),
    [records, traceRecord],
  );

  const shownActivity = showAllActivity ? activity : activity.slice(0, 12);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0">
        <PageHeader
          eyebrow="openFerment · Bench"
          title="Bioprocess literature you can operate on"
          subtitle="Ask a question and get back a number with its address attached — the source it came from, the parameter it belongs to, and the model that already uses it. Thirteen parts in three movements, over two object pools that never mix."
          actions={
            <button
              className="btn inline-flex items-center gap-1.5"
              onClick={() => useStore.getState().setUI({ tourStop: 0 })}
            >
              <Compass size={14} aria-hidden />
              What is this platform?
            </button>
          }
        />

        {/* Something to press before any number can be misread. These six are
            the flow triggers verbatim, so a cold click always plays rather
            than drawing a decline — which is what the three questions that
            used to sit at the foot of this page all did, every one of them
            scoring zero against the matcher under a heading promising they
            "land on evidence the corpus can actually answer". */}
        <div className="flex flex-wrap items-center gap-2 -mt-2 mb-6">
          <span className="text-caption text-ink-soft">Try one —</span>
          {SUGGESTED_PROMPTS.slice(0, 3).map((q) => (
            <a
              key={q}
              href={href(`/postdoc?q=${encodeURIComponent(q)}`)}
              className="chip hover:border-accent hover:bg-accent-wash"
            >
              {q}
            </a>
          ))}
          <span className="text-caption text-ink-soft basis-full">
            These play authored flows. No language model is called anywhere in this build, and no
            number in an answer comes from model weights.
          </span>
        </div>

        {/* ── Band A · the demonstration ─────────────────────────────── */}
        <section aria-labelledby="home-trace" className="mb-7">
          <SectionTitle>
            <span id="home-trace">Follow one number</span>
          </SectionTitle>
          <p className="text-body text-ink-soft mb-3 max-w-3xl">
            Most literature tools hand you a passage. This one hands you a value with its address
            attached. Here is one — chosen as a teaching example, not selected by a rule —
            including the step in the middle that has not happened.
          </p>

          {tracePaper && traceRecord ? (
            <TileBoundary label="Follow one number">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-4">
              <TraceStep
                n="01"
                what="The source"
                part="Intake"
                to={`/trawl/sources/${tracePaper.id}`}
                prov={traceProv}
              >
                <div className="font-num text-caption">{tracePaper.id}</div>
                <div className="leading-snug">{tracePaper.title}</div>
                <div className="text-caption text-ink-soft mt-1 break-words">
                  {tracePaper.authors.join(', ')} · <span className="italic">{tracePaper.venue}</span>{' '}
                  · <span className="font-num">{tracePaper.year}</span>
                  {tracePaper.doi && <> · <span className="font-num">{tracePaper.doi}</span></>}
                </div>
                <div className="text-caption text-ink-soft mt-1.5">
                  Catalogued, not ingested — no PDF has been fetched for any of the{' '}
                  <span className="font-num">{papers.length}</span> entries, so the next box quotes
                  the curator&rsquo;s note, not the paper.
                </div>
              </TraceStep>

              <TraceStep
                n="02"
                what="The record"
                part="Ledger"
                to={`/trawl/sources/${tracePaper.id}?span=${traceRecord.id}`}
                prov={traceProv}
              >
                {traceRecord.quote && (
                  <div className="border-l-2 border-line pl-2 italic leading-snug">
                    &ldquo;{traceRecord.quote}&rdquo;
                  </div>
                )}
                <div className="font-num mt-1.5">
                  {traceRecord.value} {traceRecord.unit}
                </div>
                <div className="text-caption text-ink-soft">
                  {fieldName(traceRecord.field)}
                </div>
                <div className="text-caption text-ink-soft mt-1.5">
                  <span className="font-num">{traceRecord.id}</span> · curated, unverified.
                  {traceRecord.range && (
                    <>
                      {' '}The source states a range; the curator recorded the midpoint and kept{' '}
                      <span className="font-num">
                        {traceRecord.range.low}–{traceRecord.range.high}
                      </span>{' '}
                      on the record, so a reader can see which is which.
                    </>
                  )}
                </div>
                <a
                  href={href(`/ledger/p/${traceRecord.field}`)}
                  className="text-caption text-accent hover:underline mt-1.5 inline-block"
                >
                  <span className="font-num">{onSameField}</span> values sit on this parameter →
                </a>
              </TraceStep>

              {/* No tick: there is no datum here to carry one. `.held` would be
                  wrong too — that class means "in the record and out of the
                  statistic", not "never happened". */}
              <TraceStep
                n="03"
                what="The missing check"
                part="Audit"
                to="/assay"
                dashed
              >
                <div className="font-num text-display leading-none text-ink-soft">—</div>
                <div className="mt-1.5">
                  Nobody has checked this number against its source.{' '}
                  <span className="font-num">{status.verified}</span> of{' '}
                  <span className="font-num">{records.length}</span> records are verified, and no
                  extractor has ever been run — so there is no precision, recall or F1 to show
                  either.
                </div>
                <div className="text-caption text-ink-soft mt-1.5">This box is the product.</div>
              </TraceStep>

              <TraceStep
                n="04"
                what="The model that uses it"
                part="fermOS"
                to={traceScenario ? `/fermos/s/${traceScenario.id}` : '/fermos'}
                prov={traceProv}
              >
                {traceScenario ? (
                  <>
                    <div className="font-num text-caption">{traceScenario.id}</div>
                    <div className="leading-snug">{traceScenario.name}</div>
                    {traceAssumption && (
                      <div className="text-caption text-ink-soft mt-1.5">
                        cited as{' '}
                        <span className="text-ink">{traceAssumption.label}</span> —{' '}
                        <span className="font-num text-ink">
                          {traceAssumption.value} {traceAssumption.unit}
                        </span>
                      </div>
                    )}
                    <div className="text-caption text-ink-soft mt-1.5">
                      Correct the record and this scenario is marked stale by propagation, not by
                      anybody remembering to.
                    </div>
                  </>
                ) : (
                  <div className="text-caption text-ink-soft">
                    Nothing in this session consumes it yet.
                  </div>
                )}
              </TraceStep>
            </div>
            </TileBoundary>
          ) : (
            <Card>
              <div className="text-caption text-ink-soft">
                The teaching example is not in this session&rsquo;s corpus, so the trace is not
                drawn rather than drawn with holes.
              </div>
            </Card>
          )}

          <p className="text-caption text-ink-soft mt-2.5 max-w-3xl">
            Three of those boxes wear a tick, and it is not the solid green. Every one is{' '}
            <span className="text-ink">curated</span> — the accent hue at 45 %, deliberately
            reading as <em>on its way to verified</em> rather than as a peer of it. Verifying this
            one record against its source is a two-minute job and nobody has done it.{' '}
            <a href={href('/trawl/review')} className="text-accent hover:underline">
              Open the review queue →
            </a>
          </p>
        </section>

        {/* ── Band B · the map ───────────────────────────────────────── */}
        <section aria-labelledby="home-parts" className="mb-7">
          <SectionTitle>
            <span id="home-parts">Thirteen parts, three movements</span>
          </SectionTitle>
          <p className="text-body text-ink-soft mb-3 max-w-3xl">
            These thirteen are the navigation — the rail on a wide screen, and <span
            className="font-num">g</span> plus the letter beside each name anywhere.
          </p>
          <PartsMap />
        </section>

        {/* ── Band C · the two pools ─────────────────────────────────── */}
        <section aria-labelledby="home-pools" className="mb-7">
          <SectionTitle>
            <span id="home-pools">Two pools, never merged</span>
          </SectionTitle>
          <p className="text-body text-ink-soft mb-3 max-w-3xl">
            Two kinds of object, held apart on purpose — a claim nobody has checked yet, and a
            quantity that arrived already normalised. Nothing is ever averaged across them.
          </p>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <Card className="p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft">
                β-casein corpus
              </div>
              <div className="text-body mt-0.5">
                An <span className="font-medium">ExtractionRecord</span> — a catalogued claim
                awaiting verification.
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-caption">
                <a href={href('/trawl')} className="hover:text-accent">
                  <span className="font-num text-ink">{papers.length}</span> papers
                </a>
                <a href={href('/ledger/records')} className="hover:text-accent">
                  <span className="font-num text-ink">{records.length}</span> records
                </a>
                <a href={href('/ledger')} className="hover:text-accent">
                  <span className="font-num text-ink">{ONTOLOGY.length}</span> parameters
                </a>
                <a href={href('/runbook')} className="hover:text-accent">
                  <span className="font-num text-ink">{protocols.length}</span> protocols
                </a>
              </div>
              <div className="text-caption text-ink-soft mt-2 max-w-prose">
                Real literature, unevenly keyed on purpose. Where a value is unknown the corpus
                keeps the gap rather than guessing.
              </div>
            </Card>

            {/* The other pool, as its own component: this screen reads the
                corpus through the adapter seam and must not import an
                Accession to describe one. */}
            <DemoPoolCard />
          </div>
        </section>

        {/* ── Band D · the caveat, fourth ────────────────────────────── */}
        <section aria-labelledby="home-state" className="mb-7">
          <SectionTitle>
            <span id="home-state">What this build has not measured</span>
          </SectionTitle>
          <p className="text-body text-ink-soft mb-3 max-w-3xl">
            On the face of the screen rather than behind a click. Leading with the weakness is
            what makes the rest of it credible.
          </p>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            <Card className="p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft">
                Extraction quality
              </div>
              <div className="mt-1 text-body">
                <span className="text-signal-warn font-medium">Unmeasured.</span> No extractor has
                been run against this corpus.
              </div>
              {goldSet.status === 'loading' && <Skeleton rows={2} />}
              {goldSet.status === 'failed' && (
                <div className="text-caption text-signal-warn mt-1.5">
                  The gold-set plan could not be read: {goldSet.error.message}
                </div>
              )}
              {goldPlan && (
                <div className="text-caption text-ink-soft mt-1.5">
                  <span className="font-num">
                    {goldPlan.entries.reduce((n, g) => n + g.records, 0)}
                  </span>{' '}
                  records are planned for the gold set across{' '}
                  <span className="font-num">{goldPlan.entries.length}</span> sources, and{' '}
                  <span className="font-num">{goldPlan.difficultyCases.length}</span> cases were
                  chosen to be hard.{' '}
                  <a href={href('/assay')} className="text-accent hover:underline">
                    Open Audit
                  </a>
                </div>
              )}
            </Card>

            <Card className="p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft">
                Executable coverage
              </div>
              <div className="mt-1 text-body">
                <span className="font-num">{wiredRecords}</span> of{' '}
                <span className="font-num">{records.length}</span> records feed something
                executable — a protocol or a scenario.
              </div>
              <div className="text-caption text-ink-soft mt-1.5">
                <span className="font-num text-ink">{wiredFields}</span> of{' '}
                <span className="font-num">{ONTOLOGY.length}</span> parameters are wired; the rest
                are catalogued only. The corpus is broad and the executable layer is narrow, and
                that gap is the work.
              </div>
            </Card>

            <Card className="p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft">
                Contradictions
              </div>
              {contradictions.length === 0 ? (
                <div className="mt-1 text-body text-ink-soft">
                  No set of records violates a constraint — a statement about the checks that
                  exist, not a claim the corpus agrees with itself.
                </div>
              ) : (
                <>
                  <div className="mt-1 text-body">
                    <span className="font-num text-signal-error">{contradictions.length}</span>{' '}
                    open — sets of records that cannot all be true.
                  </div>
                  <div className="text-caption text-ink-soft mt-1.5">
                    Found by arithmetic over what the ontology already knows, not by judgement.{' '}
                    <a
                      href={href('/ledger/contradictions')}
                      className="text-accent hover:underline"
                    >
                      Open the queue
                    </a>
                  </div>
                </>
              )}
            </Card>
          </div>
        </section>

        <DemoFooter />
      </div>

      {/* ── Right rail · the only part of this page that is about YOU ──
          The main column is the system and reads the same for everyone. This
          column is your session, and it resets on refresh. Splitting them
          along that seam is what lets the page stop calling a seeded,
          back-dated, zero-message conversation "your work". */}
      <aside className="min-w-0" aria-labelledby="home-activity">
        {hasWork && (
          <section aria-labelledby="home-session" className="mb-6">
            <SectionTitle>
              <span id="home-session">Where you left off</span>
            </SectionTitle>
            <div className="space-y-2">
              {resumableSession && (
                <ResumeCard
                  to={`/postdoc/${resumableSession.id}`}
                  kicker="Last conversation"
                  title={resumableSession.title}
                  prov="user"
                  meta={
                    <>
                      <span className="font-num">{resumableSession.messages.length}</span>{' '}
                      {resumableSession.messages.length === 1 ? 'message' : 'messages'} ·{' '}
                      <span className="font-num">{resumableSession.startedAt}</span>
                    </>
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
                      of <span className="font-num">{runTotal}</span>
                    </>
                  }
                >
                  <Bar value={runDone} max={Math.max(1, runTotal)} />
                </ResumeCard>
              )}
              {reviewQueue.length > 0 && (
                <ResumeCard
                  to="/trawl/review"
                  kicker="Review queue"
                  title={`${queueRemaining} of ${reviewQueue.length} remaining`}
                  prov="user"
                  meta="a accept · r reject · e edit · g gold"
                >
                  <Bar value={reviewIndex} max={Math.max(1, reviewQueue.length)} />
                </ResumeCard>
              )}
              {pinnedScenarios.length > 0 && (
                <ResumeCard
                  to="/fermos/compare"
                  kicker="Pinned scenarios"
                  title={pinnedScenarios.map((x) => x.name).join(' · ')}
                  prov="demo"
                  meta="Modelled economics, not validated."
                />
              )}
            </div>
          </section>
        )}

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
