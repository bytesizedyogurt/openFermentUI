// Extract — the dense extraction table (OF-DES-001 §8.6). Every quantitative
// row in the system lives here, faceted, unit-switchable, and exportable with
// its provenance attached. This is the screen that makes the corpus auditable.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ClipboardCheck, Download, Gauge, Table2 } from 'lucide-react';
import type { ExtractionRecord, FieldId } from '@/data/types';
import { fieldName, ONTOLOGY_BY_ID } from '@/data/ontology';
import { useStore, provenanceOf } from '@/store';
import { href, navigate, useRoute } from '@/router';
import { unitFamily, asNumber, convert } from '@/engine/units';
import { aggregate } from '@/engine/posterior';
import { ContradictionRail } from '@/components/ContradictionRail';
import { DataTable, type Column, type FacetDef } from '@/components/DataTable';
import { CitationChip } from '@/components/Chip';
import { ProvenanceLegend, type ProvKind } from '@/components/Provenance';
import { Quantity } from '@/components/QuantityField';
import {
  Bar,
  Button,
  Callout,
  Card,
  EmptyState,
  LinkButton,
  PageHeader,
  Skeleton,
  cx,
} from '@/components/ui';
import { exportCSV } from '@/lib/csv';
import { delayClass } from '@/sim/latency';

// ── row model ──────────────────────────────────────────────────────────

interface ExRow {
  rec: ExtractionRecord;
  prov: ProvKind;
  family: string;
  band: string;
  updated: string;
}

function bandOf(confidence: number): string {
  if (confidence < 0.7) return '<0.7';
  if (confidence <= 0.85) return '0.7–0.85';
  return '>0.85';
}

const FAMILY_LABEL: Record<string, string> = {
  rate: 'Rate (h⁻¹)',
  time: 'Time (h)',
  massConc: 'Mass concentration (g L⁻¹)',
  mass: 'Mass (g)',
  volume: 'Volume (L)',
  percent: 'Percent (%)',
  yield: 'Yield (g g⁻¹)',
  volProd: 'Volumetric productivity',
  specProd: 'Specific productivity',
  odDcw: 'OD→DCW factor',
  temp: 'Temperature (°C)',
  light: 'Photon flux',
  ph: 'Dimensionless (pH)',
  molar: 'Molar (mol L⁻¹)',
  vvm: 'Gas flow (vvm)',
  rpm: 'Agitation (rpm)',
  length: 'Length (m)',
  unrecognised: 'Unrecognised unit',
};

const STATUS_FACET_LABEL: Record<string, string> = {
  unverified: 'Unverified',
  verified: 'Verified',
  rejected: 'Rejected',
  gold: 'In gold set',
};

function provOf(r: ExtractionRecord): ProvKind {
  return r.status === 'rejected' ? 'rejected' : provenanceOf(r);
}

function lastAudit(r: ExtractionRecord): string {
  const a = r.audit[r.audit.length - 1];
  return a ? a.at : '—';
}

function truncate(text: string, max: number): string {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function nowStamp(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

function StatusCell({ r }: { r: ExtractionRecord }) {
  if (r.status === 'rejected') {
    return (
      <span
        className="chip text-signal-error border-signal-error/40"
        title={r.rejectReason ? `Rejected — ${r.rejectReason}` : 'Rejected during review'}
      >
        Rejected
      </span>
    );
  }
  if (r.gold) {
    return (
      <span className="chip text-gold border-gold/45" title="Curated gold-set annotation">
        Gold
      </span>
    );
  }
  if (r.status === 'verified') {
    return (
      <span className="chip text-accent border-accent/40" title="Verified by a reviewer">
        Verified
      </span>
    );
  }
  return (
    <span className="chip text-ink-soft" title="Extracted but not yet reviewed">
      Unverified
    </span>
  );
}

// ── screen ─────────────────────────────────────────────────────────────

export default function Extract() {
  const route = useRoute();
  const paperParam = route.query.get('paper');

  const records = useStore((s) => s.records);
  const contradictions = useStore((s) => s.contradictions);

  // Every corpus value per field, converted once, so each row's rail plots the
  // same axis rather than recomputing per render.
  const peersByField = useMemo(() => {
    const m = new Map<FieldId, { record: ExtractionRecord; value: number }[]>();
    for (const r of records) {
      const def = ONTOLOGY_BY_ID[r.field];
      const n = asNumber(r.value);
      if (!def || n === null) continue;
      let v = n;
      if (def.canonicalUnit && r.unit !== def.canonicalUnit) {
        try {
          v = convert(n, r.unit, def.canonicalUnit);
        } catch {
          continue;
        }
      }
      const list = m.get(r.field) ?? [];
      list.push({ record: r, value: v });
      m.set(r.field, list);
    }
    return m;
  }, [records]);
  const papers = useStore((s) => s.papers);
  const unitMode = useStore((s) => s.ui.unitMode);
  const density = useStore((s) => s.ui.density);
  const setUI = useStore((s) => s.setUI);
  const startReview = useStore((s) => s.startReview);
  const logActivity = useStore((s) => s.logActivity);
  const toast = useStore((s) => s.toast);

  const [ready, setReady] = useState(false);
  // null until the table reports its first facet/search result, so the header
  // never briefly claims "0 in view" before the table has had a chance to say.
  const [filteredRows, setFilteredRows] = useState<ExRow[] | null>(null);

  useEffect(() => {
    let alive = true;
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  const scopedPaper = paperParam ? papers.find((p) => p.id === paperParam) : undefined;

  const allRows = useMemo<ExRow[]>(
    () =>
      records.map((rec) => ({
        rec,
        prov: provOf(rec),
        family: unitFamily(rec.unit) ?? 'unrecognised',
        band: bandOf(rec.confidence),
        updated: lastAudit(rec),
      })),
    [records],
  );

  // ?paper=SP-004 narrows the whole table before the facets ever see it.
  const rows = useMemo(
    () => (paperParam ? allRows.filter((r) => r.rec.paperId === paperParam) : allRows),
    [allRows, paperParam],
  );

  // Identity-stable so DataTable's effect never drives a render loop.
  const handleFiltered = useCallback((next: ExRow[]) => {
    setFilteredRows((prev) =>
      prev !== null && prev.length === next.length && prev.every((r, i) => r.rec === next[i].rec)
        ? prev
        : next,
    );
  }, []);

  const inView = filteredRows ?? rows;
  const filteredUnverified = inView.filter((r) => r.rec.status === 'unverified');

  // ── header actions ───────────────────────────────────────────────────

  const startSession = () => {
    const ids = filteredUnverified.map((r) => r.rec.id);
    if (ids.length === 0) return;
    startReview(ids);
    logActivity({
      at: nowStamp(),
      icon: 'clipboard-check',
      text: `Review session started — ${ids.length} unverified record${ids.length === 1 ? '' : 's'}`,
      href: '#/trawl/review',
      provenance: 'user',
    });
    navigate('/trawl/review');
  };

  const exportBoth = () => {
    const source = inView;
    if (source.length === 0) {
      toast({ text: 'Nothing to export — the current filter selects no rows', kind: 'warn' });
      return;
    }
    exportCSV(
      paperParam ? `openferment-extractions-${paperParam}.csv` : 'openferment-extractions.csv',
      [
        'Record ID',
        'Paper ID',
        'Paper title',
        'Field ID',
        'Field',
        'Organism',
        'Component tag',
        'Value (as published)',
        'Unit (as published)',
        'Value (SI)',
        'Unit (SI)',
        'Unit family',
        'Confidence',
        'Confidence band',
        'Status',
        'Provenance',
        'Gold value',
        'Gold unit',
        'Reviewer',
        'Reject reason',
        'Extractor run',
        'Quote',
        'Section ID',
        'Last updated',
      ],
      source.map(({ rec, prov, family, band, updated }) => [
        rec.id,
        rec.paperId,
        papers.find((p) => p.id === rec.paperId)?.title ?? '',
        rec.field,
        fieldName(rec.field),
        rec.organism ?? '',
        rec.componentTag ?? '',
        rec.value,
        rec.unit,
        rec.si.value,
        rec.si.unit,
        FAMILY_LABEL[family] ?? family,
        rec.confidence,
        band,
        rec.status,
        prov,
        rec.gold?.value ?? '',
        rec.gold?.unit ?? '',
        rec.reviewer ?? '',
        rec.rejectReason ?? '',
        rec.extractorRun,
        rec.quote,
        rec.sectionId,
        updated,
      ]),
    );
  };

  // ── columns ──────────────────────────────────────────────────────────

  const si = unitMode === 'si';

  const columns: Column<ExRow>[] = [
    {
      key: 'id',
      header: 'Record',
      width: '96px',
      priority: 1,
      render: ({ rec }) => (
        <a
          href={href(`/library/papers/${rec.paperId}?span=${rec.id}`)}
          className="font-num text-accent hover:underline"
          title={`Open ${rec.id} anchored in ${rec.paperId}`}
          onClick={(e) => e.stopPropagation()}
        >
          {rec.id}
        </a>
      ),
      value: ({ rec }) => rec.id,
    },
    {
      key: 'field',
      header: 'Field',
      width: '230px',
      priority: 1,
      render: ({ rec }) => (
        <span className="block truncate" title={fieldName(rec.field)}>
          {fieldName(rec.field)}
        </span>
      ),
      value: ({ rec }) => fieldName(rec.field),
    },
    {
      key: 'spread',
      header: 'Spread',
      width: '58px',
      priority: 2,
      // The record table answers "what was extracted"; the rail answers "where
      // does this one sit among the others for the same field", which is the
      // question a reader has in front of any single number.
      render: ({ rec }) => (
        <ContradictionRail
          marks={peersByField.get(rec.field) ?? []}
          aggregate={aggregate((peersByField.get(rec.field) ?? []).map((x) => x.record))}
          contradictions={contradictions.filter((c) => c.recordIds.includes(rec.id))}
          height={28}
          highlightId={rec.id}
        />
      ),
      value: ({ rec }) => (peersByField.get(rec.field) ?? []).length,
    },
    {
      key: 'value',
      header: si ? 'Value (SI)' : 'Value (as published)',
      width: '110px',
      numeric: true,
      priority: 1,
      // Always converts from the stored pair, never from a displayed string.
      render: ({ rec }) => (
        <Quantity value={rec.value} unit="" si={{ value: rec.si.value, unit: '' }} mode={unitMode} />
      ),
      value: ({ rec }) => (si ? rec.si.value : rec.value),
    },
    {
      key: 'unit',
      header: 'Unit',
      width: '116px',
      priority: 1,
      render: ({ rec }) => (
        <span className="font-num text-ink-soft">{(si ? rec.si.unit : rec.unit) || '—'}</span>
      ),
      value: ({ rec }) => (si ? rec.si.unit : rec.unit) || '—',
    },
    {
      key: 'paper',
      header: 'Source',
      width: '92px',
      priority: 1,
      render: ({ rec }) => (
        <span onClick={(e) => e.stopPropagation()}>
          <CitationChip paperId={rec.paperId} />
        </span>
      ),
      value: ({ rec }) => rec.paperId,
    },
    {
      key: 'span',
      header: 'Quoted span',
      priority: 2,
      render: ({ rec }) => (
        <span className="font-serif italic text-ink-soft block truncate" title={rec.quote}>
          “{truncate(rec.quote, 96)}”
        </span>
      ),
      value: ({ rec }) => rec.quote,
    },
    {
      key: 'organism',
      header: 'Organism',
      width: '150px',
      priority: 3,
      defaultHidden: true,
      render: ({ rec }) =>
        rec.organism ? (
          <span className="italic truncate block">{rec.organism}</span>
        ) : (
          <span className="text-ink-soft">—</span>
        ),
      value: ({ rec }) => rec.organism ?? '',
    },
    {
      key: 'confidence',
      header: 'Conf.',
      width: '104px',
      numeric: true,
      priority: 2,
      render: ({ rec }) => (
        <span
          className="inline-flex items-center gap-1.5 justify-end w-full"
          title={`Extractor confidence ${rec.confidence.toFixed(2)}`}
        >
          <span className="w-10 shrink-0">
            <Bar
              value={rec.confidence}
              className={cx(
                rec.confidence < 0.7 && 'bg-signal-warn',
                rec.confidence > 0.85 && 'bg-accent',
              )}
            />
          </span>
          <span className="font-num tabular-nums">{rec.confidence.toFixed(2)}</span>
        </span>
      ),
      value: ({ rec }) => rec.confidence,
    },
    {
      key: 'status',
      header: 'Status',
      width: '104px',
      priority: 1,
      render: ({ rec }) => <StatusCell r={rec} />,
      value: ({ rec }) => (rec.gold ? 'gold' : rec.status),
    },
    {
      key: 'reviewer',
      header: 'Reviewer',
      width: '96px',
      priority: 3,
      render: ({ rec }) =>
        rec.reviewer ? <span>{rec.reviewer}</span> : <span className="text-ink-soft">—</span>,
      value: ({ rec }) => rec.reviewer ?? '',
    },
    {
      key: 'updated',
      header: 'Updated',
      width: '124px',
      priority: 3,
      render: ({ updated }) => <span className="font-num text-ink-soft">{updated}</span>,
      value: ({ updated }) => updated,
    },
  ];

  const facets: FacetDef<ExRow>[] = [
    {
      key: 'field',
      label: 'Field',
      valuesOf: ({ rec }) => [rec.field],
      labelOf: (v) => fieldName(v as ExtractionRecord['field']),
    },
    {
      key: 'organism',
      label: 'Organism',
      valuesOf: ({ rec }) => [rec.organism ?? '—unspecified—'],
      labelOf: (v) => (v === '—unspecified—' ? 'Not stated' : v),
    },
    {
      key: 'status',
      label: 'Status',
      // A gold record also matches its own status, so the facet is additive.
      valuesOf: ({ rec }) => (rec.gold ? [rec.status, 'gold'] : [rec.status]),
      labelOf: (v) => STATUS_FACET_LABEL[v] ?? v,
    },
    { key: 'paper', label: 'Paper', valuesOf: ({ rec }) => [rec.paperId] },
    { key: 'band', label: 'Confidence', valuesOf: ({ band }) => [band] },
    {
      key: 'family',
      label: 'Unit family',
      valuesOf: ({ family }) => [family],
      labelOf: (v) => FAMILY_LABEL[v] ?? v,
    },
  ];

  // ── toolbar: the shared unit switch + the deep-link scope chip ────────

  const toolbar = (
    <>
      <div
        className="flex items-center gap-1.5"
        role="group"
        aria-label="Unit display for the value and unit columns"
      >
        <span className="text-caption text-ink-soft">Units</span>
        <div className="flex rounded-input border border-line overflow-hidden">
          {(
            [
              ['published', 'As published'],
              ['si', 'SI'],
            ] as const
          ).map(([mode, label]) => (
            <button
              key={mode}
              onClick={() => setUI({ unitMode: mode })}
              aria-pressed={unitMode === mode}
              title={
                mode === 'published'
                  ? 'Show values exactly as the paper reported them'
                  : 'Convert every row to its SI twin — shared with the paper reader'
              }
              className={cx(
                'px-2 py-[3px] text-[11px]',
                unitMode === mode
                  ? 'bg-accent-wash text-ink font-medium'
                  : 'text-ink-soft hover:text-ink',
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {paperParam && (
        <span className="chip chip-active">
          Scoped to <span className="font-num">{paperParam}</span>
          <button
            className="text-ink-soft hover:text-ink ml-1"
            onClick={() => navigate('/ledger/records')}
            aria-label={`Clear the ${paperParam} scope`}
            title="Show every record again"
          >
            ×
          </button>
        </span>
      )}
    </>
  );

  // ── states ───────────────────────────────────────────────────────────

  if (!ready) {
    return (
      <>
        <PageHeader
          eyebrow="Module 0 · Evidence"
          title="Extraction records"
          subtitle="Every quantitative claim the pipeline has pulled out of the corpus, with the span it came from."
        />
        <Card>
          <Skeleton rows={12} />
        </Card>
      </>
    );
  }

  const headerActions = (
    <>
      <Button
        variant="primary"
        onClick={startSession}
        disabled={filteredUnverified.length === 0}
        title={
          filteredUnverified.length === 0
            ? 'Nothing unverified in the current filter — adjust the facets to queue records'
            : `Queue the ${filteredUnverified.length} unverified record${
                filteredUnverified.length === 1 ? '' : 's'
              } currently in view`
        }
      >
        <ClipboardCheck size={14} /> Start review session
        <span className="font-num">({filteredUnverified.length})</span>
      </Button>
      <Button onClick={exportBoth} title="CSV with both unit forms and the provenance of every row">
        <Download size={14} /> Export CSV
      </Button>
      <LinkButton to="/extract/validation">
        <Gauge size={14} /> Open validation
      </LinkButton>
    </>
  );

  if (rows.length === 0) {
    return (
      <>
        <PageHeader
          eyebrow="Module 0 · Evidence"
          title="Extraction records"
          subtitle="Every quantitative claim the pipeline has pulled out of the corpus, with the span it came from."
          actions={headerActions}
        />
        <Card>
          <EmptyState
            icon={<Table2 size={22} />}
            title={paperParam ? `No records for ${paperParam}` : 'No extraction records yet'}
            body={
              paperParam
                ? scopedPaper
                  ? `${scopedPaper.title} is in the corpus but nothing has been extracted from it in this session. Run the extractor from the paper reader to stage candidate records.`
                  : `${paperParam} is not a paper in this session's corpus. Session state resets on refresh, so a link from an older session can point at nothing.`
                : 'Nothing has been extracted in this session. Ingest a paper from the demo shelf, then run the extractor to stage candidate records here.'
            }
            action={
              paperParam ? (
                <div className="flex gap-2">
                  <Button onClick={() => navigate('/ledger/records')}>Show every record</Button>
                  {scopedPaper && (
                    <LinkButton to={`/library/papers/${scopedPaper.id}`}>Open the paper</LinkButton>
                  )}
                </div>
              ) : (
                <LinkButton to="/library/ingest">Open the ingest board</LinkButton>
              )
            }
          />
        </Card>
      </>
    );
  }

  const goldCount = rows.filter((r) => r.rec.gold).length;
  const unverifiedCount = rows.filter((r) => r.rec.status === 'unverified').length;

  return (
    <>
      <PageHeader
        eyebrow="Module 0 · Evidence"
        title="Extraction records"
        subtitle="Every quantitative claim the pipeline has pulled out of the corpus, with the span it came from. Nothing here is trusted until a reviewer says so."
        actions={headerActions}
      />

      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 mb-3 text-caption text-ink-soft">
        <span>
          <span className="font-num text-ink">{rows.length}</span> records
        </span>
        <span>
          <span className="font-num text-ink">{unverifiedCount}</span> awaiting review
        </span>
        <span>
          <span className="font-num text-gold">{goldCount}</span> in the gold set
        </span>
        <ProvenanceLegend />
      </div>

      {scopedPaper && (
        <div className="mb-3">
          <Callout kind="info" title={`Scoped to ${scopedPaper.id}`}>
            Showing only records extracted from{' '}
            <span className="font-serif">{scopedPaper.title}</span>. Facet counts below describe this
            subset.{' '}
            <button className="text-accent hover:underline" onClick={() => navigate('/ledger/records')}>
              Show every record
            </button>
            .
          </Callout>
        </div>
      )}

      <DataTable
        rows={rows}
        columns={columns}
        rowKey={({ rec }) => rec.id}
        tickOf={({ prov }) => prov}
        facets={facets}
        dense={density === 'dense'}
        toolbar={toolbar}
        onFilteredChange={handleFiltered}
        onOpen={({ rec }) => navigate(`/library/papers/${rec.paperId}?span=${rec.id}`)}
        searchOf={({ rec }) =>
          `${rec.id} ${rec.paperId} ${fieldName(rec.field)} ${rec.field} ${rec.unit} ${
            rec.si.unit
          } ${rec.organism ?? ''} ${rec.componentTag ?? ''} ${rec.quote}`
        }
        emptyTitle="No records match"
        emptyBody="Every record was filtered out. Clear a facet or widen the row filter."
        exportNote={
          unitMode === 'si'
            ? 'Values are converted from the stored published pair on every render, so switching back is lossless.'
            : undefined
        }
      />

      <p className="text-caption text-ink-soft mt-3 max-w-3xl">
        Double-click a row (or press Enter) to open the quoted span inside the paper. “Export CSV”
        writes both the as-published and SI forms alongside each row&rsquo;s provenance, so a
        downstream reader never has to guess which unit a number is in.
      </p>
    </>
  );
}
