// The figure system (OF-BLD-014 E.8). Every chart this build adds is made
// from these; `pnpm check:figures` holds the grammar.
export { ENCODING, NEVER_EVIDENCE, pointKey, type MarkStyle } from './encoding';
export { FigureFrame, Mark, EncodingLegend, lineStroke, type FigureTable } from './FigureFrame';
export { EvidenceStrip, stripPoints, median, type EvidenceStripProps, type StripRule } from './EvidenceStrip';
export { CeilingGap, CEILING_NOTES, type CeilingGapProps, type Ceiling } from './CeilingGap';
export { Frontier, toTable as frontierTable, type FrontierProps, type FrontierPoint } from './Frontier';
export { MixLine, type MixLineProps, type MixPoint } from './MixLine';
export { TrajectoryBand, type TrajectoryBandProps, type TrajectorySeries } from './TrajectoryBand';
export { Distribution, toTable as distributionTable, type DistributionProps } from './Distribution';
export { Tornado, toTable as tornadoTable, type TornadoProps, type TornadoRow } from './Tornado';
export { IntervalLedger, type IntervalLedgerProps, type IntervalLedgerRow } from './IntervalLedger';
export { CostWaterfall, waterfallTotal, priceNote, type CostWaterfallProps, type WaterfallLine, type WaterfallBar } from './CostWaterfall';
export { RecoveryByUnit, type RecoveryByUnitProps } from './RecoveryByUnit';
export { OxygenBalance, type OxygenBalanceProps } from './OxygenBalance';
export { TimeCourse, toTable as timeCourseTable, type TimeCourseProps, type TimeCourseState } from './TimeCourse';
export { PurityByStream, noBar as purityNoBar, type PurityByStreamProps } from './PurityByStream';
