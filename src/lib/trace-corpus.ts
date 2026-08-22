// Resolving a β-casein corpus record into its address.
//
// Kept apart from the demo pool's resolver on purpose. Both produce the same
// `Trace` shape, and nothing imports both — a single dispatcher that took an id
// and chose a pool by its prefix would be the first module in the build to hold
// an ExtractionRecord and an Accession at once.
//
// The four steps mirror the Bench band exactly, because they are the same four
// steps. If the vocabulary here ever drifts from the vocabulary there, the
// gesture stops teaching what the front door taught.
import type { ExtractionRecord, Paper, Protocol, Scenario } from '@/data/types';
import { ONTOLOGY_BY_ID } from '@/data/ontology';
import { dependents } from '@/engine/stale';
import { provenanceOf } from '@/store';
import type { ProvKind } from '@/components/Provenance';
import type { Trace } from '@/components/Trace';

export interface CorpusTraceSource {
  records: ExtractionRecord[];
  papers: Paper[];
  protocols: Protocol[];
  scenarios: Scenario[];
}

/**
 * The chain behind one extraction record, or null when the id resolves to
 * nothing — a deep link from a session that has since reset, most often.
 * Returning null rather than a trace with holes is the same rule the Bench
 * band follows.
 */
export function corpusTrace(recordId: string, src: CorpusTraceSource): Trace | null {
  const record = src.records.find((r) => r.id === recordId);
  if (!record) return null;
  const paper = src.papers.find((p) => p.id === record.paperId);
  const prov = provenanceOf(record) as ProvKind;
  const field = ONTOLOGY_BY_ID[record.field];
  const deps = dependents(recordId, { protocols: src.protocols, scenarios: src.scenarios });

  // ── 01 · the source ──────────────────────────────────────────────────────
  const source: Trace['steps'][number] = paper
    ? {
        label: 'The source',
        part: 'Intake',
        to: `/trawl/sources/${paper.id}`,
        headline: paper.title,
        // `year: 0` and VENUE_UNSTATED are the corpus's sentinels for "not
        // known". They are shown as gaps rather than hidden, because hiding
        // them is how a catalogue starts to look more complete than it is.
        body: [
          paper.authors.join(', ') || 'authors unstated',
          paper.venue || 'venue unstated',
          paper.year ? String(paper.year) : 'year unstated',
        ].join(' · '),
        prov,
      }
    : {
        label: 'The source',
        part: 'Intake',
        headline: record.paperId,
        body: 'Not in this session’s corpus.',
        prov,
      };

  // ── 02 · the record ──────────────────────────────────────────────────────
  const rangeNote =
    record.range && record.range.low !== record.range.high
      ? ` The source states ${record.range.low}–${record.range.high}; this is the midpoint, and the range is kept on the record.`
      : '';
  const step2: Trace['steps'][number] = {
    label: 'The record',
    part: 'Ledger',
    to: `/trawl/sources/${record.paperId}?span=${record.id}`,
    headline: `${record.value} ${record.unit}`.trim(),
    body: `${field?.name ?? record.field} · ${record.id}.${rangeNote}`,
    prov,
  };

  // ── 03 · the check that has not happened ─────────────────────────────────
  //
  // The only step that can be absent, and the only one that must never be
  // silently dropped when it is.
  const verified = record.status === 'verified';
  const step3: Trace['steps'][number] = verified
    ? {
        label: 'The check',
        part: 'Audit',
        to: '/assay',
        headline: 'Verified against its source',
        body: 'A reader compared this value with the span it was read from.',
        prov,
      }
    : {
        label: 'The missing check',
        part: 'Audit',
        to: '/assay',
        missing: true,
        headline: 'Nobody has checked this against its source.',
        body: 'No extractor has been run against this corpus either, so there is no precision, recall or F1 to show.',
      };

  // ── 04 · what already uses it ────────────────────────────────────────────
  const used = [...deps.protocols, ...deps.scenarios];
  const step4: Trace['steps'][number] = used.length
    ? {
        label: 'What uses it',
        part: deps.scenarios.length ? 'fermOS' : 'Runbook',
        to: deps.scenarios.length
          ? `/fermos/s/${deps.scenarios[0]}`
          : `/runbook/${deps.protocols[0]}`,
        headline: used.join(' · '),
        body: 'Correct this record and each of these is marked stale by propagation, not by anybody remembering to.',
        prov,
      }
    : {
        label: 'What uses it',
        part: 'fermOS',
        headline: 'Nothing yet',
        body: 'Catalogued only. Most of the corpus is — the executable layer is narrow, and that gap is the work.',
        prov,
      };

  return { id: record.id, steps: [source, step2, step3, step4] };
}
