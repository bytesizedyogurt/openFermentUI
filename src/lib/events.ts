// The project's event stream (execution prompt §7.3 item 2; core/openferment_core/events.py).
//
// Every worker job, tool call, artifact and Postdoc turn says what happened as
// it happens, on `GET /api/events?project=`; a page renders a card for each at
// once (components/TraceCards.tsx). An EventSource sends no header, so the
// project is named in the address. It reconnects by itself and sends the last
// id it read, so a page is sent what it missed while the service holds it; a
// page that opens the stream is sent what happens from then on, and reads the
// record from the tables.

type EventType =
  | 'job.queued'
  | 'job.running'
  | 'job.done'
  | 'job.failed'
  | 'tool.call'
  | 'tool.result'
  | 'artifact.kept'
  | 'turn.started'
  | 'turn.delta'
  | 'turn.plan'
  | 'turn.decline';

const EVENT_TYPES: readonly EventType[] = [
  'job.queued',
  'job.running',
  'job.done',
  'job.failed',
  'tool.call',
  'tool.result',
  'artifact.kept',
  'turn.started',
  'turn.delta',
  'turn.plan',
  'turn.decline',
];

/** One event as the service sends it (events.Event). */
export interface ServiceEvent {
  id: number;
  type: EventType;
  at: string;
  project: string;
  data: Record<string, unknown>;
}

/** One page's reader of a project's stream: what it is told of each event and of the stream's state. */
interface Reader {
  onEvent: (e: ServiceEvent) => void;
  onOpen?: (open: boolean) => void;
}

/**
 * A project's one stream on this page, shared by every reader: the store's
 * jobs tray and Home's trace cards read the same EventSource. The service is
 * plain HTTP/1.1, where a browser keeps six connections to one address across
 * all its tabs, and an open stream holds one of them for as long as it is
 * open; a stream a tab kept per reader, and kept while hidden, filled that pool
 * with six of them, and then every request of every tab waited with no word.
 * So a page holds one stream a project, and none while it is hidden: it closes
 * as the tab is hidden and opens again as it is shown, from the last event it
 * read (`?after=`), so what happened meanwhile still arrives while the service
 * holds it.
 */
interface Shared {
  readers: Set<Reader>;
  source: EventSource | null;
  last: number | null;
  open: boolean;
}

const shared = new Map<string, Shared>();
const watched = new WeakSet<object>();

function hidden(): boolean {
  return typeof document !== 'undefined' && document.visibilityState === 'hidden';
}

function tell(s: Shared, open: boolean): void {
  if (s.open === open) return;
  s.open = open;
  for (const r of [...s.readers]) r.onOpen?.(open);
}

function connect(project: string, s: Shared): void {
  if (s.source || hidden() || typeof EventSource === 'undefined') return;
  const at = `/api/events?project=${encodeURIComponent(project)}`;
  const source = new EventSource(s.last === null ? at : `${at}&after=${s.last}`);
  s.source = source;
  const handle = (m: MessageEvent<string>) => {
    let e: ServiceEvent;
    try {
      e = JSON.parse(m.data) as ServiceEvent;
    } catch {
      return; // A line that is not an event says nothing.
    }
    if (typeof e.id === 'number') {
      if (s.last !== null && e.id <= s.last) return; // read already, before the stream opened again
      s.last = e.id;
    }
    for (const r of [...s.readers]) r.onEvent(e);
  };
  for (const t of EVENT_TYPES) source.addEventListener(t, handle as EventListener);
  source.onopen = () => tell(s, true);
  source.onerror = () => tell(s, false);
}

function disconnect(s: Shared): void {
  s.source?.close();
  s.source = null;
  tell(s, false);
}

function watchVisibility(): void {
  if (typeof document === 'undefined' || watched.has(document)) return;
  watched.add(document);
  document.addEventListener('visibilitychange', () => {
    for (const [project, s] of shared) {
      if (hidden()) disconnect(s);
      else connect(project, s);
    }
  });
}

/**
 * Read the project's stream: `onEvent` is called with each event as it
 * arrives, `onOpen` with whether the stream is open now. Returns the function
 * that stops this reader; the page's stream closes when its last reader
 * stops. Outside a browser it opens nothing.
 */
export function watchEvents(
  project: string,
  onEvent: (e: ServiceEvent) => void,
  onOpen?: (open: boolean) => void,
): () => void {
  if (typeof EventSource === 'undefined') return () => undefined;
  watchVisibility();
  let s = shared.get(project);
  if (!s) {
    s = { readers: new Set(), source: null, last: null, open: false };
    shared.set(project, s);
  }
  const reader: Reader = { onEvent, onOpen };
  s.readers.add(reader);
  if (s.open) onOpen?.(true);
  connect(project, s);
  const mine = s;
  return () => {
    mine.readers.delete(reader);
    if (mine.readers.size === 0) {
      disconnect(mine);
      if (shared.get(project) === mine) shared.delete(project);
    }
  };
}
