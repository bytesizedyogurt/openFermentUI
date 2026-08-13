/**
 * fermOS, answered from the bundled corpus and the engine already in the repo.
 *
 * ── THE JOB MODEL IS NOT A NEW ONE ────────────────────────────────────────
 *
 * `submitEvaluation` / `getEvaluation` exist because T2 and T3 will not fit in
 * a request/response: a reactor model and a Monte Carlo cash flow both outrun
 * any timeout worth setting. `src/sim/jobs.ts` had already worked out the
 * shape that survives that — a `JobRunner` that REPORTS positions instead of
 * deriving them, `done` reported rather than inferred from
 * `stageIndex >= stages.length`, and jobs a runner has no news about simply
 * omitted from its report rather than interpolated to keep a bar moving. This
 * file reuses those three interfaces rather than inventing a parallel set, and
 * `jobRunner()` below returns something the store's animation loop can drive
 * beside the simulated runner without either knowing about the other.
 *
 * The fixture's own jobs finish before `submitEvaluation` returns, because the
 * work is a grid interpolation and it is instant. It issues a handle anyway.
 * That is the point of doing this now: the CALL SHAPE is what cannot be
 * retrofitted, not the latency.
 */
import { SCENARIOS } from '@/data/source';
import { DESIGNS } from '@/data/designs';
import { COST_MODELS } from '@/data/scenarios';
import { buildGrid } from '@/engine/grids';
import { evaluateDesign } from '@/engine/designs';
import type { DesignRecord, JobStage, ResultGrid, Scenario } from '@/data/types';
import type {
  AdapterResponse,
  EvaluationRequest,
  EvaluationStatus,
  JobId,
  JobPosition,
  JobRunner,
  ProcessAdapter,
} from '@/adapters/types';
import { FIXTURE_DESIGN_MODEL_VERSION, respond } from './meta';

/**
 * The stages an evaluation runs through, named for the tiers.
 *
 * `ms: 0` on every one, and that is not a placeholder. A duration here would
 * be a declared budget for a runner to integrate, which is exactly the
 * simulation `src/sim/jobs.ts` quarantines — the fixture does no work worth
 * pacing, and a server reports its own stage boundaries as it crosses them
 * rather than announcing a schedule up front.
 */
const EVALUATION_STAGES: readonly JobStage[] = [
  { label: 'T0 · ontology bounds', ms: 0 },
  { label: 'T1 · flux', ms: 0 },
  { label: 'T2 · reactor', ms: 0 },
  { label: 'T3 · cost', ms: 0 },
];

/** A position that says the work is over. Reported, never inferred. */
const FINISHED: JobPosition = {
  stageIndex: EVALUATION_STAGES.length,
  stageProgress: 1,
  done: true,
};

/**
 * A position for a job that stopped without finishing. `done` is true — the
 * runner has no further news — while `status` carries the failure, because
 * "the work is over" and "the work succeeded" are different facts and the job
 * model keeps them apart on purpose.
 */
function stopped(stageIndex: number): JobPosition {
  return { stageIndex, stageProgress: 0, done: true };
}

interface EvaluationJob {
  status: EvaluationStatus;
}

const JOBS = new Map<JobId, EvaluationJob>();
let issued = 0;

/**
 * Grids, built on first use rather than at module scope.
 *
 * `src/data/designs.ts` builds the same set at import; this is a second cache
 * and not a second computation of consequence, because `evaluatePlantCached`
 * memoises the plant solves underneath both. Lazy because under the `api`
 * backend `SCENARIOS` is empty until `initCorpus()` resolves, and a grid built
 * at import would be a grid of nothing.
 */
const GRIDS = new Map<string, ResultGrid>();

function gridFor(modelId: string): ResultGrid | null {
  const hit = GRIDS.get(modelId);
  if (hit) return hit;
  const model = COST_MODELS.find((m) => m.modelId === modelId);
  if (!model) return null;
  const grid = buildGrid(model);
  GRIDS.set(modelId, grid);
  return grid;
}

function scenarioById(scenarioId: string): Scenario | undefined {
  return SCENARIOS.find((s) => s.id === scenarioId);
}

export const fixtureProcessAdapter: ProcessAdapter = {
  async listScenarios(): Promise<AdapterResponse<Scenario[]>> {
    return respond(SCENARIOS.slice());
  },

  async getScenario(scenarioId: string): Promise<AdapterResponse<Scenario | null>> {
    return respond(scenarioById(scenarioId) ?? null);
  },

  async listDesigns(scenarioId?: string): Promise<AdapterResponse<DesignRecord[]>> {
    const designs = scenarioId ? DESIGNS.filter((d) => d.scenarioId === scenarioId) : DESIGNS.slice();
    // Stamped with a model version because these are COMPUTED — every design
    // is a point in a sweep run through the cascade, not a row that was read.
    return respond(designs, { modelVersion: FIXTURE_DESIGN_MODEL_VERSION });
  },

  async getDesign(designId: string): Promise<AdapterResponse<DesignRecord | null>> {
    return respond(DESIGNS.find((d) => d.id === designId) ?? null, {
      modelVersion: FIXTURE_DESIGN_MODEL_VERSION,
    });
  },

  async submitEvaluation(request: EvaluationRequest): Promise<AdapterResponse<JobId>> {
    const scenario = scenarioById(request.scenarioId);
    // An unknown scenario is a bad request, not a failed job: it is rejected
    // at submission, where a server would reject it, rather than issuing a
    // handle to a job that was never going to run.
    if (!scenario) {
      throw new Error(
        `openFerment adapters: submitEvaluation — no scenario '${request.scenarioId}'.`,
      );
    }

    const jobId: JobId = `fx-eval-${++issued}`;
    const grid = gridFor(scenario.modelId);

    if (!grid) {
      // A real failure of the work, collected through the handle like any
      // other outcome. `failReason` names the model, because "evaluation
      // failed" is not something anyone can act on.
      JOBS.set(jobId, {
        status: {
          jobId,
          status: 'failed',
          position: stopped(3),
          stages: EVALUATION_STAGES,
          failReason: `No cost model '${scenario.modelId}' — T3 cannot be evaluated.`,
        },
      });
      return respond(jobId, { modelVersion: FIXTURE_DESIGN_MODEL_VERSION });
    }

    // The same function `designsFor` uses for a sweep corner, so an arbitrary
    // configuration and a seeded design come back through one code path and
    // one set of absent-tier reasons.
    const result = evaluateDesign(scenario, grid, request.config, {
      id: `${scenario.id}-${jobId}`,
      label: request.label ?? `${scenario.name} — evaluated`,
    });

    JOBS.set(jobId, {
      status: { jobId, status: 'done', position: FINISHED, stages: EVALUATION_STAGES, result },
    });
    return respond(jobId, { modelVersion: FIXTURE_DESIGN_MODEL_VERSION });
  },

  async getEvaluation(jobId: JobId): Promise<AdapterResponse<EvaluationStatus>> {
    const job = JOBS.get(jobId);
    // An unknown handle REJECTS rather than returning an empty status. The
    // same rule `search()` follows in src/data/source.ts: a blank answer is
    // indistinguishable from a real one and is the worse failure.
    if (!job) {
      throw new Error(`openFerment adapters: getEvaluation — unknown job '${jobId}'.`);
    }
    return respond(job.status, { modelVersion: FIXTURE_DESIGN_MODEL_VERSION });
  },

  /**
   * The runner for this adapter's jobs.
   *
   * It reports every evaluation it is holding and NOTHING ELSE — ingest and
   * extraction jobs belong to whatever else is running them, and a runner that
   * answered for a job it knows nothing about would be inventing progress.
   * `src/sim/jobs.ts` makes omission the defined behaviour precisely so two
   * runners can coexist during a changeover.
   *
   * Every position it reports is terminal, because every job it holds finished
   * during `submitEvaluation`. A server-backed runner returns the last report
   * it received instead, and nothing above it changes.
   */
  jobRunner(): JobRunner {
    return {
      report(jobs) {
        const out = new Map<string, JobPosition>();
        for (const j of jobs) {
          const held = JOBS.get(j.id);
          if (held) out.set(j.id, held.status.position);
        }
        return out;
      },
    };
  },
};
