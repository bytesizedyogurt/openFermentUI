/**
 * The TypeScript half of `check-servers.mjs`, as a separate file because it
 * imports the app's module graph and therefore needs `tsx`.
 *
 * Emits JSON on stdout and nothing else. Two payloads:
 *
 *  - `summaries`: `COST_MODELS` projected to the `CostModelSummary` shape, so
 *    the gate can compare it against what `proforma_mcp` derives from
 *    `data/corpus/scenarios.json`.
 *  - `attribution`: the record ids `fixture/cell.ts`'s rule attributes to each
 *    strain, so the gate can compare it against `records_attributed_to`.
 *
 * The attribution rule is REPRODUCED here rather than imported, because
 * `attributedTo` is not exported from the fixture and exporting it purely for
 * a test would widen that module's surface for the convenience of its own
 * gate. That makes this a third copy — and the reason the gate exists at all
 * is to hold every copy to the canonical Python one, so a third copy that is
 * checked is the point rather than a violation of it.
 */
import { COST_MODELS } from '@/data/scenarios';
import { PAPERS, RECORDS, STRAINS } from '@/data/source';

const summaries = COST_MODELS.map((m) => ({
  modelId: m.modelId,
  dims: m.dims.map((d) => {
    const field = (d as { field?: string }).field;
    return {
      key: d.key,
      label: d.label,
      unit: d.unit,
      values: [...d.values],
      ...(field !== undefined ? { field } : {}),
    };
  }),
  referencePoint: { ...m.referencePoint },
}));

const organismsByPaper = new Map(PAPERS.map((p) => [p.id, new Set(p.organisms)]));

const attribution: Record<string, string[]> = {};
for (const strain of STRAINS) {
  attribution[strain.id] = RECORDS.filter((r) =>
    r.organism
      ? r.organism === strain.id
      : (organismsByPaper.get(r.paperId)?.has(strain.id) ?? false),
  ).map((r) => r.id);
}

process.stdout.write(JSON.stringify({ summaries, attribution }));
