// CSV export. Every export carries the disclosure header so a file can't
// launder a modeled or unchecked value into a real analysis (OF-DES-001 §20.7).
import { useStore } from '@/store';

/**
 * Export disclosure (OF-DES-001 §20.7).
 *
 * The literature is real, so a blanket "this is fictional" header would be a
 * lie. What a downstream reader needs to know is which rows carry what
 * weight, hence the per-class note.
 */
export const DISCLOSURE = [
  '# openFerment export',
  "# Literature entries, authors, venues and DOIs are REAL and citable: the documents the project holds.",
  '# Provenance classes in this file:',
  '#   gold              a value a reviewer typed against the paper\'s sentence',
  '#   verified          checked against the source document by a named reviewer',
  '#   curated           written by hand, as the vocabulary and the fields are',
  '#   unverified        the extractor\'s reading, not reviewed — verify before citing',
  '#   industry-estimate non-peer-reviewed market/vendor figure — not evidence',
  '#   assumed           rests on an assumption or an estimate, not measured',
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
  downloadBlob(filename, new Blob([content], { type: `${mime};charset=utf-8` }));
}

/** A file the service answered, handed to the person as it came. */
export function downloadBlob(filename: string, blob: Blob) {
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
