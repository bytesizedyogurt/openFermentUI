// Reactions, in the shape bioSTEAM writes them.
//
// Upstream you write `Reaction('Glucose -> 2 Ethanol + 2 CO2', 'Glucose', X=0.9)`
// and the object carries the stoichiometry, the limiting reactant and the
// conversion; calling it on a stream consumes and produces in place. That triple
// — equation, reactant, X — is the thing a process engineer actually argues
// about, so it is worth having in the same form here even though this port has
// no chemicals package behind it.
//
// The difference: upstream balances by molar stoichiometry against a `Chemicals`
// object. There is no molecular weight anywhere in this port, so the yields
// below are mass yields — kg of each product per kg of reactant consumed — and
// the equation string is written out rather than parsed. That is a real loss:
// nothing here can tell you a reaction is unbalanced, which upstream does for
// free. The equation is therefore documentation, and `yields` is the arithmetic.
import type { Stream } from './types';

export interface Reaction {
  /** As it would be written upstream, for the reader rather than the parser. */
  equation: string;
  /** The component consumed, keyed into `Stream.flow`. */
  reactant: string;
  /** Conversion of the reactant, 0–1. Upstream's `X`. */
  X: number;
  /** kg of each product per kg of reactant consumed. */
  yields: Record<string, number>;
}

/**
 * Run the reaction on a stream, returning a new one.
 *
 * Conversion applies to whatever reactant is present; a stream carrying none of
 * it passes through untouched, which is upstream's behaviour too. Mass that the
 * yields do not account for leaves as the balance component — carbon dioxide for
 * an aerobic culture — so the total is conserved and a reader can see where it
 * went instead of watching mass quietly disappear.
 */
export function applyReaction(
  feed: Stream,
  rxn: Reaction,
  balanceComponent = 'co2',
): Stream {
  const flow = { ...feed.flow };
  const available = flow[rxn.reactant] ?? 0;
  if (available <= 0) return { ...feed, flow };
  const consumed = available * Math.min(1, Math.max(0, rxn.X));
  flow[rxn.reactant] = available - consumed;
  let accounted = 0;
  for (const product in rxn.yields) {
    const made = consumed * rxn.yields[product];
    flow[product] = (flow[product] ?? 0) + made;
    accounted += made;
  }
  const balance = consumed - accounted;
  if (Math.abs(balance) > 1e-12) {
    flow[balanceComponent] = (flow[balanceComponent] ?? 0) + balance;
  }
  return { ...feed, flow };
}

/** Write the mass stoichiometry out the way upstream would print it. */
export function formatReaction(rxn: Reaction, balanceComponent = 'co2'): string {
  const parts: string[] = [];
  let accounted = 0;
  for (const p in rxn.yields) {
    parts.push(`${rxn.yields[p].toPrecision(3)} ${p}`);
    accounted += rxn.yields[p];
  }
  const balance = 1 - accounted;
  if (balance > 1e-6) parts.push(`${balance.toPrecision(3)} ${balanceComponent}`);
  return `${rxn.reactant} -> ${parts.join(' + ')}`;
}
