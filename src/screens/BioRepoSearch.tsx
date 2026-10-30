// BioRepo → Search: the papers' own words, searched (ADR-002).
//
// A question finds passages of the open project's documents through Sci RAG
// Kit (vector and keyword, no model asked), best first, each cited to its
// document and section and opening the reader at that passage. Answer asks
// the model once for a cited answer over the same passages: one call through
// the service, under the day's cap; each [n] in it is a source listed below
// it, and a source the answer did not cite is shown as uncited.
import { useState, type FormEvent } from 'react';
import { Loader2, MessageSquareQuote, Search as SearchIcon } from 'lucide-react';
import type { SearchResponse } from '@/data/types';
import { useStore } from '@/store';
import { href } from '@/router';
import { IntakeDown } from '@/lib/intake';
import { answerFromLiterature, searchLiterature, type AnswerSource } from '@/lib/literature';
import { Button, Callout, Card, EmptyState, PageHeader, SectionTitle, cx } from '@/components/ui';
import { OwnerTabs } from '@/components/OwnerTabs';
import { BIOREPO_TABS } from '@/data/tabs';

function said(e: unknown): string {
  return e instanceof IntakeDown ? `${e.message} ${e.remedy}` : String(e instanceof Error ? e.message : e);
}

const readerLink = (documentId: string, passageId: string | null) =>
  href(`/biorepo/paper/${documentId}${passageId ? `?section=${encodeURIComponent(passageId)}` : ''}`);

export default function BioRepoSearch() {
  const serviceUp = useStore((s) => s.serviceUp);
  const [query, setQuery] = useState('');
  const [found, setFound] = useState<SearchResponse | null>(null);
  const [searching, setSearching] = useState(false);
  const [answer, setAnswer] = useState('');
  const [sources, setSources] = useState<AnswerSource[] | null>(null);
  const [answering, setAnswering] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const search = async (event: FormEvent) => {
    event.preventDefault();
    if (!query.trim() || searching) return;
    setSearching(true);
    setProblem(null);
    try {
      setFound(await searchLiterature(query.trim()));
    } catch (e) {
      setProblem(said(e));
    } finally {
      setSearching(false);
    }
  };

  const ask = async () => {
    if (!query.trim() || answering) return;
    setAnswering(true);
    setProblem(null);
    setAnswer('');
    setSources(null);
    try {
      setSources(await answerFromLiterature(query.trim(), (text) => setAnswer((a) => a + text)));
    } catch (e) {
      setProblem(said(e));
    } finally {
      setAnswering(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Search the papers"
        subtitle="Passages of the project's documents, found for a question, each cited to its document and section."
      />
      <OwnerTabs tabs={BIOREPO_TABS} />

      {serviceUp === false && (
        <div className="mb-4">
          <Callout kind="warn" title="The service is not running">
            Search reads the project&rsquo;s literature on the service; start it, then reload.
          </Callout>
        </div>
      )}

      <Card className="p-3 mb-4">
        <form className="flex flex-wrap gap-2 items-center" onSubmit={search} aria-label="Search the papers">
          <input
            className="input flex-1 min-w-[240px]"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="A question, or the words a passage would use"
            aria-label="Question"
            maxLength={2000}
          />
          <Button type="submit" variant="primary" size="sm" disabled={!query.trim() || searching}>
            {searching ? <Loader2 size={14} className="animate-spin" aria-hidden /> : <SearchIcon size={14} aria-hidden />}
            Search
          </Button>
          <Button type="button" size="sm" disabled={!query.trim() || answering} onClick={() => void ask()}>
            {answering ? (
              <Loader2 size={14} className="animate-spin" aria-hidden />
            ) : (
              <MessageSquareQuote size={14} aria-hidden />
            )}
            Answer with citations
          </Button>
        </form>
        <p className="text-caption text-ink-soft mt-2">
          Search asks no model. An answer is one model call over the passages it finds, kept to the day&rsquo;s budget.
        </p>
        {problem && (
          <p className="text-caption text-signal-error mt-2" role="alert">
            {problem}
          </p>
        )}
      </Card>

      {(answer || sources) && (
        <Card className="p-3 mb-4">
          <SectionTitle>Answer</SectionTitle>
          <p className="text-body whitespace-pre-wrap" aria-live="polite">
            {answer}
          </p>
          {sources && sources.length > 0 && (
            <ol className="mt-3 space-y-1 text-caption" aria-label="Sources">
              {sources.map((s) => (
                <li key={s.index} className={cx(!s.cited && 'text-ink-soft')}>
                  [{s.index}]{' '}
                  {s.document_id ? <a href={readerLink(s.document_id, s.passage_id)}>{s.title}</a> : s.title}
                  {s.section_path ? ` · ${s.section_path}` : ''}
                  {s.cited ? '' : ' · not cited'}
                </li>
              ))}
            </ol>
          )}
        </Card>
      )}

      {found && found.hits.length === 0 && (
        <Card>
          <EmptyState
            icon={<SearchIcon size={20} />}
            title="Nothing found"
            body="No passage of the project's documents answers this. Documents enter through Intake; add the ones this question needs."
          />
        </Card>
      )}
      {found && found.hits.length > 0 && (
        <Card className="p-3">
          <SectionTitle
            right={<span className="text-caption text-ink-soft font-num">{found.hits.length} passages</span>}
          >
            Passages
          </SectionTitle>
          {found.degradedStages.length > 0 && (
            <p className="text-caption text-ink-soft mb-2">
              Not every layer answered ({found.degradedStages.join(', ')}); these are what the rest found.
            </p>
          )}
          <ol className="divide-y divide-line" aria-label="Passages found">
            {found.hits.map((h) => (
              <li key={`${h.documentId}:${h.passageId}`} className="py-2">
                <a href={readerLink(h.documentId, h.passageId)} className="text-body leading-snug">
                  {h.title}
                </a>
                <div className="text-caption text-ink-soft">
                  {h.sectionPath ?? 'Text'}
                  {h.year ? ` · ${h.year}` : ''} · {h.licenceClass.replace('_', ' ')}
                  {h.isTable ? ' · table' : ''}
                </div>
                <p className={cx('text-caption mt-1 whitespace-pre-wrap', h.isTable && 'font-num')}>
                  {h.text.length > 600 ? `${h.text.slice(0, 600)}…` : h.text}
                </p>
              </li>
            ))}
          </ol>
        </Card>
      )}
      {!found && !answer && !sources && (
        <Card>
          <EmptyState
            icon={<SearchIcon size={20} />}
            title="Ask the project's literature"
            body="Search finds the passages of the documents the project holds; an answer cites them."
          />
        </Card>
      )}
    </div>
  );
}
