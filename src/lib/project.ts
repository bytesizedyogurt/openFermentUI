// The project this page acts in (alpha 2.0, ADR-005).
//
// Every record the service keeps belongs to one project, and every call to
// the service names the open one in the X-OpenFerment-Project header: the
// service answers in that project, and refuses a store call that names none.
// The page's address names the project it opens (`#/p/<id>/...`), and the id
// of the project last opened here is remembered (durable.ts) for an address
// that names none, so the first call after a reload already names it.
// Imports nothing of the service clients, which all import this.
import type { components } from '@/api/types.gen';
import { lastProject, rememberProject } from './durable';

/** A project the service holds (`GET /api/projects`): its id, name and description, and who made it and when. */
export type Project = components['schemas']['Project'];

export const PROJECT_HEADER = 'X-OpenFerment-Project';

const PREFIX = /^#?\/p\/([^/?]+)/;

/** The project the page's address names (`#/p/<id>/...`), or null. */
export function addressedProject(): string | null {
  if (typeof window === 'undefined') return null;
  const named = PREFIX.exec(window.location.hash);
  if (!named) return null;
  try {
    return decodeURIComponent(named[1]);
  } catch {
    return null;
  }
}

/**
 * The address that opens project `id` at the screen the address shows now: the
 * screen is kept, and a record or a query the address names is left, since
 * those are the open project's.
 */
export function projectAddress(id: string): string {
  const path = (typeof window === 'undefined' ? '' : window.location.hash.replace(/^#/, '')).split('?')[0];
  const segments = path.replace(PREFIX, '').split('/').filter(Boolean);
  return `#/p/${encodeURIComponent(id)}${segments[0] ? `/${segments[0]}` : ''}`;
}

// The page opens the project its address names, so a link, a reload and a
// choice of project land in it whether or not this browser can remember one;
// an address that names none opens the one this browser last opened.
const remembered = lastProject();
let open: string | null = addressedProject() ?? remembered;

// What acts in no project, and so need not wait for one (the service's UNSCOPED).
const UNSCOPED = ['/api/health', '/api/projects'];

// A page whose project is not the one this browser remembers learns from the
// project list (the store's loadProjects) which one it acts in: the address's
// when the service holds it, else the one remembered, else the only one held.
// Its first calls wait for that, so a screen that asks the service as it
// mounts names the project the page settles on. The remembered project, or a
// run outside a browser, settles at once.
let settle: () => void = () => {};
const settled: Promise<void> =
  (open !== null && open === remembered) || typeof window === 'undefined'
    ? Promise.resolve()
    : new Promise((done) => (settle = done));

/** The project list has been read (or could not be): calls waiting for the open project go. */
export function projectSettled(): void {
  settle();
}

/** The open project's id, or null when none is open. */
export function openProjectId(): string | null {
  return open;
}

/** Open `id` (null closes it) and remember it in this browser. */
export function setOpenProjectId(id: string | null): void {
  open = id;
  rememberProject(id);
}

/** `init` with the open project named, unless the caller named one. */
function withProject(init: RequestInit = {}): RequestInit {
  if (!open) return init;
  const headers = new Headers(init.headers);
  if (!headers.has(PROJECT_HEADER)) headers.set(PROJECT_HEADER, open);
  return { ...init, headers };
}

/** `fetch`, naming the open project once the page has settled on one. */
export async function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  if (!UNSCOPED.some((path) => input.startsWith(path))) await settled;
  return fetch(input, withProject(init));
}
