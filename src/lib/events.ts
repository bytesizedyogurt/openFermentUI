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
 * A project's one stream, shared by every reader on the page and by every tab
 * of the app. The service is plain HTTP/1.1, where a browser keeps six
 * connections to one address across all its tabs, and an open stream holds
 * one of them for as long as it is open; once streams fill that pool, every
 * request of every tab waits with no word (bug hunt round 2, the jobs tray).
 *
 * So one tab holds the project's stream for the whole browser: the tab that
 * holds the Web Lock named for the project opens the EventSource and passes
 * each event to the other tabs on a BroadcastChannel of the same name. When
 * that tab closes, the lock passes to a waiting tab, which opens the stream
 * from the last event it heard (`?after=`), so nothing is missed while the
 * service holds it. A browser without Web Locks or BroadcastChannel holds one
 * stream a page, closed while the page is hidden and opened again, from the
 * last event read, when it is shown.
 */
interface Shared {
  readers: Set<Reader>;
  source: EventSource | null;
  last: number | null;
  open: boolean;
  /** The tabs' channel, and whether this tab holds the lock (shared mode). */
  channel: BroadcastChannel | null;
  leading: boolean;
  release: (() => void) | null;
  waiting: AbortController | null;
}

type Relay = { type: 'event'; event: ServiceEvent } | { type: 'open'; open: boolean } | { type: 'hello' };

const shared = new Map<string, Shared>();
const watched = new WeakSet<object>();
const NAME = (project: string) => `openferment-events:${project}`;

function canShare(): boolean {
  return (
    typeof BroadcastChannel !== 'undefined' &&
    typeof navigator !== 'undefined' &&
    typeof (navigator as Navigator & { locks?: LockManager }).locks?.request === 'function'
  );
}

function hidden(): boolean {
  return typeof document !== 'undefined' && document.visibilityState === 'hidden';
}

function tell(s: Shared, open: boolean): void {
  if (s.open === open) return;
  s.open = open;
  for (const r of [...s.readers]) r.onOpen?.(open);
}

/** An event to this page's readers, once: one heard again after the stream opened again is dropped. */
function deliver(s: Shared, e: ServiceEvent): void {
  if (typeof e.id === 'number') {
    if (s.last !== null && e.id <= s.last) return;
    s.last = e.id;
  }
  for (const r of [...s.readers]) r.onEvent(e);
}

function connect(project: string, s: Shared): void {
  if (s.source || typeof EventSource === 'undefined') return;
  if (!s.channel && hidden()) return;
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
    const fresh = s.last === null || typeof e.id !== 'number' || e.id > s.last;
    deliver(s, e);
    if (fresh) s.channel?.postMessage({ type: 'event', event: e } satisfies Relay);
  };
  for (const t of EVENT_TYPES) source.addEventListener(t, handle as EventListener);
  const say = (open: boolean) => {
    tell(s, open);
    s.channel?.postMessage({ type: 'open', open } satisfies Relay);
  };
  source.onopen = () => say(true);
  source.onerror = () => say(false);
}

function disconnect(s: Shared): void {
  s.source?.close();
  s.source = null;
  tell(s, false);
}

/** Join the tabs' channel and wait for the project's lock; holding it, this tab opens the stream. */
function share(project: string, s: Shared): void {
  const channel = new BroadcastChannel(NAME(project));
  s.channel = channel;
  channel.onmessage = (m: MessageEvent<Relay>) => {
    const d = m.data;
    if (d?.type === 'event') deliver(s, d.event);
    else if (d?.type === 'open' && !s.leading) tell(s, d.open);
    else if (d?.type === 'hello' && s.leading) channel.postMessage({ type: 'open', open: s.open } satisfies Relay);
  };
  const waiting = new AbortController();
  s.waiting = waiting;
  const locks = (navigator as Navigator & { locks: LockManager }).locks;
  locks
    .request(NAME(project), { signal: waiting.signal }, () => {
      if (shared.get(project) !== s) return undefined;
      s.waiting = null;
      s.leading = true;
      connect(project, s);
      return new Promise<void>((resolve) => {
        s.release = resolve;
      });
    })
    .catch(() => undefined); // an abandoned wait: the page stopped reading
  channel.postMessage({ type: 'hello' } satisfies Relay);
}

function watchVisibility(): void {
  if (typeof document === 'undefined' || watched.has(document)) return;
  watched.add(document);
  document.addEventListener('visibilitychange', () => {
    for (const [project, s] of shared) {
      if (s.channel) continue; // the shared stream stays with the tab that holds the lock
      if (hidden()) disconnect(s);
      else connect(project, s);
    }
  });
}

/**
 * Read the project's stream: `onEvent` is called with each event as it
 * arrives, `onOpen` with whether the stream is open now. Returns the function
 * that stops this reader; the page leaves the stream when its last reader
 * stops. Outside a browser it opens nothing.
 */
export function watchEvents(
  project: string,
  onEvent: (e: ServiceEvent) => void,
  onOpen?: (open: boolean) => void,
): () => void {
  if (typeof EventSource === 'undefined') return () => undefined;
  let s = shared.get(project);
  if (!s) {
    s = { readers: new Set(), source: null, last: null, open: false, channel: null, leading: false, release: null, waiting: null };
    shared.set(project, s);
    if (canShare()) share(project, s);
    else watchVisibility();
  }
  const reader: Reader = { onEvent, onOpen };
  s.readers.add(reader);
  if (s.open) onOpen?.(true);
  if (!s.channel) connect(project, s);
  const mine = s;
  return () => {
    mine.readers.delete(reader);
    if (mine.readers.size > 0) return;
    disconnect(mine);
    mine.waiting?.abort();
    mine.release?.();
    mine.channel?.close();
    if (shared.get(project) === mine) shared.delete(project);
  };
}
