// Shared UI primitives. Border-first elevation; one shadow reserved for
// overlays (OF-DES-001 §6.4).
import React, { useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { X, AlertTriangle, Info, CheckCircle2, XCircle } from 'lucide-react';
import { useStore } from '@/store';
import { navigate } from '@/router';

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ');
}

// ── Page scaffolding ───────────────────────────────────────────────────

export function PageHeader({
  title,
  subtitle,
  actions,
  eyebrow,
}: {
  /** null mounts the screen under an owner's header — see the note below. */
  title: ReactNode | null;
  subtitle?: ReactNode;
  actions?: ReactNode;
  eyebrow?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-6 mb-5">
      <div className="min-w-0">
        {eyebrow && (
          <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">{eyebrow}</div>
        )}
        {/* A null title is a screen mounted inside an owner that already has a
            header (OF-BLD-008 §6). The actions still belong on screen, so the
            row survives and only the heading is dropped — an empty <h1> would
            hold its line height and leave a gap nobody can explain. */}
        {title !== null && title !== undefined && (
          <h1 className="font-serif text-page-title font-semibold leading-tight">{title}</h1>
        )}
        {subtitle && <div className="text-body text-ink-soft mt-1 max-w-3xl">{subtitle}</div>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}

export function Card({
  children,
  className,
  grid,
  ...rest
}: { children: ReactNode; className?: string; grid?: boolean } & React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cx('card', grid && 'of-grid', className)} {...rest}>
      {children}
    </div>
  );
}

export function SectionTitle({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 mb-2">
      <h2 className="font-serif text-section-title font-semibold">{children}</h2>
      {right}
    </div>
  );
}

export function EmptyState({
  title,
  body,
  action,
  icon,
}: {
  title: string;
  body: string;
  action?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-12 px-6 gap-2">
      {icon && <div className="text-ink-soft mb-1">{icon}</div>}
      <div className="font-medium">{title}</div>
      <div className="text-body text-ink-soft max-w-md">{body}</div>
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function Skeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="p-3 space-y-2" aria-hidden>
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-[var(--row-h)] rounded bg-ink-soft/10"
          style={{ opacity: 1 - i * 0.09 }}
        />
      ))}
    </div>
  );
}

// ── Buttons ────────────────────────────────────────────────────────────

export function Button({
  children,
  variant = 'default',
  size,
  className,
  ...rest
}: {
  children: ReactNode;
  variant?: 'default' | 'primary';
  size?: 'sm';
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cx('btn', variant === 'primary' && 'btn-primary', size === 'sm' && 'btn-sm', className)}
      {...rest}
    >
      {children}
    </button>
  );
}

export function LinkButton({
  to,
  children,
  variant,
  size,
  className,
}: {
  to: string;
  children: ReactNode;
  variant?: 'default' | 'primary';
  size?: 'sm';
  className?: string;
}) {
  return (
    <a
      href={`#${to}`}
      className={cx('btn', variant === 'primary' && 'btn-primary', size === 'sm' && 'btn-sm', className)}
    >
      {children}
    </a>
  );
}

// ── Popover (hover/click, portal-positioned) ───────────────────────────

export function Popover({
  trigger,
  children,
  width = 340,
  openOnHover = true,
  label,
}: {
  trigger: (props: { ref: React.Ref<HTMLButtonElement>; onClick: () => void; onMouseEnter: () => void; onMouseLeave: () => void; 'aria-expanded': boolean }) => ReactNode;
  children: ReactNode;
  width?: number;
  openOnHover?: boolean;
  label?: string;
}) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  const ref = useRef<HTMLButtonElement>(null);
  const timer = useRef<number>();
  const panelRef = useRef<HTMLDivElement>(null);

  const place = () => {
    const r = ref.current?.getBoundingClientRect();
    if (!r) return;
    const top = r.bottom + 6;
    const left = Math.max(8, Math.min(window.innerWidth - width - 8, r.left));
    const flipUp = top + 260 > window.innerHeight && r.top > 280;
    setPos({ top: flipUp ? r.top - 6 : top, left });
    if (flipUp && panelRef.current) panelRef.current.style.transform = 'translateY(-100%)';
  };

  useEffect(() => {
    if (!open) return;
    place();
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node) && !panelRef.current?.contains(e.target as Node))
        setOpen(false);
    };
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('mousedown', close);
    window.addEventListener('keydown', esc);
    window.addEventListener('scroll', place, true);
    return () => {
      window.removeEventListener('mousedown', close);
      window.removeEventListener('keydown', esc);
      window.removeEventListener('scroll', place, true);
    };
  }, [open]);

  return (
    <>
      {trigger({
        ref,
        onClick: () => setOpen((o) => !o),
        onMouseEnter: () => {
          if (!openOnHover) return;
          window.clearTimeout(timer.current);
          timer.current = window.setTimeout(() => setOpen(true), 180);
        },
        onMouseLeave: () => {
          if (!openOnHover) return;
          window.clearTimeout(timer.current);
          timer.current = window.setTimeout(() => setOpen(false), 260);
        },
        'aria-expanded': open,
      })}
      {open &&
        createPortal(
          <div
            ref={panelRef}
            role="dialog"
            aria-label={label}
            className="fixed z-50 overlay rounded-card p-3 anim-in text-body"
            style={{ top: pos.top, left: pos.left, width }}
            onMouseEnter={() => window.clearTimeout(timer.current)}
            onMouseLeave={() => {
              if (!openOnHover) return;
              timer.current = window.setTimeout(() => setOpen(false), 200);
            }}
          >
            {children}
          </div>,
          document.body,
        )}
    </>
  );
}

// ── Sheet (right-side drawer) ──────────────────────────────────────────

export function Sheet({
  open,
  onClose,
  title,
  children,
  width = 560,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  width?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab' && ref.current) {
        const f = ref.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        if (f.length === 0) return;
        const first = f[0];
        const last = f[f.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      prev?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-ink/25" onClick={onClose} />
      <div
        ref={ref}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        className="relative h-full overflow-y-auto bg-surface-1 border-l border-line anim-in"
        style={{ width: Math.min(width, window.innerWidth - 24) }}
      >
        <div className="sticky top-0 bg-surface-1 border-b border-line px-4 py-3 flex items-center justify-between gap-4 z-10">
          <div className="font-serif text-section-title font-semibold">{title}</div>
          <button className="btn btn-sm" onClick={onClose} aria-label="Close">
            <X size={14} />
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>,
    document.body,
  );
}

// ── Modal (centered, for confirms) ─────────────────────────────────────

export function Modal({
  open,
  onClose,
  title,
  children,
  width = 460,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
  width?: number;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);
  if (!open) return null;
  return createPortal(
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-ink/30" onClick={onClose} />
      <div
        role="dialog"
        aria-modal="true"
        className="relative overlay rounded-card anim-in"
        style={{ width: Math.min(width, window.innerWidth - 32) }}
      >
        <div className="px-4 py-3 border-b border-line font-serif text-section-title font-semibold">
          {title}
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>,
    document.body,
  );
}

// ── Toasts (§9.3) ──────────────────────────────────────────────────────

const TOAST_ICON = {
  info: Info,
  success: CheckCircle2,
  warn: AlertTriangle,
  error: XCircle,
};
const TOAST_COLOR = {
  info: 'text-signal-info',
  success: 'text-accent',
  warn: 'text-signal-warn',
  error: 'text-signal-error',
};

export function Toasts() {
  const toasts = useStore((s) => s.toasts);
  const dismiss = useStore((s) => s.dismissToast);
  return (
    <div className="fixed bottom-4 right-4 z-[70] flex flex-col gap-2 w-[340px]" aria-live="polite">
      {toasts.map((t) => {
        const Icon = TOAST_ICON[t.kind];
        return (
          <div key={t.id} className="overlay rounded-card p-3 flex items-start gap-2 anim-in">
            <Icon size={16} className={cx('mt-[2px] shrink-0', TOAST_COLOR[t.kind])} />
            <div className="flex-1 text-body">{t.text}</div>
            {t.href && (
              <button
                className="btn btn-sm"
                onClick={() => {
                  navigate(t.href!.replace(/^#/, ''));
                  dismiss(t.id);
                }}
              >
                {t.hrefLabel ?? 'Open'}
              </button>
            )}
            <button className="text-ink-soft hover:text-ink" onClick={() => dismiss(t.id)} aria-label="Dismiss">
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

// ── Small display helpers ──────────────────────────────────────────────

export function Stat({
  label,
  value,
  unit,
  sub,
  className,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  sub?: ReactNode;
  className?: string;
}) {
  return (
    <div className={className}>
      <div className="text-caption uppercase tracking-wide text-ink-soft">{label}</div>
      <div className="font-num text-display leading-tight">
        {value}
        {unit && <span className="text-section-title text-ink-soft ml-1">{unit}</span>}
      </div>
      {sub && <div className="text-caption text-ink-soft mt-0.5">{sub}</div>}
    </div>
  );
}

export function Bar({ value, max = 1, className }: { value: number; max?: number; className?: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="h-1.5 w-full rounded-full bg-ink-soft/15 overflow-hidden">
      <div className={cx('h-full rounded-full bg-accent', className)} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Callout({
  kind = 'info',
  title,
  children,
}: {
  kind?: 'info' | 'warn' | 'error';
  title?: string;
  children: ReactNode;
}) {
  const color =
    kind === 'warn'
      ? 'border-signal-warn/40 bg-signal-warn/[0.07]'
      : kind === 'error'
        ? 'border-signal-error/40 bg-signal-error/[0.07]'
        : 'border-signal-info/40 bg-signal-info/[0.07]';
  const Icon = kind === 'info' ? Info : AlertTriangle;
  const iconColor =
    kind === 'warn' ? 'text-signal-warn' : kind === 'error' ? 'text-signal-error' : 'text-signal-info';
  return (
    <div className={cx('rounded-card border p-3 flex gap-2', color)}>
      <Icon size={16} className={cx('mt-[2px] shrink-0', iconColor)} />
      <div className="text-body">
        {title && <div className="font-medium mb-0.5">{title}</div>}
        {children}
      </div>
    </div>
  );
}

/** Explainer popover trigger — the ambient-pedagogy affordance (§4). */
export function Explain({ children, label = 'What is this?' }: { children: ReactNode; label?: string }) {
  return (
    <Popover
      label={label}
      width={320}
      trigger={(p) => (
        <button
          {...p}
          className="inline-flex items-center justify-center w-[15px] h-[15px] rounded-full border border-line text-[10px] text-ink-soft hover:border-accent hover:text-accent align-middle"
          aria-label={label}
        >
          ?
        </button>
      )}
    >
      <div className="text-body leading-relaxed">{children}</div>
    </Popover>
  );
}
