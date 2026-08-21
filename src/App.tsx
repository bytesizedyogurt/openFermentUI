// App shell (OF-DES-001 §7.1): left rail + top utility bar + content region,
// with the persistent demo banner, jobs tray, palette, and global shortcuts.
import { useEffect, useRef, useState } from 'react';
import {
  Home as HomeIcon,
  MessagesSquare,
  Library as LibraryIcon,
  Table2,
  FlaskConical,
  ClipboardList,
  LineChart,
  GraduationCap,
  Settings as SettingsIcon,
  HelpCircle,
  Search,
  Activity,
  Sun,
  Moon,
  Rows3,
  Rows4,
  X,
  PanelLeftClose,
  PanelLeftOpen,
  Import,
  Gauge,
  Scale,
  Users,
  Stamp,
  type LucideIcon,
  LayoutGrid,
  Database,
  Calculator} from 'lucide-react';
import { useStore } from '@/store';
import { useRoute, navigate } from '@/router';
import { cx, Popover, Toasts, Sheet } from '@/components/ui';
import { CommandPalette } from '@/components/CommandPalette';
import { JobsPanel } from '@/components/JobsTray';
import { GuidedTour } from '@/components/GuidedTour';
import { SHORTCUTS } from '@/data/shortcuts';
import type { FieldId } from '@/data/types';

import Home from '@/screens/Home';
import Ask from '@/screens/Ask';
import Library from '@/screens/Library';
import PaperReader from '@/screens/PaperReader';
import Ingest from '@/screens/Ingest';
import Extract from '@/screens/Extract';
import { Ledger, ParameterPage, Contradictions } from '@/screens/Ledger';
import { Parchment } from '@/screens/Parchment';
import { OpenLab } from '@/screens/OpenLab';
import { DesignIndex, DesignDetail } from '@/screens/DesignDetail';
import { Notary } from '@/screens/Notary';
import Review from '@/screens/Review';
import Validation from '@/screens/Validation';
import Organisms from '@/screens/Organisms';
import StrainPage from '@/screens/StrainPage';
import Protocols from '@/screens/Protocols';
import ProtocolDetail from '@/screens/ProtocolDetail';
import ProtocolEditor from '@/screens/ProtocolEditor';
import RunMode from '@/screens/RunMode';
import Simulate from '@/screens/Simulate';
import ScenarioWorkspace from '@/screens/ScenarioWorkspace';
import Plant from '@/screens/Plant';
import Compare from '@/screens/Compare';
import Learn from '@/screens/Learn';
import Lesson from '@/screens/Lesson';
import Settings from '@/screens/Settings';

/**
 * The rail is the architecture (OF-FE-003 §6). Grouped as the whitepaper groups
 * it — Read, Reason, Return — so a reviewer can learn the system by looking at
 * the sidebar. Shortcuts are preserved wherever the destination is the same
 * screen it was before the rename.
 */
type RailItem =
  | { group: string }
  | { to: string; label: string; icon: LucideIcon; key: string; pending?: boolean };

const RAIL: RailItem[] = [
  { to: '/', label: 'Bench', icon: HomeIcon, key: 'h' },
  { group: 'Read' },
  { to: '/trawl', label: 'Trawl', icon: Import, key: 't' },
  { to: '/ledger', label: 'Ledger', icon: Table2, key: 'd' },
  { to: '/assay', label: 'Assay', icon: Gauge, key: 'v' },
  { group: 'Reason' },
  { to: '/geneos', label: 'geneOS', icon: FlaskConical, key: 'o' },
  { to: '/fermos', label: 'fermOS', icon: LineChart, key: 's' },
  { to: '/parchment', label: 'Parchment', icon: Scale, key: 'c' },
  { to: '/postdoc', label: 'Postdoc', icon: MessagesSquare, key: 'a' },
  { group: 'Return' },
  { to: '/runbook', label: 'Runbook', icon: ClipboardList, key: 'p' },
  { to: '/openlab', label: 'openLab', icon: Users, key: 'b' },
  { to: '/notary', label: 'Notary', icon: Stamp, key: 'y' },
  { to: '/learn', label: 'Learn', icon: GraduationCap, key: 'n' },
  // ── The demo suite (OF-DEMO-001) ─────────────────────────────────────
  //
  // Its own group, not folded into the three above. The two object pools are
  // deliberately separate and the rail is the first place a reader forms a
  // mental model of what this system holds; three demo entries scattered among
  // the casein ones would say they are the same corpus, which is the one thing
  // the interface must not say.
  //
  // `y` is Notary already and the demo queue is a sub-path of it, so it needs
  // no key of its own.
  { group: 'Demo suite' },
  { to: '/bench', label: 'Bench', icon: LayoutGrid, key: 'w' },
  { to: '/repo', label: 'BioRepo', icon: Database, key: 'r' },
  { to: '/proforma', label: 'Proforma', icon: Calculator, key: 'f' },
];

function isActive(path: string, to: string) {
  if (to === '/') return path === '/';
  return path === to || path.startsWith(to + '/');
}

// ── The demo suite (OF-DEMO-001) ───────────────────────────────────────
//
// A second, parallel pool alongside the casein corpus. Its routes are new
// (`/repo`, `/proforma`, `/bench`) or new SUB-paths of existing parts
// (`/fermos/gap`, `/geneos/routes`, `/postdoc/tree`, `/notary/disclosures`), so
// no casein screen changes and no screen serves both pools. Keeping them apart
// is what lets the interface tell the truth about both — an ExtractionRecord is
// a catalogued claim awaiting verification and an Accession is a normalised
// quantity with complete provenance, and they are not the same object.
import { Bench as DemoBench } from '@/screens/demo/Bench';
import { RepoIndex, AccessionPage, ParameterPage as DemoParameterPage, ContradictionQueue } from '@/screens/demo/Repo';
import { GapMap, FactorDetail, RunIndex, RunPage, EnvelopePage } from '@/screens/demo/Fermos';
import { RouteComparison, RouteDetail } from '@/screens/demo/Geneos';
import { ProformaIndex, CapacityScreen, CandidateDetail, FacilityConceptPage } from '@/screens/demo/Proforma';
import { ProblemTreePage } from '@/screens/demo/Postdoc';
import { NotaryQueue } from '@/screens/demo/NotaryQueue';

// ── Route dispatch ─────────────────────────────────────────────────────

/**
 * Old paths keep working, permanently (OF-FE-003 §6.1). docs/, the guided tour,
 * SHORTCUTS and the golden-path test all contain the pre-migration routes, and
 * a rename that breaks a deep link costs more than the rename gains. Four lines.
 */
const ALIAS: Record<string, string> = {
  library: 'trawl',
  extract: 'ledger',
  organisms: 'geneos',
  simulate: 'fermos',
  ask: 'postdoc',
  protocols: 'runbook',
};

/**
 * Map a pre-migration path onto its current one, or null when it is already
 * canonical. Resolved synchronously so the target screen renders on the first
 * pass: redirecting during render and returning null paints an empty frame
 * first, which is a visible flash for a user and an empty measurement for the
 * route smoke test.
 */
function canonicalize(segments: string[]): string[] | null {
  const [a, b, ...rest] = segments;
  if (!a) return null;
  if (a === 'extract' && b === 'validation') return ['assay', ...rest];
  if (a === 'extract' && !b) return ['ledger', 'records'];
  if (a === 'extract' && b !== 'review') return ['ledger', 'records', b, ...rest];
  if (a === 'library' && b === 'papers') return ['trawl', 'sources', ...rest];
  if (a === 'extract' && b === 'review') return ['trawl', 'review', ...rest];
  if (a === 'simulate' && b && b !== 'compare') return ['fermos', 's', b, ...rest];
  if (ALIAS[a]) return [ALIAS[a], ...(b ? [b] : []), ...rest];
  return null;
}

/**
 * Segment `i`, or ''. The dispatch destructures four segments and two demo
 * routes need a fifth (`/proforma/screen/:plant/c/:candidate`,
 * `/fermos/gap/:id/f/:factor`). Widening the destructure would touch every
 * existing branch for the sake of two.
 */
function segAt(segments: string[], i: number): string {
  return segments[i] ?? '';
}

function Screen() {
  const route = useRoute();
  const canonical = canonicalize(route.segments);

  // Render the target immediately; correct the address bar afterwards so a
  // shared link updates itself without ever showing the wrong screen.
  useEffect(() => {
    if (!canonical) return;
    const q = route.hash.includes('?') ? `?${route.hash.split('?')[1]}` : '';
    navigate(`/${canonical.join('/')}${q}`, { replace: true });
  }, [canonical?.join('/'), route.hash]);

  const [a, b, c, d] = canonical ?? route.segments;

  if (!a) return <Home />;
  switch (a) {
    case 'postdoc':
      if (b === 'tree' && c) return <ProblemTreePage deliverableId={c} />;
      return <Ask sessionId={b} initialQuery={route.query.get('q') ?? undefined} />;
    case 'trawl':
      if (b === 'ingest') return <Ingest />;
      if (b === 'review') return <Review />;
      if (b === 'sources' && c) return <PaperReader paperId={c} spanId={route.query.get('span') ?? undefined} />;
      return <Library />;
    case 'ledger':
      if (b === 'records') return <Extract />;
      if (b === 'contradictions') return <Contradictions />;
      if (b === 'p' && c) return <ParameterPage field={c as FieldId} />;
      return <Ledger />;
    case 'assay':
      return <Validation />;
    case 'parchment':
      return <Parchment />;
    case 'openlab':
      return <OpenLab />;
    case 'notary':
      // The demo queue lives one level down; `/notary` stays the casein
      // enablement checklist. Two pools, two screens, no screen serving both.
      if (b === 'disclosures') return <NotaryQueue />;
      return <Notary />;
    case 'bench':
      return <DemoBench />;
    case 'repo':
      if (b === 'a' && c) return <AccessionPage id={c} />;
      if (b === 'p' && c) return <DemoParameterPage field={c as never} />;
      if (b === 'contradictions') return <ContradictionQueue />;
      return <RepoIndex />;
    case 'proforma':
      if (b === 'screen' && c && d === 'c') return <CandidateDetail plantId={c} candidateId={segAt(canonical ?? route.segments, 4)} />;
      if (b === 'screen' && c) return <CapacityScreen plantId={c} />;
      if (b === 'concept' && c) return <FacilityConceptPage deliverableId={c} />;
      return <ProformaIndex />;
    case 'geneos':
      // `routes` before the strain branch: a strain id is a bare segment, so
      // `/geneos/routes/3-HP` would otherwise render a chassis page for a
      // strain called "routes".
      if (b === 'routes' && c && d) return <RouteDetail productId={c} routeId={d} />;
      if (b === 'routes' && c) return <RouteComparison productId={c} />;
      return b ? <StrainPage strainId={b} /> : <Organisms />;
    case 'runbook':
      if (b && c === 'run' && d) return <RunMode protocolId={b} runId={d} />;
      if (b && c === 'edit') return <ProtocolEditor protocolId={b} />;
      return b ? <ProtocolDetail protocolId={b} /> : <Protocols />;
    case 'fermos':
      if (b === 'gap' && c && d === 'f') return <FactorDetail deliverableId={c} factorId={segAt(canonical ?? route.segments, 4)} />;
      if (b === 'gap' && c) return <GapMap deliverableId={c} />;
      if (b === 'runs' && c) return <RunPage runId={c} />;
      if (b === 'runs') return <RunIndex />;
      if (b === 'envelope' && c) return <EnvelopePage plantId={c} />;
      if (b === 'compare') return <Compare />;
      if (b === 'd') return c ? <DesignDetail designId={c} /> : <DesignIndex />;
      if (b === 's' && c && d === 'plant') return <Plant scenarioId={c} />;
      if (b === 's' && c) return <ScenarioWorkspace scenarioId={c} />;
      return b ? <ScenarioWorkspace scenarioId={b} /> : <Simulate />;
    case 'learn':
      return b && c ? <Lesson moduleId={b} lessonId={c} /> : <Learn />;
    case 'settings':
      return <Settings section={b ?? 'appearance'} />;
    default:
      return (
        <div className="p-8">
          <h1 className="font-serif text-page-title font-semibold mb-2">Route not found</h1>
          <p className="text-ink-soft mb-4">
            <span className="font-num">{route.path}</span> doesn’t match a screen in this build.
          </p>
          <div className="flex gap-2">
            <button className="btn" onClick={() => navigate('/')}>
              Go Home
            </button>
            <button className="btn" onClick={() => window.location.reload()}>
              Retry
            </button>
          </div>
        </div>
      );
  }
}

// ── Demo banner (§7.1) ─────────────────────────────────────────────────

function DemoBanner() {
  const dismissed = useStore((s) => s.ui.bannerDismissed);
  const setUI = useStore((s) => s.setUI);
  if (dismissed) return null;
  return (
    <div className="h-8 shrink-0 flex items-center gap-2 px-3 border-b border-signal-warn/30 bg-signal-warn/[0.08] text-caption">
      <span
        className="inline-block w-[3px] h-4 rounded-[1px] shrink-0"
        style={{
          backgroundImage:
            'repeating-linear-gradient(to bottom, rgb(var(--signal-warn)) 0 3px, transparent 3px 6px)',
        }}
        aria-hidden
      />
      <span className="text-signal-warn font-medium">Real literature · modeled economics</span>
      <span className="text-ink-soft hidden sm:inline">
        — papers and values are real and citable. Simulation outputs are illustrative models,
        not validated economics. Session state resets on refresh.
      </span>
      <a href="#/settings/about" className="text-accent hover:underline hidden md:inline">
        Read the colophon
      </a>
      <button
        className="ml-auto text-ink-soft hover:text-ink"
        onClick={() => setUI({ bannerDismissed: true })}
        aria-label="Dismiss banner for this session"
        title="Dismiss for this session"
      >
        <X size={13} />
      </button>
    </div>
  );
}

// ── Help sheet (§9.6, Appendix A) ──────────────────────────────────────

function HelpSheet() {
  const open = useStore((s) => s.ui.helpOpen);
  const setUI = useStore((s) => s.setUI);
  return (
    <Sheet open={open} onClose={() => setUI({ helpOpen: false })} title="Keyboard shortcuts" width={520}>
      <div className="space-y-5">
        {SHORTCUTS.map((group) => (
          <div key={group.context}>
            <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
              {group.context}
            </div>
            <div className="space-y-1">
              {group.keys.map((k) => (
                <div key={k.key} className="flex items-baseline justify-between gap-4 text-body">
                  <span className="text-ink-soft">{k.does}</span>
                  <span className="kbd shrink-0">{k.key}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
        <div className="pt-3 border-t border-line">
          <button
            className="btn"
            onClick={() => {
              setUI({ helpOpen: false, tourStop: 0 });
            }}
          >
            Start guided tour
          </button>
        </div>
      </div>
    </Sheet>
  );
}

// ── Shell ──────────────────────────────────────────────────────────────

export default function App() {
  const ui = useStore((s) => s.ui);
  const setUI = useStore((s) => s.setUI);
  const jobs = useStore((s) => s.jobs);
  const activeRunId = useStore((s) => s.activeRunId);
  const tickJobs = useStore((s) => s.tickJobs);
  const tickTimers = useStore((s) => s.tickTimers);
  const route = useRoute();
  const [gPressed, setGPressed] = useState(false);
  const lastFrame = useRef(performance.now());

  // Canonicalised routes reach Run Mode as /runbook/:id/run/:runId; gating on
  // the pre-rename 'protocols' segment silently disabled the §8.12 takeover.
  const inRunMode = route.segments[0] === 'runbook' && route.segments[2] === 'run';

  // Theme / density / motion applied at the document root.
  useEffect(() => {
    document.documentElement.dataset.theme = ui.theme;
    document.documentElement.dataset.density = ui.density;
    document.documentElement.dataset.reducedMotion = String(ui.reducedMotion);
  }, [ui.theme, ui.density, ui.reducedMotion]);

  // Single animation loop drives job stages and run timers.
  useEffect(() => {
    let raf = 0;
    const loop = (now: number) => {
      const dt = now - lastFrame.current;
      lastFrame.current = now;
      if (dt > 0 && dt < 2000) {
        if (useStore.getState().jobs.some((j) => j.status === 'running')) tickJobs(dt);
        tickTimers(dt);
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [tickJobs, tickTimers]);

  // Warn before losing an active run (§21 no-persistence confusion).
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (useStore.getState().activeRunId) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, []);

  // Global shortcuts (Appendix A).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      const typing =
        el?.tagName === 'INPUT' || el?.tagName === 'TEXTAREA' || el?.isContentEditable;

      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setUI({ paletteOpen: true });
        return;
      }
      if (typing) return;

      if (e.key === '/') {
        e.preventDefault();
        setUI({ paletteOpen: true });
      } else if (e.key === '?') {
        e.preventDefault();
        setUI({ helpOpen: true });
      } else if (e.key === 'g') {
        setGPressed(true);
        window.setTimeout(() => setGPressed(false), 1200);
      } else if (gPressed) {
        const item = RAIL.find(
          (r): r is Extract<RailItem, { to: string }> =>
            !('group' in r) && r.key === e.key.toLowerCase(),
        );
        if (item) {
          e.preventDefault();
          navigate(item.to);
        }
        setGPressed(false);
      } else if (e.key === 'D' && e.shiftKey) {
        setUI({ density: ui.density === 'dense' ? 'comfortable' : 'dense' });
      } else if (e.key === 'T' && e.shiftKey) {
        setUI({ theme: ui.theme === 'bench' ? 'night' : 'bench' });
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [gPressed, setUI, ui.density, ui.theme]);

  const runningJobs = jobs.filter((j) => j.status === 'running').length + (activeRunId ? 1 : 0);

  // Run Mode is a full-screen takeover (§8.12).
  if (inRunMode) {
    return (
      <>
        <Screen />
        <Toasts />
      </>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <DemoBanner />
      <div className="flex-1 flex min-h-0">
        {/* Left rail */}
        <nav
          className={cx(
            'shrink-0 border-r border-line bg-surface-1 flex flex-col',
            ui.railCollapsed ? 'w-[52px]' : 'w-[188px]',
            'hidden md:flex',
          )}
          aria-label="Primary"
        >
          <div
            className={cx(
              'h-12 flex items-center border-b border-line',
              ui.railCollapsed ? 'justify-center px-0' : 'px-3',
            )}
          >
            <a href="#/" className="flex items-center gap-2 min-w-0">
              <span className="w-6 h-6 rounded bg-accent/12 border border-accent/30 grid place-items-center shrink-0">
                <FlaskConical size={13} className="text-accent" />
              </span>
              {!ui.railCollapsed && (
                <span className="font-serif text-[15px] leading-none truncate">
                  open<span className="font-semibold">Ferment</span>
                </span>
              )}
            </a>
          </div>

          <div className="flex-1 py-2 space-y-0.5 px-2 overflow-y-auto">
            {RAIL.map((item) => {
              if ('group' in item) {
                // Group headers name the architecture's three movements. Not
                // clickable — they are structure, not destinations.
                if (ui.railCollapsed) {
                  return <div key={item.group} className="h-px bg-line my-2 mx-2" aria-hidden />;
                }
                return (
                  <div
                    key={item.group}
                    className="text-caption uppercase tracking-wide text-ink-soft px-2 pt-3 pb-1 select-none"
                  >
                    {item.group}
                  </div>
                );
              }
              const active = isActive(route.path, item.to);
              const Icon = item.icon;
              return (
                <a
                  key={item.to}
                  href={`#${item.to}`}
                  className={cx(
                    'flex items-center gap-2.5 rounded-btn px-2 py-1.5 text-body transition-colors',
                    active
                      ? 'bg-accent-wash text-accent font-medium'
                      : 'text-ink-soft hover:text-ink hover:bg-ink-soft/[0.06]',
                    ui.railCollapsed && 'justify-center px-0',
                  )}
                  title={ui.railCollapsed ? item.label : undefined}
                  aria-current={active ? 'page' : undefined}
                >
                  <Icon size={ui.railCollapsed ? 18 : 16} className="shrink-0" />
                  {!ui.railCollapsed && (
                    <>
                      <span className={cx('truncate', item.pending && 'text-ink-soft/70')}>
                        {item.label}
                      </span>
                      {item.pending && (
                        // Named in the rail because the rail is the architecture,
                        // marked because the surface does not exist yet. A link
                        // that looks live and is not is worse than an honest gap.
                        <span
                          className="ml-auto text-caption text-ink-soft/60 shrink-0"
                          title="Specified, not yet built"
                        >
                          soon
                        </span>
                      )}
                    </>
                  )}
                </a>
              );
            })}
          </div>

          <div className="border-t border-line px-2 py-2 space-y-0.5">
            <a
              href="#/settings/appearance"
              className={cx(
                'flex items-center gap-2.5 rounded-btn px-2 py-1.5 text-body text-ink-soft hover:text-ink hover:bg-ink-soft/[0.06]',
                ui.railCollapsed && 'justify-center px-0',
              )}
              title="Settings"
            >
              <SettingsIcon size={16} className="shrink-0" />
              {!ui.railCollapsed && 'Settings'}
            </a>
            <button
              onClick={() => setUI({ helpOpen: true })}
              className={cx(
                'w-full flex items-center gap-2.5 rounded-btn px-2 py-1.5 text-body text-ink-soft hover:text-ink hover:bg-ink-soft/[0.06]',
                ui.railCollapsed && 'justify-center px-0',
              )}
              title="Help & shortcuts (?)"
            >
              <HelpCircle size={16} className="shrink-0" />
              {!ui.railCollapsed && 'Help'}
            </button>
            <button
              onClick={() => setUI({ railCollapsed: !ui.railCollapsed })}
              className={cx(
                'w-full flex items-center gap-2.5 rounded-btn px-2 py-1.5 text-body text-ink-soft hover:text-ink hover:bg-ink-soft/[0.06]',
                ui.railCollapsed && 'justify-center px-0',
              )}
              title={ui.railCollapsed ? 'Expand rail' : 'Collapse rail'}
            >
              {ui.railCollapsed ? <PanelLeftOpen size={16} /> : <PanelLeftClose size={16} />}
              {!ui.railCollapsed && 'Collapse'}
            </button>
          </div>
        </nav>

        {/* Content column */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Top utility bar */}
          <header className="h-12 shrink-0 border-b border-line bg-surface-1 flex items-center gap-2 px-3">
            <button
              className="md:hidden btn btn-sm"
              onClick={() => setUI({ paletteOpen: true })}
              aria-label="Menu"
            >
              <Search size={14} />
            </button>
            <button
              onClick={() => setUI({ paletteOpen: true })}
              className="hidden md:flex items-center gap-2 h-8 px-2.5 rounded-btn border border-line text-ink-soft hover:border-accent/40 hover:text-ink transition-colors min-w-[280px] max-w-[420px] flex-1"
            >
              <Search size={14} />
              <span className="text-body truncate">Search papers, parameters, protocols…</span>
              <span className="kbd ml-auto">⌘K</span>
            </button>

            <div className="flex-1" />

            {ui.simSpeed !== 1 && (
              <span className="chip text-signal-info border-signal-info/40" title="Simulated latency multiplier">
                {ui.simSpeed === Infinity ? 'instant' : `${ui.simSpeed}×`} speed
              </span>
            )}

            <Popover
              openOnHover={false}
              width={360}
              label="Jobs"
              trigger={(p) => (
                <button
                  {...p}
                  className="btn btn-sm relative"
                  title="Jobs tray"
                  aria-label={`Jobs tray, ${runningJobs} running`}
                >
                  <Activity size={14} />
                  <span className="hidden lg:inline">Jobs</span>
                  {runningJobs > 0 && (
                    <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-accent text-[10px] font-num grid place-items-center text-surface-1">
                      {runningJobs}
                    </span>
                  )}
                </button>
              )}
            >
              <JobsPanel onClose={() => {}} />
            </Popover>

            <button
              className="btn btn-sm"
              onClick={() => setUI({ density: ui.density === 'dense' ? 'comfortable' : 'dense' })}
              title={`Density: ${ui.density} (⇧D)`}
              aria-label={`Density: ${ui.density}`}
            >
              {ui.density === 'dense' ? <Rows4 size={14} /> : <Rows3 size={14} />}
            </button>
            <button
              className="btn btn-sm"
              onClick={() => setUI({ theme: ui.theme === 'bench' ? 'night' : 'bench' })}
              title={`Theme: ${ui.theme === 'bench' ? 'Bench' : 'Night Shift'} (⇧T)`}
              aria-label="Toggle theme"
            >
              {ui.theme === 'bench' ? <Sun size={14} /> : <Moon size={14} />}
            </button>
            <div
              className="w-7 h-7 rounded-full bg-accent/15 border border-accent/30 grid place-items-center text-caption font-medium text-accent"
              title="Signed in as demo curator"
            >
              SC
            </div>
          </header>

          <main id="of-main" className="flex-1 overflow-y-auto of-grid">
            <div className="p-5 max-w-[1600px]">
              <Screen />
            </div>
          </main>
        </div>
      </div>

      <CommandPalette />
      <HelpSheet />
      <GuidedTour />
      <Toasts />
    </div>
  );
}
