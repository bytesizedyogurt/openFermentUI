// openFerment — protocol library (OF-DES-001 §8.11, §15), rewired onto the
// real literature corpus of OF-COR-001 §20.
//
// WHAT IS AND IS NOT SOURCED HERE. Every `paperId`, `recordId`, `sourceRecordId`
// and step `ref` below resolves to a real entry in src/data/corpus/*, and every
// claim attributed to one of those entries is a claim OF-COR-001 actually makes.
// The papers themselves have NOT been ingested — each holds a single section of
// curator's notes — so nothing here quotes a paper's own words, and no finding,
// number or condition has been invented to fill a gap.
//
// Bench procedure is not the same thing as a literature claim. Volumes, speeds,
// vessel sizes, wash steps and timings below are ordinary laboratory craft,
// written so a competent undergraduate can execute them. They are NOT
// transcriptions from the cited sources and are not presented as such. Where a
// step needs a number the corpus does not supply — an electroporation pulse
// setting, a precipitation temperature, an OD-to-dry-weight factor, a PEF field
// strength — the step says so plainly and instructs the operator to determine,
// use and record their own value. That refusal is the feature, not a gap.
//
// Scaling contract (src/engine/scale.ts):
//   'per_batch_volume'  scales with the run multiplier
//   'per_unit_biomass'  scales with the run multiplier (harvest consumables)
//   'fixed'             never scales (one probe calibration, one chamber charge)
// Step text may embed {{qty:Material Name}} for the scaled amount and
// {{stock:Material Name}} for the volume of stock that delivers it. Names must
// match Material.name exactly.
import type { Protocol } from './types';

export const PROTOCOLS: Protocol[] = [
  // ───────────────────────────────────────────────────────────────────────
  // PR-TAP-01 — TAP medium. Two versions, so the diff view has real content:
  // the v1.1 change is a change of cited trace-element source (M1 → M3).
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-TAP-01',
    title: 'TAP medium preparation (1 L base)',
    category: 'media',
    organisms: ['cw15', 'uvm4'],
    bsl: 1,
    purpose:
      'Prepare Tris-acetate-phosphate medium for mixotrophic culture of cell-wall-deficient Chlamydomonas reinhardtii from dry Tris and three concentrated stocks, at whatever scale the run needs.',
    currentVersion: '1.1',
    provenanceNote:
      'Grounded in M1 (Harris, The Chlamydomonas Sourcebook — the TAP reference), M2 (Gorman & Levine 1965 — the original Tris-acetate-phosphate formulation) and M3 (Kropat et al. 2011 — the revised trace-element supplement). OF-COR-001 catalogues all three bibliographically and transcribes exactly one composition figure: standard TAP contains 0.38 g L⁻¹ NH₄Cl (r-M8-3). Every other charge below is this laboratory’s working sheet, not a transcription, and must be checked against the Sourcebook table before first use.',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Written against the Sourcebook baseline catalogued as M1 — liquid or agar-solidified TAP, mixotrophic — with the classic Hutner trace-element supplement and a conventional titrate-to-setpoint pH step. The ammonium charge is the single composition figure the corpus states (r-M8-3, OF-COR-001 §14 M8).',
        baseBatch: { value: 1, unit: 'L', label: 'batch' },
        materials: [
          {
            name: 'Tris base',
            amount: 2.42,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
          },
          {
            name: 'Glacial acetic acid',
            amount: 1.0,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 0.05,
          },
          {
            name: 'Ammonium chloride',
            amount: 0.38,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.005,
            stock: { conc: 0.0152, unit: 'mL' },
            sourceRecordId: 'r-M8-3',
          },
          {
            name: 'Magnesium sulfate heptahydrate',
            amount: 0.1,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.001,
            stock: { conc: 0.004, unit: 'mL' },
          },
          {
            name: 'Calcium chloride dihydrate',
            amount: 0.05,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.001,
            stock: { conc: 0.002, unit: 'mL' },
          },
          {
            name: 'Potassium phosphate salts (K₂HPO₄ + KH₂PO₄)',
            amount: 1.61,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
            stock: { conc: 0.161, unit: 'mL' },
          },
          {
            name: 'Hutner trace element solution',
            amount: 1,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 0.1,
          },
          {
            name: 'Deionised water (make-up)',
            amount: 900,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'pH 7.00 calibration buffer sachet',
            amount: 1,
            unit: 'sachet',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'pH 4.01 calibration buffer sachet',
            amount: 1,
            unit: 'sachet',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'Autoclave indicator tape',
            amount: 1,
            unit: 'strip',
            scaling: 'fixed',
            precision: 1,
          },
        ],
        equipment: [
          '1 L borosilicate beaker and a 50 mm PTFE-coated stir bar',
          'Magnetic stirrer (stirring only, no heat)',
          'Analytical balance readable to 0.001 g and a top-pan balance readable to 0.01 g',
          'pH meter with a refillable glass electrode and an ATC probe',
          '1 L Class A graduated cylinder',
          '2 × 500 mL borosilicate media bottles with vented closures',
          'Autoclave capable of a 121 °C liquids cycle with slow exhaust',
          'P1000 and P5000 air-displacement pipettes',
        ],
        safety: [
          'Glacial acetic acid is corrosive and its vapour is a respiratory irritant. Dispense it in a fume hood in nitrile gloves and splash goggles, and add the acid to the bulk medium — never medium to acid.',
          'Autoclave at 121 °C on a liquids cycle with slow exhaust. Do not open the chamber until the display reads below 80 °C and the pressure gauge has fully returned to zero; bottles of hot medium boil over violently when depressurised.',
          'Cap media bottles one quarter turn back from finger tight before autoclaving. A fully sealed bottle can rupture in the chamber.',
          'The trace element stock carries soluble copper, zinc, manganese and molybdenum salts. Collect rinse water in the heavy-metal waste carboy rather than the sink.',
        ],
        steps: [
          {
            id: 'p1',
            text: 'Calibrate the pH meter immediately before use. Run a two-point calibration with {{qty:pH 7.00 calibration buffer sachet}} of pH 7.00 buffer followed by {{qty:pH 4.01 calibration buffer sachet}} of pH 4.01 buffer, at the temperature at which the medium will be measured.',
            note: 'A slope below 95 % almost always means a dried or protein-fouled junction. Refill and recondition the electrode rather than accepting the reading.',
          },
          {
            id: 'p2',
            text: 'Place a clean 1 L beaker on the stirrer, add {{qty:Deionised water (make-up)}} of deionised water and drop in the stir bar. Stir at roughly 300 rpm: fast enough to raise a shallow vortex, slow enough not to entrain air.',
          },
          {
            id: 'p3',
            text: 'Weigh {{qty:Tris base}} of Tris base and add it to the stirring water. Stir for 3–5 min until the solution is completely clear. Tris that has not dissolved by this point will not dissolve once the acetate is in.',
            note: 'OF-COR-001 does not transcribe the Sourcebook composition, so this Tris charge is the local working value and not a figure read out of M1 or M2. Check it against your own medium sheet before the first batch of a campaign.',
            refs: ['M1'],
          },
          {
            id: 'p4',
            text: 'Add {{stock:Ammonium chloride}} of salt stock S. That single addition delivers the whole salt charge: {{qty:Ammonium chloride}} ammonium chloride, {{qty:Magnesium sulfate heptahydrate}} magnesium sulfate heptahydrate and {{qty:Calcium chloride dihydrate}} calcium chloride dihydrate.',
            note: 'Invert the stock bottle three times before drawing. Magnesium settles out of stock S within a week at bench temperature.',
            refs: ['r-M8-3'],
          },
          {
            id: 'p5',
            text: 'Add {{stock:Potassium phosphate salts (K₂HPO₄ + KH₂PO₄)}} of phosphate stock P, delivering {{qty:Potassium phosphate salts (K₂HPO₄ + KH₂PO₄)}} of phosphate salts. Add it slowly and directly into the vortex, with the calcium already dispersed. A local excess of phosphate against undiluted calcium precipitates calcium phosphate as a haze that never clears.',
          },
          {
            id: 'p6',
            text: 'Add {{qty:Hutner trace element solution}} of Hutner trace element solution. The stock should be clear amber; discard any bottle showing a rust-coloured precipitate, which means the chelate has broken down and the iron is no longer bioavailable.',
          },
          {
            id: 'p7',
            text: 'In the fume hood, add {{qty:Glacial acetic acid}} of glacial acetic acid to the stirring medium and mix for 2 min.',
          },
          {
            id: 'p8',
            text: 'Read the pH and adjust to the setpoint on your medium sheet by dropwise addition of 1 M hydrochloric acid or 1 M sodium hydroxide. Record the setpoint you used and the volume of titrant.',
            note: 'OF-COR-001 records no pH setpoint for TAP. Whatever value your sheet carries, write it on the batch record — a medium released against an unrecorded setpoint cannot be compared with the next batch.',
          },
          {
            id: 'p9',
            text: 'Transfer the medium to a 1 L Class A graduated cylinder and make up to the 1,000 mL mark with deionised water. Rinse the beaker with two small aliquots of the make-up water and add the rinses, so the trace element charge transfers quantitatively.',
          },
          {
            id: 'p10',
            text: 'Split the medium between two 500 mL media bottles, leaving at least 20 % headspace in each. Cap one quarter turn back from finger tight and mark each cap with {{qty:Autoclave indicator tape}} of autoclave indicator tape.',
          },
          {
            id: 'p11',
            text: 'Autoclave at 121 °C for 20 min on a liquids cycle with slow exhaust. Start the timer when the chamber reaches setpoint, not when the cycle is initiated.',
            timerSec: 1200,
            timerLabel: 'Autoclave 121 °C, 20 min',
          },
          {
            id: 'p12',
            text: 'Leave the bottles in the closed chamber until it reads below 80 °C, then move them to the bench and let them reach room temperature before tightening the caps.',
            timerSec: 2700,
            timerLabel: 'Cool to room temperature',
          },
          {
            id: 'p13',
            text: 'Withdraw 5 mL from one bottle into a clean tube and confirm the pH of the cooled medium is within 0.2 units of the setpoint recorded at step p8.',
          },
          {
            id: 'p14',
            text: 'Label each bottle with the medium name, this protocol version, the preparation date and your initials. Store at room temperature in the dark and use within 8 weeks.',
            note: 'Discard at the first sign of turbidity. TAP is unbuffered against microbial growth and a contaminated bottle will not always look cloudy until it is heavily overgrown.',
          },
        ],
        estMinutes: { active: 40, total: 105 },
        references: [
          {
            paperId: 'M1',
            note: 'The Chlamydomonas Sourcebook — the TAP reference this recipe descends from. Catalogued only; OF-COR-001 transcribes its cultivation conditions (22 °C, 50–100 µE m⁻² s⁻¹, mixotrophic) but not its medium composition.',
          },
          {
            paperId: 'M2',
            note: 'Gorman & Levine 1965 — the original Tris-acetate-phosphate formulation. Author string flagged [verify] in the corpus; no composition transcribed.',
          },
          {
            recordId: 'r-M8-3',
            note: 'Standard TAP contains 0.38 g L⁻¹ NH₄Cl — the only TAP composition figure in the corpus. Curated, unverified against the source PDF.',
          },
        ],
      },
      {
        version: '1.1',
        changelog:
          'Trace-element supplement changed from the Hutner solution to the revised mineral nutrient supplement of Kropat et al. 2011 (M3), which OF-COR-001 §14 records as the modern trace-element recipe and whose title states that it increases biomass and growth rate in C. reinhardtii. The corpus transcribes neither recipe, so this is a change of cited source and stock identity, not a change of transcribed numbers: the volume added per litre is unchanged and the operator makes the stock to the published Kropat table. Second change: the titrate-to-setpoint pH step is replaced by a pass/fail check. Acetic acid in this medium is stoichiometrically paired with the Tris rather than trimmed against a target, and back-titrating with hydrochloric acid loads the medium with chloride while leaving the acetate carbon charge short.',
        baseBatch: { value: 1, unit: 'L', label: 'batch' },
        materials: [
          {
            name: 'Tris base',
            amount: 2.42,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
          },
          {
            name: 'Glacial acetic acid',
            amount: 1.0,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 0.05,
          },
          {
            name: 'Ammonium chloride',
            amount: 0.38,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.005,
            stock: { conc: 0.0152, unit: 'mL' },
            sourceRecordId: 'r-M8-3',
          },
          {
            name: 'Magnesium sulfate heptahydrate',
            amount: 0.1,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.001,
            stock: { conc: 0.004, unit: 'mL' },
          },
          {
            name: 'Calcium chloride dihydrate',
            amount: 0.05,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.001,
            stock: { conc: 0.002, unit: 'mL' },
          },
          {
            name: 'Potassium phosphate salts (K₂HPO₄ + KH₂PO₄)',
            amount: 1.61,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
            stock: { conc: 0.161, unit: 'mL' },
          },
          {
            name: 'Revised trace element solution (Kropat 2011)',
            amount: 1,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 0.1,
          },
          {
            name: 'Deionised water (make-up)',
            amount: 900,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'pH 7.00 calibration buffer sachet',
            amount: 1,
            unit: 'sachet',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'pH 4.01 calibration buffer sachet',
            amount: 1,
            unit: 'sachet',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'Autoclave indicator tape',
            amount: 1,
            unit: 'strip',
            scaling: 'fixed',
            precision: 1,
          },
        ],
        equipment: [
          '1 L borosilicate beaker and a 50 mm PTFE-coated stir bar',
          'Magnetic stirrer (stirring only, no heat)',
          'Analytical balance readable to 0.001 g and a top-pan balance readable to 0.01 g',
          'pH meter with a refillable glass electrode and an ATC probe',
          '1 L Class A graduated cylinder',
          '2 × 500 mL borosilicate media bottles with vented closures',
          'Autoclave capable of a 121 °C liquids cycle with slow exhaust',
          'P1000 and P5000 air-displacement pipettes',
        ],
        safety: [
          'Glacial acetic acid is corrosive and its vapour is a respiratory irritant. Dispense it in a fume hood in nitrile gloves and splash goggles, and add the acid to the bulk medium — never medium to acid.',
          'Autoclave at 121 °C on a liquids cycle with slow exhaust. Do not open the chamber until the display reads below 80 °C and the pressure gauge has fully returned to zero; bottles of hot medium boil over violently when depressurised.',
          'Cap media bottles one quarter turn back from finger tight before autoclaving. A fully sealed bottle can rupture in the chamber.',
          'Weigh Tris inside a draught shield and wipe the balance pan afterwards. The dust is an eye irritant and it carries into the next weighing.',
          'The revised trace element stock is a set of individually complexed transition-metal salts. Make it up in a fume hood, keep the concentrates labelled separately until they are combined, and collect all rinse water in the heavy-metal waste carboy.',
        ],
        steps: [
          {
            id: 'p1',
            text: 'Calibrate the pH meter immediately before use. Run a two-point calibration with {{qty:pH 7.00 calibration buffer sachet}} of pH 7.00 buffer followed by {{qty:pH 4.01 calibration buffer sachet}} of pH 4.01 buffer, at the temperature at which the medium will be measured.',
            note: 'A slope below 95 % almost always means a dried or protein-fouled junction. Refill and recondition the electrode rather than accepting the reading.',
          },
          {
            id: 'p2',
            text: 'Place a clean 1 L beaker on the stirrer, add {{qty:Deionised water (make-up)}} of deionised water and drop in the stir bar. Stir at roughly 300 rpm: fast enough to raise a shallow vortex, slow enough not to entrain air.',
          },
          {
            id: 'p3',
            text: 'Weigh {{qty:Tris base}} of Tris base and add it to the stirring water. Stir for 3–5 min until the solution is completely clear. Tris that has not dissolved by this point will not dissolve once the acetate is in.',
            refs: ['M2'],
            note: 'The Tris–acetate pairing is the defining feature of the formulation M2 introduced. OF-COR-001 does not transcribe M2’s numbers, so treat the charges on this sheet as local values traceable to the Sourcebook, not as figures read from the 1965 paper.',
          },
          {
            id: 'p4',
            text: 'Add {{stock:Ammonium chloride}} of salt stock S. That single addition delivers the whole salt charge: {{qty:Ammonium chloride}} ammonium chloride, {{qty:Magnesium sulfate heptahydrate}} magnesium sulfate heptahydrate and {{qty:Calcium chloride dihydrate}} calcium chloride dihydrate.',
            note: 'Invert the stock bottle three times before drawing. Magnesium settles out of stock S within a week at bench temperature.',
            refs: ['r-M8-3'],
          },
          {
            id: 'p5',
            text: 'Add {{stock:Potassium phosphate salts (K₂HPO₄ + KH₂PO₄)}} of phosphate stock P, delivering {{qty:Potassium phosphate salts (K₂HPO₄ + KH₂PO₄)}} of phosphate salts. Add it slowly and directly into the vortex, with the calcium already dispersed. A local excess of phosphate against undiluted calcium precipitates calcium phosphate as a haze that never clears.',
          },
          {
            id: 'p6',
            text: 'Add {{qty:Revised trace element solution (Kropat 2011)}} of the revised trace element solution, made up to the Kropat table with each metal complexed separately before combining. Do not substitute the Hutner stock at this step: the two supplements are not interchangeable and the batch record must say which was used.',
            refs: ['M3'],
            note: 'OF-COR-001 §14 records M3 as the modern trace-element recipe and its title claims increased biomass and growth rate; the corpus does not transcribe the table itself, and this platform holds no measured comparison between the two supplements. If you want that comparison, it is an experiment, not a lookup.',
          },
          {
            id: 'p7',
            text: 'In the fume hood, add {{qty:Glacial acetic acid}} of glacial acetic acid straight into the vortex. This addition is both the acetate carbon charge and the titrant for the Tris.',
            note: 'Weigh the acid rather than pipetting it at any scale above 2 L. Glacial acetic acid wets a polypropylene tip badly and volumetric delivery carries a 3–4 % error that propagates straight into the starting pH.',
          },
          {
            id: 'p8',
            text: 'Stir for 2 min, then read the pH and record it. Do not titrate to a setpoint. A reading outside the window on your medium sheet means the Tris or the acetate was weighed wrong, and the batch is remade rather than corrected.',
            note: 'A batch reading high has usually had Tris weighed against the formula weight of the hydrochloride salt. A batch reading low has had acid added twice. Neither is fixed by titration — both are fixed by reweighing.',
          },
          {
            id: 'p9',
            text: 'Transfer the medium to a 1 L Class A graduated cylinder and make up to the 1,000 mL mark with deionised water. Rinse the beaker with two small aliquots of the make-up water and add the rinses, so the trace element charge transfers quantitatively.',
          },
          {
            id: 'p10',
            text: 'Split the medium between two 500 mL media bottles, leaving at least 20 % headspace in each. Cap one quarter turn back from finger tight and mark each cap with {{qty:Autoclave indicator tape}} of autoclave indicator tape.',
          },
          {
            id: 'p11',
            text: 'Autoclave at 121 °C for 20 min on a liquids cycle with slow exhaust. Start the timer when the chamber reaches setpoint, not when the cycle is initiated.',
            timerSec: 1200,
            timerLabel: 'Autoclave 121 °C, 20 min',
          },
          {
            id: 'p12',
            text: 'Leave the bottles in the closed chamber until it reads below 80 °C, then move them to the bench and let them reach room temperature before tightening the caps.',
            timerSec: 2700,
            timerLabel: 'Cool to room temperature',
          },
          {
            id: 'p13',
            text: 'Withdraw 5 mL from one bottle into a clean tube and read the pH of the cooled medium. Release the batch only if it is within 0.1 units of the pre-autoclave reading and the medium is water-clear. A faint white haze is calcium phosphate; discard the batch and repeat step p5 more slowly.',
          },
          {
            id: 'p14',
            text: 'Label each bottle with the medium name, this protocol version, the trace-element supplement used, the preparation date and your initials. Store at room temperature in the dark and use within 8 weeks.',
            note: 'The supplement identity belongs on the label, not only on the batch sheet. A growth difference between two campaigns is uninterpretable if nobody can tell which bottles carried which trace elements.',
          },
        ],
        estMinutes: { active: 35, total: 100 },
        references: [
          {
            paperId: 'M3',
            note: 'Kropat et al. 2011, the revised mineral nutrient supplement — the source this version switches to. Author string flagged [verify] in OF-COR-001; the table itself is not transcribed, so the recipe must be taken from the paper.',
          },
          {
            paperId: 'M1',
            note: 'The Sourcebook baseline the v1.0 formulation descends from, retained as the cultivation reference.',
          },
          {
            paperId: 'M2',
            note: 'The original Tris-acetate-phosphate formulation. Cited for provenance of the Tris–acetate pairing, not for any number.',
          },
          {
            recordId: 'r-M8-3',
            note: 'Standard TAP contains 0.38 g L⁻¹ NH₄Cl. Curated from OF-COR-001 §14 M8 and unverified against the source PDF — note that M8 quotes it as the standard against which it reduced nitrogen, not as its own measurement.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-SEED-01 — seed train. Every density target is operator-determined:
  // the corpus holds no growth rate and no OD factor for cw15 itself.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-SEED-01',
    title: 'cw15 seed train: plate to 50 mL to 400 mL',
    category: 'culture',
    organisms: ['cw15', 'uvm4'],
    bsl: 1,
    purpose:
      'Raise a 400 mL mid-exponential cw15 or UVM4 seed from a single colony through a 50 mL intermediate, timed so the seed reaches the production vessel inside its exponential window rather than after it.',
    currentVersion: '1.0',
    provenanceNote:
      'Grounded in M1 (standard cultivation: 22 °C, continuous light at 50–100 µE m⁻² s⁻¹, mixotrophic), M7 (the corpus’s only specific-growth-rate record, r-M7-1) and B5 (wall-deficient strains are much more susceptible to shear and osmotic stress). OF-COR-001 holds no growth rate, doubling time or OD-to-dry-weight factor for cw15 or UVM4 themselves, so every density target below is one the operator measures and records rather than one this protocol supplies.',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Illumination and temperature follow the standard cultivation conditions catalogued for M1. Stage timings are scheduling conventions, not measured figures, and are labelled as such at the steps where it matters.',
        baseBatch: { value: 400, unit: 'mL', label: 'production seed' },
        materials: [
          {
            name: 'TAP medium — stage 1 charge',
            amount: 50,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 5,
          },
          {
            name: 'TAP medium — stage 2 charge',
            amount: 400,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: '250 mL baffled flask with silicone foam plug',
            amount: 1,
            unit: 'flask',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: '2 L baffled flask with silicone foam plug',
            amount: 1,
            unit: 'flask',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Sterile 10 mL serological pipettes',
            amount: 6,
            unit: 'pipettes',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'TAP agar plate with single colonies',
            amount: 1,
            unit: 'plate',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'Sterile disposable inoculation loops',
            amount: 2,
            unit: 'loops',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: '70 % v/v ethanol spray',
            amount: 1,
            unit: 'bottle',
            scaling: 'fixed',
            precision: 1,
          },
        ],
        equipment: [
          'Orbital shaker with a 25 mm orbit and an LED illumination panel beneath the platform',
          'Temperature-controlled shaker enclosure or a 22 °C warm room',
          'Class II cabinet or clean bench with a Bunsen burner',
          'Spectrophotometer reading at 750 nm with 10 mm cuvettes',
          'Spherical quantum sensor for photon flux verification',
        ],
        safety: [
          '70 % ethanol is flammable. Let sprayed surfaces flash off completely before lighting the burner, and never spray toward an open flame.',
          'Silicone foam plugs must stay dry. A plug wetted by a splash or by condensate is a contamination path; replace it rather than drying it.',
          'Baffled flasks walk on a shaker platform. Check every clamp before starting and never reach into a moving platform to reseat a flask.',
          'The illumination panel runs hot under the platform. Do not rest a gloved hand on it while reseating flasks, and keep the ethanol spray off it entirely.',
          'Autoclave all spent culture at 121 °C for 20 min before it goes to drain. cw15 is BSL-1, but a transformed seed carries a selectable marker and leaves the building only through the autoclave.',
        ],
        steps: [
          {
            id: 's1',
            text: 'Day 1. Set and verify the shaker before any medium is dispensed: 22 °C in the enclosure, continuous illumination measured with the quantum sensor at the working liquid depth, and a shaking speed you have recorded. Record all three on the batch sheet.',
            refs: ['M1'],
            note: 'OF-COR-001 §14 records standard cultivation for this organism as liquid or agar-solidified TAP at 22 °C under continuous light at 50–100 µE m⁻² s⁻¹, mixotrophic. Set the flux inside that band and write down the number you measured, not the number you intended.',
          },
          {
            id: 's2',
            text: 'Choose the shaking speed for the geometry you are running and keep it modest. Wall-deficient strains are much more susceptible to shear and osmotic stress than the walled wild type, and a seed train is the cheapest place in the process to discover that. Record the speed; it is a process parameter, not a preference.',
            refs: ['B5'],
          },
          {
            id: 's3',
            text: 'Dispense {{qty:TAP medium — stage 1 charge}} of TAP medium into the {{qty:250 mL baffled flask with silicone foam plug}} 250 mL baffled flask, plug it, and equilibrate it on the running shaker.',
            timerSec: 3600,
            timerLabel: 'Equilibrate stage 1 medium to 22 °C',
          },
          {
            id: 's4',
            text: 'Select one well-isolated green colony 1–2 mm across from the TAP agar plate carrying single colonies ({{qty:TAP agar plate with single colonies}} for this seed train).',
            note: 'Avoid colonies at the plate edge and any colony inside a confluent streak. Both carry a different light and nutrient history from the plate interior, and that history shows up as a longer lag.',
          },
          {
            id: 's5',
            text: 'Lift the colony with a sterile loop and swirl the loop in the stage 1 medium until no visible green remains on the plastic. Return the flask to the shaker and note the clock time as the start of stage 1.',
          },
          {
            id: 's6',
            text: 'Incubate stage 1 for 48 h, then read it. Read the culture rather than the clock: if it is still visually pale, give it longer and record the extension rather than carrying a thin seed forward.',
            timerSec: 172800,
            timerLabel: 'Stage 1 incubation, 48 h',
            note: '48 h is a scheduling convention for this flask geometry, not a measured figure. OF-COR-001 records no lag phase, doubling time or growth rate for cw15 or UVM4, so there is no literature value to schedule against — build your own growth curve on your own hardware and replace this interval with it.',
          },
          {
            id: 's7',
            text: 'Day 3. Read the OD750 of the stage 1 culture against a TAP medium blank, diluting into the linear range of your instrument and multiplying back. Record the reading; the stage 2 inoculum volume is computed from it.',
          },
          {
            id: 's8',
            text: 'Compute the stage 2 inoculum volume from your measured OD and your chosen starting OD: V_seed (mL) = OD_target × 400 / OD_seed. Reduce the stage 2 medium charge by that volume so the working volume stays at 400 mL.',
            note: 'Pick OD_target from your own growth curve and keep it constant across a campaign. Inoculating high to save a day does not work: above the point where the flask becomes light-limited the culture enters that regime before it has finished its lag, and the fitted growth rate falls.',
          },
          {
            id: 's9',
            text: 'Dispense {{qty:TAP medium — stage 2 charge}} of TAP medium, less the computed inoculum volume, into the {{qty:2 L baffled flask with silicone foam plug}} 2 L baffled flask using the {{qty:Sterile 10 mL serological pipettes}} sterile serological pipettes.',
          },
          {
            id: 's10',
            text: 'Transfer the computed volume of stage 1 culture into the stage 2 flask, working within 150 mm of the burner. Swirl once, reseat the foam plug and return the flask to the shaker at the recorded speed.',
          },
          {
            id: 's11',
            text: 'Incubate stage 2 for 24 h without sampling. Opening the flask during the first day costs more in contamination risk than an early reading is worth.',
            timerSec: 86400,
            timerLabel: 'Stage 2 incubation, 24 h',
          },
          {
            id: 's12',
            text: 'Day 4. Read OD750 at intervals short enough to place the harvest point on your own curve, and harvest at the OD750 your curve puts in mid-exponential. Do not use a number from this protocol: there isn’t one.',
            refs: ['r-M7-1'],
            note: 'For sampling-interval planning only: the corpus’s single specific-growth-rate record is 0.087 h⁻¹, measured on the walled strain cc124 in TAP with a 0 % CO₂ feed (r-M7-1). It is a different strain in a different flask and it is a planning aid, not a prediction for cw15. Sample at least four times an estimated doubling.',
          },
          {
            id: 's13',
            text: 'Convert the harvest OD to dry cell weight only if you have determined the factor yourself under PR-OD-01. There is no literature factor to fall back on for this strain, so an unconverted OD with its wavelength stated is a more honest seed record than a converted one with a borrowed factor.',
          },
          {
            id: 's14',
            text: 'Deliver the seed to the production vessel within 30 min of the final reading, at ambient temperature and without centrifugation. Record the harvest OD750, the elapsed time from colony pick, the flask identifier and the measured photon flux on the batch sheet.',
            refs: ['B5'],
            note: 'Do not centrifuge a wall-deficient seed to concentrate it before inoculation. The strain’s shear and osmotic fragility is exactly the property that makes it attractive downstream, and it is a liability here.',
          },
        ],
        estMinutes: { active: 80, total: 4400 },
        references: [
          {
            paperId: 'M1',
            note: 'Standard cultivation for C. reinhardtii: TAP at 22 °C under continuous light at 50–100 µE m⁻² s⁻¹, mixotrophic.',
          },
          {
            recordId: 'r-M7-1',
            note: 'Specific growth rate 0.087 h⁻¹ — strain cc124, TAP, 0 % CO₂ feed. The corpus’s cleanest growth-rate record, and not a cw15 measurement. Curated, unverified.',
          },
          {
            paperId: 'B5',
            note: 'Records that cell-wall-deficient strains have reduced motility and mating ability and are much more susceptible to shear and osmotic stress — the constraint behind the shaking-speed and no-centrifugation rules here.',
          },
          {
            recordId: 'r-M5-1',
            note: 'Maximum density 1.23 ± 0.13 g L⁻¹ within 96 h for wild-type CC-137c in TAP. Included as an order-of-magnitude sanity bound for a mixotrophic batch; it is a walled wild-type figure, not a seed-train target.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-TRANS-01 — NEW. Nuclear transformation by electroporation. Selection
  // concentration from A1 (r-A1-2); time to colony from B5 (r-B5-1/2/3);
  // the NHEJ screening caveat from A4. Pulse parameters are operator-set.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-TRANS-01',
    title: 'Nuclear transformation of cw15 by electroporation',
    category: 'culture',
    organisms: ['cw15', 'uvm4'],
    bsl: 1,
    purpose:
      'Introduce a linearised nuclear expression cassette into cell-wall-deficient C. reinhardtii by electroporation, select on paromomycin, and screen enough independent transformants that random-locus integration is accounted for rather than assumed away.',
    currentVersion: '1.0',
    provenanceNote:
      'Grounded in A1 (paromomycin selection at 10 µg mL⁻¹ for this lineage, r-A1-2), B5 (colonies appear on selection in 7–10 days for cw15 and UVM4 against 15–20 days for walled WT12, r-B5-1/r-B5-2/r-B5-3) and A4 (integration proceeds by non-homologous end joining at random loci, with homologous recombination at much lower frequency). OF-COR-001 transcribes no pulse parameters, DNA masses, cell densities or transformation efficiencies, so those are set, measured and recorded by the operator — this protocol does not supply values it does not have.',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Replaces nothing; the platform previously had no transformation protocol. Selection concentration and the incubation window are the two literature-backed numbers in the procedure and are cited at the steps that use them.',
        baseBatch: { value: 8, unit: 'reactions', label: 'electroporation set' },
        materials: [
          {
            name: 'Mid-exponential cw15 culture',
            amount: 200,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Linearised expression cassette DNA',
            amount: 4,
            unit: 'µg',
            scaling: 'per_batch_volume',
            precision: 0.1,
            stock: { conc: 0.5, unit: 'µL' },
          },
          {
            name: 'TAP–sucrose electroporation buffer',
            amount: 25,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: '0.4 cm electroporation cuvettes',
            amount: 8,
            unit: 'cuvettes',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'TAP recovery medium',
            amount: 80,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 5,
          },
          {
            name: 'Paromomycin sulfate',
            amount: 5,
            unit: 'mg',
            scaling: 'per_batch_volume',
            precision: 0.1,
            stock: { conc: 10, unit: 'mL' },
            sourceRecordId: 'r-A1-2',
          },
          {
            name: 'TAP agar selection plates, 25 mL each',
            amount: 20,
            unit: 'plates',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Sterile 50 mL conical tubes',
            amount: 10,
            unit: 'tubes',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Sterile 3 mm glass plating beads',
            amount: 1,
            unit: 'bottle',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'Untransformed recipient control aliquot',
            amount: 1,
            unit: 'aliquot',
            scaling: 'fixed',
            precision: 1,
          },
        ],
        equipment: [
          'Square-wave electroporator with a 0.4 cm cuvette chamber, a lid interlock and a time-constant readout',
          'Swing-out benchtop centrifuge capable of 1,000 × g with the brake disabled',
          'Class II cabinet or clean bench',
          'Spectrophotometer reading at 750 nm',
          '22 °C illuminated incubator with a shelf that can be shaded for the recovery period',
          'Haemocytometer or automated cell counter',
          'Gridded plate template or a colony counter',
        ],
        safety: [
          'The electroporator stores lethal energy in its capacitor bank. Load and unload cuvettes only with the chamber lid closed and the charge-ready lamp dark, and never bridge the cuvette electrodes with a tip, forceps or a finger to investigate a failed pulse — discharge through the instrument’s own bleed circuit.',
          'Paromomycin sulfate is an aminoglycoside: nephrotoxic and ototoxic, and the dry powder is readily airborne. Weigh it in a balance enclosure wearing nitrile gloves and eye protection, make the 10 mg mL⁻¹ stock behind a sash, and mark every plate so the next user knows it carries antibiotic.',
          'A cuvette that arcs sprays hot buffer and aerosolised cells when the lid is opened. If the time constant collapses or you hear a snap, leave the lid closed for 30 s before opening, then discard the cuvette into the autoclave stream.',
          'Wall-deficient recipients lyse on osmotic shock. Treat the resulting lysate as an aerosol source: cap tubes before vortexing and wipe the cuvette holder down between reactions.',
          'Everything that has held transgenic algae — plates, cuvettes, tubes, pipettes — is autoclaved at 121 °C for 20 min before disposal, and transformation waste is kept in a stream separate from untransformed culture so a containment question can be answered from the log.',
        ],
        steps: [
          {
            id: 't1',
            text: 'Grow the recipient to mid-exponential phase under PR-SEED-01, in TAP at 22 °C under continuous light in the 50–100 µE m⁻² s⁻¹ band recorded as standard cultivation for this organism. Use {{qty:Mid-exponential cw15 culture}} of culture for the set.',
            refs: ['M1'],
          },
          {
            id: 't2',
            text: 'Confirm the construct before the cells are touched: linearised outside the expression cassette, sequence-verified, and carrying a selectable marker that matches the selection you are about to apply.',
            refs: ['A5'],
            note: 'If this is the second cassette of a two-gene programme, it needs its own distinct marker. OF-COR-001 §2 records that UVM4 and UVM11 can hardly be crossed, so each transgene has to be introduced by a separate transformation rather than combined by mating.',
          },
          {
            id: 't3',
            text: 'Harvest the cells gently: 1,000 × g for 5 min at room temperature in a swing-out rotor with the brake off. Do not use a fixed-angle rotor at higher speed to save time.',
            refs: ['B5'],
            timerSec: 300,
            timerLabel: 'Harvest spin, 1,000 × g, 5 min',
            note: 'Wall-deficient strains are much more susceptible to shear and osmotic stress than walled strains. Cells lost here are lost invisibly — the pellet still looks right.',
          },
          {
            id: 't4',
            text: 'Resuspend the pellet in {{qty:TAP–sucrose electroporation buffer}} of TAP–sucrose electroporation buffer, to the cell density your electroporator’s validated Chlamydomonas programme calls for. Count the suspension and record the density: it is a denominator you will need later.',
          },
          {
            id: 't5',
            text: 'Assemble the set on ice. Distribute the resuspended cells evenly between the {{qty:0.4 cm electroporation cuvettes}} in the set, and deliver {{stock:Linearised expression cassette DNA}} of the 500 ng µL⁻¹ DNA stock across the set — {{qty:Linearised expression cassette DNA}} of DNA in total. Reserve one cuvette as a no-DNA mock and hold the {{qty:Untransformed recipient control aliquot}} untransformed aliquot unpulsed.',
            note: 'Both controls earn their place. The mock tells you whether your selection is tight; the unpulsed aliquot tells you whether the cells were viable before the instrument touched them.',
          },
          {
            id: 't6',
            text: 'Pulse each cuvette on your electroporator’s validated C. reinhardtii programme. Record the field strength, capacitance, pulse length and the measured time constant for every reaction on the batch sheet.',
            refs: ['A4'],
            note: 'This protocol deliberately specifies no pulse parameters. OF-COR-001 catalogues A4’s systematic review of transformation methods, selection genes and efficiency factors but does not transcribe any settings, and inventing them here would be worse than useless. A run without recorded settings cannot be repeated, so the recording is the requirement.',
          },
          {
            id: 't7',
            text: 'Recover without selection. Dilute each reaction into {{qty:TAP recovery medium}} of TAP recovery medium split between {{qty:Sterile 50 mL conical tubes}}, and hold at 22 °C in dim light with very gentle agitation for 16 h.',
            timerSec: 57600,
            timerLabel: 'Non-selective recovery, 16 h',
            note: 'Selection applied straight after the pulse kills cells that would have recovered. Dim light, not darkness: the recovery is mixotrophic and acetate does most of the work, but the culture should not be light-starved on top of being electroporated.',
          },
          {
            id: 't8',
            text: 'Plate the recovered cells on {{qty:TAP agar selection plates, 25 mL each}} selection plates containing paromomycin at 10 µg mL⁻¹, the concentration A1 records for this strain lineage. Deliver it from {{stock:Paromomycin sulfate}} of 10 mg mL⁻¹ stock — {{qty:Paromomycin sulfate}} of paromomycin across the set — added to molten agar below 55 °C. Spread with {{qty:Sterile 3 mm glass plating beads}} of sterile glass beads.',
            refs: ['r-A1-2'],
            note: 'A1 also records zeocin as a selection agent for this lineage, but OF-COR-001 gives no zeocin concentration. If you select on zeocin, the concentration is yours to determine and record — there is nothing in the corpus to copy.',
          },
          {
            id: 't9',
            text: 'Incubate the plates at 22 °C under continuous light and start counting at day 5. Colonies appear on selection in 7–10 days for cw15 and UVM4; the walled strain WT12 takes 15–20 days in the same comparison, so a cw15 plate still blank at day 12 points at a failed pulse or dead selection rather than at slow growth.',
            refs: ['r-B5-1', 'r-B5-2', 'r-B5-3'],
            note: 'That 7–10 versus 15–20 day contrast is one of the concrete operational advantages of a wall-deficient host, and it is worth logging the actual day of first appearance every time so the platform accumulates its own distribution rather than repeating the corpus figure.',
          },
          {
            id: 't10',
            text: 'Pick at least 24 independent colonies and re-streak each to a fresh selection plate. Do not pool them and do not treat colonies from one plate as replicates of one another.',
            refs: ['A4'],
            note: 'Integration proceeds by non-homologous end joining at random loci, with homologous recombination occurring at much lower frequency, and insertional events can cause deletion, recombination or translocation near the integration site. Every transformant is therefore a different strain with a different genomic context, and screening is mandatory rather than good practice.',
          },
          {
            id: 't11',
            text: 'Screen the re-streaked clones for expression and rank them. Carry at least the top three forward, not just the best one.',
            refs: ['r-A1-1'],
            note: 'For calibration of expectations only: A1 records that UVM4 and UVM11 reach about 0.2 % of total soluble protein for intracellular GFP/YFP reporters. That is a reporter figure in this lineage, not a target for a casein cassette, and OF-COR-001 contains no algal casein expression figure of any kind — there has never been a published one.',
          },
          {
            id: 't12',
            text: 'Archive the clones and close the record. Compute transformation efficiency as colonies per µg of DNA per cell plated, using the density recorded at step t4 and the DNA mass at step t5, and enter it with both denominators stated.',
            note: 'OF-COR-001 records no transformation-efficiency value for this lineage, so your figure is the first one this platform holds in the transformation_efficiency field. Report it with the pulse settings, the recipient strain and the marker — an efficiency without those is not comparable to anything, including your own next run.',
          },
        ],
        estMinutes: { active: 210, total: 15840 },
        references: [
          {
            paperId: 'A1',
            note: 'The foundational strain paper for this lineage: cw15-302 → Elow47 → UVM4/UVM11, and the source of the selection concentration used here.',
          },
          {
            recordId: 'r-A1-2',
            note: 'Selection used paromomycin at 10 µg mL⁻¹. Curated from OF-COR-001 §2 A1, unverified against the source PDF.',
          },
          {
            recordId: 'r-A1-1',
            note: '~0.2 % of total soluble protein for intracellular GFP/YFP in UVM4/UVM11 — the reporter ceiling this lineage is quoted at.',
          },
          {
            paperId: 'B5',
            note: 'Direct comparison of transformation in cw15, UVM4 and walled WT12, and the statement of the shear and osmotic fragility trade-off.',
          },
          {
            recordId: 'r-B5-1',
            note: 'Time to colony 7–10 d for cw15 on selection (point value entered as the midpoint).',
          },
          {
            recordId: 'r-B5-3',
            note: 'Time to colony 15–20 d for walled WT12 — the contrast that makes the wall-deficient host operationally cheaper.',
          },
          {
            paperId: 'A4',
            note: 'Review of nuclear transformation: NHEJ integration at random loci, low-frequency homologous recombination, and insertional deletion, recombination or translocation near the integration site. The reason step t10 exists.',
          },
          {
            paperId: 'A5',
            note: 'The UVM4/UVM11 mating limitation: strains can hardly be crossed, so each transgene needs a separate transformation with a distinct marker.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-OD-01 — analytics. The corpus holds no OD-to-dry-weight factor for any
  // strain, so this SOP determines one rather than looking one up.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-OD-01',
    title: 'OD750 and dry cell weight SOP',
    category: 'analytics',
    organisms: ['cw15', 'uvm4'],
    bsl: 1,
    purpose:
      'Measure optical density at 750 nm and gravimetric dry cell weight on the same sample, and derive the conversion factor between them for this strain, wavelength and growth phase — because there is no literature factor for this host to borrow.',
    currentVersion: '1.0',
    provenanceNote:
      'OF-COR-001 contains no OD-to-dry-weight factor for cw15, UVM4 or any C. reinhardtii strain. It does contain gravimetric biomass densities (M5, M8) that bound what a plausible result looks like. This SOP is therefore laboratory method, cited to the corpus only for those sanity bounds; the factor it produces is a measurement the operator makes, and the platform treats it as user provenance rather than literature.',
    versions: [
      {
        version: '1.0',
      // Second bar on the S1 tornado at 61.7%. r-M5-1 records 1.23 g/L for the
      // walled wild type in TAP; the S1 reference point assumes 2 g/L, which
      // the assumption note itself calls "already optimistic against this".
      decisive: {
        field: 'final_biomass_density' as const,
        currentUncertainty:
          'The biomass density the S1 model assumes has not been measured on cw15. r-M5-1 reports 1.23 g/L, and that was the walled wild type — cell-wall-deficient strains are more fragile and typically reach less.',
        whatWouldChange:
          'The reference design assumes 2 g/L. Measuring below about 1.2 g/L on cw15 itself moves the MSP by more than half the range the sweep covers, and makes the photobioreactor capital line dominant.',
      },
      resultSchema: [
        { id: 'dcw', field: 'final_biomass_density' as const, label: 'Dry cell weight', type: 'number' as const, unit: 'g L⁻¹', required: true },
        { id: 'od750', label: 'OD750 at harvest', type: 'number' as const, unit: '', required: true },
        { id: 'factor', label: 'Derived OD750 → g/L conversion factor', type: 'number' as const, unit: 'g L⁻¹', required: false },
        { id: 'notes', label: 'Notes', type: 'text' as const, required: false },
      ],
        changelog:
          'Initial release. Blanking against spent medium, filter-blank subtraction and a through-origin regression, with the corpus biomass records used as plausibility bounds on the gravimetric result rather than as targets.',
        baseBatch: { value: 12, unit: 'samples', label: 'per run' },
        materials: [
          {
            name: 'Pre-washed 0.7 µm glass-fibre filters',
            amount: 16,
            unit: 'filters',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Ammonium formate wash solution',
            amount: 600,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Spent cell-free medium',
            amount: 250,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: '10 mm disposable cuvettes',
            amount: 24,
            unit: 'cuvettes',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Aluminium weighing boats',
            amount: 16,
            unit: 'boats',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Calibrated 100–1000 µL pipette',
            amount: 1,
            unit: 'pipette',
            scaling: 'fixed',
            precision: 1,
          },
        ],
        equipment: [
          'Spectrophotometer with a 750 nm setting and a 10 mm cuvette holder',
          'Vacuum filtration manifold with 25 mm funnels and a shielded sidearm flask',
          'Analytical balance readable to 0.1 mg in a draught-free enclosure',
          '105 °C drying oven and a desiccator with fresh silica gel',
          'Vortex mixer and forceps',
        ],
        safety: [
          'The 105 °C oven and its trays cause contact burns. Move filters with forceps into a room-temperature desiccator and never weigh a hot filter — convection over the pan makes it read light by up to 0.4 mg.',
          'Vacuum flasks implode if scratched. Inspect the sidearm flask before each run and keep it inside a mesh sleeve while under vacuum.',
          'Ammonium formate decomposes to ammonia in the drying oven. Run the oven vented, and do not leave a large batch of freshly washed filters in a closed oven overnight in an unventilated room.',
          'Culture filtrate and spent medium go to the autoclave waste stream, not to drain.',
        ],
        steps: [
          {
            id: 'o1',
            text: 'Dry {{qty:Pre-washed 0.7 µm glass-fibre filters}} glass-fibre filters at 105 °C for 2 h, cool them in a desiccator for 30 min and weigh each to 0.1 mg. Record every tare against the filter position in the rack.',
            timerSec: 7200,
            timerLabel: 'Pre-dry filters, 2 h',
            note: 'Filters are not interchangeable once tared. A 0.3 mg spread between filters from the same box is normal and it is the whole signal at the dilute end of a growth curve.',
          },
          {
            id: 'o2',
            text: 'Reserve four tared filters as blanks. They receive the identical wash and dry cycle without sample, and their mean mass change is subtracted from every gravimetric result in the run.',
          },
          {
            id: 'o3',
            text: 'Invert each culture sample three times immediately before reading. Settled cells re-suspend completely, but a sample read well after mixing has already lost absorbance to sedimentation.',
          },
          {
            id: 'o4',
            text: 'Read OD750 in a 10 mm cuvette against {{qty:Spent cell-free medium}} of spent cell-free medium as the blank. Establish the top of your instrument’s linear range once, with a dilution series, and dilute every sample that exceeds it into the same spent medium before reading.',
            note: 'Blank against spent medium from the same culture, not against fresh medium. Above the linear limit, multiple scattering bends the response and the reading stops being proportional to biomass — which is why the dilution is mandatory rather than optional.',
          },
          {
            id: 'o5',
            text: 'Filter 10 mL of each sample onto its tared filter under 40 kPa of vacuum. Do not let the bed run dry between the sample and the wash, or the retained salt crystallises into the mat and cannot be washed out.',
          },
          {
            id: 'o6',
            text: 'Wash each filter twice with 10 mL of ammonium formate isotonic with the medium; a full run consumes {{qty:Ammonium formate wash solution}}. Ammonium formate removes medium salts and volatilises in the oven, whereas a deionised water wash lyses wall-deficient cells and loses soluble solids.',
          },
          {
            id: 'o7',
            text: 'Dry the loaded filters and the blanks at 105 °C for 4 h, then re-weigh after a further hour to confirm the mass has stopped falling.',
            timerSec: 14400,
            timerLabel: 'Dry to constant mass, 4 h',
          },
          {
            id: 'o8',
            text: 'Compute dry cell weight as (loaded mass − tare − mean blank drift) / 0.010 L. Report in g L⁻¹ to three significant figures and carry the standard deviation of the replicates through to the growth-rate fit.',
          },
          {
            id: 'o9',
            text: 'Sanity-check the magnitude before you trust it. A mixotrophic TAP batch of walled wild-type CC-137c reached a maximum density of 1.23 ± 0.13 g L⁻¹ within 96 h, and a nutrient-optimised culture 1.68 g L⁻¹; heterotrophic microalgal cultures reach 50–100 g L⁻¹ and autotrophic ones around 30 g L⁻¹. A flask result far outside the low single digits is a weighing artefact until it is repeated.',
            refs: ['r-M5-1', 'r-M8-4', 'r-M8-7', 'r-M8-8'],
          },
          {
            id: 'o10',
            text: 'Regress dry cell weight on OD750 through the origin, over the range in which the residuals show no curvature. Report the slope with its confidence interval, the strain, the wavelength, the growth phase and the number of points behind it, and re-determine it whenever any of those change.',
            note: 'OF-COR-001 holds no OD-to-dry-weight factor for cw15, UVM4 or any other C. reinhardtii strain, so there is no literature default and no fallback. Do not carry a factor across wavelengths either: pigment absorbance inflates the optical reading at 680 nm relative to 750 nm, and the two are not interconvertible by a constant.',
          },
          {
            id: 'o11',
            text: 'Enter the factor in the platform as a user measurement, with the run identifier attached. It is your number, not a literature value, and anything computed from it inherits that provenance.',
          },
        ],
        estMinutes: { active: 90, total: 480 },
        references: [
          {
            recordId: 'r-M5-1',
            note: 'Maximum density 1.23 ± 0.13 g L⁻¹ within 96 h, wild-type CC-137c in TAP. Used here as a plausibility bound on a gravimetric result, not as a target.',
          },
          {
            recordId: 'r-M8-4',
            note: '1.68 g L⁻¹ biomass at the response-surface nutrient optimum — the upper end of the flask-scale range in this corpus.',
          },
          {
            recordId: 'r-M8-7',
            note: 'Heterotrophic microalgal cultures can reach 50–100 g L⁻¹ dry biomass — the other end of the scale, and the reason a mixotrophic flask result in that range means a weighing error.',
          },
          {
            paperId: 'M5',
            note: 'Source of the mixotrophic TAP density and productivity figures used as bounds.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-DISRUPT-01 — NEW, replacing the old bead-mill harvest protocol. The
  // economic keystone: J10's 31 ± 6 % vs 11 ± 3 % against J11's mechanical
  // ceiling. Treatment conditions are operator-set; the yields are cited.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-DISRUPT-01',
    title: 'Harvest and mild PEF disruption of cw15',
    category: 'harvest',
    organisms: ['cw15', 'uvm4'],
    bsl: 1,
    purpose:
      'Concentrate a cw15 culture and release intracellular protein by pulsed electric field under mild conditions, scored against a bead-milled arm of the same paste. This is the comparison the cost case for a wall-deficient host rests on: cell-wall deficiency is only an asset if it is cheaper to open the cells.',
    currentVersion: '1.0',
    provenanceNote:
      'Grounded in J10 (PEF on a cell-wall-deficient mutant gave an average protein yield of 31 ± 6 % against 11 ± 3 % for the walled wild type, p < 0.05 — r-J10-1, r-J10-2, roughly three-fold, r-J10-3) and J11 (bead milling and high-pressure homogenisation gave >95 % cell disintegration, approximately 50 % w/w release of total proteins, at under 0.5 kWh per kg biomass — r-J11-1, r-J11-2, r-J11-3; and PEF on walled Chlorella vulgaris released at most 13 % even at 10–100× the energy of bead milling — r-J11-4). OF-COR-001 transcribes those yields but none of the treatment conditions behind them: field strength, pulse width, frequency, specific energy and residence time are set, measured and recorded by the operator.',
    versions: [
      {
        version: '1.0',
      // r-J10-1 records 31% protein release for wall-deficient cells against 11%
      // for the walled wild type — the strongest economic argument for cw15 as
      // the chassis, and the third bar on the S1 tornado. It was measured in a
      // cuvette, not a harvest train.
      decisive: {
        field: 'disruption_protein_yield' as const,
        currentUncertainty:
          'The 31% release for cell-wall-deficient cells under mild PEF comes from one laboratory measurement. Whether it survives a real harvest — concentration, hold time, a flow cell rather than a cuvette — is unrecorded.',
        whatWouldChange:
          'Release below about 20% erases most of the cw15 downstream advantage over a walled strain, and the case for the chassis has to rest on the secretory pathway alone.',
      },
      resultSchema: [
        { id: 'release', field: 'disruption_protein_yield' as const, label: 'Protein released', type: 'number' as const, unit: '% of total protein', required: true },
        { id: 'field_strength', label: 'Field strength applied', type: 'number' as const, unit: 'kV cm⁻¹', required: true },
        { id: 'viability', label: 'Cells visibly lysed under microscopy', type: 'boolean' as const, required: false },
        { id: 'notes', label: 'Deviations from the mild-condition window', type: 'text' as const, required: false },
      ],
        changelog:
          'Initial release. Replaces the previous bead-mill-only harvest protocol, which treated mechanical disruption as the process route. Bead milling is retained here as the comparator arm rather than the product route, because the corpus case for this host is specifically that mild PEF on wall-deficient cells reaches mechanical-scale release without mechanical-scale energy.',
        baseBatch: { value: 10, unit: 'L', label: 'culture' },
        materials: [
          {
            name: 'Low-conductivity resuspension buffer, 1 mM potassium phosphate pH 7.0',
            amount: 1000,
            unit: 'mL',
            scaling: 'per_unit_biomass',
            precision: 50,
          },
          {
            name: 'Protease inhibitor tablets, EDTA-free',
            amount: 5,
            unit: 'tablets',
            scaling: 'per_unit_biomass',
            precision: 1,
          },
          {
            name: '500 mL centrifuge bottles with sealing caps',
            amount: 6,
            unit: 'bottles',
            scaling: 'per_unit_biomass',
            precision: 1,
          },
          {
            name: 'Membrane-impermeant nucleic acid stain',
            amount: 0.5,
            unit: 'mL',
            scaling: 'per_unit_biomass',
            precision: 0.1,
          },
          {
            name: 'Bradford assay reactions',
            amount: 32,
            unit: 'reactions',
            scaling: 'per_unit_biomass',
            precision: 1,
          },
          {
            name: 'Bovine serum albumin standard, 2 mg mL⁻¹',
            amount: 2,
            unit: 'mL',
            scaling: 'fixed',
            precision: 0.1,
          },
          {
            name: '0.4 mm yttria-stabilised zirconia beads',
            amount: 0.2,
            unit: 'L',
            scaling: 'fixed',
            precision: 0.01,
          },
          {
            name: 'Chamber coolant, 30 % v/v propylene glycol',
            amount: 4,
            unit: 'L',
            scaling: 'fixed',
            precision: 0.5,
          },
          {
            name: 'Conductivity standard, 1413 µS cm⁻¹',
            amount: 50,
            unit: 'mL',
            scaling: 'fixed',
            precision: 5,
          },
        ],
        equipment: [
          'Fixed-angle floor centrifuge accepting 500 mL bottles',
          'Continuous pulsed-electric-field treatment chamber with a pulse generator, in-line conductivity measurement and inlet/outlet thermocouples',
          'Peristaltic feed pump rated to 20 L h⁻¹ with a pulsation damper',
          'Recirculating chiller for the treatment loop',
          '0.25 L laboratory bead mill with a jacketed chamber, for the comparator arm',
          'Flow cytometer with a 488 nm excitation line',
          'Spectrophotometer for the Bradford assay',
          'Conductivity meter and an energy meter or the generator’s own kWh log',
        ],
        safety: [
          'The PEF generator charges to several kilovolts and the treatment chamber and wetted lines sit at electrode potential during a pulse train. Break no union in the loop until the generator reads discharged and the earthing stick has been applied to the chamber.',
          'Interlock the pulse train to flow. A stalled pump under an active train boils the liquid in the treatment gap within seconds and can rupture the chamber; confirm the interlock trips before the first real batch of the day.',
          'Feed conductivity is a safety parameter, not only a process one. High-conductivity feed draws current the generator was not sized for. Measure and log the conductivity of every batch of resuspension buffer against the 1413 µS cm⁻¹ standard before the pump starts.',
          'The comparator bead mill holds 0.2 L of 0.4 mm zirconia beads under pressure. Isolate the drive and vent the chamber before opening the end plate, and sweep spilled beads immediately — they behave like ball bearings underfoot and must not be rinsed to drain.',
          'Balance opposing centrifuge bottles to within 1 g and use only sealing caps. A leaking rotor is both an aerosol event and a corrosion event.',
          'Fresh lysate is a nutrient-rich broth. Hold it below 4 °C from the moment of release, assay it the same day, and autoclave all spent material at 121 °C for 20 min.',
        ],
        steps: [
          {
            id: 'd1',
            text: 'Record the feed before touching it. Measure the culture’s dry cell weight under PR-OD-01 and write it on the batch sheet: OF-COR-001 gives no harvest density for cw15, so every yield below is expressed against your measured figure rather than an assumed one.',
          },
          {
            id: 'd2',
            text: 'Draw a 100 mL reference aliquot and hold it at 4 °C undisrupted. Split it: half is the untreated control for soluble protein, half the intact-cell control that sets the cytometry gate.',
            note: 'Every release figure in this protocol is referenced to that aliquot. A control drawn on another day or from another vessel invalidates the score no matter how carefully the gate is drawn.',
          },
          {
            id: 'd3',
            text: 'Concentrate the culture: 4,000 × g for 10 min at 10 °C with the brake set low. Decant into a tared carboy and weigh both fractions so the mass balance across feed, concentrate and centrate closes.',
            timerSec: 600,
            timerLabel: 'Harvest spin, 4,000 × g, 10 min',
            note: 'A hard brake re-suspends the pellet edge, and a wall-deficient pellet resuspends more readily than a walled one. Gravimetric closure is what makes a recovery figure defensible; recovery computed from pellet volume counts interstitial medium as biomass.',
          },
          {
            id: 'd4',
            text: 'Dissolve {{qty:Protease inhibitor tablets, EDTA-free}} inhibitor tablets in {{qty:Low-conductivity resuspension buffer, 1 mM potassium phosphate pH 7.0}} of cold low-conductivity buffer and resuspend the pellets in it. Measure the conductivity of the finished suspension and log it.',
            note: 'Use the EDTA-free formulation: chelated divalent metals carried into a protein assay depress colour development, and the protein figure comes back low for a reason unrelated to disruption. Low conductivity is a PEF requirement — the specific energy delivered per pulse depends on it, so a suspension whose conductivity is not recorded produces a yield that cannot be interpreted.',
          },
          {
            id: 'd5',
            text: 'Split the suspension into a PEF arm and a bead-mill comparator arm from the same paste, on the same day, with the same inhibitor batch.',
            refs: ['r-J10-3', 'r-J11-2'],
            note: 'The comparison is only meaningful within one paste. Note what each arm is for: J10’s roughly three-fold contrast is between wall-deficient and walled cells under PEF, not between PEF and milling. The milling arm here supplies the mechanical ceiling from J11, so that the PEF result can be read against both.',
          },
          {
            id: 'd6',
            text: 'Run the PEF arm on your chamber’s validated microalgae programme. Record field strength, pulse width, frequency, specific energy, flow rate and both inlet and outlet temperatures for the whole pass.',
            refs: ['J10'],
            note: 'This protocol specifies no treatment conditions. OF-COR-001 §11 records J10’s protein yield but not the field strength, pulse parameters or energy input that produced it, so there is nothing to copy and inventing a setting would misrepresent the source. Hold the outlet below 25 °C: "mild" is the entire claim of this route, and a thermal excursion converts it into thermal lysis with a different selectivity.',
          },
          {
            id: 'd7',
            text: 'Hold the treated stream at 4 °C with gentle stirring for 30 min before separation. Release after permeabilisation is diffusive rather than instantaneous, so separating immediately understates the yield.',
            timerSec: 1800,
            timerLabel: 'Post-PEF diffusive hold, 30 min',
          },
          {
            id: 'd8',
            text: 'Run the comparator arm through the bead mill in a single pass, with the chamber charged to 80 % of free volume with {{qty:0.4 mm yttria-stabilised zirconia beads}} of 0.4 mm zirconia beads and the jacket held cold using {{qty:Chamber coolant, 30 % v/v propylene glycol}} of coolant. Log the motor energy and the outlet temperature every minute.',
            refs: ['r-J11-1', 'r-J11-3'],
            note: 'The published mechanical benchmark this arm is standing in for is >95 % cell disintegration at under 0.5 kWh per kg biomass. If your mill does not approach that on this feed, the comparator is mis-set and the PEF arm has nothing to be compared against.',
          },
          {
            id: 'd9',
            text: 'Stain a sample from each arm and from the intact-cell control with {{qty:Membrane-impermeant nucleic acid stain}} of the impermeant stain and count intact cells by flow cytometry, same day, same gate. Score disintegration as fractional loss of intact cells against the control.',
          },
          {
            id: 'd10',
            text: 'Clarify both arms at 10,000 × g for 15 min at 4 °C and assay soluble protein in the supernatants and in the untreated control by Bradford, using {{qty:Bradford assay reactions}} against a curve built from {{qty:Bovine serum albumin standard, 2 mg mL⁻¹}} of albumin standard diluted in the identical buffer.',
            timerSec: 900,
            timerLabel: 'Clarify lysate, 10,000 × g, 15 min',
            note: 'Express release as a percentage of total cell protein and state on the record how total protein was determined. A release percentage whose denominator is undefined is not comparable with the corpus figures or with your own previous run.',
          },
          {
            id: 'd11',
            text: 'Score the PEF arm against the corpus. PEF on cell-wall-deficient cells gave an average protein yield of 31 ± 6 % of total protein, against 11 ± 3 % for the walled wild type; bead milling gives >95 % disintegration and approximately 50 % w/w release. A PEF arm landing near 10 % on a wall-deficient feed is a process fault to be diagnosed, not a strain result to be reported.',
            refs: ['r-J10-1', 'r-J10-2', 'r-J11-1', 'r-J11-2'],
          },
          {
            id: 'd12',
            text: 'Score the energy, which is the half of the argument that decides the cost case. Compute kWh per kg dry biomass for both arms from the generator log and the mill motor log, against the dry cell weight recorded at step d1.',
            refs: ['r-J11-3', 'r-J11-4'],
            note: 'The mechanical benchmark is under 0.5 kWh per kg biomass. A PEF pass that matches the release figure but not the energy figure has not made the economic case. The corpus is explicit about the failure mode: PEF released a maximum of 13 % of protein from walled Chlorella vulgaris even at 10–100× the energy of bead milling — energy without wall deficiency buys nothing.',
          },
          {
            id: 'd13',
            text: 'Report the chain rather than the endpoints: culture → concentrate → treated stream → clarified supernatant, with mass recovery, disintegration score, soluble protein and specific energy at each transition, for both arms.',
            note: 'A protein figure that outruns the disintegration score means the cytometry gate is counting permeabilised cells as intact, or vice versa. Reconcile the two before either number leaves the bench.',
          },
        ],
        estMinutes: { active: 260, total: 470 },
        references: [
          {
            paperId: 'J10',
            note: 'Mild and selective protein release from cell-wall-deficient microalgae by pulsed electric field — the record that converts "cw15 is easy to transform" into "cw15 is cheap to process". Treatment conditions are not transcribed in OF-COR-001.',
          },
          {
            recordId: 'r-J10-1',
            note: 'Average protein yield 31 ± 6 % from the cell-wall-deficient mutant under PEF. Point value entered; the spread is a standard deviation, not a range.',
          },
          {
            recordId: 'r-J10-2',
            note: '11 ± 3 % for the walled wild type — the control that makes the 31 % meaningful. Kept as its own record so the contrast survives aggregation.',
          },
          {
            recordId: 'r-J10-3',
            note: 'Roughly three-fold. A ratio of the two records above, not an independent measurement — do not count it as a third data point.',
          },
          {
            paperId: 'J11',
            note: 'Mechanical disruption benchmarks: bead milling and high-pressure homogenisation on Nannochloropsis gaditana, plus the PEF-on-walled-cells counterexample. Author string flagged [verify] for one of the two gathered sources.',
          },
          {
            recordId: 'r-J11-1',
            note: '>95 % cell disintegration by bead milling or high-pressure homogenisation.',
          },
          {
            recordId: 'r-J11-2',
            note: 'Approximately 50 % w/w release of total proteins — the mechanical ceiling the PEF arm is measured against.',
          },
          {
            recordId: 'r-J11-3',
            note: 'Under 0.5 kWh per kg biomass — the energy benchmark. Different organism (N. gaditana), so treat it as an order-of-magnitude comparator.',
          },
          {
            recordId: 'r-J11-4',
            note: 'PEF released at most 13 % of protein from walled Chlorella vulgaris at 10–100× the energy of bead milling.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-BCN-01 — NEW. Isoelectric capture at pH 4.6. E1 says 4.65, J7 says
  // 4.6; the protocol holds the disagreement rather than averaging it away.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-BCN-01',
    title: 'Isoelectric precipitation of β-casein at pH 4.6',
    category: 'harvest',
    organisms: ['cw15', 'bovine'],
    bsl: 1,
    purpose:
      'Capture recombinant β-casein from a clarified cw15 lysate by acidifying to the isoelectric point, then redissolve the pellet at neutral pH — the cheapest capture step available for a bulk food protein, and one whose precipitation pH doubles as an early phosphorylation readout.',
    currentVersion: '1.0',
    provenanceNote:
      'Grounded in E1 (caseins are heat-stable but precipitate readily at their isoelectric point, pH 4.65, on acidification — r-E1-2) and J7 (solubility surfaces in temperature × pH, quoted in OF-COR-001 §11 as directly usable for isoelectric precipitation of recombinant β-casein at pI 4.6 — r-J7-1). J1 supplies the strategy: conventional chromatography is too costly for bulk food proteins, and cost-effective production means prioritising functionality over purity. The corpus does not transcribe J7’s solubility surface, so the working temperature is chosen, bracketed and recorded by the operator.',
    versions: [
      {
        version: '1.0',
      // The top bar on the S1 tornado at 92.4%: nothing else moves the MSP as
      // much. And it is the axis the corpus cannot speak to at all — A1's ~0.2%
      // TSP is an intracellular reporter, not a casein.
      decisive: {
        field: 'expression_pct_tsp' as const,
        currentUncertainty:
          'No casein has been expressed in a microalga, so every point on the % TSP axis above zero is extrapolation from reporter proteins. A1 records ~0.2% TSP for intracellular GFP/YFP in UVM4 — a reporter ceiling, never measured on a casein.',
        whatWouldChange:
          'This is the most influential parameter in the S1 cost model. Below roughly 0.2% TSP the reference design does not reach a defensible MSP at any biomass density, and the route depends entirely on the 8.6-fold safe-harbour uplift in r-A7-1 being real for this construct.',
      },
      resultSchema: [
        { id: 'pct_tsp', field: 'expression_pct_tsp' as const, label: 'β-casein as % of total soluble protein', type: 'number' as const, unit: '% TSP', required: true },
        { id: 'recovery', label: 'Recovery through the pH 4.6 precipitation', type: 'number' as const, unit: '%', required: true },
        { id: 'redissolved', label: 'Pellet redissolved cleanly at pH 7', type: 'boolean' as const, required: true },
        { id: 'notes', label: 'Observations', type: 'text' as const, required: false },
      ],
        changelog:
          'Initial release. Written as a capture step, not a polishing step. The two corpus values for the isoelectric point (4.65 and 4.6) are carried through to the bench rather than reconciled on paper, and the operator records the pH actually held.',
        baseBatch: { value: 2, unit: 'L', label: 'clarified lysate' },
        materials: [
          {
            name: 'Clarified cw15 lysate',
            amount: 2000,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 50,
          },
          {
            name: 'Hydrochloric acid, 1 M',
            amount: 60,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Sodium hydroxide, 1 M',
            amount: 40,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Wash water adjusted to pH 4.6',
            amount: 400,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Resuspension buffer, 20 mM sodium phosphate pH 7.0',
            amount: 200,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 5,
          },
          {
            name: '250 mL centrifuge bottles',
            amount: 8,
            unit: 'bottles',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Bradford assay reactions',
            amount: 24,
            unit: 'reactions',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Native bovine β-casein reference standard',
            amount: 10,
            unit: 'mg',
            scaling: 'fixed',
            precision: 0.5,
          },
          {
            name: 'pH 4.01 calibration buffer sachet',
            amount: 1,
            unit: 'sachet',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'pH 7.00 calibration buffer sachet',
            amount: 1,
            unit: 'sachet',
            scaling: 'fixed',
            precision: 1,
          },
        ],
        equipment: [
          'Jacketed 3 L glass vessel with a circulating water bath covering 4–40 °C',
          'Overhead stirrer with a pitched-blade impeller',
          'pH meter with an ATC probe and a low-temperature-capable electrode',
          'Syringe pump or peristaltic pump for controlled acid addition',
          'Refrigerated centrifuge accepting 250 mL bottles, rated to 10,000 × g',
          'SDS-PAGE rig and gel imager',
          'Spectrophotometer for the Bradford assay',
        ],
        safety: [
          '1 M hydrochloric acid and 1 M sodium hydroxide are both corrosive and are used within minutes of one another here. Keep the two bottles on opposite sides of the bench so a mis-grab is physically awkward, add acid to the stirred bulk rather than bulk to acid, and wear a face shield for the acidification.',
          'Do not seal the vessel while acidifying. Carbonate carried in from the lysate buffer releases CO₂ as the pH falls, and a closed jacketed vessel will pressurise.',
          'Acidified lysate near room temperature at pH 4.6 is a selective medium for lactic acid bacteria. Work cold, complete the redissolution the same day, and never hold the acidified slurry overnight.',
          'Casein pellets are dense and slippery, and a decanted 250 mL bottle is heavy and wet. Decant over a tray, not over the floor.',
          'The redissolved product is a food protein preparation from a genetically modified organism. It stays inside the process stream — it is not tasted, and it leaves the laboratory only as autoclaved waste or as a labelled analytical sample.',
        ],
        steps: [
          {
            id: 'b1',
            text: 'Calibrate the pH meter at the temperature at which you intend to precipitate, using {{qty:pH 7.00 calibration buffer sachet}} of pH 7.00 buffer and {{qty:pH 4.01 calibration buffer sachet}} of pH 4.01 buffer.',
            note: 'A meter calibrated warm and used cold will miss the isoelectric point by more than the useful window is wide. Calibrate at the working temperature, not at bench temperature.',
          },
          {
            id: 'b2',
            text: 'Choose and record the precipitation temperature. Bracket it first: run three 50 mL trials at three temperatures on your own material and carry the best forward.',
            refs: ['J7'],
            note: 'This protocol names no temperature deliberately. OF-COR-001 records that J7 maps casein solubility across temperature and pH and that the surface is directly usable for isoelectric precipitation, but it does not transcribe the surface. Casein solubility is strongly temperature-dependent near the isoelectric point, so the choice is real and it is yours.',
          },
          {
            id: 'b3',
            text: 'Charge {{qty:Clarified cw15 lysate}} of clarified lysate into the jacketed vessel, equilibrate to the chosen temperature and stir at 150–200 rpm — enough to keep the vessel uniform, not enough to draw in air.',
          },
          {
            id: 'b4',
            text: 'Acidify slowly with {{qty:Hydrochloric acid, 1 M}} of 1 M hydrochloric acid, pumped in beneath the liquid surface at no more than 1 mL min⁻¹ per litre of charge, down to pH 4.60.',
            refs: ['r-E1-2', 'r-J7-1'],
            note: 'Caseins are heat-stable but precipitate readily at their isoelectric point on acidification — the transition is sharp and local over-acidification at the addition point produces fines that never sediment. Slow beats stirring harder.',
          },
          {
            id: 'b5',
            text: 'Stop at pH 4.60 and record the value you actually held, to two decimal places, together with the temperature.',
            refs: ['r-E1-2', 'r-J7-1'],
            note: 'The corpus does not speak with one voice here: E1 states the isoelectric point as pH 4.65 and J7 is quoted for precipitation at pI 4.6. The difference is small but it sits on the steep shoulder of the solubility curve, so "about 4.6" is not a record. Write down the number.',
          },
          {
            id: 'b6',
            text: 'Hold at the setpoint for 30 min with gentle stirring so the precipitate coarsens before separation.',
            timerSec: 1800,
            timerLabel: 'Isoelectric hold, 30 min',
          },
          {
            id: 'b7',
            text: 'Transfer to {{qty:250 mL centrifuge bottles}} and centrifuge at 5,000 × g for 15 min at the precipitation temperature. Keep the supernatant — it is assayed, not discarded.',
            timerSec: 900,
            timerLabel: 'Recover precipitate, 5,000 × g, 15 min',
          },
          {
            id: 'b8',
            text: 'Wash the pellet twice by resuspending in {{qty:Wash water adjusted to pH 4.6}} of water pre-adjusted to pH 4.6 and re-centrifuging. Washing with unadjusted water redissolves product at the pellet surface.',
          },
          {
            id: 'b9',
            text: 'Redissolve the washed pellet in {{qty:Resuspension buffer, 20 mM sodium phosphate pH 7.0}} of phosphate buffer, adding {{qty:Sodium hydroxide, 1 M}} of 1 M sodium hydroxide dropwise with stirring until the suspension clears at pH 7.0. Do not overshoot past pH 8.',
          },
          {
            id: 'b10',
            text: 'Assay the redissolved product, the pooled supernatant and the wash by Bradford using {{qty:Bradford assay reactions}}, and run all three on SDS-PAGE beside {{qty:Native bovine β-casein reference standard}} of the native bovine β-casein standard.',
            note: 'The supernatant assay is what tells you whether the step worked. A clean pellet with most of the target still in the supernatant is a failed capture that looks like a successful one.',
          },
          {
            id: 'b11',
            text: 'Read an unexpected precipitation pH as data, not as a failure of this protocol. If the bulk of the material comes down nearer pH 5.5 than 4.6, stop and run PR-PHOS-01 before changing anything here.',
            refs: ['r-I1-2'],
            note: 'Fully dephosphorylated caseins precipitate at their isoelectric point around pH 5.5 and hardly form micelle structures at all. A shifted precipitation pH is the cheapest early indication available that the phosphorylation programme has not worked — cheaper than a gel and far cheaper than an assembly run.',
          },
          {
            id: 'b12',
            text: 'Close the record: mass in, mass out, precipitation pH, temperature, and the fraction of feed protein captured. State the concentration the product came in at.',
            refs: ['r-E1-1', 'J1'],
            note: 'Scale context: β-casein is present in bovine milk at roughly 2.6 g L⁻¹, and a cw15 lysate is orders of magnitude below that. This step is capture from a dilute stream, not polishing of a concentrated one — which is exactly why J1 argues that bulk food proteins cannot carry conventional chromatography and that functionality, not purity, is the specification to design against.',
          },
        ],
        estMinutes: { active: 180, total: 330 },
        references: [
          {
            paperId: 'E1',
            note: 'Bovine β-casein review: isolation, properties and functionality. The corpus’s most useful reference-value source for this molecule.',
          },
          {
            recordId: 'r-E1-2',
            note: 'Caseins precipitate readily at their isoelectric point, pH 4.65, on acidification. Curated, unverified.',
          },
          {
            recordId: 'r-E1-1',
            note: 'β-casein present at roughly 2.6 g L⁻¹ in bovine milk — the concentration scale this unit operation was developed at.',
          },
          {
            paperId: 'J7',
            note: 'Solubility of caseins as a function of temperature and pH. The surface itself is not transcribed in OF-COR-001, which is why step b2 brackets rather than specifies.',
          },
          {
            recordId: 'r-J7-1',
            note: 'Quoted for isoelectric precipitation of recombinant β-casein at pI 4.6 — the second, slightly different value the protocol deliberately preserves.',
          },
          {
            recordId: 'r-I1-2',
            note: 'Fully dephosphorylated caseins precipitate at their isoelectric point around pH 5.5 — the diagnostic behind step b11.',
          },
          {
            paperId: 'J1',
            note: 'Downstream processing of food proteins from precision fermentation: chromatography is too costly for bulk food proteins; prioritise functionality over purity.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-PHOS-01 — NEW. The assay the whole programme is judged on. Phos-tag
  // from H1's method review; urea-PAGE + phosphatase because H4 used exactly
  // that pairing (r-H4-4). A mobility shift is never a phosphate count.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-PHOS-01',
    title: 'Phos-tag phosphorylation analysis of recombinant β-casein',
    category: 'analytics',
    organisms: ['cw15', 'gs115', 'bovine'],
    bsl: 1,
    purpose:
      'Establish whether a recombinant β-casein preparation carries phosphate, and how heterogeneous the population is, by Phos-tag SDS-PAGE against a phosphatase-treated companion, with urea-PAGE ± phosphatase as the orthogonal check. This is the assay that says whether the programme worked: an unphosphorylated casein will not reassemble into micelles, will not bind calcium as it should, and will not gel.',
    currentVersion: '1.0',
    provenanceNote:
      'Grounded in H1, which reviews the four phosphorylation-analysis methods used across the heterologous-casein literature — MALDI-MS / LC-ESI-MS, SDS-PAGE with Ethyl Stains-All, urea-PAGE with phosphatase treatment, and Phos-tag — and records "undetermined" for most bacterial studies because the analysis was never done. The orthogonal check is the pairing H4 used: phosphatase treatment plus urea-PAGE, showing its Pichia-expressed bovine β-casein carried the same degree of phosphorylation as animal-derived β-casein (r-H4-4). OF-COR-001 transcribes no gel recipe or run condition, so acrylamide percentage, Phos-tag and Mn²⁺ concentrations and run conditions come from the reagent supplier and are recorded per run.',
    versions: [
      {
        version: '1.0',
      // The central open question of the whole programme. D5 asks whether
      // C. reinhardtii encodes a Fam20-family kinase at all, and no casein has
      // been published in any microalga — so nothing in the corpus can answer
      // this by argument. Only this assay can.
      decisive: {
        field: 'phosphorylation_degree' as const,
        currentUncertainty:
          'No record in this corpus reports the phosphorylation degree of a β-casein made in any alga, because none has been made. Whether C. reinhardtii phosphorylates the Ser-x-Glu motifs at all is open — D5 asks whether it even encodes a Fam20-family kinase, and that search has not been run.',
        whatWouldChange:
          'A degree at or near the 5 mol/mol of the bovine protein makes the cw15 route viable without co-expressing a kinase. A degree near zero means every design needs FAM20C alongside the casein, which changes the construct, the strain and the cost model together.',
      },
      resultSchema: [
        { id: 'degree', field: 'phosphorylation_degree' as const, label: 'Phosphorylation degree', type: 'number' as const, unit: 'mol mol⁻¹', required: true },
        { id: 'shifted', label: 'Phos-tag band shift observed', type: 'boolean' as const, required: true },
        { id: 'bands', label: 'Distinct shifted species counted', type: 'number' as const, unit: '', required: false },
        { id: 'notes', label: 'Gel notes', type: 'text' as const, required: false },
      ],
        changelog:
          'Initial release. Written so that the result it produces is interpretable in this platform’s ontology: every phosphorylation value entered from this protocol carries its analysis method, and "undetermined" remains available and legitimate for anything the run did not actually measure.',
        baseBatch: { value: 10, unit: 'lanes', label: 'per gel pair' },
        materials: [
          {
            name: 'Purified recombinant β-casein sample',
            amount: 100,
            unit: 'µg',
            scaling: 'per_batch_volume',
            precision: 5,
          },
          {
            name: 'Native bovine β-casein reference standard',
            amount: 50,
            unit: 'µg',
            scaling: 'per_batch_volume',
            precision: 5,
          },
          {
            name: 'Phos-tag acrylamide',
            amount: 50,
            unit: 'µL',
            scaling: 'per_batch_volume',
            precision: 5,
          },
          {
            name: 'Manganese(II) chloride, 10 mM',
            amount: 500,
            unit: 'µL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Alkaline phosphatase, calf intestinal',
            amount: 40,
            unit: 'units',
            scaling: 'per_batch_volume',
            precision: 1,
            stock: { conc: 10, unit: 'µL' },
          },
          {
            name: 'Acrylamide/bis solution, 30 % 37.5:1',
            amount: 20,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Urea, molecular biology grade',
            amount: 25,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.1,
          },
          {
            name: 'EDTA soak solution, 10 mM',
            amount: 200,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Coomassie R-250 staining solution',
            amount: 100,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Ethyl Stains-All reagent',
            amount: 25,
            unit: 'mL',
            scaling: 'fixed',
            precision: 5,
          },
          {
            name: 'Protein ladder, 10–250 kDa',
            amount: 100,
            unit: 'µL',
            scaling: 'fixed',
            precision: 10,
          },
        ],
        equipment: [
          'Two mini-gel casting and running rigs, so the Phos-tag and urea gels run in parallel',
          'Power supply capable of a constant 100 V for an extended cold run',
          '4 °C cabinet or cold room large enough to hold a running gel rig',
          'Gel documentation system with white-light and fluorescence capture',
          'Heat block at 37 °C and a second at 95 °C',
          'Orbital shaker for gel soaks and staining',
        ],
        safety: [
          'Unpolymerised acrylamide is a cumulative neurotoxin and is absorbed through intact skin. Cast gels in a fume hood in double nitrile gloves, use only the pre-made 30 % solution rather than weighing powder, and treat casting waste and every unpolymerised drop as hazardous.',
          'Phos-tag gels are manganese-loaded. Collect the EDTA soak, the run buffer and the gel itself as heavy-metal waste rather than pouring them to drain.',
          'Ethyl Stains-All is light-sensitive and stains skin, bench surfaces and clothing persistently. Work in subdued light over a bench liner and dispose of the used stain into organic solvent waste.',
          'Do not heat urea gels or urea-containing samples above 55 °C at any point. Urea decomposes to cyanate, which carbamylates lysine residues and shifts the very mobility this assay is reading — a carbamylation artefact looks exactly like partial phosphorylation.',
          'Methanol in the staining and destaining solutions is toxic by inhalation and skin contact. Stain and destain in a fume hood or a ducted staining box, with the lid on the tray whenever it is not being handled.',
        ],
        steps: [
          {
            id: 'f1',
            text: 'Build the panel before touching a gel. You need four things on one gel: the recombinant sample, the {{qty:Native bovine β-casein reference standard}} native standard, a phosphatase-treated aliquot of each, and a mock-treated aliquot that has seen the phosphatase buffer but no enzyme.',
            note: 'The mock is not optional. Phosphatase buffer alone changes casein mobility on a Phos-tag gel enough to be misread as partial dephosphorylation, and without the mock you cannot tell the two apart.',
          },
          {
            id: 'f2',
            text: 'Dephosphorylate the treated aliquots: add {{stock:Alkaline phosphatase, calf intestinal}} of calf intestinal alkaline phosphatase ({{qty:Alkaline phosphatase, calf intestinal}} across the panel) and incubate at 37 °C for 2 h. Run the mock alongside on the same block.',
            timerSec: 7200,
            timerLabel: 'Phosphatase digest, 37 °C, 2 h',
          },
          {
            id: 'f3',
            text: 'Cast the Phos-tag gel from {{qty:Acrylamide/bis solution, 30 % 37.5:1}} of 30 % acrylamide/bis with {{qty:Phos-tag acrylamide}} of Phos-tag acrylamide and {{qty:Manganese(II) chloride, 10 mM}} of 10 mM manganese chloride, at the supplier’s stated ratio for a protein of this size. Cast a matched conventional gel with no Phos-tag as the mobility reference.',
            refs: ['H1'],
            note: 'OF-COR-001 records only that H1 reviews Phos-tag as one of four phosphorylation-analysis methods; it transcribes no gel composition, no Phos-tag concentration and no run conditions. Take them from the supplier’s table, write the numbers you used onto the gel image, and hold them constant between runs — mobilities from differently composed gels are not comparable.',
          },
          {
            id: 'f4',
            text: 'Run both gels cold and slow: 100 V at 4 °C until the dye front reaches the bottom. Heat is what smears a Phos-tag gel, and a smeared ladder is uninterpretable rather than merely ugly.',
          },
          {
            id: 'f5',
            text: 'Soak the Phos-tag gel three times for 10 min each in {{qty:EDTA soak solution, 10 mM}} of 10 mM EDTA before staining or transfer. Manganese left in the gel blocks transfer and stains unevenly.',
            timerSec: 600,
            timerLabel: 'EDTA soak, 10 min (repeat ×3)',
          },
          {
            id: 'f6',
            text: 'Stain both gels with {{qty:Coomassie R-250 staining solution}} of Coomassie R-250, destain to a clear background and image them under identical settings with the {{qty:Protein ladder, 10–250 kDa}} ladder in view.',
          },
          {
            id: 'f7',
            text: 'Read the Phos-tag gel as a mobility ladder, and say so in the record. A phosphorylated preparation resolves into a retarded ladder that collapses to a single fast band on phosphatase treatment; the ladder establishes that phosphate is present and that the population is heterogeneous.',
            refs: ['H1'],
            note: 'It does not establish how many phosphates. Only mass spectrometry counts them. H1 records "undetermined" for most of the bacterial studies it tabulates precisely because the analysis was never done — and in this platform "undetermined" means the measurement was not made, which is a different claim from a measured zero.',
          },
          {
            id: 'f8',
            text: 'Run the orthogonal check: urea-PAGE with {{qty:Urea, molecular biology grade}} of urea, loading the untreated and phosphatase-treated pairs of both the sample and the native standard on one gel, and read the mobility shift on dephosphorylation.',
            refs: ['r-H4-4', 'H6'],
            note: 'This is the exact pairing H4 used — phosphatase treatment plus urea-PAGE — to establish that its Pichia-expressed bovine β-casein carried the same degree of phosphorylation as animal-derived β-casein. H6 reports the same style of result in S. cerevisiae: identical urea-gel mobilities before and after dephosphorylation. Two independent readouts agreeing is the standard this assay is held to.',
          },
          {
            id: 'f9',
            text: 'Optionally confirm band identity as phosphoprotein with {{qty:Ethyl Stains-All reagent}} of Ethyl Stains-All on a conventional SDS-PAGE gel. Treat it as a fast qualitative confirmation and never as a quantity.',
            refs: ['H1'],
          },
          {
            id: 'f10',
            text: 'State the target explicitly when you report. Fully phosphorylated bovine β-casein carries about 5 phosphates, clustered at the N-terminus; a preparation whose ladder tops out well short of the native standard’s is partially phosphorylated.',
            refs: ['r-F5-1', 'H3'],
            note: 'Partial phosphorylation is a published outcome, not an anomaly: H3 co-expressed bovine β-casein with CK2 in E. coli and reached much lower phosphorylation than the native 5P state, because only some of the bovine cluster serines sit in canonical CK2 sites. H4 is the full-phosphorylation outcome. Knowing which of the two you have is the entire point of this protocol.',
          },
          {
            id: 'f11',
            text: 'Escalate to mass spectrometry when the programme needs a number rather than a comparison, or when the ladder is ambiguous. Send material for LC-ESI-MS or MALDI-MS and record which was used.',
            refs: ['H1'],
          },
          {
            id: 'f12',
            text: 'Enter the result with its method attached, and with the residue-numbering convention if you report site positions. A phosphorylation value without its analysis method is not interpretable in this platform and will be rejected at entry.',
            refs: ['F1'],
            note: 'Numbering matters: bovine β-casein is 224 residues as translated and 209 after signal-peptide removal, so mature and precursor positions differ by 15. Every site position must say which convention it uses.',
          },
        ],
        estMinutes: { active: 300, total: 620 },
        references: [
          {
            paperId: 'H1',
            note: 'The keystone review of heterologous caseins and phosphorylation. Source of the four-method framing used here, and of the finding that most bacterial studies record "undetermined" because the analysis was never performed.',
          },
          {
            paperId: 'H4',
            note: 'Bovine β-casein in Pichia pastoris — the closest eukaryotic precedent, and the study whose phosphatase + urea-PAGE pairing step f8 reproduces.',
          },
          {
            recordId: 'r-H4-4',
            note: 'Recombinant protein carried the same degree of phosphorylation as animal-derived β-casein, by urea-PAGE with phosphatase treatment. Curated, unverified.',
          },
          {
            paperId: 'H6',
            note: 'Bovine β-casein in S. cerevisiae: identical urea-gel mobilities before and after dephosphorylation — the second precedent for the orthogonal check.',
          },
          {
            paperId: 'H3',
            note: 'The companion negative result: bovine β-casein co-expressed with CK2 in E. coli reached much lower phosphorylation than the native 5P state.',
          },
          {
            recordId: 'r-F5-1',
            note: 'β-casein carries approximately 5 phosphates concentrated at the N-terminus — the success criterion stated numerically. Method recorded as undetermined in the corpus.',
          },
          {
            paperId: 'F1',
            note: '224-residue primary translation product, 209-residue mature protein — the source of the numbering caveat in step f12.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-ACM-01 — NEW. Artificial casein micelle assembly. I3 for rate control,
  // I4 for the scalable routes; scored against I1's 87 % sedimentable.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-ACM-01',
    title: 'Artificial casein micelle assembly',
    category: 'harvest',
    organisms: ['bovine', 'cw15'],
    bsl: 1,
    purpose:
      'Assemble purified β-casein with κ-casein and calcium phosphate into artificial casein micelles by a rate-controlled, scalable route, then score the product by particle size and sedimentable fraction — the functional test that separates a recombinant casein that behaves like a dairy ingredient from one that merely runs at the right size on a gel.',
    currentVersion: '1.0',
    provenanceNote:
      'Grounded in I3 (micellar diameter is controllable by preparation rate during assembly) and I4 (casein micelle formation treated as a calcium phosphate phase separation process, with vacuum evaporation and membrane routes replacing the unscalable dropwise-mixing method). The reference geometry is E2 (approximately spherical, radius ~70 nm — r-E2-1); the scoring benchmark is I1 (roughly 87 % of total protein sedimentable in the fully phosphorylated case — r-I1-1); the failure signature is I2 (predominantly dephosphorylated casein forms irregular structures roughly three times larger than normal — r-I2-1). OF-COR-001 transcribes no rate–diameter relationship and no mixing recipe, so the rate ladder is built on your own material.',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Dropwise mixing is excluded as a route on the corpus’s own grounds — I4 replaces it precisely because it does not scale — so the protocol offers the two scalable alternatives and requires the operator to record which was used.',
        baseBatch: { value: 500, unit: 'mL', label: 'assembly batch' },
        materials: [
          {
            name: 'Purified β-casein (recombinant or native)',
            amount: 2.5,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.05,
          },
          {
            name: 'Purified κ-casein',
            amount: 0.37,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
            sourceRecordId: 'r-F4-3',
          },
          {
            name: 'Sodium phosphate buffer, 20 mM pH 7.0',
            amount: 500,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Calcium chloride dihydrate',
            amount: 1.47,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
            stock: { conc: 0.0735, unit: 'mL' },
          },
          {
            name: 'Dipotassium hydrogen phosphate',
            amount: 0.87,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
            stock: { conc: 0.087, unit: 'mL' },
          },
          {
            name: '0.22 µm bottle-top filter units',
            amount: 2,
            unit: 'units',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Diafiltration cassette, 10 kDa cut-off',
            amount: 1,
            unit: 'cassette',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Low-volume DLS cuvettes',
            amount: 12,
            unit: 'cuvettes',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Bradford assay reactions',
            amount: 24,
            unit: 'reactions',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Sodium azide preservative, 2 % w/v',
            amount: 5,
            unit: 'mL',
            scaling: 'fixed',
            precision: 0.5,
          },
        ],
        equipment: [
          'Jacketed stirred vessel with an overhead stirrer and a circulating bath',
          'Calibrated syringe pump or metering peristaltic pump for rate-controlled delivery',
          'Rotary evaporator or vacuum concentrator with a bath controllable below 40 °C',
          'Tangential-flow filtration rig with a 10 kDa membrane and inlet/retentate gauges',
          'Dynamic light scattering instrument',
          'Refrigerated centrifuge capable of 25,000 × g',
          'pH meter with an ATC probe',
          'Spectrophotometer for the Bradford assay',
        ],
        safety: [
          'Sodium azide is acutely toxic and forms shock-sensitive heavy-metal azides in copper and lead plumbing. Add it only to material destined for storage, never to anything that will be poured to drain, and label every azide-containing bottle at the moment it is made.',
          'Rotary evaporation of a protein solution foams without warning and a foam-over contaminates the vacuum line and destroys the batch. Keep the bath below 40 °C, fit a bump trap, and do not leave the flask under full vacuum unattended.',
          'Dissolving calcium chloride is strongly exothermic. Make the stock in a beaker standing in a water bath, never directly in the assembly vessel with protein present.',
          'The TFF pump develops several bar behind a blinded membrane. Confirm the retentate valve is open before starting and watch the inlet gauge through the first minute of every run.',
          'Micelle suspensions containing recombinant protein are process material, not food. They are not tasted; they leave the laboratory as labelled analytical samples or as autoclaved waste.',
        ],
        steps: [
          {
            id: 'a1',
            text: 'Dissolve {{qty:Purified β-casein (recombinant or native)}} of β-casein and {{qty:Purified κ-casein}} of κ-casein in {{qty:Sodium phosphate buffer, 20 mM pH 7.0}} of 20 mM sodium phosphate buffer at pH 7.0, stirring gently at 4 °C overnight, then filter through the {{qty:0.22 µm bottle-top filter units}} filter units.',
            refs: ['r-F4-3', 'E6'],
            note: 'β-casein alone does not make a micelle that stops growing. κ-casein makes up about 13 % of total caseins, sits mostly at the micelle surface and is the calcium-insensitive fraction that caps growth; the ratio here follows that proportion. Leave it out and you get aggregates, not micelles.',
          },
          {
            id: 'a2',
            text: 'Equilibrate the solution at the assembly temperature you have chosen and record it, together with the measured pH after equilibration.',
          },
          {
            id: 'a3',
            text: 'Choose the assembly route and write it on the batch sheet: Route A, vacuum evaporation (step a4), or Route B, membrane transport (step a5). Do not assemble by dropwise mixing.',
            refs: ['I4'],
            note: 'OF-COR-001 §10 records that I4 treats micelle formation as a calcium phosphate phase separation process and replaces the dropwise-mixing method with vacuum evaporation and membrane routes specifically because dropwise mixing does not scale. A method excluded on scalability grounds should not be the one a process protocol teaches.',
          },
          {
            id: 'a4',
            text: 'Route A — vacuum evaporation. Make the protein solution up to twice its final volume, add {{stock:Calcium chloride dihydrate}} of 0.5 M calcium chloride ({{qty:Calcium chloride dihydrate}} as the salt) and {{stock:Dipotassium hydrogen phosphate}} of 0.5 M dipotassium hydrogen phosphate ({{qty:Dipotassium hydrogen phosphate}} as the salt) while the mineral is still undersaturated, then concentrate under vacuum below 40 °C at a controlled rate until the target protein concentration is reached.',
            note: 'The supersaturation that drives phase separation is generated by removing water, not by adding reagent. That is the whole point of the route: the mineral arrives everywhere at once instead of at the tip of a dropper.',
          },
          {
            id: 'a5',
            text: 'Route B — membrane. Hold the protein solution in the retentate of the {{qty:Diafiltration cassette, 10 kDa cut-off}} 10 kDa cassette and diafiltrate against a permeate carrying calcium and phosphate at the target activity, so that mineral arrives at the protein by transport across the membrane at a rate you set with the permeate flux.',
            refs: ['I4'],
          },
          {
            id: 'a6',
            text: 'Build a rate ladder rather than running one condition. Run at least three preparation rates spanning an order of magnitude, on the same material, on the same day, with everything else held constant.',
            refs: ['I3'],
            note: 'I3 records that micellar diameter is controllable by preparation rate during assembly. OF-COR-001 does not transcribe the relationship — no slope, no direction, no range — so the ladder is how you obtain it for your own material rather than assuming it.',
          },
          {
            id: 'a7',
            text: 'Measure particle size by DLS in {{qty:Low-volume DLS cuvettes}}, diluting in the assembly buffer and never in water. Report the z-average diameter and the polydispersity index against the preparation rate that produced them.',
            refs: ['r-E2-1'],
            note: 'Reference geometry: native casein micelles are approximately spherical with a radius of about 70 nm — a diameter near 140 nm — containing on the order of 10,000 casein molecules. Diluting into water strips the mineral phase and you will measure the dissociation, not the micelle.',
          },
          {
            id: 'a8',
            text: 'Score the micellar fraction. Centrifuge at 25,000 × g for 60 min, assay protein in the supernatant by Bradford ({{qty:Bradford assay reactions}} across the batch), and express the sedimentable fraction as a percentage of the protein charged.',
            timerSec: 3600,
            timerLabel: 'Sediment micelles, 25,000 × g, 60 min',
            refs: ['r-I1-1'],
            note: 'The benchmark: in I1’s reassembly experiments roughly 87 % of total protein was sedimentable in the fully phosphorylated case, across all three systems, while fully dephosphorylated caseins hardly formed micelle structures at all and remained in the serum. That 87 % is the number this step is scored against.',
          },
          {
            id: 'a9',
            text: 'Read a bad batch correctly before you change the mixing. A large diameter with a wide polydispersity index and a low sedimentable fraction is a phosphorylation result, not a mixing result — go back to PR-PHOS-01 rather than re-tuning the pump.',
            refs: ['r-I2-1'],
            note: 'Artificial micelles built predominantly from dephosphorylated casein form irregular structures roughly three times larger than normal. Micelle reassembly ability is proportional to phosphorylation degree; the assembly rig cannot compensate for a protein that lacks its phosphate centre.',
          },
          {
            id: 'a10',
            text: 'Record the result as a complete claim or not at all: phosphorylation state and the method that established it, protein source and purity, assembly route, preparation rate, temperature, pH, diameter, polydispersity and sedimentable fraction.',
            refs: ['r-I9-2'],
            note: 'OF-COR-001 §10 records that artificial-micelle formation from recombinant caseins has so far been unsuccessful, largely for post-translational-modification reasons. A successful assembly here would be a novel result, and a novel result reported without its phosphorylation method attached is not evidence of anything.',
          },
          {
            id: 'a11',
            text: 'Preserve only what is going to analysis: add {{qty:Sodium azide preservative, 2 % w/v}} of 2 % sodium azide to a final 0.02 % w/v in analytical samples held beyond the working day, and keep those samples physically separate from any material destined for functional or sensory work.',
          },
        ],
        estMinutes: { active: 330, total: 1500 },
        references: [
          {
            paperId: 'I3',
            note: 'Preparation rate and coagulation properties: micellar diameter is controllable by preparation rate during assembly. The relationship itself is not transcribed in OF-COR-001.',
          },
          {
            paperId: 'I4',
            note: 'Casein micelle formation as a calcium phosphate phase separation process; vacuum evaporation and membrane routes replace the unscalable dropwise-mixing method. The unit operation that would sit downstream of a cw15 fermentation.',
          },
          {
            recordId: 'r-I1-1',
            note: 'Roughly 87 % of total protein sedimentable in the fully phosphorylated case — the scoring benchmark for step a8.',
          },
          {
            recordId: 'r-I2-1',
            note: 'Predominantly dephosphorylated artificial micelles form irregular structures roughly three times larger than normal — the failure signature in step a9.',
          },
          {
            recordId: 'r-E2-1',
            note: 'Native micelle geometry: approximately spherical, radius ~70 nm (entered as a 140 nm diameter). Method recorded as undetermined.',
          },
          {
            recordId: 'r-F4-3',
            note: 'κ-casein ≈ 13 % of total caseins — the basis for the κ:β ratio charged at step a1.',
          },
          {
            paperId: 'E6',
            note: 'κ-casein sits mostly at the micelle surface and limits micelle growth; α- and β-caseins sit inside and bind calcium phosphate.',
          },
          {
            recordId: 'r-I9-2',
            note: 'ACM formation from recombinant caseins has so far been unsuccessful, largely for PTM reasons. The prior this protocol is run against.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-CIP-01 — the pure-checklist pattern, kept. Laboratory practice rather
  // than literature: cited to N3 because a production-process record is
  // exactly what the EFSA dossier was found to be missing.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-CIP-01',
    title: 'Benchtop bioreactor CIP and sterilization SOP',
    category: 'sop',
    organisms: ['cw15', 'gs115'],
    bsl: 1,
    purpose:
      'Clean, inspect, reassemble and sterilise a benchtop bioreactor between runs, and record the checks that make the next batch’s sterility failure diagnosable rather than mysterious.',
    currentVersion: '1.0',
    provenanceNote:
      'This SOP is laboratory practice, not a literature transcription: OF-COR-001 contains no cleaning or sterilisation procedure and this protocol claims none. It is cited to N3 because EFSA could not establish the safety of a C. reinhardtii novel food after identifying data gaps across identity, production process and specifications — a production-process record is precisely what a dossier of that kind stands on — and to B5 for the shear constraint that governs impeller and sparger choice on this line.',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Written to serve both the photobioreactor and fermentation lines; consumable quantities are per cleaning cycle and do not scale with the batch the vessel last held.',
        baseBatch: { value: 1, unit: 'vessel', label: 'per cycle' },
        materials: [
          {
            name: 'Alkaline CIP detergent concentrate',
            amount: 100,
            unit: 'mL',
            scaling: 'fixed',
            precision: 5,
          },
          {
            name: 'Deionised water for rinsing',
            amount: 30,
            unit: 'L',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'Phosphoric acid rinse, 1 % v/v',
            amount: 5,
            unit: 'L',
            scaling: 'fixed',
            precision: 0.5,
          },
          {
            name: 'Headplate O-ring set, silicone',
            amount: 1,
            unit: 'set',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'Triclamp gasket set, 25 mm',
            amount: 1,
            unit: 'set',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: '0.2 µm inlet air filter',
            amount: 1,
            unit: 'filter',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: '0.2 µm exhaust filter',
            amount: 1,
            unit: 'filter',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'pH calibration buffer sachets, 4.01 and 7.00',
            amount: 2,
            unit: 'sachets',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'Dissolved-oxygen probe electrolyte',
            amount: 5,
            unit: 'mL',
            scaling: 'fixed',
            precision: 0.5,
          },
          {
            name: 'Silicone grease, food grade',
            amount: 5,
            unit: 'g',
            scaling: 'fixed',
            precision: 0.5,
          },
          {
            name: 'Autoclave indicator tape',
            amount: 1,
            unit: 'strip',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'Biological indicator spore strip',
            amount: 1,
            unit: 'strip',
            scaling: 'fixed',
            precision: 1,
          },
        ],
        equipment: [
          'CIP recirculation pump with a 25 mm sanitary connection and a spray ball fitting',
          'Immersion heater or jacket circuit capable of 60 °C on the cleaning solution',
          'Conductivity meter and pH meter for rinse-water verification',
          'Borescope or a bright inspection lamp for the headplate underside and the sparger',
          'Torque wrench set to the vessel manufacturer figure',
          'Autoclave with a 121 °C cycle sized for the assembled vessel',
          '55 °C incubator for reading the biological indicator',
        ],
        safety: [
          'Alkaline CIP detergent at working strength is a strong caustic. Wear a face shield, chemical apron and long-cuff nitrile gloves for the whole recirculation step; an eye splash requires 15 min of irrigation and medical review.',
          'Never follow caustic with acid without an intervening rinse to neutral. Mixing the two in the vessel generates heat and a violent gas release.',
          'Confirm the vessel is at atmospheric pressure and below 40 °C before loosening any triclamp. A headplate released under residual pressure travels.',
          'Do not autoclave the vessel with a closed vent filter, a clamped exhaust or a fully tightened sample-port cap. Each of those turns the vessel into a sealed pressure vessel.',
          'Sterilise at 121 °C for 45 min and break no connection until the chamber reads below 80 °C and the pressure gauge has returned to zero.',
          'The exhaust condenser and sparge line hold heat long after the broth is cool. Handle them with heat-resistant gloves and let the vessel stand 20 min before moving it; the display reads the liquid, not the metal.',
          'Check the dissolved-oxygen probe data sheet before discarding spent electrolyte. Older galvanic probes use a lead anode and their electrolyte is not drain-legal.',
        ],
        steps: [
          {
            id: 'c1',
            text: 'Isolate the vessel and drain it. Work through the isolation checklist before touching a single fitting.',
            multiCheck: [
              'Controller in manual, all control loops off',
              'Gas supply isolated at the wall and the line bled to atmosphere',
              'Jacket circuit isolated and the vessel below 40 °C',
              'Feed, acid, base and antifoam pumps stopped and their lines clamped',
              'Broth drained to the kill tank and the drain valve confirmed closed',
              'Vessel confirmed at atmospheric pressure through the vent filter',
            ],
          },
          {
            id: 'c2',
            text: 'Strip the vessel. Remove every wetted part and lay it out on a clean tray in the order it came off.',
            multiCheck: [
              'pH and dissolved-oxygen probes removed, rinsed and stored in their keeper solutions',
              'Exhaust condenser and both filters removed and set aside for replacement',
              'Sample port, septum port and harvest dip tube removed',
              'Impeller shaft, impellers and baffles removed',
              'Ring sparger removed and its holes checked against a light',
              'Headplate lifted, inverted and set on a clean support',
            ],
          },
          {
            id: 'c3',
            text: 'Pre-rinse the vessel body and all removed parts with deionised water at ambient temperature until the effluent runs clear. Budget roughly half of the {{qty:Deionised water for rinsing}} allocated for this cycle to the pre-rinse and the post-rinse together.',
            note: 'Pre-rinse cold. Hot water bakes protein onto the glass and the headplate underside, and no subsequent caustic step fully recovers a baked film.',
          },
          {
            id: 'c4',
            text: 'Make up the cleaning solution from {{qty:Alkaline CIP detergent concentrate}} of alkaline detergent concentrate in 5 L of deionised water, heat it to 60 °C and recirculate it through the spray ball and every dead leg for 20 min.',
            timerSec: 1200,
            timerLabel: 'Recirculate alkaline detergent, 20 min',
          },
          {
            id: 'c5',
            text: 'Drain the detergent to the neutralisation tank and rinse to neutral. Confirm the rinse is complete before any acid enters the vessel.',
            multiCheck: [
              'Effluent pH within 0.5 units of the incoming deionised water',
              'Effluent conductivity within 20 µS cm⁻¹ of the incoming water',
              'No foam visible in the effluent stream',
              'Sight glass and headplate underside free of film under the inspection lamp',
            ],
          },
          {
            id: 'c6',
            text: 'Recirculate {{qty:Phosphoric acid rinse, 1 % v/v}} of 1 % phosphoric acid for 10 min to remove mineral scale from the sparger and the probe ports, then rinse to neutral again with deionised water.',
            timerSec: 600,
            timerLabel: 'Acid rinse, 10 min',
            note: 'Skip the acid rinse only if the last run was a photobioreactor batch on TAP. Skip it never after a mineral-salts fermentation, where calcium and magnesium sulfate scale forms under the sparger within one campaign.',
          },
          {
            id: 'c7',
            text: 'Inspect and replace the elastomers, drawing on the {{qty:Headplate O-ring set, silicone}} headplate O-ring set and the {{qty:Triclamp gasket set, 25 mm}} triclamp gasket set. Every seal below is replaced on a fixed cycle, not on appearance.',
            multiCheck: [
              'Headplate O-ring replaced and seated square in its groove',
              'All 25 mm triclamp gaskets replaced, none reused across a cycle',
              'Probe port O-rings inspected for compression set and swelling',
              'Glass vessel inspected for chips at the rim and star cracks at the base',
              'Sparger holes confirmed clear against a light',
              'Mechanical seal or magnetic drive coupling checked for play',
            ],
          },
          {
            id: 'c8',
            text: 'Reassemble in reverse order. Apply {{qty:Silicone grease, food grade}} of food-grade silicone grease sparingly to the probe port threads only, then torque the headplate bolts in a diagonal sequence to the manufacturer figure.',
            note: 'Grease on an O-ring face, rather than on the thread, is a leak path and a contamination site. A trace on the thread is what stops galling on the next disassembly.',
          },
          {
            id: 'c9',
            text: 'Refit the impeller and sparger to the configuration recorded for the line this vessel serves, and record which configuration was fitted.',
            refs: ['B5'],
            note: 'For the algal line this is not housekeeping. Cell-wall-deficient strains are much more susceptible to shear than walled strains, so a high-shear impeller left in from a fermentation run is a process change that nobody logged.',
          },
          {
            id: 'c10',
            text: 'Service the probes: calibrate the pH electrode with the {{qty:pH calibration buffer sachets, 4.01 and 7.00}} buffer sachets and install it; charge the dissolved-oxygen electrode with {{qty:Dissolved-oxygen probe electrolyte}} of fresh electrolyte, fit a new membrane and install it. Record the pH slope on the vessel log.',
            note: 'A slope that has dropped more than three points since the previous cycle predicts a mid-run pH failure. Replace the electrode now rather than after it has cost a batch.',
          },
          {
            id: 'c11',
            text: 'Fit the {{qty:0.2 µm inlet air filter}} inlet filter and the {{qty:0.2 µm exhaust filter}} exhaust filter, charge the vessel with 1 L of deionised water, place the {{qty:Biological indicator spore strip}} biological indicator spore strip in the vessel, mark the headplate with {{qty:Autoclave indicator tape}} of indicator tape, and sterilise at 121 °C for 45 min with the vent open.',
            timerSec: 2700,
            timerLabel: 'Sterilise 121 °C, 45 min',
          },
          {
            id: 'c12',
            text: 'Cool in the closed chamber to below 80 °C, then hold the sterilised vessel at 30 °C for 24 h as a sterility hold. Incubate the spore strip at 55 °C for 48 h and read it. Release the vessel only when the hold water is clear, the spore strip is negative, and both results are on the vessel log.',
            timerSec: 3600,
            timerLabel: 'Cool below 80 °C',
            note: 'A vessel that fails the hold goes back to step c2, not to step c11. A failed hold after a passing spore strip means a post-sterilisation ingress point, and re-sterilising will pass again while the ingress point remains.',
          },
          {
            id: 'c13',
            text: 'Sign the cycle off on the vessel log: date, operator, detergent lot, elastomer lot, probe slopes, sterilisation cycle number, spore strip result and the configuration fitted at step c9.',
            refs: ['N3'],
            note: 'Keep this log as if it will be read by an assessor, because for a food application it will be. EFSA could not establish the safety of a C. reinhardtii novel food after identifying data gaps across identity, production process, composition and specifications and receiving no reply to repeated requests — a procedural failure, not a finding of harm, and exactly the kind of gap a signed cycle record closes.',
          },
        ],
        estMinutes: { active: 190, total: 1580 },
        references: [
          {
            paperId: 'N3',
            note: 'EFSA NDA Panel 2025 on dried C. reinhardtii biomass: safety could not be established after data gaps across identity, production process, composition and specifications went unanswered. Cited for why this record exists, not for any procedure — OF-COR-001 contains no cleaning or sterilisation method.',
          },
          {
            paperId: 'B5',
            note: 'Cell-wall-deficient strains are much more susceptible to shear and osmotic stress — the constraint behind the impeller-configuration check at step c9.',
          },
        ],
      },
    ],
  },
];
