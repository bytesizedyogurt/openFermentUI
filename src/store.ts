// Single store (OF-DES-001 §13.3). All mutations flow through actions so
// provenance-affecting changes fan out to derived views in one place.
// No localStorage/sessionStorage anywhere — session-only by design (§9.5).
import { create } from 'zustand';
import type {
  ActivityEvent,
  ChatMessage,
  ChatSession,
  Collection,
  Deviation,
  Contradiction,
  ExtractionRecord,
  Job,
  LearnModule,
  Paper,
  Protocol,
  Provenance,
  RecordStatus,
  ResultGrid,
  RunOutput,
  RunState,
  Scenario,
  Strain,
  TimerState,
} from '@/data/types';
import { PAPERS } from '@/data/papers';
import { CONTRADICTIONS } from '@/data/contradictions';
import { RECORDS } from '@/data/records';
import { RUN_OUTPUTS } from '@/data/runOutputs';
import { STRAINS } from '@/data/strains';
import { PROTOCOLS } from '@/data/protocols';
import { SCENARIOS, COST_MODELS } from '@/data/scenarios';
import { MODULES } from '@/data/learn';
import { COLLECTIONS, ACTIVITY, SEED_SESSIONS } from '@/data/misc';
import { buildGrid } from '@/engine/grids';
import { toSI } from '@/engine/units';

export type Theme = 'bench' | 'night';
export type Density = 'comfortable' | 'dense';
export type UnitMode = 'published' | 'si';

export interface Toast {
  id: string;
  text: string;
  kind: 'info' | 'success' | 'warn' | 'error';
  href?: string;
  hrefLabel?: string;
}

interface UndoFrame {
  records: ExtractionRecord[];
  queueIndex: number;
  label: string;
}

let seq = 0;
export const nextId = (prefix: string) => `${prefix}-${++seq}`;

/** Deterministic clock-free timestamp label for audit entries. */
function stamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

export interface OFState {
  // ── seeded data (session-mutable) ────────────────────────────────────
  papers: Paper[];
  records: ExtractionRecord[];
  /**
   * Derived by the referee at load, not authored — see data/contradictions.ts.
   * Held in the store so a review edit can re-run the checks and the queue can
   * carry curator status alongside the finding.
   */
  contradictions: Contradiction[];
  runOutputs: RunOutput[];
  strains: Strain[];
  protocols: Protocol[];
  scenarios: Scenario[];
  grids: Record<string, ResultGrid>;
  collections: Collection[];
  modules: LearnModule[];
  activity: ActivityEvent[];
  sessions: ChatSession[];

  // ── runtime ──────────────────────────────────────────────────────────
  runs: Record<string, RunState>;
  activeRunId: string | null;
  jobs: Job[];
  toasts: Toast[];
  reviewQueue: string[];
  reviewIndex: number;
  reviewStats: { accepted: number; rejected: number; edited: number; skipped: number; gold: number; startedAt: number };
  undoStack: UndoFrame[];
  learnProgress: Record<string, boolean>;
  checkpointAnswers: Record<string, boolean>;
  exports: { name: string; at: string; rows: number }[];

  ui: {
    theme: Theme;
    density: Density;
    simSpeed: number; // 1, 4, or Infinity (instant)
    reducedMotion: boolean;
    unitMode: UnitMode;
    bannerDismissed: boolean;
    paletteOpen: boolean;
    jobsOpen: boolean;
    inspectorOpen: boolean;
    sessionsOpen: boolean;
    railCollapsed: boolean;
    tourStop: number | null;
    helpOpen: boolean;
    chatMode: 'scripted' | 'live';
  };

  // ── actions ──────────────────────────────────────────────────────────
  setUI: (patch: Partial<OFState['ui']>) => void;
  toast: (t: Omit<Toast, 'id'>) => void;
  dismissToast: (id: string) => void;

  // records / review
  startReview: (ids: string[]) => void;
  reviewDecide: (
    id: string,
    action: 'accept' | 'reject' | 'skip' | 'gold',
    payload?: { reason?: string },
  ) => void;
  editRecord: (id: string, value: number, unit: string) => void;
  setRecordStatus: (id: string, status: RecordStatus, reason?: string) => void;
  undoReview: () => void;
  advanceReview: (delta: number) => void;
  /**
   * File a coverage dispute against a source (OF-FE-003 §8.4). Recall failure
   * is the failure that hides: a wrong value gets clicked and corrected, a
   * missed one is invisible forever. Filing returns the source to the review
   * queue rather than parking a passive annotation on it.
   */
  disputeCoverage: (paperId: string, note: string) => void;

  // jobs
  startJob: (job: Omit<Job, 'id' | 'stageIndex' | 'stageProgress' | 'status' | 'startedAt'>) => string;
  tickJobs: (dtMs: number) => void;
  failJob: (id: string, reason: string) => void;
  clearJobs: () => void;

  // ingest
  ingestPaper: (paperId: string) => void;
  setPaperIngest: (paperId: string, status: Paper['ingest']) => void;

  // protocols / runs
  startRun: (protocolId: string, version: string, scale: number) => string;
  completeStep: (runId: string, stepId: string) => void;
  uncompleteStep: (runId: string, stepId: string) => void;
  skipStep: (runId: string, stepId: string, reason: string) => void;
  setRunStep: (runId: string, index: number) => void;
  toggleCheck: (runId: string, stepId: string, idx: number) => void;
  addDeviation: (runId: string, d: Deviation) => void;
  addTimer: (runId: string, t: Omit<TimerState, 'running' | 'remainingSec'>) => void;
  toggleTimer: (runId: string, timerId: string) => void;
  extendTimer: (runId: string, timerId: string, sec: number) => void;
  dismissTimer: (runId: string, timerId: string) => void;
  tickTimers: (dtMs: number) => void;
  finishRun: (runId: string) => void;
  addProtocolVersion: (protocolId: string, version: Protocol['versions'][number]) => void;

  // scenarios
  setScenarioPoint: (id: string, point: Record<string, number>) => void;
  togglePin: (id: string) => void;
  duplicateScenario: (id: string) => string;

  // chat
  createSession: (title: string, scope?: ChatSession['scope']) => string;
  appendMessage: (sessionId: string, msg: ChatMessage) => void;
  updateMessage: (sessionId: string, msgId: string, patch: Partial<ChatMessage>) => void;
  pinEvidence: (sessionId: string, hits: ChatSession['pinned']) => void;

  // learn
  completeLesson: (lessonId: string) => void;
  recordCheckpoint: (qid: string, correct: boolean) => void;

  // misc
  logActivity: (e: ActivityEvent) => void;
  logExport: (name: string, rows: number) => void;
  addCollectionPapers: (collectionId: string, paperIds: string[]) => void;
  resetDemo: () => void;
}

const seedGrids = (): Record<string, ResultGrid> =>
  Object.fromEntries(COST_MODELS.map((m) => [m.modelId, buildGrid(m)]));

const seedState = () => ({
  papers: structuredClone(PAPERS),
  records: structuredClone(RECORDS),
  contradictions: structuredClone(CONTRADICTIONS),
  runOutputs: structuredClone(RUN_OUTPUTS),
  strains: structuredClone(STRAINS),
  protocols: structuredClone(PROTOCOLS),
  scenarios: structuredClone(SCENARIOS),
  collections: structuredClone(COLLECTIONS),
  modules: structuredClone(MODULES),
  activity: structuredClone(ACTIVITY),
  sessions: structuredClone(SEED_SESSIONS),
  runs: {} as Record<string, RunState>,
  activeRunId: null,
  jobs: [] as Job[],
  reviewQueue: [] as string[],
  reviewIndex: 0,
  reviewStats: { accepted: 0, rejected: 0, edited: 0, skipped: 0, gold: 0, startedAt: Date.now() },
  undoStack: [] as UndoFrame[],
  learnProgress: {} as Record<string, boolean>,
  checkpointAnswers: {} as Record<string, boolean>,
  exports: [] as { name: string; at: string; rows: number }[],
});

/**
 * Open in the viewer's theme rather than always in Bench. Night Shift exists
 * for late lab sessions and projector-hostile rooms (§6.2); starting in the
 * wrong one and making the user find the toggle is a small rudeness. The top
 * bar toggle still wins once touched.
 */
function initialTheme(): Theme {
  if (typeof window === 'undefined' || !window.matchMedia) return 'bench';
  const stamped = document.documentElement.dataset.theme;
  if (stamped === 'dark') return 'night';
  if (stamped === 'light') return 'bench';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'night' : 'bench';
}

export const useStore = create<OFState>()((set, get) => ({
  ...seedState(),
  grids: seedGrids(),
  toasts: [],
  ui: {
    theme: initialTheme(),
    density: 'comfortable',
    simSpeed: 1,
    reducedMotion: false,
    unitMode: 'published',
    bannerDismissed: false,
    paletteOpen: false,
    jobsOpen: false,
    inspectorOpen: true,
    sessionsOpen: true,
    railCollapsed: false,
    tourStop: null,
    helpOpen: false,
    chatMode: 'scripted',
  },

  setUI: (patch) => set((s) => ({ ui: { ...s.ui, ...patch } })),

  toast: (t) => {
    const id = nextId('toast');
    set((s) => ({ toasts: [...s.toasts.slice(-2), { ...t, id }] }));
    setTimeout(() => get().dismissToast(id), 6000);
  },
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  // ── review ───────────────────────────────────────────────────────────
  startReview: (ids) =>
    set({
      reviewQueue: ids,
      reviewIndex: 0,
      undoStack: [],
      reviewStats: { accepted: 0, rejected: 0, edited: 0, skipped: 0, gold: 0, startedAt: Date.now() },
    }),

  reviewDecide: (id, action, payload) => {
    const s = get();
    const frame: UndoFrame = {
      records: structuredClone(s.records),
      queueIndex: s.reviewIndex,
      label: action,
    };
    const stats = { ...s.reviewStats };
    const records = s.records.map((r) => {
      if (r.id !== id) return r;
      const audit = [...r.audit];
      if (action === 'accept') {
        audit.push({ at: stamp(), who: 'you', action: 'verified' });
        stats.accepted++;
        return { ...r, status: 'verified' as RecordStatus, reviewer: 'you', audit };
      }
      if (action === 'reject') {
        audit.push({ at: stamp(), who: 'you', action: `rejected — ${payload?.reason ?? 'unspecified'}` });
        stats.rejected++;
        return {
          ...r,
          status: 'rejected' as RecordStatus,
          reviewer: 'you',
          rejectReason: payload?.reason,
          audit,
        };
      }
      if (action === 'gold') {
        audit.push({ at: stamp(), who: 'you', action: 'flagged for gold set' });
        stats.gold++;
        return {
          ...r,
          status: 'verified' as RecordStatus,
          reviewer: 'you',
          gold: r.gold ?? { value: r.corrected?.value ?? r.value, unit: r.corrected?.unit ?? r.unit },
          audit,
        };
      }
      stats.skipped++;
      return r;
    });
    set({
      records,
      undoStack: [...s.undoStack.slice(-25), frame],
      reviewStats: stats,
      reviewIndex: Math.min(s.reviewIndex + 1, s.reviewQueue.length),
    });
  },

  editRecord: (id, value, unit) => {
    const s = get();
    const frame: UndoFrame = {
      records: structuredClone(s.records),
      queueIndex: s.reviewIndex,
      label: 'edit',
    };
    const records = s.records.map((r) => {
      if (r.id !== id) return r;
      const si = toSI(value, unit);
      return {
        ...r,
        corrected: { value, unit },
        value,
        unit,
        si,
        audit: [
          ...r.audit,
          {
            at: stamp(),
            who: 'you',
            action: 'edited value',
            from: `${r.value} ${r.unit}`,
            to: `${value} ${unit}`,
          },
        ],
      };
    });
    set({
      records,
      undoStack: [...s.undoStack.slice(-25), frame],
      reviewStats: { ...s.reviewStats, edited: s.reviewStats.edited + 1 },
    });
  },

  setRecordStatus: (id, status, reason) =>
    set((s) => ({
      records: s.records.map((r) =>
        r.id === id
          ? {
              ...r,
              status,
              reviewer: 'you',
              rejectReason: reason ?? r.rejectReason,
              audit: [...r.audit, { at: stamp(), who: 'you', action: `set ${status}` }],
            }
          : r,
      ),
    })),

  undoReview: () => {
    const s = get();
    const frame = s.undoStack[s.undoStack.length - 1];
    if (!frame) return;
    set({
      records: frame.records,
      reviewIndex: frame.queueIndex,
      undoStack: s.undoStack.slice(0, -1),
    });
  },

  advanceReview: (delta) =>
    set((s) => ({
      reviewIndex: Math.max(0, Math.min(s.reviewIndex + delta, s.reviewQueue.length)),
    })),

  // ── jobs ─────────────────────────────────────────────────────────────
  startJob: (job) => {
    const id = nextId('job');
    set((s) => ({
      jobs: [
        ...s.jobs,
        { ...job, id, stageIndex: 0, stageProgress: 0, status: 'running', startedAt: Date.now() },
      ],
    }));
    return id;
  },

  tickJobs: (dtMs) => {
    const speed = get().ui.simSpeed;
    const dt = speed === Infinity ? 1e9 : dtMs * speed;
    const finishedJobs: Job[] = [];
    set((s) => ({
      jobs: s.jobs.map((j) => {
        if (j.status !== 'running') return j;
        let { stageIndex, stageProgress } = j;
        let budget = dt;
        while (budget > 0 && stageIndex < j.stages.length) {
          const stage = j.stages[stageIndex];
          const remaining = stage.ms * (1 - stageProgress);
          if (budget >= remaining) {
            budget -= remaining;
            stageIndex += 1;
            stageProgress = 0;
          } else {
            stageProgress += budget / stage.ms;
            budget = 0;
          }
        }
        if (stageIndex >= j.stages.length) {
          const done: Job = { ...j, stageIndex: j.stages.length, stageProgress: 1, status: 'done' };
          finishedJobs.push(done);
          return done;
        }
        return { ...j, stageIndex, stageProgress };
      }),
    }));
    for (const j of finishedJobs) {
      get().toast({
        text: `${j.title} — complete`,
        kind: 'success',
        href: j.href,
        hrefLabel: j.href ? 'View' : undefined,
      });
      if (j.kind === 'ingest') {
        const paperId = j.href?.split('/').pop() ?? '';
        if (paperId) get().setPaperIngest(paperId, 'complete');
      }
    }
  },

  failJob: (id, reason) =>
    set((s) => ({
      jobs: s.jobs.map((j) => (j.id === id ? { ...j, status: 'failed', failReason: reason } : j)),
    })),

  clearJobs: () => set((s) => ({ jobs: s.jobs.filter((j) => j.status === 'running') })),

  // ── ingest ───────────────────────────────────────────────────────────
  ingestPaper: (paperId) => {
    const paper = get().papers.find((p) => p.id === paperId);
    if (!paper) return;
    // With a real corpus, ingestion needs the source document — and this build
    // has none. Open-access entries would be fetchable with network access;
    // paywalled ones need institutional credentials. Either way the pipeline
    // halts at Fetch rather than pretending to parse something it never got.
    const fails = true;
    get().setPaperIngest(paperId, 'stage:fetch');
    const id = get().startJob({
      title: `Ingest ${paperId}`,
      kind: 'ingest',
      stages: [
        { label: 'Fetch', ms: 900 },
        { label: 'Parse', ms: 1400 },
        { label: 'Chunk', ms: 700 },
        { label: 'Embed', ms: 1100 },
        { label: 'Extract', ms: 1800 },
      ],
      href: `#/library/papers/${paperId}`,
    });
    if (fails) {
      // Scripted failure path (§8.5): halts at Parse with a specific reason.
      const speed = get().ui.simSpeed;
      const wait = speed === Infinity ? 50 : 900 / speed;
      const reason = paper.openAccess
        ? `Source not retrieved — ${paper.doi ? `DOI ${paper.doi}` : paper.pmcid ?? 'the record'} is open access, but this build makes no network requests.`
        : 'Source not retrieved — publisher requires institutional access. Fetch this one manually and re-run.';
      setTimeout(() => {
        get().failJob(id, reason);
        get().setPaperIngest(paperId, 'failed:fetch');
        get().toast({
          text: `Ingest ${paperId} halted at Fetch`,
          kind: 'error',
          href: '#/library/ingest',
          hrefLabel: 'Review',
        });
      }, wait);
    }
    get().logActivity({
      at: stamp(),
      icon: 'download',
      text: `Ingest started for ${paperId}`,
      href: `#/library/ingest`,
      provenance: 'demo',
    });
  },

  setPaperIngest: (paperId, status) =>
    set((s) => ({
      papers: s.papers.map((p) => (p.id === paperId ? { ...p, ingest: status } : p)),
    })),

  // ── runs ─────────────────────────────────────────────────────────────
  startRun: (protocolId, version, scale) => {
    const id = nextId('run');
    const run: RunState = {
      id,
      protocolId,
      version,
      scale,
      startedAt: Date.now(),
      currentStep: 0,
      completed: {},
      skipped: {},
      checks: {},
      deviations: [],
      timers: [],
    };
    set((s) => ({ runs: { ...s.runs, [id]: run }, activeRunId: id }));
    return id;
  },

  completeStep: (runId, stepId) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: {
          ...s.runs,
          [runId]: { ...run, completed: { ...run.completed, [stepId]: Date.now() } },
        },
      };
    }),

  uncompleteStep: (runId, stepId) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      const completed = { ...run.completed };
      delete completed[stepId];
      return { runs: { ...s.runs, [runId]: { ...run, completed } } };
    }),

  skipStep: (runId, stepId, reason) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: { ...s.runs, [runId]: { ...run, skipped: { ...run.skipped, [stepId]: reason } } },
      };
    }),

  setRunStep: (runId, index) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return { runs: { ...s.runs, [runId]: { ...run, currentStep: Math.max(0, index) } } };
    }),

  toggleCheck: (runId, stepId, idx) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      const arr = [...(run.checks[stepId] ?? [])];
      arr[idx] = !arr[idx];
      return { runs: { ...s.runs, [runId]: { ...run, checks: { ...run.checks, [stepId]: arr } } } };
    }),

  addDeviation: (runId, d) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return { runs: { ...s.runs, [runId]: { ...run, deviations: [...run.deviations, d] } } };
    }),

  addTimer: (runId, t) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      if (run.timers.some((x) => x.id === t.id)) return {};
      const timer: TimerState = { ...t, remainingSec: t.totalSec, running: true, startedAt: Date.now() };
      return { runs: { ...s.runs, [runId]: { ...run, timers: [...run.timers, timer] } } };
    }),

  toggleTimer: (runId, timerId) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: {
          ...s.runs,
          [runId]: {
            ...run,
            timers: run.timers.map((t) => (t.id === timerId ? { ...t, running: !t.running } : t)),
          },
        },
      };
    }),

  extendTimer: (runId, timerId, sec) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: {
          ...s.runs,
          [runId]: {
            ...run,
            timers: run.timers.map((t) =>
              t.id === timerId
                ? { ...t, remainingSec: t.remainingSec + sec, totalSec: t.totalSec + sec }
                : t,
            ),
          },
        },
      };
    }),

  dismissTimer: (runId, timerId) =>
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: { ...s.runs, [runId]: { ...run, timers: run.timers.filter((t) => t.id !== timerId) } },
      };
    }),

  tickTimers: (dtMs) => {
    const s = get();
    const speed = s.ui.simSpeed === Infinity ? 60 : s.ui.simSpeed;
    const dt = (dtMs / 1000) * speed;
    const finishedTimers: TimerState[] = [];
    const runs = { ...s.runs };
    let changed = false;
    for (const [id, run] of Object.entries(runs)) {
      if (!run.timers.some((t) => t.running && t.remainingSec > 0)) continue;
      changed = true;
      runs[id] = {
        ...run,
        timers: run.timers.map((t) => {
          if (!t.running || t.remainingSec <= 0) return t;
          const remainingSec = Math.max(0, t.remainingSec - dt);
          if (remainingSec === 0) finishedTimers.push({ ...t, remainingSec, running: false });
          return { ...t, remainingSec, running: remainingSec > 0 };
        }),
      };
    }
    if (changed) set({ runs });
    for (const f of finishedTimers) {
      get().toast({ text: `Timer complete — ${f.label}`, kind: 'success' });
    }
  },

  finishRun: (runId) => {
    set((s) => {
      const run = s.runs[runId];
      if (!run) return {};
      return {
        runs: { ...s.runs, [runId]: { ...run, finishedAt: Date.now() } },
        activeRunId: s.activeRunId === runId ? null : s.activeRunId,
      };
    });
    const run = get().runs[runId];
    const proto = get().protocols.find((p) => p.id === run?.protocolId);
    if (proto) {
      get().logActivity({
        at: stamp(),
        icon: 'check',
        text: `Run completed — ${proto.title}`,
        href: `#/protocols/${proto.id}`,
        provenance: 'user',
      });
    }
  },

  addProtocolVersion: (protocolId, version) =>
    set((s) => ({
      protocols: s.protocols.map((p) =>
        p.id === protocolId
          ? { ...p, versions: [...p.versions, version], currentVersion: version.version }
          : p,
      ),
    })),

  // ── scenarios ────────────────────────────────────────────────────────
  setScenarioPoint: (id, point) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) => (sc.id === id ? { ...sc, point: { ...sc.point, ...point } } : sc)),
    })),

  togglePin: (id) =>
    set((s) => ({
      scenarios: s.scenarios.map((sc) => (sc.id === id ? { ...sc, pinned: !sc.pinned } : sc)),
    })),

  duplicateScenario: (id) => {
    const s = get();
    const src = s.scenarios.find((x) => x.id === id);
    if (!src) return id;
    const copy: Scenario = {
      ...structuredClone(src),
      id: nextId('sc'),
      name: `${src.name} (copy)`,
      pinned: false,
    };
    set({ scenarios: [...s.scenarios, copy] });
    return copy.id;
  },

  // ── chat ─────────────────────────────────────────────────────────────
  createSession: (title, scope) => {
    const id = nextId('sess');
    const session: ChatSession = { id, title, startedAt: stamp(), scope, messages: [], pinned: [] };
    set((s) => ({ sessions: [session, ...s.sessions] }));
    return id;
  },

  appendMessage: (sessionId, msg) =>
    set((s) => ({
      sessions: s.sessions.map((x) =>
        x.id === sessionId ? { ...x, messages: [...x.messages, msg] } : x,
      ),
    })),

  updateMessage: (sessionId, msgId, patch) =>
    set((s) => ({
      sessions: s.sessions.map((x) =>
        x.id === sessionId
          ? {
              ...x,
              messages: x.messages.map((m) =>
                m.id === msgId ? ({ ...m, ...patch } as ChatMessage) : m,
              ),
            }
          : x,
      ),
    })),

  pinEvidence: (sessionId, hits) =>
    set((s) => ({
      sessions: s.sessions.map((x) => {
        if (x.id !== sessionId) return x;
        const seen = new Set(x.pinned.map((p) => `${p.paperId}:${p.sectionId}`));
        const add = hits.filter((h) => !seen.has(`${h.paperId}:${h.sectionId}`));
        return { ...x, pinned: [...x.pinned, ...add] };
      }),
    })),

  // ── learn ────────────────────────────────────────────────────────────
  completeLesson: (lessonId) =>
    set((s) => ({ learnProgress: { ...s.learnProgress, [lessonId]: true } })),

  recordCheckpoint: (qid, correct) =>
    set((s) => ({ checkpointAnswers: { ...s.checkpointAnswers, [qid]: correct } })),

  // ── misc ─────────────────────────────────────────────────────────────
  disputeCoverage: (paperId, note) => {
    const at = stamp();
    set((s) => ({
      papers: s.papers.map((p) =>
        p.id === paperId ? { ...p, coverageDisputed: { note, at } } : p,
      ),
      // Back into the queue, at the front — a source somebody has looked at and
      // found wanting is a better use of review time than the next one in line.
      reviewQueue: s.reviewQueue.includes(paperId)
        ? s.reviewQueue
        : [paperId, ...s.reviewQueue],
    }));
    get().logActivity({
      at,
      icon: 'flag',
      text: `Coverage disputed on ${paperId}: ${note}`,
      href: `/trawl/sources/${paperId}`,
      provenance: 'user',
    });
    get().toast({ text: 'Filed. This source is back in the review queue.', kind: 'info' });
  },

  logActivity: (e) => set((s) => ({ activity: [e, ...s.activity].slice(0, 40) })),

  logExport: (name, rows) =>
    set((s) => ({ exports: [{ name, at: stamp(), rows }, ...s.exports].slice(0, 30) })),

  addCollectionPapers: (collectionId, paperIds) =>
    set((s) => ({
      collections: s.collections.map((c) =>
        c.id === collectionId
          ? { ...c, paperIds: Array.from(new Set([...c.paperIds, ...paperIds])) }
          : c,
      ),
    })),

  resetDemo: () => {
    set({ ...seedState(), grids: seedGrids(), toasts: [] });
    get().toast({
      text: 'Workspace restored to the seeded corpus — review decisions, runs and scenario edits discarded',
      kind: 'info',
    });
  },
}));

// ── derived selectors ──────────────────────────────────────────────────

// Aggregation policy now lives in engine/aggregation.ts — pure functions of a
// record, needed by engine modules that must not import app state. Re-exported
// here so every existing call site keeps working unchanged.
export {
  provenanceOf,
  aggregateExclusion,
  isAggregatable,
  EXCLUSION_NOTE,
} from '@/engine/aggregation';
export type { AggregateExclusion } from '@/engine/aggregation';

export const tickClass = (p: Provenance | 'rejected'): string =>
  ({
    gold: 'tick tick-gold',
    verified: 'tick tick-verified',
    curated: 'tick tick-curated',
    unverified: 'tick tick-unverified',
    user: 'tick tick-user',
    'industry-estimate': 'tick tick-industry-estimate',
    demo: 'tick tick-demo',
    rejected: 'tick tick-rejected',
    unsourced: 'tick tick-unsourced',
  })[p];

export const PROVENANCE_LABEL: Record<Provenance, string> = {
  gold: 'Curated · gold set',
  verified: 'Verified against source',
  curated: 'Curated · pending source check',
  unverified: 'Extracted · unverified',
  user: 'User-entered',
  'industry-estimate': 'Industry estimate · not evidence',
  demo: 'Modeled · not measured',
  unsourced: 'UNSOURCED — no provenance record',
};
