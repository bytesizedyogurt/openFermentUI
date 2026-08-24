// The component architecture, made visible (OF-BLD-006 §2).
//
// The eighteen names and seven layers previously existed only in COMPONENTS.md
// and in attribution tags scattered a few pixels high. That is enough for
// building the system and not enough for reading it, so this screen renders
// the architecture as the thing it actually is: a pipeline with a direction,
// seven components not yet built, and one layer where the arrow reverses.
//
// It does NOT rename anything. The rail still says Ask, Extract, Simulate —
// §2.2 is explicit that a user hunting a chat interface should find "Ask", and
// a reference screen is not an excuse to relitigate that. Each component says
// which nav label it sits under, which is the mapping a reader actually needs.
import { ArrowDown, CircleDashed, FileCode2 } from 'lucide-react';
import {
  COMPONENTS,
  FULL_NAME,
  LAYERS,
  componentsInLayer,
  isBuilt,
  type ComponentDef,
} from '@/data/components';
import { COMPONENT_ROLE } from '@/components/ComponentTag';
import { Callout, Card, Explain, PageHeader, SectionTitle, cx } from '@/components/ui';

function ComponentRow({ c }: { c: ComponentDef }) {
  const built = isBuilt(c);
  return (
    <li
      className={cx(
        'py-2.5 border-b border-line/70 last:border-0',
        !built && 'opacity-70',
      )}
    >
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <span
          className={cx('font-num text-body', built ? 'text-ink' : 'text-ink-soft')}
          title={COMPONENT_ROLE[c.name]}
        >
          {FULL_NAME[c.name] ?? c.name}
        </span>
        {c.surfacedAs ? (
          <span className="text-caption text-ink-soft">
            reached through <span className="text-ink">{c.surfacedAs}</span>
          </span>
        ) : (
          <span className="chip text-ink-soft text-[11px] py-0 inline-flex items-center gap-1">
            <CircleDashed size={11} aria-hidden />
            not built
          </span>
        )}
      </div>
      <div className="text-body text-ink-soft mt-0.5">{c.role}</div>
      {built && (
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
          {c.livesIn.map((path) => (
            <span
              key={path}
              className="font-num text-caption text-ink-soft inline-flex items-center gap-1"
            >
              <FileCode2 size={11} aria-hidden />
              {path}
            </span>
          ))}
        </div>
      )}
    </li>
  );
}

export default function Architecture() {
  const built = COMPONENTS.filter(isBuilt).length;

  return (
    <>
      <PageHeader
        eyebrow="Settings · Architecture"
        title="Components"
        subtitle="Eighteen named components in seven layers. This is the architecture the system is built from — not a menu, and deliberately not the nav rail."
      />

      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 mb-4 text-caption text-ink-soft">
        <span>
          <span className="font-num text-ink">{COMPONENTS.length}</span> components
        </span>
        <span>
          <span className="font-num text-accent">{built}</span> built ·{' '}
          <span className="font-num text-ink">{COMPONENTS.length - built}</span> named but not built
        </span>
        <span>
          <span className="font-num text-ink">{LAYERS.length}</span> layers
        </span>
        <span className="inline-flex items-center gap-1">
          Why the rail does not say these
          <Explain label="Why nav labels are not component names">
            Because the names are for building the system, not for navigating it. Somebody looking
            for a chat interface types &ldquo;Ask&rdquo;; renaming that button to
            &ldquo;Postdoc&rdquo; would make the product worse in exchange for making the
            architecture louder. The names surface in three places instead: the module a
            component&rsquo;s code lives in, an attribution tag beside work it performed, and this
            table.
          </Explain>
        </span>
      </div>

      <Callout
        kind="info"
        title={`${COMPONENTS.length - built} of these are names with nothing under them`}
      >
        That is on purpose, and it is why the empty rows are here rather than omitted. A name with
        no code behind it is a smaller problem than a system with no name for the thing it is
        missing — <span className="font-num">geneOS</span> and{' '}
        <span className="font-num">fermOS</span> are the two largest holes in the platform, and
        leaving them off this page would make it look complete.
      </Callout>

      <div className="mt-5 space-y-5">
        {LAYERS.map((layer, i) => {
          const items = componentsInLayer(layer.id);
          const layerBuilt = items.filter(isBuilt).length;
          return (
            <section key={layer.id} aria-labelledby={`layer-${i}`}>
              <SectionTitle
                right={
                  <span className="font-num text-caption text-ink-soft">
                    {layerBuilt}/{items.length} built
                  </span>
                }
              >
                <span id={`layer-${i}`}>{layer.id}</span>
              </SectionTitle>
              <p className="text-body text-ink-soft mb-2 max-w-3xl">{layer.blurb}</p>
              <Card className="px-4 py-1">
                <ul>
                  {items.map((c) => (
                    <ComponentRow key={c.name} c={c} />
                  ))}
                </ul>
              </Card>
              {i < LAYERS.length - 1 && (
                <div className="flex justify-center mt-3 text-ink-soft/40" aria-hidden>
                  <ArrowDown size={16} />
                </div>
              )}
            </section>
          );
        })}
      </div>

      <div className="mt-6">
        <Callout kind="warn" title="Assay is where software stops">
          Everything above the last layer is the platform reasoning about the world from
          literature, models and claim text. Runbook is the last thing it can produce on its own: a
          falsifiable claim. Deposition is the world answering back, and it is the only ground truth
          the platform ever gets about its own predictions — nothing in the literature can tell you
          whether a yield model works.
        </Callout>
      </div>
    </>
  );
}
