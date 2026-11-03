// One call to the service, with its two failures named.
//
// `ServiceDown`: nothing answered, or it answered with an error a person
// cannot act on here; the remedy names the command that starts the service.
// `ServiceRefused`: the service answered and said no, in words (a 404 with a
// reason, a 409, a 422, a 503). Nothing stands in for a result. Moved out of
// the retired passage-search client (lib/rag.ts) when Sci RAG Kit became the
// literature layer (alpha 2.0, ADR-002); every service client shares it.
import { START_COMMAND, postdocHealth } from './postdoc';
import { apiFetch } from './project';

export class ServiceDown extends Error {
  constructor(
    message: string,
    readonly remedy: string = `Start it with \`${START_COMMAND}\` from \`core/\`.`,
  ) {
    super(message);
    this.name = 'ServiceDown';
  }
}

/** The service answered and said no, in words. */
export class ServiceRefused extends Error {
  constructor(
    readonly status: number,
    why: string,
  ) {
    super(why);
    this.name = 'ServiceRefused';
  }
}

/**
 * A refusal's detail in words. The service's own words stand as they are. A
 * request whose fields the service refused answers a list of field errors
 * (FastAPI's 422, each with the field's place and why), said here field by
 * field; a field the service does not hold means this page was loaded before
 * the service changed, and the words say to reload it.
 */
export function detailWords(detail: unknown): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const fields = detail.map((d) => {
      const e = (d ?? {}) as { loc?: unknown; msg?: unknown };
      const where = Array.isArray(e.loc) ? e.loc.filter((x) => x !== 'body').join('.') : '';
      return `${where ? `${where}: ` : ''}${typeof e.msg === 'string' && e.msg ? e.msg : 'refused'}`;
    });
    const older = detail.some((d) => (d as { type?: unknown } | null)?.type === 'extra_forbidden');
    return (
      `The service refused the request's fields: ${fields.join('; ')}.` +
      (older ? ' This page was loaded before the service changed what it takes: reload the page.' : '')
    );
  }
  if (detail == null) return '';
  return typeof detail === 'object' ? JSON.stringify(detail) : String(detail);
}

export async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await apiFetch(path, init);
  } catch {
    throw new ServiceDown('The service is not running.');
  }
  if (response.ok) return (await response.json()) as T;
  // 413 is an upload past the size an import takes, 502 a source the service
  // could not fetch (an SFF reference file); like 404, a 502 is the service's
  // only when it says why, since a proxy in front of it answers 502 too.
  if ([404, 409, 413, 422, 502, 503].includes(response.status)) {
    let detail = '';
    try {
      detail = detailWords(((await response.json()) as { detail?: unknown }).detail);
    } catch {
      /* the status is the message */
    }
    if ((response.status !== 404 && response.status !== 502) || detail)
      throw new ServiceRefused(response.status, detail || `The service answered ${response.status}.`);
  }
  try {
    await postdocHealth(init?.signal ?? undefined);
  } catch {
    throw new ServiceDown('The service is not running.');
  }
  throw new ServiceDown(`The service answered ${response.status}.`, 'The service is running, so check its log — it will name what went wrong.');
}
