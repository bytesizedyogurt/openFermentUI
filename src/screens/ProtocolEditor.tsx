// Structured protocol editor (OF-DES-001 §5.3 `/runbooks/protocols/:id/edit`, fidelity
// item 14). Edits, reorders, and quantity binding are real; a saved draft
// becomes the protocol's new current version, kept by the service in the
// reviewer's name (ADR-017), every version before it standing as it was kept.
// A step names the skills a person needs to do it, picked from the project's
// skill catalogue, which the service holds every keep to. The form opens on
// the protocol's current version once the service has answered with it, so an
// editor opened by its address starts from the steps and materials kept.
import { useMemo, useState } from 'react';
import {
  ArrowDown,
  ArrowUp,
  Plus,
  Trash2,
  Save,
  Eye,
  Timer,
  Link2,
} from 'lucide-react';
import { useProtocol, useSkills, useStore } from '@/store';
import { href, navigate } from '@/router';
import type { Material, Protocol, ProtocolVersion, ScalingClass, Step } from '@/lib/protocols';
import { renderStepText, scaleMaterial, batchLabel } from '@/engine/scale';
import { fmt, normalizeUnit } from '@/engine/units';
import { PageHeader, Card, Button, Callout, SectionTitle, cx, Modal, EmptyState } from '@/components/ui';
import { CitationChip } from '@/components/Chip';

const SCALING_LABEL: Record<ScalingClass, string> = {
  per_batch_volume: 'Scales with batch volume',
  fixed: 'Fixed — does not scale',
  per_unit_biomass: 'Scales with biomass',
};

/** Bump 1.1 → 1.2, or 1.1.1 → 1.1.2 — whatever scheme the protocol's versions use. */
function bumpVersion(v: string): string {
  const parts = v.split('.');
  const last = parseInt(parts[parts.length - 1] ?? '0', 10);
  parts[parts.length - 1] = String((isNaN(last) ? 0 : last) + 1);
  return parts.join('.');
}

export default function ProtocolEditor({ protocolId }: { protocolId: string }) {
  const { protocol, state, problem } = useProtocol(protocolId);
  const base = protocol?.versions.find((v) => v.version === protocol.currentVersion);
  if (!protocol || !base) {
    const title =
      state === 'problem' ? 'The protocols could not be read' : state === 'reading' ? 'Reading the project\u2019s protocols' : 'Protocol not found';
    const body =
      state === 'problem'
        ? (problem ?? '')
        : state === 'reading'
          ? 'The protocols are read from the service as the page opens.'
          : protocol
            ? `Protocol ${protocolId} names ${protocol.currentVersion} as its current version and holds no version of that name.`
            : `The project keeps no protocol ${protocolId}.`;
    return (
      <EmptyState title={title} body={body} action={<Button onClick={() => navigate('/runbooks/protocols')}>Back to protocols</Button>} />
    );
  }
  // A version kept while the form is open makes a new current version: the form starts again from it.
  return <VersionEditor key={`${protocol.id}@${protocol.currentVersion}`} protocol={protocol} base={base} />;
}

/** The form over one protocol's current version, its state begun from that version's steps and materials. */
function VersionEditor({ protocol, base }: { protocol: Protocol; base: ProtocolVersion }) {
  const protocolId = protocol.id;
  const keepProtocolVersion = useStore((s) => s.keepProtocolVersion);
  const logActivity = useStore((s) => s.logActivity);
  const toast = useStore((s) => s.toast);
  const reviewer = useStore((s) => s.reviewer.trim());
  const skills = useSkills();
  // Until the skill catalogue is read, no step's skill is called one it does not hold.
  const skillsRead = useStore((s) => s.cataloguesRead);
  const [saving, setSaving] = useState(false);
  const [refusal, setRefusal] = useState<string | null>(null);

  const [steps, setSteps] = useState<Step[]>(() => structuredClone(base.steps ?? []));
  const [materials, setMaterials] = useState<Material[]>(() => structuredClone(base.materials ?? []));
  const [changelog, setChangelog] = useState('');
  const [preview, setPreview] = useState(false);
  const [previewScale, setPreviewScale] = useState(1);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const draftVersion: ProtocolVersion = useMemo(
    () => ({ ...base, steps, materials, version: bumpVersion(base.version), changelog }),
    [base, steps, materials, changelog],
  );

  // Validation runs live; edge cases are surfaced, never silently swallowed.
  const problems = useMemo(() => {
    const out: { level: 'error' | 'warn'; text: string }[] = [];
    const names = new Set(materials.map((m) => m.name));
    const known = new Set(skills.map((k) => k.id));
    if (steps.length === 0)
      out.push({
        level: 'error',
        text:
          (base.steps ?? []).length > 0
            ? `This version holds no step, and version ${base.version} holds ${(base.steps ?? []).length}: a version a run follows holds its steps.`
            : 'This version holds no step yet: a version a run follows holds its steps.',
      });
    for (const s of steps) {
      for (const k of s.skills ?? [])
        if (skillsRead && !known.has(k))
          out.push({
            level: 'error',
            text: `Step ${s.id} needs ${k}, which the project's skill catalogue does not hold; the service keeps no step naming it.`,
          });
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
  }, [steps, materials, skills, skillsRead, base]);

  const blocking = problems.filter((p) => p.level === 'error');

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

  const save = async () => {
    setSaving(true);
    const why = await keepProtocolVersion(protocolId, draftVersion);
    setSaving(false);
    if (why) {
      setRefusal(why);
      return;
    }
    setRefusal(null);
    logActivity({
      at: new Date().toISOString().slice(0, 16).replace('T', ' '),
      icon: 'file',
      text: `${protocol.title} — version ${draftVersion.version} kept in ${reviewer}\u2019s name`,
      href: `#/runbooks/protocols/${protocolId}`,
      provenance: 'user',
    });
    toast({
      text: `Version ${draftVersion.version} kept; it is the protocol\u2019s current version`,
      kind: 'success',
      href: `#/runbooks/protocols/${protocolId}`,
      hrefLabel: 'Open',
    });
    setConfirmOpen(false);
    navigate(`/runbooks/protocols/${protocolId}`);
  };

  const toggleSkill = (i: number, skillId: string) =>
    setSteps((s) =>
      s.map((step, k) => {
        if (k !== i) return step;
        const held = step.skills ?? [];
        return { ...step, skills: held.includes(skillId) ? held.filter((x) => x !== skillId) : [...held, skillId] };
      }),
    );

  return (
    <div>
      <PageHeader
        eyebrow={<><span className="normal-case font-num">{protocol.id}</span> · editing from v{base.version}</>}
        title={protocol.title}
        subtitle={
          <>
            Edits here make <strong>version {draftVersion.version}</strong>, kept by the service in your name and
            made the protocol&rsquo;s current version; every version before it stands as it was kept. Quantities
            bind to materials with{' '}
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
            <Button onClick={() => navigate(`/runbooks/protocols/${protocolId}`)}>Cancel</Button>
            <Button variant="primary" disabled={blocking.length > 0 || !reviewer} onClick={() => setConfirmOpen(true)}>
              <Save size={14} /> Save as v{draftVersion.version}
            </Button>
          </>
        }
      />

      {!reviewer && (
        <div className="mb-4">
          <Callout kind="warn" title="A version is kept in a person's name">
            Set your reviewer name in{' '}
            <a className="text-accent hover:underline" href={href('/settings/corpus')}>
              Settings
            </a>{' '}
            before saving; the service keeps each version with who kept it.
          </Callout>
        </div>
      )}

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
                              timerSec: e.target.value === '' ? null : Number(e.target.value),
                            })
                          }
                        />
                      </label>
                      {step.timerSec != null && (
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

                    <div className="text-caption" role="group" aria-label={`Step ${i + 1} skills`}>
                      <span className="text-ink-soft mr-1.5">Skills it needs</span>
                      {skills.length === 0 ? (
                        <span className="text-ink-soft">
                          the project&rsquo;s skill catalogue holds none yet;{' '}
                          <a className="text-accent hover:underline" href={href('/catalogues/skills')}>
                            add one
                          </a>
                        </span>
                      ) : (
                        <span className="inline-flex flex-wrap gap-1 align-middle">
                          {skills.map((k) => {
                            const on = (step.skills ?? []).includes(k.id);
                            return (
                              <button
                                key={k.id}
                                type="button"
                                className={cx('chip', on && 'chip-active')}
                                aria-pressed={on}
                                onClick={() => toggleSkill(i, k.id)}
                                title={k.summary ?? undefined}
                              >
                                {k.name}
                              </button>
                            );
                          })}
                        </span>
                      )}
                      {(step.skills ?? [])
                        .filter((id) => !skills.some((k) => k.id === id))
                        .map((id) => (
                          <button
                            key={id}
                            type="button"
                            className="chip chip-active text-signal-error border-signal-error/40 ml-1"
                            aria-pressed
                            onClick={() => toggleSkill(i, id)}
                            title="Not in the project's skill catalogue: press to take it off this step"
                          >
                            {id}
                          </button>
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
                        onChange={(e) => patchStep(i, { note: e.target.value || null })}
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
          This keeps version <span className="font-num">{draftVersion.version}</span> of {protocol.title} with{' '}
          {steps.length} step{steps.length === 1 ? '' : 's'} and {materials.length} material{materials.length === 1 ? '' : 's'} in{' '}
          {reviewer ? <>{reviewer}&rsquo;s</> : 'your'} name, and
          makes it the current version. Every version before it stays as it was kept.
        </p>
        {!changelog.trim() && (
          <Callout kind="warn">
            No changelog yet. The version diff will show what changed, but not why.
          </Callout>
        )}
        {refusal && (
          <div className="mt-3" role="alert">
            <Callout kind="error" title="The service kept nothing">
              {refusal}
            </Callout>
          </div>
        )}
        <div className="flex justify-end gap-2 mt-4">
          <Button onClick={() => setConfirmOpen(false)}>Back to editing</Button>
          <Button variant="primary" disabled={saving || !reviewer} onClick={() => void save()}>
            <Save size={14} /> {saving ? 'Keeping…' : 'Keep this version'}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
