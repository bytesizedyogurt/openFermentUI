// One table component powers Library, Extract, and assumption lists
// (OF-DES-001 §7.6): sticky header, facets, sort, column show/hide, bulk
// actions, keyboard row navigation, CSV export, virtualization > 200 rows.
import React, { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { ArrowDown, ArrowUp, Columns3, Download, Search, X, ChevronRight } from 'lucide-react';
import { exportCSV } from '@/lib/csv';
import { cx, EmptyState, Popover } from './ui';
import type { ProvKind } from './Provenance';

export interface Column<T> {
  key: string;
  header: string;
  /** Unit lives in the header, never in the cell (§7.6). */
  headerUnit?: string;
  width?: string;
  numeric?: boolean;
  sortable?: boolean;
  defaultHidden?: boolean;
  /** Priority 1 = keep at narrow widths; higher sheds first (§9.4). */
  priority?: number;
  render: (row: T) => ReactNode;
  value: (row: T) => string | number;
}

export interface FacetDef<T> {
  key: string;
  label: string;
  valuesOf: (row: T) => string[];
  /** Optional pretty label for a raw value. */
  labelOf?: (v: string) => string;
}

const TICK_BG: Record<ProvKind, string> = {
  gold: 'rgb(var(--gold))',
  verified: 'rgb(var(--accent))',
  curated: 'rgb(var(--accent) / 0.45)',
  'industry-estimate': 'rgb(var(--ink-soft) / 0.6)',
  unverified: 'rgb(var(--ink-soft))',
  user: 'rgb(var(--signal-info))',
  demo: 'rgb(var(--signal-warn))',
  rejected: 'rgb(var(--signal-error))',
  unsourced: 'rgb(var(--signal-error))',
};

export function DataTable<T>({
  rows,
  columns,
  rowKey,
  tickOf,
  onOpen,
  facets = [],
  exportName,
  exportNote,
  searchOf,
  bulkActions,
  toolbar,
  onFilteredChange,
  emptyTitle = 'Nothing here yet',
  emptyBody = 'No rows to show.',
  dense,
  maxHeight = 'calc(100vh - 260px)',
}: {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  tickOf?: (row: T) => ProvKind;
  onOpen?: (row: T) => void;
  facets?: FacetDef<T>[];
  exportName?: string;
  exportNote?: string;
  searchOf?: (row: T) => string;
  bulkActions?: (selected: T[], clear: () => void) => ReactNode;
  toolbar?: ReactNode;
  /**
   * Fired whenever the facet/search/sort result changes, so a host screen can
   * act on exactly what the user is looking at (e.g. "review these rows").
   * Memoize the callback — it is called on every recompute.
   */
  onFilteredChange?: (rows: T[]) => void;
  emptyTitle?: string;
  emptyBody?: string;
  dense?: boolean;
  maxHeight?: string;
}) {
  const [sort, setSort] = useState<{ key: string; dir: 1 | -1 } | null>(null);
  const [hidden, setHidden] = useState<Set<string>>(
    () => new Set(columns.filter((c) => c.defaultHidden).map((c) => c.key)),
  );
  const [active, setActive] = useState<Record<string, Set<string>>>({});
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [focusIdx, setFocusIdx] = useState(0);
  const [scrollTop, setScrollTop] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  const visibleCols = columns.filter((c) => !hidden.has(c.key));

  // Facet counts are computed against rows filtered by *other* facets, so the
  // numbers describe what clicking would actually yield.
  const facetData = useMemo(() => {
    return facets.map((f) => {
      const others = rows.filter((row) =>
        facets.every((g) => {
          if (g.key === f.key) return true;
          const sel = active[g.key];
          if (!sel || sel.size === 0) return true;
          return g.valuesOf(row).some((v) => sel.has(v));
        }),
      );
      const counts = new Map<string, number>();
      for (const row of others) {
        for (const v of f.valuesOf(row)) counts.set(v, (counts.get(v) ?? 0) + 1);
      }
      return {
        ...f,
        options: [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])),
      };
    });
  }, [rows, facets, active]);

  const filtered = useMemo(() => {
    let out = rows.filter((row) =>
      facets.every((f) => {
        const sel = active[f.key];
        if (!sel || sel.size === 0) return true;
        return f.valuesOf(row).some((v) => sel.has(v)); // OR within a facet
      }),
    ); // AND across facets
    if (query.trim() && searchOf) {
      const q = query.toLowerCase();
      out = out.filter((r) => searchOf(r).toLowerCase().includes(q));
    }
    if (sort) {
      const col = columns.find((c) => c.key === sort.key);
      if (col) {
        out = [...out].sort((a, b) => {
          const av = col.value(a);
          const bv = col.value(b);
          if (typeof av === 'number' && typeof bv === 'number') return (av - bv) * sort.dir;
          return String(av).localeCompare(String(bv)) * sort.dir;
        });
      }
    }
    return out;
  }, [rows, facets, active, query, searchOf, sort, columns]);

  useEffect(() => {
    setFocusIdx((i) => Math.min(i, Math.max(0, filtered.length - 1)));
  }, [filtered.length]);

  useEffect(() => {
    onFilteredChange?.(filtered);
  }, [filtered, onFilteredChange]);

  const narrowingFacet = useMemo(() => {
    for (const f of facets) {
      const sel = active[f.key];
      if (sel && sel.size > 0) {
        const without = rows.filter((row) =>
          facets.every((g) => {
            if (g.key === f.key) return true;
            const s = active[g.key];
            if (!s || s.size === 0) return true;
            return g.valuesOf(row).some((v) => s.has(v));
          }),
        );
        if (without.length > 0) return { facet: f, values: [...sel] };
      }
    }
    return null;
  }, [facets, active, rows]);

  const toggleFacet = (key: string, value: string) =>
    setActive((a) => {
      const next = new Set(a[key] ?? []);
      next.has(value) ? next.delete(value) : next.add(value);
      return { ...a, [key]: next };
    });

  const clearFacets = () => {
    setActive({});
    setQuery('');
  };

  const doExport = () => {
    if (!exportName) return;
    const headers = visibleCols.map((c) => (c.headerUnit ? `${c.header} (${c.headerUnit})` : c.header));
    const body = filtered.map((r) => visibleCols.map((c) => c.value(r)));
    exportCSV(`${exportName}.csv`, headers, body);
  };

  // ── virtualization ───────────────────────────────────────────────────
  const rowH = dense ? 30 : 40;
  const VIRTUAL = filtered.length > 200;
  const viewportH = 700;
  const start = VIRTUAL ? Math.max(0, Math.floor(scrollTop / rowH) - 8) : 0;
  const end = VIRTUAL ? Math.min(filtered.length, start + Math.ceil(viewportH / rowH) + 16) : filtered.length;
  const windowRows = filtered.slice(start, end);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setFocusIdx((i) => Math.min(filtered.length - 1, i + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setFocusIdx((i) => Math.max(0, i - 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const row = filtered[focusIdx];
      if (row && onOpen) onOpen(row);
    } else if (e.key === 'e' && !e.metaKey && !e.ctrlKey) {
      doExport();
    }
  };

  const selectedRows = filtered.filter((r) => selected.has(rowKey(r)));

  return (
    <div className="flex gap-4 items-start">
      {facets.length > 0 && (
        // xl, not lg: the app's own 188px rail shows from md, so turning the
        // facet rail on at 1024 leaves the table itself under ~640px.
        <aside className="w-[196px] shrink-0 hidden xl:block">
          <div className="flex items-center justify-between mb-2">
            <div className="text-caption uppercase tracking-wide text-ink-soft">Filters</div>
            {Object.values(active).some((s) => s.size > 0) && (
              <button className="text-caption text-accent hover:underline" onClick={clearFacets}>
                Clear
              </button>
            )}
          </div>
          <div className="space-y-4">
            {facetData.map((f) => (
              <div key={f.key}>
                <div className="text-caption font-medium mb-1">{f.label}</div>
                <div className="space-y-0.5 max-h-52 overflow-y-auto pr-1">
                  {f.options.map(([value, count]) => {
                    const on = active[f.key]?.has(value) ?? false;
                    return (
                      <button
                        key={value}
                        onClick={() => toggleFacet(f.key, value)}
                        className={cx(
                          'w-full flex items-center justify-between gap-2 px-1.5 py-[3px] rounded-input text-left text-caption',
                          on ? 'bg-accent-wash text-ink font-medium' : 'hover:bg-ink-soft/8 text-ink-soft',
                        )}
                        aria-pressed={on}
                      >
                        <span className="truncate">{f.labelOf?.(value) ?? value}</span>
                        <span className="font-num text-[11px] shrink-0">{count}</span>
                      </button>
                    );
                  })}
                  {f.options.length === 0 && <div className="text-caption text-ink-soft">—</div>}
                </div>
              </div>
            ))}
          </div>
        </aside>
      )}

      <div className="flex-1 min-w-0">
        <div className="flex flex-wrap items-center gap-2 mb-2">
          {searchOf && (
            <div className="relative">
              <Search size={13} className="absolute left-2 top-1/2 -translate-y-1/2 text-ink-soft" />
              <input
                className="input pl-7 w-[220px]"
                placeholder="Filter rows…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                aria-label="Filter rows"
              />
              {query && (
                <button
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 text-ink-soft hover:text-ink"
                  onClick={() => setQuery('')}
                  aria-label="Clear filter"
                >
                  <X size={13} />
                </button>
              )}
            </div>
          )}
          {toolbar}
          <div className="flex-1" />
          <span className="text-caption text-ink-soft font-num">
            {filtered.length === rows.length
              ? `${rows.length} rows`
              : `${filtered.length} of ${rows.length}`}
          </span>
          <Popover
            openOnHover={false}
            width={220}
            label="Columns"
            trigger={(p) => (
              <button {...p} className="btn btn-sm" title="Show/hide columns">
                <Columns3 size={13} /> Columns
              </button>
            )}
          >
            <div className="space-y-1">
              {columns.map((c) => (
                <label key={c.key} className="flex items-center gap-2 text-body cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!hidden.has(c.key)}
                    onChange={() =>
                      setHidden((h) => {
                        const n = new Set(h);
                        n.has(c.key) ? n.delete(c.key) : n.add(c.key);
                        return n;
                      })
                    }
                  />
                  {c.header}
                </label>
              ))}
            </div>
          </Popover>
          {exportName && (
            <button className="btn btn-sm" onClick={doExport} title="Export current filtered view (e)">
              <Download size={13} /> CSV
            </button>
          )}
        </div>

        {exportNote && <div className="text-caption text-ink-soft mb-2">{exportNote}</div>}

        {selectedRows.length > 0 && bulkActions && (
          <div className="mb-2 flex items-center gap-2 rounded-card border border-accent/40 bg-accent-wash px-3 py-1.5 anim-in">
            <span className="text-body font-medium font-num">{selectedRows.length} selected</span>
            {bulkActions(selectedRows, () => setSelected(new Set()))}
            <button className="btn btn-sm ml-auto" onClick={() => setSelected(new Set())}>
              Clear
            </button>
          </div>
        )}

        <div
          ref={scrollRef}
          className="card overflow-auto"
          style={{ maxHeight }}
          onScroll={(e) => VIRTUAL && setScrollTop(e.currentTarget.scrollTop)}
          onKeyDown={onKeyDown}
          tabIndex={0}
          role="region"
          aria-label="Data table"
        >
          <table className="w-full border-collapse" style={{ fontSize: 'var(--table-fs)' }}>
            <thead className="sticky top-0 z-10">
              <tr className="bg-surface-1 border-b border-line">
                {bulkActions && (
                  <th className="w-8 px-2">
                    <input
                      type="checkbox"
                      aria-label="Select all filtered rows"
                      checked={selected.size > 0 && selectedRows.length === filtered.length}
                      onChange={(e) =>
                        setSelected(e.target.checked ? new Set(filtered.map(rowKey)) : new Set())
                      }
                    />
                  </th>
                )}
                {visibleCols.map((c) => (
                  <th
                    key={c.key}
                    className={cx(
                      'text-caption font-medium text-ink-soft px-2 py-2 whitespace-nowrap',
                      c.numeric ? 'text-right' : 'text-left',
                      !!c.priority && c.priority > 2 && 'hidden xl:table-cell',
                    )}
                    style={{ width: c.width }}
                  >
                    {c.sortable !== false ? (
                      <button
                        className="inline-flex items-center gap-1 hover:text-ink"
                        onClick={() =>
                          setSort((s) =>
                            s?.key === c.key
                              ? { key: c.key, dir: s.dir === 1 ? -1 : 1 }
                              : { key: c.key, dir: 1 },
                          )
                        }
                      >
                        {c.header}
                        {c.headerUnit && <span className="font-num opacity-70">({c.headerUnit})</span>}
                        {sort?.key === c.key &&
                          (sort.dir === 1 ? <ArrowUp size={11} /> : <ArrowDown size={11} />)}
                      </button>
                    ) : (
                      <>
                        {c.header}
                        {c.headerUnit && <span className="font-num opacity-70"> ({c.headerUnit})</span>}
                      </>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {VIRTUAL && start > 0 && <tr style={{ height: start * rowH }} aria-hidden />}
              {windowRows.map((row, i) => {
                const key = rowKey(row);
                const idx = start + i;
                const isFocus = idx === focusIdx;
                const isSel = selected.has(key);
                return (
                  <tr
                    key={key}
                    onClick={() => setFocusIdx(idx)}
                    onDoubleClick={() => onOpen?.(row)}
                    className={cx(
                      'border-b border-line/70 transition-colors',
                      isSel ? 'bg-accent-wash' : isFocus ? 'bg-ink-soft/[0.06]' : 'hover:bg-ink-soft/[0.04]',
                      onOpen && 'cursor-pointer',
                    )}
                    style={{ height: rowH }}
                  >
                    {bulkActions && (
                      <td className="px-2 tick-cell">
                        <input
                          type="checkbox"
                          aria-label={`Select ${key}`}
                          checked={isSel}
                          onChange={() =>
                            setSelected((s) => {
                              const n = new Set(s);
                              n.has(key) ? n.delete(key) : n.add(key);
                              return n;
                            })
                          }
                          onClick={(e) => e.stopPropagation()}
                        />
                      </td>
                    )}
                    {visibleCols.map((c, ci) => (
                      <td
                        key={c.key}
                        className={cx(
                          'px-2 py-1 align-middle',
                          c.numeric && 'text-right font-num',
                          !!c.priority && c.priority > 2 && 'hidden xl:table-cell',
                          ci === 0 && !bulkActions && tickOf && 'tick-cell pl-3',
                        )}
                      >
                        {ci === 0 && !bulkActions && tickOf && (
                          <span
                            aria-hidden
                            className="absolute left-0 top-[3px] bottom-[3px] w-[3px] rounded-[1px]"
                            style={{
                              background: TICK_BG[tickOf(row)],
                              backgroundImage:
                                tickOf(row) === 'demo'
                                  ? `repeating-linear-gradient(to bottom, ${TICK_BG.demo} 0 3px, transparent 3px 6px)`
                                  : tickOf(row) === 'industry-estimate'
                                    ? `repeating-linear-gradient(to bottom, ${TICK_BG['industry-estimate']} 0 3px, transparent 3px 6px)`
                                    : undefined,
                            }}
                          />
                        )}
                        {c.render(row)}
                      </td>
                    ))}
                  </tr>
                );
              })}
              {VIRTUAL && end < filtered.length && (
                <tr style={{ height: (filtered.length - end) * rowH }} aria-hidden />
              )}
            </tbody>
          </table>

          {filtered.length === 0 && (
            <EmptyState
              title={narrowingFacet ? 'Nothing matches' : emptyTitle}
              body={
                narrowingFacet
                  ? `“${narrowingFacet.facet.label}: ${narrowingFacet.values
                      .map((v) => narrowingFacet.facet.labelOf?.(v) ?? v)
                      .join(', ')}” is the narrowing filter.`
                  : emptyBody
              }
              action={
                narrowingFacet ? (
                  <button
                    className="btn"
                    onClick={() => setActive((a) => ({ ...a, [narrowingFacet.facet.key]: new Set() }))}
                  >
                    Remove it <ChevronRight size={13} />
                  </button>
                ) : undefined
              }
            />
          )}
        </div>
        <div className="text-caption text-ink-soft mt-1.5 flex items-center gap-3">
          <span>
            <span className="kbd">↑</span> <span className="kbd">↓</span> navigate
          </span>
          <span>
            <span className="kbd">Enter</span> open
          </span>
          {exportName && (
            <span>
              <span className="kbd">e</span> export
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
