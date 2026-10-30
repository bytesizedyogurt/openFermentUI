// Add to this project (ADR-002): a paper, a report or a strain entry by its
// identifier, a file, or pasted text, collected into the open project's
// corpus in Sci RAG Kit; and the documents the project holds.
//
// Every addition is signed with the reviewer name typed in Settings and kept
// on the project's link with the reason given, so the list can say who
// brought each document in and why. Not collected is shown as the service
// said it, reason and all; nothing is retried behind the reader's back.
import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { ClipboardPaste, FileUp, Link2, Loader2 } from 'lucide-react';
import type { CollectOutcome, LiteratureDocument } from '@/data/types';
import { useStore } from '@/store';
import { IntakeDown } from '@/lib/intake';
import {
  LICENCE_CLASSES,
  collect,
  outcomeWords,
  pasteDocument,
  projectDocuments,
  uploadDocument,
} from '@/lib/literature';
import { Button, Callout, Card, EmptyState, SectionTitle, cx } from '@/components/ui';

type Mode = 'identifier' | 'file' | 'paste';

const MODES: { mode: Mode; label: string; icon: typeof Link2 }[] = [
  { mode: 'identifier', label: 'Identifier', icon: Link2 },
  { mode: 'file', label: 'File', icon: FileUp },
  { mode: 'paste', label: 'Paste', icon: ClipboardPaste },
];

const COLLECTOR_NAMES: Record<string, string> = {
  europepmc: 'Europe PMC',
  osti: 'OSTI',
  sgd: 'SGD',
  upload: 'Upload',
  paste: 'Pasted',
};

function said(e: unknown): string {
  return e instanceof IntakeDown ? `${e.message} ${e.remedy}` : String(e instanceof Error ? e.message : e);
}

export function CollectCard() {
  const reviewer = useStore((s) => s.reviewer).trim();
  const projectId = useStore((s) => s.projectId);
  const serviceUp = useStore((s) => s.serviceUp);
  const hydrateOverlay = useStore((s) => s.hydrateOverlay);
  const [mode, setMode] = useState<Mode>('identifier');
  const [identifier, setIdentifier] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');
  const [url, setUrl] = useState('');
  const [licenceClass, setLicenceClass] = useState('unknown');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState<CollectOutcome | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [documents, setDocuments] = useState<LiteratureDocument[] | null>(null);

  const refresh = useCallback(async (signal?: AbortSignal) => {
    try {
      setDocuments(await projectDocuments(signal));
      setProblem(null);
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return;
      setProblem(said(e));
    }
  }, []);

  useEffect(() => {
    if (serviceUp !== true || !projectId) return;
    const controller = new AbortController();
    void refresh(controller.signal);
    return () => controller.abort();
  }, [serviceUp, projectId, refresh]);

  const ready =
    mode === 'identifier' ? identifier.trim() !== '' : mode === 'file' ? file !== null : title.trim() !== '' && text.trim() !== '';

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!reviewer || busy || !ready) return;
    setBusy(true);
    setLast(null);
    try {
      const outcome =
        mode === 'identifier'
          ? await collect({ identifier: identifier.trim(), by: reviewer, reason })
          : mode === 'file' && file
            ? await uploadDocument(file, { by: reviewer, title, licenceClass, reason })
            : await pasteDocument({ title, text, url, by: reviewer, licenceClass, reason });
      setLast(outcome);
      if (outcome.status !== 'failed') {
        setIdentifier('');
        setFile(null);
        setTitle('');
        setText('');
        setUrl('');
        setReason('');
        // The overlay brings the document as a paper: the board, BioRepo and
        // the reader see it without a reload.
        await Promise.all([refresh(), hydrateOverlay()]);
      }
    } catch (e) {
      setProblem(said(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="p-3">
      <SectionTitle
        right={
          documents ? (
            <span className="text-caption text-ink-soft font-num">
              {documents.length} in this project
            </span>
          ) : undefined
        }
      >
        Add to this project
      </SectionTitle>
      <p className="text-caption text-ink-soft mb-2">
        Collected text is split into passages, embedded on this machine and kept in the project&rsquo;s
        corpus, where search, answers and extraction read it. A paper another project holds already is
        linked rather than stored twice.
      </p>

      {serviceUp === false && (
        <Callout kind="warn" title="The service is not running">
          Nothing can be collected until it is: start it, then reload.
        </Callout>
      )}

      <div className="flex gap-1 mb-2" role="tablist" aria-label="How to add">
        {MODES.map(({ mode: m, label, icon: Icon }) => (
          <button
            key={m}
            type="button"
            role="tab"
            aria-selected={mode === m}
            className={cx('btn btn-sm', mode === m && 'btn-primary')}
            onClick={() => setMode(m)}
          >
            <Icon size={14} aria-hidden /> {label}
          </button>
        ))}
      </div>

      <form className="space-y-2" onSubmit={submit} aria-label="Add a document">
        {mode === 'identifier' && (
          <input
            className="input w-full"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="PMC…, a DOI, PMID:…, OSTI:…, or an osti.gov or yeastgenome.org address"
            aria-label="Identifier"
            maxLength={500}
          />
        )}
        {mode === 'file' && (
          <input
            className="input w-full"
            type="file"
            accept=".pdf,.xml,.md,.markdown,.txt,.html,.htm"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            aria-label="File"
          />
        )}
        {mode !== 'identifier' && (
          <input
            className="input w-full"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={mode === 'paste' ? 'Title' : 'Title (the file name when left empty)'}
            aria-label="Title"
            maxLength={500}
          />
        )}
        {mode === 'paste' && (
          <>
            <textarea
              className="input w-full min-h-[96px]"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="The text"
              aria-label="Text"
            />
            <input
              className="input w-full"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Where it came from (optional)"
              aria-label="Where it came from"
              maxLength={2000}
            />
          </>
        )}
        {mode !== 'identifier' && (
          <select
            className="input w-full"
            value={licenceClass}
            onChange={(e) => setLicenceClass(e.target.value)}
            aria-label="Licence"
          >
            {LICENCE_CLASSES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        )}
        <input
          className="input w-full"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Why it belongs here (optional)"
          aria-label="Why it belongs here"
          maxLength={2000}
        />
        <div className="flex items-center gap-2">
          <Button type="submit" variant="primary" size="sm" disabled={!reviewer || busy || !ready || serviceUp === false}>
            {busy ? <Loader2 size={14} className="animate-spin" aria-hidden /> : null}
            {busy ? 'Collecting…' : 'Collect'}
          </Button>
          {!reviewer && (
            <span className="text-caption text-ink-soft">
              Type your name in <a href="#/settings">Settings</a> first: every addition is signed.
            </span>
          )}
        </div>
      </form>

      {last && (
        <p
          className={cx('text-caption mt-2', last.status === 'failed' ? 'text-signal-error' : 'text-ink')}
          role="status"
        >
          {last.title || last.identifier}: {outcomeWords(last)}
          {last.status === 'failed' && last.transient ? ' Try again later.' : ''}
        </p>
      )}
      {problem && (
        <p className="text-caption text-signal-error mt-2" role="alert">
          {problem}
        </p>
      )}

      {documents && documents.length === 0 && (
        <div className="mt-3">
          <EmptyState title="Nothing collected yet" body="What this project reads appears here once it is added." />
        </div>
      )}
      {documents && documents.length > 0 && (
        <ul className="mt-3 divide-y divide-line" aria-label="Documents in this project">
          {documents.map((d) => (
            <li key={d.documentId} className="py-2">
              <div className="text-body leading-snug">{d.title}</div>
              <div className="text-caption text-ink-soft">
                {COLLECTOR_NAMES[d.collector ?? ''] ?? d.collector ?? 'unknown source'}
                {d.year ? ` · ${d.year}` : ''} · <span className="font-num">{d.chunks}</span> passages ·{' '}
                {d.licenceClass.replace('_', ' ')} · added by {d.linkedBy}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
