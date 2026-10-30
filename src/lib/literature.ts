// The browser's side of the literature layer (ADR-002): a document collected
// into the open project's corpus in Sci RAG Kit, by its identifier, as a file
// or as pasted text, and the list of what the project holds.
//
// Not collected is an answer, not an error: the service returns the outcome
// with `status: 'failed'` and the reason, and the Intake card shows it as it
// stands. Only a service that cannot be reached throws (IntakeDown).
import type { CollectOutcome, CollectRequest, LiteratureDocument, PasteRequest, SearchResponse } from '@/data/types';
import { IntakeDown, explain } from './intake';
import { parseEvents } from './postdoc';
import { apiFetch } from './project';

async function asked<T>(input: string, init: RequestInit = {}, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await apiFetch(input, { ...init, signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new IntakeDown('Intake service not running.');
  }
  if (!response.ok) await explain(response, signal);
  return (await response.json()) as T;
}

const json = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

/** A paper, a report or a strain entry by its identifier: a PMCID, a DOI, PMID:…, OSTI:…, or an osti.gov or yeastgenome.org address. */
export function collect(request: CollectRequest, signal?: AbortSignal): Promise<CollectOutcome> {
  return asked<CollectOutcome>('/api/intake/collect', json(request), signal);
}

/** A file: PDF, JATS XML, Markdown, HTML or plain text. */
export function uploadDocument(
  file: File,
  fields: { by: string; title?: string; licenceClass?: string; licence?: string; reason?: string },
  signal?: AbortSignal,
): Promise<CollectOutcome> {
  const form = new FormData();
  form.append('file', file, file.name);
  for (const [name, value] of Object.entries(fields)) if (value) form.append(name, value);
  return asked<CollectOutcome>('/api/intake/upload', { method: 'POST', body: form }, signal);
}

/** Text pasted under its title. */
export function pasteDocument(request: PasteRequest, signal?: AbortSignal): Promise<CollectOutcome> {
  return asked<CollectOutcome>('/api/intake/paste', json(request), signal);
}

/** Every document the open project holds, newest first. */
export function projectDocuments(signal?: AbortSignal): Promise<LiteratureDocument[]> {
  return asked<LiteratureDocument[]>('/api/literature/documents', {}, signal);
}

/** The kit's licence classes, as a person may choose one for what they add. */
export const LICENCE_CLASSES: { value: string; label: string }[] = [
  { value: 'unknown', label: 'Not stated' },
  { value: 'public', label: 'Public domain' },
  { value: 'open_commercial', label: 'Open, commercial use allowed (CC BY, CC BY-SA)' },
  { value: 'open_noncommercial', label: 'Open, non-commercial only (CC BY-NC…)' },
  { value: 'restricted', label: 'Held, not to be shared (paywalled, private)' },
];

/** What an outcome's status means, in the reader's words. */
export function outcomeWords(outcome: CollectOutcome): string {
  switch (outcome.status) {
    case 'ingested':
      return `stored in ${outcome.chunks} passage${outcome.chunks === 1 ? '' : 's'}`;
    case 'linked':
      return 'already in the instance; this project holds it now too';
    case 'held':
      return 'this project holds it already';
    default:
      return outcome.reason ?? 'not collected';
  }
}

/** The passages of the open project's documents that best answer `q`, best first. */
export function searchLiterature(q: string, opts: { topK?: number; signal?: AbortSignal } = {}): Promise<SearchResponse> {
  const params = new URLSearchParams({ q, topK: String(opts.topK ?? 10) });
  return asked<SearchResponse>(`/api/literature/search?${params}`, {}, opts.signal);
}

/** One source of a cited answer, as the kit reports it. */
export interface AnswerSource {
  index: number;
  title: string;
  citation: string | null;
  license_class: string;
  document_id: string | null;
  passage_id: string | null;
  section_path: string | null;
  cited: boolean;
}

/**
 * A cited answer over the open project's documents, streamed: `onText` with
 * each piece of the answer as it is written; the promise resolves with the
 * sources, each saying whether the answer cited it. An `error` event throws
 * IntakeDown with the service's words, a missing key among them.
 */
export async function answerFromLiterature(
  question: string,
  onText: (text: string) => void,
  signal?: AbortSignal,
): Promise<AnswerSource[]> {
  let response: Response;
  try {
    response = await apiFetch('/api/literature/answer', { ...json({ question }), signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new IntakeDown('Intake service not running.');
  }
  if (!response.ok) await explain(response, signal);
  if (!response.body) throw new IntakeDown('The service answered with no stream.');
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let sources: AnswerSource[] = [];
  for (;;) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const parsed = parseEvents(done ? `${buffer}\n\n` : buffer);
    buffer = parsed.rest;
    for (const e of parsed.events) {
      const data = e.data as { text?: string; citations?: AnswerSource[]; message?: string };
      if (e.event === 'delta' && data.text) onText(data.text);
      else if (e.event === 'citations') sources = data.citations ?? [];
      else if (e.event === 'error') throw new IntakeDown(String(data.message ?? 'The answer failed.'), 'The service log says why.');
      else if (e.event === 'done') return sources;
    }
    if (done) return sources;
  }
}
