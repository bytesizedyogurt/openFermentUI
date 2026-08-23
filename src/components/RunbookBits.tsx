// Shared runbook iconography (OF-BLD-005 §7). The board and the detail page
// must agree about what a state looks like, so the mapping lives once.
//
// No new colour: every state lands on an existing token. The three states that
// need a person — a halted input, a boundary held for review, an unauthorised
// spend — are the warm ones, because those are the ones a reader should find
// first.
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Clock,
  Database,
  Eye,
  FileText,
  Loader2,
  Wallet,
} from 'lucide-react';
import type { RunbookStageStatus, RunbookStatus } from '@/data/types';
import { cx } from './ui';

const STATUS_META: Record<
  RunbookStatus,
  { Icon: typeof CheckCircle2; color: string; spin?: boolean }
> = {
  running: { Icon: Loader2, color: 'text-signal-info', spin: true },
  blocked_unverified: { Icon: AlertTriangle, color: 'text-signal-error' },
  needs_review: { Icon: Eye, color: 'text-signal-warn' },
  awaiting_budget: { Icon: Wallet, color: 'text-signal-warn' },
  complete: { Icon: CheckCircle2, color: 'text-accent' },
  cache_hit: { Icon: Database, color: 'text-accent/70' },
  draft: { Icon: FileText, color: 'text-ink-soft' },
};

export function RunbookStatusIcon({ status, size = 15 }: { status: RunbookStatus; size?: number }) {
  const { Icon, color, spin } = STATUS_META[status];
  return <Icon size={size} className={cx(color, spin && 'animate-spin')} aria-hidden />;
}

const STAGE_META: Record<
  RunbookStageStatus,
  { Icon: typeof CheckCircle2; color: string; dot: string; label: string; spin?: boolean }
> = {
  done: { Icon: CheckCircle2, color: 'text-accent', dot: 'bg-accent', label: 'done' },
  running: {
    Icon: Loader2,
    color: 'text-signal-info',
    dot: 'bg-signal-info',
    label: 'running',
    spin: true,
  },
  queued: { Icon: Clock, color: 'text-ink-soft', dot: 'bg-ink-soft/60', label: 'queued' },
  pending: { Icon: Circle, color: 'text-ink-soft/70', dot: 'bg-ink-soft/25', label: 'pending' },
  review: { Icon: Eye, color: 'text-signal-warn', dot: 'bg-signal-warn', label: 'held for review' },
  blocked: {
    Icon: AlertTriangle,
    color: 'text-signal-error',
    dot: 'bg-signal-error',
    label: 'blocked',
  },
  draft: { Icon: FileText, color: 'text-ink-soft', dot: 'bg-ink-soft/40', label: 'draft' },
};

export function stageMeta(status: RunbookStageStatus) {
  return STAGE_META[status];
}

export function StageIcon({ status, size = 15 }: { status: RunbookStageStatus; size?: number }) {
  const { Icon, color, spin } = STAGE_META[status];
  return <Icon size={size} className={cx('shrink-0', color, spin && 'animate-spin')} aria-hidden />;
}

/** Compact per-stage marker for a card — the shape of a run at a glance. */
export function StageDot({ status }: { status: RunbookStageStatus }) {
  const { dot, label } = STAGE_META[status];
  return <span className={cx('h-1.5 flex-1 rounded-full', dot)} title={label} />;
}
