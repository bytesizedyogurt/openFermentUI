// Sizing a train of batch reactors: how large each vessel is, how long a cycle
// takes, and how many vessels it takes to swallow a continuous feed.
//
// Ported from BioSTEAM v2.53.11 `units/design_tools/batch.py` (UIUC/NCSA
// licence; see NOTICE.md). That module holds `size_batch` and nothing else, so
// the only thing left behind is the docstring's LaTeX, restated below as prose.
//
// Units of measure are the caller's, exactly as upstream: they need only be
// mutually consistent, so the feed rate must use the same volume unit as
// `V_max` and the same time unit as the two residence times. openFerment calls
// this with m³/hr, hr and m³ throughout.
import { wegstein } from './solvers';

/** The four numbers upstream returns from `size_batch`, in the caller's units. */
export interface BatchSizing {
  /** Actual volume of one vessel, i.e. working volume grossed up by `V_wf`. */
  reactorVolume: number;
  /** Reaction plus cleaning plus loading — one full cycle of one vessel. */
  batchTime: number;
  /** Time one vessel spends filling. */
  loadingTime: number;
  /** Vessel count, always a whole number. */
  nReactors: number;
}

const ARGUMENT_ERROR = 'must pass either `N_reactors` or `V_max`';

/**
 * Solve for batch reactor volume, cycle time and loading time.
 *
 * With no downtime the vessels between them must hold everything that arrives
 * over a full cycle, so the total volume is
 *
 *   V_T = F_vol · (τ_reaction + τ_cleaning + τ_loading),
 *
 * which conservatively credits no reaction at all to the time a vessel spends
 * filling. Rounded up to whole vessels against the largest working volume one
 * vessel offers, that gives N = ceil(V_T / (V_max · V_wf)).
 *
 * When the caller does not state a loading time, upstream assumes there is no
 * upstream storage and one vessel is therefore always filling, so its loading
 * time is its own working volume divided by the feed rate. Substituting that
 * back and solving for V_T removes τ_loading from the right-hand side:
 *
 *   V_T = F_vol · (τ_reaction + τ_cleaning) / (1 − 1/N).
 *
 * Exactly one of `V_max` and `N_reactors` must be supplied — the first sizes a
 * vessel count from a vessel size, the second does the reverse, and giving both
 * would let the two disagree — so supplying both or neither throws.
 *
 * Doctests, with F_vol = 1000 m³/hr, τ_reaction = 30 hr, τ_cleaning = 3 hr and
 * V_wf = 0.95:
 *
 *   {V_max: 1e3, loading_time: 0}
 *     -> {reactorVolume: 992.4812030075188, batchTime: 33,
 *         loadingTime: 0, nReactors: 35}
 *   {N_reactors: 35, loading_time: 0}   -> the same
 *   {V_max: 1000}
 *     -> {reactorVolume: 992.4812030075188, batchTime: 33.94285714285714,
 *         loadingTime: 0.9428571428571428, nReactors: 36}
 *   {N_reactors: 36}                    -> the same
 *
 * A reader checking those against upstream's docstring should know that its
 * first two examples print 992.48, rounded: bioSTEAM runs its doctests with
 * pytest's NUMBER flag, which compares only as many digits as are written out.
 * Its third example is a genuine disagreement, and upstream's code is taken as
 * the authority here over upstream's prose. That example reports 992.69 m³ and
 * a 0.95 hr loading time, which are the values computed *before* the vessel
 * count is rounded up; the code then re-derives both from the integer count and
 * overwrites them, so it in fact returns the fourth example's numbers. The
 * re-derivation is the behaviour worth keeping — rounding 35.74 vessels up to
 * 36 buys slack, and the volume and cycle time reported should be the ones the
 * 36 vessels actually have, not the ones the fractional vessel count implied.
 */
export function sizeBatch(
  F_vol: number,
  tau_reaction: number,
  tau_cleaning: number,
  V_wf: number,
  opts: { V_max?: number; N_reactors?: number; loading_time?: number },
): BatchSizing {
  const { V_max, N_reactors: N_given, loading_time } = opts;

  // Resolving the vessel count first is what lets the sizing below narrow
  // `V_max` without an assertion; upstream instead validates the pair up front
  // and then re-tests `N_reactors` inside each branch, to the same effect.
  let N_reactors: number;
  if (N_given === undefined) {
    if (V_max === undefined) throw new Error(ARGUMENT_ERROR);
    const V_working_max = V_max * V_wf;
    if (loading_time === undefined) {
      // Neither the vessel count nor the loading time is known, and each fixes
      // the other, so the loading time is found as a fixed point over a
      // fractional vessel count before anything is rounded.
      const tau_loading = wegstein((tau) => {
        // Below two vessels there is no rotation to speak of and the 1 − 1/N
        // term goes to zero, so the iteration is floored where the model still
        // means something rather than allowed to run off to infinite volume.
        const N = Math.max(
          (F_vol * (tau_reaction + tau_cleaning + tau)) / V_working_max,
          2,
        );
        const V_T = (F_vol * (tau_reaction + tau_cleaning)) / (1 - 1 / N);
        return V_T / N / F_vol;
      }, 0.5);
      N_reactors = Math.max(
        Math.ceil(
          (F_vol * (tau_reaction + tau_cleaning + tau_loading)) / V_working_max,
        ),
        2,
      );
    } else {
      // A stated loading time closes the volume balance on its own, so the
      // count follows directly and upstream applies no floor here.
      N_reactors = Math.ceil(
        (F_vol * (tau_reaction + tau_cleaning + loading_time)) / V_working_max,
      );
    }
  } else {
    if (V_max !== undefined) throw new Error(ARGUMENT_ERROR);
    N_reactors = N_given;
  }

  let V_i: number;
  let tau_loading: number;
  if (loading_time === undefined) {
    // Total volume of all reactors, assuming no downtime.
    const V_T = (F_vol * (tau_reaction + tau_cleaning)) / (1 - 1 / N_reactors);
    V_i = V_T / N_reactors;
    tau_loading = V_i / F_vol;
  } else {
    tau_loading = loading_time;
    const V_T = F_vol * (tau_reaction + tau_cleaning + tau_loading);
    V_i = V_T / N_reactors;
  }

  return {
    // Dividing out the working fraction turns working volume into the vessel
    // that has to be bought, which is what every downstream cost correlation
    // wants.
    reactorVolume: V_i / V_wf,
    batchTime: tau_reaction + tau_cleaning + tau_loading,
    loadingTime: tau_loading,
    nReactors: N_reactors,
  };
}
