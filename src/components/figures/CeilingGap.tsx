// What was reported, beside the most a reaction network allows (OF-BLD-014
// §6.1). An EvidenceStrip of a yield field with each computed ceiling as a
// dotted rule labelled with its model. The distance between the points and
// the rules is the figure's whole message, so it prints no derived
// percentage. A point above a rule is ringed, for a reviewer to check its
// basis.
import type { ComputedBasis, ExtractionRecord, Provenance } from '@/data/types';
import { EvidenceStrip, toTable as stripTable, type EvidenceStripProps } from './EvidenceStrip';
import type { FigureTable } from './FigureFrame';

/** The two fixed sentences every ceiling carries (§6.3). */
export const CEILING_NOTES = [
  'A ceiling from flux balance analysis: the most product this reaction network can make from this feed, under the constraints listed. It has no time axis and no vessel.',
  'A genome-scale ceiling uses every reaction in the full reconstruction, including routes a living cell may never run at pace. A reported yield above the line is marked for a reviewer to check its basis.',
];

export interface Ceiling {
  value: number;
  /** The model that made it. */
  model: string;
  basis?: ComputedBasis;
  /** Its own provenance: computed, or assumed for a stand-in network. */
  provenance?: Provenance;
}

export interface CeilingGapProps {
  title: string;
  records: ExtractionRecord[];
  unit: string;
  quantity: string;
  ceilings: Ceiling[];
  groupBy?: EvidenceStripProps['groupBy'];
  csvName?: string;
}

function asStrip(props: CeilingGapProps): EvidenceStripProps {
  return {
    title: props.title,
    records: props.records,
    unit: props.unit,
    quantity: props.quantity,
    groupBy: props.groupBy ?? 'organism',
    rules: props.ceilings.map((c) => ({ value: c.value, label: c.model, provenance: c.provenance ?? 'computed' })),
    flagAbove: true,
    basis: props.ceilings.map((c) => c.basis).filter((b): b is ComputedBasis => Boolean(b)),
    csvName: props.csvName ?? 'ceiling-gap',
    notes: CEILING_NOTES,
    empty: {
      what: 'no reported yield of this field in the store.',
      where: 'Reported yields arrive through Intake and its extraction; ceilings are computed in geneOS → Model.',
    },
  };
}

export function toTable(props: CeilingGapProps): FigureTable {
  return stripTable(asStrip(props));
}

export function CeilingGap(props: CeilingGapProps) {
  return <EvidenceStrip {...asStrip(props)} />;
}
