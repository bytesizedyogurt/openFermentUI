// MIRROR of openferment_core/protocol/scale.py. Python is canonical. Changes go
// there first, then here, and parity is enforced by pnpm verify.
//
// This file is not dead weight and is not scheduled for deletion: the UI runs
// offline in the browser, where there is no Python, and a bench sheet that had
// to make a network call before it could show an amount would be useless at the
// bench it was printed for. So the mirror stays — and because it stays, the
// agreement between the two has to be mechanically checked rather than
// remembered. `pnpm check:protocol` replays fixtures/scale.json, the
// language-neutral pin, against this file. If you change a scaling class, a
// precision increment or the stock-volume calculation here without changing it
// in Python, that check fails — and these numbers are weighed out by hand.
//
// Protocol scaling math (OF-DES-001 §8.11): quantities scale by declared
// class, rounded to each material's precision spec so recipes stay pipettable.
import type { Material, ProtocolVersion, Step } from '@/data/types';
import { roundToPrecision, fmt } from './units';

export interface ScaledMaterial extends Material {
  scaledAmount: number;
  scales: boolean;
  /** Volume of stock solution to reach scaledAmount, if stock is defined. */
  stockVolume?: { value: number; unit: string };
}

export function scaleMaterial(m: Material, scale: number): ScaledMaterial {
  const scales = m.scaling !== 'fixed';
  const raw = scales ? m.amount * scale : m.amount;
  const scaledAmount = roundToPrecision(raw, m.precision);
  const out: ScaledMaterial = { ...m, scaledAmount, scales };
  if (m.stock) {
    // amount (mass or volume of pure component) via stock concentration.
    // stock.conc in unit-per-mL of stock (e.g. g/mL → mL of stock needed).
    const vol = raw / m.stock.conc;
    out.stockVolume = { value: roundToPrecision(vol, 0.1), unit: m.stock.unit };
  }
  return out;
}

export function scaleMaterials(version: ProtocolVersion, scale: number): ScaledMaterial[] {
  return version.materials.map((m) => scaleMaterial(m, scale));
}

/**
 * Render a step's text at scale: replaces {{qty:materialName}} with the
 * scaled amount + unit, and {{stock:materialName}} with the stock volume.
 */
export function renderStepText(step: Step, version: ProtocolVersion, scale: number): string {
  return step.text.replace(/\{\{(qty|stock):([^}]+)\}\}/g, (_, kind, name) => {
    const mat = version.materials.find((m) => m.name === name);
    if (!mat) return `⟨unknown material: ${name}⟩`;
    const scaled = scaleMaterial(mat, scale);
    if (kind === 'stock' && scaled.stockVolume) {
      return `${fmt(scaled.stockVolume.value)} ${scaled.stockVolume.unit}`;
    }
    return `${fmt(scaled.scaledAmount)} ${mat.unit}`;
  });
}

/** Total batch label at scale, e.g. "5 L batch". */
export function batchLabel(version: ProtocolVersion, scale: number): string {
  const v = version.baseBatch.value * scale;
  return `${fmt(v)} ${version.baseBatch.unit} ${version.baseBatch.label}`;
}

/** Plain-text checklist of materials at scale (Copy as checklist). */
export function materialsChecklist(version: ProtocolVersion, scale: number, title: string): string {
  const lines = [
    `# ${title} — materials at ${batchLabel(version, scale)}`,
    `# openFerment export — corpus OF-COR-001 v1.0`,
    `# Protocol content is real: drawn from the catalogued literature and standard bench practice.`,
    `# Amounts here are computed by scaling the base batch, not measured at this scale.`,
    `# Cited figures are curator transcriptions, not yet checked against the source PDFs.`,
    '',
  ];
  for (const m of scaleMaterials(version, scale)) {
    const fixedNote = m.scales ? '' : ' (fixed — does not scale)';
    const stockNote = m.stockVolume
      ? ` — use ${fmt(m.stockVolume.value)} ${m.stockVolume.unit} of stock (${fmt(m.stock!.conc)} ${m.unit}/${m.stock!.unit === 'mL' ? 'mL' : m.stock!.unit})`
      : '';
    lines.push(`[ ] ${m.name}: ${fmt(m.scaledAmount)} ${m.unit}${fixedNote}${stockNote}`);
  }
  return lines.join('\n');
}

/** Inoculation-density helper: volume of seed at measured OD to hit target OD. */
export function inoculumVolume(
  targetOD: number,
  cultureVolumeML: number,
  seedOD: number,
): number | null {
  if (seedOD <= targetOD || seedOD <= 0) return null;
  // V_seed = V_final * targetOD / (seedOD - targetOD) approximated for small V:
  // exact: V_seed * seedOD = targetOD * (V_final); assume V_final includes seed.
  const v = (targetOD * cultureVolumeML) / seedOD;
  return roundToPrecision(v, 0.1);
}
