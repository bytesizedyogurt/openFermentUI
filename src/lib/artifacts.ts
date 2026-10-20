// The browser's side of BioRepo's artifact store (OF-BLD-014 §3.2, E.5).
//
// Three calls: list what the service computed, read one, replay one. Same
// discipline as lib/intake.ts: when the service is unreachable this says so
// and names the command that starts it, and it never shows stand-in data in
// the service's place (E.2).
import type { Artifact, ReplayResult } from '@/data/types';
import { START_COMMAND, postdocHealth } from './postdoc';
import { isArchived, programOfPaperId } from '@/data/programs';
import type { ProgramId } from '@/data/types';
import { programOf, type ProgramLookup } from '@/store';

export class ArtifactsDown extends Error {
  constructor(
    message: string,
    readonly remedy: string = `Start it with \`${START_COMMAND}\` from \`core/\`.`,
  ) {
    super(message);
    this.name = 'ArtifactsDown';
  }
}

/** The service answered, and said no: an unknown id, or a tool it cannot replay. */
export class ArtifactRefused extends Error {
  constructor(
    readonly status: number,
    why: string,
  ) {
    super(why);
    this.name = 'ArtifactRefused';
  }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ArtifactsDown('The service is not running.');
  }
  if (response.ok) return (await response.json()) as T;
  if (response.status === 404 || response.status === 409) {
    let detail = '';
    try {
      detail = String(((await response.json()) as { detail?: string }).detail ?? '');
    } catch {
      /* the status is the message */
    }
    throw new ArtifactRefused(response.status, detail || `The service answered ${response.status}.`);
  }
  // The dev proxy answers 500 when nothing is behind it; ask health which it was.
  try {
    await postdocHealth(init?.signal ?? undefined);
  } catch {
    throw new ArtifactsDown('The service is not running.');
  }
  throw new ArtifactsDown(
    `The service answered ${response.status}.`,
    'The service is running, so check its log — it will name what went wrong.',
  );
}

/**
 * What the service kept. It leaves out an artifact computed from an archived
 * program's inputs unless the program switch asks for them (OF-BLD-016 §2.R),
 * so the switch rides along; the browser filters again with `visibleArtifacts`.
 */
export const listArtifacts = (signal?: AbortSignal, includeArchived = false) =>
  call<Artifact[]>(`/api/biorepo/artifacts${includeArchived ? '?includeArchived=true' : ''}`, { signal });

// A paper id inside a record's or a candidate's id: `r-B5-3`, `cl1-P12-…`.
const PAPER_IN_ID = /(?:^|-)([A-Z]\d+)(?=-|$)/;

/**
 * A computed artifact's program, from what its basis names: a record (by the
 * paper it cites, or the paper id a candidate's id carries), a product or a
 * strain (by their own field). An archived program among them wins, so a
 * value computed from casein or PHA inputs hides with them; anything else is
 * general (a benchmark, a fit of a deposition). The rule
 * `programs.program_of_artifact` applies in the service, read from the
 * browser's own lists.
 */
export function programOfArtifact(a: Artifact, s: ProgramLookup = {}): ProgramId | null {
  const found: ProgramId[] = [];
  for (const i of a.inputs ?? []) {
    if (i.source?.kind === 'record' && i.source.id) {
      const m = PAPER_IN_ID.exec(i.source.id);
      const p = programOf('record', i.source.id, s) ?? (m ? programOfPaperId(m[1]) : null);
      if (p) found.push(p);
    }
    if (typeof i.value === 'string' && (i.name === 'product' || i.name === 'productId')) {
      const p = programOf('product', i.value, s);
      if (p) found.push(p);
    }
    if (typeof i.value === 'string' && (i.name === 'strain' || i.name === 'strainId' || i.name === 'host')) {
      const p = programOf('strain', i.value, s);
      if (p) found.push(p);
    }
  }
  return found.find((p) => isArchived(p)) ?? found[0] ?? null;
}

/** The artifacts that show under the program switch. */
export function visibleArtifacts(all: Artifact[], s: ProgramLookup & { showArchived: boolean }): Artifact[] {
  return s.showArchived ? all : all.filter((a) => !isArchived(programOfArtifact(a, s)));
}

export const getArtifact = (id: string, signal?: AbortSignal) =>
  call<Artifact>(`/api/biorepo/artifacts/${encodeURIComponent(id)}`, { signal });

export const replayArtifact = (id: string) =>
  call<ReplayResult>(`/api/biorepo/artifacts/${encodeURIComponent(id)}/replay`, { method: 'POST' });

/**
 * What a table shows for an artifact's value. A tool's output is its own
 * shape; by convention a tool puts the value a person reads first under
 * `label`, `value` and `unit`, and an output without them shows none.
 */
export function headline(a: Artifact): { label: string | null; value: string | null; unit: string } {
  const o = a.output ?? {};
  const label = typeof o.label === 'string' ? o.label : null;
  const v = o.value;
  const value = typeof v === 'number' || typeof v === 'string' ? String(v) : null;
  const unit = typeof o.unit === 'string' ? o.unit : '';
  return { label, value, unit };
}
