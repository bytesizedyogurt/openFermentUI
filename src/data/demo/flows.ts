// openFerment demo suite — the six archetype flows.
//
// Typed as the existing ChatFlow with two backward-compatible additions
// (OF-DEMO-002 §7): `deliverableId` and `handoffs`. Each answer ends with a
// deliverable card that deep-links to the rendered artifact. Do not try to
// render a capacity screen inside a chat bubble.
//
// A citation chip resolves Accession, patent-family, organism and run ids here, in
// addition to the paper and record ids the casein flows use.
import type { ChatFlow } from '../types';

export interface DemoChatFlow extends ChatFlow {
  deliverableId?: string;
  handoffs?: string[];
}

export const ARCHETYPE_FLOWS: DemoChatFlow[] = [
  // ══ AR1 — parameter gap ═══════════════════════════════════════════
  {
    id: 'AR1',
    deliverableId: 'DLV-AR1-001',
    triggers: [
      'which factor combinations are already covered',
      'what process space is unexplored for lysine',
      'i have twelve runs before a review',
      'show me the gap map',
      'which conditions are excluded including unpublished failures',
    ],
    plan: [
      'Parse the fixed constraints — organism, product, vessel, current operating point',
      'Retrieve every Accession on the six process fields',
      'Separate explored, excluded and unexplored regions per factor',
      'Check exclusions against patent working examples, including comparative ones',
      'Check the Ledger for runs that must not enter the map',
      'Propose a twelve-run block that lands entirely in open space',
    ],
    toolCalls: [
      { name: 'repo.accessionsByField', args: { fields: ['temperature', 'ph', 'dissolved_oxygen', 'mu_setpoint', 'co2_overlay', 'biotin_conc'], organism: 'ORG-CGL-02' }, durationMs: 1180 },
      { name: 'intake.patentExamples', args: { families: ['PF-001', 'PF-002', 'PF-003'], comparativeOnly: false }, durationMs: 1420,
        retrieval: [
          { paperId: 'PF-002', sectionId: 'Example 7', score: 0.94, snippet: 'titer of 71 g/L against 96 g/L for the unshifted control' },
          { paperId: 'PF-001', sectionId: 'Example 5', score: 0.91, snippet: 'lactate accumulated to 6.8 g/L notwithstanding increased agitation' },
          { paperId: 'PF-002', sectionId: 'Example 9', score: 0.88, snippet: 'growth arrested at 40 h' },
        ] },
      { name: 'ledger.runsForOrganism', args: { organismId: 'ORG-CGL-02', includeFlagged: true }, durationMs: 640 },
      { name: 'audit.singleSourceExclusions', args: { deliverable: 'factor-map' }, durationMs: 480 },
    ],
    answerMd: `Six factors, and the honest summary is that the open space is smaller than it looks and it is all in one corner.

**What the literature covers.** Temperature is well sampled at 30 and 33 °C and nowhere in between. pH is sampled at four points. Dissolved oxygen is the densest factor, with Accessions at 5, 10, 15, 20 and 30 % — and nothing at all between 12 and 18 %, which is the interesting part.

**What is excluded, and by what.** Two of the five exclusions come from patent working examples rather than from journals. [[OF-A-00140]] is a comparative example at 37 °C showing a 26 % titer loss, and [[OF-A-00139]] is a comparative example at 15 % DO where lactate reached 6.8 g/L despite the agitation being raised to compensate. Neither would ever appear in a journal, because neither is a result anyone wanted. Comparative examples exist to demonstrate non-obviousness, which means the applicant is motivated to report the failure accurately.

**Where the exclusions are weak.** The 37 °C boundary rests on [[OF-A-00140]] alone. The 15 % DO boundary rests on [[OF-A-00139]] alone, and that example does not state the cell density at which it was measured — which matters, because oxygen demand scales with biomass and a boundary measured at 60 g/L says nothing about the same setpoint at 20 g/L. Both carry single-source markers on the factor band.

**One run excluded from the map.** [[RUN-047]] deposited [[OF-A-00147]] at 39.4 g/L. It is held, because [[OF-A-00150]] shows carbon balance closure at 91.8 % against a five-run basis of 96.2 %. The run produced material and it is not comparable, and the gap map shows it greyed rather than dropping it silently.

**FTO on two factors.** [[PF-001]] recites 20–45 % dissolved oxygen and [[PF-002]] recites a 32–36 °C production phase. Neither family ever entered Rwanda, ARIPO, Kenya or South Africa, so neither constrains work here — and both constrain any partner operating in the US, EP, CN, JP or KR. The factor bands render that as a jurisdiction-conditional flag rather than as a blanket warning.

**The twelve runs.** A 2³ factorial on dissolved oxygen at 14 and 18 %, bicarbonate at 0 and 40 mM, and μ at 0.10 and 0.15 h⁻¹, plus two centre points and two confirmation runs held back to the end. Every corner lands in unexplored space. The centre replicate is not optional — without it the block has no error term and every effect is uninterpretable.

**What should be published.** The whole 12–18 % dissolved oxygen region with bicarbonate support. It is open, it is where the answer probably is, and it is exactly the region an incumbent would file on next.`,
    followups: [
      'flow:AR6|Why was RUN-047 excluded?',
      'flow:AR3|Can my plant even run this process?',
      'chip:DLV-AR1-001|Open the gap map',
    ],
  },

  // ══ AR2 — pathway selection ═══════════════════════════════════════
  {
    id: 'AR2',
    deliverableId: 'DLV-AR2-001',
    triggers: [
      'compare the three routes to 3-hp',
      'which pathway has the most open patent surface',
      'malonyl-coa versus beta-alanine versus glycerol',
      'which enzyme steps are enclosed',
      'route selection for 3-hydroxypropionic acid',
    ],
    plan: [
      'Resolve the product and enumerate routes at enzyme-step resolution',
      'Retrieve theoretical yields, achieved titers and cofactor demand per route',
      'Map every step onto claim status by jurisdiction',
      'Compute expiry countdowns against the frozen demo date',
      'Rank on open surface rather than on performance alone',
    ],
    toolCalls: [
      { name: 'geneos.routes', args: { productId: '3-HP', resolution: 'enzyme-step' }, durationMs: 1340 },
      { name: 'repo.accessionsByField', args: { fields: ['theoretical_yield', 'titer', 'cofactor_demand', 'our'], productId: '3-HP' }, durationMs: 980 },
      { name: 'audit.claimOverlay', args: { routeIds: ['RTE-3HP-MCR', 'RTE-3HP-BAL', 'RTE-3HP-GLY'], jurisdictions: ['US', 'EP', 'CN', 'JP', 'KR', 'BR', 'IN', 'RW'] }, durationMs: 1520,
        retrieval: [
          { paperId: 'PF-004', sectionId: 'Claim 1', score: 0.93, snippet: 'separately expressed N-terminal and C-terminal fragments' },
          { paperId: 'PF-008', sectionId: 'Claim 1', score: 0.9, snippet: 'aspartate 1-decarboxylase comprising a specified substitution set' },
          { paperId: 'PF-006', sectionId: 'Claim 1', score: 0.87, snippet: 'dehydration of glycerol by a B12-dependent dehydratase' },
        ] },
    ],
    answerMd: `The biochemistry ranks them one way and the expiry dates rank them the other way, and the second ranking is the one that decides.

**On yield ceiling the β-alanine route wins.** [[OF-A-00206]] puts it at 1.24 mol/mol on glucose, above unity because the route fixes CO₂ on the way in at phosphoenolpyruvate. It also has the lowest cofactor demand at one NADPH per product ([[OF-A-00207]]) against two for the malonyl-CoA route ([[OF-A-00202]]).

**On achieved titer the glycerol route wins, and by a lot.** [[OF-A-00218]] records 71.9 g/L on crude glycerol — roughly double the malonyl-CoA route's 40.6 g/L ([[OF-A-00203]]) and more than double β-alanine's 31.2 g/L ([[OF-A-00208]]). That best-in-class number comes from a patent working example, not a journal. A corpus that excluded patent literature would lose the best data point in the field.

**Then the overlay reverses everything.**

| Route | Steps | Enclosed | Expiring | Earliest relief |
|---|---|---|---|---|
| Malonyl-CoA | 3 | 3 | 0 | 2033 |
| β-alanine | 3 | 3 | 0 | 2036, and one step to 2040 |
| Glycerol | 2 | 0 | 2 | **2030** |

[[PF-005]] claims the β-alanine route as a whole rather than one enzyme, which is the hardest shape to design around. Worse, [[PF-008]] separately claims the decarboxylase variant that fixes mechanism-based inactivation, filed in 2020 and running to 2040. The wild-type enzyme is free and the version that makes the route industrially viable is not — that is the pattern that catches programmes late, because the route screens clean at pathway level and fails at one substitution.

**The glycerol route sits entirely under [[PF-006]], expiring 2030 in all three jurisdictions it ever entered.** Two steps, no third-party variant claim, highest titer in the pool, and a substrate one oxidation state from the product, which is why [[OF-A-00211]] normalises to 0.978 g/g on a mass basis.

**The two things that argue against it.** Coenzyme B12 must be fed, and [[OF-A-00212]] puts that at 340 USD per tonne of product with a comparative example establishing it is not optional. Using [[ORG-PDN-01]], which makes its own B12, removes the cost line and costs you genetic tractability. Separately, 3-HPA is toxic at 1.11 g/L ([[OF-A-00214]]) so the oxidation has to keep pace with the dehydration or the route poisons itself.

**One thing nobody in this comparison reports.** Producing above the pKa costs 210 USD per tonne in neutralisation and acid springing ([[OF-A-00215]]). It is a downstream number in a set of upstream papers, and it is roughly two thirds of the B12 penalty everyone does report. [[OF-A-00216]] shows a yeast host producing at pH 3.5 and avoiding it entirely, at a third of the titer — and [[PF-007]] claims that operating region outright in the US, EP and Brazil.

**Recommendation.** Glycerol route, second-best on ceiling and best on freedom. And publish now on the post-2030 improvement space, because the moment that family lapses is the moment someone files improvement patents over the top of it.`,
    followups: [
      'flow:AR5|What if I do not know my target yet?',
      'flow:AR3|Where could I actually build this?',
      'chip:DLV-AR2-001|Open the route comparison',
    ],
  },

  // ══ AR3 — capacity-first ══════════════════════════════════════════
  {
    id: 'AR3',
    deliverableId: 'DLV-AR3-001',
    triggers: [
      'what can i make with these two vessels',
      'find me a product for this plant',
      'capacity screen for my equipment',
      'what fits this envelope and is not patented here',
      'two 5 m3 vessels what should i produce',
    ],
    plan: [
      'Express the plant as a supply envelope on seven axes',
      'Compute kLa, the OTR ceiling and the cooling ceiling from first principles',
      'Express every candidate as a demand vector on the same axes',
      'Match, and record which axis binds for each failure',
      'Overlay claim status for this jurisdiction only',
      'Rank survivors by import displacement value',
    ],
    toolCalls: [
      { name: 'fermos.envelope', args: { plantId: 'PLT-KGL-01' }, durationMs: 1090 },
      { name: 'fermos.transport', args: { correlation: 'vantRiet', powerPerVolume: 1500, vvm: 1.0, hOverD: 2.0, volumeM3: 5 }, durationMs: 870 },
      { name: 'proforma.candidates', args: { feedstocksWithinKm: 200, jurisdiction: 'RW' }, durationMs: 1260 },
      { name: 'audit.jurisdictionScan', args: { jurisdiction: 'RW', families: 'all' }, durationMs: 1410 },
      { name: 'proforma.tradeMatch', args: { hsCodes: ['2922.41', '2918.11', '2918.14', '3507.90', '2102.20', '3101.00', '2905.44'] }, durationMs: 720 },
    ],
    answerMd: `Start with the plant, because it is more constrained than it looks.

**Oxygen transfer.** At 1,500 W/m³ and 1 VVM in a 5 m³ vessel with H/D = 2, superficial gas velocity is 0.049 m/s and the clean-water correlation gives 385 h⁻¹ ([[OF-A-00307]]). Applying a broth factor of 0.46 for a high-solids broth with antifoam gives an effective **177 h⁻¹** ([[OF-A-00308]]). At 30 °C and a 20 % setpoint that is an OTR ceiling of **33.2 mmol L⁻¹ h⁻¹**, rising to **49.7** with the head at 1.5 bar absolute.

**Cooling.** 80 kW installed ([[OF-A-00324]]), less 15 kW of agitation heat across two vessels, leaves 65 kW for metabolic heat. At 460 kJ per mole of O₂ that is an OUR ceiling of **50.9 mmol L⁻¹ h⁻¹**.

**The ordering matters and it is easy to get backwards.** At one atmosphere, transfer fails 17 mmol before cooling does, so cooling never appears as the binding axis on this screen. That is not because cooling is comfortable — it is because oxygen never gets into the broth in the first place. Relieve transfer with overpressure and the two ceilings land at 49.7 and 50.9, 1.2 mmol apart, and there is no operating point where one is comfortable and the other is not. Ambient here is 26 °C ([[OF-A-00325]]), so against a 30 °C broth there is 4 K of driving force to tower water and the chiller is doing all of the work.

**Eight candidates fail on oxygen transfer alone.** Single-cell protein at 165 mmol L⁻¹ h⁻¹ ([[OF-A-00320]]), citric acid at 145 ([[OF-A-00321]]), lysine at 118 ([[OF-A-00121]]), itaconic acid at 95, baker's yeast at 88 ([[OF-A-00322]]), cellulase at 72, α-amylase at 48, spent-grain yeast extract at 42. Citric acid is the painful one — it is the largest import line in the survey at 620 t/yr, and a transient oxygen interruption does not slow citrate formation, it stops it. With an intermittent grid that is a different category of risk from a yield penalty.

**Three fail somewhere else.** Xanthan on installed power — [[OF-A-00309]] records 3,200 mPa·s at 10 s⁻¹, so the Rushton train cannot move the broth and adding power adds heat. 2,3-butanediol and acetic acid on separation, because both need a distillation column and a column is a different plant rather than a line item.

**Seven survive.** Thermophilic lactate, rhizobial inoculant, starter cultures, succinic acid, coffee-pulp hydrolysate, biofungicide and xylitol — plus lysine once it is de-rated.

**Lysine fails at the published operating point and survives de-rated.** [[OF-A-00121]] puts peak OUR at 118 mmol L⁻¹ h⁻¹ at 62 g/L dry weight, which is more than double either ceiling. Taking the head to 1.5 bara, dropping the feed setpoint to μ = 0.10 per [[OF-A-00124]], and de-rating final biomass to 20 g/L brings peak OUR to 48 ([[OF-A-00152]]). That fits, by 1.7 mmol on transfer and by 4.6 % on cooling. Volumetric productivity falls about 45 %.

**Recommendation, with the risk named.** Feed-grade lysine HCl. 340 t/yr enters the region at 2,100 USD/t CIF ([[OF-A-00310]], [[OF-A-00311]]), cassava starch is 60 km away at 380 USD/t ([[OF-A-00301]]), and [[PF-001]], [[PF-002]] and [[PF-003]] never entered Rwanda, ARIPO, Kenya or South Africa. The risk is that 4.6 % of cooling headroom is not a margin, it is a coincidence, and a hot week eats it.

**The candidate that would be the safe answer.** Thermophilic lactic acid. [[OF-A-00305]] has [[ORG-BCG-01]] running at 52 °C, which turns 4 K of driving force into 24 K and removes the chiller from the process entirely. It fits every axis with room to spare — and [[PF-012]] is enclosed in the US, China and Brazil, so it is free to make and sell across the EAC and blocked for export to the three largest buyers. That is a market failure rather than a production failure, and the distinction is worth making explicitly.

**What should be published.** The de-rated lysine operating region — elevated head pressure with reduced μ and de-rated biomass. It is the process region that makes under-specified plants viable, which makes it the region an incumbent would most want to claim.`,
    followups: [
      'flow:AR1|Where did the μ = 0.10 number come from?',
      'flow:AR4|What if I were building from scratch?',
      'chip:DLV-AR3-001|Open the capacity screen',
    ],
  },

  // ══ AR4 — greenfield ══════════════════════════════════════════════
  {
    id: 'AR4',
    deliverableId: 'DLV-AR4-001',
    triggers: [
      'design a plant for 400000 tonnes of bagasse',
      'greenfield lignocellulosic conversion',
      'what should i build for sugarcane bagasse',
      'capex against scale for a biorefinery',
      'highest return pathway for bagasse',
    ],
    plan: [
      'Establish feedstock composition and the fermentable fraction',
      'Compare pretreatments on sugar yield, inhibitor load and capital intensity',
      'Match inhibitor profiles against organism tolerance',
      'Select products for each sugar stream',
      'Size equipment, scale capital by the six-tenths rule, run sensitivity',
    ],
    toolCalls: [
      { name: 'repo.accessionsByField', args: { fields: ['purity', 'yield_product_substrate', 'byproduct_conc', 'inhibitor_tolerance'], feedstock: 'sugarcane bagasse' }, durationMs: 1210 },
      { name: 'geneos.toleranceMatch', args: { inhibitors: ['furfural', 'HMF'], organismIds: ['ORG-BCG-01', 'ORG-SCE-01', 'ORG-RTO-01'] }, durationMs: 890 },
      { name: 'proforma.capexCurve', args: { anchorAccessionId: 'OF-A-00416', exponent: 0.6, scales: [8000, 18000, 22000] }, durationMs: 1040 },
      { name: 'audit.claimOverlay', args: { steps: ['pretreatment', 'fermentation', 'polyol'], jurisdictions: ['EP', 'US', 'BR', 'CN', 'RW'] }, durationMs: 1180 },
    ],
    answerMd: `400,000 t/yr as received is roughly 200,000 t/yr dry, and it is 42 % cellulose, 27 % hemicellulose and 21 % lignin ([[OF-A-00401]], [[OF-A-00402]], [[OF-A-00403]]). The pentose fraction is over a quarter of the feedstock, which is too much to keep burning.

**The pretreatment choice decides both the capital cost and the patent position, and they point opposite ways.** Organosolv gives the best sugar yield at 0.72 g/g ([[OF-A-00409]]) and the lowest furfural at 0.6 g/L ([[OF-A-00412]]) — and it costs 1.9× the dilute-acid case at equal throughput ([[OF-A-00413]]) and is claimed by [[PF-014]] in EP, US and Brazil. Dilute acid gives 0.61 g/g ([[OF-A-00407]]) with furfural at 2.4 g/L ([[OF-A-00411]]), which sits above the 1.9 g/L tolerance of the chosen organism ([[OF-A-00404]]).

That last mismatch is the design problem. The usual answer is a detoxification unit. The better answer is to run the pretreatment at lower severity and accept a lower sugar yield, because a detoxification step costs capital, costs sugar, and never appears in the pretreatment paper that quoted the yield.

**Three concepts.**

The recommended one splits the streams. Pentose liquor to xylitol, hexose to thermophilic lactate with [[ORG-BCG-01]] at 52 °C ([[OF-A-00406]], [[OF-A-00305]]). 18,000 t/yr, 58.6 M USD installed at AACE Class 5, breakeven at 11,200 t/yr. Two things make it work: xylitol carries a much higher price than lactate ([[OF-A-00417]] against [[OF-A-00418]]), and [[PF-013]] has expired in the US and EP, so the high-value half of the concept is unencumbered. The 52 °C fermentation also needs no chiller, which is the same finding the capacity screen reached from the other direction.

The organosolv single-stream concept reaches 22,000 t/yr on better sugar recovery and costs 66.8 M USD, and its NPV is dominated by solvent recovery efficiency at ±52 %. A single parameter carrying half the sensitivity is not a design, it is a bet.

The minimum-viable concept keeps burning the pentose and does 8,000 t/yr for 19.4 M USD at Class 4 accuracy. It concedes 27 % of the feedstock and it is the only one of the three that a first-time developer could finance.

**What moves NPV in the recommended case.** Xylitol price at ±41 %, sugar yield at ±34 %, enzyme loading at ±20 % ([[OF-A-00415]]), lactate price at ±16 %, installed capital at ±13 %. Capital is fifth, which is worth stating because capital is what everyone argues about.

**A note on the cost basis.** [[OF-A-00419]] and [[OF-A-00418]] are the same quantity from European and US cost bases and they agree within 1.5 % after conversion at the fixed corpus rate of 1.08. That agreement is invisible until the units are closed.

**What should be published.** Two-stream conversion at reduced pretreatment severity matched to organism tolerance. Nobody has claimed the combination, and it is the kind of process-level integration that a well-resourced incumbent files on the moment it appears in a conference abstract.`,
    followups: [
      'flow:AR3|Compare this to using existing equipment',
      'flow:AR2|How do I pick a product for the C5 stream?',
      'chip:DLV-AR4-001|Open the facility concepts',
    ],
  },

  // ══ AR5 — end-state translation ═══════════════════════════════════
  {
    id: 'AR5',
    deliverableId: 'DLV-AR5-001',
    handoffs: ['AR2'],
    triggers: [
      'i want to make a burger indistinguishable from beef',
      'where do i start with a meat analogue',
      'precision fermentation burger where do i begin',
      'how do i make something that tastes like beef',
      'decompose this consumer product for me',
    ],
    plan: [
      'Reject the question as posed — the target is not a molecule',
      'Decompose into independently solvable sub-problems',
      'For each, identify the molecular target and candidate hosts',
      'Rate patent density and technical maturity per branch',
      'Recommend build, license or avoid, and name the follow-on queries',
    ],
    toolCalls: [
      { name: 'postdoc.decompose', args: { endState: 'beef-indistinguishable patty', depth: 2 }, durationMs: 1580 },
      { name: 'repo.accessionsByField', args: { fields: ['purity', 'temperature', 'titer'], productIds: ['heme protein', 'structured fat', 'texturised protein'] }, durationMs: 1120 },
      { name: 'audit.densityScan', args: { branches: ['heme', 'fat-phase', 'fibrous-matrix'], jurisdictions: 'all' }, durationMs: 1470,
        retrieval: [
          { paperId: 'PF-009', sectionId: 'Claim 1', score: 0.95, snippet: 'a meat substitute comprising a recombinant heme-containing protein' },
          { paperId: 'PF-010', sectionId: 'Claim 1', score: 0.82, snippet: 'a fat composition having a stated solid fat content' },
          { paperId: 'PF-011', sectionId: 'Claim 1', score: 0.86, snippet: 'applying a defined shear field to a hydrated protein mass' },
        ] },
    ],
    answerMd: `A burger is not a fermentation target, so the first useful thing I can do is refuse the question as posed and restructure it.

It decomposes into three independent problems with three different organisms, three different processes, and — the actual finding — three dramatically different patent landscapes.

**Branch one: the heme carrier.** Flavour chemistry and the raw-to-cooked colour transition. Target is a recombinant globin at 0.8 % of formulation mass ([[OF-A-00501]]), because sensory discrimination is lost below that. Technically solved: [[OF-A-00502]] records 3.6 g/L secreted from [[ORG-KPH-01]], and the quality attribute is heme occupancy at 62 % ([[OF-A-00503]]) rather than titer, since apoprotein without its cofactor does nothing. Commercially closed: [[PF-009]] covers both the composition and the production method across eight jurisdictions, and the concentration you need sits inside the recited range. **Avoid or license.**

**Branch two: the structured fat phase.** Beef fat melts across 28–45 °C ([[OF-A-00505]]); the incumbent plant fat melts across 24–26 °C ([[OF-A-00506]]). The width matters as much as the midpoint, because the width is what gives the release profile. [[ORG-RTO-01]] reaches 58 % lipid on dry weight ([[OF-A-00507]]) with a fatty acid profile tunable by nitrogen regime ([[OF-A-00508]]), which makes the melting band a design variable rather than a property. [[PF-010]] is in force in one jurisdiction and pending in one more, and no microbial route to that profile is claimed by anyone. **Build.**

**That asymmetry is the answer to your question.** Eight jurisdictions against one. The branch everyone works on is enclosed and the branch that is equally necessary is open. A programme that starts at the heme protein starts inside someone else's claim; a programme that starts at the fat phase does not.

**Branch three: the fibrous matrix.** Two structurally different routes reach the same measured outcome. Shear-cell texturisation gives an anisotropy index of 3.4 ([[OF-A-00511]]) and is claimed by [[PF-011]] in three jurisdictions. Native hyphal morphology in [[ORG-FVE-01]] gives the same 3.4 ([[OF-A-00509]]) and is claimed by nobody. Identical outcome, one route enclosed — route around rather than license. The branch carries a hidden unit operation: RNA below 2 % w/w for food use ([[OF-A-00512]]), invisible in every paper about the organism and a real yield loss. Run length is separately capped near 1,000 h by colonial mutants ([[OF-A-00510]]). **Build, with the RNA step costed in from the start.**

**One branch I am dropping.** Binding and cook-loss is well served by existing ingredients and does not justify a fermentation programme. Saying so is more useful than adding a fourth branch to look thorough.

**A constraint arriving from somewhere else entirely.** Lipid accumulation is aerobic and high-OUR, so branch two inherits the cooling wall from the capacity screen — in a warm ambient this is a siting decision, not a strain decision.

**Where this goes next.** Three follow-on queries, each a route comparison: candidate organisms and routes to the target melting profile; non-globin Maillard precursor systems as a partial heme substitute; and native-morphology versus texturised matrix at equal anisotropy. The first is the one worth running now, and it is running.

**What to do about it.** Six branches is a diagram, not a plan. The programme orders them by how much each would reduce uncertainty per bench-week and names, for every one, the single measurement that would settle it and what a result would have to *say* to move the recommendation:

| # | decides | measurement | flips if |
|---|---|---|---|
| 1 | the fat phase | solid fat content by pNMR, 4–45 °C | it melts below 25 °C |
| 2 | siting that fat phase | crystallisation hold at 26 °C ambient | it will not set without chilling |
| 3 | binding and cook-loss | cook-loss at 71 °C core, three binders | an unencumbered one lands within two points |
| 4 | the fibrous matrix | anisotropy by tensile ratio, blind | the native route lands under 3.0 |
| … | | | |
| 8 | the question you asked | triangle test, n = 60, against beef | nothing — it is terminal |

Eight decisions. **29 bench weeks on one bench, 13 on the critical path**, £90,100. The order is not the order the branches were found in: it maximises information per pound-week discounted by how much is still unknown on each branch, so the fat phase goes first and the heme question — the one with the highest stakes — waits, because it is the most expensive way to learn something the cheaper branches partly determine.

The triangle test sits last, behind five dependencies. That is the answer to what you asked: **the thing you asked for is not the first thing to measure.** A programme that ran it first would spend £22,000 learning that the patty is distinguishable, without learning which branch made it so.`,
    followups: [
      'chip:RB-AR5-001|Open the decision programme',
      'flow:AR2|Run the fat-phase route comparison',
      'flow:AR3|Where could the fat phase be produced?',
      'chip:DLV-AR5-001|Open the decomposition tree',
    ],
  },

  // ══ AR6 — run adjudication ════════════════════════════════════════
  {
    id: 'AR6',
    deliverableId: 'DLV-AR6-001',
    triggers: [
      'run 47 tick 340 do crashed is this batch still good',
      'is this run comparable to the prior runs',
      'should i flag this accession as an excursion',
      'do dropped to 8 percent for eleven minutes',
      'adjudicate this excursion',
    ],
    plan: [
      'Load the run and the comparison basis from the Ledger',
      'Locate the excursion window and integrate the deviation',
      'Check the physiological threshold for this organism',
      'Test whether the trajectory recovered',
      'Issue a verdict and write the annotation that propagates',
    ],
    toolCalls: [
      { name: 'ledger.run', args: { runId: 'RUN-047', withBasis: true }, durationMs: 640 },
      { name: 'fermos.excursionIntegrals', args: { runId: 'RUN-047', basis: ['RUN-042', 'RUN-043', 'RUN-044', 'RUN-045', 'RUN-046'], window: [340, 471] }, durationMs: 1130 },
      { name: 'geneos.threshold', args: { organismId: 'ORG-CGL-02', field: 'critical_do' }, durationMs: 420 },
      { name: 'repo.accessionsForRun', args: { runId: 'RUN-047' }, durationMs: 510 },
    ],
    answerMd: `Not comparable. Finish the run for material and flag the Accessions.

**Why the depth matters more than the duration.** [[OF-A-00119]] puts the critical dissolved oxygen tension for this organism at 8 %. The excursion did not approach that threshold, it landed on it. At the critical point respiration becomes transport-limited and the fermentative branch opens, so eleven minutes at 8 % is a different event from eleven minutes at 15 %.

**Three independent signals agree.** RQ rose above unity inside the window, the same signature [[OF-A-00122]] records under sustained limitation, so the transient was metabolically real rather than an instrument artefact. Lactate reached 0.47 g/L at harvest ([[OF-A-00148]]) against a basis where it is not detected — a small number, and it has to be, because eleven minutes cannot produce more. And carbon balance closure fell to 94.9 % ([[OF-A-00150]]) against 96.2 ± 0.4 across the five-run basis ([[OF-A-00149]]) — a 1.3-point gap, about three standard deviations. Small enough that nobody watching the chart would have flagged it, which is the whole argument for adjudicating against a basis rather than against an impression.

**The signal that decides it.** Dissolved oxygen recovered and the metabolism did not. Respiratory quotient settled about three percent above its pre-excursion baseline and held there for the rest of the run, which is what you saw as a shifted off-gas CO₂ reading — the percentage is a consequence of that, not an independent fact. A transient the culture absorbs shows both recovering together. Had RQ returned to baseline, the recommendation would be to continue unflagged and note the event; the divergence is what moves it.

**Verdict.** Continue, flagged. [[OF-A-00147]] at 39.4 g/L, [[OF-A-00148]] and [[OF-A-00150]] all carry the excursion hold. They stay visible and citable and they may not enter a median, a factor map, or a yield claim.

**Where the flag goes.** [[OF-A-00147]] renders held on the lysine gap map with [[RUN-047]] named as the reason. That propagation is the point — an excursion that is adjudicated here and silently forgotten there is worse than no adjudication at all, because it looks like diligence while behaving like an average.

**What should be published.** The adjudication criteria themselves. Integrated O₂ deficit, CER deviation, the closure gap that corresponds to a given transient, and the decision rule with its false-positive behaviour. Every process group re-derives this privately and nobody has published a rule anyone can cite.`,
    followups: [
      'flow:AR1|Show me the gap map this feeds',
      'chip:RUN-047|Open the run',
      'chip:DLV-AR6-001|Open the verdict',
    ],
  },
];

/** Empty-state prompts. Each is an exact trigger, so a cold click never declines. */
export const ARCHETYPE_PROMPTS: { id: string; label: string; prompt: string }[] = [
  { id: 'AR5', label: 'Translate an end state', prompt: 'i want to make a burger indistinguishable from beef' },
  { id: 'AR3', label: 'Find a product for a plant', prompt: 'two 5 m3 vessels what should i produce' },
  { id: 'AR1', label: 'Map an unexplored process space', prompt: 'which factor combinations are already covered' },
  { id: 'AR2', label: 'Choose a pathway', prompt: 'compare the three routes to 3-hp' },
  { id: 'AR6', label: 'Adjudicate a run', prompt: 'run 47 tick 340 do crashed is this batch still good' },
  { id: 'AR4', label: 'Design from a feedstock', prompt: 'design a plant for 400000 tonnes of bagasse' },
];
