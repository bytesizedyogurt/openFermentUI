// A sentence a claim quotes (OF-BLD-014 §5.4).
//
// The words are the paper's: the validator dropped any claim whose quote is
// not in its passage word for word, so what shows here was checked before it
// arrived. One click opens the reader on the sentence, where span location
// marks it or says it could not.
import { ExternalLink, Quote } from 'lucide-react';
import type { Passage, PassageRef } from '@/data/types';
import { useStore } from '@/store';
import { href } from '@/router';

export function passageReaderHref(passage: Passage, quote: string): string {
  const q = new URLSearchParams({ section: passage.sectionId, quote });
  return href(`/biorepo/paper/${passage.paperId}?${q.toString()}`);
}

export function PassageQuote({ cite, passage }: { cite: PassageRef; passage: Passage | undefined }) {
  const title = useStore((s) => (passage ? s.papers.find((p) => p.id === passage.paperId)?.title : undefined));
  return (
    <figure className="border-l-2 border-accent/70 pl-2.5 py-0.5" data-testid="passage-quote">
      <blockquote className="text-body text-ink">
        <Quote size={10} className="inline mr-1 -mt-0.5 text-ink-soft" aria-hidden />
        {cite.quote}
      </blockquote>
      <figcaption className="mt-0.5 flex flex-wrap items-baseline gap-x-2 text-caption text-ink-soft">
        {passage ? (
          <>
            <span className="font-num">{passage.paperId}</span>
            {title && <span className="truncate max-w-[36ch]">{title}</span>}
            <span>· {passage.heading}</span>
            <a
              className="inline-flex items-center gap-1 hover:text-accent"
              href={passageReaderHref(passage, cite.quote)}
              data-testid="quote-in-reader"
            >
              Open at this sentence <ExternalLink size={10} aria-hidden />
            </a>
          </>
        ) : (
          <span className="font-num">{cite.passageId}</span>
        )}
      </figcaption>
    </figure>
  );
}
