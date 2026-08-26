// ⌘K palette (OF-DES-001 §7.2) — the demo driver's steering wheel. Three
// groups: Navigate, Actions, Ask. Every golden-path step is reachable here.
//
// It is also the escape hatch for the renamed vocabulary (§6). Every surface
// carries the words it used to be called, so someone who reaches for "library"
// or "run mode" lands on the right screen and learns the new name from the
// result rather than from a dead search.
import { useEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import {
  Library,
  FlaskConical,
  Boxes,
  ClipboardList,
  GitBranch,
  LineChart,
  Settings as SettingsIcon,
  Search,
  Sparkles,
  CornerDownLeft,
  type LucideIcon,
} from 'lucide-react';
import { useStore } from '@/store';
import { navigate } from '@/router';
import { PRODUCT_CATEGORY_LABEL } from '@/data/products';
import { RUNBOOK_STATUS_LABEL } from '@/data/runbooks';
import { RAIL, SUB_VIEWS } from '@/data/nav';
import { cx } from './ui';

interface Item {
  id: string;
  group: 'Navigate' | 'Actions' | 'Ask';
  label: string;
  hint?: string;
  /**
   * Words that should find this item without appearing on it (§6). The old
   * names live here: someone who has typed "library" for months should not
   * have to learn that it is called BioRepo before they can go there.
   */
  aliases?: string[];
  icon?: LucideIcon;
  run: () => void;
}

/**
 * Best score across a label and its aliases.
 *
 * An alias is discounted so that a real label match always outranks it: typing
 * "review" should reach Guild, but if a record were ever literally titled
 * "review" that record would come first, which is right.
 */
function scoreItem(query: string, it: Item): number {
  const direct = score(query, it.label) + (it.hint ? score(query, it.hint) * 0.3 : 0);
  const viaAlias = Math.max(0, ...(it.aliases ?? []).map((a) => score(query, a) * 0.9));
  return Math.max(direct, viaAlias);
}

function score(query: string, label: string): number {
  if (!query) return 1;
  const q = query.toLowerCase();
  const l = label.toLowerCase();
  if (l === q) return 100;
  if (l.startsWith(q)) return 80;
  if (l.includes(q)) return 60;
  // subsequence (fuzzy)
  let qi = 0;
  for (let i = 0; i < l.length && qi < q.length; i++) if (l[i] === q[qi]) qi++;
  return qi === q.length ? 30 : 0;
}

export function CommandPalette() {
  const open = useStore((s) => s.ui.paletteOpen);
  const setUI = useStore((s) => s.setUI);
  const papers = useStore((s) => s.papers);
  const strains = useStore((s) => s.strains);
  const products = useStore((s) => s.products);
  const runbooks = useStore((s) => s.runbooks);
  const protocols = useStore((s) => s.protocols);
  const scenarios = useStore((s) => s.scenarios);
  const records = useStore((s) => s.records);
  const resetDemo = useStore((s) => s.resetDemo);
  const [query, setQuery] = useState('');
  const [sel, setSel] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const close = () => {
    setUI({ paletteOpen: false });
    setQuery('');
    setSel(0);
  };

  const items = useMemo<Item[]>(() => {
    // Built from the vocabulary module rather than restated here, so a name
    // can only be changed in one place (§2.2 as revised).
    const nav: Item[] = [
      ...RAIL.map((r) => ({
        id: `n-${r.label.toLowerCase()}`,
        group: 'Navigate' as const,
        label: r.label,
        hint: r.descriptor,
        aliases: r.aliases,
        icon: r.icon,
        run: () => navigate(r.to),
      })),
      ...SUB_VIEWS.map((r) => ({
        id: `n-${r.label.toLowerCase()}`,
        group: 'Navigate' as const,
        label: r.label,
        hint: r.descriptor,
        aliases: r.aliases,
        icon: r.icon,
        run: () => navigate(r.to),
      })),
      { id: 'n-ing', group: 'Navigate', label: 'Intake — ingest board', hint: 'what is queued, fetched, failed', aliases: ['ingest', 'library ingest', 'fetch'], icon: Library, run: () => navigate('/intake/ingest') },
      { id: 'n-cmp', group: 'Navigate', label: 'Proforma — compare scenarios', aliases: ['compare', 'simulate compare'], icon: LineChart, run: () => navigate('/biorepo/compare') },
      { id: 'n-set', group: 'Navigate', label: 'Settings', icon: SettingsIcon, run: () => navigate('/settings/appearance') },
      { id: 'n-arch', group: 'Navigate', label: 'Architecture — the eighteen components', hint: 'what every name means', aliases: ['components', 'names', 'glossary', 'vocabulary', 'map'], icon: Boxes, run: () => navigate('/settings/architecture') },
      { id: 'n-abt', group: 'Navigate', label: 'About & colophon', icon: SettingsIcon, run: () => navigate('/settings/about') },
    ];
    for (const p of papers) {
      nav.push({
        id: `p-${p.id}`,
        group: 'Navigate',
        label: `${p.id} — ${p.title}`,
        hint: `${p.year} · paper`,
        icon: Library,
        run: () => navigate(`/biorepo/paper/${p.id}`),
      });
    }
    for (const s of strains) {
      nav.push({
        id: `s-${s.id}`,
        group: 'Navigate',
        label: `${s.binomial} ${s.designation}`,
        hint: 'strain',
        icon: FlaskConical,
        run: () => navigate(`/fermos/organisms/${s.id}`),
      });
    }
    for (const p of products) {
      nav.push({
        id: `mo-${p.id}`,
        group: 'Navigate',
        label: p.name,
        hint: `${PRODUCT_CATEGORY_LABEL[p.category]} · molecule`,
        icon: Boxes,
        run: () => navigate(`/dominion/molecules/${p.id}`),
      });
    }
    for (const r of runbooks) {
      nav.push({
        id: `rb-${r.id}`,
        group: 'Navigate',
        label: r.title,
        hint: `${r.kind} runbook · ${RUNBOOK_STATUS_LABEL[r.status]}`,
        icon: GitBranch,
        run: () => navigate(`/runbooks/${r.id}`),
      });
    }
    for (const p of protocols) {
      nav.push({
        id: `pr-${p.id}`,
        group: 'Navigate',
        label: p.title,
        hint: `${p.id} · protocol`,
        icon: ClipboardList,
        run: () => navigate(`/runbooks/protocols/${p.id}`),
      });
    }
    for (const s of scenarios) {
      nav.push({
        id: `sc-${s.id}`,
        group: 'Navigate',
        label: s.name,
        hint: `${s.modelId} · scenario`,
        icon: LineChart,
        run: () => navigate(`/proforma/scenario/${s.id}`),
      });
    }

    const actions: Item[] = [
      {
        id: 'a-review',
        group: 'Actions',
        label: 'Open Guild — start a review session',
        hint: `${records.filter((r) => r.status === 'unverified').length} unverified`,
        run: () => navigate('/guild'),
      },
      {
        id: 'a-newsc',
        group: 'Actions',
        label: 'New Proforma scenario from cw15 defaults',
        run: () => navigate('/proforma/scenario/sc-s1'),
      },
      {
        id: 'a-tour',
        group: 'Actions',
        label: 'Start guided tour',
        run: () => useStore.getState().setUI({ tourStop: 0 }),
      },
      {
        id: 'a-theme',
        group: 'Actions',
        label: 'Toggle theme (Bench / Night Shift)',
        run: () => {
          const t = useStore.getState().ui.theme;
          useStore.getState().setUI({ theme: t === 'bench' ? 'night' : 'bench' });
        },
      },
      {
        id: 'a-density',
        group: 'Actions',
        label: 'Toggle density (comfortable / dense)',
        run: () => {
          const d = useStore.getState().ui.density;
          useStore.getState().setUI({ density: d === 'dense' ? 'comfortable' : 'dense' });
        },
      },
      {
        id: 'a-speed',
        group: 'Actions',
        label: 'Cycle sim speed (1× / 4× / instant)',
        run: () => {
          const s = useStore.getState().ui.simSpeed;
          const next = s === 1 ? 4 : s === 4 ? Infinity : 1;
          useStore.getState().setUI({ simSpeed: next });
          useStore.getState().toast({
            text: `Sim speed: ${next === Infinity ? 'instant' : `${next}×`}`,
            kind: 'info',
          });
        },
      },
      {
        id: 'a-rb-example',
        group: 'Actions',
        label: 'Open the worked runbook (brazzein, complete)',
        hint: 'what a finished industrial runbook contains',
        run: () => navigate('/runbooks/rb-brazzein'),
      },
      {
        id: 'a-blocked',
        group: 'Actions',
        label: 'Show molecules with blocking patent claims',
        hint: `${products.filter((p) => p.clearanceState === 'blocked').length} blocked`,
        run: () => navigate('/dominion/molecules?clearance=blocked'),
      },
      { id: 'a-help', group: 'Actions', label: 'Keyboard shortcuts', run: () => useStore.getState().setUI({ helpOpen: true }) },
      { id: 'a-reset', group: 'Actions', label: 'Reset demo data', run: resetDemo },
    ];

    return [...nav, ...actions];
  }, [papers, strains, products, runbooks, protocols, scenarios, records, resetDemo]);

  const results = useMemo(() => {
    const scored = items
      .map((it) => ({ it, s: scoreItem(query, it) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 30)
      .map((x) => x.it);

    // Any unmatched string offers "Ask the agent" (§7.2)
    if (query.trim().length > 2) {
      scored.push({
        id: 'ask-it',
        group: 'Ask',
        label: `Ask the agent: “${query.trim()}”`,
        icon: Sparkles,
        run: () => navigate(`/postdoc?q=${encodeURIComponent(query.trim())}`),
      });
    }
    return scored;
  }, [items, query]);

  useEffect(() => setSel(0), [query]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 20);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSel((s) => Math.min(results.length - 1, s + 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSel((s) => Math.max(0, s - 1));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const item = results[sel];
        if (item) {
          item.run();
          close();
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, results, sel]);

  useEffect(() => {
    listRef.current?.querySelector('[data-sel="true"]')?.scrollIntoView({ block: 'nearest' });
  }, [sel]);

  if (!open) return null;

  let lastGroup = '';
  return createPortal(
    <div className="fixed inset-0 z-[80] flex items-start justify-center pt-[12vh] px-4">
      <div className="absolute inset-0 bg-ink/30" onClick={close} />
      <div className="relative overlay rounded-card w-full max-w-[620px] anim-in overflow-hidden">
        <div className="flex items-center gap-2 px-3 py-2.5 border-b border-line">
          <Search size={16} className="text-ink-soft" />
          <input
            ref={inputRef}
            className="flex-1 bg-transparent outline-none text-reading"
            placeholder="Search papers, parameters, protocols, actions…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label="Command palette"
          />
          <span className="kbd">esc</span>
        </div>
        <div ref={listRef} className="max-h-[52vh] overflow-y-auto py-1" role="listbox">
          {results.map((it, i) => {
            const showGroup = it.group !== lastGroup;
            lastGroup = it.group;
            const Icon = it.icon;
            return (
              <div key={it.id}>
                {showGroup && (
                  <div className="text-caption uppercase tracking-wide text-ink-soft px-3 pt-2 pb-1">
                    {it.group}
                  </div>
                )}
                <button
                  data-sel={i === sel}
                  role="option"
                  aria-selected={i === sel}
                  onMouseEnter={() => setSel(i)}
                  onClick={() => {
                    it.run();
                    close();
                  }}
                  className={cx(
                    'w-full flex items-center gap-2.5 px-3 py-1.5 text-left',
                    i === sel ? 'bg-accent-wash' : 'hover:bg-ink-soft/[0.05]',
                  )}
                >
                  {Icon && <Icon size={14} className="text-ink-soft shrink-0" />}
                  <span className="flex-1 truncate text-body">{it.label}</span>
                  {it.hint && <span className="text-caption text-ink-soft shrink-0">{it.hint}</span>}
                  {i === sel && <CornerDownLeft size={12} className="text-ink-soft" />}
                </button>
              </div>
            );
          })}
          {results.length === 0 && (
            <div className="px-3 py-6 text-center text-ink-soft text-body">
              Nothing matches. Type more than two characters to ask the agent instead.
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
