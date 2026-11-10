// Row 36: the browser's provenanceOf on the decided record the overlay serves (verified, label gold, no gold value).
// Run from the repository root: node_modules/.bin/tsx bughunt/notes/P/scripts/row36_provenanceOf.ts
(globalThis as any).localStorage = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
(globalThis as any).window = globalThis;
const { provenanceOf } = await import('../../../../src/store');
const decided = { id: 'r', status: 'verified', provenance: 'gold', gold: null, reviewer: 'Ada Moreno' } as any;
console.log('browser provenanceOf(verified, label gold, gold null) =', provenanceOf(decided));
console.log('browser provenanceOf(verified, label gold, gold {value}) =', provenanceOf({ ...decided, gold: { value: 1, unit: 'd' } }));
