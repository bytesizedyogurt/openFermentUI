// The figure system (OF-BLD-014 E.8). Every chart this build adds is made
// from these; `pnpm check:figures` holds the grammar.
export { ENCODING, NEVER_EVIDENCE, pointKey, type MarkStyle } from './encoding';
export { FigureFrame, Mark, EncodingLegend, lineStroke, type FigureTable } from './FigureFrame';
export { EvidenceStrip, stripPoints, median, toTable as evidenceStripTable, type EvidenceStripProps, type StripRule } from './EvidenceStrip';
export { CeilingGap, CEILING_NOTES, toTable as ceilingGapTable, type CeilingGapProps, type Ceiling } from './CeilingGap';
export { Frontier, toTable as frontierTable, type FrontierProps, type FrontierPoint } from './Frontier';
export { MixLine, toTable as mixLineTable, type MixLineProps, type MixPoint } from './MixLine';
export { TrajectoryBand, toTable as trajectoryTable, type TrajectoryBandProps, type TrajectorySeries } from './TrajectoryBand';
export { Distribution, toTable as distributionTable, type DistributionProps } from './Distribution';
export { Tornado, toTable as tornadoTable, sorted as tornadoSorted, type TornadoProps, type TornadoRow } from './Tornado';
export { IntervalLedger, toTable as intervalLedgerTable, type IntervalLedgerProps, type IntervalLedgerRow } from './IntervalLedger';
