// fermOS — Archetype 1 (the factor map) and Archetype 6 (run adjudication),
// plus the envelope match the capacity screen reads from.
//
// These two are built as a pair, and the pair is the demonstration: Archetype 6
// produces the excursion Accession, Archetype 1 consumes it as an EXCLUSION.
// Following the greyed row backwards from the gap map to the run and scrubbing
// to the Tick where the deviation starts is the whole argument for a shared
// object pool, so both directions of that link are rendered rather than
// described.
import { useMemo } from 'react';
import { ArrowUpRight } from 'lucide-react';

import { ACCESSION_BY_ID } from '@/data/demo/accessions';
import { PLANTS, PLANT_BY_ID, ORGANISM_BY_ID, FIELD_BY_ID } from '@/data/demo/core';
import {
  DELIVERABLES,
  DELIVERABLE_BY_ID,
  LYSINE_FACTOR_MAP,
  LYSINE_RUN_DESIGN,
  CANDIDATES,
} from '@/data/demo/archetypes';
import { RUNS, RUN_BY_ID, excursionIntegrals, hydrateExcursions } from '@/data/demo/runs';
import { plantCeilings, matchEnvelope } from '@/lib/demo';
import { href, navigate } from '@/router';
import { PageHeader, Card, SectionTitle, EmptyState, Callout, cx } from '@/components/ui';
import { AccessionValue } from '@/components/demo/AccessionValue';
import { FactorBand } from '@/components/demo/FactorBand';
import { EnvelopeMatch } from '@/components/demo/EnvelopeMatch';
import { TickScrubber } from '@/components/demo/TickScrubber';
import { DisclosureCard } from '@/components/demo/DisclosureCard';
import { DemoTickLegend, HOLD_LABEL, demoTickClass, demoTickTitle } from '@/components/demo/DemoTick';
import { DemoFooter } from '@/components/demo/DemoFooter';
import { DISCLOSURES } from '@/data/demo/archetypes';

import { partEyebrow } from '@/data/parts';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('fermos', 'demo');
// The run channels carry authored excursion windows; the integrals over them
// are computed. Hydrating once at module scope keeps every screen reading the
// same numbers rather than each recomputing its own.
hydrateExcursions();

// ── /fermos/gap/:id — ARCHETYPE 1 ──────────────────────────────────────

export function GapMap({ deliverableId }: { deliverableId: string }) {
  const dlv = DELIVERABLE_BY_ID[deliverableId] ?? DELIVERABLES.find((d) => d.payload.kind === 'factor-map');

  const excluded = useMemo(() => {
    if (!dlv || dlv.payload.kind !== 'factor-map') return [];
    return dlv.payload.excludedAccessionIds.map((id) => ACCESSION_BY_ID[id]).filter(Boolean);
  }, [dlv]);

  if (!dlv || dlv.payload.kind !== 'factor-map') {
    return <EmptyState title="No factor map" body={`No deliverable ${deliverableId} of that kind.`} />;
  }

  const factors = dlv.payload.factors.length ? dlv.payload.factors : LYSINE_FACTOR_MAP;
  const design = dlv.payload.design.length ? dlv.payload.design : LYSINE_RUN_DESIGN;
  const disclosures = DISCLOSURES.filter((d) => dlv.disclosureCandidateIds.includes(d.id));

  return (
    <div className="p-6 max-w-[1200px]">
      <PageHeader eyebrow={EYEBROW} title={dlv.title} subtitle={dlv.query} />

      <Callout>
        The bands below say three different things and only one of them is a result. The washed
        band is what the record supports; the hatching is what it rules out; the bare grid is
        where nobody has been. The third is the finding — a design that only visits the first is a
        design that learns nothing.
      </Callout>

      <div className="mt-4">
        <DemoTickLegend types={['journal', 'patent-example', 'bench-deposit', 'computed']} />
      </div>

      <div className="grid md:grid-cols-2 gap-6 mt-4">
        {factors.map((f) => (
          <Card key={f.field}>
            <FactorBand
              factor={f}
              onSelect={() => navigate(`/fermos/gap/${dlv.id}/f/${f.field}`)}
              marks={markForFactor(f.field)}
            />
          </Card>
        ))}
      </div>

      {/* The seam, rendered. */}
      {excluded.length > 0 && (
        <Card className="mt-6">
          <SectionTitle>Held out of the map</SectionTitle>
          <div className="text-caption text-ink-soft mb-2">
            These Accessions exist, are on record, and do not move any recommendation. Each names
            the reason and the run behind it — a value excluded without a reason is just a value
            somebody disliked.
          </div>
          <div className="space-y-2">
            {excluded.map((a) => (
              <div key={a.id} className="flex flex-wrap items-baseline gap-2 opacity-70">
                <a
                  href={href(`/repo/a/${a.id}`)}
                  className={cx(demoTickClass(a.provenance, a.sourceType), 'pl-2 font-num hover:text-accent')}
                  title={demoTickTitle(a.provenance, a.sourceType, a.hold)}
                >
                  {a.id}
                </a>
                <span className="text-caption">{FIELD_BY_ID[a.field]?.name ?? a.field}</span>
                <span className="font-num text-caption">
                  {a.normalized.value} {a.normalized.unit}
                </span>
                {a.hold && <span className="text-caption text-signal-warn">{HOLD_LABEL[a.hold]}</span>}
                {a.runId && (
                  <a
                    href={href(`/fermos/runs/${a.runId}`)}
                    className="text-caption text-accent hover:underline inline-flex items-center gap-1"
                  >
                    {a.runId}
                    <ArrowUpRight className="w-3 h-3" />
                  </a>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card className="mt-6">
        <SectionTitle>Run design · {design.length} runs</SectionTitle>
        <div className="text-caption text-ink-soft mb-2">
          Every run lands in a cell nothing currently speaks to. A design that reproduced the
          explored region would be a design that confirms what is already on record.
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-body">
            <thead className="text-caption text-ink-soft text-left">
              <tr className="border-b border-line">
                <th className="font-normal p-2">#</th>
                <th className="font-normal p-2">Setpoints</th>
                <th className="font-normal p-2">Cell</th>
                <th className="font-normal p-2">Rationale</th>
              </tr>
            </thead>
            <tbody>
              {design.map((r) => (
                <tr key={r.run} className="border-b border-line/50">
                  <td className="p-2 font-num align-top">{r.run}</td>
                  <td className="p-2 font-num align-top whitespace-nowrap text-caption">
                    {Object.entries(r.setpoints)
                      .map(([k, v]) => `${k} ${v}`)
                      .join(' · ')}
                  </td>
                  <td className="p-2 font-num align-top text-caption">{r.cell}</td>
                  <td className="p-2 align-top text-caption text-ink-soft">{r.rationale}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <DisclosureSection disclosures={disclosures} />
      <DemoFooter />
    </div>
  );
}

/**
 * The de-rated design point from Archetype 3, marked inside Archetype 1's band.
 *
 * Seam-matrix row 3. It is computed here rather than authored on the factor so
 * the mark cannot drift from the Accession it represents.
 */
function markForFactor(field: string): { at: number; label: string }[] {
  if (field === 'mu_setpoint') {
    const a = ACCESSION_BY_ID['OF-A-00124'];
    return a ? [{ at: a.normalized.value, label: `${a.id} — the μ the capacity screen was rescued by` }] : [];
  }
  if (field === 'biomass_density') {
    const a = ACCESSION_BY_ID['OF-A-00153'];
    return a ? [{ at: a.normalized.value, label: `${a.id} — the de-rated design point` }] : [];
  }
  return [];
}

// ── /fermos/gap/:id/f/:factor — one factor ─────────────────────────────

export function FactorDetail({ deliverableId, factorId }: { deliverableId: string; factorId: string }) {
  const dlv = DELIVERABLE_BY_ID[deliverableId];
  const factor =
    (dlv && dlv.payload.kind === 'factor-map' ? dlv.payload.factors : LYSINE_FACTOR_MAP).find(
      (f) => f.field === factorId,
    ) ?? LYSINE_FACTOR_MAP.find((f) => f.field === factorId);

  if (!factor) return <EmptyState title="No such factor" body={`${factorId} is not in this map.`} />;

  const supporting = factor.explored.flatMap((e) => e.accessionIds);

  return (
    <div className="p-6 max-w-[900px]">
      <PageHeader eyebrow={EYEBROW}
        title={FIELD_BY_ID[factor.field]?.name ?? factor.field}
        subtitle={
          <a href={href(`/fermos/gap/${deliverableId}`)} className="hover:text-accent">
            ← back to the factor map
          </a>
        }
      />
      <Card>
        <FactorBand factor={factor} marks={markForFactor(factor.field)} />
      </Card>

      <Card className="mt-4">
        <SectionTitle>Supporting Accessions · {supporting.length}</SectionTitle>
        <div className="space-y-1 mt-2">
          {supporting.map((id) => (
            <div key={id} className="text-caption">
              <a href={href(`/repo/a/${id}`)} className="font-num hover:text-accent mr-2">
                {id}
              </a>
              <AccessionValue id={id} />
            </div>
          ))}
          {!supporting.length && (
            <div className="text-caption text-ink-soft">
              Nothing in the pool has been measured on this factor. Every recommendation on it
              rests on an exclusion rather than on a positive result.
            </div>
          )}
        </div>
      </Card>
      <DemoFooter />
    </div>
  );
}

// ── /fermos/runs — the index ───────────────────────────────────────────

export function RunIndex() {
  return (
    <div className="p-6 max-w-[1100px]">
      <PageHeader eyebrow={EYEBROW} title="Runs" subtitle={`${RUNS.length} runs across the Ledger.`} />
      <Card className="p-0 overflow-x-auto">
        <table className="w-full text-body">
          <thead className="text-caption text-ink-soft text-left">
            <tr className="border-b border-line">
              <th className="font-normal p-2">Run</th>
              <th className="font-normal p-2">Organism</th>
              <th className="font-normal p-2">Product</th>
              <th className="font-normal p-2">Started</th>
              <th className="font-normal p-2">Excursions</th>
              <th className="font-normal p-2">Deposited</th>
            </tr>
          </thead>
          <tbody>
            {RUNS.map((r) => (
              <tr
                key={r.id}
                className="border-b border-line/50 hover:bg-[rgb(var(--accent-wash))]/30 cursor-pointer"
                onClick={() => navigate(`/fermos/runs/${r.id}`)}
              >
                <td className="p-2 font-num">{r.id}</td>
                <td className="p-2 italic text-caption">{ORGANISM_BY_ID[r.organismId]?.binomial ?? r.organismId}</td>
                <td className="p-2 text-caption">{r.productId}</td>
                <td className="p-2 font-num text-caption text-ink-soft">{r.startedAt}</td>
                <td className="p-2 text-caption">
                  {r.excursions.length ? (
                    <span className="text-signal-warn">{r.excursions.length}</span>
                  ) : (
                    <span className="text-ink-soft">—</span>
                  )}
                </td>
                <td className="p-2 font-num text-caption text-ink-soft">
                  {r.depositedAccessionIds.length}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      {/* The envelope page was dispatched and linked from nowhere. It belongs
          here: a run's achievable OUR is bounded by the vessel it ran in, so
          the ceiling is the thing to read before deciding a run underperformed
          rather than the plant. */}
      <div className="text-caption text-ink-soft mt-3">
        Every run above happened in{' '}
        <a href={href(`/fermos/envelope/${PLANTS[0].id}`)} className="text-accent hover:underline">
          {PLANTS[0].name}
        </a>
        , whose oxygen-transfer and cooling ceilings are computed from the vessel and the
        utilities. A run that misses its target inside those ceilings is a process problem; one
        that misses them at the ceiling is an asset problem, and they are not the same finding.
      </div>

      <DemoFooter />
    </div>
  );
}

// ── /fermos/runs/:runId — ARCHETYPE 6 ──────────────────────────────────

export function RunPage({ runId }: { runId: string }) {
  const run = RUN_BY_ID[runId];
  const priors = useMemo(
    () => (run ? run.comparisonBasis.map((id) => RUN_BY_ID[id]).filter(Boolean) : []),
    [run],
  );
  const integrals = useMemo(
    () => (run ? excursionIntegrals(run.id, run.comparisonBasis) : null),
    [run],
  );

  if (!run) return <EmptyState title={`No run ${runId}`} body="This Ledger holds no run under that id." />;

  const dlv = DELIVERABLES.find(
    (d) => d.payload.kind === 'excursion-verdict' && d.payload.runId === run.id,
  );
  const verdict = run.verdict ?? (dlv && dlv.payload.kind === 'excursion-verdict' ? dlv.payload.verdict : undefined);
  const disclosures = dlv ? DISCLOSURES.filter((d) => dlv.disclosureCandidateIds.includes(d.id)) : [];

  return (
    <div className="p-6 max-w-[1400px]">
      <PageHeader eyebrow={EYEBROW}
        title={run.id}
        subtitle={`${ORGANISM_BY_ID[run.organismId]?.binomial ?? run.organismId} · ${run.productId} · started ${run.startedAt}`}
      />

      <Card>
        <TickScrubber run={run} priorRuns={priors} />
      </Card>

      {run.excursions.map((e) => (
        <Card key={e.id} className="mt-4">
          <SectionTitle>
            Excursion {e.id} · Ticks {e.startTick}–{e.endTick}
          </SectionTitle>
          <div className="text-caption text-ink-soft mt-1">{e.description}</div>
          {e.integrals && (
            <dl className="mt-3 grid sm:grid-cols-3 gap-3 text-caption">
              <Metric k="Integrated O₂ deficit" v={`${e.integrals.o2DeficitMmolPerL} mmol L⁻¹`} />
              <Metric k="CER deviation" v={`${e.integrals.cerDeviationMmolPerL} mmol L⁻¹`} />
              <Metric
                k="Carbon diverted (est.)"
                v={`${e.integrals.estimatedCarbonDivertedCmolPerL} C-mol L⁻¹`}
              />
            </dl>
          )}
          <div className="text-caption text-ink-soft mt-2">
            Integrated by trapezoid against the median of {run.comparisonBasis.length} basis runs,
            not against a setpoint. A setpoint says what was asked for; the basis says what this
            equipment actually does, and only the second makes a deviation a deviation.
          </div>
        </Card>
      ))}

      {verdict && (
        <Card className="mt-4">
          <SectionTitle>Verdict</SectionTitle>
          <div className="mt-1 flex flex-wrap items-baseline gap-3">
            <span
              className={cx(
                'text-body font-medium',
                verdict.recommendation === 'terminate'
                  ? 'text-signal-error'
                  : verdict.recommendation === 'continue-flagged'
                    ? 'text-signal-warn'
                    : 'text-signal-open',
              )}
            >
              {verdict.recommendation}
            </span>
            <span className="text-caption text-ink-soft">
              {verdict.comparable
                ? 'comparable to the basis'
                : 'NOT comparable to the basis — this run may not be pooled with it'}
            </span>
          </div>
          <ul className="mt-2 space-y-1">
            {verdict.reasoning.map((r, i) => (
              <li key={i} className="text-caption pl-3 relative">
                <span className="absolute left-0 text-ink-soft">·</span>
                {r}
              </li>
            ))}
          </ul>

          <div className="mt-3 border-t border-line pt-2">
            <div className="text-caption text-ink-soft">
              What this verdict does downstream — the annotation that propagates:
            </div>
            <div className="text-caption mt-1">
              {verdict.annotation.accessionIds.map((id) => (
                <a key={id} href={href(`/repo/a/${id}`)} className="font-num hover:text-accent mr-2">
                  {id}
                </a>
              ))}
              <span className="text-signal-warn">held: {HOLD_LABEL[verdict.annotation.hold]}</span>
            </div>
            <div className="text-caption text-ink-soft mt-1">{verdict.annotation.note}</div>
            <div className="text-caption mt-2">
              The same Accession renders greyed on{' '}
              <a href={href('/fermos/gap/DLV-AR1-001')} className="text-accent hover:underline">
                the factor map
              </a>
              , with this run as its reason. One object, two screens, one story.
            </div>
          </div>
        </Card>
      )}

      {run.commonSeal && (
        <Card className="mt-4">
          <SectionTitle>Common Seal</SectionTitle>
          <div className="text-caption mt-1">
            <span className="font-num">{run.commonSeal.id}</span> · {run.commonSeal.operator} ·{' '}
            {run.commonSeal.chapterId} · sealed {run.commonSeal.sealedAt}
          </div>
          <div className="text-caption text-ink-soft mt-1">
            A seal binds executed work to a person, an institution and a date. It attests that this
            run happened as recorded — never that its numbers are right.
          </div>
        </Card>
      )}

      <DisclosureSection disclosures={disclosures} />
      <DemoFooter />
    </div>
  );
}

function Metric({ k, v }: { k: string; v: string }) {
  return (
    <div>
      <dt className="text-ink-soft">{k}</dt>
      <dd className="font-num tick-cell tick-user tick-ev-computed pl-2" title="Computed by trapezoid, not measured">
        {v}
      </dd>
    </div>
  );
}

// ── /fermos/envelope/:plantId ──────────────────────────────────────────

export function EnvelopePage({ plantId }: { plantId: string }) {
  const plant = PLANT_BY_ID[plantId] ?? PLANTS[0];
  const ceilings = useMemo(() => plantCeilings(plant), [plant]);
  const pressed = useMemo(() => plantCeilings(plant, { pressureBara: 1.5 }), [plant]);

  return (
    <div className="p-6 max-w-[1100px]">
      <PageHeader eyebrow={EYEBROW} title={plant.name} subtitle={`${plant.location.city}, ${plant.location.country} · ambient ${plant.location.ambientC} °C`} />

      <Card>
        <SectionTitle>The two ceilings</SectionTitle>
        <div className="text-caption text-ink-soft mb-3 max-w-prose">
          Both are computed from the vessel and the utilities, not asserted. Change the installed
          power per volume in the seed and kLa moves; the ceilings move with it.
        </div>
        <div className="grid sm:grid-cols-2 gap-6">
          <div>
            <div className="text-caption text-ink-soft">At 1 atm</div>
            <dl className="text-caption space-y-1 mt-1">
              <Metric k="Superficial gas velocity" v={`${ceilings.superficialGasVelocity} m s⁻¹`} />
              <Metric k="kLa, clean water" v={`${ceilings.klaClean} h⁻¹`} />
              <Metric k="kLa, effective" v={`${ceilings.klaEffective} h⁻¹`} />
              <Metric k="C*" v={`${ceilings.cStar} mmol L⁻¹`} />
              <Metric k="OTR ceiling" v={`${ceilings.otrCeiling} mmol L⁻¹ h⁻¹`} />
              <Metric k="Cooling ceiling" v={`${ceilings.coolingCeiling} mmol L⁻¹ h⁻¹`} />
            </dl>
          </div>
          <div>
            <div className="text-caption text-ink-soft">At 1.5 bara</div>
            <dl className="text-caption space-y-1 mt-1">
              <Metric k="C*" v={`${pressed.cStar} mmol L⁻¹`} />
              <Metric k="OTR ceiling" v={`${pressed.otrCeiling} mmol L⁻¹ h⁻¹`} />
              <Metric k="Cooling ceiling" v={`${pressed.coolingCeiling} mmol L⁻¹ h⁻¹`} />
            </dl>
            <div className="text-caption text-ink-soft mt-3 max-w-prose">
              At one atmosphere transfer fails {(ceilings.coolingCeiling - ceilings.otrCeiling).toFixed(1)}{' '}
              mmol before cooling does, so cooling never appears as a binding axis on the capacity
              screen. That is the equipment, not a gap in the data, and it is the opposite of what
              the tropical-cooling argument leads people to expect. Relieve transfer with
              overpressure and the two land{' '}
              {Math.abs(pressed.otrCeiling - ceilings.coolingCeiling).toFixed(1)} mmol apart, with
              nowhere left to go.
            </div>
          </div>
        </div>
      </Card>

      <Card className="mt-4">
        <SectionTitle>Candidates against this envelope</SectionTitle>
        <div className="space-y-5 mt-2">
          {CANDIDATES.slice(0, 4).map((c) => (
            <div key={c.id}>
              <div className="text-caption mb-1">
                <a href={href(`/proforma/screen/${plant.id}/c/${c.id}`)} className="font-num hover:text-accent">
                  {c.id}
                </a>{' '}
                {c.product}
              </div>
              <EnvelopeMatch match={c.match ?? matchEnvelope(plant, c)} />
            </div>
          ))}
        </div>
      </Card>

      <DemoFooter />
    </div>
  );
}

// ── shared ─────────────────────────────────────────────────────────────

export function DisclosureSection({ disclosures }: { disclosures: typeof DISCLOSURES }) {
  return (
    <div className="mt-6">
      <SectionTitle>What should be published · {disclosures.length}</SectionTitle>
      <div className="text-caption text-ink-soft mb-2 max-w-prose">
        Every archetype ends here. An archetype that produced no disclosure candidate would be a
        signal that the archetype is wrong, not that the field is optional.
      </div>
      {disclosures.length ? (
        <div className="grid md:grid-cols-2 gap-3">
          {disclosures.map((d) => (
            <DisclosureCard key={d.id} dc={d} />
          ))}
        </div>
      ) : (
        <EmptyState title="None" body="This deliverable names nothing to publish, which is itself a finding." />
      )}
      <div className="text-caption mt-2">
        <a href={href('/notary/disclosures')} className="text-accent hover:underline">
          the whole queue →
        </a>
      </div>
    </div>
  );
}
