// Home (OF-DES-001 §8.1) — orient any persona in five seconds: what is in the
// corpus, where you left off, and what to do next. Three bands plus a rail.
import React, { useMemo, useState, type ReactNode } from 'react';
import {
  AlertTriangle,
  ArrowUpRight,
  Award,
  BookOpen,
  Boxes,
  Check,
  CircleDot,
  ClipboardList,
  Clock,
  Compass,
  Download,
  FileText,
  FlaskConical,
  GitBranch,
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
import { useStore, provenanceOf, useProgramFilter, type ProgramEntityKind } from '@/store';
import { ProposalsCard } from '@/components/ProposalsCard';
import { href } from '@/router';
import { RUNBOOK_STATUS_LABEL, RUNBOOKS } from '@/data/runbooks';
import { ELEVEN } from '@/data/nav';
import { PAPERS } from '@/data/papers';
import { RECORDS } from '@/data/records';
import { STRAINS } from '@/data/strains';
import { PRODUCTS } from '@/data/products';
import { PROTOCOLS } from '@/data/protocols';
import { UNIT_OPERATIONS } from '@/data/vocabulary';
import { MODULES } from '@/data/learn';
import { SCENARIOS, COST_MODELS } from '@/data/scenarios';
import { Bar, Card, EmptyState, Explain, PageHeader, SectionTitle, cx } from '@/components/ui';
import { ProvDot, ProvenanceLegend, Tick, provMeta, type ProvKind } from '@/components/Provenance';
import type { ActivityEvent, ExtractionRecord, Paper, Program, ProgramId } from '@/data/types';
import { WorkforceCard } from '@/components/GuildBits';
import { HIT_RATE_MIN_TESTED, ledgerCounts } from '@/engine/ledger';
import { livePrompts, subjectsShow, type OfferedPrompt } from '@/data/livePrompts';
import { PROGRAMS, PROGRAMS_SETTINGS_PATH, THREAD_LETTER_CLASS } from '@/data/programs';
import { sessionShows } from '@/data/flows';

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

/**
 * The research programs the corpus serves (OF-BLD-014 §2.2), declared in
 * src/data/programs.ts (OF-BLD-016 §2.1): each a set of thread letters and a
 * status. The strip shows a tile for each program whose papers the program
 * selector shows — the active ones, and the archived ones while the switch is
 * on — in thread order, and names the archived ones it hides on one muted
 * line. The counts are read from the store, so they follow the overlay: a
 * fetch or a decision moves them.
 */
const PROGRAM_TITLE: Record<ProgramId, ReactNode> = {
  casein: (
    <>
      β-casein in <i>C. reinhardtii</i> cw15
    </>
  ),
  pha: 'PHA from waste cellulosic sugars',
  yeast: (
    <>
      Yeast ethanol: <i>S. cerevisiae</i> on glucose
    </>
  ),
};

/** "threads A to O", "thread P": a program's letters as the strip writes them. */
function threadsLabel(program: Program): string {
  const l = [...program.letters].sort();
  return l.length === 1 ? `thread ${l[0]}` : `threads ${l[0]} to ${l[l.length - 1]}`;
}

/** The programs in thread order (A first), the order the strip has always drawn them in. */
const STRIP_ORDER: Program[] = [...PROGRAMS].sort((a, b) =>
  [...a.letters].sort()[0].localeCompare([...b.letters].sort()[0]),
);

/** "Casein", "Casein and PHA", "Casein, PHA and X". */
function joinNames(names: string[]): string {
  return names.length <= 1 ? (names[0] ?? '') : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}

/** The link to the switch, as every hidden-things line on Home writes it. */
function SwitchLink() {
  return (
    <a className="text-accent hover:underline" href={href(PROGRAMS_SETTINGS_PATH)}>
      Settings → Programs
    </a>
  );
}

function ProgramTile({
  program,
  papers,
  records,
}: {
  program: Program;
  papers: Paper[];
  records: ExtractionRecord[];
}) {
  const mine = papers.filter((p) => program.letters.includes(p.thread));
  const ids = new Set(mine.map((p) => p.id));
  const fullText = mine.filter((p) => p.textSource === 'full-text').length;
  const byProv = new Map<ProvKind, number>();
  for (const r of records) {
    if (!ids.has(r.paperId)) continue;
    const k = provenanceOf(r) as ProvKind;
    byProv.set(k, (byProv.get(k) ?? 0) + 1);
  }
  const provs = [...byProv.entries()].sort((a, b) => b[1] - a[1]);
  return (
    <a
      href={href('/intake')}
      className="card p-3 block transition-colors hover:border-accent/45 hover:bg-accent-wash/40"
      data-program={program.id}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-serif text-section-title font-semibold leading-snug">
            {PROGRAM_TITLE[program.id] ?? program.name}
          </div>
          <div className="text-caption uppercase tracking-wide text-ink-soft">
            {threadsLabel(program)}
            {program.status === 'archived' && ' · archived'}
          </div>
        </div>
        <ArrowUpRight size={13} className="text-ink-soft shrink-0" aria-hidden />
      </div>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-body">
        <span>
          <span className="font-num">{mine.length}</span> papers
        </span>
        <span>
          <span className="font-num">{fullText}</span> with full text
        </span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-caption text-ink-soft">
        {provs.length === 0 ? (
          <span>No records yet. Values arrive through Intake and a Guild decision.</span>
        ) : (
          provs.map(([k, n]) => (
            <span key={k} className="inline-flex items-center gap-1.5">
              <ProvDot p={k} />
              {provMeta(k).label} <span className="font-num">{n}</span>
            </span>
          ))
        )}
      </div>
    </a>
  );
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

function PredictionsCard() {
  const runbooks = useStore((s) => s.runbooks);
  const depositions = useStore((s) => s.depositions);
  // Counted over the runbooks and depositions whose program shows (§2.2),
  // as the ledger page counts them.
  const shows = useProgramFilter();
  const c = ledgerCounts(runbooks, depositions, shows);
  return (
    <Card className="p-4" data-testid="home-predictions">
      <div className="grid grid-cols-2 gap-y-1 text-body">
        <span>Locked</span><span className="font-num text-right">{c.locked}</span>
        <span>Tested</span><span className="font-num text-right">{c.tested}</span>
        <span>Held</span><span className="font-num text-right">{c.held}</span>
        <span>Missed</span><span className="font-num text-right">{c.missed}</span>
        <span>Inconclusive runs</span><span className="font-num text-right">{c.inconclusiveRuns}</span>
      </div>
      <p className="text-caption text-ink-soft mt-2">
        {c.hitRate === null
          ? `Too few tested for a hit rate; one is shown from ${HIT_RATE_MIN_TESTED}.`
          : `Hit rate ${Math.round(c.hitRate * 100)} % of ${c.tested} tested.`}{' '}
        <a className="text-accent hover:underline" href={href('/runbooks/ledger')}>Open the ledger</a>
      </p>
    </Card>
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
  runbook: GitBranch,
  molecule: Boxes,
  search: Search,
  clock: Clock,
  timer: Clock,
  alert: AlertTriangle,
  warn: AlertTriangle,
  pin: Pin,
};

// Each card says the verb AND names the surface it lands on, because the
// surface names are the vocabulary now (§2.2 as revised) and Home is where a
// first-time reader meets them. The verb is what they came to do; the name is
// what they will type next time.
/**
 * What each of the eleven actually has, right now (§7).
 *
 * Counted from the seed where there is something to count, and stated as
 * "nothing" where there is not. `built` drives the greying: a destination with
 * no code renders dimmed rather than being quietly indistinguishable from one
 * that works, because "I clicked fermOS and it was empty" should be something
 * Home told you first.
 */
type Shows = (kind: ProgramEntityKind, id: string) => boolean;

/** The seed lists counted below, each through the program selector (OF-BLD-016 §2.2). */
function stateOf(shows: Shows): Record<string, { now: string; built: boolean }> {
  const n = <T extends { id: string }>(list: readonly T[], kind: ProgramEntityKind) =>
    list.filter((x) => shows(kind, x.id)).length;
  return {
    Intake: { now: `${n(RECORDS, 'record')} extraction records`, built: true },
    BioRepo: { now: `${n(PAPERS, 'paper')} papers · gold set not yet annotated`, built: true },
    Postdoc: { now: 'live through openferment-core, on the model it is configured with', built: true },
    geneOS: { now: `${n(STRAINS, 'strain')} hosts · no sequence tooling`, built: true },
    fermOS: { now: 'empty — no kinetics, no transport, no scale-up', built: false },
    pureOS: { now: `${UNIT_OPERATIONS.length} unit operations · no process model`, built: true },
    Proforma: { now: `${n(SCENARIOS, 'scenario')} scenarios over ${COST_MODELS.length} cost models`, built: true },
    Runbooks: { now: `${n(RUNBOOKS, 'runbook')} runbooks · ${n(PROTOCOLS, 'protocol')} protocols`, built: true },
    Dominion: { now: `${n(PRODUCTS, 'product')} molecules · clearance modelled, not searched`, built: true },
    Primer: { now: `${n(MODULES, 'module')} modules`, built: true },
    Guild: { now: 'review queue and roles', built: true },
  };
}

const ENTRY_CARDS: {
  to: string;
  title: string;
  where: string;
  desc: string;
  Icon: LucideIcon;
}[] = [
  {
    to: '/postdoc',
    title: 'Ask a question',
    where: 'Postdoc',
    desc: 'Get a cited answer with the plan, tool calls and retrieved passages shown.',
    Icon: MessagesSquare,
  },
  {
    to: '/guild',
    title: 'Review extractions',
    where: 'Guild',
    desc: 'Triage machine-extracted parameters against the span they came from.',
    Icon: Table2,
  },
  {
    to: '/runbooks/protocols',
    title: 'Run a protocol',
    where: 'Protocols → Deposition',
    desc: 'Scale a verified procedure to your batch size and execute it at the bench.',
    Icon: ClipboardList,
  },
  {
    to: '/proforma',
    title: 'Model a process',
    where: 'Proforma',
    desc: 'Sweep a scenario and see where the cost per kilogram actually goes.',
    Icon: LineChart,
  },
  {
    to: '/dominion/molecules',
    title: 'Browse molecules',
    where: 'Molecules',
    desc: 'What could be made, in which host, on which train — and who already owns it.',
    Icon: Boxes,
  },
  {
    to: '/runbooks',
    title: 'Open a runbook',
    where: 'Runbooks',
    desc: 'A synthesised answer to "how would we make this", with the stages it took to get there.',
    Icon: GitBranch,
  },
];

/**
 * Asked when fewer than three live questions show. Each names what it is
 * about, as the live ones do, so it passes the same program selector: the
 * first stands on the Chlorella vulgaris disruption values of J11, the third
 * on O7's harvesting assessment, and the second asks of whatever the corpus
 * holds.
 */
const COLD_START_QUESTIONS: OfferedPrompt[] = [
  {
    text: 'What specific growth rate does Chlorella vulgaris reach in mixotrophic culture?',
    about: [{ kind: 'paper', id: 'J11' }],
  },
  {
    text: 'Which strain in the corpus has the highest reported protein content, and how was it measured?',
    about: [],
  },
  {
    text: 'How does harvest recovery differ between centrifugation and membrane filtration?',
    about: [{ kind: 'paper', id: 'O7' }],
  },
];

/**
 * The entities an activity line names: what its link opens (a paper, a span
 * on one, a strain, a molecule, a scenario, a protocol, a deposition, a
 * runbook, a lesson) and every paper or record id its text writes. A line
 * shows when every one of them shows (§2.2); a line naming none is general.
 */
const TEXT_IDS = new RegExp(`\\b(r-${THREAD_LETTER_CLASS}\\d+[a-z]*-\\d+|${THREAD_LETTER_CLASS}\\d+[a-z]*)\\b`, 'g');
function activityShows(e: ActivityEvent, shows: Shows): boolean {
  const subjects: { kind: ProgramEntityKind; id: string }[] = [];
  if (e.href) {
    const [path, query] = e.href.replace(/^#/, '').split('?');
    const [a, b, c] = path.split('/').filter(Boolean);
    if (a === 'biorepo' && b === 'paper' && c) subjects.push({ kind: 'paper', id: c });
    if (a === 'geneos' && b === 'hosts' && c) subjects.push({ kind: 'strain', id: c });
    if (a === 'dominion' && b === 'molecules' && c) subjects.push({ kind: 'product', id: c });
    if (a === 'proforma' && b === 'scenario' && c) subjects.push({ kind: 'scenario', id: c });
    if (a === 'runbooks' && b === 'protocols' && c) subjects.push({ kind: 'protocol', id: c });
    else if (a === 'runbooks' && b === 'depositions' && c) subjects.push({ kind: 'deposition', id: c });
    else if (a === 'runbooks' && b && b !== 'ledger') subjects.push({ kind: 'runbook', id: b });
    if (a === 'primer' && b && b !== 'path' && b !== 'practice') {
      if (MODULES.some((m) => m.id === b)) subjects.push({ kind: 'module', id: b });
      const lesson = c ?? b;
      if (MODULES.some((m) => m.lessons.some((l) => l.id === lesson))) subjects.push({ kind: 'lesson', id: lesson });
    }
    const span = query ? new URLSearchParams(query).get('span') : null;
    if (span) subjects.push({ kind: 'record', id: span });
  }
  for (const m of e.text.matchAll(TEXT_IDS)) subjects.push({ kind: m[1].startsWith('r-') ? 'record' : 'paper', id: m[1] });
  return subjects.every((x) => shows(x.kind, x.id));
}

// ── screen ─────────────────────────────────────────────────────────────

export default function Home() {
  const allPapers = useStore((s) => s.papers);
  const allRecords = useStore((s) => s.records);
  const allProtocols = useStore((s) => s.protocols);
  const allScenarios = useStore((s) => s.scenarios);
  const allProducts = useStore((s) => s.products);
  const allRunbooks = useStore((s) => s.runbooks);
  const allSessions = useStore((s) => s.sessions);
  const collections = useStore((s) => s.collections);
  const liveConversations = useStore((s) => s.liveConversations);
  const allActivity = useStore((s) => s.activity);
  const runs = useStore((s) => s.runs);
  const activeRunId = useStore((s) => s.activeRunId);
  const fullQueue = useStore((s) => s.reviewQueue);
  const fullIndex = useStore((s) => s.reviewIndex);

  const [showAllActivity, setShowAllActivity] = useState(false);

  // ── programs (OF-BLD-016 §2.2) ───────────────────────────────────────
  // Every list, count and card below reads these, never the store's lists:
  // with archived programs hidden (the default) nothing of theirs is counted
  // or offered, and with the switch on each is the whole list, in its order.
  const shows = useProgramFilter();
  const papers = useMemo(() => allPapers.filter((p) => shows('paper', p.id)), [allPapers, shows]);
  const records = useMemo(() => allRecords.filter((r) => shows('record', r.id)), [allRecords, shows]);
  const protocols = useMemo(() => allProtocols.filter((p) => shows('protocol', p.id)), [allProtocols, shows]);
  const scenarios = useMemo(() => allScenarios.filter((x) => shows('scenario', x.id)), [allScenarios, shows]);
  const products = useMemo(() => allProducts.filter((p) => shows('product', p.id)), [allProducts, shows]);
  const runbooks = useMemo(() => allRunbooks.filter((r) => shows('runbook', r.id)), [allRunbooks, shows]);
  const sessions = useMemo(
    () => allSessions.filter((x) => sessionShows(x, shows, collections)),
    [allSessions, shows, collections],
  );
  const activity = useMemo(() => allActivity.filter((e) => activityShows(e, shows)), [allActivity, shows]);
  // The review queue as it stands, less the records whose program is hidden:
  // the position is the count of shown records before the reviewer's place.
  const reviewQueue = useMemo(() => fullQueue.filter((id) => shows('record', id)), [fullQueue, shows]);
  const reviewIndex = useMemo(
    () => fullQueue.slice(0, fullIndex).filter((id) => shows('record', id)).length,
    [fullQueue, fullIndex, shows],
  );
  const STATE = useMemo(() => stateOf(shows), [shows]);
  // Something is hidden from this page: a line under a tile says so and
  // where the switch is, without counting what it hides.
  const papersHidden = papers.length < allPapers.length;
  const recordsHidden = records.length < allRecords.length;

  // The program tiles: each program whose papers show, in thread order. An
  // active program always has its tile, papers or none.
  const programTiles = useMemo(
    () => STRIP_ORDER.filter((p) => p.status === 'active' || papers.some((x) => p.letters.includes(x.thread))),
    [papers],
  );
  const archivedPrograms = PROGRAMS.filter((p) => p.status === 'archived');
  const archivedHidden = archivedPrograms.filter((p) => !programTiles.includes(p));

  // ── band 1 numbers ───────────────────────────────────────────────────
  const ingested = useMemo(() => papers.filter((p) => p.ingest === 'complete'), [papers]);
  const shelved = papers.length - ingested.length;

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
  // The lookup reads every record: a shown protocol bound to a record in an
  // archived program still has that record's provenance.
  const protocolProv = useMemo(() => {
    const byId = new Map(allRecords.map((r) => [r.id, r]));
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
  }, [protocols, allRecords]);

  // ── catalogue numbers (OF-BLD-005) ───────────────────────────────────
  //
  // Deliberately not folded into Corpus vitals. Those tiles count real
  // literature; these count a modeled catalogue. Putting them in one row would
  // quietly imply the same standard of evidence stands behind both, which is
  // the one thing this page is built not to do.
  const blockedProducts = useMemo(
    () => products.filter((p) => p.clearanceState === 'blocked').length,
    [products],
  );
  const runbooksWaiting = useMemo(
    () =>
      runbooks.filter((r) =>
        ['blocked_unverified', 'needs_review', 'awaiting_budget'].includes(r.status),
      ),
    [runbooks],
  );
  const runbooksRunning = useMemo(
    () => runbooks.filter((r) => r.status === 'running').length,
    [runbooks],
  );

  // ── band 2 state ─────────────────────────────────────────────────────
  // The last conversation somebody actually had: a Live one first, else a
  // scripted session with messages in it. The seeded sessions are empty, and
  // an empty session is not work to resume.
  const lastLive = liveConversations.find((c) => c.turns.length > 0) ?? null;
  const lastSession = lastLive ? null : (sessions.find((x) => x.messages.length > 0) ?? null);
  const pinnedScenarios = useMemo(() => scenarios.filter((x) => x.pinned), [scenarios]);
  // A run in progress shows while its protocol's program does (§2.2).
  const runInProgress = activeRunId ? (runs[activeRunId] ?? null) : null;
  const activeRun = runInProgress && shows('protocol', runInProgress.protocolId) ? runInProgress : null;
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
    lastLive !== null ||
    lastSession !== null ||
    reviewQueue.length > 0 ||
    activeRun !== null ||
    pinnedScenarios.length > 0 ||
    runbooksWaiting.length > 0;

  const shownActivity = showAllActivity ? activity : activity.slice(0, 12);

  // Three questions for a first visit: the live ones whose program shows,
  // else the cold-start ones that do (§2.2).
  const firstQuestions = useMemo(() => {
    const live = livePrompts(shows);
    return live.length >= 3
      ? live.slice(0, 3)
      : COLD_START_QUESTIONS.filter((q) => subjectsShow(q.about, shows)).map((q) => q.text);
  }, [shows]);

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="min-w-0">
        <PageHeader
          eyebrow="openFerment"
          title="Bioprocess literature you can operate on"
          subtitle="Ask Postdoc against a curated corpus, verify every extracted number against the span it came from, turn verified parameters into runnable protocols, and model what they cost at scale."
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
                to="/biorepo"
                label="Papers catalogued"
                prov="curated"
                tickTitle="Real literature, curated by hand — metadata and a curator note, no full text retrieved"
                sub={
                  papers.length === 0 ? (
                    papersHidden ? (
                      'Every paper belongs to an archived program, and archived programs are hidden'
                    ) : (
                      'No corpus loaded'
                    )
                  ) : (
                    <>
                      <span className="font-num">{shelved}</span> awaiting full-text ingest
                    </>
                  )
                }
              >
                <div className="font-num text-display leading-tight">
                  {ingested.length}
                  <span className="text-section-title text-ink-soft ml-1.5">
                    / {papers.length}
                  </span>
                </div>
              </VitalTile>
            </TileBoundary>

            <TileBoundary label="Extraction records">
              <VitalTile
                to="/intake"
                label="Extraction records"
                prov={recordProv}
                sub={
                  status.total === 0 && recordsHidden ? (
                    <span data-testid="home-records-hidden">
                      No values for the active programs yet: they arrive through Intake and a Guild
                      decision. Values in archived programs are hidden.
                    </span>
                  ) : (
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
                  )
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
                to="/biorepo/witness"
                label="Gold set"
                prov="gold"
                sub={
                  goldRecords.length === 0 ? (
                    recordsHidden ? (
                      'None in the active programs yet — flag records with g in review. Archived programs are hidden.'
                    ) : (
                      'No curated values yet — flag records with g in review'
                    )
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
                to="/runbooks/protocols"
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

        {/* ── Band 1a · Programs (OF-BLD-014 §2.2) ────────────────────── */}
        <section aria-labelledby="home-programs" className="mb-7">
          <SectionTitle
            right={
              <Explain label="What is a program?">
                A program is one research question and the papers gathered for it. Thread P's
                and thread Q's papers are proposed by a fixed search rule and enter the corpus
                only when a person approves them; none of their values is typed by hand. Every
                count here is read from the corpus as it stands now. An archived program is kept
                whole and leaves every default view; the switch in Settings → Programs brings it
                back.
              </Explain>
            }
          >
            <span id="home-programs">Programs</span>
          </SectionTitle>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {programTiles.map((program) => (
              <TileBoundary key={program.id} label={threadsLabel(program)}>
                <ProgramTile program={program} papers={papers} records={records} />
              </TileBoundary>
            ))}
          </div>
          {archivedPrograms.length > 0 && (
            <p className="text-caption text-ink-soft mt-2" data-testid="home-programs-archived">
              {archivedHidden.length > 0 ? (
                <>
                  Archived: {joinNames(archivedHidden.map((p) => `${p.name} (${threadsLabel(p)})`))}.{' '}
                  {archivedHidden.length === 1 ? 'It is' : 'They are'} kept, and hidden from every list,
                  count and suggested question. <SwitchLink /> shows archived programs again.
                </>
              ) : (
                <>
                  {joinNames(archivedPrograms.map((p) => p.name))}{' '}
                  {archivedPrograms.length === 1 ? 'is an archived program' : 'are archived programs'},
                  shown because the switch in <SwitchLink /> is on.
                </>
              )}
            </p>
          )}
        </section>

        {/* ── Band 1b · Catalogue (OF-BLD-005) ───────────────────────── */}
        <section aria-labelledby="home-catalogue" className="mb-7">
          <SectionTitle
            right={
              <Explain label="Why these are a separate band">
                The tiles above count real literature: papers with DOIs, records that resolve to a
                span, protocols bound to those records. These two count a modeled catalogue —
                molecules assembled from a facet vocabulary and runbooks synthesised from them.
                Both are useful and only one is evidence, so they wear the dashed amber tick and
                sit in their own row rather than blurring into the corpus count.
              </Explain>
            }
          >
            <span id="home-catalogue">Catalogue</span>
          </SectionTitle>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <TileBoundary label="Molecules catalogued">
              <VitalTile
                to="/dominion/molecules"
                label="Molecules catalogued"
                prov="demo"
                tickTitle="Modeled — a map of the option space, not a set of measurements"
                sub={
                  <>
                    <span className="font-num text-signal-error">{blockedProducts}</span> behind
                    live blocking claims ·{' '}
                    <span className="font-num">
                      {new Set(products.map((p) => p.processCode)).size}
                    </span>{' '}
                    process families
                  </>
                }
              >
                <div className="font-num text-display leading-tight">{products.length}</div>
              </VitalTile>
            </TileBoundary>

            <TileBoundary label="Runbooks">
              <VitalTile
                to="/runbooks"
                label="Runbooks"
                prov="demo"
                tickTitle="Synthesised answers — modeled throughout, and never a clearance opinion"
                sub={
                  <>
                    <span className="font-num">{runbooksRunning}</span> running ·{' '}
                    <span
                      className={
                        runbooksWaiting.length > 0 ? 'font-num text-signal-warn' : 'font-num'
                      }
                    >
                      {runbooksWaiting.length}
                    </span>{' '}
                    waiting on a person
                  </>
                }
              >
                <div className="font-num text-display leading-tight">{runbooks.length}</div>
              </VitalTile>
            </TileBoundary>
          </div>
        </section>

        {/* ── Band 2 · Your work / cold start ────────────────────────── */}
        {/* OF-BLD-015 §7.4 — what a model asked for at a gate, each with the
            one button a person presses. Nothing when the service is down or
            nothing waits. */}
        <ProposalsCard />

        <section aria-labelledby="home-work" className="mb-7">
          <SectionTitle>
            <span id="home-work">{hasWork ? 'Your work' : 'Three good first questions'}</span>
          </SectionTitle>

          {hasWork ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {lastLive && (
                <ResumeCard
                  to={`/postdoc/${lastLive.id}`}
                  kicker="Last conversation"
                  title={lastLive.title}
                  prov="user"
                  meta={
                    <>
                      <span className="font-num">{lastLive.turns.length}</span>{' '}
                      {lastLive.turns.length === 1 ? 'question' : 'questions'} ·{' '}
                      <span className="font-num">{lastLive.startedAt}</span>
                    </>
                  }
                />
              )}
              {lastSession && (
                <ResumeCard
                  to={`/postdoc/${lastSession.id}`}
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
                  to="/guild"
                  kicker="Review queue"
                  title={`${queueRemaining} of ${reviewQueue.length} remaining`}
                  prov="user"
                  meta="Pick up where you stopped — a accept, r reject, e edit, g gold"
                >
                  <Bar value={reviewIndex} max={Math.max(1, reviewQueue.length)} />
                </ResumeCard>
              ) : (
                <ResumeCard
                  to="/guild"
                  kicker="Review queue"
                  title={
                    records.length === 0 && recordsHidden
                      ? 'No values in the active programs yet'
                      : unverifiedCount === 0
                        ? 'Nothing left unverified'
                        : `${unverifiedCount} unverified records waiting`
                  }
                  prov="unverified"
                  meta={
                    records.length === 0 && recordsHidden
                      ? 'Values in archived programs are hidden. New values arrive through Intake and wait here for a decision.'
                      : unverifiedCount === 0
                        ? 'Every extraction has been decided. Open the queue to re-check any of them.'
                        : 'Start a queue and triage them one span at a time.'
                  }
                />
              )}

              {activeRun && activeProtocol && (
                <ResumeCard
                  to={`/runbooks/protocols/${activeRun.protocolId}/run/${activeRun.id}`}
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

              {runbooksWaiting.length > 0 && (
                <ResumeCard
                  to={
                    runbooksWaiting.length === 1
                      ? `/runbooks/${runbooksWaiting[0].id}`
                      : '/runbooks'
                  }
                  kicker="Runbooks waiting on you"
                  title={
                    runbooksWaiting.length === 1
                      ? runbooksWaiting[0].title
                      : `${runbooksWaiting.length} runbooks need a decision`
                  }
                  prov="demo"
                  meta={runbooksWaiting
                    .map((r) => RUNBOOK_STATUS_LABEL[r.status])
                    .join(' · ')}
                >
                  <Bar
                    value={runbooks.length - runbooksWaiting.length}
                    max={Math.max(1, runbooks.length)}
                    className="bg-signal-warn"
                  />
                </ResumeCard>
              )}

              {pinnedScenarios.length > 0 && (
                <ResumeCard
                  to="/biorepo/compare"
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
                {firstQuestions.map((q) => (
                  <li key={q}>
                    <a
                      href={href(`/postdoc?q=${encodeURIComponent(q)}`)}
                      className="card p-3 h-full flex flex-col gap-2 transition-colors hover:border-accent/45 hover:bg-accent-wash/40"
                    >
                      <MessagesSquare size={15} className="text-accent shrink-0" aria-hidden />
                      <span className="font-serif text-reading leading-snug">{q}</span>
                    </a>
                  </li>
                ))}
              </ul>
              {firstQuestions.length === 0 && (
                <p className="text-body text-ink-soft" data-testid="home-questions-hidden">
                  The suggested questions are about archived programs, which are hidden.{' '}
                  <SwitchLink /> shows them again, or ask your own in{' '}
                  <a className="text-accent hover:underline" href={href('/postdoc')}>
                    Postdoc
                  </a>
                  .
                </p>
              )}
            </>
          )}
        </section>

        {/* ── Band 3 · The eleven ────────────────────────────────────── */}
        {/* OF-BLD-008 §7 — the whole navigation, laid out once with an honest
            current state per entry. "Empty" is a legitimate state and is shown
            as one: geneOS says it has nothing, and a reader who wants sequence
            work learns that here rather than by clicking through to find out. */}
        <section aria-labelledby="home-eleven">
          <SectionTitle
            right={
              <span className="font-num text-caption text-ink-soft">
                {ELEVEN.filter((d) => STATE[d.label]?.built).length}/{ELEVEN.length} with something behind them
              </span>
            }
          >
            <span id="home-eleven">The eleven</span>
          </SectionTitle>
          <p className="text-body text-ink-soft mb-3 max-w-3xl">
            Everything this platform does lives inside one of these. The list is closed — when
            something new is built the question is which of the eleven owns it, never whether to
            add a twelfth.
          </p>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {ELEVEN.map((d) => {
              const state = STATE[d.label];
              return (
                <a
                  key={d.to}
                  href={href(d.to)}
                  className={cx(
                    'card p-4 flex items-start gap-3 transition-colors hover:border-accent/45 hover:bg-accent-wash/40',
                    !state?.built && 'opacity-70',
                  )}
                >
                  <span
                    className={cx(
                      'w-9 h-9 rounded-btn grid place-items-center shrink-0 border',
                      state?.built
                        ? 'bg-accent/10 border-accent/25'
                        : 'bg-ink-soft/5 border-line',
                    )}
                  >
                    <d.icon
                      size={17}
                      className={state?.built ? 'text-accent' : 'text-ink-soft'}
                      aria-hidden
                    />
                  </span>
                  <span className="min-w-0">
                    <span className="block font-serif text-section-title font-semibold leading-snug">
                      {d.label}
                    </span>
                    <span className="block text-body text-ink-soft">{d.descriptor}</span>
                    <span
                      className={cx(
                        'block font-num text-caption mt-1',
                        state?.built ? 'text-ink' : 'text-ink-soft/70',
                      )}
                    >
                      {state?.now ?? '—'}
                    </span>
                  </span>
                </a>
              );
            })}
          </div>
        </section>

        {/* ── Band 4 · Start something ───────────────────────────────── */}
        <section aria-labelledby="home-start" className="mt-7">
          <SectionTitle>
            <span id="home-start">Start something</span>
          </SectionTitle>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
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
                  <span className="block font-num text-[11px] leading-tight text-ink-soft truncate">
                    {c.where}
                  </span>
                  <span className="block font-serif text-section-title font-semibold leading-snug">
                    {c.title}
                  </span>
                  <span className="block text-body text-ink-soft mt-0.5">{c.desc}</span>
                </span>
              </a>
            ))}
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-2">
            <button
              className="inline-flex items-center gap-1.5 text-body text-ink-soft hover:text-accent"
              onClick={() => useStore.getState().setUI({ tourStop: 0 })}
            >
              <Compass size={14} aria-hidden />
              What is this platform?
            </button>
            {/* The full map, one click from Home. The grid above names the
                eleven; this is where every component each one owns is laid out,
                including the seven with nothing under them yet. */}
            <a
              href={href('/settings/architecture')}
              className="inline-flex items-center gap-1.5 text-body text-ink-soft hover:text-accent"
            >
              <Boxes size={14} aria-hidden />
              The map behind these names
            </a>
          </div>
        </section>
      </div>

      {/* ── Right rail · recent activity ─────────────────────────────── */}
      <aside className="min-w-0" aria-labelledby="home-activity">
        {/* OF-BLD-013 §2 — the workforce, from Guild's ledger. */}
        <SectionTitle>
          <span>Workforce</span>
        </SectionTitle>
        <div className="mb-6">
          <WorkforceCard />
        </div>
        {/* OF-BLD-014 §9.3 — predictions, counted as the ledger counts them. */}
        <SectionTitle>
          <span>Predictions</span>
        </SectionTitle>
        <div className="mb-6">
          <PredictionsCard />
        </div>
        <SectionTitle>
          <span id="home-activity">Recent activity</span>
        </SectionTitle>
        <Card className="overflow-hidden">
          {activity.length === 0 ? (
            <EmptyState
              title="No activity yet"
              body={
                allActivity.length > 0 ? (
                  <>
                    Activity about archived programs is hidden. <SwitchLink /> shows it again. Ingests,
                    review decisions, runs and exports land here as you work.
                  </>
                ) : (
                  'Ingests, review decisions, runs and exports land here as you work. Nothing is recorded outside this browser session.'
                )
              }
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
