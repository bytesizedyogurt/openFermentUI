// openFerment Sim — protocol library (OF-DES-001 §8.11, §15).
//
// SYNTHETIC CONTENT. These are executable-shaped bench procedures written for
// the working simulation. Every literature reference points at the synthetic
// corpus in src/data/corpus/*; no real publication, DOI or researcher is cited
// anywhere in this file (BUILD-SPEC §20).
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
  // PR-TAP-01 — TAP medium, two versions so the diff view has real content.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-TAP-01',
    title: 'TAP medium preparation (1 L base)',
    category: 'media',
    organisms: ['cw15', 'cc1690'],
    bsl: 1,
    purpose:
      'Prepare Tris-acetate-phosphate medium for mixotrophic culture of Chlamydomonas reinhardtii from dry Tris and three concentrated stocks, with the acetate charge set so the finished medium lands at pH 7.0 without back-titration.',
    currentVersion: '1.1',
    provenanceNote: 'Derived from SP-001, SP-002 · curated by SMKC',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Composition transcribed from the fully specified flask formulation in SP-001 §Materials and Methods, with the acetate charge rounded to 1.00 g L⁻¹ and a conventional titrate-to-setpoint pH step.',
        baseBatch: { value: 1, unit: 'L', label: 'batch' },
        materials: [
          {
            name: 'Tris base',
            amount: 2.42,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
            sourceRecordId: 'ex-0005',
          },
          {
            name: 'Glacial acetic acid',
            amount: 1.0,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
          },
          {
            name: 'Ammonium chloride',
            amount: 0.375,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.005,
            stock: { conc: 0.015, unit: 'mL' },
            sourceRecordId: 'ex-0006',
          },
          {
            name: 'Magnesium sulfate heptahydrate',
            amount: 0.1,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.001,
            stock: { conc: 0.004, unit: 'mL' },
            sourceRecordId: 'ex-0019',
          },
          {
            name: 'Calcium chloride dihydrate',
            amount: 0.05,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.001,
            stock: { conc: 0.002, unit: 'mL' },
            sourceRecordId: 'ex-0017',
          },
          {
            name: 'Potassium phosphate',
            amount: 1.61,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
            stock: { conc: 0.161, unit: 'mL' },
            sourceRecordId: 'ex-0010',
          },
          {
            name: 'Chelated trace element solution',
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
          'The chelated trace element stock contains soluble copper, zinc and molybdenum salts. Collect rinse water in the heavy-metal waste carboy rather than the sink.',
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
            refs: ['ex-0005'],
          },
          {
            id: 'p4',
            text: 'Add {{stock:Ammonium chloride}} of salt stock S. That single addition delivers the whole salt charge: {{qty:Ammonium chloride}} ammonium chloride, {{qty:Magnesium sulfate heptahydrate}} magnesium sulfate heptahydrate and {{qty:Calcium chloride dihydrate}} calcium chloride dihydrate.',
            note: 'Invert the stock bottle three times before drawing. Magnesium settles out of stock S within a week at bench temperature.',
            refs: ['ex-0006', 'ex-0019'],
          },
          {
            id: 'p5',
            text: 'Add {{stock:Potassium phosphate}} of phosphate stock P, delivering {{qty:Potassium phosphate}} of potassium phosphate. Add it slowly and directly into the vortex, with the calcium already dispersed. A local excess of phosphate against undiluted calcium precipitates calcium phosphate as a haze that never clears.',
            refs: ['ex-0010'],
          },
          {
            id: 'p6',
            text: 'Add {{qty:Chelated trace element solution}} of chelated trace element solution. The stock should be clear amber; discard any bottle showing a rust-coloured precipitate, which means the chelate has broken down and the iron is no longer bioavailable.',
          },
          {
            id: 'p7',
            text: 'In the fume hood, add {{qty:Glacial acetic acid}} of glacial acetic acid to the stirring medium and mix for 2 min.',
          },
          {
            id: 'p8',
            text: 'Read the pH and adjust to 7.0 by dropwise addition of 1 M hydrochloric acid or 1 M sodium hydroxide as required.',
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
            text: 'Withdraw 5 mL from one bottle into a clean tube and confirm that the pH of the cooled medium lies between 6.8 and 7.2.',
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
            paperId: 'SP-001',
            note: 'Fully specified TAP composition used for the reference flask configuration.',
          },
          { recordId: 'ex-0005', note: 'Tris base at 2.42 g L⁻¹ — verified, gold.' },
          { recordId: 'ex-0010', note: 'Potassium phosphate to 1.61 g L⁻¹ — gold annotation.' },
        ],
      },
      {
        version: '1.1',
        changelog:
          'Acetate charge revised from 1.00 to 1.05 g L⁻¹, and the titrate-to-setpoint pH step replaced by a pass/fail check. Rationale: in this recipe acetic acid is not an additive trimmed against a pH target, it is stoichiometrically paired with the Tris. SP-002 makes the pairing explicit by doubling acetate to 2.10 g L⁻¹ alongside 4.84 g L⁻¹ Tris in the TAP-2T variant (record ex-0016, still unverified — the extractor transcribed the unit as mg L⁻¹). Setting acetate to 1.05 g L⁻¹ against 2.42 g L⁻¹ Tris lands the medium at pH 7.0 unaided, matching SP-001. Back-titrating with hydrochloric acid, which v1.0 permitted, added up to 4 mmol L⁻¹ of chloride and left the acetate charge short, shortening the carbon-limited batch by roughly 3 h.',
        baseBatch: { value: 1, unit: 'L', label: 'batch' },
        materials: [
          {
            name: 'Tris base',
            amount: 2.42,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
            sourceRecordId: 'ex-0005',
          },
          {
            name: 'Glacial acetic acid',
            amount: 1.05,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
          },
          {
            name: 'Ammonium chloride',
            amount: 0.375,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.005,
            stock: { conc: 0.015, unit: 'mL' },
            sourceRecordId: 'ex-0006',
          },
          {
            name: 'Magnesium sulfate heptahydrate',
            amount: 0.1,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.001,
            stock: { conc: 0.004, unit: 'mL' },
            sourceRecordId: 'ex-0019',
          },
          {
            name: 'Calcium chloride dihydrate',
            amount: 0.05,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.001,
            stock: { conc: 0.002, unit: 'mL' },
            sourceRecordId: 'ex-0017',
          },
          {
            name: 'Potassium phosphate',
            amount: 1.61,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.01,
            stock: { conc: 0.161, unit: 'mL' },
            sourceRecordId: 'ex-0010',
          },
          {
            name: 'Chelated trace element solution',
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
          'The chelated trace element stock contains soluble copper, zinc and molybdenum salts. Collect rinse water in the heavy-metal waste carboy rather than the sink.',
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
            refs: ['ex-0005'],
          },
          {
            id: 'p4',
            text: 'Add {{stock:Ammonium chloride}} of salt stock S. That single addition delivers the whole salt charge: {{qty:Ammonium chloride}} ammonium chloride, {{qty:Magnesium sulfate heptahydrate}} magnesium sulfate heptahydrate and {{qty:Calcium chloride dihydrate}} calcium chloride dihydrate.',
            note: 'Invert the stock bottle three times before drawing. Magnesium settles out of stock S within a week at bench temperature.',
            refs: ['ex-0006', 'ex-0019'],
          },
          {
            id: 'p5',
            text: 'Add {{stock:Potassium phosphate}} of phosphate stock P, delivering {{qty:Potassium phosphate}} of potassium phosphate. Add it slowly and directly into the vortex, with the calcium already dispersed. A local excess of phosphate against undiluted calcium precipitates calcium phosphate as a haze that never clears.',
            refs: ['ex-0010'],
          },
          {
            id: 'p6',
            text: 'Add {{qty:Chelated trace element solution}} of chelated trace element solution. The stock should be clear amber; discard any bottle showing a rust-coloured precipitate, which means the chelate has broken down and the iron is no longer bioavailable.',
          },
          {
            id: 'p7',
            text: 'In the fume hood, add {{qty:Glacial acetic acid}} of glacial acetic acid straight into the vortex (about 1.00 mL per litre of batch at 20 °C, ρ = 1.049 g mL⁻¹). This addition is both the acetate carbon charge and the titrant for the Tris.',
            note: 'Weigh the acid rather than pipetting it at any scale above 2 L. Glacial acetic acid wets a polypropylene tip badly and volumetric delivery carries a 3–4 % error that propagates straight into the starting pH.',
          },
          {
            id: 'p8',
            text: 'Stir for 2 min, then read the pH. The medium must land at 7.0 ± 0.1 with no further addition. Do not titrate to a setpoint: a reading outside that window means the Tris or the acetate was weighed wrong, and the batch is remade rather than corrected.',
            note: 'A batch reading 7.3–7.5 has usually had Tris weighed against the formula weight of the hydrochloride salt. A batch reading below 6.8 has had acid added twice.',
            refs: ['ex-0018', 'ex-0016'],
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
            text: 'Withdraw 5 mL from one bottle into a clean tube and read the pH of the cooled medium. Release the batch only if it reads between 6.9 and 7.1 and the medium is water-clear. A faint white haze is calcium phosphate; discard the batch and repeat step 5 more slowly.',
          },
          {
            id: 'p14',
            text: 'Label each bottle with the medium name, this protocol version, the preparation date and your initials. Store at room temperature in the dark and use within 8 weeks.',
            note: 'Discard at the first sign of turbidity. TAP is unbuffered against microbial growth and a contaminated bottle will not always look cloudy until it is heavily overgrown.',
          },
        ],
        estMinutes: { active: 35, total: 100 },
        references: [
          {
            paperId: 'SP-001',
            note: 'Fully specified TAP composition; glacial acetic acid to 1.05 g L⁻¹ sets the initial pH to 7.0 without further adjustment.',
          },
          { recordId: 'ex-0005', note: 'Tris base at 2.42 g L⁻¹ — verified, gold.' },
          { recordId: 'ex-0006', note: 'Ammonium chloride at 0.375 g L⁻¹ — verified, gold.' },
          {
            recordId: 'ex-0016',
            note: 'Acetate doubled to 2.10 g L⁻¹ alongside doubled Tris in the TAP-2T variant. Unverified: the extractor transcribed the unit as mg L⁻¹, so treat the value and not the unit as the evidence.',
          },
          {
            paperId: 'SP-002',
            note: 'Buffer and nitrogen variants; terminal pH reaches 8.4 in standard medium, which is why the starting point matters.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-TAP-02 — plates and stock maintenance. Fixed vs scalable quantities.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-TAP-02',
    title: 'TAP agar plates and cw15 stock maintenance',
    category: 'media',
    organisms: ['cw15'],
    bsl: 1,
    purpose:
      'Pour TAP agar plates from prepared medium and use them to hold a cw15 working stock by monthly streak transfer, with a defined retirement point back to the cryopreserved bank.',
    currentVersion: '1.0',
    provenanceNote: 'Derived from SP-001, SP-003 · curated by SMKC',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Pour temperature and plate-drying practice follow the maintenance regime described in SP-001 §Materials and Methods.',
        baseBatch: { value: 500, unit: 'mL', label: 'of agar' },
        materials: [
          {
            name: 'TAP medium (prepared per PR-TAP-01)',
            amount: 500,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Bacteriological agar',
            amount: 7.5,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.1,
          },
          {
            name: '90 mm Petri dishes',
            amount: 22,
            unit: 'dishes',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Autoclave indicator tape',
            amount: 1,
            unit: 'strip',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'Parafilm',
            amount: 1,
            unit: 'roll',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'Sterile disposable inoculation loops',
            amount: 4,
            unit: 'loops',
            scaling: 'fixed',
            precision: 1,
          },
          {
            name: 'cw15 working stock slant',
            amount: 1,
            unit: 'slant',
            scaling: 'fixed',
            precision: 1,
          },
        ],
        equipment: [
          '1 L borosilicate bottle with a vented closure',
          'Autoclave with a 121 °C liquids cycle',
          'Water bath set to 50 °C with a rack that takes a 1 L bottle',
          'Laminar flow hood, or a clean bench with a Bunsen burner',
          'Infrared thermometer',
          'Level pouring surface or a plate carousel',
          '25 °C illuminated incubator and a 22 °C dim maintenance rack',
        ],
        safety: [
          'Molten agar at 90 °C adheres to skin and causes deep scalds. Carry the bottle two-handed in a heat-resistant carrier and never pour above shoulder height.',
          'Autoclave at 121 °C for 20 min on a liquids cycle and do not open the chamber until it reads below 80 °C and the pressure has fully released.',
          'Never re-melt agar in a microwave in a capped bottle. Superheated agar erupts when the bottle is moved; use the water bath, or an uncapped vessel with the closure resting loose.',
          'cw15 is a BSL-1 organism, but used plates still go to the autoclave at 121 °C for 20 min before disposal, not into general refuse.',
        ],
        steps: [
          {
            id: 'g1',
            text: 'Add {{qty:TAP medium (prepared per PR-TAP-01)}} of prepared TAP medium to a 1 L bottle and swirl in {{qty:Bacteriological agar}} of bacteriological agar. The agar will not dissolve at room temperature; wet the powder evenly and leave it as a suspension.',
          },
          {
            id: 'g2',
            text: 'Cap loosely, mark the cap with {{qty:Autoclave indicator tape}} of indicator tape and autoclave at 121 °C for 20 min. The agar dissolves during the cycle, so do not attempt to melt it beforehand.',
            timerSec: 1200,
            timerLabel: 'Autoclave 121 °C, 20 min',
          },
          {
            id: 'g3',
            text: 'Move the bottle to the 50 °C water bath and hold it there until an infrared thermometer reads 50–55 °C on the bottle shoulder and the glass is comfortable to hold through a glove.',
            timerSec: 2400,
            timerLabel: 'Temper agar to 50 °C',
            note: 'Pouring above 60 °C warps the dishes and drives condensation onto the lids. Below 45 °C the agar sets on the way out of the neck and leaves a ridged surface that cannot be streaked cleanly.',
          },
          {
            id: 'g4',
            text: 'Lay out {{qty:90 mm Petri dishes}} Petri dishes in the hood in overlapping rows with the lids on, and let the airflow run for 5 min before the first pour.',
          },
          {
            id: 'g5',
            text: 'Pour each dish to a depth of about 4 mm, roughly 22 mL, until the base is just covered with no meniscus climbing the wall. Flame the bottle neck between rows.',
            note: 'Pass a lit burner flame briefly across the surface of any plate carrying bubbles, before the agar sets. A bubble at the surface becomes a false colony under the dissecting scope.',
          },
          {
            id: 'g6',
            text: 'Leave the poured plates undisturbed on a level surface until fully set, then dry them lid-ajar in the hood with the airflow running.',
            timerSec: 1800,
            timerLabel: 'Dry plates in the hood, 30 min',
          },
          {
            id: 'g7',
            text: 'Invert the dried plates, sleeve them and store at 4 °C in the dark. Use within 6 weeks; a plate that has dried enough to show a shrunken edge gives false-negative growth.',
          },
          {
            id: 'g8',
            text: 'To transfer the working stock, take the {{qty:cw15 working stock slant}} cw15 slant from the 22 °C maintenance rack and let it reach room temperature. Using one of the {{qty:Sterile disposable inoculation loops}} sterile loops, lift a loopful of green biomass from the slant surface without cutting into the agar.',
            refs: ['SP-001'],
          },
          {
            id: 'g9',
            text: 'Streak a fresh plate in three sectors, discarding the loop between sectors, then seal the plate edge with {{qty:Parafilm}} of parafilm stretched only lightly.',
            note: 'A fully occlusive parafilm seal starves the culture of CO₂ and the colonies stay pinpoint. One light turn that still admits gas is the intent.',
          },
          {
            id: 'g10',
            text: 'Incubate at 25 °C under continuous illumination at 40–60 µmol m⁻² s⁻¹ until single colonies reach 1–2 mm, typically 5–7 d, then move the plate to the 22 °C dim maintenance rack. Transfer monthly, and retire the lineage back to a cryopreserved vial after ten serial transfers.',
            refs: ['ex-0004', 'ex-0007'],
            note: 'Serial transfer on acetate selects steadily for faster heterotrophic growth. Ten passages is the point at which the drift becomes measurable against the bank in a flask growth check.',
          },
        ],
        estMinutes: { active: 55, total: 150 },
        references: [
          {
            paperId: 'SP-001',
            note: 'Maintenance on TAP agar slants at 22 °C under continuous dim illumination, subcultured every three weeks.',
          },
          { recordId: 'ex-0004', note: 'Culture temperature 25 °C — verified.' },
          {
            recordId: 'ex-0007',
            note: 'Flask illumination 60 µmol m⁻² s⁻¹ at the vessel base — unverified.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-SEED-01 — multi-day seed train with an inoculation-density calculation.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-SEED-01',
    title: 'cw15 seed train: plate to 50 mL to 400 mL',
    category: 'culture',
    organisms: ['cw15'],
    bsl: 1,
    purpose:
      'Raise a 400 mL mid-exponential cw15 seed from a single colony through a 50 mL intermediate, timed so the seed reaches the production vessel inside its exponential window rather than after it.',
    currentVersion: '1.0',
    provenanceNote: 'Derived from SP-001, SP-010 · curated by SMKC',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Stage timings, illumination geometry and the mid-exponential harvest rule follow the reference flask configuration in SP-001; the OD-to-dry-weight factors come from SP-010.',
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
          'Temperature-controlled shaker enclosure or a 25 °C warm room',
          'Class II cabinet or clean bench with a Bunsen burner',
          'Spectrophotometer reading at 750 nm with 10 mm cuvettes',
          'Spherical quantum sensor for photon flux verification',
        ],
        safety: [
          '70 % ethanol is flammable. Let sprayed surfaces flash off completely before lighting the burner, and never spray toward an open flame.',
          'Silicone foam plugs must stay dry. A plug wetted by a splash or by condensate is a contamination path; replace it rather than drying it.',
          'Baffled flasks at 130 rpm walk on a shaker platform. Check every clamp before starting and never reach into a moving platform to reseat a flask.',
          'Autoclave all spent cw15 culture at 121 °C for 20 min before it goes to drain, even though the strain is BSL-1.',
        ],
        steps: [
          {
            id: 's1',
            text: 'Day 1. Verify the shaker: 25 °C in the enclosure, 130 rpm, and 60 ± 5 µmol m⁻² s⁻¹ measured with the quantum sensor held at the working liquid depth above the platform. Record all three on the batch sheet before any medium is dispensed.',
            refs: ['ex-0004', 'ex-0007'],
          },
          {
            id: 's2',
            text: 'Dispense {{qty:TAP medium — stage 1 charge}} of TAP medium into the {{qty:250 mL baffled flask with silicone foam plug}} 250 mL baffled flask, plug it, and equilibrate it on the running shaker.',
            timerSec: 3600,
            timerLabel: 'Equilibrate stage 1 medium to 25 °C',
          },
          {
            id: 's3',
            text: 'Select one well-isolated green colony 1–2 mm across from the {{qty:TAP agar plate with single colonies}} plate.',
            note: 'Avoid colonies at the plate edge and any colony inside a confluent streak. Both carry a different light and nutrient history from the plate interior, and that history shows up as a longer lag.',
          },
          {
            id: 's4',
            text: 'Lift the colony with a sterile loop and swirl the loop in the stage 1 medium until no visible green remains on the plastic. Return the flask to the shaker and note the clock time as the start of stage 1.',
          },
          {
            id: 's5',
            text: 'Incubate stage 1 for 48 h. The culture should reach OD750 0.6–1.0. If it is below 0.4 at 48 h, discard it and restart from a fresh colony rather than extending the incubation.',
            timerSec: 172800,
            timerLabel: 'Stage 1 incubation, 48 h',
            note: 'A slow start almost always reflects a colony that was already past exponential phase on the plate. Extending the incubation recovers the density but not the physiology.',
          },
          {
            id: 's6',
            text: 'Day 3. Read the OD750 of the stage 1 culture against a TAP medium blank, diluting into the 0.1–0.8 linear range and multiplying back. Record the reading; the stage 2 inoculum volume is computed from it.',
            refs: ['ex-0080'],
          },
          {
            id: 's7',
            text: 'Compute the stage 2 inoculum volume for a target starting OD750 of 0.05: V_seed (mL) = 0.05 × 400 / OD_seed. A stage 1 culture at OD750 0.80 therefore contributes 25 mL, and the medium charge is reduced by that volume so the working volume stays at 400 mL.',
            refs: ['ex-0001', 'ex-0080'],
            note: 'Inoculating high to save a day does not work. Above a starting OD750 of about 0.1 the culture enters the light-limited region of the flask before it has finished its lag, and the fitted growth rate falls by roughly 15 % against the 0.118 h⁻¹ reference.',
          },
          {
            id: 's8',
            text: 'Dispense {{qty:TAP medium — stage 2 charge}} of TAP medium, less the computed inoculum volume, into the {{qty:2 L baffled flask with silicone foam plug}} 2 L baffled flask using the {{qty:Sterile 10 mL serological pipettes}} sterile serological pipettes.',
          },
          {
            id: 's9',
            text: 'Transfer the computed volume of stage 1 culture into the stage 2 flask, working within 150 mm of the burner. Swirl once, reseat the foam plug and return the flask to the shaker at 130 rpm.',
          },
          {
            id: 's10',
            text: 'Incubate stage 2 for 24 h without sampling. Opening the flask during the first day costs more in contamination risk than an early reading is worth.',
            timerSec: 86400,
            timerLabel: 'Stage 2 incubation, 24 h',
          },
          {
            id: 's11',
            text: 'Day 4. Read OD750 hourly from 20 h. Harvest the seed at OD750 1.2–1.6, which is 0.50–0.67 g L⁻¹ dry cell weight at the exponential-phase cw15 factor of 0.42 g L⁻¹ OD⁻¹ and lies inside the exponential window.',
            refs: ['ex-0001', 'ex-0080'],
          },
          {
            id: 's12',
            text: 'Deliver the seed to the production vessel within 30 min of the final reading, at ambient temperature and without centrifugation. Record the harvest OD750, the elapsed time from colony pick and the flask identifier on the batch sheet.',
            refs: ['ex-0086'],
            note: 'Never inoculate from a stationary-phase seed. Stationary cw15 carries a starch load that lengthens the lag by 6–10 h, and its OD-to-dry-weight factor has already shifted from 0.42 to about 0.55 g L⁻¹ OD⁻¹, so the inoculum is heavier than the optical reading suggests.',
          },
        ],
        estMinutes: { active: 80, total: 4400 },
        references: [
          {
            paperId: 'SP-001',
            note: 'Mid-exponential preculture, 60 µmol m⁻² s⁻¹ from below, 130 rpm, inoculation to OD750 0.05.',
          },
          {
            recordId: 'ex-0001',
            note: 'μ = 0.118 h⁻¹ for cw15 under this flask configuration — verified, gold.',
          },
          {
            recordId: 'ex-0080',
            note: 'OD750→DCW factor 0.42 g L⁻¹ OD⁻¹ for exponential cw15 — verified, gold.',
          },
          {
            recordId: 'ex-0086',
            note: 'Stationary-phase cw15 requires 0.55 g L⁻¹ OD⁻¹ — gold annotation.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-PBR-01 — 2 L stirred vessel, sampling sub-checklist, concurrent timers.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-PBR-01',
    title: 'Mixotrophic batch culture, 2 L stirred vessel',
    category: 'culture',
    organisms: ['cw15'],
    bsl: 1,
    purpose:
      'Run a mixotrophic cw15 batch in a 2 L jacketed stirred vessel under controlled temperature, pH, dissolved oxygen and illumination, with a fixed sampling schedule that supports a defensible growth-rate fit and a closed carbon balance.',
    currentVersion: '1.0',
    provenanceNote: 'Derived from SP-001, SP-002, SP-003 · curated by SMKC',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Illumination and pH control follow SP-003; the acid-only pH strategy and the nitrogen-versus-carbon termination diagnostic follow SP-002.',
        baseBatch: { value: 2, unit: 'L', label: 'working volume' },
        materials: [
          {
            name: 'TAP medium (prepared per PR-TAP-01)',
            amount: 1800,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 50,
          },
          {
            name: 'cw15 seed culture (from PR-SEED-01)',
            amount: 200,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Antifoam emulsion, 10 % v/v silicone',
            amount: 0.4,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 0.1,
          },
          {
            name: '1 M sulfuric acid',
            amount: 100,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: '0.5 M sodium hydroxide',
            amount: 100,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Sterile 10 mL sampling syringes',
            amount: 16,
            unit: 'syringes',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: '0.2 µm syringe filters',
            amount: 16,
            unit: 'filters',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Pre-dried 0.7 µm glass-fibre filters',
            amount: 48,
            unit: 'filters',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'pH calibration buffer sachets, 7.00 and 4.01',
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
            name: '0.2 µm inlet air filter',
            amount: 1,
            unit: 'filter',
            scaling: 'fixed',
            precision: 1,
          },
        ],
        equipment: [
          '2 L jacketed glass bioreactor with headplate, Rushton impeller and ring sparger',
          'Bench controller with temperature, pH, dissolved-oxygen and agitation loops',
          'Gel-filled pH electrode and a polarographic dissolved-oxygen electrode',
          'Dimmable white LED panel and a spherical quantum sensor',
          'Recirculating chiller/heater set to 25 °C',
          'Peristaltic pumps for acid, base and antifoam',
          'Autoclave with a chamber that takes the assembled 2 L vessel',
          'Spectrophotometer at 750 nm, vacuum filtration manifold, 105 °C drying oven',
        ],
        safety: [
          'Torque the headplate bolts in a diagonal sequence to the manufacturer figure. An unevenly loaded glass vessel can fail on the pressure rise in the autoclave.',
          'Confirm the vessel vents through the 0.2 µm inlet filter and that the exhaust line is unclamped before autoclaving. A sealed bioreactor is a pressure vessel.',
          'Sterilise the assembled vessel at 121 °C for 45 min and do not move it until the chamber reads below 80 °C and the internal pressure has equalised through the vent filter.',
          '1 M sulfuric acid and 0.5 M sodium hydroxide are corrosive. Prime both pumps into a waste beaker inside a spill tray, in goggles, before connecting the lines to the headplate.',
          'The rear face of the LED panel reaches 55 °C. Keep the acid, base and antifoam lines clear of it and never drape tubing across the panel.',
          'Do not open the sample port while the vessel is at positive pressure. Reduce the sparge to zero and let the headspace equalise first.',
        ],
        steps: [
          {
            id: 'b1',
            text: 'Assemble the 2 L vessel: fit the Rushton impeller 20 mm above the ring sparger, install the sparger, baffles and exhaust condenser, and torque the headplate bolts in a diagonal sequence to the manufacturer figure.',
          },
          {
            id: 'b2',
            text: 'Charge the vessel with {{qty:TAP medium (prepared per PR-TAP-01)}} of TAP medium and add {{qty:Antifoam emulsion, 10 % v/v silicone}} of antifoam emulsion. Leave the remaining working volume for the seed.',
          },
          {
            id: 'b3',
            text: 'Calibrate the pH electrode on the bench with the {{qty:pH calibration buffer sachets, 7.00 and 4.01}} buffer sachets, then install it. Charge the dissolved-oxygen electrode with {{qty:Dissolved-oxygen probe electrolyte}} of fresh electrolyte and install it, but do not calibrate it yet.',
            note: 'pH is calibrated before sterilisation and never after. The gel electrode drifts by up to 0.15 units through a liquids cycle, and recalibrating inside a sterile vessel is not possible.',
          },
          {
            id: 'b4',
            text: 'Fit the {{qty:0.2 µm inlet air filter}} inlet air filter, clamp every addition line except the vent, and sterilise the assembled vessel at 121 °C for 45 min on a liquids cycle.',
            timerSec: 2700,
            timerLabel: 'Sterilise vessel, 121 °C, 45 min',
          },
          {
            id: 'b5',
            text: 'Move the cooled vessel to the controller skid, connect the jacket to the chiller at 25 °C and start agitation at 200 rpm. Polarise the dissolved-oxygen electrode for 6 h before calibration; carry out steps b6 and b7 while it polarises.',
            timerSec: 21600,
            timerLabel: 'Polarise DO electrode, 6 h',
            refs: ['ex-0004'],
          },
          {
            id: 'b6',
            text: 'Mount the LED panel 120 mm from the vessel wall and let it warm up before measuring. Set the incident photon flux density to 150 µmol m⁻² s⁻¹ at the vessel surface with the spherical quantum sensor, and record both the reading and the panel-to-glass distance.',
            timerSec: 1800,
            timerLabel: 'LED panel warm-up, 30 min',
            refs: ['ex-0023'],
            note: 'White LED output falls 5–8 % over the first 20 min as the junction warms. A flux set from a cold panel is systematically high, and it is the single most common reason two runs on the same rig disagree.',
          },
          {
            id: 'b7',
            text: 'Prime the acid and base pumps with {{qty:1 M sulfuric acid}} of 1 M sulfuric acid and {{qty:0.5 M sodium hydroxide}} of 0.5 M sodium hydroxide, then set the pH loop to 7.0 with a 0.1 unit dead band. Expect acid demand only: acetate uptake drives this culture alkaline.',
            refs: ['ex-0018'],
            note: 'Deviation-prone. If the base pump runs at all in the first 12 h, either the electrode is reading low or the medium was back-titrated during preparation. Stop and resolve it before the culture is committed.',
          },
          {
            id: 'b8',
            text: 'With polarisation complete, sparge nitrogen at 0.2 vvm until the dissolved-oxygen signal is flat and set that point to 0 %. Switch to air at 0.2 vvm and 400 rpm, wait for a stable reading and set it to 100 %.',
            timerSec: 900,
            timerLabel: 'Nitrogen zero, 15 min',
          },
          {
            id: 'b9',
            text: 'Set the dissolved-oxygen cascade to hold 30 % of air saturation on agitation between 200 and 700 rpm, at a fixed 0.2 vvm air sparge. Confirm the loop responds by dropping the setpoint to 20 % and watching agitation move within 60 s, then restore it.',
          },
          {
            id: 'b10',
            text: 'Inoculate with {{qty:cw15 seed culture (from PR-SEED-01)}} of mid-exponential seed through the septum port, to a starting OD750 of 0.10–0.15 in a 2.0 L final working volume. Record the clock time as t = 0.',
            refs: ['ex-0001'],
          },
          {
            id: 'b11',
            text: 'Sample at t = 0, then every 3 h to 36 h and every 6 h thereafter, using one of the {{qty:Sterile 10 mL sampling syringes}} sampling syringes each time. Complete every line below before the sample leaves the bench.',
            multiCheck: [
              'Reduce the sparge to zero and let the headspace equalise before opening the port',
              'Discard the first 5 mL as line hold-up',
              'Withdraw 10 mL and record controller time, temperature, pH, dissolved oxygen and agitation',
              'Read OD750 against a TAP blank, diluting to fall between 0.1 and 0.8',
              'Filter 5 mL through a 0.2 µm syringe filter into a labelled vial and freeze at −20 °C for acetate',
              'Filter 10 mL onto a pre-dried glass-fibre filter, wash twice with ammonium formate, dry at 105 °C',
              'Restore the sparge and confirm the dissolved-oxygen trace recovers within 5 min',
            ],
            refs: ['ex-0080'],
          },
          {
            id: 'b12',
            text: 'Dry the gravimetric filters to constant mass and weigh them against filter blanks carried through the identical wash and dry cycle. Subtract the blank before computing dry cell weight.',
            refs: ['ex-0080'],
            note: 'At the dilute end of the run the filter blank is the largest single source of bias. Two blanks per sampling day, from the same filter lot, is the minimum that makes the early points usable.',
          },
          {
            id: 'b13',
            text: 'Fit the specific growth rate by unweighted linear regression of ln(DCW) against time, over the window in which the residuals show no systematic trend — typically 6 h to 30 h. Expect 0.09–0.12 h⁻¹ for cw15 in this configuration.',
            refs: ['ex-0001', 'ex-0011', 'ex-0070'],
            note: 'A fitted rate below 0.07 h⁻¹ points at light or oxygen limitation in the vessel, not at the strain. Check the recorded photon flux and whether agitation ever hit its ceiling on the dissolved-oxygen cascade before blaming the inoculum.',
          },
          {
            id: 'b14',
            text: 'Track culture pH against the cumulative acid demand. A culture that stops consuming acid before 40 h has exhausted its acetate; a culture whose pH climbs above 7.5 despite acid addition has a failed pump or a blocked line. Log either as a deviation with the elapsed time and the last good reading.',
            refs: ['SP-002'],
            note: 'Deviation-prone. Standard TAP terminates on nitrogen at around 52 h and on carbon later, and which limit you hit is diagnostic of the batch. Do not correct it silently by topping up.',
          },
          {
            id: 'b15',
            text: 'Harvest when dry cell weight has been flat across two consecutive samples, typically 54–60 h at 1.5–2.0 g L⁻¹. Record the final dry cell weight, the terminal pH and the total acid consumed.',
            refs: ['ex-0003', 'ex-0022'],
          },
          {
            id: 'b16',
            text: 'Shut down: stop the LED panel and all pumps, drain the culture to the harvest carboy through the bottom port, and pass the vessel to the clean-in-place SOP within 2 h. Culture left standing in a warm vessel is markedly harder to clean.',
          },
        ],
        estMinutes: { active: 430, total: 4320 },
        references: [
          {
            paperId: 'SP-003',
            note: 'Matched-illumination photoautotrophic and mixotrophic culture; 150 µmol m⁻² s⁻¹ at the vessel surface.',
          },
          {
            paperId: 'SP-002',
            note: 'Nitrogen-versus-carbon termination diagnostic and the alkaline pH drift of standard TAP.',
          },
          {
            recordId: 'ex-0023',
            note: 'Incident photon flux density 150 µmol m⁻² s⁻¹ — verified.',
          },
          {
            recordId: 'ex-0070',
            note: 'μ = 0.094 h⁻¹ for mixotrophic cw15 in a stirred vessel — verified, gold.',
          },
          {
            recordId: 'ex-0003',
            note: 'Final biomass density 1.62 g L⁻¹ at 54 h under acetate limitation — verified.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-OD-01 — analytics SOP; the coefficient step carries the od_dcw_factor.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-OD-01',
    title: 'OD750 and dry cell weight SOP',
    category: 'analytics',
    organisms: ['cw15', 'cc1690'],
    bsl: 1,
    purpose:
      'Measure optical density at 750 nm and gravimetric dry cell weight on the same sample, and convert between them using a factor determined for this strain, wavelength and growth phase rather than a literature default.',
    currentVersion: '1.0',
    provenanceNote: 'Derived from SP-010 · curated by SMKC',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Blanking against spent medium, the filter-blank subtraction and the through-origin regression follow SP-010 §Materials and Methods.',
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
            text: 'Invert each culture sample three times immediately before reading. Settled cw15 re-suspends completely, but a sample read 30 s after mixing has already lost 2–3 % of its absorbance to sedimentation.',
          },
          {
            id: 'o4',
            text: 'Read OD750 in a 10 mm cuvette against {{qty:Spent cell-free medium}} of spent cell-free medium as the blank. Dilute any sample reading above 0.85 into the same spent medium and multiply back.',
            refs: ['ex-0080'],
            note: 'Blank against spent medium from the same culture, not against fresh medium. Above OD750 0.85 multiple scattering bends the response and the reading stops being proportional to biomass, which is why the dilution is mandatory rather than optional.',
          },
          {
            id: 'o5',
            text: 'Filter 10 mL of each sample onto its tared filter under 40 kPa of vacuum. Do not let the bed run dry between the sample and the wash, or the retained salt crystallises into the mat and cannot be washed out.',
          },
          {
            id: 'o6',
            text: 'Wash each filter twice with 10 mL of ammonium formate isotonic with the medium; a full run consumes {{qty:Ammonium formate wash solution}}. Ammonium formate removes medium salts and volatilises in the oven, whereas a deionised water wash lyses cw15 and loses soluble solids.',
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
            text: 'Regress dry cell weight on OD750 through the origin, over the range in which the residuals show no curvature. Exponential-phase cw15 should return 0.42 g L⁻¹ OD⁻¹; stationary-phase cw15 returns about 0.55 and the walled wild type cc1690 about 0.47. Re-determine the factor whenever the strain, the wavelength or the growth phase changes.',
            refs: ['ex-0080', 'ex-0086', 'ex-0081', 'ex-0082'],
            note: 'Do not carry a 680 nm factor into a 750 nm workflow. Pigment absorbance inflates the optical reading at 680 nm, giving 0.31 g L⁻¹ OD⁻¹, and that factor drifts a further 11 % with light acclimation. Record ex-0082 also has the OD basis dropped from its unit string, so it reads as a plain concentration.',
          },
        ],
        estMinutes: { active: 90, total: 480 },
        references: [
          {
            paperId: 'SP-010',
            note: 'Wavelength and growth phase dominate OD-to-dry-weight error; spent-medium blanking and filter-blank subtraction.',
          },
          {
            recordId: 'ex-0080',
            note: 'cw15 exponential-phase factor 0.42 g L⁻¹ OD⁻¹ — verified, gold.',
          },
          {
            recordId: 'ex-0086',
            note: 'Stationary-phase cw15 factor 0.55 g L⁻¹ OD⁻¹ — gold annotation.',
          },
          {
            recordId: 'ex-0081',
            note: 'Walled wild type cc1690 requires 0.47 g L⁻¹ OD⁻¹ — verified.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-HARV-01 — per_unit_biomass consumables; disruption reference chips.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-HARV-01',
    title: 'Harvest and bead-mill disruption of cw15',
    category: 'harvest',
    organisms: ['cw15'],
    bsl: 1,
    purpose:
      'Concentrate a mixotrophic cw15 culture by centrifugation and disrupt the paste in a single bead-mill pass, scoring both the disruption efficiency and the soluble protein release against an undisrupted control drawn from the same feed.',
    currentVersion: '1.0',
    provenanceNote: 'Derived from SP-006, SP-010 · curated by SMKC',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Chamber charge, tip speed, residence time and the cytometric disruption score follow SP-006 §Materials and Methods; the recovery target is the gravimetric closure reported there.',
        baseBatch: { value: 10, unit: 'L', label: 'culture at 2.6 g L⁻¹' },
        materials: [
          {
            name: 'Wash buffer, 50 mM potassium phosphate pH 7.0',
            amount: 1000,
            unit: 'mL',
            scaling: 'per_unit_biomass',
            precision: 50,
          },
          {
            name: 'Ammonium formate wash solution',
            amount: 200,
            unit: 'mL',
            scaling: 'per_unit_biomass',
            precision: 10,
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
            name: 'Lowry assay reactions',
            amount: 24,
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
            amount: 1.12,
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
        ],
        equipment: [
          'Fixed-angle floor centrifuge accepting 500 mL bottles, rated to 6,000 × g',
          '1.4 L horizontal bead mill with a jacketed grinding chamber and a variable-speed drive',
          'Recirculating chiller for the mill jacket',
          'Peristaltic feed pump rated to 40 L h⁻¹',
          'Flow cytometer with a 488 nm excitation line',
          'Spectrophotometer for the Lowry assay',
          'Top-pan balance readable to 0.01 g for gravimetric closure',
        ],
        safety: [
          'Balance opposing centrifuge bottles to within 1 g on a top-pan balance, and use only sealing caps. A leaking rotor at 4,000 × g is both an aerosol event and a corrosion event.',
          'The mill chamber holds 1.12 L of 0.4 mm zirconia beads under pressure. Isolate the drive and vent the chamber before opening the end plate, and never open it while the jacket is cold and the chamber under vacuum.',
          'Hold the mill jacket at 12 °C and confirm the outlet stream never exceeds 21 °C. Released protein denatures above that and the Lowry result stops tracking the disruption score.',
          'Spilled zirconia beads behave like ball bearings underfoot. Sweep them up immediately and do not rinse them to drain.',
          'cw15 lysate is a nutrient-rich broth. Chill it to 4 °C within 30 min of milling or it will not be microbiologically stable long enough to assay.',
        ],
        steps: [
          {
            id: 'h1',
            text: 'Confirm the culture is ready to harvest: dry cell weight 2.4–2.8 g L⁻¹ and residual acetate below 0.2 g L⁻¹. Draw a 50 mL reference aliquot, hold it at 4 °C as the undisrupted control, and determine its dry cell weight with the filters washed using {{qty:Ammonium formate wash solution}} of ammonium formate wash solution.',
            refs: ['ex-0050'],
            note: 'Every disruption score in this protocol is referenced to that aliquot. A control drawn on a different day, or from a different vessel, invalidates the score no matter how carefully the cytometry is gated.',
          },
          {
            id: 'h2',
            text: 'Chill the culture to 12 °C in the vessel before harvest. Warm cw15 paste compacts poorly and re-suspends into a stringy slurry that blocks the mill inlet.',
          },
          {
            id: 'h3',
            text: 'Fill {{qty:500 mL centrifuge bottles with sealing caps}} centrifuge bottles, balancing opposing pairs to within 1 g and seating every cap fully.',
          },
          {
            id: 'h4',
            text: 'Centrifuge at 4,000 × g for 15 min at 12 °C with the brake set low. A hard brake re-suspends the pellet edge and costs 2–4 percentage points of recovery.',
            timerSec: 900,
            timerLabel: 'Centrifuge 4,000 × g, 15 min',
          },
          {
            id: 'h5',
            text: 'Decant the supernatant into a tared carboy and weigh it, then weigh the bottles with their pellets. Close the mass balance across feed, concentrate and centrate. Expect 92–97 % recovery against the 96.4 % reported for continuous disc-stack harvest of this strain.',
            refs: ['ex-0046', 'ex-0047'],
            note: 'Gravimetric closure is what makes a recovery figure defensible. A recovery computed from pellet volume alone routinely overstates by five points because it counts interstitial medium as biomass.',
          },
          {
            id: 'h6',
            text: 'Dissolve {{qty:Protease inhibitor tablets, EDTA-free}} inhibitor tablets in {{qty:Wash buffer, 50 mM potassium phosphate pH 7.0}} of cold wash buffer, then resuspend the combined pellets in it to a target paste concentration of 40–45 g L⁻¹ dry solids.',
            note: 'Use the EDTA-free formulation. Chelated divalent metals carried into the Lowry assay depress the colour development and the protein figure comes back low for a reason unrelated to disruption.',
          },
          {
            id: 'h7',
            text: 'Charge the mill chamber to 80 % of its free volume with {{qty:0.4 mm yttria-stabilised zirconia beads}} of 0.4 mm zirconia beads. This charge is a property of the 1.4 L chamber and does not change with batch size.',
          },
          {
            id: 'h8',
            text: 'Start the jacket chiller with {{qty:Chamber coolant, 30 % v/v propylene glycol}} of coolant and hold the chamber at 12 °C. Circulate cold wash buffer through the mill until the outlet reads within 1 °C of the jacket.',
            timerSec: 1200,
            timerLabel: 'Pre-chill mill chamber, 20 min',
          },
          {
            id: 'h9',
            text: 'Mill the paste in a single pass at a tip speed of 12 m s⁻¹, with the feed rate set for a 3.5 min residence time — 24 L h⁻¹ for the 1.4 L chamber. Log the outlet temperature every minute and abort the pass if it exceeds 21 °C.',
            refs: ['ex-0043'],
            note: 'Disruption rises steeply with residence time to about 3 min and then flattens. Pushing tip speed past 12 m s⁻¹ buys under two percentage points at a disproportionate energy cost and a real thermal one.',
          },
          {
            id: 'h10',
            text: 'Draw a 5 mL lysate sample and a matched aliquot of the undisrupted control. Stain both with {{qty:Membrane-impermeant nucleic acid stain}} of the impermeant nucleic acid stain and count intact cells by flow cytometry on the same day, against the same gate.',
            refs: ['ex-0043'],
          },
          {
            id: 'h11',
            text: 'Score disruption as the fractional loss of intact cells relative to the control. A single bead-mill pass on this feed should return 92–96 %. For context, a single homogeniser pass at 1,200 bar returns about 88.6 % and 20 min of bath sonication only 61.5 %, which is why sonication is a reference and not a process step.',
            refs: ['ex-0043', 'ex-0044', 'ex-0051', 'ex-0045'],
          },
          {
            id: 'h12',
            text: 'Clarify 20 mL of lysate at 10,000 × g for 10 min and assay soluble protein in the supernatant by Lowry, using {{qty:Lowry assay reactions}} reactions against a standard curve built from {{qty:Bovine serum albumin standard, 2 mg mL⁻¹}} of albumin standard diluted in the identical buffer. Dilute every lysate to fall in the middle third of the curve.',
            timerSec: 600,
            timerLabel: 'Clarify lysate, 10,000 × g, 10 min',
            refs: ['ex-0048'],
          },
          {
            id: 'h13',
            text: 'Report the chain rather than the endpoints: culture → paste → clarified lysate, with recovery, disruption efficiency and soluble protein at each transition. Expect overall soluble-protein recovery near 88 % for the bead-mill route.',
            refs: ['ex-0046', 'ex-0048'],
            note: 'A protein figure that outruns the disruption score means the cytometry gate is counting permeabilised cells as disrupted. Those cells exclude the dye but still hold their chloroplast-associated protein.',
          },
        ],
        estMinutes: { active: 245, total: 430 },
        references: [
          {
            paperId: 'SP-006',
            note: 'Bead milling versus high-pressure homogenisation on the same cw15 feed; chamber charge, tip speed and residence time.',
          },
          {
            recordId: 'ex-0043',
            note: 'Single-pass bead milling at 12 m s⁻¹ disrupts 94.2 % of cells — verified, gold.',
          },
          {
            recordId: 'ex-0046',
            note: 'Continuous disc-stack centrifugation recovers 96.4 % of culture biomass — verified, gold.',
          },
          {
            recordId: 'ex-0051',
            note: 'Bath sonication reference, 61.5 % after 20 min — gold annotation.',
          },
          {
            recordId: 'ex-0050',
            note: 'Harvest dry cell weight 2.6 g L⁻¹ at 96 h — verified.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-PICH-01 — longest run; rescaling feed table, induction-phase timers.
  // ───────────────────────────────────────────────────────────────────────
  {
    id: 'PR-PICH-01',
    title: 'Fed-batch K. phaffii, methanol induction (10 L)',
    category: 'fermentation',
    organisms: ['gs115'],
    bsl: 1,
    purpose:
      'Run a three-phase fed-batch of Komagataella phaffii GS115 at a 10 L working volume — glycerol batch, glycerol transition feed, then methanol induction under a transfer-limited feed law — to produce a secreted recombinant protein at high cell density.',
    currentVersion: '1.0',
    provenanceNote: 'Derived from SP-012, SP-014 · curated by SMKC',
    versions: [
      {
        version: '1.0',
        changelog:
          'Initial release. Batch salts and the induction temperature shift follow SP-014; the transfer-limited feed law and the residual-methanol interlock follow SP-014 §Materials and Methods, with the induction ramp shaped after the DO-stat policy in SP-012.',
        baseBatch: { value: 10, unit: 'L', label: 'working volume' },
        materials: [
          {
            name: 'Glycerol, batch charge',
            amount: 400,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 5,
          },
          {
            name: 'Potassium sulfate',
            amount: 182,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Magnesium sulfate heptahydrate',
            amount: 149,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Calcium sulfate dihydrate',
            amount: 9.3,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.1,
          },
          {
            name: 'Phosphoric acid, 85 % w/w',
            amount: 267,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'PTM1 trace metal solution',
            amount: 43.5,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 0.5,
          },
          {
            name: 'Biotin',
            amount: 0.004,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 0.001,
            stock: { conc: 0.0002, unit: 'mL' },
          },
          {
            name: 'Ammonium hydroxide, 28 % w/w',
            amount: 1500,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Glycerol transition feed, 500 g L⁻¹ with PTM1',
            amount: 700,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 10,
          },
          {
            name: 'Methanol charge, induction hours 0–6',
            amount: 105,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 5,
          },
          {
            name: 'Methanol charge, induction hours 6–24',
            amount: 630,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 5,
          },
          {
            name: 'Methanol charge, induction hours 24–90',
            amount: 2770,
            unit: 'g',
            scaling: 'per_batch_volume',
            precision: 5,
          },
          {
            name: 'Antifoam, polypropylene glycol P2000',
            amount: 20,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 1,
          },
          {
            name: 'Seed culture in buffered glycerol complex medium',
            amount: 1000,
            unit: 'mL',
            scaling: 'per_batch_volume',
            precision: 50,
          },
          {
            name: 'Methanol sensor calibration standard',
            amount: 1,
            unit: 'vial',
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
        ],
        equipment: [
          '15 L stirred-tank fermenter with a 10 L working volume, two Rushton impellers and a ring sparger',
          'In-situ sterilisable vessel with steam-in-place jacket and vent condenser',
          'Controller with temperature, pH, dissolved-oxygen, agitation, air and oxygen-enrichment loops',
          'Off-gas analyser: paramagnetic oxygen and infrared carbon dioxide',
          'Headspace methanol sensor with a daily calibration routine',
          'Gravimetric feed station: methanol reservoir on a load cell inside a bunded tray',
          'Peristaltic feed pumps for glycerol, methanol and antifoam',
          'Oxygen enrichment line with a flow controller and a hard enrichment cap',
        ],
        safety: [
          'Methanol is highly flammable, toxic by inhalation and absorbed through skin, and its vapour is invisible. Feed it from an earthed, bunded reservoir with a bonding strap to the skid, and keep the feed line off the floor and away from traffic.',
          'The methanol reservoir sits on a load cell inside a spill tray of at least 110 % of its volume. Gravimetric verification is a safety control here, not only an analytical one: a stopped pump and a dead-heading pump look identical on the controller trace.',
          'A methanol-adapted culture above 100 g L⁻¹ dry cell weight outruns the vessel oxygen supply within minutes of an agitation trip. Interlock the feed to suspend on loss of agitation and never bypass that interlock to ride out a fault.',
          'Ammonium hydroxide at 28 % releases ammonia vapour. Connect and disconnect the base line in the fume hood with the pump stopped and the vessel vented.',
          'Do not open the vessel while methanol feeding is active. Residual methanol above 6 g L⁻¹ produces a flammable headspace on depressurisation.',
          'Cap oxygen enrichment at the value on the vessel data sheet. Enriched headspace over a methanol-fed broth widens the flammability envelope.',
          'Sterilise in situ at 121 °C for 45 min and break no connection until the vessel is below 80 °C and pressure has released through the vent filter.',
        ],
        steps: [
          {
            id: 'k1',
            text: 'Prepare the batch salts in about 7 L of deionised water in the vessel: {{qty:Potassium sulfate}} potassium sulfate, {{qty:Magnesium sulfate heptahydrate}} magnesium sulfate heptahydrate and {{qty:Calcium sulfate dihydrate}} calcium sulfate dihydrate. Stir until dissolved; the calcium sulfate will remain as a fine suspension and that is expected.',
          },
          {
            id: 'k2',
            text: 'Add {{qty:Phosphoric acid, 85 % w/w}} of 85 % phosphoric acid slowly, with agitation, then add {{qty:Glycerol, batch charge}} of glycerol and {{qty:Antifoam, polypropylene glycol P2000}} of antifoam. Make up to 9.0 L, leaving the balance of the working volume for the seed and the base demand.',
          },
          {
            id: 'k3',
            text: 'Calibrate the pH electrode with the {{qty:pH calibration buffer sachets, 4.01 and 7.00}} buffer sachets and install it. Charge the dissolved-oxygen electrode with {{qty:Dissolved-oxygen probe electrolyte}} of electrolyte and install it. Calibrate the headspace methanol sensor against {{qty:Methanol sensor calibration standard}} calibration standard vial.',
            note: 'The methanol sensor is an interlock, not the controlled variable. It is calibrated daily throughout induction because a drifting sensor silently raises the residual methanol at which the feed will actually cut.',
          },
          {
            id: 'k4',
            text: 'Sterilise in situ at 121 °C for 45 min, with the vent filter open and the exhaust condenser running. Confirm the sterilisation hold on the batch record before the chart is filed.',
            timerSec: 2700,
            timerLabel: 'Sterilise in situ, 121 °C, 45 min',
          },
          {
            id: 'k5',
            text: 'Cool to 30.0 °C, start agitation at 400 rpm and air at 0.5 vvm, and polarise the dissolved-oxygen electrode for 6 h. Complete steps k6 and k7 while it polarises, then set 100 % against air at the run agitation and aeration.',
            timerSec: 21600,
            timerLabel: 'Polarise DO electrode, 6 h',
          },
          {
            id: 'k6',
            text: 'Add {{qty:PTM1 trace metal solution}} of filter-sterilised PTM1 trace metal solution and {{stock:Biotin}} of biotin stock, delivering {{qty:Biotin}} of biotin. Both are added after sterilisation; autoclaved PTM1 precipitates and the biotin degrades.',
          },
          {
            id: 'k7',
            text: 'Connect the base line and set the pH loop to 5.0, controlled by on-demand addition of {{qty:Ammonium hydroxide, 28 % w/w}} of 28 % ammonium hydroxide. The base is also the sole nitrogen source, so its consumption is a process measurement and not just a control action.',
            refs: ['ex-0097'],
          },
          {
            id: 'k8',
            text: 'Inoculate with {{qty:Seed culture in buffered glycerol complex medium}} of seed culture at 10 % of the working volume. Record the time as batch t = 0 and start the off-gas analyser logging.',
          },
          {
            id: 'k9',
            text: 'Run the glycerol batch phase at 30.0 °C, holding dissolved oxygen above 25 % of air saturation by cascading agitation, then air flow, then oxygen enrichment. The batch glycerol exhausts at 18–24 h and announces itself as a sharp dissolved-oxygen rise.',
            timerSec: 300,
            timerLabel: 'Confirm DO spike, 5 min',
            note: 'Wait the full 5 min before acting on the spike. A transient rise from a foam collapse or an antifoam shot looks identical for the first 60 s, and starting the transition feed early leaves unconsumed glycerol to repress the promoter.',
          },
          {
            id: 'k10',
            text: 'Start the glycerol transition feed: {{qty:Glycerol transition feed, 500 g L⁻¹ with PTM1}} of 500 g L⁻¹ glycerol with PTM1, delivered over 4 h at a rate that holds dissolved oxygen above 25 %. This phase brings the vessel to a common biomass before induction.',
            timerSec: 14400,
            timerLabel: 'Glycerol transition feed, 4 h',
            refs: ['ex-0099'],
          },
          {
            id: 'k11',
            text: 'Stop the glycerol feed and hold the culture carbon-starved for 30 min. Confirm the dissolved oxygen has risen and settled, and record the dry cell weight; it should be 40–45 g L⁻¹ at this point.',
            timerSec: 1800,
            timerLabel: 'Carbon starvation before induction, 30 min',
            note: 'Deviation-prone. Inducing over residual glycerol is the most common cause of a low first-day titre, because the AOX1 promoter stays repressed while the methanol feed is already running and residual methanol climbs.',
          },
          {
            id: 'k12',
            text: 'Ramp the temperature from 30.0 °C to 26.0 °C over 30 min and hold it there for the rest of the run. The lower induction temperature reduces proteolytic clipping of the secreted product at the cost of a slightly lower specific rate.',
            timerSec: 1800,
            timerLabel: 'Temperature ramp to 26 °C, 30 min',
            refs: ['ex-0112'],
          },
          {
            id: 'k13',
            text: 'Start methanol induction and follow the feed schedule below. Rates are per litre of working volume and do not change with batch size; the charges do.\n\n| Induction window | Methanol feed rate | Charge at this batch size |\n| --- | --- | --- |\n| 0–6 h | 1.0 → 2.5 g L⁻¹ h⁻¹ linear ramp | {{qty:Methanol charge, induction hours 0–6}} |\n| 6–24 h | 3.5 g L⁻¹ h⁻¹ held | {{qty:Methanol charge, induction hours 6–24}} |\n| 24–90 h | 4.2 g L⁻¹ h⁻¹, trimmed on oxygen uptake | {{qty:Methanol charge, induction hours 24–90}} |',
            note: 'The 0–6 h ramp is an adaptation phase, not a productivity phase. Cells arriving from glycerol have no alcohol oxidase pool and a full-rate feed simply accumulates methanol.',
            refs: ['ex-0091'],
          },
          {
            id: 'k14',
            text: 'Set the residual-methanol interlock to suspend the feed above 6 g L⁻¹ in the broth, and verify it once by raising the threshold alarm and confirming the pump stops. Log every suspension with its clock time and duration.',
          },
          {
            id: 'k15',
            text: 'From 24 h, trim the feed every 90 s to hold the oxygen uptake rate at 90 % of the transfer capacity estimated for the current agitation, aeration and enrichment state. Recompute transfer capacity from the off-gas oxygen balance at least once per shift.',
            refs: ['ex-0117'],
            note: 'This is what makes the run transfer-limited rather than kinetically limited, and it is the reason the same feed law reproduces across vessel scales that have different transfer coefficients.',
          },
          {
            id: 'k16',
            text: 'Sample every 12 h through induction. Complete each line before the sample leaves the bench.',
            multiCheck: [
              'Record elapsed induction time, temperature, pH, dissolved oxygen, agitation and enrichment',
              'Read cumulative methanol and base mass from the load cells and log both',
              'Withdraw 20 mL through the sample port after a 10 mL discard',
              'Determine dry cell weight in quadruplicate on washed, oven-dried pellets',
              'Clarify 5 mL at 10,000 × g and freeze the supernatant at −20 °C for titre',
              'Check the broth for foam carryover into the exhaust condenser',
            ],
          },
          {
            id: 'k17',
            text: 'Assay the frozen supernatants at the end of the run by reversed-phase chromatography against a purified reference, with monomer content checked in parallel by size exclusion. Expect 90–130 g L⁻¹ dry cell weight and a titre in the 10–26 g L⁻¹ range depending on the construct.',
            refs: ['ex-0091', 'ex-0109', 'ex-0111', 'ex-0096'],
            note: 'Report titre alongside biomass and induction time, never alone. A titre quoted without the biomass it was made on cannot be compared with anything, which is the whole difficulty the corpus records document.',
          },
          {
            id: 'k18',
            text: 'End the run at 90 h of induction: stop the feed, hold agitation and cooling for 20 min to consume residual methanol, then chill the broth to 12 °C and confirm headspace methanol has fallen below 0.5 g L⁻¹ before opening the vessel. Pass the vessel to the clean-in-place SOP the same day.',
            timerSec: 1200,
            timerLabel: 'Consume residual methanol, 20 min',
          },
        ],
        estMinutes: { active: 960, total: 8280 },
        references: [
          {
            paperId: 'SP-014',
            note: 'High-cell-density fed-batch with a transfer-limited methanol feed law and a 6 g L⁻¹ residual interlock.',
          },
          {
            paperId: 'SP-012',
            note: 'Methanol feeding policy governs specific productivity at matched biomass and medium history.',
          },
          {
            recordId: 'ex-0091',
            note: 'Titre 12.4 g L⁻¹ of RlpB-3 after 72 h of induction under a DO-stat policy — verified, gold.',
          },
          {
            recordId: 'ex-0109',
            note: 'Titre 25.8 g L⁻¹ of rALB-7 at the 1,200 L scale — verified, gold.',
          },
          {
            recordId: 'ex-0117',
            note: 'Biomass yield on methanol during induction 0.39 g g⁻¹ — gold annotation.',
          },
          {
            recordId: 'ex-0112',
            note: 'Induction temperature 26 °C — verified.',
          },
        ],
      },
    ],
  },

  // ───────────────────────────────────────────────────────────────────────
  // PR-CIP-01 — pure checklist SOP; every material fixed, safety-dense.
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
      'Derived from SP-007, SP-014 · curated by SMKC · procedural detail is demo content with no literature value',
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
            text: 'Service the probes: calibrate the pH electrode with the {{qty:pH calibration buffer sachets, 4.01 and 7.00}} buffer sachets and install it; charge the dissolved-oxygen electrode with {{qty:Dissolved-oxygen probe electrolyte}} of fresh electrolyte, fit a new membrane and install it. Record the pH slope on the vessel log.',
            note: 'A slope that has dropped more than three points since the previous cycle predicts a mid-run pH failure. Replace the electrode now rather than after it has cost a batch.',
          },
          {
            id: 'c10',
            text: 'Fit the {{qty:0.2 µm inlet air filter}} inlet filter and the {{qty:0.2 µm exhaust filter}} exhaust filter, charge the vessel with 1 L of deionised water, place the {{qty:Biological indicator spore strip}} biological indicator spore strip in the vessel, mark the headplate with {{qty:Autoclave indicator tape}} of indicator tape, and sterilise at 121 °C for 45 min with the vent open.',
            timerSec: 2700,
            timerLabel: 'Sterilise 121 °C, 45 min',
          },
          {
            id: 'c11',
            text: 'Cool in the closed chamber to below 80 °C, then hold the sterilised vessel at 30 °C for 24 h as a sterility hold. Incubate the spore strip at 55 °C for 48 h and read it. Release the vessel only when the hold water is clear, the spore strip is negative, and both results are on the vessel log.',
            timerSec: 3600,
            timerLabel: 'Cool below 80 °C',
            note: 'A vessel that fails the hold goes back to step c2, not to step c10. A failed hold after a passing spore strip means a post-sterilisation ingress point, and re-sterilising will pass again while the ingress point remains.',
          },
        ],
        estMinutes: { active: 180, total: 1560 },
        references: [
          {
            paperId: 'SP-014',
            note: 'In-situ sterilisation and vessel preparation practice at 30 L to 1,200 L scale.',
          },
          {
            paperId: 'SP-007',
            note: 'Flat-panel and bubble-column hardware whose sparger and probe-port fouling this SOP is written against.',
          },
          {
            recordId: 'ex-0112',
            note: 'Induction-phase temperature 26 °C — the setpoint the sterility hold is checked against for the fermentation line.',
          },
        ],
      },
    ],
  },
];
