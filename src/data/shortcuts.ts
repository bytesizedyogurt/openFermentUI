// Keyboard shortcut map (OF-DES-001 Appendix A, OF-BLD-006 §5 as revised).
//
// The rail chord keys are initials of the names a user now reads, so the chord
// is learnable from the rail itself rather than from this sheet: o for
// Postdoc, b for BioRepo, i for Intake, f for Proforma, n for Primer. Two are
// not initials and cannot be — 'p' went to Protocols before Postdoc existed
// and moving it would break a reflex for no gain, and Primer's 'p' is taken,
// so it keeps 'n'. Nothing collides, which is the actual requirement.
export const SHORTCUTS: { context: string; keys: { key: string; does: string }[] }[] = [
  {
    context: 'Global',
    keys: [
      { key: '⌘K', does: 'Command palette' },
      { key: '/', does: 'Focus search' },
      { key: 'g then h/o/b/i/g/m/p/r/f/n', does: 'Go to rail item' },
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
