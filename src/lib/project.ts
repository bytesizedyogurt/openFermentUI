// The project this page acts in (alpha 2.0, ADR-005).
//
// Every record the service keeps belongs to one project, and every call to
// the service names the open one in the X-OpenFerment-Project header: the
// service answers in that project, and refuses a store call that names none.
// The id of the project last opened here is remembered (durable.ts), so the
// first call after a reload already names it. Imports nothing of the service
// clients, which all import this.
import { lastProject, rememberProject } from './durable';

export const PROJECT_HEADER = 'X-OpenFerment-Project';

let open: string | null = lastProject();

// What acts in no project, and so need not wait for one (the service's UNSCOPED).
const UNSCOPED = ['/api/health', '/api/projects'];

// A page that remembers no project learns which one is open from the
// project list (the store's loadProjects, which opens the only one held).
// Its first calls wait for that, so a screen that asks the service as it
// mounts names the project the page settles on. A remembered project, or a
// run outside a browser, settles at once.
let settle: () => void = () => {};
const settled: Promise<void> =
  open !== null || typeof window === 'undefined' ? Promise.resolve() : new Promise((done) => (settle = done));

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
export function withProject(init: RequestInit = {}): RequestInit {
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
