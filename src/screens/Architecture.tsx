// The component architecture, made visible (OF-BLD-006 §2, §2.2 reversed).
//
// The eighteen names and seven layers used to live only in COMPONENTS.md and
// in attribution tags a few pixels high. This screen renders the architecture
// as the thing it actually is: a pipeline with a direction, seven components
// not yet built, one piece of code with no name at all, and one layer where
// the arrow reverses.
//
// It is also the glossary, and since OF-BLD-008 it is the map of the ELEVEN:
// the rail carries Home plus eleven destinations and nothing else, and every
// component below is owned by one of them. A reader who has met a few names in
// the rail sees the whole architecture here, including which parts they have
// not met because there is nothing there yet.
import { ArrowDown, CircleDashed, FileCode2, Tag } from 'lucide-react';
import {
  COMPONENTS,
  FULL_NAME,
  LAYERS,
  UNNAMED,
  componentsInLayer,
  isBuilt,
  type ComponentDef,
} from '@/data/components';
import { DESCRIPTOR } from '@/data/nav';
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
        {DESCRIPTOR[c.name] && (
          <span className="text-caption text-ink-soft">{DESCRIPTOR[c.name]}</span>
        )}
        {/* OF-BLD-008 — which of the eleven owns this. Shown on machinery
            rather than on destinations, where it would just repeat the name. */}
        {c.owner !== c.name && (
          <span className="text-caption text-ink-soft">
            inside <span className="text-ink">{c.owner}</span>
          </span>
        )}
        {c.surfacedAs ? (
          <span className="text-caption text-ink-soft">
            · read as <span className="text-ink">{c.surfacedAs}</span>
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
        subtitle="Home plus eleven destinations, and the components each one owns. This is both the architecture the system is built from and the vocabulary it is used through — the words in the rail are these words, and the list is closed."
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
          Why the rail says these
          <Explain label="Why the rail uses component names">
            Because you are going to use this daily, and a precise name learned once beats a
            generic one re-read forever. &ldquo;Ask&rdquo; names the verb and tells you nothing
            about what you are talking to; &ldquo;Postdoc&rdquo; tells you it plans, retrieves,
            shows its working, and can be handed a half-formed question. Three things keep that
            from being hostile on day one: every label carries a descriptor, the command palette
            still answers to the old words, and every old link redirects rather than 404s. Type
            &ldquo;library&rdquo; in the palette and BioRepo comes up.
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
                  {/* §3 — code in this layer that has no name. Primer used to
                      name the unit engine and now names the Learn screens; the
                      engine was not handed a replacement on the spot. It is on
                      the map as unnamed rather than quietly dropped. */}
                  {UNNAMED.filter((u) => u.layer === layer.id).map((u) => (
                    <li key={u.what} className="py-2.5 border-b border-line/70 last:border-0">
                      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                        <span className="font-serif italic text-body text-ink-soft">{u.what}</span>
                        <span className="chip text-ink-soft text-[11px] py-0 inline-flex items-center gap-1">
                          <Tag size={11} aria-hidden />
                          no name yet
                        </span>
                      </div>
                      <div className="text-body text-ink-soft mt-0.5">{u.role}</div>
                      <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5">
                        {u.livesIn.map((path) => (
                          <span
                            key={path}
                            className="font-num text-caption text-ink-soft inline-flex items-center gap-1"
                          >
                            <FileCode2 size={11} aria-hidden />
                            {path}
                          </span>
                        ))}
                      </div>
                    </li>
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
