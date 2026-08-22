// What the scenario's point actually builds — fermOS's half of a slider move.
//
// The scenario workspace used to answer "what does this point cost?" four ways
// and "what does this point build?" not at all. Its whole right column was a
// price decomposition, a tornado ranked on price and a sweep of price. Those are
// Proforma's, and they have moved there.
//
// This is what fermOS should have been showing all along: move a slider and see
// the plant change. Vessel count, working volume, the duties the plant has to
// supply and reject, and what comes out of the end of it — cultivation physics
// and the recovery train, which is what the part's charter says it owns.
//
// ── WHY THIS SOLVES AND THE PRICE STRIP INTERPOLATES ──────────────────────
//
// The price above it is read off the precomputed sweep, because interpolating a
// grid is cheap enough to do on every frame of a drag. There is no grid of
// vessel counts — a plant has to be built to know how many fermenters it needs —
// so this panel calls the solve. `evaluatePlantCached` keys on (model, point),
// so dragging back through a point already visited is free, and the flowsheets
// here are seven to nine units.
import { Boxes, Factory, Thermometer, Zap } from 'lucide-react';

import { usePlantSolve } from '@/lib/use-plant';
import { fmt } from '@/engine/units';
import { href } from '@/router';
import { Card, SectionTitle, cx } from '@/components/ui';

/** One engineering readout: figure in mono, unit demoted, source named. */
function Reading({
  label,
  value,
  unit,
  sub,
  icon,
}: {
  label: string;
  value: string;
  unit?: string;
  sub?: string;
  icon?: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-baseline gap-1.5">
        {icon}
        <span className="text-caption uppercase tracking-wide text-ink-soft">{label}</span>
      </div>
      <div className="font-num text-section-title leading-tight mt-0.5">
        {value}
        {unit && <span className="text-caption text-ink-soft ml-1">{unit}</span>}
      </div>
      {sub && <div className="text-caption text-ink-soft mt-0.5">{sub}</div>}
    </div>
  );
}

export function ProcessConsequence({ scenarioId }: { scenarioId: string }) {
  const { scenario, spec, result } = usePlantSolve(scenarioId);

  if (!scenario || !spec) return null;

  if (!result) {
    return (
      <Card className="p-4">
        <SectionTitle>What this point builds</SectionTitle>
        <p className="text-body text-ink-soft max-w-prose">
          The flowsheet does not size at this point — usually a titer low enough that the vessel
          count runs away. The price above is clamped to the nearest modelled corner; this panel is
          not, so it says nothing rather than something plausible.
        </p>
      </Card>
    );
  }

  // The fermentation island, which is what a scenario's sliders mostly move.
  const reactors = result.units.filter((u) => u.area === 300);
  const vesselCount = reactors.reduce(
    (n, u) => n + Math.max(1, ...Object.values(u.parallel ?? {}), 1),
    0,
  );
  const volume = reactors
    .flatMap((u) => Object.entries(u.design))
    .filter(([k]) => /volume|V_?wf|reactor/i.test(k))
    .map(([, d]) => d.value)
    .reduce((a, b) => Math.max(a, b), 0);

  const recovery = result.areas.filter((a) => a.area >= 400);
  const recoveryShare =
    result.capital.installedEquipmentCost > 0
      ? recovery.reduce((t, a) => t + a.installedCost, 0) / result.capital.installedEquipmentCost
      : 0;

  return (
    <Card className="p-4">
      <SectionTitle
        right={
          <a
            className="text-caption text-accent hover:underline"
            href={href(`/fermos/s/${scenario.id}/plant`)}
          >
            The whole flowsheet →
          </a>
        }
      >
        What this point builds
      </SectionTitle>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Reading
          label="Fermentation"
          value={String(vesselCount)}
          unit={vesselCount === 1 ? 'vessel' : 'vessels'}
          sub={volume > 0 ? `${fmt(volume)} m³ working volume` : `${reactors.length} units in area 300`}
          icon={<Factory size={12} className="text-ink-soft" aria-hidden />}
        />
        <Reading
          label="Cooling duty"
          value={fmt(result.process.coolingDuty / 1000)}
          unit="MJ h⁻¹"
          sub="what the plant has to reject"
          icon={<Thermometer size={12} className="text-ink-soft" aria-hidden />}
        />
        <Reading
          label="Connected load"
          value={fmt(result.process.powerConsumption)}
          unit="kW"
          sub={`${result.units.length} unit operations`}
          icon={<Zap size={12} className="text-ink-soft" aria-hidden />}
        />
        <Reading
          label="Product"
          value={fmt(result.annualProduction / 1000)}
          unit="t yr⁻¹"
          sub={`${(result.product.purity * 100).toFixed(0)}% ${spec.productLabel}`}
          icon={<Boxes size={12} className="text-ink-soft" aria-hidden />}
        />
      </div>

      <div className="mt-3 pt-3 border-t border-line text-caption text-ink-soft max-w-prose">
        The recovery train carries{' '}
        <span className="font-num text-ink">{(recoveryShare * 100).toFixed(0)}%</span> of installed
        equipment cost here.{' '}
        {result.warnings.length > 0 && (
          <span className={cx('text-signal-warn')}>
            {result.warnings.length} unit{result.warnings.length === 1 ? ' is' : 's are'} sized or
            costed outside the range its correlation was fitted over — named on the plant screen.
          </span>
        )}
      </div>
    </Card>
  );
}
