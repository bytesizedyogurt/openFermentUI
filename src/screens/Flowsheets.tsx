// The project's SFF flowsheets (alpha 2.1 stage B; ADR-003): /flowsheets.
//
// Every SFF record the project keeps, newest first (GET /api/flowsheets): the
// file each engine run wrote, a reference file of the toolkit kept here, or a
// file a person imported, each a link to its page and its graph. Two ways in,
// each in the person's name:
//
//   a file        an SFF file chosen from this computer
//                 (POST /api/flowsheets/import): read, checked by the toolkit
//                 in the worker, drawn and kept; a file that fails validation
//                 is kept with its findings, and one that is not an SFF
//                 flowsheet is refused in the service's words;
//   a reference   one of the toolkit's reference files at the pinned commit
//                 (GET /api/flowsheets/library, POST …/library/{id}): fetched,
//                 its hash checked, checked and kept with origin `library`.
//
// No importer rebuilds a plant from a file (§3.4): a record is what the file
// says, and a run is made on Studies.
import { useEffect, useRef, useState } from 'react';
import { BookOpen, Upload } from 'lucide-react';
import type { SFFFlowsheet } from '@/data/types';
import { href, navigate } from '@/router';
import { useStore } from '@/store';
import { stamp } from '@/lib/proforma';
import { StudiesDown, flowsheetLibrary, importFlowsheet, importLibraryFlowsheet, listFlowsheets, type SFFLibraryEntry } from '@/lib/studies';
import { Button, Callout, Card, EmptyState, LinkButton, PageHeader } from '@/components/ui';

const problemOf = (e: unknown) => (e instanceof StudiesDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

/** Where a record came from, in words. */
const ORIGIN_SAYS: Record<SFFFlowsheet['origin'], string> = {
  run: 'an engine run wrote it',
  library: 'a reference file of the toolkit',
  imported: 'imported by a person',
};

function ImportFile() {
  const reviewer = useStore((s) => s.reviewer).trim();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const go = () => {
    if (!file) return;
    setBusy(true);
    setProblem(null);
    importFlowsheet(file, reviewer)
      .then((record) => navigate(`/flowsheets/${record.id}`))
      .catch((e: unknown) => setProblem(problemOf(e)))
      .finally(() => setBusy(false));
  };
  return (
    <Card className="p-4" data-testid="flowsheets-import">
      <h2 className="font-serif text-section-title font-semibold mb-1">Import an SFF file</h2>
      <p className="text-caption text-ink-soft mb-2">
        An SFF flowsheet from this computer, such as a run&rsquo;s file from an export package. The toolkit checks it against the schema it ships; a file
        that fails is kept with what the check found.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={input}
          type="file"
          accept=".json,application/json"
          aria-label="An SFF file"
          className="text-caption"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          data-testid="flowsheets-import-file"
        />
        <Button variant="primary" disabled={busy || !file || !reviewer} onClick={go} data-testid="flowsheets-import-go">
          <Upload size={14} /> {busy ? 'Checking…' : 'Import it'}
        </Button>
      </div>
      {!reviewer && <p className="text-caption text-ink-soft mt-1">A file is kept in a person&rsquo;s name: set yours in Settings first.</p>}
      {problem && (
        <p className="text-caption text-signal-warn mt-1" data-testid="flowsheets-import-problem">
          {problem}
        </p>
      )}
    </Card>
  );
}

function ReferenceFiles({ held }: { held: SFFFlowsheet[] }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const [files, setFiles] = useState<SFFLibraryEntry[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [problem, setProblem] = useState<{ id: string; words: string } | null>(null);
  const [listProblem, setListProblem] = useState<string | null>(null);
  useEffect(() => {
    const ctrl = new AbortController();
    flowsheetLibrary(ctrl.signal)
      .then(setFiles)
      .catch((e: unknown) => !ctrl.signal.aborted && setListProblem(problemOf(e)));
    return () => ctrl.abort();
  }, []);
  const kept = new Map(held.filter((r) => r.libraryId).map((r) => [r.libraryId as string, r.id]));
  const keep = (f: SFFLibraryEntry) => {
    setBusy(f.id);
    setProblem(null);
    importLibraryFlowsheet(f.id, reviewer)
      .then((record) => navigate(`/flowsheets/${record.id}`))
      .catch((e: unknown) => setProblem({ id: f.id, words: problemOf(e) }))
      .finally(() => setBusy(null));
  };
  return (
    <Card className="p-4" data-testid="flowsheets-library">
      <h2 className="font-serif text-section-title font-semibold mb-1">The toolkit&rsquo;s reference files</h2>
      <p className="text-caption text-ink-soft mb-2">
        The SFF toolkit&rsquo;s reference flowsheets at the commit openFerment pins, each fetched once, its hash checked, and kept here as a record.
      </p>
      {listProblem && <p className="text-caption text-signal-warn">{listProblem}</p>}
      {files === null && !listProblem && <p className="text-body text-ink-soft">Reading the toolkit&rsquo;s list…</p>}
      {files && (
        <table className="w-full text-caption">
          <thead>
            <tr className="border-b border-line text-ink-soft">
              {['File', 'Title', 'SFF', 'From', ''].map((h) => (
                <th key={h} className="text-left py-1 pr-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {files.map((f) => (
              <tr key={f.id} className="border-b border-line/50 align-top" data-testid="flowsheets-library-file" data-file={f.id}>
                <td className="py-1 pr-2 font-num">{f.id}</td>
                <td className="py-1 pr-2">{f.title}</td>
                <td className="py-1 pr-2 font-num">{f.sffVersion ?? '—'}</td>
                <td className="py-1 pr-2">{f.model ?? '—'}</td>
                <td className="py-1 pr-2">
                  {kept.has(f.id) ? (
                    <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/flowsheets/${kept.get(f.id)}`)}>
                      kept as {kept.get(f.id)}
                    </a>
                  ) : (
                    <Button size="sm" disabled={!!busy || !reviewer} onClick={() => keep(f)} data-testid="flowsheets-library-keep">
                      {busy === f.id ? 'Fetching…' : f.fetched ? 'Keep it' : 'Fetch and keep it'}
                    </Button>
                  )}
                  {problem?.id === f.id && <span className="block text-signal-warn mt-0.5">{problem.words}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  );
}

export default function Flowsheets() {
  const [held, setHeld] = useState<SFFFlowsheet[] | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  useEffect(() => {
    const ctrl = new AbortController();
    listFlowsheets(ctrl.signal)
      .then(setHeld)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    return () => ctrl.abort();
  }, []);
  return (
    <div data-testid="flowsheets">
      <PageHeader
        eyebrow="Proforma · SFF"
        title="Flowsheets"
        subtitle="Every SFF flowsheet the project keeps: the file each engine run wrote, the toolkit's reference files kept here, and the files people imported, each as the toolkit checked and scored it."
        actions={
          <LinkButton to="/proforma/studies">
            <BookOpen size={14} /> Studies
          </LinkButton>
        }
      />
      {problem && (
        <div className="mb-4">
          <Callout kind="warn">
            <span data-testid="flowsheets-problem">{problem}</span>
          </Callout>
        </div>
      )}
      {held && (
        <div className="space-y-4">
          <Card className="p-4" data-testid="flowsheets-held">
            <h2 className="font-serif text-section-title font-semibold mb-1">What the project keeps</h2>
            {held.length === 0 ? (
              <EmptyState title="No SFF flowsheet yet" body="An engine run writes one; so does importing a file or keeping a reference file below." />
            ) : (
              <table className="w-full text-caption">
                <thead>
                  <tr className="border-b border-line text-ink-soft">
                    {['Record', 'Title', 'From', 'Valid', 'Units', 'Streams', 'By', 'At'].map((h) => (
                      <th key={h} className="text-left py-1 pr-2 font-medium">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {held.map((r) => (
                    <tr key={r.id} className="border-b border-line/50 align-top" data-testid="flowsheets-record" data-record={r.id} data-origin={r.origin}>
                      <td className="py-1 pr-2">
                        <a className="font-num underline underline-offset-2 hover:text-accent" href={href(`/flowsheets/${r.id}`)}>
                          {r.id}
                        </a>
                      </td>
                      <td className="py-1 pr-2">{r.title}</td>
                      <td className="py-1 pr-2">{ORIGIN_SAYS[r.origin] ?? r.origin}</td>
                      <td className="py-1 pr-2">
                        {r.validation.valid ? 'yes' : 'no'}, SFF <span className="font-num">{r.validation.schemaVersion}</span>
                      </td>
                      <td className="py-1 pr-2 font-num">{r.units}</td>
                      <td className="py-1 pr-2 font-num">{r.streams}</td>
                      <td className="py-1 pr-2">{r.createdBy}</td>
                      <td className="py-1 pr-2 font-num">{stamp(r.createdAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
          <ImportFile />
          <ReferenceFiles held={held} />
        </div>
      )}
    </div>
  );
}
