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
import { plantCeilings, matchEnvelope, normalise, monthsToExpiry, metabolicHeatKW } from '@/lib/demo';

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
    if (kind === 'chip') ok(dlvIds.has(target) || runIds.has(target) || accIds.has(target), `${f.id}: followup chip ${target} does not resolve`);
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
