// Structured protocol editor (OF-DES-001 §5.3 `/protocols/:id/edit`, fidelity
// item 14). Edits, reorders, and quantity binding are real; a saved draft
// becomes a live new version for the rest of the session.
import { useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  Plus,
  Trash2,
  Save,
  Eye,
  AlertTriangle,
  Timer,
  Link2,
} from 'lucide-react';
import { useStore } from '@/store';
import { navigate } from '@/router';
import type { Material, ProtocolVersion, ScalingClass, Step } from '@/data/types';
import { renderStepText, scaleMaterial, batchLabel } from '@/engine/scale';
import { fmt, normalizeUnit } from '@/engine/units';
import { PageHeader, Card, Button, Callout, SectionTitle, cx, Modal, EmptyState } from '@/components/ui';
import { CitationChip } from '@/components/Chip';

const SCALING_LABEL: Record<ScalingClass, string> = {
  per_batch_volume: 'Scales with batch volume',
  fixed: 'Fixed — does not scale',
  per_unit_biomass: 'Scales with biomass',
};

/** Bump 1.1 → 1.2, or 1.1.1 → 1.1.2 — whatever the seeded scheme uses. */
function bumpVersion(v: string): string {
  const parts = v.split('.');
  const last = parseInt(parts[parts.length - 1] ?? '0', 10);
  parts[parts.length - 1] = String((isNaN(last) ? 0 : last) + 1);
  return parts.join('.');
}

export default function ProtocolEditor({ protocolId }: { protocolId: string }) {
  const protocol = useStore((s) => s.protocols.find((p) => p.id === protocolId));
  const addProtocolVersion = useStore((s) => s.addProtocolVersion);
  const logActivity = useStore((s) => s.logActivity);
  const toast = useStore((s) => s.toast);

  const base = protocol?.versions.find((v) => v.version === protocol.currentVersion);

  const [steps, setSteps] = useState<Step[]>(() => structuredClone(base?.steps ?? []));
  const [materials, setMaterials] = useState<Material[]>(() =>
    structuredClone(base?.materials ?? []),
  );
  const [changelog, setChangelog] = useState('');
  const [preview, setPreview] = useState(false);
  const [previewScale, setPreviewScale] = useState(1);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const draftVersion: ProtocolVersion | null = useMemo(
    () => (base ? { ...base, steps, materials, version: bumpVersion(base.version), changelog } : null),
    [base, steps, materials, changelog],
  );

  // Validation runs live; edge cases are surfaced, never silently swallowed.
  const problems = useMemo(() => {
    const out: { level: 'error' | 'warn'; text: string }[] = [];
    const names = new Set(materials.map((m) => m.name));
    for (const s of steps) {
      for (const match of s.text.matchAll(/\{\{(?:qty|stock):([^}]+)\}\}/g)) {
        if (!names.has(match[1]))
          out.push({
            level: 'error',
            text: `Step ${s.id} binds “${match[1]}”, which is not in the materials list.`,
          });
      }
      for (const match of s.text.matchAll(/\{\{stock:([^}]+)\}\}/g)) {
        const mat = materials.find((m) => m.name === match[1]);
        if (mat && !mat.stock)
          out.push({
            level: 'error',
            text: `Step ${s.id} asks for a stock volume of “${mat.name}”, which has no stock concentration.`,
          });
      }
      if (!s.text.trim()) out.push({ level: 'error', text: `Step ${s.id} has no instruction text.` });
    }
    for (const m of materials) {
      if (!m.name.trim()) out.push({ level: 'error', text: 'A material has no name.' });
      if (normalizeUnit(m.unit) === null)
        out.push({ level: 'warn', text: `Unit “${m.unit}” on ${m.name} is not one the converter knows.` });
      if (m.precision <= 0)
        out.push({ level: 'warn', text: `${m.name} has no rounding precision — scaled amounts may not be pipettable.` });
    }
    const unbound = materials.filter(
      (m) => !steps.some((s) => s.text.includes(`{{qty:${m.name}}}`) || s.text.includes(`{{stock:${m.name}}}`)),
    );
    for (const m of unbound)
      out.push({ level: 'warn', text: `${m.name} is never referenced by a step — it will appear only in the materials table.` });
    return out;
  }, [steps, materials]);

  const blocking = problems.filter((p) => p.level === 'error');

  if (!protocol || !base || !draftVersion) {
    return (
      <EmptyState
        title="Protocol not found"
        body={`No protocol with id ${protocolId} exists in this session.`}
        action={<Button onClick={() => navigate('/runbook')}>Back to protocols</Button>}
      />
    );
  }

  const move = (i: number, delta: number) => {
    const j = i + delta;
    if (j < 0 || j >= steps.length) return;
    const next = [...steps];
    [next[i], next[j]] = [next[j], next[i]];
    setSteps(next);
  };

  const patchStep = (i: number, patch: Partial<Step>) =>
    setSteps((s) => s.map((step, k) => (k === i ? { ...step, ...patch } : step)));

  const patchMaterial = (i: number, patch: Partial<Material>) =>
    setMaterials((m) => m.map((mat, k) => (k === i ? { ...mat, ...patch } : mat)));

  const save = () => {
    addProtocolVersion(protocolId, draftVersion);
    logActivity({
      at: new Date().toISOString().slice(0, 16).replace('T', ' '),
      icon: 'file',
      text: `${protocol.title} — version ${draftVersion.version} published`,
      href: `#/protocols/${protocolId}`,
      provenance: 'user',
    });
    toast({
      text: `Version ${draftVersion.version} published for this session`,
      kind: 'success',
      href: `#/protocols/${protocolId}`,
      hrefLabel: 'Open',
    });
    setConfirmOpen(false);
    navigate(`/protocols/${protocolId}`);
  };

  return (
    <div>
      <PageHeader
        eyebrow={`${protocol.id} · editing from v${base.version}`}
        title={protocol.title}
        subtitle={
          <>
            Edits here create <strong>version {draftVersion.version}</strong>, live for the rest of this
            session. Quantities bind to materials with{' '}
            <code className="font-num text-[12px] bg-surface-0 px-1 rounded">{'{{qty:Name}}'}</code> and{' '}
            <code className="font-num text-[12px] bg-surface-0 px-1 rounded">{'{{stock:Name}}'}</code>,
            which re-render at whatever scale a run uses.
          </>
        }
        actions={
          <>
            <Button onClick={() => setPreview((p) => !p)}>
              <Eye size={14} /> {preview ? 'Hide preview' : 'Preview at scale'}
            </Button>
            <Button onClick={() => navigate(`/protocols/${protocolId}`)}>Cancel</Button>
            <Button variant="primary" disabled={blocking.length > 0} onClick={() => setConfirmOpen(true)}>
              <Save size={14} /> Save as v{draftVersion.version}
            </Button>
          </>
        }
      />

      {problems.length > 0 && (
        <div className="mb-4 space-y-2">
          {blocking.length > 0 && (
            <Callout kind="error" title={`${blocking.length} problem${blocking.length > 1 ? 's' : ''} block saving`}>
              <ul className="list-disc pl-4 space-y-0.5">
                {blocking.map((p, i) => (
                  <li key={i}>{p.text}</li>
                ))}
              </ul>
            </Callout>
          )}
          {problems.filter((p) => p.level === 'warn').length > 0 && (
            <Callout kind="warn" title="Worth a look">
              <ul className="list-disc pl-4 space-y-0.5">
                {problems
                  .filter((p) => p.level === 'warn')
                  .map((p, i) => (
                    <li key={i}>{p.text}</li>
                  ))}
              </ul>
            </Callout>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_400px] gap-5 items-start">
        {/* Steps */}
        <div>
          <SectionTitle
            right={
              <Button
                size="sm"
                onClick={() =>
                  setSteps((s) => [...s, { id: `s${s.length + 1}-new-${s.length}`, text: '' }])
                }
              >
                <Plus size={13} /> Add step
              </Button>
            }
          >
            Steps
          </SectionTitle>

          <div className="space-y-2">
            {steps.map((step, i) => (
              <Card key={step.id} className="p-3">
                <div className="flex items-start gap-3">
                  <div className="font-num text-ink-soft text-caption pt-2 w-6 shrink-0 text-right">
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0 space-y-2">
                    <textarea
                      className="input font-sans resize-y min-h-[64px]"
                      value={step.text}
                      onChange={(e) => patchStep(i, { text: e.target.value })}
                      aria-label={`Step ${i + 1} instruction`}
                    />

                    <div className="flex flex-wrap items-center gap-2">
                      <label className="flex items-center gap-1.5 text-caption text-ink-soft">
                        <Timer size={12} />
                        Timer (s)
                        <input
                          type="number"
                          className="input w-[84px] font-num"
                          value={step.timerSec ?? ''}
                          placeholder="—"
                          onChange={(e) =>
                            patchStep(i, {
                              timerSec: e.target.value === '' ? undefined : Number(e.target.value),
                            })
                          }
                        />
                      </label>
                      {step.timerSec !== undefined && (
                        <input
                          className="input w-[200px]"
                          placeholder="Timer label"
                          value={step.timerLabel ?? ''}
                          onChange={(e) => patchStep(i, { timerLabel: e.target.value })}
                          aria-label={`Step ${i + 1} timer label`}
                        />
                      )}
                      {(step.refs ?? []).map((r) => (
                        <CitationChip key={r} paperId={r.startsWith('r-') ? undefined : r} recordId={r.startsWith('r-') ? r : undefined} />
                      ))}
                    </div>

                    <details className="text-caption">
                      <summary className="cursor-pointer text-ink-soft hover:text-ink">
                        Rationale note {step.note ? '' : '(none)'}
                      </summary>
                      <textarea
                        className="input mt-1.5 font-sans resize-y"
                        value={step.note ?? ''}
                        placeholder="Why this step is done this way — shown to the reader on request."
                        onChange={(e) => patchStep(i, { note: e.target.value || undefined })}
                        aria-label={`Step ${i + 1} rationale`}
                      />
                    </details>

                    {preview && (
                      <div className="rounded-input border border-line bg-surface-0 p-2">
                        <div className="text-caption text-ink-soft mb-0.5">
                          Rendered at {batchLabel(draftVersion, previewScale)}
                        </div>
                        <div className="text-body">{renderStepText(step, draftVersion, previewScale)}</div>
                      </div>
                    )}
                  </div>

                  <div className="flex flex-col gap-1 shrink-0">
                    <button
                      className="btn btn-sm"
                      onClick={() => move(i, -1)}
                      disabled={i === 0}
                      aria-label={`Move step ${i + 1} up`}
                    >
                      <ArrowUp size={12} />
                    </button>
                    <button
                      className="btn btn-sm"
                      onClick={() => move(i, 1)}
                      disabled={i === steps.length - 1}
                      aria-label={`Move step ${i + 1} down`}
                    >
                      <ArrowDown size={12} />
                    </button>
                    <button
                      className="btn btn-sm text-signal-error"
                      onClick={() => setSteps((s) => s.filter((_, k) => k !== i))}
                      aria-label={`Delete step ${i + 1}`}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Materials + changelog */}
        <div className="space-y-4">
          {preview && (
            <Card className="p-3">
              <div className="text-caption uppercase tracking-wide text-ink-soft mb-2">Preview scale</div>
              <div className="flex items-center gap-1.5">
                {[0.5, 1, 2, 5].map((s) => (
                  <button
                    key={s}
                    className={cx('chip', previewScale === s && 'chip-active')}
                    onClick={() => setPreviewScale(s)}
                  >
                    ×{s}
                  </button>
                ))}
              </div>
              <div className="text-caption text-ink-soft mt-2 font-num">
                {batchLabel(draftVersion, previewScale)}
              </div>
            </Card>
          )}

          <div>
            <SectionTitle
              right={
                <Button
                  size="sm"
                  onClick={() =>
                    setMaterials((m) => [
                      ...m,
                      { name: '', amount: 0, unit: 'g', scaling: 'per_batch_volume', precision: 0.1 },
                    ])
                  }
                >
                  <Plus size={13} /> Add
                </Button>
              }
            >
              Materials
            </SectionTitle>

            <div className="space-y-2">
              {materials.map((m, i) => {
                const scaled = scaleMaterial(m, preview ? previewScale : 1);
                const bound = steps.some(
                  (s) => s.text.includes(`{{qty:${m.name}}}`) || s.text.includes(`{{stock:${m.name}}}`),
                );
                return (
                  <Card key={i} className="p-2.5">
                    <div className="flex items-start gap-2">
                      <div className="flex-1 min-w-0 space-y-1.5">
                        <div className="flex items-center gap-1.5">
                          <input
                            className="input flex-1"
                            value={m.name}
                            placeholder="Material name"
                            onChange={(e) => patchMaterial(i, { name: e.target.value })}
                            aria-label={`Material ${i + 1} name`}
                          />
                          {bound && (
                            <span title="Referenced by a step" className="text-accent shrink-0">
                              <Link2 size={13} />
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1.5">
                          <input
                            type="number"
                            className="input w-[90px] font-num"
                            value={m.amount}
                            step="any"
                            onChange={(e) => patchMaterial(i, { amount: Number(e.target.value) })}
                            aria-label={`Material ${i + 1} amount`}
                          />
                          <input
                            className="input w-[80px] font-num"
                            value={m.unit}
                            onChange={(e) => patchMaterial(i, { unit: e.target.value })}
                            aria-label={`Material ${i + 1} unit`}
                          />
                          <input
                            type="number"
                            className="input w-[80px] font-num"
                            value={m.precision}
                            step="any"
                            title="Rounding increment"
                            onChange={(e) => patchMaterial(i, { precision: Number(e.target.value) })}
                            aria-label={`Material ${i + 1} rounding precision`}
                          />
                        </div>
                        <select
                          className="input"
                          value={m.scaling}
                          onChange={(e) => patchMaterial(i, { scaling: e.target.value as ScalingClass })}
                          aria-label={`Material ${i + 1} scaling class`}
                        >
                          {(Object.keys(SCALING_LABEL) as ScalingClass[]).map((k) => (
                            <option key={k} value={k}>
                              {SCALING_LABEL[k]}
                            </option>
                          ))}
                        </select>
                        {preview && (
                          <div className="text-caption font-num text-ink-soft">
                            → {fmt(scaled.scaledAmount)} {m.unit}
                            {scaled.stockVolume &&
                              ` · ${fmt(scaled.stockVolume.value)} ${scaled.stockVolume.unit} of stock`}
                          </div>
                        )}
                        {m.sourceRecordId && <CitationChip recordId={m.sourceRecordId} />}
                      </div>
                      <button
                        className="btn btn-sm text-signal-error shrink-0"
                        onClick={() => setMaterials((x) => x.filter((_, k) => k !== i))}
                        aria-label={`Delete material ${i + 1}`}
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>

          <Card className="p-3">
            <label className="text-caption uppercase tracking-wide text-ink-soft block mb-1.5">
              Changelog for v{draftVersion.version}
            </label>
            <textarea
              className="input font-sans resize-y min-h-[70px]"
              value={changelog}
              placeholder="What changed and why — this line appears in the version diff."
              onChange={(e) => setChangelog(e.target.value)}
            />
          </Card>
        </div>
      </div>

      <Modal open={confirmOpen} onClose={() => setConfirmOpen(false)} title={`Publish v${draftVersion.version}?`}>
        <p className="text-body mb-3">
          This creates version <span className="font-num">{draftVersion.version}</span> of{' '}
          {protocol.title} with {steps.length} steps and {materials.length} materials, and makes it the
          current version. It lives for this session only — session state resets on refresh.
        </p>
        {!changelog.trim() && (
          <Callout kind="warn">
            No changelog yet. The version diff will show what changed, but not why.
          </Callout>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <Button onClick={() => setConfirmOpen(false)}>Back to editing</Button>
          <Button variant="primary" onClick={save}>
            <Save size={14} /> Publish
          </Button>
        </div>
      </Modal>
    </div>
  );
}
