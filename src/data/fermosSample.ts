// fermOS's sample run (OF-BLD-014 §7.4). INVENTED: a time course
// `demo.py --prototype` makes from a logistic curve with a fixed scatter and
// writes to fermosSample.json, so the Fits and Forecast views have something
// to show before a real run is deposited, and the smoke double's fixtures fit
// these same readings. Like Guild's sample team it stays in the browser: a
// fit or forecast over it is computed inline (`sample: true`), labelled as
// sample, and kept in neither the artifact store nor the ledger. Nothing here
// is a measurement, a literature value or a result, and nothing here enters
// fermOS's fits of real runs.
import type { FermosSeries } from './types';
import sample from './fermosSample.json';

export const SAMPLE_NOTE: string = sample._sample;
export const SAMPLE_DEPOSITION_ID = 'sample-run';
export const SAMPLE_SERIES = sample.series as unknown as FermosSeries[];
