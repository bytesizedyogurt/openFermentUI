// Guided tour / demo autopilot (OF-DES-001 §8.1, §19 fallback narrator).
// Six stops that walk the golden path; doubles as the contingency if a live
// demo goes sideways.
//
// It is also the first place a new reader meets the vocabulary, so every stop
// names the surface it is standing on. Six stops is six names learned in
// context — which is the only way a coined word ever sticks.
import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ArrowRight, ArrowLeft, X } from 'lucide-react';
import { useStore } from '@/store';
import { navigate } from '@/router';

interface Stop {
  route: string;
  /** The surface this stop is standing on, named. */
  surface: string;
  title: string;
  body: string;
}

const STOPS: Stop[] = [
  {
    route: '/',
    surface: 'Home',
    title: 'Corpus vitals',
    body: 'Home answers three questions in five seconds: what is in the corpus, what needs your attention, and where you left off. Every tile is ticked by the provenance of the data behind it, and clicks through to its home screen.',
  },
  {
    route: '/postdoc',
    surface: 'Postdoc',
    title: 'Ask, with the work shown',
    body: 'Postdoc is the thing you talk to. Its plan, tool calls, and retrieved passages are first-class UI — collapsed by default, never hidden. Every number in an answer carries a citation chip that resolves to a source span in two interactions.',
  },
  {
    route: '/biorepo/papers/SP-002',
    surface: 'BioRepo',
    title: 'Evidence in context',
    body: 'BioRepo is the corpus and everything retrieved from it. A chip’s promise is kept here: the span is highlighted in the source, and the right rail lists every extraction anchored to this paper. Hovering either side previews the other; clicking commits the scroll.',
  },
  {
    route: '/guild',
    surface: 'Guild',
    title: 'Human-in-the-loop',
    body: 'The Guild of Applied Life is who may verify. Reviewers triage by keyboard: a accept, r reject, e edit, g flag for gold, u undo. Every decision lands in the record’s audit trail immediately — and propagates to the strain pages and to Witness.',
  },
  {
    route: '/protocols/PR-TAP-01',
    surface: 'Protocols',
    title: 'Verified numbers become procedures',
    body: 'Scaling is real arithmetic: change the batch size and every bound quantity, stock volume, and materials row recomputes, rounded to each material’s precision so the recipe stays pipettable. Deposition then executes it at the bench.',
  },
  {
    route: '/witness',
    surface: 'Witness',
    title: 'How we know, and how we’re honest when we’re wrong',
    body: 'Witness asks whether it reproduces. No extractor has been run against this corpus, so this screen shows no precision, recall or F1 — it shows the gold-set plan those numbers would be earned against, the six cases chosen to be hard, and the real values the ontology has no field for. Refusing to display a metric it has not earned is the point of the screen.',
  },
];

export function GuidedTour() {
  const stop = useStore((s) => s.ui.tourStop);
  const setUI = useStore((s) => s.setUI);

  useEffect(() => {
    if (stop === null) return;
    navigate(STOPS[stop].route);
  }, [stop]);

  useEffect(() => {
    if (stop === null) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setUI({ tourStop: null });
      if (e.key === 'ArrowRight')
        setUI({ tourStop: stop + 1 >= STOPS.length ? null : stop + 1 });
      if (e.key === 'ArrowLeft' && stop > 0) setUI({ tourStop: stop - 1 });
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [stop, setUI]);

  if (stop === null) return null;
  const s = STOPS[stop];

  return createPortal(
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[75] w-[min(560px,calc(100vw-32px))]">
      <div className="overlay rounded-card p-4 anim-in">
        <div className="flex items-start justify-between gap-3 mb-1">
          <div className="text-caption uppercase tracking-wide text-ink-soft">
            Guided tour · stop {stop + 1} of {STOPS.length}
            <span className="text-ink-soft/60"> · </span>
            <span className="font-num normal-case tracking-normal text-ink">{s.surface}</span>
          </div>
          <button
            className="text-ink-soft hover:text-ink"
            onClick={() => setUI({ tourStop: null })}
            aria-label="End tour"
          >
            <X size={14} />
          </button>
        </div>
        <div className="font-serif text-section-title font-semibold mb-1">{s.title}</div>
        <p className="text-body text-ink-soft leading-relaxed mb-3">{s.body}</p>
        <div className="flex items-center gap-2">
          <div className="flex gap-1 flex-1">
            {STOPS.map((_, i) => (
              <button
                key={i}
                onClick={() => setUI({ tourStop: i })}
                className={`h-1.5 flex-1 rounded-full ${i <= stop ? 'bg-accent' : 'bg-ink-soft/20'}`}
                aria-label={`Go to stop ${i + 1}`}
              />
            ))}
          </div>
          <button className="btn btn-sm" disabled={stop === 0} onClick={() => setUI({ tourStop: stop - 1 })}>
            <ArrowLeft size={12} /> Back
          </button>
          <button
            className="btn btn-sm btn-primary"
            onClick={() => setUI({ tourStop: stop + 1 >= STOPS.length ? null : stop + 1 })}
          >
            {stop + 1 >= STOPS.length ? 'Finish' : 'Next'} <ArrowRight size={12} />
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
