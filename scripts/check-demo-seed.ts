// openFerment demo suite — seed integrity check.
//
// Run: npx tsx src/data/check-seed.ts
// Wire into CI. Every assertion here maps to a line in 02-WALKTHROUGH.md §7.
// It exits non-zero on failure, and it fails loudly rather than warning,
// because a broken cross-reference propagates into all six archetypes.
import { ORGANISMS, PLANTS, SOURCES, SOURCE_BY_ID, HS_CODES, DEMO_NOW, SEED_DISCLAIMER, assertCoreIntegrity } from '@/data/demo/core';
import { PATENT_FAMILIES, PATENT_BY_ID } from '@/data/demo/patents';
import { ACCESSIONS, ACCESSION_BY_ID, verifyNormalisation, heldAccessions } from '@/data/demo/accessions';
import {
  AUX_ORGANISMS, LYSINE_FACTOR_MAP, LYSINE_RUN_DESIGN, ROUTES_3HP, CANDIDATES,
  BAGASSE_CONCEPTS, BURGER_TREE, DISCLOSURES, DELIVERABLES, LYSINE_RESCUE, applyRescues,
} from '@/data/demo/archetypes';
import { RUNS, RUN_BY_ID, excursionIntegrals, hydrateExcursions } from '@/data/demo/runs';
import { ARCHETYPE_FLOWS } from '@/data/demo/flows';
import { BURGER_PROGRAMME, programmeOrder } from '@/data/demo/runbook';
import { FIELD_BY_ID } from '@/data/demo/core';
import protocolsJson from '../data/corpus/protocols.json';
const PROTOCOL_IDS = new Set((protocolsJson as { id: string }[]).map((x) => x.id));
import { FLOWS } from '@/data/flows';
import {
  plantCeilings, matchEnvelope, normalise, monthsToExpiry, metabolicHeatKW,
  // Aliased: this file already has a local `conflictPairs`, a flat list of
  // Accessions carrying links. These two are the pairwise resolutions.
  conflictPairs as railConflicts, reconciledPairs as railReconciled, isContradiction,
  openSurfaceIn, trajectoryRecovered,
} from '@/lib/demo';

const fails: string[] = [];
const ok = (cond: boolean, msg: string) => { if (!cond) fails.push(msg); };
const near = (a: number, b: number, tolPct = 1) => Math.abs(a - b) / Math.max(1e-9, Math.abs(b)) * 100 <= tolPct;

// ── Referential ────────────────────────────────────────────────────────

assertCoreIntegrity(ACCESSIONS);

const accIds = new Set(ACCESSIONS.map((a) => a.id));
const orgIds = new Set([...ORGANISMS, ...AUX_ORGANISMS].map((o) => o.id));
const pfIds = new Set(PATENT_FAMILIES.map((p) => p.id));
const runIds = new Set(RUNS.map((r) => r.id));
const dlvIds = new Set(DELIVERABLES.map((d) => d.id));
const dcIds = new Set(DISCLOSURES.map((d) => d.id));
const flowIds = new Set(ARCHETYPE_FLOWS.map((f) => f.id));

const checkAcc = (ids: string[], where: string) =>
  ids.forEach((id) => ok(accIds.has(id), `${where}: unknown Accession ${id}`));

LYSINE_FACTOR_MAP.forEach((f) => {
  f.excluded.forEach((e) => checkAcc(e.accessionIds, `factor ${f.field} exclusion`));
  f.explored.forEach((e) => checkAcc(e.accessionIds, `factor ${f.field} explored`));
  if (f.ftoFlag) ok(pfIds.has(f.ftoFlag.patentFamilyId), `factor ${f.field}: unknown family ${f.ftoFlag.patentFamilyId}`);
});
ROUTES_3HP.forEach((r) => {
  r.steps.forEach((s) => {
    checkAcc(s.accessionIds, `step ${s.id}`);
    s.claims.forEach((c) => ok(pfIds.has(c.patentFamilyId), `step ${s.id}: unknown family ${c.patentFamilyId}`));
  });
  r.hosts.forEach((h) => ok(orgIds.has(h.organismId), `route ${r.id}: unknown organism ${h.organismId}`));
  checkAcc([r.theoreticalYieldAccessionId], `route ${r.id}`);
});
CANDIDATES.forEach((c) => {
  ok(orgIds.has(c.organismId), `${c.id}: unknown organism ${c.organismId}`);
  checkAcc([c.feedstockCostAccessionId, ...c.tradeAccessionIds], c.id);
  c.patentPosition.forEach((p) => p.familyIds.forEach((f) => ok(pfIds.has(f), `${c.id}: unknown family ${f}`)));
});
BAGASSE_CONCEPTS.forEach((fc) => {
  fc.blockFlow.forEach((b) => checkAcc(b.accessionIds, `${fc.id} / ${b.block}`));
  fc.patentOverlay.forEach((p) => p.familyIds.forEach((f) => ok(pfIds.has(f), `${fc.id}: unknown family ${f}`)));
});
BURGER_TREE.forEach((n) => {
  checkAcc(n.accessionIds, n.id);
  n.candidateOrganismIds.forEach((o) => ok(orgIds.has(o), `${n.id}: unknown organism ${o}`));
  if (n.parentId) ok(BURGER_TREE.some((p) => p.id === n.parentId), `${n.id}: orphan parent ${n.parentId}`);
  if (n.spawnsFlowId) ok(flowIds.has(n.spawnsFlowId), `${n.id}: unknown flow ${n.spawnsFlowId}`);
});
DISCLOSURES.forEach((d) => checkAcc(d.supportingAccessionIds, d.id));
DELIVERABLES.forEach((d) => {
  checkAcc(d.accessionIds, d.id);
  d.disclosureCandidateIds.forEach((x) => ok(dcIds.has(x), `${d.id}: unknown disclosure ${x}`));
  ok(d.disclosureCandidateIds.length > 0, `${d.id}: no disclosure candidate — every archetype must produce one`);
  ok(d.accessionIds.length >= 6, `${d.id}: only ${d.accessionIds.length} Accessions, minimum is six`);
});
ok(dlvIds.has(LYSINE_RESCUE.byDeliverableId), 'LYSINE_RESCUE points at an unknown deliverable');
ok(CANDIDATES.some((c) => c.id === LYSINE_RESCUE.candidateId), 'LYSINE_RESCUE points at an unknown candidate');

ARCHETYPE_FLOWS.forEach((f) => {
  if (f.deliverableId) ok(dlvIds.has(f.deliverableId), `${f.id}: unknown deliverable ${f.deliverableId}`);
  (f.handoffs ?? []).forEach((h) => ok(flowIds.has(h), `${f.id}: unknown handoff ${h}`));
  (f.followups ?? []).forEach((s) => {
    const [kind, rest] = String(s).split(':');
    const target = (rest ?? '').split('|')[0];
    if (kind === 'flow') ok(flowIds.has(target), `${f.id}: followup to unknown flow ${target}`);
    if (kind === 'chip')
      ok(
        dlvIds.has(target) || runIds.has(target) || accIds.has(target) || target === BURGER_PROGRAMME.id,
        `${f.id}: followup chip ${target} does not resolve`,
      );
  });
  const chips = [...String(f.answerMd).matchAll(/\[\[([A-Za-z0-9-]+)\]\]/g)].map((m) => m[1]);
  chips.forEach((c) =>
    ok(accIds.has(c) || pfIds.has(c) || orgIds.has(c) || runIds.has(c) || dlvIds.has(c), `${f.id}: chip ${c} does not resolve`));
});

ACCESSIONS.forEach((a) => {
  ok(!!SOURCE_BY_ID[a.sourceId], `${a.id}: unknown source ${a.sourceId}`);
  if (a.sourceType === 'patent-example' || a.sourceType === 'patent-claim') {
    ok(!!a.patentFamilyId && !!PATENT_BY_ID[a.patentFamilyId], `${a.id}: patent Accession without a resolvable family`);
    if (a.patentFamilyId) ok(PATENT_BY_ID[a.patentFamilyId].jurisdictions.length > 0, `${a.id}: family has no jurisdictions`);
  }
  if (a.runId) ok(runIds.has(a.runId), `${a.id}: unknown run ${a.runId}`);
  if (a.citesAccessionId) ok(accIds.has(a.citesAccessionId), `${a.id}: recitation target missing`);
  (a.conflictsWith ?? []).forEach((c) => ok(accIds.has(c), `${a.id}: conflict target ${c} missing`));
  ok(a.provenance !== 'unsourced', `${a.id}: provenance is unsourced — this is the fault state`);
});
HS_CODES.forEach((h) => checkAcc(h.accessionIds, `HS ${h.code}`));

// ── Numeric ────────────────────────────────────────────────────────────

verifyNormalisation().forEach((e) => fails.push(`normalisation: ${e}`));
ACCESSIONS.forEach((a) => {
  const v = normalise(a, ACCESSION_BY_ID);
  ok(near(v, a.normalized.value, 0.5), `${a.id}: lib recomputes ${v} against stored ${a.normalized.value}`);
});

const c = plantCeilings(PLANTS[0]);
ok(near(c.superficialGasVelocity, 0.049), `vs = ${c.superficialGasVelocity}, expected 0.049`);
ok(near(c.klaClean, 385), `kLa clean = ${c.klaClean}, expected 385`);
ok(near(c.klaEffective, 177.1), `kLa effective = ${c.klaEffective}, expected 177.1`);
ok(near(c.otrCeiling, 33.2, 2), `OTR at 1 atm = ${c.otrCeiling}, expected 33.2`);
ok(near(c.coolingCeiling, 50.9), `cooling ceiling = ${c.coolingCeiling}, expected 50.9`);

const cPressed = plantCeilings(PLANTS[0], { pressureBara: 1.5 });
ok(near(cPressed.otrCeiling, 49.7, 2), `OTR at 1.5 bara = ${cPressed.otrCeiling}, expected 49.7`);
ok(
  Math.abs(cPressed.otrCeiling - c.coolingCeiling) < 2,
  `the two ceilings should land within 2 mmol of each other: ${cPressed.otrCeiling} vs ${c.coolingCeiling}`,
);

BAGASSE_CONCEPTS.forEach((fc) => {
  const sum = fc.majorEquipment.reduce((s, e) => s + e.costUSD, 0);
  ok(near(sum, fc.capexUSD, 0.5), `${fc.id}: equipment sums to ${sum}, capex states ${fc.capexUSD}`);
});

// OF-DEMO-003 §7 requires EVERY row of its §3 table to recompute, and six were
// not covered: C*, the de-rated peak OUR, the cooling headroom, the RUN-047 O₂
// deficit and closure gap, and the capex anchor. A table row nobody replays is
// a number that has quietly become an assertion, which is the exact thing that
// table exists to prevent.

// C* at 30 °C, air at 1 atm — the input every OTR number below depends on.
ok(near(c.cStar, 0.234), `C* at 30 °C = ${c.cStar}, expected 0.234`);

// De-rated lysine peak OUR: qO₂ · X, from the two Accessions that state them.
{
  const q = ACCESSION_BY_ID['OF-A-00152'];
  const x = ACCESSION_BY_ID['OF-A-00153'];
  ok(!!q && !!x, 'OF-A-00152 and OF-A-00153 must both exist — the de-rated design point rests on them');
  if (q && x) {
    ok(near(q.reported.value * x.normalized.value, 48), `de-rated peak OUR = ${q.reported.value * x.normalized.value}, expected 48`);
    ok(near(q.normalized.value, 48), `OF-A-00152 normalises to ${q.normalized.value}, expected 48`);
  }
}

// Cooling headroom at the de-rated point. The duty is what the de-rated OUR
// costs in heat; the headroom is what the plant has left over it.
{
  const oxygen = ACCESSION_BY_ID['OF-A-00152']!.normalized.value; // mmol L⁻¹ h⁻¹
  const totalVolumeL = PLANTS[0].vessels.workingVolumeM3 * PLANTS[0].vessels.count * 1000;
  // Metabolic heat is not the whole duty: agitation puts its shaft power in as
  // heat too, and the chiller sees the sum. matchEnvelope adds them the same
  // way — this check mirrors it rather than inventing a second convention.
  const dutyKW = metabolicHeatKW(oxygen, totalVolumeL) + c.agitationKW;
  const installed = PLANTS[0].utilities.chilledWaterKW;
  const headroom = ((installed - dutyKW) / installed) * 100;
  ok(near(dutyKW, 76.3, 2), `de-rated cooling duty = ${dutyKW.toFixed(1)} kW, expected 76.3`);
  ok(near(headroom, 4.6, 15), `cooling headroom = ${headroom.toFixed(1)} %, expected 4.6`);
  ok(headroom > 0, 'the de-rated point must sit INSIDE the cooling ceiling, or the promotion is not a promotion');
}

// RUN-047, both stated integrals.
{
  const iv = excursionIntegrals('RUN-047', RUN_BY_ID['RUN-047'].comparisonBasis);
  ok(!!iv && near(iv.o2DeficitMmolPerL, 7.4, 2), `RUN-047 O₂ deficit = ${iv?.o2DeficitMmolPerL}, expected 7.4`);
  const closed = ACCESSION_BY_ID['OF-A-00149'];
  const observed = ACCESSION_BY_ID['OF-A-00150'];
  ok(!!closed && !!observed, 'the two carbon-closure Accessions must exist');
  if (closed && observed) {
    const gap = closed.normalized.value - observed.normalized.value;
    ok(near(gap, 1.3, 2), `RUN-047 closure gap = ${gap.toFixed(2)} points, expected 1.3`);
  }
}

// The lysine capex anchor. Stored as a reported quantity rather than derived,
// so what is checked here is that the stored value still equals the division
// OF-DEMO-003 §3 says it came from. If the two ever part, one of them is wrong.
{
  const anchor = ACCESSION_BY_ID['OF-A-00416'];
  ok(!!anchor, 'OF-A-00416 (lysine capex anchor) must exist');
  if (anchor) ok(near(anchor.normalized.value, 38e6 / 12000, 1), `capex anchor = ${anchor.normalized.value}, expected 38 M USD / 12,000 t = ${(38e6 / 12000).toFixed(0)}`);
}

ok(monthsToExpiry('2028-06-19', DEMO_NOW) === 22, `PF-003 expiry should be 22 months, got ${monthsToExpiry('2028-06-19', DEMO_NOW)}`);

hydrateExcursions();
const it = excursionIntegrals('RUN-047', RUN_BY_ID['RUN-047'].comparisonBasis);
ok(!!it && it.o2DeficitMmolPerL > 0, `RUN-047 O₂ deficit should be positive, got ${it?.o2DeficitMmolPerL}`);
ok(!!it && it.cerDeviationMmolPerL !== 0, `RUN-047 CER deviation should be non-zero, got ${it?.cerDeviationMmolPerL}`);
ok(RUNS.filter((r) => r.excursions.length > 0).length === 1, 'exactly one run should carry an excursion');
RUNS.forEach((r) => {
  const lens = new Set(r.channels.map((ch) => ch.values.length));
  ok(lens.size === 1, `${r.id}: channels have mismatched lengths`);
});

// ── Structural ─────────────────────────────────────────────────────────

const held = heldAccessions();
ok(held.some((h) => h.id === 'OF-A-00147' && h.reason === 'excursion-flagged'), 'OF-A-00147 must be held as excursion-flagged');
ok(
  (DELIVERABLES.find((d) => d.id === 'DLV-AR1-001')!.payload as { excludedAccessionIds: string[] }).excludedAccessionIds.includes('OF-A-00147'),
  'seam 1 broken: OF-A-00147 must be excluded on the gap map',
);
ok(LYSINE_RESCUE.change.includes('OF-A-00124'), 'seam 2 broken: the rescue must cite the μ = 0.10 Accession');
ok(BURGER_TREE.some((n) => n.id === 'PN-210' && n.accessionIds.includes('OF-A-00325')), 'seam 4 broken: PN-210 must inherit the ambient constraint');
ok(BURGER_TREE.filter((n) => n.spawnsFlowId === 'AR2').length >= 2, 'seam 8 broken: at least two leaves must spawn AR2');

const conflictPairs = ACCESSIONS.filter((a) => (a.conflictsWith ?? []).length > 0);
ok(conflictPairs.length >= 2, 'the pool must carry at least one live contradiction in both directions');
ok(
  !ACCESSION_BY_ID['OF-A-00404'].conflictsWith?.length && !ACCESSION_BY_ID['OF-A-00414'].conflictsWith?.length,
  'contradiction 4 is not a contradiction — different organisms must not flag a rail',
);

LYSINE_FACTOR_MAP.forEach((f) => {
  f.excluded.forEach((e) => {
    ok(e.accessionIds.length > 0, `factor ${f.field}: an exclusion with no supporting Accession`);
    ok(e.singleSource === (e.accessionIds.length === 1), `factor ${f.field}: singleSource flag disagrees with the Accession count`);
  });
});
ok(LYSINE_RUN_DESIGN.length === 12, `run design should be twelve runs, got ${LYSINE_RUN_DESIGN.length}`);
ok(LYSINE_RUN_DESIGN.filter((r) => r.cell === 'centre').length === 2, 'the block needs a centre replicate or it has no error term');

applyRescues(CANDIDATES);
const jurisdiction = PLANTS[0].location.jurisdiction;
const matches = CANDIDATES.map((cand) => ({ cand, m: matchEnvelope(PLANTS[0], cand) }));
const survivors = matches.filter((x) => x.m.feasible);
ok(survivors.length === 7, `expected seven survivors, got ${survivors.length}`);
const byAxis = (ax: string) => matches.filter((x) => x.m.bindingAxis === ax).length;
ok(byAxis('Oxygen transfer') === 8, `expected eight oxygen-transfer exclusions, got ${byAxis('Oxygen transfer')}`);
ok(byAxis('Installed power') === 1, `expected one power exclusion, got ${byAxis('Installed power')}`);
ok(byAxis('Separation') === 2, `expected two separation exclusions, got ${byAxis('Separation')}`);
ok(byAxis('Cooling duty') === 0, 'cooling must not appear as a binding axis at this plant');
ok(survivors.every((x) => !x.m.bindingAxis), 'a survivor must not be labelled with a binding axis');
ok(
  matches.find((x) => x.cand.id === 'CND-002')!.m.feasible,
  'CND-002 thermophilic lactate must survive the envelope — it is the safe answer',
);
ok(
  !matches.find((x) => x.cand.id === 'CND-001')!.m.feasible,
  'CND-001 must fail at the naive operating point, or the rescue has nothing to rescue',
);
// Cooling never appears as a BINDING axis at this plant, and that is a real
// finding rather than a gap. Oxygen transfer fails 16 mmol earlier at 1 atm,
// so it always binds first; relieve transfer with overpressure and cooling
// becomes binding within 1.2 mmol. Assert the structure, not a fabricated
// cooling failure.
ok(
  c.coolingCeiling > c.otrCeiling,
  `transfer must bind before cooling at 1 atm: OTR ${c.otrCeiling}, cooling ${c.coolingCeiling}`,
);
ok(
  matches.filter((x) => x.m.bindingAxis === 'Oxygen transfer' && !x.m.feasible).length >= 5,
  'the screen must show oxygen transfer as the dominant exclusion axis',
);
ok(
  Math.abs(c.coolingCeiling - cPressed.otrCeiling) < 2,
  `once transfer is relieved, cooling must bind within 2 mmol: ${cPressed.otrCeiling} vs ${c.coolingCeiling}`,
);
ok(matches.some((x) => x.m.bindingAxis === 'Installed power'), 'xanthan must fail on power, not on oxygen');
ok(
  CANDIDATES.some((x) => x.id === 'CND-002' && x.patentPosition.some((p) => p.jurisdiction !== jurisdiction && p.status === 'enclosed')),
  'CND-002 must carry the export-market FTO caveat',
);

// A factor exclusion states `singleSource` and also lists its Accessions. The
// band renders a warning triangle off the flag and the reader counts the ids
// beside it, so the two must agree or the screen contradicts itself in place.
for (const f of LYSINE_FACTOR_MAP) {
  for (const e of f.excluded) {
    ok(
      e.singleSource === (e.accessionIds.length === 1),
      `${f.field} exclusion ${e.low}-${e.high}: singleSource is ${e.singleSource} but it cites ${e.accessionIds.length} Accession(s)`,
    );
    ok(e.accessionIds.length > 0, `${f.field} exclusion ${e.low}-${e.high} cites no Accession — an exclusion nobody can check`);
    ok(e.low < e.high, `${f.field} exclusion ${e.low}-${e.high} is empty or inverted`);
    ok(
      e.low >= f.domain.low && e.high <= f.domain.high,
      `${f.field} exclusion ${e.low}-${e.high} falls outside the domain ${f.domain.low}-${f.domain.high}`,
    );
  }
  ok(
    f.recommended.low >= f.domain.low && f.recommended.high <= f.domain.high,
    `${f.field}: the recommended range falls outside the domain`,
  );
  // The unexplored gap is what the band is FOR. A factor with none has nothing
  // to say on the screen that exists to show where nobody has been.
  const covered = [...f.explored, ...f.excluded].map((r) => [r.low, r.high] as const).sort((a, b) => a[0] - b[0]);
  let cursor = f.domain.low;
  let gap = 0;
  for (const [a, b] of covered) { if (a > cursor) gap += a - cursor; cursor = Math.max(cursor, b); }
  if (cursor < f.domain.high) gap += f.domain.high - cursor;
  ok(gap > 0, `${f.field}: nothing is unexplored, so the factor band has no finding to show`);
}

// ── The four deliberate contradictions (OF-DEMO-003 §5) ────────────────
//
// Three must render and the fourth must NOT. That last one is the check that
// matters: a system which flags everything is as useless as one that flags
// nothing, and furfural tolerance at 1.9 and 0.9 g L⁻¹ is not a disagreement —
// the two are different organisms and the context field says which.

{
  const on = (f: string) => ACCESSIONS.filter((x) => x.field === f);

  // 1 — temperature shift. A journal and a patent working example disagreeing.
  {
    const pair = railConflicts(on('titer'));
    ok(
      pair.some(([x, y]) => [x.id, y.id].sort().join() === 'OF-A-00106,OF-A-00107'),
      'contradiction 1 (temperature shift, OF-A-00106 vs OF-A-00107) must render an unresolved rail',
    );
  }

  // 2 — anisotropy 3.4 both ways. Identical value, opposing implications, so
  // spread cannot find it and only the curated link can.
  {
    const pair = railConflicts(on('purity'));
    ok(
      pair.some(([x, y]) => [x.id, y.id].sort().join() === 'OF-A-00509,OF-A-00511'),
      'contradiction 2 (anisotropy, OF-A-00509 vs OF-A-00511) must render an unresolved rail — the values agree and what they imply does not',
    );
    const a509 = ACCESSION_BY_ID['OF-A-00509'];
    ok(!!a509?.conflictNote, 'contradiction 2 must carry a conflictNote — two identical numbers cannot show the disagreement by themselves');
  }

  // 3 — lactate MSP, two cost bases. The REVERSE case: it must render as
  // reconciled, never as a conflict.
  {
    const rec = railReconciled(on('minimum_selling_price'));
    ok(
      rec.some(([x, y]) => [x.id, y.id].sort().join() === 'OF-A-00418,OF-A-00419'),
      'contradiction 3 (lactate MSP) must render as closed-by-normalisation',
    );
    ok(
      !railConflicts(on('minimum_selling_price')).some(([x, y]) => [x.id, y.id].sort().join() === 'OF-A-00418,OF-A-00419'),
      'contradiction 3 must NOT render as unresolved — the two agree once the units are closed',
    );
    const a = ACCESSION_BY_ID['OF-A-00418'];
    const b = ACCESSION_BY_ID['OF-A-00419'];
    if (a && b) {
      const spread = Math.abs(a.normalized.value - b.normalized.value) / a.normalized.value * 100;
      ok(spread <= 1.5, `contradiction 3 should agree within 1.5 % after normalisation; it differs by ${spread.toFixed(2)} %`);
    }
  }

  // 4 — furfural tolerance. Must NOT render a rail.
  {
    const accs = on('inhibitor_tolerance');
    ok(accs.length >= 2, 'contradiction 4 needs at least two Accessions on inhibitor_tolerance to be a meaningful non-case');
    ok(
      !isContradiction(accs),
      'contradiction 4 (furfural tolerance) must NOT render a rail — the values differ because the organisms differ, and the context field says so',
    );
    const orgs = new Set(accs.map((x) => x.context.organismId).filter(Boolean));
    ok(orgs.size > 1, 'contradiction 4 is only a non-case because the organisms differ — every Accession must carry one');
  }

  // And the suite-level rule: exactly the curated pairs, no others invented.
  const allConflicts = new Set<string>();
  for (const x of ACCESSIONS) for (const id of x.conflictsWith ?? []) allConflicts.add([x.id, id].sort().join());
  ok(allConflicts.size === 2, `expected exactly 2 curated conflicting pairs, found ${allConflicts.size}: ${[...allConflicts].join(' ')}`);
  for (const x of ACCESSIONS) {
    for (const id of [...(x.conflictsWith ?? []), ...(x.reconciledWith ?? [])]) {
      const other = ACCESSION_BY_ID[id];
      ok(!!other, `${x.id} names ${id}, which is not in the pool`);
      if (other) {
        ok(other.field === x.field, `${x.id} and ${id} are linked but sit on different fields (${x.field} vs ${other.field}) — a rail can only compare like with like`);
        const back = [...(other.conflictsWith ?? []), ...(other.reconciledWith ?? [])];
        ok(back.includes(x.id), `${x.id} names ${id} but ${id} does not name it back — a one-way link renders on one screen and not the other`);
      }
    }
  }
}

// ── The seam matrix (OF-DEMO-003 §4) ───────────────────────────────────
//
// Ten cross-references, each of which must render on BOTH named screens. This
// is the table that makes the suite read as a platform rather than as six
// demos, and it is the one most likely to rot: a screen can be rewritten
// without anyone noticing that the object it used to link to is no longer
// reachable from it.
//
// What is checked here is the DATA side of each row — that the object exists,
// that both ends reference it, and that the property the row depends on still
// holds. The rendering side is `scripts/smoke.mjs`, which visits both screens.

{
  const dlvById = new Map(DELIVERABLES.map((d) => [d.id, d]));
  const seam = (n: number, cond: boolean, msg: string) => ok(cond, `seam ${n}: ${msg}`);

  // 1 — OF-A-00147, produced by AR6, consumed by AR1 as an exclusion.
  {
    const a = ACCESSION_BY_ID['OF-A-00147'];
    seam(1, !!a, 'OF-A-00147 must exist');
    seam(1, a?.hold === 'excursion-flagged', `OF-A-00147 must be held as excursion-flagged, is ${a?.hold}`);
    seam(1, !!a?.runId, 'OF-A-00147 must name the run behind it, or the gap map cannot link back');
    const ar1 = DELIVERABLES.find((d) => d.payload.kind === 'factor-map');
    seam(
      1,
      !!ar1 && ar1.payload.kind === 'factor-map' && ar1.payload.excludedAccessionIds.includes('OF-A-00147'),
      'the factor map must list OF-A-00147 among its exclusions',
    );
  }

  // 2 — OF-A-00124 (mu), produced by AR1, rescues CND-001 in AR3.
  {
    seam(2, !!ACCESSION_BY_ID['OF-A-00124'], 'OF-A-00124 must exist');
    const c = CANDIDATES.find((x) => x.id === 'CND-001');
    seam(2, !!c?.rescue, 'CND-001 must carry a rescue');
    seam(2, !!c?.rescue && dlvById.has(c.rescue.byDeliverableId), `CND-001's rescue must name a real deliverable`);
    seam(2, !!c?.rescue?.change.includes('OF-A-00124'), 'the rescue note must name the Accession it rests on');
  }

  // 3 — the de-rated point, marked inside AR1's band.
  {
    for (const id of ['OF-A-00152', 'OF-A-00153']) seam(3, !!ACCESSION_BY_ID[id], `${id} must exist`);
    const mu = ACCESSION_BY_ID['OF-A-00124'];
    const f = LYSINE_FACTOR_MAP.find((x) => x.field === 'mu_setpoint');
    seam(3, !!f, 'the factor map must carry a mu_setpoint band for the de-rated point to be marked in');
    if (f && mu) {
      seam(
        3,
        mu.normalized.value >= f.domain.low && mu.normalized.value <= f.domain.high,
        `the de-rated mu ${mu.normalized.value} falls outside the band domain ${f.domain.low}-${f.domain.high}, so the mark would render off-canvas`,
      );
      seam(
        3,
        mu.normalized.value >= f.recommended.low && mu.normalized.value <= f.recommended.high,
        `the de-rated mu ${mu.normalized.value} must sit INSIDE the recommended band — that is what makes it a rescue rather than a gamble`,
      );
    }
  }

  // 4 — ambient temperature, from AR3's cooling ceiling into AR5's tree.
  seam(4, !!ACCESSION_BY_ID['OF-A-00325'], 'OF-A-00325 (ambient) must exist');

  // 6, 7 — patent families shared between AR3 and AR4.
  for (const [n, fid] of [[6, 'PF-012'], [7, 'PF-013']] as [number, string][]) {
    const fam = PATENT_BY_ID[fid];
    seam(n, !!fam, `${fid} must exist`);
    seam(n, !!fam && fam.jurisdictions.length > 0, `${fid} must record jurisdictions`);
  }

  // 8 — AR5's leaves hand off to AR2.
  {
    const tree = DELIVERABLES.find((d) => d.payload.kind === 'problem-tree');
    seam(8, !!tree, 'the problem tree must exist');
    if (tree && tree.payload.kind === 'problem-tree') {
      const spawning = tree.payload.nodes.filter((n) => n.spawnsFlowId);
      seam(8, spawning.length > 0, 'at least one leaf must spawn a route comparison — that handoff IS the composability demonstration');
      for (const n of spawning) {
        seam(8, ARCHETYPE_FLOWS.some((f) => f.id === n.spawnsFlowId), `${n.id} spawns ${n.spawnsFlowId}, which is not a flow`);
      }
    }
  }

  // 9 — OF-A-00119, the critical-DO Accession, in AR1 and AR6.
  {
    const a = ACCESSION_BY_ID['OF-A-00119'];
    seam(9, !!a, 'OF-A-00119 must exist');
    const inFactor = LYSINE_FACTOR_MAP.some((f) =>
      [...f.excluded.flatMap((e) => e.accessionIds), ...f.explored.flatMap((e) => e.accessionIds)].includes('OF-A-00119'),
    );
    seam(9, inFactor, 'OF-A-00119 must appear in the factor map');
    // The verdict lives on the DELIVERABLE payload, not on the RunRecord —
    // `RunRecord.verdict` is optional and unset in this seed, and a check that
    // read it would have silently passed on `undefined`.
    const ar6 = DELIVERABLES.find((d) => d.payload.kind === 'excursion-verdict');
    seam(9, !!ar6, 'the excursion-verdict deliverable must exist');
    const reasoning = ar6 && ar6.payload.kind === 'excursion-verdict' ? ar6.payload.verdict.reasoning : [];
    seam(9, reasoning.length > 0, 'the verdict must give its reasoning');
    seam(
      9,
      reasoning.join(' ').includes('OF-A-00119'),
      'the verdict must cite OF-A-00119 by id — the same value, both places, or the seam is a coincidence',
    );
  }

  // 10 — a two-deep derivation chain must actually be two deep, or the
  // Accession page's recursion has nothing to show.
  {
    const a = ACCESSION_BY_ID['OF-A-00308'];
    seam(10, !!a, 'OF-A-00308 (effective kLa) must exist');
    if (a) {
      const depth = (acc: typeof a, seen = new Set<string>()): number => {
        if (!acc || seen.has(acc.id)) return 0;
        seen.add(acc.id);
        const kids = acc.derivation.usingAccessionIds.map((id) => ACCESSION_BY_ID[id]).filter(Boolean);
        return kids.length ? 1 + Math.max(...kids.map((k) => depth(k, seen))) : 0;
      };
      seam(10, depth(a) >= 2, `OF-A-00308's derivation chain is ${depth(a)} deep; the seam calls for two`);
    }
  }

  // And the suite-level rule behind all ten: every deliverable names at least
  // one disclosure candidate, and every candidate resolves.
  for (const d of DELIVERABLES) {
    ok(d.disclosureCandidateIds.length > 0, `${d.id} names no disclosure candidate — that is a signal the archetype is wrong, not that the field is optional`);
    ok(d.accessionIds.length >= 6, `${d.id} references ${d.accessionIds.length} Accessions; every deliverable must rest on at least six`);
  }
}

// ── The flows, and the chips inside them (OF-DEMO-003 §7) ──────────────
//
// The six archetype flows share one matcher with the thirteen casein flows.
// Two things must hold for that to be safe, and neither is obvious from either
// array on its own — which is exactly why they are checked here.

{
  // 1. No trigger may be claimed by two flows. A shared trigger means the
  //    matcher's answer depends on array order, and array order is not a
  //    product decision anybody made.
  const claim = new Map<string, string>();
  for (const f of [...FLOWS, ...ARCHETYPE_FLOWS]) {
    for (const t of f.triggers) {
      const norm = t.trim().toLowerCase();
      const prev = claim.get(norm);
      ok(!prev, `trigger "${t}" is claimed by both ${prev} and ${f.id} — the matcher would answer by array order`);
      claim.set(norm, f.id);
    }
  }

  // 2. Every chip in every archetype answer must resolve, and resolve to the
  //    DEMO pool. A chip that fell through to the corpus resolver would put an
  //    invented identifier beside real literature.
  const CHIP = /\[\[([A-Za-z0-9-]+)\]\]/g;
  const demoIds = new Set<string>([
    ...ACCESSIONS.map((a) => a.id),
    ...PATENT_FAMILIES.map((f) => f.id),
    ...[...ORGANISMS, ...AUX_ORGANISMS].map((o) => o.id),
    ...RUNS.map((r) => r.id),
    ...DELIVERABLES.map((d) => d.id),
  ]);
  let chips = 0;
  for (const f of ARCHETYPE_FLOWS) {
    for (const m of f.answerMd.matchAll(CHIP)) {
      chips += 1;
      ok(demoIds.has(m[1]), `flow ${f.id} cites [[${m[1]}]], which is not in the demo pool`);
    }
    ok(f.answerMd.trim().length > 0 || !!f.clarify, `flow ${f.id} has neither an answer nor a clarify`);
    ok(f.triggers.length > 0, `flow ${f.id} has no trigger, so nothing can reach it`);
    ok(f.plan.length > 0, `flow ${f.id} shows no plan`);
    // 3. A deliverableId must resolve, or the answer's closing card is a dead
    //    link — and it is the one chip a reviewer is most likely to click.
    const d = (f as { deliverableId?: string }).deliverableId;
    if (d) ok(dlvIds.has(d), `flow ${f.id} names deliverable ${d}, which does not exist`);
    for (const h of (f as { handoffs?: string[] }).handoffs ?? []) {
      ok(
        [...FLOWS, ...ARCHETYPE_FLOWS].some((x) => x.id === h),
        `flow ${f.id} hands off to ${h}, which is not a flow`,
      );
    }
    for (const c of f.clarify?.options ?? []) {
      ok(
        [...FLOWS, ...ARCHETYPE_FLOWS].some((x) => x.id === c.flowId),
        `flow ${f.id} offers a clarify option into ${c.flowId}, which is not a flow`,
      );
    }
  }
  ok(chips > 0, 'no chips were checked in any archetype answer, which means this check is watching nothing');

  // 4. Every archetype must be reachable and must produce a deliverable.
  for (const a of ['AR1', 'AR2', 'AR3', 'AR4', 'AR5', 'AR6']) {
    ok(ARCHETYPE_FLOWS.some((f) => f.id === a), `no flow for archetype ${a}`);
    ok(DELIVERABLES.some((d) => d.archetype === a), `no deliverable for archetype ${a}`);
  }
}

// ── The decision programme (Archetype 5's terminus) ────────────────────
//
// The tree restructures the question; the programme says what to do about it.
// Its ORDER is derived from information value per pound-week subject to
// dependencies, which is the kind of thing that looks right and silently is
// not — so it is checked rather than admired.

{
  const order = programmeOrder();
  const ids = new Set(BURGER_PROGRAMME.decisions.map((d) => d.id));
  const nodeIds = new Set(BURGER_TREE.map((n) => n.id));

  ok(order.length === BURGER_PROGRAMME.decisions.length, `programme order drops ${BURGER_PROGRAMME.decisions.length - order.length} decision(s) — a cycle in blockedBy`);

  // Every decision must land after everything that would change its answer.
  const seen = new Set<string>();
  for (const d of order) {
    for (const b of d.blockedBy ?? []) {
      ok(ids.has(b), `${d.id} is blocked by ${b}, which is not a decision`);
      if (ids.has(b)) ok(seen.has(b), `${d.id} is scheduled before ${b}, which it depends on`);
    }
    seen.add(d.id);
  }

  for (const d of BURGER_PROGRAMME.decisions) {
    ok(nodeIds.has(d.nodeId), `${d.id} settles ${d.nodeId}, which is not a node in the tree`);
    ok(!!FIELD_BY_ID[d.wouldProduce], `${d.id} would produce an Accession on ${d.wouldProduce}, which is not a field`);
    checkAcc(d.restsOn, `${d.id} restsOn`);
    if (d.protocolId) ok(PROTOCOL_IDS.has(d.protocolId), `${d.id} names protocol ${d.protocolId}, which is not in the corpus`);
    // A decisive measurement with no flip condition is just a measurement.
    ok(d.flipsIf.trim().length > 20, `${d.id} names a decisive measurement but not what would flip it`);
    ok(d.weeks > 0 && d.costGBP > 0, `${d.id} costs nothing and takes no time, which is not a decision`);
    ok(d.informationValue > 0 && d.informationValue <= 1, `${d.id} has an information value outside 0–1`);
  }

  // The question actually asked must be IN the programme and must not be first.
  const terminal = order.findIndex((d) => d.nodeId === 'PN-000');
  ok(terminal >= 0, 'the programme must contain the question that was asked');
  ok(terminal === order.length - 1, 'the triangle test must be last — it is the terminal measurement, and a programme that ran it first would spend the budget learning nothing about which branch failed');

  // The ordering must be doing work. If it equals declaration order, nothing
  // was optimised and the "derived, not authored" claim is decoration.
  const declared = BURGER_PROGRAMME.decisions.map((d) => d.id).join();
  ok(order.map((d) => d.id).join() !== declared, 'the derived order equals declaration order, so the ordering is not doing anything');
}

// ── Honesty ────────────────────────────────────────────────────────────
//
// CLAUDE.md's second invariant forbids fabricated data and names DOIs, years,
// authors and venues specifically. OF-DEMO-001 §2.1 requires exactly those to
// be synthetic here. The two are reconcilable only one way: the identifiers
// must be impossible BY CONSTRUCTION and mechanically proven so, not merely
// declared synthetic in a paragraph nobody re-reads. That is what this section
// does. If any check below stops holding, this pool has started to look like
// real literature and the disclaimer has become a lie.

{
  // A DOI prefix is issued by a registration agency. 10.9999 is not issued to
  // anyone, so no string here can collide with a real article.
  const SYNTHETIC_DOI_PREFIX = '10.9999';
  for (const src of SOURCES) {
    const doi = (src as { doi?: string }).doi;
    if (!doi) continue;
    ok(
      doi.startsWith(`${SYNTHETIC_DOI_PREFIX}/`),
      `${src.id} carries DOI '${doi}', which is not under the unissued ${SYNTHETIC_DOI_PREFIX} prefix. A DOI that could resolve is a fabricated claim about a real paper.`,
    );
  }

  // Patent numbers must sit in series that cannot have been granted. Each
  // pattern is impossible for a different reason, and the reason is the point:
  // a reviewer who checks one must find it unfindable rather than wrong.
  const IMPOSSIBLE: { re: RegExp; why: string }[] = [
    { re: /^US 20(2[89]|[3-9]\d)\/\d{7} A1$/, why: 'US publication year beyond any published series' },
    { re: /^EP 4 9\d{2} \d{3} A\d$/, why: 'EP number beyond current numbering' },
    { re: /^WO 20(2[89]|[3-9]\d)\/\d{6}$/, why: 'WO publication year beyond any published series' },
  ];
  let numbers = 0;
  for (const fam of PATENT_FAMILIES) {
    const num = fam.representativeNumber;
    numbers += 1;
    ok(
      IMPOSSIBLE.some((p) => p.re.test(num)),
      `patent number '${num}' (${fam.id}) is not in an impossible series — it could be mistaken for a live filing`,
    );
  }
  ok(numbers > 0, 'no patent numbers were checked, which means this check is watching nothing');

  ok(SEED_DISCLAIMER.length > 100, 'SEED_DISCLAIMER must state what is synthetic, at length');
  ok(
    /synthetic/i.test(SEED_DISCLAIMER) && /patent/i.test(SEED_DISCLAIMER),
    'SEED_DISCLAIMER must say that citation identifiers and patent numbers are synthetic',
  );

  // The two object pools must not mix. OF-DEMO-001 §8 forbids merging them and
  // the reason is epistemic: an ExtractionRecord is a catalogued claim awaiting
  // verification, an Accession is a normalised quantity with complete
  // provenance. A synthetic identifier leaking into the casein corpus would put
  // invented literature beside real literature, which is the one unrecoverable
  // error in this project.
  const demoIds = new Set<string>([
    ...ACCESSIONS.map((a) => a.id),
    ...PATENT_FAMILIES.map((f) => f.id),
    ...SOURCES.map((x) => x.id),
  ]);
  for (const id of demoIds) {
    ok(
      /^(OF-A-|PF-|SRC-)/.test(id),
      `demo id '${id}' does not carry a demo-pool prefix, so it cannot be told apart from a corpus id`,
    );
  }
}

// ── Report ─────────────────────────────────────────────────────────────

// RUN-047's excursion narrative says the off-gas CO₂ "did not return to the
// pre-excursion trajectory". `trajectoryRecovered` is the function that tests
// exactly that against the recorded series, and nothing called it — so the
// sentence and the data could have disagreed indefinitely. The prose is the
// claim; this is the check.
{
  const r = RUN_BY_ID['RUN-047'];
  const exc = r?.excursions[0];
  const cer = r?.channels.find((c) => c.id === 'cer');
  ok(Boolean(exc && cer), 'RUN-047 must carry an excursion and an off-gas CO₂ channel');
  if (exc && cer) {
    ok(
      trajectoryRecovered(cer.values, exc.startTick, exc.endTick) === false,
      'RUN-047 off-gas CO₂ is described as not returning to its pre-excursion ' +
        'trajectory; the recorded series must agree',
    );
  }
}

// ══════════════════════════════════════════════════════════════════════
// A stored number nobody checks is a decoration
// ══════════════════════════════════════════════════════════════════════
//
// `route.openSurface` — how many of a route's steps are enclosed, expiring or
// open — is the finding Archetype 2 turns on: the biochemistry ranks the
// routes one way and the patent positions reverse it. It was WRITTEN OUT in
// the seed at three sites while `openSurfaceIn`, the function that derives it
// from the per-step claim data, was never called by anything. Either could
// have drifted from the other without a single gate noticing, which is exactly
// the failure 00-BRIEF §4 exists to prevent: anything that only ever renders a
// stored number is decoration.
for (const r of ROUTES_3HP) {
  const computed = openSurfaceIn(
    r.steps.map((st) => st.claims.map((c) => ({ jurisdictions: c.jurisdictions, status: c.status }))),
    'US',
  );
  ok(
    computed.totalSteps === r.openSurface.totalSteps &&
      computed.enclosedSteps === r.openSurface.enclosedSteps &&
      computed.expiringSteps === r.openSurface.expiringSteps,
    `${r.id} openSurface must equal what the claim data computes — stored ` +
      `${JSON.stringify(r.openSurface)}, computed ${JSON.stringify(computed)}`,
  );
}

if (fails.length) {
  console.error(`\n[of] seed check FAILED — ${fails.length} problem(s):\n`);
  fails.forEach((f) => console.error('  · ' + f));
  process.exit(1);
}
console.log(
  `[of] seed check passed — ${ACCESSIONS.length} Accessions, ${PATENT_FAMILIES.length} families, ` +
  `${ORGANISMS.length + AUX_ORGANISMS.length} organisms, ${CANDIDATES.length} candidates, ` +
  `${RUNS.length} runs, ${DELIVERABLES.length} deliverables, ${DISCLOSURES.length} disclosures.`,
);
