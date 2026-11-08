// The project's catalogues (alpha 2.2 E.8; the execution prompt's §6.5): /catalogues.
//
// The strains and the other names papers give them, the products, Guild's skills and Primer's lessons the project
// keeps, one tab a catalogue (/catalogues, /catalogues/products, /catalogues/skills, /catalogues/lessons). Each tab
// lists its entries, each with who kept it, in which lane, when and from where (GET /api/catalogues/{kind}); adds
// an entry and edits one (POST /api/catalogues/{kind}), each keep in the name Settings holds, so a keep waits for a
// name and the service refuses one with none in words too; and takes in a file of entries (POST
// /api/intake/catalogue, JSON or CSV), every row kept or refused in the service's words. Editing an entry keeps it
// under its id in the person's name, whoever kept it before. Nothing here takes an entry out: taking a person's entry
// out of a live instance is the owner's call.
//
// Who reads what is kept, on the service: pureOS proposes a train for a product made in a strain kept here, by the
// product's class and where the cells leave it; Postdoc reads the strains among geneOS's hosts and finds a strain a
// question names by any of its names; ProtParam computes from a product's sequence; Guild rates people on each skill
// by its policy, and nobody on a skill kept with none; a lesson passed counts toward the skills it names. The store
// reads all four catalogues (alpha 2.2 E.9 and E.12) as the page opens and again after each keep and each file taken
// in here, so geneOS's hosts, the strain choosers, the runbooks, Guild, the protocols and Primer name what this screen
// keeps. A lesson's body (its minutes, its blocks and its checkpoint, ADR-018) arrives in a file of lessons; the form
// edits the rest of a lesson and sends its body back as the lesson holds it (`edited`). Every shape is the service's
// own (src/lib/catalogues.ts).
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { BookMarked, Pencil, Plus, Upload } from 'lucide-react';
import { href } from '@/router';
import { useStore } from '@/store';
import { stamp } from '@/lib/proforma';
import {
  CataloguesDown,
  blankEntry,
  bodyWords,
  edited,
  hasPolicy,
  keepEntry,
  keptIn,
  listCatalogue,
  takeInCatalogue,
  type CatalogueEntry,
  type CatalogueIntake,
  type CatalogueKind,
  type ProductCategory,
  type ProductLocation,
  type SkillCriticality,
} from '@/lib/catalogues';
import { PRODUCT_CATEGORY_LABEL, PRODUCT_LOCATION_LABEL, SKILL_CRITICALITY_LABEL } from '@/data/labels';
import { FAMILIES } from '@/data/skillFamilies';
import { CATALOGUE_TABS } from '@/data/tabs';
import { OwnerTabs } from '@/components/OwnerTabs';
import { Button, Callout, Card, EmptyState, PageHeader } from '@/components/ui';

const problemOf = (e: unknown) => (e instanceof CataloguesDown ? `${e.message} ${e.remedy ?? ''}`.trim() : e instanceof Error ? e.message : String(e));

/** Each tab's path segment and the catalogue it shows; the strains are at /catalogues. */
const KIND_OF_VIEW: Record<string, CatalogueKind> = { '': 'strain', strains: 'strain', products: 'product', skills: 'skill', lessons: 'lesson' };

/** What each catalogue is called, one entry and many, and who reads it. */
const KIND_WORDS: Record<CatalogueKind, { one: string; many: string; read: string }> = {
  strain: {
    one: 'strain',
    many: 'strains',
    read: 'A strain kept here is a host pureOS proposes a train in, and Postdoc reads it among geneOS’s hosts; its other names are the names papers give it.',
  },
  product: {
    one: 'product',
    many: 'products',
    read: 'A product kept here is one pureOS proposes a train for, by its class and where the cells leave it, and ProtParam computes from its sequence.',
  },
  skill: {
    one: 'skill',
    many: 'skills',
    read: 'A skill kept here is one Guild rates people on, by the policy its entry holds: how critical it is, how many days a qualification stands, how many supervised runs come before a witnessed check, and the skills it needs first.',
  },
  lesson: {
    one: 'lesson',
    many: 'lessons',
    read: 'A lesson kept here counts toward the skills it names: passing it puts a learner at Learning on each of them that holds a policy.',
  },
};

/** An entry as the form holds it while a person types: every field in words, a list one item a line. */
interface Draft {
  id: string;
  name: string;
  summary: string;
  note: string;
  source: string;
  species: string;
  program: string;
  aliases: string;
  category: ProductCategory | '';
  location: ProductLocation | '';
  sequence: string;
  sequenceSource: string;
  family: string;
  mastery: string;
  criticality: SkillCriticality | '';
  recencyDays: string;
  supervisedRuns: string;
  prerequisites: string[];
  skills: string[];
}

/** The fields a person types as words. */
type TextKey = 'id' | 'name' | 'summary' | 'note' | 'source' | 'species' | 'program' | 'aliases' | 'sequence' | 'sequenceSource' | 'mastery';

const draftOf = (e: CatalogueEntry): Draft => ({
  id: e.id,
  name: e.name,
  summary: e.summary ?? '',
  note: e.note ?? '',
  source: e.source ?? '',
  species: e.species ?? '',
  program: e.program ?? '',
  aliases: (e.aliases ?? []).join('\n'),
  category: e.category ?? '',
  location: e.location ?? '',
  sequence: e.sequence ?? '',
  sequenceSource: e.sequenceSource ?? '',
  family: e.family ?? '',
  mastery: (e.mastery ?? []).join('\n'),
  criticality: e.criticality ?? '',
  recencyDays: e.recencyDays == null ? '' : String(e.recencyDays),
  supervisedRuns: e.supervisedRuns == null ? '' : String(e.supervisedRuns),
  prerequisites: [...(e.prerequisites ?? [])],
  skills: [...(e.skills ?? [])],
});

const words = (s: string): string | null => s.trim() || null;
const lines = (s: string): string[] =>
  s
    .split('\n')
    .map((x) => x.trim())
    .filter(Boolean);
/** A count a person typed, or none when the box is empty; the service refuses one that is no whole number, in words. */
const count = (s: string): number | null => (s.trim() === '' ? null : Number(s));

/**
 * The entry a draft sends: the entry as the form opened it with the fields its kind's form holds laid over it, a blank
 * field as none (`edited`), so a lesson's body goes back as the lesson holds it. The service writes who kept it and when.
 */
function entryOf(kind: CatalogueKind, d: Draft, start: CatalogueEntry): CatalogueEntry {
  const base: Partial<CatalogueEntry> = { id: d.id.trim(), name: d.name.trim(), summary: words(d.summary), note: words(d.note), source: words(d.source) };
  switch (kind) {
    case 'strain':
      return edited(start, { ...base, species: words(d.species), program: words(d.program), aliases: lines(d.aliases) });
    case 'product':
      return edited(start, { ...base, category: d.category || null, location: d.location || null, sequence: words(d.sequence), sequenceSource: words(d.sequenceSource) });
    case 'skill':
      return edited(start, {
        ...base,
        family: words(d.family),
        mastery: lines(d.mastery),
        criticality: d.criticality || null,
        recencyDays: count(d.recencyDays),
        supervisedRuns: count(d.supervisedRuns),
        prerequisites: d.prerequisites,
      });
    case 'lesson':
      return edited(start, { ...base, skills: d.skills });
  }
}

/** A labelled box of the form. */
function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block text-caption text-ink-soft">
      {label}
      {children}
      {hint && <span className="block mt-0.5 text-ink-soft/80">{hint}</span>}
    </label>
  );
}

/** The skills a skill needs first, or a lesson counts toward, chosen from the skills the project keeps. */
function SkillChoice({
  label,
  held,
  chosen,
  leaveOut,
  onChange,
  testid,
}: {
  label: string;
  held: CatalogueEntry[];
  chosen: string[];
  leaveOut?: string;
  onChange: (ids: string[]) => void;
  testid: string;
}) {
  // An id the entry names that the catalogue holds no skill under stays offered, so a keep leaves it as it was. A
  // skill kept with no policy is marked: nobody reaches Supervised on it, so a skill that needs it first waits too.
  const offered = [
    ...held.filter((s) => s.id !== leaveOut).map((s) => ({ id: s.id, name: s.name, rated: hasPolicy(s) })),
    ...chosen.filter((id) => !held.some((s) => s.id === id)).map((id) => ({ id, name: 'an id the skills catalogue keeps no entry under', rated: true })),
  ];
  const flip = (id: string) => onChange(chosen.includes(id) ? chosen.filter((x) => x !== id) : [...chosen, id]);
  return (
    <fieldset className="text-caption text-ink-soft" data-testid={testid}>
      <legend>{label}</legend>
      {offered.length === 0 ? (
        <p className="mt-0.5">
          Keep this skill first; the skills kept after it can name it as a prerequisite.
        </p>
      ) : (
        <div className="mt-0.5 flex flex-wrap gap-x-4 gap-y-1">
          {offered.map((s) => (
            <label key={s.id} className="inline-flex items-center gap-1.5 text-body text-ink">
              <input type="checkbox" checked={chosen.includes(s.id)} onChange={() => flip(s.id)} />
              <span className="font-num">{s.id}</span>
              <span className="text-caption text-ink-soft">{s.name}</span>
              {!s.rated && <span className="text-caption text-signal-warn">no policy yet</span>}
            </label>
          ))}
        </div>
      )}
    </fieldset>
  );
}

/** Adds an entry of `kind`, or edits `start` under its own id, in the name Settings holds. */
function EntryForm({
  kind,
  start,
  skills,
  onKept,
  onDone,
}: {
  kind: CatalogueKind;
  start: CatalogueEntry;
  skills: CatalogueEntry[];
  onKept: (kept: CatalogueEntry) => void;
  onDone: () => void;
}) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const editing = start.id !== '';
  const [d, setD] = useState<Draft>(() => draftOf(start));
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const set = <K extends keyof Draft>(key: K, value: Draft[K]) => setD((was) => ({ ...was, [key]: value }));
  const box = (key: TextKey, label: string, hint?: string) => (
    <Field label={label} hint={hint}>
      <input
        className="input text-body block mt-0.5 w-full"
        value={d[key]}
        onChange={(e) => set(key, e.target.value)}
        readOnly={key === 'id' && editing}
        aria-label={label}
        data-testid={`catalogue-field-${key}`}
      />
    </Field>
  );
  const area = (key: TextKey, label: string, hint?: string, mono = false) => (
    <Field label={label} hint={hint}>
      <textarea
        className={`input text-body block mt-0.5 w-full min-h-[72px] resize-y ${mono ? 'font-num' : 'font-sans'}`}
        value={d[key]}
        onChange={(e) => set(key, e.target.value)}
        aria-label={label}
        data-testid={`catalogue-field-${key}`}
      />
    </Field>
  );
  const keep = () => {
    setBusy(true);
    setProblem(null);
    keepEntry({ entry: entryOf(kind, d, start), by: reviewer })
      .then(onKept)
      .catch((e: unknown) => setProblem(problemOf(e)))
      .finally(() => setBusy(false));
  };
  const kw = KIND_WORDS[kind];
  return (
    <Card className="p-4" data-testid="catalogue-form" data-mode={editing ? 'edit' : 'add'} data-entry={start.id || undefined}>
      <h2 className="font-serif text-section-title font-semibold mb-1">{editing ? `Edit ${start.id}` : `Add a ${kw.one}`}</h2>
      <p className="text-caption text-ink-soft mb-3">
        {editing
          ? `Keeping it replaces the entry under ${start.id} with what this form holds, in your name${start.agent === 'model' ? '; a model kept it, so keeping it makes it a person’s' : ''}.`
          : kind === 'skill'
            ? 'A skill and its policy, in words.'
            : `Names and words: a number a paper reports is a record, kept in BioRepo.`}
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        {box('id', 'Id', editing ? 'An entry keeps its id.' : 'A letter or a digit first, then letters, digits, ".", "_", ":" or "-".')}
        {box('name', 'Name')}
        {kind === 'strain' && (
          <>
            {box('species', 'Species')}
            {box('program', 'Chemical set', 'The chemical set its trains use, as pureOS names it.')}
            <div className="sm:col-span-2">{area('aliases', 'Other names', 'The names papers give it, one a line.')}</div>
          </>
        )}
        {kind === 'product' && (
          <>
            <Field label="Class" hint="The class pureOS's proposer reads.">
              <select className="input text-body block mt-0.5 w-full" value={d.category} onChange={(e) => set('category', e.target.value as Draft['category'])} aria-label="Class" data-testid="catalogue-field-category">
                <option value="">None stated</option>
                {(Object.entries(PRODUCT_CATEGORY_LABEL) as [ProductCategory, string][]).map(([c, label]) => (
                  <option key={c} value={c}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Where the cells leave it" hint="The proposer's rules split a protein or a polymer on it.">
              <select className="input text-body block mt-0.5 w-full" value={d.location} onChange={(e) => set('location', e.target.value as Draft['location'])} aria-label="Where the cells leave it" data-testid="catalogue-field-location">
                <option value="">None stated</option>
                {(Object.entries(PRODUCT_LOCATION_LABEL) as [ProductLocation, string][]).map(([l, label]) => (
                  <option key={l} value={l}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <div className="sm:col-span-2">{area('sequence', 'Sequence', "A protein's own chain, one letter a residue.", true)}</div>
            <div className="sm:col-span-2">{box('sequenceSource', 'Where the sequence was read', 'A sequence enters with where it was read: an entry of a database, a table of a paper.')}</div>
          </>
        )}
        {kind === 'skill' && (
          <>
            <Field label="Family">
              <select className="input text-body block mt-0.5 w-full" value={d.family} onChange={(e) => set('family', e.target.value)} aria-label="Family" data-testid="catalogue-field-family">
                <option value="">None stated</option>
                {FAMILIES.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
                {d.family && !FAMILIES.some((f) => f.id === d.family) && <option value={d.family}>{d.family}</option>}
              </select>
            </Field>
            <Field label="Criticality" hint="Part of the policy Guild's levels read.">
              <select className="input text-body block mt-0.5 w-full" value={d.criticality} onChange={(e) => set('criticality', e.target.value as Draft['criticality'])} aria-label="Criticality" data-testid="catalogue-field-criticality">
                <option value="">None stated</option>
                {(Object.entries(SKILL_CRITICALITY_LABEL) as [SkillCriticality, string][]).map(([c, label]) => (
                  <option key={c} value={c}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Days a qualification stands" hint="The days a qualification stands unobserved.">
              <input type="number" min={1} step={1} className="input text-body block mt-0.5 w-full" value={d.recencyDays} onChange={(e) => set('recencyDays', e.target.value)} aria-label="Days a qualification stands" data-testid="catalogue-field-recencyDays" />
            </Field>
            <Field label="Supervised runs before a check" hint="Cosigned runs before a witnessed check can qualify.">
              <input type="number" min={0} step={1} className="input text-body block mt-0.5 w-full" value={d.supervisedRuns} onChange={(e) => set('supervisedRuns', e.target.value)} aria-label="Supervised runs before a check" data-testid="catalogue-field-supervisedRuns" />
            </Field>
            <div className="sm:col-span-2">
              <SkillChoice label="Skills it needs first, at Supervised or above" held={skills} chosen={d.prerequisites} leaveOut={d.id.trim()} onChange={(ids) => set('prerequisites', ids)} testid="catalogue-field-prerequisites" />
            </div>
            <div className="sm:col-span-2">{area('mastery', 'What mastery means', 'What an assessor watches for, one criterion a line.')}</div>
          </>
        )}
        {kind === 'lesson' && (
          <div className="sm:col-span-2">
            <SkillChoice label="Skills it counts toward" held={skills} chosen={d.skills} onChange={(ids) => set('skills', ids)} testid="catalogue-field-skills" />
            <p className="text-caption text-ink-soft mt-1" data-testid="catalogue-lesson-body">
              Its body ({bodyWords(start)}) is written in a file of lessons taken in below, and keeping this form keeps the body as the
              lesson holds it.
            </p>
          </div>
        )}
        <div className="sm:col-span-2">
          {area('summary', 'Summary', kind === 'lesson' ? 'What the lesson is about, in plain words: Primer shows it under the lesson’s name.' : 'What it is, in plain words.')}
        </div>
        {kind === 'lesson'
          ? box('note', 'Opening words', 'The words Primer opens the lesson with, before its blocks; Markdown.')
          : box('note', 'Note', 'What the entry rests on, in words.')}
        {box('source', 'Where it came from', 'A document, a record, a person.')}
      </div>
      {kind === 'skill' && (
        <p className="text-caption text-ink-soft mt-2">
          A policy names its criticality, its days and its supervised runs together; Guild rates people on a skill once its policy is written here.
        </p>
      )}
      <div className="flex flex-wrap items-center gap-2 mt-3">
        <Button variant="primary" disabled={busy || !reviewer || !d.id.trim() || !d.name.trim()} onClick={keep} data-testid="catalogue-keep">
          {busy ? 'Keeping…' : editing ? 'Keep the change' : `Keep the ${kw.one}`}
        </Button>
        <Button onClick={onDone} disabled={busy} data-testid="catalogue-cancel">
          Close
        </Button>
        {!reviewer && (
          <span className="text-caption text-ink-soft">
            An entry is kept in a person&rsquo;s name: set yours in{' '}
            <a className="underline underline-offset-2 hover:text-accent" href={href('/settings/corpus')}>
              Settings
            </a>{' '}
            first.
          </span>
        )}
      </div>
      {problem && (
        <p className="text-caption text-signal-warn mt-2" data-testid="catalogue-problem">
          {problem}
        </p>
      )}
    </Card>
  );
}

/** A file of entries of `kind` taken in, in the name Settings holds: every row kept or refused in the service's words. */
function TakeInFile({ kind, onTaken }: { kind: CatalogueKind; onTaken: () => void }) {
  const reviewer = useStore((s) => s.reviewer).trim();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [taken, setTaken] = useState<CatalogueIntake | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const go = () => {
    if (!file) return;
    setBusy(true);
    setProblem(null);
    setTaken(null);
    takeInCatalogue(kind, file, reviewer)
      .then((got) => {
        setTaken(got);
        onTaken();
      })
      .catch((e: unknown) => setProblem(problemOf(e)))
      .finally(() => setBusy(false));
  };
  const kw = KIND_WORDS[kind];
  return (
    <Card className="p-4" data-testid="catalogue-intake">
      <h2 className="font-serif text-section-title font-semibold mb-1">Take in a file of {kw.many}</h2>
      <p className="text-caption text-ink-soft mb-2">
        JSON, a list of entries or one under <span className="font-num">entries</span>, or CSV with <span className="font-num">id</span> and{' '}
        <span className="font-num">name</span> columns, a list&rsquo;s items split by <span className="font-num">;</span>. Every row that is an entry is kept
        in your name with the file as its source, an entry under its id replaced; every other row is refused with its reason.
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          ref={input}
          type="file"
          accept=".json,.csv,application/json,text/csv"
          aria-label={`A file of ${kw.many}`}
          className="text-caption"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          data-testid="catalogue-intake-file"
        />
        <Button variant="primary" disabled={busy || !file || !reviewer} onClick={go} data-testid="catalogue-intake-go">
          <Upload size={14} /> {busy ? 'Taking it in…' : 'Take it in'}
        </Button>
      </div>
      {!reviewer && <p className="text-caption text-ink-soft mt-1">A file is taken in a person&rsquo;s name: set yours in Settings first.</p>}
      {problem && (
        <p className="text-caption text-signal-warn mt-1" data-testid="catalogue-intake-problem">
          {problem}
        </p>
      )}
      {taken && (
        <div className="text-caption mt-2" data-testid="catalogue-intake-result" data-kept={taken.kept.length} data-refused={taken.refused.length}>
          <p>
            {taken.kept.length === 0 ? 'No row was kept.' : `Kept ${taken.kept.length}: `}
            {taken.kept.map((k, i) => (
              <span key={k} className="font-num">
                {i > 0 && ', '}
                {k}
              </span>
            ))}
          </p>
          {taken.refused.length > 0 && (
            <ul className="mt-1 text-signal-warn list-disc pl-5">
              {taken.refused.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  );
}

/** What a row says of one entry, beside its id and name, by kind. */
function Cells({ entry }: { entry: CatalogueEntry }) {
  const none = <span className="text-ink-soft">—</span>;
  switch (entry.kind) {
    case 'strain':
      return (
        <>
          <td className="py-1 pr-2">{entry.species ?? none}</td>
          <td className="py-1 pr-2 font-num">{entry.program ?? none}</td>
          <td className="py-1 pr-2">{entry.aliases?.length ? entry.aliases.join(', ') : none}</td>
        </>
      );
    case 'product':
      return (
        <>
          <td className="py-1 pr-2">{entry.category ? PRODUCT_CATEGORY_LABEL[entry.category] : none}</td>
          <td className="py-1 pr-2">{entry.location ? PRODUCT_LOCATION_LABEL[entry.location] : none}</td>
          <td className="py-1 pr-2">{entry.sequence ? `${entry.sequence.length} residues, read from ${entry.sequenceSource ?? 'a source left unnamed'}` : none}</td>
        </>
      );
    case 'skill':
      return (
        <>
          <td className="py-1 pr-2">{entry.family ? (FAMILIES.find((f) => f.id === entry.family)?.name ?? entry.family) : none}</td>
          <td className="py-1 pr-2" data-testid="catalogue-policy" data-policy={hasPolicy(entry) ? 'held' : 'none'}>
            {hasPolicy(entry) ? (
              `${entry.criticality === 'critical' ? 'Critical' : 'Routine'}; a qualification stands ${entry.recencyDays} days; ${entry.supervisedRuns} supervised run${entry.supervisedRuns === 1 ? '' : 's'} before a check`
            ) : (
              <span className="text-signal-warn">No policy yet: Guild rates nobody on it</span>
            )}
          </td>
          <td className="py-1 pr-2 font-num">{entry.prerequisites?.length ? entry.prerequisites.join(', ') : none}</td>
        </>
      );
    case 'lesson':
      return (
        <>
          <td className="py-1 pr-2 font-num">{entry.skills?.length ? entry.skills.join(', ') : none}</td>
          <td
            className="py-1 pr-2"
            data-testid="catalogue-lesson-row-body"
            data-minutes={entry.minutes ?? ''}
            data-blocks={(entry.blocks ?? []).length}
            data-questions={(entry.checkpoint ?? []).length}
          >
            {bodyWords(entry)}
          </td>
        </>
      );
  }
}

const COLUMNS: Record<CatalogueKind, string[]> = {
  strain: ['Species', 'Chemical set', 'Other names'],
  product: ['Class', 'Where the cells leave it', 'Sequence'],
  skill: ['Family', 'Policy', 'Needs first'],
  lesson: ['Counts toward', 'Body'],
};

export default function Catalogues({ view }: { view?: string }) {
  const kind = KIND_OF_VIEW[view ?? ''];
  const [entries, setEntries] = useState<CatalogueEntry[] | null>(null);
  const [skills, setSkills] = useState<CatalogueEntry[]>([]);
  const [problem, setProblem] = useState<string | null>(null);
  const [editing, setEditing] = useState<CatalogueEntry | null>(null);
  const [kept, setKept] = useState<CatalogueEntry | null>(null);
  const [version, setVersion] = useState(0);
  const hydrateCatalogues = useStore((s) => s.hydrateCatalogues);
  // After a keep or a file, this tab reads its catalogue again, and the store reads all four catalogues again.
  const reread = () => {
    setVersion((v) => v + 1);
    void hydrateCatalogues();
  };
  useEffect(() => {
    setEditing(null);
    setKept(null);
  }, [kind]);
  useEffect(() => {
    if (!kind) return;
    const ctrl = new AbortController();
    setEntries(null);
    setProblem(null);
    listCatalogue(kind, ctrl.signal)
      .then(setEntries)
      .catch((e: unknown) => !ctrl.signal.aborted && setProblem(problemOf(e)));
    // A skill names the skills it needs first and a lesson the skills it counts toward, chosen from those kept.
    if (kind === 'lesson')
      listCatalogue('skill', ctrl.signal)
        .then(setSkills)
        .catch(() => setSkills([]));
    return () => ctrl.abort();
  }, [kind, version]);
  const choices = useMemo(() => (kind === 'skill' ? (entries ?? []) : skills), [kind, entries, skills]);
  const header = (
    <PageHeader
      eyebrow="The project's catalogues"
      title="Catalogues"
      subtitle="The strains and the other names papers give them, the products, Guild's skills and Primer's lessons this project keeps, each entry in its keeper's name. Every entry stays once kept, and keeping a file under an entry's id replaces it."
    />
  );
  if (!kind) {
    return (
      <div data-testid="catalogues">
        {header}
        <OwnerTabs tabs={CATALOGUE_TABS} />
        <Callout kind="warn">
          There is no catalogue at <span className="font-num">/catalogues/{view}</span>: the catalogues are the strains, the products, the skills and the
          lessons.
        </Callout>
      </div>
    );
  }
  const kw = KIND_WORDS[kind];
  return (
    <div data-testid="catalogues" data-kind={kind}>
      {header}
      <OwnerTabs tabs={CATALOGUE_TABS} />
      {problem && (
        <div className="mb-4">
          <Callout kind="warn">
            <span data-testid="catalogues-problem">{problem}</span>
          </Callout>
        </div>
      )}
      <div className="space-y-4">
        <Card className="p-4" data-testid="catalogues-held">
          <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
            <h2 className="font-serif text-section-title font-semibold">The {kw.many} the project keeps</h2>
            <Button size="sm" onClick={() => setEditing(blankEntry(kind))} disabled={entries === null} data-testid="catalogue-add">
              <Plus size={14} /> Add a {kw.one}
            </Button>
          </div>
          <p className="text-caption text-ink-soft mb-2">{kw.read}</p>
          {kept?.kind === kind && (
            <p className="text-caption mb-2" data-testid="catalogue-kept" data-entry={kept.id}>
              Kept <span className="font-num">{kept.id}</span> in {kept.by}&rsquo;s name.
            </p>
          )}
          {entries === null && !problem && <p className="text-body text-ink-soft">Reading the catalogue…</p>}
          {entries && entries.length === 0 && (
            <EmptyState icon={<BookMarked size={20} />} title={`No ${kw.one} yet`} body={`Add one with the button above, or take in a file of ${kw.many} below.`} />
          )}
          {entries && entries.length > 0 && (
            <table className="w-full text-caption">
              <thead>
                <tr className="border-b border-line text-ink-soft">
                  {['Id', 'Name', ...COLUMNS[kind], 'Kept', ''].map((h) => (
                    <th key={h} className="text-left py-1 pr-2 font-medium">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id} className="border-b border-line/50 align-top" data-testid="catalogue-entry" data-entry={e.id} data-agent={e.agent ?? 'person'}>
                    <td className="py-1 pr-2 font-num">{e.id}</td>
                    <td className="py-1 pr-2">
                      {e.name}
                      {e.summary && <span className="block text-ink-soft">{e.summary}</span>}
                    </td>
                    <Cells entry={e} />
                    <td className="py-1 pr-2">
                      {e.by || '—'}
                      <span className="block text-ink-soft">
                        {keptIn(e)}
                        {e.at ? `, ${stamp(e.at)}` : ''}
                      </span>
                      {e.source && <span className="block text-ink-soft">from {e.source}</span>}
                    </td>
                    <td className="py-1 pr-2">
                      <Button size="sm" onClick={() => setEditing(e)} data-testid="catalogue-edit">
                        <Pencil size={12} /> Edit
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
        {/* The form and the file each belong to the tab they were opened on: a tab of another kind starts afresh. */}
        {editing?.kind === kind && (
          <EntryForm
            key={`${kind}:${editing.id || 'new'}:${version}`}
            kind={kind}
            start={editing}
            skills={choices}
            onKept={(entry) => {
              setKept(entry);
              setEditing(null);
              reread();
            }}
            onDone={() => setEditing(null)}
          />
        )}
        <TakeInFile
          key={kind}
          kind={kind}
          onTaken={() => {
            // The line naming the last keep from the form gives way to the file's own result.
            setKept(null);
            reread();
          }}
        />
      </div>
    </div>
  );
}
