// The Chemical Engineering Plant Cost Index.
//
// Ported from BioSTEAM v2.53.11 `units/design_tools/cost_index.py`, together
// with the module-global `CE` defined in `biosteam/__init__.py` (UIUC/NCSA
// licence; see NOTICE.md). The upstream table is reproduced whole. Nothing else
// lives in that file, so nothing is left behind but the Python docstring.
//
// The index is what makes a published purchase cost mean anything at all. A
// correlation fitted against 2007 quotations returns 2007 dollars, and a plant
// costed today from that correlation is wrong by whatever the market has done to
// equipment prices in the meantime — between 2007 and 2021 that is about a third
// of the number. So every correlation in this port carries the index it was
// published at, and its cost is multiplied by CE / CE_published at the moment it
// is applied. Dropping that ratio is not a rounding error, it is a different
// answer, and it is the single easiest way to make a capital estimate look
// cheap without lying about anything a reviewer can see.

/**
 * Chemical Engineering Plant Cost Index, by year. Dimensionless — only ratios
 * of two entries are ever meaningful.
 *
 * 1980–2014 are upstream's original figures. 2015–2021 were added by bioSTEAM
 * from https://www.toweringskills.com/financial-analysis/cost-indices/
 * (upstream records the access date as 2022-11-25), which is why 2017 reads 568
 * here while `CE` below still defaults to the 567.5 bioSTEAM has always used.
 */
export const CEPCI_BY_YEAR: Record<number, number> = {
  1980: 261,
  1981: 297,
  1982: 314,
  1983: 317,
  1984: 323,
  1985: 325,
  1986: 318,
  1987: 324,
  1988: 343,
  1989: 355,
  1990: 358,
  1991: 361,
  1992: 358,
  1993: 359,
  1994: 368,
  1995: 381,
  1996: 382,
  1997: 387,
  1998: 390,
  1999: 391,
  2000: 394,
  2001: 394,
  2002: 396,
  2003: 402,
  2004: 444,
  2005: 468,
  2006: 500,
  2007: 525,
  2008: 575,
  2009: 522,
  2010: 551,
  2011: 586,
  2012: 585,
  2013: 567,
  2014: 576,
  2015: 557,
  2016: 542,
  2017: 568,
  2018: 603,
  2019: 608,
  2020: 596,
  2021: 708,
};

/** Most recent year the table covers. */
export const CEPCI_LATEST_YEAR: number = 2021;

/**
 * The index every cost correlation in this directory is scaled to, mutable at
 * run time.
 *
 * 567.5 is bioSTEAM's own default (`CE: float = 567.5`, 2017 basis). It is a
 * holder object rather than a bare number because `unit.ts` reads `CE.value`
 * when it prices a design, exactly as upstream reads the module-global
 * `bst.CE`: changing the year has to change what every already-imported
 * correlation charges, and an exported `number` binding cannot do that.
 */
export const CE: { value: number } = { value: 567.5 };

/**
 * Set the working cost index to a given year's CEPCI.
 *
 * Throws rather than falling back to the nearest year, because a silent
 * substitution here shifts a capital estimate by tens of per cent with nothing
 * on screen to show for it.
 */
export function setCEPCI(year: number): void {
  const index: number | undefined = CEPCI_BY_YEAR[year];
  if (index === undefined) {
    throw new Error(
      `No CEPCI on record for ${year}; the table covers 1980 to ${CEPCI_LATEST_YEAR}.`,
    );
  }
  CE.value = index;
}
