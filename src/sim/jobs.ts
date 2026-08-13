// SIMULATION — REMOVED WITH THE SCRIPTED AGENT.
//
// Removed in: the final migration phase, the one that lands the real job
// runner. `sim/` is retired last, by design (README, Architecture).
// Replaced by: an implementation of `JobRunner` fed by the server — progress
// reported over a socket or a poll, not integrated from a millisecond budget.
// The interface below is the whole of what has to be re-implemented; when it
// is, this file is deleted and one line in `store.ts` changes.
//
// ── What this file is ─────────────────────────────────────────────────
//
// The pacing of a job, and nothing else. A job's existence, its stages, its
// status, and everything that happens when it finishes stay in `store.ts`,
// because a real runner does all of that too. What a real runner does NOT do
// is compute where a job has got to from the durations someone declared for
// its stages — it is told, by the thing actually doing the work. That
// computation is the simulation, so it lives here.
//
// This is the seam the README used to flag as unclean: the simulated pacing
// lived in `store.ts` next to the real job bookkeeping, so retiring the
// simulation meant unpicking the store. It no longer does.
import type { JobStage } from '@/data/types';

/**
 * The part of a job a runner is allowed to see.
 *
 * Deliberately narrower than `Job`: a runner has no business with the title,
 * the href, the toast, or the paper the job belongs to. It answers one
 * question — where is this job now — and `id` is how it says which job it is
 * answering about.
 *
 * `stages` is here because the SIMULATED runner needs the declared durations.
 * A server-backed runner ignores it; the server knows the real stage list.
 */
export interface PacedJob {
  readonly id: string;
  readonly stages: readonly JobStage[];
  readonly stageIndex: number;
  readonly stageProgress: number;
}

/**
 * Where a job has got to, as reported by a runner.
 *
 * `done` is reported, not derived. The simulated runner sets it when it has
 * consumed every declared stage; a real runner sets it when the server says
 * the work finished. The store must not infer completion from
 * `stageIndex >= stages.length` — that inference is exactly the simulation.
 */
export interface JobPosition {
  /** Index of the stage now in flight; equals `stages.length` when done. */
  readonly stageIndex: number;
  /** 0–1 within `stageIndex`. */
  readonly stageProgress: number;
  readonly done: boolean;
}

/**
 * A source of job progress.
 *
 * The store owns jobs; a `JobRunner` owns only the answer to "where has each
 * one got to?". `report` is called from the animation loop for every running
 * job, and returns a position for each job it has an opinion about. **Jobs it
 * omits are left exactly as they are** — that is the affordance a real runner
 * needs, because between two server messages the honest answer is "no news",
 * not a position interpolated to keep a bar moving.
 *
 * A real implementation differs in three ways:
 *
 *   1. It does not read `elapsedMs`. Elapsed wall-clock time is only useful to
 *      something integrating a budget. A server-backed runner keeps the last
 *      report it received from a socket, an SSE stream or a poll, and returns
 *      that — `report` stays synchronous because the store is driven by a
 *      requestAnimationFrame loop; the network work happens outside it.
 *   2. It reports fewer jobs, and sometimes none. Progress arrives when the
 *      server sends it. Returning an empty map is the correct behaviour on a
 *      frame where nothing new was heard.
 *   3. It can report a stage the client never declared, and can go backwards
 *      (a retried stage). Nothing here forbids either; the simulated runner
 *      simply never does it.
 *
 * A runner reports progress. It does not decide what progress means.
 */
export interface JobRunner {
  report(jobs: readonly PacedJob[], elapsedMs: number): Map<string, JobPosition>;
}

/**
 * The simulated runner: advance each job through its declared `stage.ms`
 * durations, scaled by the demo's `simSpeed` multiplier.
 *
 * `simSpeed` is passed in rather than read from the store, so this file has no
 * dependency on the store at all — deleting it cannot leave a dangling import
 * behind. It is a getter, not a number, because the user can change the speed
 * mid-job from Settings and the next frame must respect it.
 *
 * The multiplier applies the opposite way round to `latency.ts`'s `scaled()`:
 * there a DURATION is divided by the speed, here ELAPSED TIME is multiplied by
 * it. Same knob, both ends of it.
 */
export function createSimulatedJobRunner(simSpeed: () => number): JobRunner {
  return {
    report(jobs, elapsedMs) {
      const speed = simSpeed();
      // Instant means instant: one frame's budget has to be large enough to
      // swallow every stage of every job in flight, so the demo driver never
      // waits on a progress bar. `latency.ts` spells the same case `0`.
      const dt = speed === Infinity ? 1e9 : elapsedMs * speed;
      const out = new Map<string, JobPosition>();

      for (const j of jobs) {
        let stageIndex = j.stageIndex;
        let stageProgress = j.stageProgress;
        let budget = dt;
        // Spend this frame's budget across as many stages as it reaches. A
        // fast enough frame — or an instant one — can cross several.
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
          out.set(j.id, { stageIndex: j.stages.length, stageProgress: 1, done: true });
        } else {
          out.set(j.id, { stageIndex, stageProgress, done: false });
        }
      }

      return out;
    },
  };
}
