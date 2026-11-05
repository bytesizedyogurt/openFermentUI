// A project's catalogues, the browser's side (alpha 2.2 E.8; core/openferment_core/catalogues.py):
//
//   GET  /api/catalogues/{kind}          the entries of one catalogue (strain, product, skill, lesson), by id
//   GET  /api/catalogues/{kind}/{id}     one entry, with who kept it, in which lane, when and from where
//   POST /api/catalogues/{kind}          one entry kept in a person's name, an entry under its id replaced
//   POST /api/intake/catalogue           a file of entries of one kind, JSON or CSV, every row kept or refused
//
// The catalogues screen (/catalogues) lists, adds and edits entries through these, each keep in the name Settings
// holds. The service decides what an entry may hold: it refuses, in words, a field its kind does not take, a
// product's class outside the twelve pureOS's proposer reads, a skill's policy with a part left out, and a keep
// that names nobody. With the service down a call says so (ServiceDown); a refusal comes back in the service's
// words (ServiceRefused). Nothing here takes an entry out.
//
// The store reads the project's strains and products through `listStrains` and `listProducts` (alpha 2.2 E.9):
// geneOS's hosts and their pages, the strain choosers of fermOS and pureOS, the runbooks and the protocols name a
// strain as its entry does, and a product likewise. It reads the skills and the lessons through `listSkills` and
// `listLessons` (alpha 2.2 E.12): Guild rates people on the skills its catalogue keeps, a protocol's step names
// them, and Primer teaches the lessons, each with its body (ADR-018).
//
// Every shape here is the service's own, generated from its models into src/api/types.gen.ts (ADR-007). The keep's
// body is the entry as the catalogue answers one (`CatalogueKeep.entry`), so the generated entry names every field
// with a default as one a reader may find absent.
import type { components } from '@/api/types.gen';
import { ServiceDown, ServiceRefused, call } from './http';

type S = components['schemas'];

/** One entry of a project's catalogue; the fields a kind does not use stay empty. */
export type CatalogueEntry = S['CatalogueEntry'];
/** Which catalogue: strain, product, skill or lesson. */
export type CatalogueKind = CatalogueEntry['kind'];
/** POST /api/catalogues/{kind}: one entry and who keeps it. */
export type CatalogueKeep = S['CatalogueKeep'];
/** What a file of entries came to: the ids kept, and each row refused with why. */
export type CatalogueIntake = S['CatalogueIntake'];
/** A product's class, one of those pureOS's proposer reads. */
export type ProductCategory = NonNullable<CatalogueEntry['category']>;
/** Where the cells leave a product: secreted, or kept inside them. */
export type ProductLocation = NonNullable<CatalogueEntry['location']>;
/** A skill's criticality: a critical skill is one where a mistake hurts a person or loses a batch. */
export type SkillCriticality = NonNullable<CatalogueEntry['criticality']>;
/** A strain the project works with, as its strain catalogue keeps it: its name, species, chemical set and other names. */
export type Strain = CatalogueEntry & { kind: 'strain' };
/** A product the project works with, as its product catalogue keeps it: its name, class, location and sequence. */
export type Product = CatalogueEntry & { kind: 'product' };
/**
 * A skill Guild rates people on, as the project's skill catalogue keeps it: its family, its summary, what an assessor
 * watches for, and the policy its levels read (criticality, recency, supervised runs, prerequisites). An entry kept
 * with no policy rates nobody (`hasPolicy`; competence.unrated on the service, `rated` in src/engine/competence.ts).
 */
export type Skill = CatalogueEntry & { kind: 'skill' };
/**
 * A lesson Primer teaches, as the project's lesson catalogue keeps it: its name, its words, the skills it counts
 * toward, and its body (ADR-018): its minutes, its blocks and its checkpoint. A lesson kept with no body shows its
 * name, its words and its skills.
 */
export type Lesson = CatalogueEntry & { kind: 'lesson' };
/** One block of a lesson's body: prose in Markdown, or one of the nine embeds Primer's page draws. */
export type LessonBlock = S['LessonProse'] | S['LessonEmbed'];
/** Which embed a block draws: the nine Primer's page knows. */
export type LessonEmbedName = S['LessonEmbed']['embed'];
/**
 * One question of a lesson's checkpoint: a multiple-choice question with its options and the index of its answer, or a
 * numeric one with its answer's value, unit and tolerance in percent.
 */
export type CheckpointQuestion = S['CheckpointQuestion'];

export { ServiceDown as CataloguesDown, ServiceRefused as CataloguesRefused };

/** The four catalogues, in the order the screen shows them. */
export const KINDS: CatalogueKind[] = ['strain', 'product', 'skill', 'lesson'];

const id = (s: string) => encodeURIComponent(s);

/** The open project's entries of one catalogue, by id. */
export const listCatalogue = (kind: CatalogueKind, signal?: AbortSignal) =>
  call<CatalogueEntry[]>(`/api/catalogues/${kind}`, { signal });

/** The open project's strains, as its strain catalogue keeps them. */
export const listStrains = (signal?: AbortSignal) =>
  listCatalogue('strain', signal).then((entries) => entries.filter((e): e is Strain => e.kind === 'strain'));

/** The open project's products, as its product catalogue keeps them. */
export const listProducts = (signal?: AbortSignal) =>
  listCatalogue('product', signal).then((entries) => entries.filter((e): e is Product => e.kind === 'product'));

/** The open project's skills, as its skill catalogue keeps them. */
export const listSkills = (signal?: AbortSignal) =>
  listCatalogue('skill', signal).then((entries) => entries.filter((e): e is Skill => e.kind === 'skill'));

/** The open project's lessons, as its lesson catalogue keeps them, each with its body. */
export const listLessons = (signal?: AbortSignal) =>
  listCatalogue('lesson', signal).then((entries) => entries.filter((e): e is Lesson => e.kind === 'lesson'));

/** A strain in words, as a chooser or a label names it: its species, where its entry keeps one, then its name. */
export const strainWords = (s: Pick<CatalogueEntry, 'name' | 'species'>): string => [s.species, s.name].filter(Boolean).join(' ');

/** One entry of the open project's catalogue of `kind`. */
export const catalogueEntry = (kind: CatalogueKind, entryId: string, signal?: AbortSignal) =>
  call<CatalogueEntry>(`/api/catalogues/${kind}/${id(entryId)}`, { signal });

/**
 * One entry kept in the catalogue of its kind in `by`'s name, as a person's keep: an entry under its id is replaced,
 * whoever kept it. The service writes the keeper, the lane, the door and the time over what the entry sends.
 */
export const keepEntry = (asked: CatalogueKeep) =>
  call<CatalogueEntry>(`/api/catalogues/${asked.entry.kind}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(asked),
  });

/**
 * A file of entries of one kind taken in, JSON (a list of objects, or one under `entries`) or CSV (with `id` and
 * `name` columns, a list's items split by `;`), in `by`'s name: every row that is an entry is kept with the file as
 * its source, and every other row is refused with its reason.
 */
export function takeInCatalogue(kind: CatalogueKind, file: File, by: string): Promise<CatalogueIntake> {
  const form = new FormData();
  form.append('kind', kind);
  form.append('by', by);
  form.append('file', file);
  return call<CatalogueIntake>('/api/intake/catalogue', { method: 'POST', body: form });
}

/** An empty entry of `kind`, as the screen begins one. */
export function blankEntry(kind: CatalogueKind): CatalogueEntry {
  return { kind, id: '', name: '', by: '', at: '' };
}

/** Whose lane an entry was kept in, in words: a person's keep, or a model's write through the door it came in by. */
export function keptIn(entry: CatalogueEntry): string {
  if (entry.agent !== 'model') return 'a person’s keep';
  if (entry.via === 'mcp') return 'a model’s write, over MCP';
  if (entry.via === 'http') return 'a model’s write, at the HTTP endpoint';
  return 'Postdoc’s write';
}

/** Whether a skill's entry holds its policy, which Guild's levels read; Guild rates nobody on a skill with none. */
export const hasPolicy = (entry: CatalogueEntry): boolean =>
  entry.criticality != null && entry.recencyDays != null && entry.supervisedRuns != null;
