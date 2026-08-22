// The citation chip (OF-DES-001 §7.3) — the load-bearing primitive. One
// component in agent answers, extraction tables, protocol references,
// simulation assumptions, and lesson text.
import { ExternalLink, Copy, AlertTriangle, BookMarked } from 'lucide-react';
import { useStore, provenanceOf } from '@/store';
import { navigate } from '@/router';
import { fmt } from '@/engine/units';
import { fieldName } from '@/data/ontology';
import { Popover, cx, BrokenRef } from './ui';
import { ProvenanceBadge, provMeta, type ProvKind } from './Provenance';

function shortTitle(t: string, max = 64) {
  return t.length > max ? t.slice(0, max - 1) + '…' : t;
}

export function CitationChip({
  paperId,
  recordId,
  label,
  className,
}: {
  paperId?: string;
  recordId?: string;
  label?: string;
  className?: string;
}) {
  const papers = useStore((s) => s.papers);
  const records = useStore((s) => s.records);

  const record = recordId ? records.find((r) => r.id === recordId) : undefined;
  const pid = paperId ?? record?.paperId;
  const paper = pid ? papers.find((p) => p.id === pid) : undefined;

  // Broken links render as an error chip rather than failing silently (§7.3).
  if (!paper) {
    return (
      <BrokenRef
        id={label ?? recordId ?? paperId ?? 'unknown'}
        what="the current corpus"
        className={className}
      />
    );
  }

  const prov: ProvKind = record ? provenanceOf(record) : 'demo';
  const target = record
    ? `/trawl/sources/${paper.id}?span=${record.id}`
    : `/trawl/sources/${paper.id}`;

  const copyCitation = () => {
    const doi = paper.doi ? ` https://doi.org/${paper.doi}` : paper.pmcid ? ` PMC${paper.pmcid.replace(/^PMC/, '')}` : '';
    const caveat =
      paper.textSource === 'curation-note'
        ? ' [catalogued in openFerment; full text not ingested — verify before citing]'
        : '';
    const authors = paper.authors.length ? paper.authors.join(', ') : '(authors pending verification)';
    const text = `${authors} (${paper.year}). ${paper.title}. ${paper.venue}.${doi}${caveat}`;
    navigator.clipboard?.writeText(text);
    useStore.getState().toast({ text: 'Citation copied', kind: 'info' });
  };

  return (
    <Popover
      width={380}
      label={`Source ${paper.id}`}
      trigger={(p) => (
        <button
          {...p}
          className={cx(
            'font-num text-[12px] px-1.5 py-[1px] rounded-input border align-baseline motion-colors',
            'border-line hover:border-accent hover:bg-accent-wash',
            prov === 'gold' && 'border-gold/45',
            prov === 'verified' && 'border-accent/40',
            className,
          )}
          title={`${paper.id} — ${shortTitle(paper.title, 80)}`}
        >
          [{label ?? paper.id}]
        </button>
      )}
    >
      <div className="space-y-2">
        <div>
          <div className="font-serif font-semibold leading-snug">{shortTitle(paper.title, 110)}</div>
          <div className="text-caption text-ink-soft mt-0.5">
            {paper.authors.slice(0, 3).join(', ')}
            {paper.authors.length > 3 ? ' et al.' : ''} · {paper.year} · {paper.venue}
          </div>
        </div>

        {record && (
          <>
            <div
              className={cx('rounded-input border border-line bg-surface-0 p-2 text-body italic', 'font-serif')}
            >
              “{record.quote}”
            </div>
            <div className="flex items-center justify-between gap-2 text-body">
              <div>
                <div className="text-caption text-ink-soft">{fieldName(record.field)}</div>
                <div className="font-num">
                  {fmt(record.value)} {record.unit}
                  {record.si.unit !== record.unit && (
                    <span className="text-ink-soft"> = {fmt(record.si.value)} {record.si.unit}</span>
                  )}
                </div>
              </div>
              <ProvenanceBadge
                p={prov}
                confidence={record.status === 'unverified' ? record.confidence : undefined}
                compact
              />
            </div>
          </>
        )}

        {!record && (
          <div className="text-caption text-ink-soft">
            Paper-level reference. Open to read the source and its anchored extractions.
          </div>
        )}

        <div className="flex items-center gap-2 pt-1 border-t border-line">
          <button className="btn btn-sm" onClick={() => navigate(target)}>
            <ExternalLink size={12} /> Open in context
          </button>
          <button className="btn btn-sm" onClick={copyCitation}>
            <Copy size={12} /> Copy citation
          </button>
        </div>
        {paper.textSource === 'curation-note' && (
          <div className="text-[10px] text-ink-soft flex items-start gap-1.5">
            <BookMarked size={11} className="shrink-0 mt-[1px]" />
            <span>
              Catalogued, full text not yet ingested. The quoted span is the curator&rsquo;s note,
              not the paper&rsquo;s own words.
              {paper.verifyNeeded && ' Author string pending verification.'}
            </span>
          </div>
        )}
      </div>
    </Popover>
  );
}

/** Compact record chip that reads "ex-0112" — used in audit and assumption rows. */
export function RecordChip({ recordId }: { recordId: string }) {
  const record = useStore((s) => s.records.find((r) => r.id === recordId));
  if (!record) return <CitationChip recordId={recordId} label={recordId} />;
  return <CitationChip recordId={recordId} label={record.id} />;
}

/** A tiny inline provenance mark used where a chip would be too heavy. */
export function ProvMark({ p }: { p: ProvKind }) {
  const { Icon, color, label } = provMeta(p);
  return <Icon size={12} className={cx('inline align-[-2px]', color)} aria-label={label} />;
}
