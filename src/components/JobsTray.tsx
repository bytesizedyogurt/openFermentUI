// Jobs tray (OF-DES-001 §7.7). Anything over ~2s is a Job: optimistic toast,
// stage-level progress here, completion toast that deep-links to the result.
// Jobs never modally block the interface.
import { CheckCircle2, Loader2, XCircle, Trash2 } from 'lucide-react';
import { useStore } from '@/store';
import { navigate } from '@/router';
import { cx, EmptyState } from './ui';

export function JobsPanel({ onClose }: { onClose: () => void }) {
  const jobs = useStore((s) => s.jobs);
  const clearJobs = useStore((s) => s.clearJobs);
  const runs = useStore((s) => s.runs);
  const activeRunId = useStore((s) => s.activeRunId);
  const protocols = useStore((s) => s.protocols);

  const activeRun = activeRunId ? runs[activeRunId] : null;
  const activeProto = activeRun ? protocols.find((p) => p.id === activeRun.protocolId) : null;

  return (
    <div className="w-[360px]">
      <div className="flex items-center justify-between px-3 py-2 border-b border-line">
        <div className="font-medium">Jobs</div>
        {jobs.some((j) => j.status !== 'running') && (
          <button className="btn btn-sm" onClick={clearJobs}>
            <Trash2 size={12} /> Clear finished
          </button>
        )}
      </div>

      <div className="max-h-[420px] overflow-y-auto">
        {activeRun && activeProto && (
          <button
            className="w-full text-left px-3 py-2.5 border-b border-line hover:bg-accent-wash"
            onClick={() => {
              navigate(`/protocols/${activeProto.id}/run/${activeRun.id}`);
              onClose();
            }}
          >
            <div className="flex items-center gap-2">
              <Loader2 size={14} className="text-accent animate-spin" />
              <span className="font-medium text-body">Run in progress</span>
            </div>
            <div className="text-caption text-ink-soft mt-0.5 pl-6">
              {activeProto.title} · {Object.keys(activeRun.completed).length}/
              {activeProto.versions.find((v) => v.version === activeRun.version)?.steps.length} steps
              {activeRun.timers.filter((t) => t.running).length > 0 &&
                ` · ${activeRun.timers.filter((t) => t.running).length} timer(s) running`}
            </div>
          </button>
        )}

        {jobs.length === 0 && !activeRun && (
          <EmptyState
            title="No jobs running"
            body="Ingests, extraction runs, and simulations appear here with stage-level progress."
          />
        )}

        {[...jobs].reverse().map((j) => {
          const stage = j.stages[Math.min(j.stageIndex, j.stages.length - 1)];
          const pct =
            j.status === 'done'
              ? 100
              : ((j.stageIndex + j.stageProgress) / j.stages.length) * 100;
          return (
            <div key={j.id} className="px-3 py-2.5 border-b border-line last:border-0">
              <div className="flex items-center gap-2">
                {j.status === 'running' && <Loader2 size={14} className="text-signal-info animate-spin" />}
                {j.status === 'done' && <CheckCircle2 size={14} className="text-accent" />}
                {j.status === 'failed' && <XCircle size={14} className="text-signal-error" />}
                <span className="font-medium text-body flex-1 truncate">{j.title}</span>
                {j.href && j.status === 'done' && (
                  <button
                    className="btn btn-sm"
                    onClick={() => {
                      navigate(j.href!.replace(/^#/, ''));
                      onClose();
                    }}
                  >
                    View
                  </button>
                )}
              </div>
              <div className="pl-6 mt-1.5">
                <div className="h-1 rounded-full bg-ink-soft/15 overflow-hidden">
                  <div
                    className={cx(
                      'h-full rounded-full transition-[width] duration-200',
                      j.status === 'failed' ? 'bg-signal-error' : 'bg-accent',
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                  {j.stages.map((s, i) => (
                    <span
                      key={s.label}
                      className={cx(
                        'text-[10px] font-num px-1 rounded',
                        j.status === 'failed' && i === j.stageIndex
                          ? 'bg-signal-error/15 text-signal-error'
                          : i < j.stageIndex || j.status === 'done'
                            ? 'bg-accent/15 text-accent'
                            : i === j.stageIndex
                              ? 'bg-signal-info/15 text-signal-info'
                              : 'text-ink-soft',
                      )}
                    >
                      {s.label}
                    </span>
                  ))}
                </div>
                {j.status === 'failed' && (
                  <div className="text-caption text-signal-error mt-1">{j.failReason}</div>
                )}
                {j.status === 'running' && (
                  <div className="text-caption text-ink-soft mt-1">{stage?.label}…</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
