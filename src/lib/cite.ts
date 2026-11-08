// How a document is named where room is short: a short title, a short cite
// (the first author's surname and the year), and the author line. A
// document's id stays in a title attribute, where a person who needs it
// finds it, and the words a person reads are the document's own.

interface Named {
  id: string;
  title: string;
  authors: string[];
  year: number | null;
}

/** A title cut to `max` characters, an ellipsis ending a cut one. */
export function shortTitle(t: string, max = 64): string {
  return t.length > max ? `${t.slice(0, max - 1).trimEnd()}…` : t;
}

/** The surname of an author as a document lists one: "Last, First" or "First Last". */
function surname(author: string): string {
  const a = author.trim();
  if (a.includes(',')) return a.split(',')[0].trim();
  const parts = a.split(/\s+/);
  return parts[parts.length - 1] ?? a;
}

/** A short cite: the first author's surname, "et al." for more than two, and the year; the short title for a document with no author. */
export function shortCite(paper: Named, max = 24): string {
  const year = paper.year != null ? ` ${paper.year}` : '';
  if (paper.authors.length === 0) return `${shortTitle(paper.title, max)}${year}`;
  const first = surname(paper.authors[0]);
  const rest = paper.authors.length === 2 ? ` & ${surname(paper.authors[1])}` : paper.authors.length > 2 ? ' et al.' : '';
  return `${first}${rest}${year}`;
}

/** The authors as one line, each author kept whole ("Last, First"), joined with semicolons. */
export function authorsLine(authors: string[], max = 3): string {
  const shown = authors.slice(0, max).join('; ');
  return authors.length > max ? `${shown} et al.` : shown;
}

/** The last characters of a long id, enough to tell two apart on one screen; the whole id goes in a title. */
export function idTail(id: string, n = 8): string {
  return id.length > n + 1 ? `…${id.slice(-n)}` : id;
}
