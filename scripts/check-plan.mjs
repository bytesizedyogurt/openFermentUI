/**
 * AnswerPlan drift guard (OF-BLD-007 §3, §10.4).
 *
 * The plan shape is defined twice — Pydantic in `core/openferment_core/models.py`,
 * TypeScript in `src/data/types.ts` — because the service validates it and the
 * browser renders it, and neither can import the other's definition.
 *
 * A shape that exists twice and is enforced once is a shape that is about to
 * disagree with itself, and the disagreement is silent: the service starts
 * returning a field the UI never reads, or the UI reads a field the service
 * stopped sending, and the plan renders with a hole in it. So the two are
 * compared field for field here, and a mismatch fails the build.
 *
 * Deliberately text-level and pure Node. Verify must run with no Python
 * toolchain and no service, so this parses rather than imports — which is
 * enough to catch the only failure that actually happens: somebody adds a
 * field to one side.
 */
import { readFileSync } from 'node:fs';

const errors = [];
const fail = (m) => errors.push(m);

const py = readFileSync('core/openferment_core/models.py', 'utf8');
const ts = readFileSync('src/data/types.ts', 'utf8');

/**
 * Field names declared in a Pydantic model body — the wire names. A field that
 * declares `alias="x"` is serialised as `x`, which is what the browser reads,
 * so that is the name compared (Python needs the alias when the wire name is
 * a keyword: `from_: ... = Field(alias="from")`).
 */
function pydanticFields(source, className) {
  const body = source.split(`class ${className}(BaseModel):`)[1]?.split('\nclass ')[0];
  if (body === undefined) {
    fail(`models.py: no class ${className}`);
    return null;
  }
  return new Set(
    [...body.matchAll(/^ {4}([a-zA-Z_][a-zA-Z0-9_]*)\s*:(.*)$/gm)].map(
      (m) => m[2].match(/\balias="([^"]+)"/)?.[1] ?? m[1],
    ),
  );
}

/** Field names declared in a TS interface body, comments stripped. */
function tsFields(source, name) {
  const body = source.split(`export interface ${name} {`)[1]?.split('\n}')[0];
  if (body === undefined) {
    fail(`types.ts: no interface ${name}`);
    return null;
  }
  const clean = body.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
  return new Set(
    [...clean.matchAll(/^\s{2}([a-zA-Z_][a-zA-Z0-9_]*)\??\s*:/gm)].map((m) => m[1]),
  );
}

const PAIRS = [
  ['Claim', 'Claim'],
  ['Usage', 'AnswerPlanUsage'],
  ['AnswerPlan', 'AnswerPlan'],
  // OF-BLD-015 §7.1 — the coverage map.
  ['CoverageHit', 'CoverageHit'],
  ['ModuleCoverage', 'ModuleCoverage'],
  ['CoverageMap', 'CoverageMap'],
  ['ArchivedCoverage', 'ArchivedCoverage'],
  // OF-BLD-015 §7.2 — what a module's read tool returns.
  ['ModuleRow', 'ModuleRow'],
  // OF-BLD-015 §7.3, §7.4 — the audit log and the proposals.
  ['AuditEntry', 'AuditEntry'],
  ['Proposal', 'Proposal'],
  ['ProposalAction', 'ProposalAction'],
  // OF-BLD-012 §2.5 — Intake. The service's FetchedSection is the browser's
  // PaperSection; the rest keep their names on both sides.
  ['FetchedSection', 'PaperSection'],
  ['FetchLicense', 'FetchLicense'],
  ['FetchResult', 'FetchResult'],
  ['IntakeStatus', 'IntakeStatus'],
  ['OverlayPaper', 'OverlayPaper'],
  ['Overlay', 'Overlay'],
  // OF-BLD-012 §2.5 — extraction and review. The service's names differ
  // from the browser's where the browser already had one.
  ['Quantity', 'Quantity'],
  ['Range', 'Range'],
  ['Candidate', 'Candidate'],
  ['ExtractRunResult', 'RunResult'],
  ['ExtractRunFalsePositive', 'RunFalsePositive'],
  ['ExtractRun', 'RunOutput'],
  ['ReviewDecision', 'ReviewDecision'],
  ['DecisionCheck', 'DecisionCheck'],
  ['AuditEvent', 'AuditEvent'],
  ['DroppedCandidate', 'DroppedCandidate'],
  ['BioRepo', 'BioRepo'],
  ['ExtractResponse', 'ExtractResponse'],
  // OF-BLD-013 §1.2 — Guild's ledger.
  ['GuildPerson', 'GuildPerson'],
  ['EvidenceSource', 'EvidenceSource'],
  ['GuildEvidence', 'GuildEvidence'],
  ['GuildWithdrawal', 'GuildWithdrawal'],
  ['Guild', 'Guild'],
  ['GuildPolicy', 'GuildPolicy'],
  // OF-BLD-013 §4 — Practice.
  ['PracticeStepRef', 'PracticeStepRef'],
  ['PracticeSource', 'PracticeSource'],
  ['PracticeValue', 'PracticeValue'],
  ['PracticeScenario', 'PracticeScenario'],
  ['PracticeDepositionEntry', 'PracticeDepositionEntry'],
  ['PracticeDepositionObservation', 'PracticeDepositionObservation'],
  ['PracticeDeposition', 'PracticeDeposition'],
  ['PracticeDraftRequest', 'PracticeDraftRequest'],
  ['PracticeTurn', 'PracticeTurn'],
  ['PracticeObservation', 'PracticeObservation'],
  ['PracticeSession', 'PracticeSession'],
  ['PracticeTurnRequest', 'PracticeTurnRequest'],
  ['Practice', 'Practice'],
  // OF-BLD-013 §5 — Checks.
  ['CheckReason', 'CheckReason'],
  ['CheckCriterion', 'CheckCriterion'],
  ['CheckBrief', 'CheckBrief'],
  ['CheckResult', 'CheckResult'],
  ['Check', 'Check'],
  ['Checks', 'Checks'],
  ['CheckRequest', 'CheckRequest'],
  ['CheckSchedule', 'CheckSchedule'],
  ['CheckDismiss', 'CheckDismiss'],
  ['CheckNote', 'CheckNote'],
  ['CheckRecord', 'CheckRecord'],
  // OF-BLD-014 §3.1 — computed values and their basis.
  ['BasisSource', 'BasisSource'],
  ['BasisInput', 'BasisInput'],
  ['ComputedBasis', 'ComputedBasis'],
  ['Evidence', 'Evidence'],
  // OF-BLD-014 §3.2 — the artifact store.
  ['Artifact', 'Artifact'],
  ['ReplayDifference', 'ReplayDifference'],
  ['ReplayResult', 'ReplayResult'],
  // OF-BLD-014 §3.4 — the tool registry.
  ['ToolInfo', 'ToolInfo'],
  ['ToolResult', 'ToolResult'],
  ['Prediction', 'Prediction'],
  ['Measure', 'Measure'],
  ['DraftItem', 'DraftItem'],
  ['DraftMeasure', 'DraftMeasure'],
  ['RunbookDraft', 'RunbookDraft'],
  // OF-BLD-014 §4.1 — passages.
  ['Passage', 'Passage'],
  // OF-BLD-014 §5.1 — a plan cites sentences and computed values.
  ['PassageRef', 'PassageRef'],
  // OF-BLD-014 §6.3 — geneOS's shelf and its results.
  ['GeneosModelInfo', 'GeneosModelInfo'],
  ['GeneosResult', 'GeneosResult'],
  // OF-BLD-014 §7.2 — fermOS's fits.
  ['FermosPoint', 'FermosPoint'],
  ['FermosSeries', 'FermosSeries'],
  ['FermosFitRequest', 'FermosFitRequest'],
  ['FitParam', 'FitParam'],
  ['GrowthFit', 'GrowthFit'],
  ['SeriesFitQuality', 'SeriesFitQuality'],
  ['KineticFit', 'KineticFit'],
  ['FermosFitResponse', 'FermosFitResponse'],
  ['StartValues', 'StartValues'],
  ['ForecastRequest', 'ForecastRequest'],
  ['Band', 'Band'],
  ['Interval', 'Interval'],
  ['ForecastResult', 'ForecastResult'],
  ['BoundRecord', 'BoundRecord'],
  ['ScenarioInput', 'ScenarioInput'],
  ['InputAssumption', 'InputAssumption'],
  ['ProformaScenarioInfo', 'ProformaScenarioInfo'],
  ['ProformaRunRequest', 'ProformaRunRequest'],
  ['HistogramBin', 'HistogramBin'],
  ['InputSensitivity', 'InputSensitivity'],
  ['ProformaGrid', 'ProformaGrid'],
  ['ProformaRunResult', 'ProformaRunResult'],
  // OF-BLD-019 §5.1 — a fermOS fit feeds the fermenter.
  ['FitFeed', 'FitFeed'],
  ['FermosFitInfo', 'FermosFitInfo'],
  // OF-BLD-019 §5.2 — a scenario's yield read against the geneOS ceiling.
  ['CeilingRow', 'CeilingRow'],
  ['CeilingCheck', 'CeilingCheck'],
  // OF-BLD-019 §2.1 — the shelf of flowsheets and the run's tables.
  ['FlowsheetInput', 'FlowsheetInput'],
  ['FlowsheetInfo', 'FlowsheetInfo'],
  ['StreamRow', 'StreamRow'],
  ['UnitRow', 'UnitRow'],
  ['UtilityDuties', 'UtilityDuties'],
  ['TeaLine', 'TeaLine'],
  ['TeaBreakdown', 'TeaBreakdown'],
  ['ProformaTables', 'ProformaTables'],
  // OF-BLD-019 §2.2 — a reference biorefinery's run and its package's test.
  ['RegressionValue', 'RegressionValue'],
  ['PackageRegression', 'PackageRegression'],
  ['RegressionCheck', 'RegressionCheck'],
  ['ProformaReference', 'ProformaReference'],
  ['TraceStep', 'TraceStep'],
  // A follow-up carries its conversation's earlier turns in words.
  ['PriorTurn', 'PriorTurn'],
  ['AskRequest', 'AskRequest'],
  // OF-BLD-016 §2.1 — a program is data.
  ['Program', 'Program'],
  // OF-BLD-019 §4.1 — pureOS reads the train from the run Proforma priced.
  ['TrainUnit', 'TrainUnit'],
  ['Train', 'Train'],
  ['TrainSummary', 'TrainSummary'],
  // OF-BLD-019 §4.2 — thermosteam answers property questions.
  ['ThermoPropsRequest', 'ThermoPropsRequest'],
  ['ThermoProps', 'ThermoProps'],
  // OF-BLD-020 §7.1 — a product's properties: ProtParam on its sequence, its volatility by thermosteam.
  ['ProductPropertyRequest', 'ProductPropertyRequest'],
  ['ProtParam', 'ProtParam'],
  ['Volatility', 'Volatility'],
  // OF-BLD-020 §2.1 — one parameter panel: a parameter declared once,
  // resolved with its source, and a person's change a named assumption.
  ['ParameterSpec', 'ParameterSpec'],
  ['ParameterValue', 'ParameterValue'],
  ['Override', 'Override'],
  ['ParamScope', 'ParamScope'],
  ['ParamResolveRequest', 'ParamResolveRequest'],
  ['ParamResolveResult', 'ParamResolveResult'],
  // OF-BLD-020 §4.1 — fermOS's vessel, designed by BioSTEAM in the worker.
  ['VesselRequest', 'VesselRequest'],
  ['VesselDesignRow', 'VesselDesignRow'],
  ['VesselOxygen', 'VesselOxygen'],
  ['VesselHeat', 'VesselHeat'],
  ['VesselCostItem', 'VesselCostItem'],
  ['VesselCost', 'VesselCost'],
  ['VesselDesign', 'VesselDesign'],
  ['VesselSummary', 'VesselSummary'],
  // OF-BLD-020 §3.1 — fermOS's model families, and what a simulation keeps.
  ['FamilyInfo', 'FamilyInfo'],
  ['SimulationRequest', 'SimulationRequest'],
  ['OxygenUptake', 'OxygenUptake'],
  ['MassBalance', 'MassBalance'],
  ['SimulationCeilingRow', 'SimulationCeilingRow'],
  ['SimulationCeiling', 'SimulationCeiling'],
  ['SteadyState', 'SteadyState'],
  ['SimulationResult', 'SimulationResult'],
  ['SimulationSummary', 'SimulationSummary'],
  // OF-BLD-020 §3.2 — a family's parameters bound from a fit, the records, a kept simulation.
  ['FermosBinding', 'FermosBinding'],
  // OF-BLD-020 §6.2 — a kept simulation's broth at an hour, read from its kept series.
  ['HarvestState', 'HarvestState'],
  ['FermosHarvest', 'FermosHarvest'],
  // OF-BLD-020 §5.1 — pureOS's unit catalogue: each entry a BioSTEAM class
  // or an in-house unit, with its parameters and their sources.
  ['UnitPort', 'UnitPort'],
  ['NotOffered', 'NotOffered'],
  ['UnitNeed', 'UnitNeed'],
  ['UnitType', 'UnitType'],
  ['UnitDefault', 'UnitDefault'],
  ['UnitParamMap', 'UnitParamMap'],
  ['UnitSpecs', 'UnitSpecs'],
  // OF-BLD-020 §5.2 — a train is data; the worker runs it; one artifact keeps it.
  ['TrainParam', 'TrainParam'],
  ['TrainInlet', 'TrainInlet'],
  ['TrainUnitReadFrom', 'TrainUnitReadFrom'],
  ['TrainUnitSpec', 'TrainUnitSpec'],
  ['TrainSpec', 'TrainSpec'],
  ['TrainValidation', 'TrainValidation'],
  ['TrainRunRequest', 'TrainRunRequest'],
  ['StreamImpurity', 'StreamImpurity'],
  ['StreamPurity', 'StreamPurity'],
  ['TrainPurity', 'TrainPurity'],
  ['TrainUnitCost', 'TrainUnitCost'],
  ['TrainInletRead', 'TrainInletRead'],
  ['TrainUnitParameters', 'TrainUnitParameters'],
  ['TrainRun', 'TrainRun'],
  // OF-BLD-020 §5.4 — a train a model built, kept on the service.
  ['KeptTrain', 'KeptTrain'],
  ['KeptTrains', 'KeptTrains'],
  // OF-BLD-020 §7.2 — a train proposed by rules that each name the property they read.
  ['ProposeRequest', 'ProposeRequest'],
  ['ProposalReason', 'ProposalReason'],
  ['ProposalMissing', 'ProposalMissing'],
  ['TrainProposal', 'TrainProposal'],
  // OF-BLD-020 §5.3 — a run's units read into a train for the Builder.
  ['TrainFromRunRequest', 'TrainFromRunRequest'],
  ['TrainUnmapped', 'TrainUnmapped'],
  ['TrainFromRun', 'TrainFromRun'],
];

let compared = 0;
for (const [pyName, tsName] of PAIRS) {
  const a = pydanticFields(py, pyName);
  const b = tsFields(ts, tsName);
  if (!a || !b) continue;
  compared += a.size;
  for (const f of a) {
    if (!b.has(f)) fail(`${pyName}.${f} exists in models.py but not in types.ts ${tsName}`);
  }
  for (const f of b) {
    if (!a.has(f)) fail(`${tsName}.${f} exists in types.ts but not in models.py ${pyName}`);
  }
}

// ── the provenance vocabulary ──────────────────────────────────────────
// Both sides must know the same classes. A class the service can emit and the
// browser has no tick for renders as a blank, which reads as "no provenance"
// rather than as "a provenance this build does not understand".
const pyProv = new Set(
  [...(py.split('Provenance = Literal[')[1]?.split(']')[0] ?? '').matchAll(/"([^"]+)"/g)].map(
    (m) => m[1],
  ),
);
// Comments are stripped first: the union is documented inline and one of those
// comments contains an apostrophe ("somebody else's paper"), which a naive
// quote match reads as the start of a member.
// Stripped BEFORE the union is cut at its `;`, so a semicolon inside a
// member's comment cannot end the union early and drop the members after it.
const tsProvSource = (
  ts.split('export type Provenance =')[1]?.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '') ?? ''
).split(';')[0];
const tsProv = new Set([...tsProvSource.matchAll(/'([^']+)'/g)].map((m) => m[1]));
for (const p of pyProv) if (!tsProv.has(p)) fail(`provenance '${p}' is in models.py but not types.ts`);
for (const p of tsProv) if (!pyProv.has(p)) fail(`provenance '${p}' is in types.ts but not models.py`);

// PROVENANCE_ORDER is the ranking `weakest_provenance` walks. A class missing
// from it would sort as unknown-and-weakest without anybody saying so.
const order = [
  ...(py.split('PROVENANCE_ORDER: list[str] = [')[1]?.split(']')[0] ?? '').matchAll(/"([^"]+)"/g),
].map((m) => m[1]);
for (const p of pyProv) {
  if (!order.includes(p)) fail(`provenance '${p}' is in the union but missing from PROVENANCE_ORDER`);
}
if (order[0] !== 'measured') fail(`PROVENANCE_ORDER starts at '${order[0]}', expected 'measured' as the strongest`);
if (order.indexOf('gold') <= order.indexOf('measured')) fail('PROVENANCE_ORDER: measured must outrank gold');
if (order.indexOf('industry-estimate') < order.indexOf('unverified')) {
  fail('PROVENANCE_ORDER: an industry estimate must not outrank an unverified extraction');
}

// OF-BLD-014 §3.1, E.4 — one ranking. PROVENANCE_RANK in src/store.ts is the
// browser's copy; it must hold the same members in the same order, so a value
// the service calls weaker never draws as stronger. Membership alone let the
// two disagree about `user` and `unverified` until §3.1.
const store = readFileSync('src/store.ts', 'utf8');
const rankBody = store.split('export const PROVENANCE_RANK: Record<Provenance, number> = {')[1]?.split('};')[0];
if (rankBody === undefined) {
  fail('src/store.ts: no PROVENANCE_RANK');
} else {
  const rank = [...rankBody.replace(/\/\/.*$/gm, '').matchAll(/^\s*'?([a-z-]+)'?\s*:\s*(\d+)\s*,?\s*$/gm)]
    .map((m) => [m[1], Number(m[2])])
    .sort((x, y) => x[1] - y[1]);
  const tsOrder = rank.map(([p]) => p);
  const ranks = rank.map(([, n]) => n);
  if (new Set(ranks).size !== ranks.length) fail(`PROVENANCE_RANK gives two classes one rank: ${ranks.join(', ')}`);
  if (tsOrder.join(' ') !== order.join(' ')) {
    fail(`PROVENANCE_RANK orders ${tsOrder.join(' > ')}; PROVENANCE_ORDER orders ${order.join(' > ')}`);
  }
}

console.log('\nopenFerment AnswerPlan shape check');
console.log('──────────────────────────────────');
console.log(`  fields        ${compared} compared across ${PAIRS.length} types, Python ↔ TypeScript`);
console.log(`  provenance    ${pyProv.size} classes agree, ranked ${order.length} deep in one order`);

if (errors.length) {
  console.error(`\n✗ ${errors.length} error(s):`);
  for (const e of errors) console.error(`  - ${e}`);
  process.exit(1);
}
console.log('\n✓ The plan shape is the same on both sides.');
