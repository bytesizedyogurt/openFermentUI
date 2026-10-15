// The figure system (OF-BLD-014 E.8). Every chart this build adds is made
// from these; `pnpm check:figures` holds the grammar.
export { ENCODING, NEVER_EVIDENCE, pointKey, type MarkStyle } from './encoding';
export { FigureFrame, Mark, EncodingLegend, lineStroke, type FigureTable } from './FigureFrame';
export { EvidenceStrip, stripPoints, median, toTable as evidenceStripTable, type EvidenceStripProps, type StripRule } from './EvidenceStrip';
export { CeilingGap, CEILING_NOTES, toTable as ceilingGapTable, type CeilingGapProps, type Ceiling } from './CeilingGap';
export { Frontier, toTable as frontierTable, type FrontierProps, type FrontierPoint } from './Frontier';
