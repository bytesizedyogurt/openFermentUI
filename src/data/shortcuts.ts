// Keyboard shortcut map (OF-DES-001 Appendix A).
export const SHORTCUTS: { context: string; keys: { key: string; does: string }[] }[] = [
  {
    context: 'Global',
    keys: [
      { key: '⌘K', does: 'Command palette' },
      { key: '/', does: 'Focus search' },
      { key: 'g then a rail key', does: 'Go to rail item — h t d v o s c a p b y n for the corpus, w r f for the demo suite' },
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
    context: 'Review queue',
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
    context: 'Run Mode',
    keys: [
      { key: 'Space', does: 'Mark step complete' },
      { key: 't', does: 'Start / stop timer' },
      { key: 'n', does: 'Add deviation note' },
      { key: '← →', does: 'Previous / next step' },
    ],
  },
  {
    context: 'Ask',
    keys: [
      { key: 'Enter', does: 'Send' },
      { key: '⇧Enter', does: 'Newline' },
      { key: '⌘I', does: 'Toggle Inspector' },
      { key: '⌘⇧P', does: 'Pin sources from last answer' },
    ],
  },
  {
    context: 'Simulate',
    keys: [
      { key: 'p', does: 'Pin scenario to compare' },
      { key: 'c', does: 'Open compare' },
      { key: '[ ]', does: 'Nudge the active slider' },
    ],
  },
];
