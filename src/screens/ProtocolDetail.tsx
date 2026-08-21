// Protocol detail (OF-DES-001 §8.11) — the screen where a literature-derived
// procedure becomes executable. The batch-size control is the spine: every
// bound quantity in the steps and every row of the materials table is
// recomputed from @/engine/scale, so scaling 1 L → 5 L is one number changing
// in one place and nothing else needing to agree by hand.
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowRight,
  ChevronDown,
  ClipboardList,
  Copy,
  Download,
  FileText,
  GitCompare,
  Play,
  Square,
  Timer as TimerIcon,
  Wrench,
} from 'lucide-react';
import type { ExtractionRecord, Protocol, ProtocolVersion, RunState, Step } from '@/data/types';
import { useStore } from '@/store';
import { fieldName } from '@/data/ontology';
import { href, navigate } from '@/router';
import {
  batchLabel,
  materialsChecklist,
  renderStepText,
  scaleMaterials,
  type ScaledMaterial,
} from '@/engine/scale';
import { diffVersions } from '@/engine/diff';
import { convert, fmt, normalizeUnit, sameFamily } from '@/engine/units';
import { CitationChip } from '@/components/Chip';
import { Markdown, inlineMarkdown } from '@/components/Markdown';
import { ProvDot, ProvenanceBadge, Tick, type ProvKind } from '@/components/Provenance';
import {
  Button,
  Callout,
  Card,
  EmptyState,
  LinkButton,
  PageHeader,
  SectionTitle,
  Sheet,
  cx,
} from '@/components/ui';
import { exportCSV, exportText } from '@/lib/csv';
import { partEyebrow } from '@/data/parts';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('runbook', 'corpus');
import {
  CAPABILITY_META,
  CATEGORY_META,
  capabilitiesOf,
  capabilityKeys,
  capabilityReason,
  fmtMinutes,
  protocolProvenance,
  provenanceFromRefs,
  strainLabel,
} from '@/screens/Protocols';

// ── formatting helpers ─────────────────────────────────────────────────

const PLACEHOLDER_SPLIT = /(\{\{(?:qty|stock):[^}]+\}\})/g;
const PLACEHOLDER_EXACT = /^\{\{(?:qty|stock):[^}]+\}\}$/;
const PLACEHOLDER_SCAN = /\{\{(?:qty|stock):([^}]+)\}\}/g;

function fmtTimer(sec: number): string {
  const s = Math.max(0, Math.round(sec));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  const p = (n: number) => String(n).padStart(2, '0');
  return h > 0 ? `${h}:${p(m)}:${p(r)}` : `${m}:${p(r)}`;
}

function clockLabel(epoch: number): string {
  return new Date(epoch).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/** A step's provenance: what it cites, plus the sources of what it binds. */
function stepProvenance(
  step: Step,
  version: ProtocolVersion,
  records: ExtractionRecord[],
): ProvKind {
  const recordIds = new Set<string>();
  const paperIds = new Set<string>();
  for (const ref of step.refs ?? []) (ref.startsWith('r-') ? recordIds : paperIds).add(ref);
  for (const m of step.text.matchAll(PLACEHOLDER_SCAN)) {
    const mat = version.materials.find((x) => x.name === m[1]);
    if (mat?.sourceRecordId) recordIds.add(mat.sourceRecordId);
  }
  return provenanceFromRefs(recordIds, paperIds, records);
}

/** Chip for a step/version reference id — records are `ex-…`, papers `SP-…`. */
function RefChip({ id }: { id: string }) {
  return id.startsWith('r-') ? <CitationChip recordId={id} /> : <CitationChip paperId={id} />;
}

// ── batch-size parsing (unit-aware, tolerant of non-metric base units) ──

type ScaleParse = { ok: true; scale: number } | { ok: false; error: string };

function parseBatch(text: string, base: { value: number; unit: string }): ScaleParse {
  const t = text.trim();
  const m = t.match(/^(-?\d+(?:[.,]\d+)?(?:[eE]-?\d+)?)\s*(.*)$/);
  if (!m) return { ok: false, error: `Enter a batch size, e.g. “${fmt(base.value)} ${base.unit}”.` };
  const value = parseFloat(m[1].replace(',', '.'));
  if (!isFinite(value)) return { ok: false, error: 'That is not a number.' };
  const rawUnit = m[2].trim();

  const finish = (inBaseUnit: number): ScaleParse =>
    inBaseUnit > 0
      ? { ok: true, scale: inBaseUnit / base.value }
      : { ok: false, error: 'Batch size has to be greater than zero.' };

  if (rawUnit === '') return finish(value);

  const baseNorm = normalizeUnit(base.unit);
  const norm = normalizeUnit(rawUnit);
  if (baseNorm === null || norm === null) {
    // The converter doesn't know this family (e.g. "samples"), so the only
    // safe reading is the protocol's own spelling of its batch unit.
    if (rawUnit.toLowerCase() !== base.unit.toLowerCase())
      return { ok: false, error: `This protocol's batch is measured in ${base.unit}.` };
    return finish(value);
  }
  if (!sameFamily(norm, baseNorm))
    return { ok: false, error: `“${rawUnit}” is not compatible with ${base.unit}.` };
  try {
    return finish(convert(value, norm, baseNorm));
  } catch {
    return { ok: false, error: `Cannot convert ${rawUnit} to ${base.unit}.` };
  }
}

// ── every difference diffVersions does not already model ───────────────

interface OtherChange {
  label: string;
  before?: string;
  after?: string;
}

function refKey(r: { paperId?: string; recordId?: string; note?: string }): string {
  return `${r.paperId ?? ''}|${r.recordId ?? ''}|${r.note ?? ''}`;
}

function refLabel(r: { paperId?: string; recordId?: string; note?: string }): string {
  const id = r.recordId ?? r.paperId ?? '—';
  return r.note ? `${id} — ${r.note}` : id;
}

/**
 * diffVersions compares step text/timer/sub-checks and material
 * amount/unit/scaling. Everything else a ProtocolVersion carries is compared
 * here, so the compare panel accounts for every field that can differ:
 * baseBatch, estMinutes, equipment, safety, references, step order, step
 * rationale/timer-label/refs, and material precision/stock/source record.
 */
function otherChanges(a: ProtocolVersion, b: ProtocolVersion): OtherChange[] {
  const out: OtherChange[] = [];

  if (
    a.baseBatch.value !== b.baseBatch.value ||
    a.baseBatch.unit !== b.baseBatch.unit ||
    a.baseBatch.label !== b.baseBatch.label
  )
    out.push({
      label: 'Base batch',
      before: `${fmt(a.baseBatch.value)} ${a.baseBatch.unit} ${a.baseBatch.label}`,
      after: `${fmt(b.baseBatch.value)} ${b.baseBatch.unit} ${b.baseBatch.label}`,
    });
  if (a.estMinutes.active !== b.estMinutes.active)
    out.push({
      label: 'Estimated active time',
      before: fmtMinutes(a.estMinutes.active),
      after: fmtMinutes(b.estMinutes.active),
    });
  if (a.estMinutes.total !== b.estMinutes.total)
    out.push({
      label: 'Estimated total time',
      before: fmtMinutes(a.estMinutes.total),
      after: fmtMinutes(b.estMinutes.total),
    });

  for (const e of b.equipment) if (!a.equipment.includes(e)) out.push({ label: 'Equipment added', after: e });
  for (const e of a.equipment) if (!b.equipment.includes(e)) out.push({ label: 'Equipment removed', before: e });
  for (const s of b.safety) if (!a.safety.includes(s)) out.push({ label: 'Safety note added', after: s });
  for (const s of a.safety) if (!b.safety.includes(s)) out.push({ label: 'Safety note removed', before: s });

  const aRefs = a.references.map(refKey);
  const bRefs = b.references.map(refKey);
  for (const r of b.references)
    if (!aRefs.includes(refKey(r))) out.push({ label: 'Reference added', after: refLabel(r) });
  for (const r of a.references)
    if (!bRefs.includes(refKey(r))) out.push({ label: 'Reference removed', before: refLabel(r) });

  const aSteps = new Map(a.steps.map((s) => [s.id, s]));
  for (const s of b.steps) {
    const prev = aSteps.get(s.id);
    if (!prev) continue;
    if ((prev.note ?? '') !== (s.note ?? ''))
      out.push({ label: `Step ${s.id} rationale`, before: prev.note || '—', after: s.note || '—' });
    if ((prev.timerLabel ?? '') !== (s.timerLabel ?? ''))
      out.push({
        label: `Step ${s.id} timer label`,
        before: prev.timerLabel || '—',
        after: s.timerLabel || '—',
      });
    if ((prev.refs ?? []).join(',') !== (s.refs ?? []).join(','))
      out.push({
        label: `Step ${s.id} references`,
        before: (prev.refs ?? []).join(', ') || '—',
        after: (s.refs ?? []).join(', ') || '—',
      });
  }
  const sharedInB = b.steps.filter((s) => aSteps.has(s.id)).map((s) => s.id);
  const sharedInA = a.steps.filter((s) => b.steps.some((x) => x.id === s.id)).map((s) => s.id);
  if (sharedInA.join('>') !== sharedInB.join('>'))
    out.push({ label: 'Step order', before: sharedInA.join(' → '), after: sharedInB.join(' → ') });

  const aMats = new Map(a.materials.map((m) => [m.name, m]));
  for (const m of b.materials) {
    const prev = aMats.get(m.name);
    if (!prev) continue;
    if (prev.precision !== m.precision)
      out.push({
        label: `${m.name} — rounding increment`,
        before: `${fmt(prev.precision)} ${prev.unit}`,
        after: `${fmt(m.precision)} ${m.unit}`,
      });
    const stockOf = (s?: { conc: number; unit: string }, unit?: string) =>
      s ? `${fmt(s.conc)} ${unit} per ${s.unit}` : 'no stock solution';
    if (JSON.stringify(prev.stock ?? null) !== JSON.stringify(m.stock ?? null))
      out.push({
        label: `${m.name} — stock solution`,
        before: stockOf(prev.stock, prev.unit),
        after: stockOf(m.stock, m.unit),
      });
    if ((prev.sourceRecordId ?? '') !== (m.sourceRecordId ?? ''))
      out.push({
        label: `${m.name} — source record`,
        before: prev.sourceRecordId ?? '—',
        after: m.sourceRecordId ?? '—',
      });
  }
  return out;
}

// ── step text with live quantity binding ───────────────────────────────

function StepText({
  step,
  version,
  scale,
}: {
  step: Step;
  version: ProtocolVersion;
  scale: number;
}) {
  const parts = step.text.split(PLACEHOLDER_SPLIT);
  return (
    <span>
      {parts.map((part, i) =>
        PLACEHOLDER_EXACT.test(part) ? (
          <span
            key={i}
            className="font-num rounded-input bg-accent-wash px-1 py-[1px] border border-accent/25"
            title="Bound quantity — recomputed from the materials list at the current batch size"
          >
            {/* The engine renders it, so the step and the table can never disagree. */}
            {renderStepText({ ...step, text: part }, version, scale)}
          </span>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </span>
  );
}

// ── step card ──────────────────────────────────────────────────────────

function StepCard({
  step,
  index,
  version,
  scale,
  records,
}: {
  step: Step;
  index: number;
  version: ProtocolVersion;
  scale: number;
  records: ExtractionRecord[];
}) {
  const [noteOpen, setNoteOpen] = useState(false);
  const prov = stepProvenance(step, version, records);
  return (
    <Card className="p-0 overflow-hidden">
      <Tick p={prov} className="py-3 pr-3" title={`Step ${index + 1} — ${prov} provenance`}>
        <div className="flex items-start gap-3">
          <div className="font-num text-caption text-ink-soft w-6 shrink-0 text-right pt-[2px]">
            {index + 1}
          </div>
          <div className="flex-1 min-w-0 space-y-2">
            <div className="text-body leading-relaxed">
              <StepText step={step} version={version} scale={scale} />
            </div>

            {(step.timerSec !== undefined || (step.refs?.length ?? 0) > 0) && (
              <div className="flex flex-wrap items-center gap-1.5">
                {step.timerSec !== undefined && (
                  <span
                    className="chip text-signal-info border-signal-info/40"
                    title="Run Mode starts this countdown when the step opens"
                  >
                    <TimerIcon size={11} aria-hidden />
                    Timer: <span className="font-num">{fmtTimer(step.timerSec)}</span>
                    {step.timerLabel && <span className="text-ink-soft">— {step.timerLabel}</span>}
                  </span>
                )}
                {(step.refs ?? []).map((r) => (
                  <RefChip key={r} id={r} />
                ))}
              </div>
            )}

            {step.multiCheck && step.multiCheck.length > 0 && (
              <div className="rounded-input border border-line bg-surface-0 p-2">
                <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">
                  Sub-checks — ticked off during a run
                </div>
                <ul className="space-y-0.5">
                  {step.multiCheck.map((c, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-body">
                      <Square size={13} className="mt-[3px] shrink-0 text-ink-soft" aria-hidden />
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {step.note && (
              <div>
                <button
                  className="text-caption text-ink-soft hover:text-accent inline-flex items-center gap-1"
                  aria-expanded={noteOpen}
                  aria-controls={`step-note-${step.id}`}
                  onClick={() => setNoteOpen((o) => !o)}
                >
                  <ChevronDown
                    size={12}
                    className={cx('transition-transform', noteOpen && 'rotate-180')}
                    aria-hidden
                  />
                  {noteOpen ? 'Hide rationale' : 'Why this step'}
                </button>
                <div
                  id={`step-note-${step.id}`}
                  className={cx(
                    'mt-1.5 rounded-input border border-line bg-surface-0 p-2 text-body text-ink-soft',
                    !noteOpen && 'hidden',
                  )}
                >
                  {inlineMarkdown(step.note, `note-${step.id}`)}
                </div>
              </div>
            )}
          </div>
        </div>
      </Tick>
    </Card>
  );
}

// ── materials table ────────────────────────────────────────────────────

function MaterialsTable({
  materials,
  records,
}: {
  materials: ScaledMaterial[];
  records: ExtractionRecord[];
}) {
  if (materials.length === 0)
    return (
      <p className="text-body text-ink-soft">
        This version declares no materials — it consumes only what the steps name inline.
      </p>
    );
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-body">
        <caption className="sr-only">
          Materials recomputed for the current batch size
        </caption>
        <thead>
          <tr className="border-b border-line">
            <th className="text-caption font-medium text-ink-soft text-left px-1 py-1.5">Item</th>
            <th className="text-caption font-medium text-ink-soft text-right px-1 py-1.5">Amount</th>
            <th className="text-caption font-medium text-ink-soft text-left px-1 py-1.5">Unit</th>
          </tr>
        </thead>
        <tbody>
          {materials.map((m) => {
            const rec = m.sourceRecordId ? records.find((r) => r.id === m.sourceRecordId) : undefined;
            const prov: ProvKind = m.sourceRecordId
              ? provenanceFromRefs([m.sourceRecordId], [], records)
              : 'demo';
            return (
              <tr key={m.name} className="border-b border-line/60 align-top">
                <td className="px-1 py-1.5">
                  <div className="flex items-start gap-1.5">
                    <span className="mt-[6px] shrink-0">
                      <ProvDot p={prov} size={7} />
                    </span>
                    <div className="min-w-0">
                      <div>{m.name}</div>
                      {!m.scales && (
                        <div
                          className="text-caption text-signal-warn"
                          title="Declared scaling class: fixed"
                        >
                          does not scale
                        </div>
                      )}
                      {m.stockVolume && m.stock && (
                        <div className="text-caption text-ink-soft font-num">
                          use {fmt(m.stockVolume.value)} {m.stockVolume.unit} of stock (
                          {fmt(m.stock.conc)} {m.unit} per {m.stock.unit})
                        </div>
                      )}
                      {m.sourceRecordId && (
                        <div className="mt-0.5">
                          <CitationChip
                            recordId={m.sourceRecordId}
                            label={rec ? rec.id : m.sourceRecordId}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-1 py-1.5 text-right font-num whitespace-nowrap">
                  {fmt(m.scaledAmount)}
                </td>
                <td className="px-1 py-1.5 font-num text-ink-soft whitespace-nowrap">{m.unit}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── version compare ────────────────────────────────────────────────────

function ChangeBadge({ kind }: { kind: 'added' | 'removed' | 'modified' | 'unchanged' }) {
  const cls =
    kind === 'added'
      ? 'text-accent border-accent/40'
      : kind === 'removed'
        ? 'text-signal-error border-signal-error/40'
        : kind === 'modified'
          ? 'text-signal-warn border-signal-warn/40'
          : 'text-ink-soft';
  return <span className={cx('chip text-caption', cls)}>{kind}</span>;
}

function CompareBody({
  protocol,
  aVersion,
  bVersion,
  onPick,
}: {
  protocol: Protocol;
  aVersion: string;
  bVersion: string;
  onPick: (which: 'a' | 'b', v: string) => void;
}) {
  const [showUnchanged, setShowUnchanged] = useState(false);
  const a = protocol.versions.find((v) => v.version === aVersion);
  const b = protocol.versions.find((v) => v.version === bVersion);

  const picker = (
    <div className="flex flex-wrap items-center gap-2 mb-4">
      <label className="text-caption text-ink-soft" htmlFor="cmp-a">
        Baseline
      </label>
      {/* `.input` hard-sets width:100%, so the sizing lives on a wrapper. */}
      <div className="w-[104px]">
        <select
          id="cmp-a"
          className="input font-num"
          value={aVersion}
          onChange={(e) => onPick('a', e.target.value)}
        >
          {protocol.versions.map((v) => (
            <option key={v.version} value={v.version}>
              v{v.version}
            </option>
          ))}
        </select>
      </div>
      <ArrowRight size={14} className="text-ink-soft" aria-hidden />
      <label className="text-caption text-ink-soft" htmlFor="cmp-b">
        Compared
      </label>
      <div className="w-[104px]">
        <select
          id="cmp-b"
          className="input font-num"
          value={bVersion}
          onChange={(e) => onPick('b', e.target.value)}
        >
          {protocol.versions.map((v) => (
            <option key={v.version} value={v.version}>
              v{v.version}
            </option>
          ))}
        </select>
      </div>
    </div>
  );

  if (!a || !b)
    return (
      <>
        {picker}
        <EmptyState
          title="Version unavailable"
          body="One of the selected versions is no longer in this session."
        />
      </>
    );

  if (a.version === b.version)
    return (
      <>
        {picker}
        <Callout kind="info" title="Same version on both sides">
          Pick two different versions to see what changed between them.
        </Callout>
      </>
    );

  const diff = diffVersions(a, b);
  const other = otherChanges(a, b);
  const stepAdds = diff.steps.filter((s) => s.kind === 'added');
  const stepRemoves = diff.steps.filter((s) => s.kind === 'removed');
  const stepMods = diff.steps.filter((s) => s.kind === 'modified');
  const stepSame = diff.steps.filter((s) => s.kind === 'unchanged');
  const matAdds = diff.materials.filter((m) => m.kind === 'added');
  const matRemoves = diff.materials.filter((m) => m.kind === 'removed');
  const matMods = diff.materials.filter((m) => m.kind === 'modified');
  const totalChanges =
    stepAdds.length +
    stepRemoves.length +
    stepMods.length +
    matAdds.length +
    matRemoves.length +
    matMods.length +
    other.length;

  return (
    <>
      {picker}

      <Callout kind="info" title={`Why v${b.version} exists`}>
        {diff.changelog ? (
          <span>{inlineMarkdown(diff.changelog, 'changelog')}</span>
        ) : (
          <span className="text-ink-soft">
            No changelog was recorded on v{b.version}. The differences below are what actually
            changed.
          </span>
        )}
      </Callout>

      <p className="text-caption text-ink-soft mt-3 font-num">
        {totalChanges === 0
          ? 'v' + a.version + ' and v' + b.version + ' are identical in every field.'
          : `${totalChanges} difference${totalChanges === 1 ? '' : 's'}: ` +
            `${stepAdds.length} step${stepAdds.length === 1 ? '' : 's'} added, ` +
            `${stepRemoves.length} removed, ${stepMods.length} changed · ` +
            `${matAdds.length} material${matAdds.length === 1 ? '' : 's'} added, ` +
            `${matRemoves.length} removed, ${matMods.length} changed · ` +
            `${other.length} other`}
      </p>

      {/* Materials */}
      <div className="mt-5">
        <SectionTitle>Materials</SectionTitle>
        {diff.materials.filter((m) => m.kind !== 'unchanged').length === 0 ? (
          <p className="text-body text-ink-soft">No material changed between these versions.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-body">
              <thead>
                <tr className="border-b border-line">
                  <th className="text-caption font-medium text-ink-soft text-left px-2 py-1.5">
                    Material
                  </th>
                  <th className="text-caption font-medium text-ink-soft text-left px-2 py-1.5 font-num">
                    v{a.version}
                  </th>
                  <th className="text-caption font-medium text-ink-soft text-left px-2 py-1.5 font-num">
                    v{b.version}
                  </th>
                  <th className="text-caption font-medium text-ink-soft text-left px-2 py-1.5">
                    Change
                  </th>
                </tr>
              </thead>
              <tbody>
                {diff.materials
                  .filter((m) => m.kind !== 'unchanged')
                  .map((m) => (
                    <tr key={`${m.kind}-${m.name}`} className="border-b border-line/60 align-top">
                      <td className="px-2 py-1.5">{m.name}</td>
                      <td className="px-2 py-1.5 font-num">
                        {m.a ? `${fmt(m.a.amount)} ${m.a.unit}` : <span className="text-ink-soft">—</span>}
                      </td>
                      <td className="px-2 py-1.5 font-num">
                        {m.b ? `${fmt(m.b.amount)} ${m.b.unit}` : <span className="text-ink-soft">—</span>}
                      </td>
                      <td className="px-2 py-1.5">
                        <ChangeBadge kind={m.kind} />
                        {m.kind === 'modified' && m.a && m.b && m.a.scaling !== m.b.scaling && (
                          <div className="text-caption text-ink-soft mt-0.5">
                            scaling {m.a.scaling} → {m.b.scaling}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Steps */}
      <div className="mt-6">
        <SectionTitle
          right={
            stepSame.length > 0 ? (
              <button
                className="text-caption text-accent hover:underline"
                aria-expanded={showUnchanged}
                onClick={() => setShowUnchanged((s) => !s)}
              >
                {showUnchanged ? 'Hide' : 'Show'} {stepSame.length} unchanged
              </button>
            ) : undefined
          }
        >
          Steps
        </SectionTitle>
        <div className="space-y-2">
          {diff.steps.map((d, i) => {
            if (d.kind === 'unchanged' && !showUnchanged) return null;
            const id = d.b?.id ?? d.a?.id ?? `d${i}`;
            return (
              <div key={`${d.kind}-${id}`} className="rounded-card border border-line p-2.5">
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="font-num text-caption text-ink-soft">{id}</span>
                  <ChangeBadge kind={d.kind} />
                  {d.kind === 'modified' && d.a && d.b && (
                    <span className="text-caption text-ink-soft">
                      {[
                        d.a.text !== d.b.text ? 'instruction' : null,
                        d.a.timerSec !== d.b.timerSec ? 'timer' : null,
                        JSON.stringify(d.a.multiCheck ?? null) !==
                        JSON.stringify(d.b.multiCheck ?? null)
                          ? 'sub-checks'
                          : null,
                      ]
                        .filter(Boolean)
                        .join(', ')}
                    </span>
                  )}
                </div>
                {d.kind === 'modified' ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div className="rounded-input border border-signal-error/30 bg-signal-error/[0.05] p-2">
                      <div className="text-caption text-ink-soft font-num mb-1">v{a.version}</div>
                      <div className="text-body">{renderStepText(d.a!, a, 1)}</div>
                      {d.a!.timerSec !== undefined && (
                        <div className="text-caption text-ink-soft font-num mt-1">
                          timer {fmtTimer(d.a!.timerSec)}
                        </div>
                      )}
                      {d.a!.multiCheck && (
                        <div className="text-caption text-ink-soft mt-1">
                          {d.a!.multiCheck.length} sub-check
                          {d.a!.multiCheck.length === 1 ? '' : 's'}
                        </div>
                      )}
                    </div>
                    <div className="rounded-input border border-accent/30 bg-accent-wash/60 p-2">
                      <div className="text-caption text-ink-soft font-num mb-1">v{b.version}</div>
                      <div className="text-body">{renderStepText(d.b!, b, 1)}</div>
                      {d.b!.timerSec !== undefined && (
                        <div className="text-caption text-ink-soft font-num mt-1">
                          timer {fmtTimer(d.b!.timerSec)}
                        </div>
                      )}
                      {d.b!.multiCheck && (
                        <div className="text-caption text-ink-soft mt-1">
                          {d.b!.multiCheck.length} sub-check
                          {d.b!.multiCheck.length === 1 ? '' : 's'}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div
                    className={cx(
                      'rounded-input border p-2 text-body',
                      d.kind === 'added'
                        ? 'border-accent/30 bg-accent-wash/60'
                        : d.kind === 'removed'
                          ? 'border-signal-error/30 bg-signal-error/[0.05]'
                          : 'border-line bg-surface-0',
                    )}
                  >
                    {d.kind === 'removed' ? renderStepText(d.a!, a, 1) : renderStepText(d.b!, b, 1)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
        <p className="text-caption text-ink-soft mt-2">
          Step text is shown at each version's own base batch, so a quantity change reads directly as
          old versus new.
        </p>
      </div>

      {/* Everything else */}
      <div className="mt-6">
        <SectionTitle>Other changes</SectionTitle>
        {other.length === 0 ? (
          <p className="text-body text-ink-soft">
            No other field differs — equipment, safety, timings, references, step order and material
            specs are identical.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {other.map((c, i) => (
              <li key={i} className="text-body">
                <span className="text-ink-soft">{c.label}: </span>
                {c.before !== undefined && <span className="line-through opacity-70">{c.before}</span>}
                {c.before !== undefined && c.after !== undefined && (
                  <ArrowRight size={12} className="inline mx-1 align-[-1px] text-ink-soft" aria-hidden />
                )}
                {c.after !== undefined && <span>{c.after}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}

// ── screen ─────────────────────────────────────────────────────────────

export default function ProtocolDetail({ protocolId }: { protocolId: string }) {
  const protocol = useStore((s) => s.protocols.find((p) => p.id === protocolId));
  const records = useStore((s) => s.records);
  // Corrections upstream age this protocol. Reading the patches here is what
  // turns "propagates to downstream artifacts" from a claim into something a
  // reader watches happen.
  //
  // Select the array, filter outside the selector: a selector that builds a new
  // array returns a fresh identity on every store read, so zustand's Object.is
  // check never settles and the component re-renders until React gives up.
  const stale = useStore((s) => s.stale);
  const stalePatches = useMemo(
    () => stale.filter((x) => x.dependents.protocols.includes(protocolId)),
    [stale, protocolId],
  );
  const strains = useStore((s) => s.strains);
  const runs = useStore((s) => s.runs);
  const startRun = useStore((s) => s.startRun);
  const toast = useStore((s) => s.toast);

  const [versionId, setVersionId] = useState<string | null>(null);
  const [scale, setScale] = useState(1);
  const [batchText, setBatchText] = useState(() => {
    const p = useStore.getState().protocols.find((x) => x.id === protocolId);
    const v = p?.versions.find((x) => x.version === p.currentVersion) ?? p?.versions[0];
    return v ? `${fmt(v.baseBatch.value)} ${v.baseBatch.unit}` : '';
  });
  const [compareOpen, setCompareOpen] = useState(false);
  const [cmpA, setCmpA] = useState<string>('');
  const [cmpB, setCmpB] = useState<string>('');
  const batchRef = useRef<HTMLInputElement>(null);
  const scaleRef = useRef(scale);
  scaleRef.current = scale;

  const version = useMemo<ProtocolVersion | null>(() => {
    if (!protocol) return null;
    return (
      protocol.versions.find((v) => v.version === versionId) ??
      protocol.versions.find((v) => v.version === protocol.currentVersion) ??
      protocol.versions[0] ??
      null
    );
  }, [protocol, versionId]);

  // Switching versions keeps the operator's chosen scale but restates the batch
  // in the new version's own base units.
  useEffect(() => {
    if (!version) return;
    setBatchText(`${fmt(version.baseBatch.value * scaleRef.current)} ${version.baseBatch.unit}`);
  }, [version]);

  const parse = useMemo<ScaleParse>(
    () => (version ? parseBatch(batchText, version.baseBatch) : { ok: false, error: '' }),
    [batchText, version],
  );

  const scaled = useMemo<ScaledMaterial[]>(
    () => (version ? scaleMaterials(version, scale) : []),
    [version, scale],
  );

  const protocolRuns = useMemo<RunState[]>(
    () =>
      Object.values(runs)
        .filter((r) => r.protocolId === protocolId)
        .sort((a, b) => b.startedAt - a.startedAt),
    [runs, protocolId],
  );

  if (!protocol || !version) {
    return (
      <>
        <PageHeader title="Protocol not found" eyebrow={EYEBROW} />
        <Card>
          <EmptyState
            title="No such protocol"
            body={`Nothing in this session has the id “${protocolId}”. It may have been renamed, or the link is from a different build.`}
            icon={<ClipboardList size={22} />}
            action={<LinkButton to="/protocols">Back to all protocols</LinkButton>}
          />
        </Card>
      </>
    );
  }

  const meta = CATEGORY_META[protocol.category];
  const Glyph = meta.Icon;
  const caps = capabilitiesOf(version);
  const prov = protocolProvenance(version, records);
  const isCurrent = version.version === protocol.currentVersion;
  const citedMaterials = version.materials.filter((m) => m.sourceRecordId).length;
  const citedSteps = version.steps.filter((s) => (s.refs?.length ?? 0) > 0).length;
  const extreme = scale > 20 || scale < 0.1;

  const setBatch = (t: string) => {
    setBatchText(t);
    const p = parseBatch(t, version.baseBatch);
    if (p.ok) setScale(p.scale);
  };

  const setQuickScale = (mult: number) => {
    setScale(mult);
    setBatchText(`${fmt(version.baseBatch.value * mult)} ${version.baseBatch.unit}`);
  };

  const copyChecklist = () => {
    const text = materialsChecklist(version, scale, protocol.title);
    const filename = `${protocol.id}-v${version.version}-materials.txt`;
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(
        () =>
          toast({
            text: `Materials checklist copied — ${scaled.length} items at ${batchLabel(version, scale)}`,
            kind: 'success',
          }),
        () => {
          exportText(filename, text);
          toast({
            text: 'Clipboard was refused, so the checklist downloaded as a text file instead',
            kind: 'info',
          });
        },
      );
    } else {
      exportText(filename, text);
      toast({
        text: 'This browser exposes no clipboard, so the checklist downloaded as a text file',
        kind: 'info',
      });
    }
  };

  const exportMaterials = () => {
    exportCSV(
      `openferment-${protocol.id}-v${version.version}-materials.csv`,
      [
        'Material',
        'Amount',
        'Unit',
        'Scaling class',
        'Scales with batch',
        'Stock concentration',
        'Stock unit',
        'Stock volume',
        'Source record',
      ],
      scaled.map((m) => [
        m.name,
        m.scaledAmount,
        m.unit,
        m.scaling,
        m.scales ? 'yes' : 'no',
        m.stock ? m.stock.conc : '',
        m.stock ? m.stock.unit : '',
        m.stockVolume ? `${m.stockVolume.value} ${m.stockVolume.unit}` : '',
        m.sourceRecordId ?? '',
      ]),
    );
  };

  const beginRun = () => {
    const runId = startRun(protocol.id, version.version, scale);
    navigate(`/runbook/${protocol.id}/run/${runId}`);
  };

  const openCompare = () => {
    const idx = protocol.versions.findIndex((v) => v.version === version.version);
    const aIdx = idx > 0 ? idx - 1 : 0;
    const bIdx = idx > 0 ? idx : Math.min(1, protocol.versions.length - 1);
    setCmpA(protocol.versions[aIdx].version);
    setCmpB(protocol.versions[bIdx].version);
    setCompareOpen(true);
  };

  return (
    <>
      {stalePatches.length > 0 && (
        <div className="mb-3">
          <Callout
            kind="warn"
            title={`Stale — ${stalePatches.length} source record${stalePatches.length === 1 ? '' : 's'} changed since this was last read`}
          >
            <ul className="space-y-1">
              {stalePatches.map((patch) => (
                <li key={patch.recordId} className="text-caption">
                  <a
                    href={href(`/ledger/records?record=${patch.recordId}`)}
                    className="font-mono text-accent hover:underline"
                  >
                    {patch.recordId}
                  </a>{' '}
                  {patch.diff ? (
                    <>
                      changed from{' '}
                      <span className="font-num">
                        {fmt(patch.diff.before)} {patch.diff.unit}
                      </span>{' '}
                      to{' '}
                      <span className="font-num text-ink">
                        {fmt(patch.diff.after)} {patch.diff.unit}
                      </span>
                    </>
                  ) : (
                    <>was edited</>
                  )}{' '}
                  <span className="text-ink-soft">· {patch.changedAt}</span>
                </li>
              ))}
            </ul>
            <p className="mt-1.5 text-caption text-ink-soft">
              Quantities below still reflect the values as they were bound. Re-derive before
              running this at the bench.
            </p>
          </Callout>
        </div>
      )}
      {version.decisive && (
        // Above the fold, deliberately. This is the return leg of the
        // experiment loop: a tornado bar names the parameter, and this says
        // what running the protocol would settle. Burying it under the
        // materials list would make the loop a diagram rather than a path.
        <Card className="p-3 mb-3 border-accent/45 bg-accent-wash/30">
          <div className="flex items-baseline justify-between gap-3 flex-wrap">
            <span className="text-caption uppercase tracking-wide text-accent">
              Decisive measurement
            </span>
            <a
              href={href(`/ledger/p/${version.decisive.field}`)}
              className="text-caption text-accent hover:underline"
            >
              {fieldName(version.decisive.field)} →
            </a>
          </div>
          <p className="text-reading font-serif mt-1.5">
            {version.decisive.currentUncertainty}
          </p>
          <p className="text-body mt-2">
            <span className="text-ink-soft">What a result would change: </span>
            {version.decisive.whatWouldChange}
          </p>
        </Card>
      )}

      <PageHeader
        eyebrow={
          <span className="inline-flex items-center gap-1.5">
            <Glyph size={13} aria-hidden />
            <span className="font-num">{protocol.id}</span> · {meta.label}
          </span>
        }
        title={protocol.title}
        actions={
          <>
            <label className="sr-only" htmlFor="version-select">
              Protocol version
            </label>
            {/* `.input` hard-sets width:100%, so the sizing lives on a wrapper. */}
            <div className="w-[148px]">
              <select
                id="version-select"
                className="input font-num"
                value={version.version}
                onChange={(e) => setVersionId(e.target.value)}
                title="Show a different version of this protocol"
              >
                {protocol.versions.map((v) => (
                  <option key={v.version} value={v.version}>
                    v{v.version}
                    {v.version === protocol.currentVersion ? ' (current)' : ''}
                  </option>
                ))}
              </select>
            </div>
            <Button
              onClick={openCompare}
              disabled={protocol.versions.length < 2}
              title={
                protocol.versions.length < 2
                  ? 'Only one version of this protocol exists — nothing to compare against'
                  : 'Side-by-side diff of two versions'
              }
            >
              <GitCompare size={14} /> Compare versions
            </Button>
            <LinkButton to={`/runbook/${protocol.id}/edit`} size="sm">
              <FileText size={13} /> Edit
            </LinkButton>
          </>
        }
      />

      {!isCurrent && (
        <div className="mb-4">
          <Callout kind="warn" title={`You are reading v${version.version}, not the current version`}>
            The current version is{' '}
            <span className="font-num">v{protocol.currentVersion}</span>. Runs started from here will
            record v{version.version}.{' '}
            <button className="text-accent hover:underline" onClick={() => setVersionId(protocol.currentVersion)}>
              Switch to the current version
            </button>
          </Callout>
        </div>
      )}

      {/* Meta strip */}
      <Card className="p-3 mb-4">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <span className="chip text-caption text-ink-soft" title={meta.blurb}>
            <Glyph size={11} aria-hidden />
            {meta.label}
          </span>
          {protocol.organisms.length === 0 ? (
            <span className="text-caption text-ink-soft">Organism-independent</span>
          ) : (
            <span className="flex flex-wrap items-center gap-1">
              {protocol.organisms.map((o) => {
                const s = strainLabel(o, strains);
                return (
                  <a
                    key={o}
                    href={href(`/geneos/${o}`)}
                    className="chip text-caption text-ink-soft hover:border-accent/40 hover:bg-accent-wash"
                    title={s.title}
                  >
                    {s.label}
                  </a>
                );
              })}
            </span>
          )}
          <span
            className="chip text-caption text-signal-warn border-signal-warn/40"
            title="Handle at this containment level. Local biosafety rules take precedence."
          >
            BSL-<span className="font-num">{protocol.bsl}</span>
          </span>
          <span className="text-caption text-ink-soft font-num">
            {fmtMinutes(version.estMinutes.active)} active · {fmtMinutes(version.estMinutes.total)}{' '}
            total · {version.steps.length} steps
          </span>
          <span className="flex items-center gap-1">
            {capabilityKeys(caps).map((k) => {
              const Icon = CAPABILITY_META[k].Icon;
              return (
                <span key={k} className="chip text-caption text-ink-soft" title={capabilityReason(k, caps)}>
                  <Icon size={11} aria-hidden />
                  {CAPABILITY_META[k].label}
                </span>
              );
            })}
          </span>
        </div>
        <div className="flex items-start gap-2 mt-2.5 pt-2.5 border-t border-line">
          <ProvenanceBadge p={prov} compact />
          <p className="text-caption text-ink-soft flex-1 min-w-0">
            {inlineMarkdown(protocol.provenanceNote, 'provnote')}{' '}
            <span className="font-num">
              {citedMaterials}/{version.materials.length}
            </span>{' '}
            materials and{' '}
            <span className="font-num">
              {citedSteps}/{version.steps.length}
            </span>{' '}
            steps cite a source. Everything else is a demo value authored for this simulation.
          </p>
        </div>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_420px] gap-5 items-start">
        {/* ── main column ─────────────────────────────────────────────── */}
        <div className="space-y-5 min-w-0">
          <section>
            <SectionTitle>Overview</SectionTitle>
            <Card className="p-4">
              <Markdown md={protocol.purpose} className="prose-reading" />
              {version.references.length > 0 && (
                <div className="mt-3 pt-3 border-t border-line">
                  <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
                    Rationale and sources
                  </div>
                  <ul className="space-y-1.5">
                    {version.references.map((r, i) => (
                      <li key={i} className="text-body flex flex-wrap items-baseline gap-1.5">
                        {r.recordId && <CitationChip recordId={r.recordId} />}
                        {!r.recordId && r.paperId && <CitationChip paperId={r.paperId} />}
                        <span className="text-ink-soft">{r.note ?? 'Supporting source.'}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          </section>

          <section>
            <SectionTitle>Safety</SectionTitle>
            {version.safety.length === 0 ? (
              <Callout kind="warn" title="No safety notes on this version">
                This version records no hazards. Treat that as an omission, not an all-clear — check
                your local risk assessment before running it.
              </Callout>
            ) : (
              <Callout kind="warn" title={`BSL-${protocol.bsl} · ${version.safety.length} hazard notes`}>
                <ul className="list-disc pl-4 space-y-1">
                  {version.safety.map((s, i) => (
                    <li key={i}>{inlineMarkdown(s, `safety-${i}`)}</li>
                  ))}
                </ul>
              </Callout>
            )}
          </section>

          <section>
            <SectionTitle
              right={
                <span className="text-caption text-ink-soft font-num">
                  {version.steps.length} steps at {batchLabel(version, scale)}
                </span>
              }
            >
              Steps
            </SectionTitle>
            {version.steps.length === 0 ? (
              <Card>
                <EmptyState
                  title="This version has no steps"
                  body="Nothing to run yet. Open the editor to add the procedure."
                  action={<LinkButton to={`/runbook/${protocol.id}/edit`}>Open editor</LinkButton>}
                />
              </Card>
            ) : (
              <div className="space-y-2">
                {version.steps.map((s, i) => (
                  <StepCard
                    key={s.id}
                    step={s}
                    index={i}
                    version={version}
                    scale={scale}
                    records={records}
                  />
                ))}
              </div>
            )}
          </section>
        </div>

        {/* ── right rail ──────────────────────────────────────────────── */}
        <div className="space-y-4">
          {/* Scale */}
          <Card className="p-3">
            <SectionTitle
              right={
                <span className="chip font-num text-caption" title="Multiplier against the base batch">
                  ×{fmt(scale)}
                </span>
              }
            >
              Scale
            </SectionTitle>
            <label className="text-caption text-ink-soft block mb-1" htmlFor="batch-size">
              Batch size
            </label>
            <input
              id="batch-size"
              ref={batchRef}
              className={cx('input font-num', !parse.ok && 'border-signal-error')}
              value={batchText}
              onChange={(e) => setBatch(e.target.value)}
              aria-invalid={!parse.ok}
              aria-describedby="batch-hint"
              inputMode="decimal"
            />
            <div id="batch-hint" className="text-caption mt-1" aria-live="polite">
              {parse.ok ? (
                <span className="text-ink-soft font-num">
                  {batchLabel(version, scale)} — base is {fmt(version.baseBatch.value)}{' '}
                  {version.baseBatch.unit}
                </span>
              ) : (
                <span className="text-signal-error">{parse.error}</span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-1.5 mt-2">
              {[0.5, 1, 5].map((m) => (
                <button
                  key={m}
                  className={cx('chip', scale === m && 'chip-active')}
                  aria-pressed={scale === m}
                  onClick={() => setQuickScale(m)}
                  title={`${fmt(version.baseBatch.value * m)} ${version.baseBatch.unit}`}
                >
                  <span className="font-num">×{m}</span>
                </button>
              ))}
              <button
                className={cx('chip', ![0.5, 1, 5].includes(scale) && 'chip-active')}
                aria-pressed={![0.5, 1, 5].includes(scale)}
                onClick={() => {
                  batchRef.current?.focus();
                  batchRef.current?.select();
                }}
                title="Type any batch size in the field above"
              >
                Custom
              </button>
              {scale !== 1 && (
                <button
                  className="text-caption text-accent hover:underline ml-1"
                  onClick={() => setQuickScale(1)}
                >
                  Reset to base
                </button>
              )}
            </div>

            {extreme && (
              <p className="text-caption text-signal-warn mt-2">
                <span className="font-num">×{fmt(scale)}</span> is far outside what this procedure was
                written for. Quantities still compute, but mixing, heat transfer and vessel geometry
                do not scale linearly — treat the numbers as arithmetic, not advice.
              </p>
            )}
            {!caps.scalable && (
              <p className="text-caption text-ink-soft mt-2">
                Every material in this version is declared <strong>fixed</strong>, so the batch size
                changes the label only — no amount moves.
              </p>
            )}

            <Button variant="primary" className="w-full mt-3 justify-center" onClick={beginRun}>
              <Play size={14} /> Start run at {batchLabel(version, scale)}
            </Button>
            <p className="text-caption text-ink-soft mt-1.5">
              Run Mode records step completions, deviations and timers for this session only.
            </p>
          </Card>

          {/* Materials */}
          <Card className="p-3">
            <SectionTitle
              right={<span className="text-caption text-ink-soft font-num">{scaled.length} items</span>}
            >
              Materials
            </SectionTitle>
            <MaterialsTable materials={scaled} records={records} />
            <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-line">
              <Button size="sm" onClick={copyChecklist} disabled={scaled.length === 0}>
                <Copy size={13} /> Copy as checklist
              </Button>
              <Button size="sm" onClick={exportMaterials} disabled={scaled.length === 0}>
                <Download size={13} /> Export CSV
              </Button>
            </div>
            <p className="text-caption text-ink-soft mt-2 flex items-start gap-1.5">
              <span className="mt-[5px] shrink-0">
                <ProvDot p="demo" size={7} />
              </span>
              <span>
                Amounts round to each material's own precision spec, so a scaled recipe stays
                pipettable. Rows without a source chip are demo values authored for this simulation.
              </span>
            </p>
          </Card>

          {/* Equipment */}
          <Card className="p-3">
            <SectionTitle>Equipment</SectionTitle>
            {version.equipment.length === 0 ? (
              <p className="text-body text-ink-soft">This version declares no equipment.</p>
            ) : (
              <ul className="space-y-1">
                {version.equipment.map((e, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-body">
                    <Wrench size={13} className="mt-[4px] shrink-0 text-ink-soft" aria-hidden />
                    <span>{e}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {/* Runs */}
          <Card className="p-3">
            <SectionTitle
              right={
                <span className="text-caption text-ink-soft font-num">
                  {protocolRuns.length} this session
                </span>
              }
            >
              Runs
            </SectionTitle>
            {protocolRuns.length === 0 ? (
              <p className="text-body text-ink-soft">
                No runs yet. Starting one records completions, skips, deviations and timers — and it
                lives for this session only.
              </p>
            ) : (
              <ul className="space-y-2">
                {protocolRuns.map((r) => {
                  const rv =
                    protocol.versions.find((v) => v.version === r.version) ?? version;
                  const total = rv.steps.length;
                  const done = Object.keys(r.completed).length;
                  const skipped = Object.keys(r.skipped).length;
                  const minutes = r.finishedAt
                    ? Math.max(1, Math.round((r.finishedAt - r.startedAt) / 60000))
                    : null;
                  return (
                    <li key={r.id}>
                      <Tick p="user" className="py-0.5">
                        <a
                          href={href(`/runbook/${protocol.id}/run/${r.id}`)}
                          className="text-body hover:text-accent hover:underline font-num"
                        >
                          {r.id}
                        </a>
                        <div className="text-caption text-ink-soft font-num">
                          v{r.version} · ×{fmt(r.scale)} · started {clockLabel(r.startedAt)}
                        </div>
                        <div className="text-caption text-ink-soft font-num">
                          {done}/{total} steps
                          {skipped > 0 && ` · ${skipped} skipped`}
                          {r.deviations.length > 0 &&
                            ` · ${r.deviations.length} deviation${r.deviations.length === 1 ? '' : 's'}`}
                          {minutes !== null ? ` · finished in ${minutes} min` : ' · in progress'}
                        </div>
                      </Tick>
                    </li>
                  );
                })}
              </ul>
            )}
          </Card>
        </div>
      </div>

      <Sheet
        open={compareOpen}
        onClose={() => setCompareOpen(false)}
        title={`${protocol.title} — version compare`}
        width={760}
      >
        <CompareBody
          protocol={protocol}
          aVersion={cmpA}
          bVersion={cmpB}
          onPick={(which, v) => (which === 'a' ? setCmpA(v) : setCmpB(v))}
        />
      </Sheet>
    </>
  );
}
