// Discounted-cash-flow techno-economic analysis: the cash flow table, and the
// two solves that read backwards off it — break-even IRR and break-even price.
//
// Ported from BioSTEAM v2.53.11 `_tea.py` (UIUC/NCSA licence; see NOTICE.md),
// together with the `SugarcaneTEA` subclass from the upstream tutorial notebook
// `docs/tutorial/Techno-economic_analysis.ipynb`. The notebook matters as much
// as the module: upstream's `TEA` is abstract in `_DPI`, `_TDC`, `_FCI` and
// `_FOC`, and the notebook is where those four are actually given bodies,
// following Huang, Long & Singh (2016).
//
// bioSTEAM leaves `TEA` abstract on purpose — it will not pick a capital
// factoring convention on your behalf, because that choice is an assumption a
// reviewer is entitled to see. Subclassing per convention would be the faithful
// port, but a single browser session has no place to put a class hierarchy the
// user cannot edit, so the convention is data here instead: the eight
// NREL/Humbird factors on `TEAOptions` all default to zero, which collapses
// DPI = TDC = FCI and reproduces the Huang assumption the tutorial uses exactly.
// Set them and you get the Humbird 2011 direct/indirect build-up instead.
//
// Everything is plain USD. Upstream divides the whole cash flow table by 1e6
// for display; that is a presentation choice and it is not made here.
//
// What is deliberately NOT ported:
//
//   * Inflation. Upstream escalates costs, sales, capital and working capital
//     by `(1 + inflation_rate)^t` and discounts at the Fisher-nominal rate.
//     Half of that machinery — nominal cashflows discounted at a real rate, or
//     the reverse — silently misprices a project by the inflation rate
//     compounded over twenty years, so it is left out whole rather than left
//     out partly. Every number here is base-year dollars discounted at the
//     real IRR, which is what upstream does when `inflation_rate` is None.
//   * Agile systems (`bst.AgileSystem`): multiple operation modes sharing one
//     capital base. `BioSystem` has a single operating mode by construction.
//   * Life-cycle assessment and characterisation-factor accounting.
//   * Incentives. Upstream reserves a per-year incentives array that its
//     subclasses (state tax credits, and so on) fill in. It stays zero here,
//     and the column is dropped from `CashflowRow` rather than shown as a
//     column of zeros that implies incentives were considered.
//   * Replacement costs. Upstream re-buys a unit every `equipment_lifetime`
//     years and adds it to the fixed-capital row. No unit in this port carries
//     an equipment lifetime, so there is nothing to schedule.
//   * `investment_site_factors`, the `Accounting` report tables, and
//     `production_costs` / `total_production_cost` allocation across
//     co-products.
//   * `accumulate_interest_during_construction`. Upstream defaults it to False
//     — interest during construction is paid as it accrues rather than rolled
//     into the principal — and that default is fixed here.
import { solveBrentq } from './solvers';
import type { BioSystem } from './system';
import { massFlow, type Stream } from './types';

/**
 * Depreciation schedules, as fractions of total depreciable capital per year.
 *
 * MACRS is the U.S. IRS publication 946 modified accelerated cost recovery
 * system under the half-year convention, which is why an n-year schedule runs
 * over n+1 years: half a year of depreciation is taken in the first year and
 * the remainder trails into the last.
 *
 * Upstream keys these by the tuple `('MACRS', 7)`; a flat string key is the
 * same information in the form the `depreciation` option already carries.
 */
export const DEPRECIATION_SCHEDULES: Record<string, number[]> = {
  MACRS3: [0.3333, 0.4445, 0.1481, 0.0741],

  MACRS5: [0.2, 0.32, 0.192, 0.1152, 0.1152, 0.0576],

  MACRS7: [0.1429, 0.2449, 0.1749, 0.1249, 0.0893, 0.0892, 0.0893, 0.0446],

  MACRS10: [
    0.1, 0.18, 0.144, 0.1152, 0.0922, 0.0737, 0.0655, 0.0655, 0.0656, 0.0655,
    0.0328,
  ],

  MACRS15: [
    0.05, 0.095, 0.0855, 0.077, 0.0693, 0.0623, 0.059, 0.059, 0.0591, 0.059,
    0.0591, 0.059, 0.0591, 0.059, 0.0591, 0.0295,
  ],

  MACRS20: [
    0.0375, 0.07219, 0.06677, 0.06177, 0.05713, 0.05285, 0.04888, 0.04522,
    0.04462, 0.04461, 0.04462, 0.04461, 0.04462, 0.04461, 0.04462, 0.04461,
    0.04462, 0.04461, 0.04462, 0.04461, 0.02231,
  ],
};

/**
 * Double-declining-balance schedule over `years` years.
 *
 * Each year takes 2/n of whatever book value is left, so the schedule never
 * quite reaches zero and the fractions do not sum to one — upstream does not
 * switch to straight line at the crossover point, and neither does this.
 */
export function generateDDBSchedule(years: number): number[] {
  let val = 1;
  const arr = new Array<number>(years).fill(1);
  const factor = 2 / years;
  for (let i = 0; i < years; i++) {
    const depreciation = val * factor;
    arr[i] = depreciation;
    val -= depreciation;
  }
  return arr;
}

/** Sum-of-the-years'-digits schedule over `years` years. These do sum to one. */
export function generateSYDSchedule(years: number): number[] {
  const digitSum = (years * (years + 1)) / 2;
  const arr = new Array<number>(years).fill(1);
  for (let i = 0; i < years; i++) arr[i] = (years - i) / digitSum;
  return arr;
}

export interface TEAOptions {
  /** Real internal rate of return, fraction. */
  IRR: number;
  /** Start and end year of the venture, e.g. [2018, 2038] — 20 operating years. */
  duration: [startYear: number, endYear: number];
  /** '{schedule}{years}', e.g. 'MACRS7', 'SL10', 'DDB10', 'SYD10'. */
  depreciation: string;
  /** Combined federal and state income tax, fraction. */
  incomeTax: number;
  /** Operating days per year. Sets the system's operating hours. */
  operatingDays: number;
  /**
   * Lang factor: fixed capital as a multiple of total purchase cost. When set,
   * bare-module factors are bypassed. Null to use the units' own F_BM.
   */
  langFactor: number | null;
  /** Capital investment fraction per construction year, e.g. [0.4, 0.6]. */
  constructionSchedule: number[];
  /** Startup time, months. */
  startupMonths: number;
  /** Fraction of fixed operating cost incurred during startup. */
  startupFOCfrac: number;
  /** Fraction of variable operating cost incurred during startup. */
  startupVOCfrac: number;
  /** Fraction of sales achieved during startup. */
  startupSalesfrac: number;
  /** Working capital as a fraction of fixed capital investment. */
  WC_over_FCI: number;
  /** Nominal yearly interest on the loan, fraction. Zero for an unfinanced project. */
  financeInterest: number;
  /** Years over which the loan is repaid. */
  financeYears: number;
  /** Fraction of capital cost that is financed. */
  financeFraction: number;

  // Fixed operating cost, in the decomposition SugarcaneTEA uses.
  /** Total labour cost, USD/yr. */
  laborCost: number;
  /** Fringe benefits as a fraction of labour cost. */
  fringeBenefits: number;
  /** Yearly fee as a fraction of fixed capital investment. */
  propertyTax: number;
  /** Yearly fee as a fraction of fixed capital investment. */
  propertyInsurance: number;
  /** Yearly fee as a fraction of labour cost. */
  supplies: number;
  /** Yearly fee as a fraction of fixed capital investment. */
  maintenance: number;
  /** Yearly fee as a fraction of fixed capital investment. */
  administration: number;

  // Direct and indirect capital factors, Humbird 2011 (NREL/TP-5100-47764).
  // Direct factors lift installed equipment cost to DPI; indirect factors lift
  // DPI to TDC. All default to zero, which is DPI = TDC = FCI = installed cost.
  /** Warehouse, fraction of installed equipment cost. */
  warehouse?: number;
  /** Site development, fraction of installed equipment cost. */
  siteDevelopment?: number;
  /** Additional piping, fraction of installed equipment cost. */
  additionalPiping?: number;
  /** Proratable costs, fraction of DPI. */
  proratableCosts?: number;
  /** Field expenses, fraction of DPI. */
  fieldExpenses?: number;
  /** Home office and construction, fraction of DPI. */
  construction?: number;
  /** Project contingency, fraction of DPI. */
  contingency?: number;
  /** Other indirect costs — start-up, permits — as a fraction of DPI. */
  otherIndirect?: number;
}

/**
 * One year of the cash flow table.
 *
 * Every field is USD except `year` and `discountFactor`. Upstream reports the
 * whole table in millions; the scaling belongs to whatever draws it.
 */
export interface CashflowRow {
  /**
   * Calendar year. Construction years run before `duration[0]`, so the table
   * opens at `duration[0] - constructionSchedule.length`. Upstream's current
   * DataFrame is indexed by years relative to the last construction year
   * instead; the two differ by that same offset and nothing else.
   */
  year: number;
  depreciableCapital: number;
  fixedCapitalInvestment: number;
  workingCapital: number;
  depreciation: number;
  /** Money received from the loan. */
  loan: number;
  loanInterestPayment: number;
  loanPayment: number;
  /** Outstanding principal at the end of the year. */
  loanPrincipal: number;
  /** Annual operating cost, excluding depreciation. */
  annualOperatingCost: number;
  sales: number;
  tax: number;
  /** Taxable earnings after losses carried forward from earlier years. */
  taxedEarnings: number;
  /**
   * Losses carried into this year and still available to offset earnings,
   * reported negative as upstream reports it. It returns to zero in the year
   * the accumulated loss is finally absorbed.
   */
  forwardedLosses: number;
  netEarnings: number;
  cashFlow: number;
  discountFactor: number;
  NPV: number;
  cumulativeNPV: number;
}

function zeros(n: number): number[] {
  return new Array<number>(n).fill(0);
}

/**
 * Taxable earnings after carrying losses forward.
 *
 * A loss in one year is not refunded; it reduces the tax due in the following
 * year, and if that year is also a loss the whole lot rolls on again. A
 * project that loses money early and earns it back later would otherwise be
 * taxed on the recovery as though the loss had never happened, which overstates
 * the tax bill and understates the IRR.
 *
 * Upstream calls this `taxable_earnings_with_fowarded_losses`; the misspelling
 * is upstream's own and is corrected here, because a reader grepping the Python
 * for "forwarded" will not find it either way and a wrong word in a public name
 * is not worth preserving for its own sake.
 */
function taxableEarningsWithForwardedLosses(taxableCashflow: number[]): number[] {
  const taxedEarnings = taxableCashflow.slice();
  for (let i = 0; i < taxedEarnings.length - 1; i++) {
    const x = taxedEarnings[i];
    if (x < 0) {
      taxedEarnings[i] = 0;
      taxedEarnings[i + 1] += x;
    }
  }
  // A loss in the final year has nowhere to go: the venture ends and the
  // shelter expires unused.
  const last = taxedEarnings.length - 1;
  if (taxedEarnings[last] < 0) taxedEarnings[last] = 0;
  return taxedEarnings;
}

/** Loan principal at the end of construction when interest is rolled up into it. */
function loanPrincipalWithInterest(loan: number[], interest: number): number {
  let principal = 0;
  const k = 1 + interest;
  for (const i of loan) {
    principal *= k;
    principal += i;
  }
  return principal;
}

/** The level annual payment that retires `principal` over `years` at `interest`. */
function solvePayment(principal: number, interest: number, years: number): number {
  const f = 1 + interest;
  const fn = f ** years;
  return (principal * interest * fn) / (fn - 1);
}

export class TEA {
  system: BioSystem;

  /** Real internal rate of return, fraction. Mutable — `tea.IRR = tea.solveIRR()`. */
  IRR: number;
  duration: [number, number];
  depreciation: string;
  incomeTax: number;
  langFactor: number | null;
  constructionSchedule: number[];
  startupMonths: number;
  startupFOCfrac: number;
  startupVOCfrac: number;
  startupSalesfrac: number;
  WC_over_FCI: number;
  financeInterest: number;
  financeYears: number;
  financeFraction: number;
  laborCost: number;
  fringeBenefits: number;
  propertyTax: number;
  propertyInsurance: number;
  supplies: number;
  maintenance: number;
  administration: number;
  warehouse: number;
  siteDevelopment: number;
  additionalPiping: number;
  proratableCosts: number;
  fieldExpenses: number;
  construction: number;
  contingency: number;
  otherIndirect: number;

  constructor(system: BioSystem, options: TEAOptions) {
    this.system = system;
    this.IRR = options.IRR;
    // Upstream stores `duration` as `[int(start), int(end)]`; the venture length
    // is an array length downstream, so a fractional year has to be truncated
    // here rather than turned into an unallocatable array further down.
    this.duration = [Math.trunc(options.duration[0]), Math.trunc(options.duration[1])];
    this.depreciation = options.depreciation;
    this.incomeTax = options.incomeTax;
    this.langFactor = options.langFactor;
    this.constructionSchedule = options.constructionSchedule.slice();
    this.startupMonths = options.startupMonths;
    this.startupFOCfrac = options.startupFOCfrac;
    this.startupVOCfrac = options.startupVOCfrac;
    this.startupSalesfrac = options.startupSalesfrac;
    this.WC_over_FCI = options.WC_over_FCI;
    this.financeInterest = options.financeInterest;
    this.financeYears = options.financeYears;
    this.financeFraction = options.financeFraction;
    this.laborCost = options.laborCost;
    this.fringeBenefits = options.fringeBenefits;
    this.propertyTax = options.propertyTax;
    this.propertyInsurance = options.propertyInsurance;
    this.supplies = options.supplies;
    this.maintenance = options.maintenance;
    this.administration = options.administration;
    this.warehouse = options.warehouse ?? 0;
    this.siteDevelopment = options.siteDevelopment ?? 0;
    this.additionalPiping = options.additionalPiping ?? 0;
    this.proratableCosts = options.proratableCosts ?? 0;
    this.fieldExpenses = options.fieldExpenses ?? 0;
    this.construction = options.construction ?? 0;
    this.contingency = options.contingency ?? 0;
    this.otherIndirect = options.otherIndirect ?? 0;

    // Operating days live on the system, not on the TEA, because the material
    // and utility costs the TEA reads are already annualised by it. Upstream
    // writes through to `system.operating_hours` in exactly the same way, and
    // the alternative — two places that both believe they know the operating
    // schedule — is how a plant ends up costed on 200 days and priced on 330.
    this.operatingDays = options.operatingDays;
  }

  /** Operating days per year. */
  get operatingDays(): number {
    return this.system.operatingHours / 24;
  }
  set operatingDays(days: number) {
    this.system.operatingHours = 24 * days;
  }

  /** Number of construction years, and the index at which operation begins. */
  private get start(): number {
    const start = this.constructionSchedule.length;
    if (start < 1) {
      throw new Error(
        'construction schedule must have at least one year; working capital is ' +
          'placed in the year before operation begins and there is no such year',
      );
    }
    return start;
  }

  /** Operating years. */
  private get years(): number {
    return this.duration[1] - this.duration[0];
  }

  // Capital build-up. Named for upstream's abstract methods so the two can be
  // read side by side.

  private _DPI(installedEquipmentCost: number): number {
    return (
      installedEquipmentCost *
      (1 + this.warehouse + this.siteDevelopment + this.additionalPiping)
    );
  }

  private _TDC(DPI: number): number {
    return (
      DPI *
      (1 +
        this.proratableCosts +
        this.fieldExpenses +
        this.construction +
        this.contingency +
        this.otherIndirect)
    );
  }

  private _FCI(TDC: number): number {
    // Humbird's indirect costs are all depreciable, so nothing separates fixed
    // capital from total depreciable capital here. Land would, but land is not
    // costed by anything upstream of this module.
    return TDC;
  }

  private _FOC(FCI: number): number {
    return (
      FCI *
        (this.propertyTax +
          this.propertyInsurance +
          this.maintenance +
          this.administration) +
      this.laborCost * (1 + this.fringeBenefits + this.supplies)
    );
  }

  /**
   * Total installed equipment cost, USD.
   *
   * With a Lang factor there is no way back to an installed equipment cost, so
   * upstream treats installed cost, TDC and FCI as the same number and says so
   * in a warning. The same shortcut is taken here.
   */
  get installedEquipmentCost(): number {
    const lang = this.langFactor;
    return lang ? this.system.purchaseCost * lang : this.system.installedEquipmentCost;
  }

  /** Total purchase cost, USD. */
  get purchaseCost(): number {
    return this.system.purchaseCost;
  }

  /** Direct permanent investment, USD. */
  get DPI(): number {
    return this._DPI(this.installedEquipmentCost);
  }

  /** Total depreciable capital, USD. */
  get TDC(): number {
    return this._TDC(this.DPI);
  }

  /** Fixed capital investment, USD. */
  get FCI(): number {
    return this._FCI(this.TDC);
  }

  /** Total capital investment — fixed plus working, USD. */
  get TCI(): number {
    return (1 + this.WC_over_FCI) * this.FCI;
  }

  /** Working capital, USD. */
  get workingCapital(): number {
    return this.WC_over_FCI * this.FCI;
  }

  /** Fixed operating cost, USD/yr. */
  get FOC(): number {
    return this._FOC(this.FCI);
  }

  /** Variable operating cost — materials and utilities, USD/yr. */
  get VOC(): number {
    return this.materialCost + this.utilityCost;
  }

  /** Annual operating cost excluding depreciation, USD/yr. */
  get AOC(): number {
    return this.FOC + this.VOC;
  }

  /** Annual sales revenue, USD/yr. */
  get sales(): number {
    return (
      this.system.products.reduce((t, s) => t + s.price * massFlow(s), 0) *
      this.system.operatingHours
    );
  }

  /** Annual material cost, USD/yr. */
  get materialCost(): number {
    return this.system.materialCost;
  }

  /** Annual utility cost, USD/yr. */
  get utilityCost(): number {
    return this.system.utilityCost;
  }

  /**
   * Total depreciable capital spread flat over the venture, USD/yr.
   *
   * This is not the depreciation the tax calculation uses — that follows the
   * MACRS schedule and is front-loaded. It is the straight-line figure that
   * belongs in a production cost, where charging a product for eight years of
   * accelerated depreciation and nothing thereafter would be meaningless.
   */
  get annualDepreciation(): number {
    return this.TDC / (this.duration[1] - this.duration[0]);
  }

  /**
   * Net earnings at steady state, USD/yr, ignoring annualised depreciation.
   *
   * A loss is not taxed, and it is also not credited: upstream returns the loss
   * gross rather than multiplying it by `(1 - income_tax)`, which would quietly
   * assume the losses are worth something against income earned elsewhere.
   */
  get netEarnings(): number {
    const netEarnings = this.sales - this.AOC;
    return netEarnings < 0 ? netEarnings : (1 - this.incomeTax) * netEarnings;
  }

  /** Return on investment, 1/yr, ignoring annualised depreciation. */
  get ROI(): number {
    return this.netEarnings / this.TCI;
  }

  /** Payback period, years, ignoring annualised depreciation and the time value of money. */
  get PBP(): number {
    return this.FCI / this.netEarnings;
  }

  /**
   * Net present value at the current IRR, USD.
   *
   * Upstream computes this without building the table, off `TDC * Σ(schedule)`
   * escalated for inflation rather than off the depreciable-capital row. With
   * inflation left out those two are the same number, so the table is built and
   * its last cumulative NPV read instead — one implementation to audit rather
   * than two that must be kept in agreement.
   */
  get NPV(): number {
    const table = this.getCashflowTable();
    return table[table.length - 1].cumulativeNPV;
  }

  /** The depreciation schedule named by `this.depreciation`, as yearly fractions. */
  private getDepreciationArray(): number[] {
    const name = this.depreciation;
    for (const prefix of ['MACRS', 'SL', 'DDB', 'SYD']) {
      if (!name.startsWith(prefix)) continue;
      const suffix = name.slice(prefix.length);
      // An omitted year count means "depreciate over the whole venture".
      const years = suffix === '' ? this.years : Number(suffix);
      if (!Number.isInteger(years) || years < 1) {
        throw new Error(`invalid depreciation period in '${name}'`);
      }
      if (prefix === 'MACRS') {
        const schedule = DEPRECIATION_SCHEDULES[`MACRS${years}`];
        if (!schedule) {
          throw new Error(
            `depreciation name '${name}' has a valid format, but only MACRS ` +
              '3, 5, 7, 10, 15 and 20 are published',
          );
        }
        return schedule;
      }
      if (prefix === 'SL') return new Array<number>(years).fill(1 / years);
      if (prefix === 'DDB') return generateDDBSchedule(years);
      return generateSYDSchedule(years);
    }
    throw new Error(
      `invalid depreciation name '${name}'; expected '{schedule}{years}' where ` +
        "schedule is one of 'MACRS', 'SL', 'DDB' or 'SYD'",
    );
  }

  /**
   * The full cash flow analysis, one row per year of the venture.
   *
   * Rows run from the first construction year through the last operating year:
   * `constructionSchedule.length + (duration[1] - duration[0])` of them.
   */
  getCashflowTable(): CashflowRow[] {
    const start = this.start;
    const years = this.years;
    const length = start + years;
    const TDC0 = this.TDC;
    const FCI = this._FCI(TDC0);
    const FOC = this._FOC(FCI);
    const VOC = this.VOC;
    const sales = this.sales;
    const WC = this.WC_over_FCI * FCI;

    const C_D = zeros(length); // depreciable capital
    const C_FC = zeros(length); // fixed capital
    const C_WC = zeros(length); // working capital
    const D = zeros(length); // depreciation
    const L = zeros(length); // loan drawn
    const LI = zeros(length); // loan interest paid
    const LP = zeros(length); // loan payment
    const LPl = zeros(length); // loan principal outstanding
    const C = zeros(length); // annual operating cost, excluding depreciation
    const S = zeros(length); // sales

    // Startup. A startup time that is not a whole number of years splits the
    // year it lands in: `w0` of that year runs at startup rates and `w1` at
    // full rates, so the year gets a blended cost and a blended revenue. Whole
    // years of startup before it run entirely at startup rates. Simplifying
    // this to "round to the nearest year" would move a whole year of sales
    // across the discounting, which at a 15% IRR is not a rounding error.
    const startupTime = this.startupMonths / 12;
    const w0 = startupTime % 1;
    const w1 = 1 - w0;
    const endStart = start + Math.trunc(startupTime);
    if (endStart >= length) {
      throw new Error('startup period extends past the end of the venture');
    }
    C[endStart] =
      w0 * this.startupVOCfrac * VOC +
      w1 * VOC +
      w0 * this.startupFOCfrac * FOC +
      w1 * FOC;
    for (let i = start; i < endStart; i++) {
      C[i] = this.startupVOCfrac * VOC + this.startupFOCfrac * FOC;
    }
    S[endStart] = w0 * this.startupSalesfrac * sales + w1 * sales;
    for (let i = start; i < endStart; i++) S[i] = this.startupSalesfrac * sales;
    for (let i = endStart + 1; i < length; i++) {
      C[i] = VOC + FOC;
      S[i] = sales;
    }

    // Capital is spent over the construction years and depreciated from the
    // first operating year. The depreciable base is what the schedule actually
    // laid out, not TDC — a construction schedule that does not sum to one
    // depreciates only what it spent, which is upstream's behaviour and worth
    // preserving because it makes a malformed schedule visible in the table
    // rather than silently normalised away.
    for (let i = 0; i < start; i++) {
      C_D[i] = TDC0 * this.constructionSchedule[i];
      C_FC[i] = FCI * this.constructionSchedule[i];
    }
    const depreciableBase = C_D.slice(0, start).reduce((t, x) => t + x, 0);
    const depreciationArray = this.getDepreciationArray();
    if (depreciationArray.length > years) {
      throw new Error('depreciation schedule is longer than plant lifetime');
    }
    for (let i = 0; i < depreciationArray.length; i++) {
      D[start + i] = depreciableBase * depreciationArray[i];
    }

    // Working capital is put up in the last year of construction and released
    // when the plant closes; it is a loan to the project from its owner, not a
    // cost, which is why it comes back at the end undepreciated.
    C_WC[start - 1] = WC;
    C_WC[length - 1] += -WC;

    let taxable: number[];
    let nontaxable: number[];
    if (this.financeInterest) {
      const interest = this.financeInterest;
      const end = start + this.financeYears;
      for (let i = 0; i < start; i++) L[i] = this.financeFraction * C_FC[i];
      const initialPrincipal = L.slice(0, start).reduce((t, x) => t + x, 0);
      const payment = solvePayment(initialPrincipal, interest, this.financeYears);
      for (let i = start; i < Math.min(end, length); i++) LP[i] = payment;

      let principal = 0;
      for (let i = 0; i < Math.min(end, length); i++) {
        // Interest during construction is paid as it accrues rather than rolled
        // into the principal, which is upstream's default.
        const li = i < start ? 0 : (principal + L[i]) * interest;
        LI[i] = li;
        principal = principal - LP[i] + li + L[i];
        LPl[i] = principal;
      }
      for (let i = 0; i < start; i++) LI[i] = L[i] * interest;

      taxable = C.map((_, i) => S[i] - C[i] - D[i] - LP[i]);
      nontaxable = C.map((_, i) => D[i] + L[i] - C_FC[i] - C_WC[i]);
      // Interest paid during construction is real money out of the door in
      // years that have no earnings to deduct it from.
      for (let i = 0; i < start; i++) nontaxable[i] -= LI[i];
    } else {
      taxable = C.map((_, i) => S[i] - C[i] - D[i]);
      nontaxable = C.map((_, i) => D[i] - C_FC[i] - C_WC[i]);
    }

    const TE = taxableEarningsWithForwardedLosses(taxable);
    const FL = zeros(length);
    let cumulativeLoss = 0;
    for (let i = 0; i < length - 1; i++) {
      cumulativeLoss += taxable[i] - TE[i];
      FL[i + 1] = cumulativeLoss;
    }

    const rows: CashflowRow[] = [];
    let cumulativeNPV = 0;
    for (let i = 0; i < length; i++) {
      // Incentives are a zero array here; the term is kept so the expression
      // still reads as upstream's.
      const incentives = 0;
      const tax = this.incomeTax * Math.max(TE[i], 0);
      const netEarnings = taxable[i] + incentives - tax;
      const cashFlow = netEarnings + nontaxable[i];
      // Years before operation discount up, not down: the duration array runs
      // from -(start - 1) to `years`, so year zero is the last construction
      // year and capital spent before it is worth more than face value.
      const t = -start + 1 + i;
      const discountFactor = 1 / (1 + this.IRR) ** t;
      const NPV = cashFlow * discountFactor;
      cumulativeNPV += NPV;
      rows.push({
        year: this.duration[0] - start + i,
        depreciableCapital: C_D[i],
        fixedCapitalInvestment: C_FC[i],
        workingCapital: C_WC[i],
        depreciation: D[i],
        loan: L[i],
        loanInterestPayment: LI[i],
        loanPayment: LP[i],
        loanPrincipal: LPl[i],
        annualOperatingCost: C[i],
        sales: S[i],
        tax,
        taxedEarnings: TE[i],
        forwardedLosses: FL[i],
        netEarnings,
        cashFlow,
        discountFactor,
        NPV,
        cumulativeNPV,
      });
    }
    return rows;
  }

  /**
   * The real IRR at which NPV is zero, fraction.
   *
   * Upstream opens with an unbracketed secant from the previous IRR and falls
   * back to bracketed interpolation only when bounds are supplied. Bracketing
   * from the start is used here instead: NPV is monotonically decreasing in the
   * discount rate for a conventional cashflow, so a bracket that contains the
   * root cannot be lost, whereas the secant can walk to a discount rate below
   * -100% where the discount factors are not defined.
   */
  solveIRR(): number {
    const saved = this.IRR;
    const npvAt = (irr: number): number => {
      this.IRR = irr;
      return this.NPV;
    };
    try {
      // -90% to +1000%: wide enough for any project worth reporting, and both
      // ends are finite.
      const lo = -0.9;
      const hi = 10;
      const fLo = npvAt(lo);
      const fHi = npvAt(hi);
      if (fLo > 0 === fHi > 0) {
        throw new Error(
          `NPV does not cross zero between ${lo * 100}% and ${hi * 100}% IRR ` +
            `(NPV ${fLo.toPrecision(4)} and ${fHi.toPrecision(4)} USD); the ` +
            'project either never pays back or has no finite break-even rate',
        );
      }
      return solveBrentq(npvAt, lo, hi, { xtol: 1e-8 });
    } finally {
      this.IRR = saved;
    }
  }

  /**
   * The price of a product stream at which NPV is zero, USD/kg — the MPSP.
   *
   * Upstream solves this analytically: NPV is affine in additional sales once
   * the tax is linearised, so `solve_sales` finds the extra revenue needed and
   * divides by the stream's price-to-cost factor. That analytic route is not
   * taken here. It is exact only while the tax term stays linear, and the
   * loss-forwarding above makes it piecewise linear — upstream copes by
   * bracketing and re-solving when the secant fails, which is a numeric solve
   * with an analytic first guess. Bracketing on the price directly does the
   * same work in a form that can be checked by reading one function, and the
   * two agree to solver tolerance.
   */
  solvePrice(productStreamID: string): number {
    const stream: Stream | undefined = this.system.products.find(
      (p) => p.ID === productStreamID,
    );
    if (!stream) {
      throw new Error(
        `no product stream '${productStreamID}' in system ${this.system.ID}`,
      );
    }
    if (massFlow(stream) <= 0) {
      throw new Error(`cannot solve the price of empty stream '${productStreamID}'`);
    }

    const saved = stream.price;
    const npvAt = (price: number): number => {
      stream.price = price;
      return this.NPV;
    };
    try {
      let lo = 1e-6;
      let hi = 1e6;
      let fLo = npvAt(lo);
      let fHi = npvAt(hi);
      // NPV rises with the selling price, so a bracket that fails to straddle
      // zero fails on one known side and can be widened towards it. Giving away
      // the product (or paying to dispose of it) is a legitimate answer for a
      // co-product, hence the negative lower bound.
      for (let i = 0; i < 12 && fLo > 0 === fHi > 0; i++) {
        if (fLo > 0) {
          lo = lo > 0 ? -1 : lo * 10;
          fLo = npvAt(lo);
        } else {
          hi *= 10;
          fHi = npvAt(hi);
        }
      }
      if (fLo > 0 === fHi > 0) {
        throw new Error(
          `no break-even price for '${productStreamID}' between ${lo} and ${hi} ` +
            'USD/kg; NPV never crosses zero over that range',
        );
      }
      return solveBrentq(npvAt, lo, hi, { xtol: 1e-10 });
    } finally {
      stream.price = saved;
    }
  }
}
