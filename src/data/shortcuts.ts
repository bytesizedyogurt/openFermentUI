// Keyboard shortcut map (OF-DES-001 Appendix A, OF-BLD-008 §5).
//
// The rail chord keys are initials of the names a user reads, so the chord is
// learnable from the rail itself rather than from this sheet: i for Intake,
// b for BioRepo, f for fermOS, d for Dominion, g for Guild. Three cannot be
// initials and are not: Postdoc takes 'o' because 'p' reads as a word nobody
// types; Proforma takes 'c' for cost; Primer keeps 'n'. Twelve keys, all
// distinct, which is the actual requirement.
export const SHORTCUTS: { context: string; keys: { key: string; does: string }[] }[] = [
  {
    context: 'Global',
    keys: [
      { key: '⌘K', does: 'Command palette' },
      { key: '/', does: 'Focus search' },
      { key: 'g then h/i/b/o/e/f/u/c/r/d/n/g', does: 'Go to one of the twelve' },
      { key: '⇧D', does: 'Toggle density' },
      { key: '⇧T', does: 'Toggle theme' },
      { key: '?', does: 'This shortcut sheet' },
    ],
  },
  {
    context: 'Tables',
    keys: [
      { key: '↑ ↓', does: 'Move between rows' },
      { key: 'Enter', does: 'Open focused row' },
      { key: 'e', does: 'Export current filtered view' },
    ],
  },
  {
    context: 'Guild — the review queue',
    keys: [
      { key: 'a', does: 'Accept' },
      { key: 'r', does: 'Reject (opens reason picker)' },
      { key: 'e', does: 'Edit value' },
      { key: 's', does: 'Skip' },
      { key: 'g', does: 'Flag for gold set' },
      { key: 'u', does: 'Undo last decision' },
      { key: 'j / k', does: 'Next / previous record' },
    ],
  },
  {
    context: 'Deposition',
    keys: [
      { key: 'Space', does: 'Mark step complete' },
      { key: 't', does: 'Start / stop timer' },
      { key: 'n', does: 'Add deviation note' },
      { key: '← →', does: 'Previous / next step' },
    ],
  },
  {
    context: 'Postdoc',
    keys: [
      { key: 'Enter', does: 'Send' },
      { key: '⇧Enter', does: 'Newline' },
      { key: '⌘I', does: 'Toggle Inspector' },
      { key: '⌘⇧P', does: 'Pin sources from last answer' },
    ],
  },
  {
    context: 'Proforma',
    keys: [
      { key: 'p', does: 'Pin scenario to compare' },
      { key: 'c', does: 'Open compare' },
      { key: '[ ]', does: 'Nudge the active slider' },
    ],
  },
];
