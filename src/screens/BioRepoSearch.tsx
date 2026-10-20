// BioRepo → Search (OF-BLD-014 §4.4): the papers' own words, searched.
//
// A question goes to the service, which searches the passage index on the
// chosen lane (or the one picked here) and returns passages: each with its
// paper, its section, the sentence the grading reader chose when a rerank
// lane ran, and where each lane ranked it. Every word shown in a passage is
// the paper's; one click opens the reader at that sentence. With the service
// down this says so; nothing stands in for a result (E.2).
//
// OF-BLD-016 §2.2: a passage from a paper in an archived program is not shown
// while archived programs are hidden (the default); the result line says how
// many were held back and where the switch is.
import { useEffect, useState, type FormEvent } from 'react';
import { Search as SearchIcon } from 'lucide-react';
import type { PassageHit, RagSearchResponse, RagStatus } from '@/data/types';
import { RagDown, RagRefused, quoteOf, ragSearch, ragStatus, readerHref } from '@/lib/rag';
import { PROGRAMS, PROGRAMS_SETTINGS_PATH } from '@/data/programs';
import { href } from '@/router';
import { archivedProgramOf, useProgramFilter, useStore } from '@/store';
import { Button, Callout, Card, EmptyState, PageHeader } from '@/components/ui';
import { OwnerTabs } from '@/components/OwnerTabs';
import { BIOREPO_TABS } from '@/data/tabs';

const KIND_LABEL: Record<string, string> = { abstract: 'Abstract', prose: 'Text', table: 'Table', figure: 'Figure caption' };

/** The archived programs some hidden papers belong to, named in PROGRAMS order. */
function archivedNames(paperIds: string[]): string {
  const hit = new Set(paperIds.map((id) => archivedProgramOf('paper', id)?.id));
  return PROGRAMS.filter((p) => hit.has(p.id))
    .map((p) => p.name)
    .join(' and ');
}

export default function BioRepoSearch() {
  const papers = useStore((s) => s.papers);
  const shows = useProgramFilter();
  const showArchived = useStore((s) => s.showArchived);
  const [status, setStatus] = useState<RagStatus | null>(null);
  const [down, setDown] = useState<RagDown | null>(null);
  const [question, setQuestion] = useState('');
  const [lane, setLane] = useState<string>('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<RagSearchResponse | null>(null);
  const [refused, setRefused] = useState<string | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    ragStatus(ctrl.signal).then(
      (s) => setStatus(s),
      (e: unknown) => {
        if (!ctrl.signal.aborted) setDown(e instanceof RagDown ? e : new RagDown(String(e)));
      },
    );
    return () => ctrl.abort();
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setRefused(null);
    try {
      setResult(await ragSearch(question.trim(), lane || null));
    } catch (err) {
      setResult(null);
      if (err instanceof RagRefused) setRefused(err.message);
      else if (err instanceof RagDown) setDown(err);
      else setRefused(String(err));
    } finally {
      setBusy(false);
    }
  };

  const titleOf = (paperId: string) => papers.find((p) => p.id === paperId)?.title ?? paperId;

  return (
    <div>
      <PageHeader
        title="Search the papers"
        subtitle="Passages of the fetched papers' own text, found for a question. Every passage shown is the paper's own words; the reader opens at the sentence."
      />
      <OwnerTabs tabs={BIOREPO_TABS} />
      {down && (
        <EmptyState
          icon={<SearchIcon size={28} />}
          title="Search needs the service"
          body={
            <>
              {down.message} The service holds the passage index and searches it. {down.remedy}
            </>
          }
        />
      )}
      {!down && status && status.passages === 0 && (
        <EmptyState
          icon={<SearchIcon size={28} />}
          title="No passages indexed yet"
          body="The index is cut from the papers fetched with full text. Fetch papers in Intake, then run pnpm index:build."
        />
      )}
      {!down && status && status.passages > 0 && (
        <>
          <form onSubmit={submit} className="flex flex-wrap items-end gap-2 mb-2" role="search">
            <label className="flex-1 min-w-[260px]">
              <span className="sr-only">Question</span>
              <input
                aria-label="Question"
                className="input w-full"
                placeholder="e.g. ethanol yield of Saccharomyces cerevisiae on glucose"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
              />
            </label>
            <label className="text-caption text-ink-soft">
              <span className="block mb-0.5">Lane</span>
              <select aria-label="Lane" className="input" value={lane} onChange={(e) => setLane(e.target.value)}>
                <option value="">chosen ({status.chosenLane})</option>
                {status.lanes.map((l) => (
                  <option key={l.name} value={l.name} disabled={!l.available} title={l.why ?? undefined}>
                    {l.name}
                    {l.available ? '' : ' — unavailable'}
                  </option>
                ))}
              </select>
            </label>
            <Button type="submit" variant="primary" disabled={busy || !question.trim()}>
              {busy ? 'Searching…' : 'Search'}
            </Button>
          </form>
          <p className="text-caption text-ink-soft mb-4">
            {/* The service counts its whole index, which holds every program's
                passages; with archived programs hidden a search returns only
                passages from papers that show (OF-BLD-016 §2.3). */}
            The index holds {status.passages.toLocaleString()} passages from {status.papersIndexed} papers, every
            program&rsquo;s{showArchived ? '' : '; a search returns passages only from the papers that show'}.{' '}
            {status.lanes
              .filter((l) => !l.available)
              .map((l) => `${l.name}: ${l.why}`)
              .join(' · ')}
          </p>
          {refused && <Callout kind="warn">{refused}</Callout>}
          {result && (
            <Results
              result={result}
              titleOf={titleOf}
              shows={(h) => shows('paper', h.passage.paperId)}
            />
          )}
        </>
      )}
    </div>
  );
}

function Results({
  result,
  titleOf,
  shows,
}: {
  result: RagSearchResponse;
  titleOf: (id: string) => string;
  shows: (hit: PassageHit) => boolean;
}) {
  const hits = result.hits.filter(shows);
  const hidden = result.hits.filter((h) => !shows(h)).map((h) => h.passage.paperId);
  const hiddenLine =
    hidden.length > 0 ? (
      <>
        {hidden.length} passage{hidden.length === 1 ? '' : 's'} from papers in {archivedNames(hidden)}{' '}
        {hidden.length === 1 ? 'is' : 'are'} not shown, because archived programs are hidden.{' '}
        <a className="text-accent underline underline-offset-2" href={href(PROGRAMS_SETTINGS_PATH)}>
          Settings → Programs
        </a>{' '}
        shows them.
      </>
    ) : null;
  if (hits.length === 0 && hidden.length > 0) {
    return (
      <EmptyState
        icon={<SearchIcon size={28} />}
        title="Every passage found is in an archived program"
        body={hiddenLine}
      />
    );
  }
  if (result.hits.length === 0) {
    return (
      <EmptyState
        icon={<SearchIcon size={28} />}
        title="No passage answers that"
        body="Nothing in the indexed text matched. A question of three or more words whose best match shares one word with it returns nothing rather than a coincidence."
      />
    );
  }
  return (
    <div className="space-y-3" data-testid="search-results">
      <p className="text-caption text-ink-soft">
        {hits.length} passages · lane {result.lane}
        {result.phrasings.length > 0 && ` · also searched, as phrased by a model: ${result.phrasings.join('; ')}`}
        {result.unverifiedSentences > 0 &&
          ` · ${result.unverifiedSentences} sentence${result.unverifiedSentences === 1 ? '' : 's'} the reader returned were not in their passage and were dropped`}
        {result.costUsd > 0 && ` · $${result.costUsd.toFixed(4)}`}
      </p>
      {hiddenLine && (
        <p className="text-caption text-ink-soft" data-testid="archived-hidden">
          {hiddenLine}
        </p>
      )}
      {result.note && <Callout kind="info">{result.note}</Callout>}
      {hits.map((h) => (
        <Hit key={h.passage.id} hit={h} title={titleOf(h.passage.paperId)} />
      ))}
    </div>
  );
}

function Hit({ hit, title }: { hit: PassageHit; title: string }) {
  const p = hit.passage;
  return (
    <Card className="p-3" data-testid="search-hit">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div className="min-w-0">
          <div className="font-medium truncate">
            <span className="font-mono text-caption text-ink-soft mr-2">{p.paperId}</span>
            {title}
          </div>
          <div className="text-caption text-ink-soft">
            {KIND_LABEL[p.kind] ?? p.kind} · {p.heading}
          </div>
        </div>
        <a className="chip text-caption" href={readerHref(hit)} data-testid="open-in-reader">
          Open at this {hit.sentence ? 'sentence' : 'passage'}
        </a>
      </div>
      {hit.sentence && (
        <blockquote className="mt-2 border-l-2 border-accent pl-2 text-body" title="The sentence the grading reader chose; checked word for word against the passage">
          {hit.sentence}
          {hit.grade !== null && <span className="text-caption text-ink-soft ml-2">grade {hit.grade} of 3</span>}
        </blockquote>
      )}
      <p className="mt-2 text-body text-ink-soft whitespace-pre-line line-clamp-6">{p.text}</p>
      <div className="mt-2 flex flex-wrap gap-1 text-caption text-ink-soft" aria-label="Where each lane ranked it">
        {Object.entries(hit.lanes).map(([name, rank]) => (
          <span key={name} className="chip">
            {name} #{rank}
          </span>
        ))}
      </div>
    </Card>
  );
}
