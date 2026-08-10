// CSV export. Every export carries the demo disclosure header so a file can't
// launder synthetic data into a real analysis (OF-DES-001 §20.7).
import { useStore } from '@/store';

/**
 * Export disclosure (OF-DES-001 §20.7, revised by OF-COR-001 §20).
 *
 * The corpus is real, so a blanket "this is fictional" header would now be a
 * lie in the other direction. What a downstream reader actually needs to know
 * is which rows carry what weight — hence the per-class note.
 */
export const DISCLOSURE = [
  '# openFerment export — corpus OF-COR-001 v1.0',
  '# Literature entries, authors, venues and DOIs are REAL and citable.',
  '# Provenance classes in this file:',
  '#   gold              hand-curated reference annotation',
  '#   verified          checked against the source document',
  '#   curated           transcribed from the curation document, NOT yet checked',
  '#                     against the source PDF — verify before citing',
  '#   unverified        extractor output, not reviewed',
  '#   industry-estimate non-peer-reviewed market/vendor figure — not evidence',
  '#   demo              modeled, not measured (simulation outputs)',
  '# Simulation economics are illustrative models, not validated.',
];

function esc(v: unknown): string {
  const s = v === null || v === undefined ? '' : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCSV(headers: string[], rows: unknown[][]): string {
  return [...DISCLOSURE, headers.map(esc).join(','), ...rows.map((r) => r.map(esc).join(','))].join(
    '\n',
  );
}

export function download(filename: string, content: string, mime = 'text/csv') {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function exportCSV(filename: string, headers: string[], rows: unknown[][]) {
  download(filename, toCSV(headers, rows));
  const st = useStore.getState();
  st.logExport(filename, rows.length);
  st.toast({ text: `Exported ${filename} — ${rows.length} rows`, kind: 'success' });
}

export function exportText(filename: string, content: string) {
  download(filename, content, 'text/plain');
  const st = useStore.getState();
  st.logExport(filename, content.split('\n').length);
  st.toast({ text: `Exported ${filename}`, kind: 'success' });
}
