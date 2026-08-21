// openFerment demo suite — patent families.
//
// ALL NUMBERS AND ASSIGNEES ARE SYNTHETIC. Series are provably impossible:
// US publication years beyond the present, EP numbers beyond current
// numbering, WO years in the future. A reviewer who recognises a real
// assignee attached to fabricated claim scope discards the whole suite, so no
// real company appears anywhere in this file.
//
// The SUBSTANCE is real. Which enzymatic steps attract claims, how families
// cluster around the commercially decisive step, and the fact that the
// overwhelming majority of fermentation patents are never nationalised beyond
// US/EP/CN/JP/KR — those are all true, and they are what the demo argues.
import type { PatentFamily } from './types';

/** Jurisdictions the suite models. RW and ARIPO are where the argument lives. */
export const JURISDICTIONS = ['US', 'EP', 'CN', 'JP', 'KR', 'BR', 'IN', 'ZA', 'KE', 'ARIPO', 'RW'] as const;

export const PATENT_FAMILIES: PatentFamily[] = [
  // ══ Lysine cluster ═══════════════════════════════════════════════════
  {
    id: 'PF-001',
    representativeNumber: 'US 2029/0114872 A1',
    assignee: 'Aurelis Bioindustrie GmbH',
    title: 'Process for producing L-lysine at controlled dissolved oxygen with feedback-resistant aspartokinase',
    priorityDate: '2011-03-14',
    termYears: 20,
    jurisdictions: [
      { code: 'US', status: 'expiring', expiry: '2031-03-14' },
      { code: 'EP', status: 'expiring', expiry: '2031-03-14' },
      { code: 'CN', status: 'enclosed', expiry: '2031-03-14' },
      { code: 'JP', status: 'enclosed', expiry: '2031-03-14' },
      { code: 'KR', status: 'enclosed', expiry: '2031-03-14' },
      { code: 'BR', status: 'never-nationalised' },
      { code: 'IN', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      {
        element: 'Cultivating a Corynebacterium carrying a feedback-resistant aspartokinase under a controlled dissolved oxygen tension',
        fields: ['dissolved_oxygen', 'titer'],
        recitedRange: { field: 'dissolved_oxygen', low: 20, high: 45, unit: '%' },
      },
      {
        element: 'Wherein the cultivation temperature is maintained within a stated band',
        fields: ['temperature'],
        recitedRange: { field: 'temperature', low: 29, high: 33, unit: '°C' },
      },
    ],
    examples: [
      { number: 'Example 3', comparative: false, summary: 'DO held at 30 %, 32 °C, titer within the recited band.', accessionIds: ['OF-A-00142', 'OF-A-00120'] },
      { number: 'Example 5', comparative: true, summary: 'DO reduced to 15 % with agitation raised to compensate. Lactate accumulates; the example exists to show the lower bound is not arbitrary.', accessionIds: ['OF-A-00139'] },
    ],
    notes:
      'The claim recites a DO band of 20–45 %. Operating below 20 % is outside the claim and is also where this family says the process fails. That combination — outside the claim and asserted to fail — is exactly the region worth re-examining, because the assertion rests on one comparative example at one cell density.',
  },
  {
    id: 'PF-002',
    representativeNumber: 'EP 4 917 330 A1',
    assignee: 'Kanto Amino Kagaku K.K.',
    title: 'Two-phase temperature protocol for amino acid fermentation',
    priorityDate: '2014-09-02',
    termYears: 20,
    jurisdictions: [
      { code: 'EP', status: 'enclosed', expiry: '2034-09-02' },
      { code: 'US', status: 'enclosed', expiry: '2034-09-02' },
      { code: 'JP', status: 'enclosed', expiry: '2034-09-02' },
      { code: 'CN', status: 'enclosed', expiry: '2034-09-02' },
      { code: 'KR', status: 'enclosed', expiry: '2034-09-02' },
      { code: 'IN', status: 'pending' },
      { code: 'BR', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      {
        element: 'Growth phase at a first temperature followed by a production phase at a second, higher temperature',
        fields: ['temperature'],
        recitedRange: { field: 'temperature', low: 32, high: 36, unit: '°C' },
      },
    ],
    examples: [
      { number: 'Example 4', comparative: false, summary: 'Shift to 33 °C at 18 h. No titer improvement observed at the cell density used, which the specification attributes to oxygen limitation rather than to the shift.', accessionIds: ['OF-A-00107'] },
      { number: 'Example 7', comparative: true, summary: 'Shift to 37 °C. Titer falls 26 % against the unshifted control.', accessionIds: ['OF-A-00140'] },
      { number: 'Example 9', comparative: true, summary: 'pH allowed to fall to 6.3. Growth arrests at 40 h.', accessionIds: ['OF-A-00143'] },
    ],
    notes:
      'The most valuable entry in the lysine cluster and nobody reads it. Three comparative examples, each a deliberate failure, each carrying a normalisable quantity. Comparative examples exist to demonstrate non-obviousness, which means the applicant is motivated to report failure accurately — the opposite of the publication bias in the journal literature.',
  },
  {
    id: 'PF-003',
    representativeNumber: 'US 2029/0088401 A1',
    assignee: 'Meridian Fermentation Sciences LLC',
    title: 'Enhanced lysine export by transporter overexpression',
    priorityDate: '2008-06-19',
    termYears: 20,
    jurisdictions: [
      { code: 'US', status: 'expiring', expiry: '2028-06-19' },
      { code: 'EP', status: 'expiring', expiry: '2028-06-19' },
      { code: 'CN', status: 'expiring', expiry: '2028-06-19' },
      { code: 'JP', status: 'expired', expiry: '2028-06-19' },
      { code: 'KR', status: 'never-nationalised' },
      { code: 'BR', status: 'never-nationalised' },
      { code: 'IN', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'Corynebacterium with an overexpressed lysine efflux transporter', fields: ['specific_productivity', 'titer'] },
    ],
    examples: [
      { number: 'Example 2', comparative: false, summary: 'Transporter overexpression raises titer against the parent.', accessionIds: ['OF-A-00141'] },
    ],
    notes:
      'Expires 19 June 2028 in every jurisdiction where it was ever in force. Twenty-two months from DEMO_NOW. This is the finding no incumbent tool produces: a step that is enclosed today, unencumbered before a programme started now would reach pilot, and therefore not worth designing around.',
  },

  // ══ 3-HP cluster ═════════════════════════════════════════════════════
  {
    id: 'PF-004',
    representativeNumber: 'US 2029/0201558 A1',
    assignee: 'Verdant Chemicals Inc.',
    title: 'Malonyl-CoA reductase fragments for 3-hydroxypropionic acid biosynthesis',
    priorityDate: '2013-11-08',
    termYears: 20,
    jurisdictions: [
      { code: 'US', status: 'enclosed', expiry: '2033-11-08' },
      { code: 'EP', status: 'enclosed', expiry: '2033-11-08' },
      { code: 'CN', status: 'enclosed', expiry: '2033-11-08' },
      { code: 'JP', status: 'enclosed', expiry: '2033-11-08' },
      { code: 'BR', status: 'enclosed', expiry: '2033-11-08' },
      { code: 'IN', status: 'enclosed', expiry: '2033-11-08' },
      { code: 'KR', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'Separately expressed N-terminal and C-terminal fragments of a bifunctional malonyl-CoA reductase', fields: ['enzyme_activity', 'titer'] },
      { element: 'Host cell comprising an overexpressed acetyl-CoA carboxylase together with said fragments', fields: ['flux_split'] },
    ],
    examples: [
      { number: 'Example 11', comparative: false, summary: 'Split-fragment expression in E. coli fed-batch.', accessionIds: ['OF-A-00224'] },
    ],
    notes: 'The fragment split is the step that made the malonyl-CoA route work, and it is claimed in six jurisdictions including Brazil and India — unusually broad nationalisation, which is itself a signal about how commercially serious the assignee was.',
  },
  {
    id: 'PF-005',
    representativeNumber: 'WO 2028/114872',
    assignee: 'Norhavn Biosolutions A/S',
    title: 'β-alanine mediated production of 3-hydroxypropionic acid',
    priorityDate: '2016-02-25',
    termYears: 20,
    jurisdictions: [
      { code: 'US', status: 'enclosed', expiry: '2036-02-25' },
      { code: 'EP', status: 'enclosed', expiry: '2036-02-25' },
      { code: 'CN', status: 'enclosed', expiry: '2036-02-25' },
      { code: 'JP', status: 'never-nationalised' },
      { code: 'KR', status: 'never-nationalised' },
      { code: 'BR', status: 'never-nationalised' },
      { code: 'IN', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'Conversion of aspartate to β-alanine by a heterologous aspartate 1-decarboxylase in a recombinant host', fields: ['flux_split', 'titer'] },
      { element: 'Transamination of β-alanine to malonate semialdehyde with pyruvate as amino acceptor', fields: ['enzyme_activity'] },
    ],
    examples: [
      { number: 'Example 6', comparative: false, summary: 'Three-enzyme cassette in E. coli, fed-batch on glucose.', accessionIds: ['OF-A-00208'] },
    ],
    notes: 'Covers the route as a whole, not one enzyme. Route-level claims are the hardest to design around and the easiest to miss when screening step by step.',
  },
  {
    id: 'PF-006',
    representativeNumber: 'EP 4 902 117 A1',
    assignee: 'Delta Carbon Technologies Ltd',
    title: 'Coenzyme B12 dependent glycerol dehydration to 3-hydroxypropionaldehyde and onward oxidation',
    priorityDate: '2010-07-30',
    termYears: 20,
    jurisdictions: [
      { code: 'EP', status: 'expiring', expiry: '2030-07-30' },
      { code: 'US', status: 'expiring', expiry: '2030-07-30' },
      { code: 'CN', status: 'expiring', expiry: '2030-07-30' },
      { code: 'IN', status: 'never-nationalised' },
      { code: 'BR', status: 'never-nationalised' },
      { code: 'JP', status: 'never-nationalised' },
      { code: 'KR', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'Dehydration of glycerol by a B12-dependent dehydratase followed by aldehyde dehydrogenase oxidation', fields: ['titer', 'yield_product_substrate'] },
    ],
    examples: [
      { number: 'Example 8', comparative: false, summary: 'Fed-batch on crude glycerol with B12 supplementation.', accessionIds: ['OF-A-00218'] },
      { number: 'Example 12', comparative: true, summary: 'Without B12 supplementation, conversion stops at the dehydratase step.', accessionIds: ['OF-A-00212'] },
    ],
    notes: 'Expires 2030 everywhere it was filed. Four years out — long enough to matter for a programme starting now, short enough to change a licensing posture.',
  },
  {
    id: 'PF-007',
    representativeNumber: 'US 2030/0033914 A1',
    assignee: 'Verdant Chemicals Inc.',
    title: 'Production of organic acids in yeast below the acid dissociation constant',
    priorityDate: '2019-05-11',
    termYears: 20,
    jurisdictions: [
      { code: 'US', status: 'enclosed', expiry: '2039-05-11' },
      { code: 'EP', status: 'enclosed', expiry: '2039-05-11' },
      { code: 'BR', status: 'enclosed', expiry: '2039-05-11' },
      { code: 'CN', status: 'pending' },
      { code: 'JP', status: 'never-nationalised' },
      { code: 'KR', status: 'never-nationalised' },
      { code: 'IN', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'Fermentative production of a C3 organic acid at a broth pH below the pKa of said acid', fields: ['ph', 'titer'], recitedRange: { field: 'ph', low: 2.5, high: 4.4, unit: '' } },
    ],
    examples: [
      { number: 'Example 2', comparative: false, summary: 'S. cerevisiae producing 3-HP at pH 3.5.', accessionIds: ['OF-A-00216'] },
    ],
    notes: 'The newest family in the pool and the broadest in effect: it claims an operating region rather than a mechanism. Any low-pH route in a filed jurisdiction reads on it regardless of which pathway produces the acid.',
  },
  {
    id: 'PF-008',
    representativeNumber: 'WO 2028/220145',
    assignee: 'Norhavn Biosolutions A/S',
    title: 'Aspartate 1-decarboxylase variants with reduced mechanism-based inactivation',
    priorityDate: '2020-10-06',
    termYears: 20,
    jurisdictions: [
      { code: 'US', status: 'enclosed', expiry: '2040-10-06' },
      { code: 'EP', status: 'enclosed', expiry: '2040-10-06' },
      { code: 'CN', status: 'enclosed', expiry: '2040-10-06' },
      { code: 'KR', status: 'enclosed', expiry: '2040-10-06' },
      { code: 'JP', status: 'never-nationalised' },
      { code: 'BR', status: 'never-nationalised' },
      { code: 'IN', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'Aspartate 1-decarboxylase comprising a specified substitution set, and host cells comprising it', fields: ['enzyme_activity'] },
    ],
    examples: [
      { number: 'Example 3', comparative: false, summary: 'Variant retains activity over an extended production window against the wild-type enzyme.', accessionIds: ['OF-A-00210'] },
    ],
    notes: 'Narrow, recent, and blocking. The wild-type enzyme is free; the variant that makes the route industrially viable is not. This is the shape that catches programmes late — the route screens clean at the pathway level and fails at one substitution.',
  },

  // ══ Meat-analogue cluster ════════════════════════════════════════════
  {
    id: 'PF-009',
    representativeNumber: 'US 2029/0177203 A1',
    assignee: 'Sanguine Foods Ltd',
    title: 'Heme-containing protein produced by a methylotrophic yeast for use in a meat substitute',
    priorityDate: '2012-04-17',
    termYears: 20,
    jurisdictions: [
      { code: 'US', status: 'enclosed', expiry: '2032-04-17' },
      { code: 'EP', status: 'enclosed', expiry: '2032-04-17' },
      { code: 'CN', status: 'enclosed', expiry: '2032-04-17' },
      { code: 'JP', status: 'enclosed', expiry: '2032-04-17' },
      { code: 'KR', status: 'enclosed', expiry: '2032-04-17' },
      { code: 'BR', status: 'enclosed', expiry: '2032-04-17' },
      { code: 'IN', status: 'enclosed', expiry: '2032-04-17' },
      { code: 'ZA', status: 'enclosed', expiry: '2032-04-17' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'A meat substitute comprising a recombinant heme-containing protein at a specified concentration', fields: ['purity', 'titer'], recitedRange: { field: 'purity', low: 0.1, high: 5, unit: '% (w/w)' } },
      { element: 'Method of producing said protein in a methylotrophic yeast with augmented heme biosynthesis', fields: ['flux_split'] },
    ],
    examples: [
      { number: 'Example 1', comparative: false, summary: 'Secreted globin at gram-per-litre scale with heme co-supplementation.', accessionIds: ['OF-A-00502', 'OF-A-00503'] },
    ],
    notes:
      'Eight jurisdictions. The densest family in the pool and it covers both the composition and the method. This is the branch a decomposition should route around rather than through, and the asymmetry against PF-010 is the whole finding of Archetype 5.',
  },
  {
    id: 'PF-010',
    representativeNumber: 'EP 4 944 088 A1',
    assignee: 'Lipidor Process AB',
    title: 'Structured triacylglycerol composition having a defined solid fat content profile',
    priorityDate: '2021-01-22',
    termYears: 20,
    jurisdictions: [
      { code: 'EP', status: 'enclosed', expiry: '2041-01-22' },
      { code: 'US', status: 'pending' },
      { code: 'CN', status: 'never-nationalised' },
      { code: 'JP', status: 'never-nationalised' },
      { code: 'KR', status: 'never-nationalised' },
      { code: 'BR', status: 'never-nationalised' },
      { code: 'IN', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'A fat composition having a stated solid fat content at 20 °C and at 35 °C', fields: ['purity'] },
    ],
    examples: [
      { number: 'Example 4', comparative: false, summary: 'Blended structured fat meeting the recited melting profile.', accessionIds: ['OF-A-00505', 'OF-A-00506'] },
    ],
    notes:
      'One jurisdiction in force and one pending. Against PF-009 this is an open field, and the technical requirement — a fat phase that is solid at 20 °C and substantially melted at 35 °C — is a well-posed engineering target with several unclaimed routes to it. Microbial routes to that profile are not claimed by anyone in this pool.',
  },
  {
    id: 'PF-011',
    representativeNumber: 'US 2029/0310664 A1',
    assignee: 'Textura Process AB',
    title: 'Shear-cell texturisation of high-moisture protein systems',
    priorityDate: '2017-08-30',
    termYears: 20,
    jurisdictions: [
      { code: 'US', status: 'enclosed', expiry: '2037-08-30' },
      { code: 'EP', status: 'enclosed', expiry: '2037-08-30' },
      { code: 'CN', status: 'enclosed', expiry: '2037-08-30' },
      { code: 'JP', status: 'never-nationalised' },
      { code: 'KR', status: 'never-nationalised' },
      { code: 'BR', status: 'never-nationalised' },
      { code: 'IN', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'Applying a defined shear field to a hydrated protein mass to produce anisotropic fibre alignment', fields: ['purity'] },
    ],
    examples: [
      { number: 'Example 5', comparative: false, summary: 'Anisotropy index achieved at the recited shear rate and temperature.', accessionIds: ['OF-A-00511'] },
    ],
    notes: 'Claims the unit operation. A native-morphology organism route sidesteps it entirely, which is why the fibrous branch has two structurally different options rather than one optimised one.',
  },

  // ══ Lignocellulose cluster ═══════════════════════════════════════════
  {
    id: 'PF-012',
    representativeNumber: 'WO 2028/041992',
    assignee: 'Thermolytic Bioworks Pte Ltd',
    title: 'Thermophilic homofermentative lactate production from lignocellulosic hydrolysate',
    priorityDate: '2018-12-04',
    termYears: 20,
    jurisdictions: [
      { code: 'US', status: 'enclosed', expiry: '2038-12-04' },
      { code: 'CN', status: 'enclosed', expiry: '2038-12-04' },
      { code: 'BR', status: 'enclosed', expiry: '2038-12-04' },
      { code: 'EP', status: 'never-nationalised' },
      { code: 'JP', status: 'never-nationalised' },
      { code: 'KR', status: 'never-nationalised' },
      { code: 'IN', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'Fermentation of a pentose-containing hydrolysate above 48 °C by a homofermentative Bacillus', fields: ['temperature', 'titer'], recitedRange: { field: 'temperature', low: 48, high: 58, unit: '°C' } },
    ],
    examples: [
      { number: 'Example 7', comparative: false, summary: 'Mixed C5/C6 hydrolysate fermented at 52 °C to lactate.', accessionIds: ['OF-A-00406'] },
    ],
    notes:
      'Enclosed in the US, China and Brazil. Never entered EP, and never entered any African jurisdiction. The thermophilic route that solves the tropical cooling problem is claimed precisely where the cooling problem does not exist.',
  },
  {
    id: 'PF-013',
    representativeNumber: 'US 2028/0455201 A1',
    assignee: 'Pentose Valorisation Corp.',
    title: 'Catalytic and fermentative routes to xylitol from hemicellulose hydrolysate',
    priorityDate: '2009-02-11',
    termYears: 20,
    jurisdictions: [
      { code: 'US', status: 'expired', expiry: '2029-02-11' },
      { code: 'EP', status: 'expired', expiry: '2029-02-11' },
      { code: 'CN', status: 'expiring', expiry: '2029-02-11' },
      { code: 'BR', status: 'never-nationalised' },
      { code: 'IN', status: 'never-nationalised' },
      { code: 'JP', status: 'never-nationalised' },
      { code: 'KR', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'Hydrogenation or bioconversion of a xylose-rich stream to xylitol', fields: ['yield_product_substrate'] },
    ],
    examples: [
      { number: 'Example 1', comparative: false, summary: 'Xylose stream converted at stated yield.', accessionIds: ['OF-A-00417'] },
    ],
    notes: 'Expired or expiring everywhere. The pentose half of the two-stream bagasse concept is effectively free, which is why the concept puts the C5 stream on the high-value product and the C6 stream on the commodity.',
  },
  {
    id: 'PF-014',
    representativeNumber: 'EP 4 928 776 A1',
    assignee: 'Solvora Pretreatment Systems N.V.',
    title: 'Organosolv fractionation with integrated solvent recovery',
    priorityDate: '2016-06-28',
    termYears: 20,
    jurisdictions: [
      { code: 'EP', status: 'enclosed', expiry: '2036-06-28' },
      { code: 'US', status: 'enclosed', expiry: '2036-06-28' },
      { code: 'BR', status: 'enclosed', expiry: '2036-06-28' },
      { code: 'CN', status: 'never-nationalised' },
      { code: 'JP', status: 'never-nationalised' },
      { code: 'KR', status: 'never-nationalised' },
      { code: 'IN', status: 'never-nationalised' },
      { code: 'ZA', status: 'never-nationalised' },
      { code: 'KE', status: 'never-nationalised' },
      { code: 'ARIPO', status: 'never-nationalised' },
      { code: 'RW', status: 'never-nationalised' },
    ],
    claimScope: [
      { element: 'Fractionating lignocellulose with an aqueous organic solvent and recovering said solvent by a stated separation train', fields: ['yield_product_substrate', 'capex'] },
    ],
    examples: [
      { number: 'Example 2', comparative: false, summary: 'Bagasse fractionated at stated severity; sugar yield and inhibitor profile reported.', accessionIds: ['OF-A-00409', 'OF-A-00412'] },
    ],
    notes: 'The pretreatment with the best sugar yield and the lowest inhibitor load is also the one that is claimed and the one with the highest capital intensity. Two of those three facts are usually discovered separately and late.',
  },
];

export const PATENT_BY_ID: Record<string, PatentFamily> = Object.fromEntries(PATENT_FAMILIES.map((p) => [p.id, p]));

/**
 * The finding the capacity screen turns on, computed rather than asserted.
 * Returns families with no in-force claim in the given jurisdiction.
 */
export function openIn(jurisdiction: string, familyIds?: string[]): PatentFamily[] {
  const pool = familyIds ? PATENT_FAMILIES.filter((f) => familyIds.includes(f.id)) : PATENT_FAMILIES;
  return pool.filter((f) => {
    const j = f.jurisdictions.find((x) => x.code === jurisdiction);
    return !j || j.status === 'never-nationalised' || j.status === 'expired';
  });
}

/** Months until expiry, against the frozen DEMO_NOW. Never `new Date()`. */
export function monthsToExpiry(iso: string, demoNow: string): number {
  const a = new Date(demoNow);
  const b = new Date(iso);
  return Math.round((b.getTime() - a.getTime()) / (1000 * 60 * 60 * 24 * 30.44));
}
