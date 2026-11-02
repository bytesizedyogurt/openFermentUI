// The project's event stream (execution prompt §7.3 item 2; core/openferment_core/events.py).
//
// Every worker job, tool call, artifact and Postdoc turn says what happened as
// it happens, on `GET /api/events?project=`; a page renders a card for each at
// once (components/TraceCards.tsx). An EventSource sends no header, so the
// project is named in the address. It reconnects by itself and sends the last
// id it read, so a page is sent what it missed while the service holds it; a
// page that opens the stream is sent what happens from then on, and reads the
// record from the tables.

export type EventType =
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

export const EVENT_TYPES: readonly EventType[] = [
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

/**
 * Open the project's stream: `onEvent` is called with each event as it
 * arrives, `onOpen` with whether the stream is open now. Returns the function
 * that closes it. Outside a browser it opens nothing.
 */
export function watchEvents(
  project: string,
  onEvent: (e: ServiceEvent) => void,
  onOpen?: (open: boolean) => void,
): () => void {
  if (typeof EventSource === 'undefined') return () => undefined;
  const source = new EventSource(`/api/events?project=${encodeURIComponent(project)}`);
  const handle = (m: MessageEvent<string>) => {
    try {
      onEvent(JSON.parse(m.data) as ServiceEvent);
    } catch {
      // A line that is not an event says nothing.
    }
  };
  for (const t of EVENT_TYPES) source.addEventListener(t, handle as EventListener);
  source.onopen = () => onOpen?.(true);
  source.onerror = () => onOpen?.(false);
  return () => source.close();
}
