// One call to the service, with its two failures named.
//
// `ServiceDown`: nothing answered, or it answered with an error a person
// cannot act on here; the remedy names the command that starts the service.
// `ServiceRefused`: the service answered and said no, in words (a 404 with a
// reason, a 409, a 422, a 503). Nothing stands in for a result. Moved out of
// the retired passage-search client (lib/rag.ts) when Sci RAG Kit became the
// literature layer (alpha 2.0, ADR-002); every service client shares it.
import { START_COMMAND, postdocHealth } from './postdoc';

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

export async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ServiceDown('The service is not running.');
  }
  if (response.ok) return (await response.json()) as T;
  if ([404, 409, 422, 503].includes(response.status)) {
    let detail = '';
    try {
      detail = String(((await response.json()) as { detail?: unknown }).detail ?? '');
    } catch {
      /* the status is the message */
    }
    if (response.status !== 404 || detail) throw new ServiceRefused(response.status, detail || `The service answered ${response.status}.`);
  }
  try {
    await postdocHealth(init?.signal ?? undefined);
  } catch {
    throw new ServiceDown('The service is not running.');
  }
  throw new ServiceDown(`The service answered ${response.status}.`, 'The service is running, so check its log — it will name what went wrong.');
}
