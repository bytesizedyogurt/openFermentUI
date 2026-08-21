// Parchment (OF-FE-003 §8.6) — patent scope in the same ontology as the
// literature.
//
// The scope map is not drawn, and that is the honest state rather than an
// omission. Drawing claimed regions requires parsed claim bounds; the corpus
// holds a one-line description of each patent's subject matter and no claim
// text at all. A map with rectangles inferred from subject matter would read as
// analysis and be guesswork, and §12.6's rule against inventing a patent is
// worth less than nothing if a real patent can be given invented scope.
//
// So this screen ships the six real entries, states precisely what is missing,
// and shows the arithmetic that is already built and waiting for input.
import { Scale, AlertTriangle } from 'lucide-react';
import { unparsedClaims } from '@/engine/scope';
import { useStore } from '@/store';
import { href } from '@/router';
import {
  Card,
  PageHeader,
  SectionTitle,
  Callout,
  Explain,
  LinkButton,
  Skeleton,
} from '@/components/ui';
// Patents come from BioRepo, not from a "Parchment" server. Parchment is this
// screen; a patent is catalogued literature that carries claims, keyed by
// `paperId` to a corpus entry, and `CorpusAdapter.getScope` already reads the
// same six to test a configuration. Naming an adapter after the page that
// draws it would make a UI layout into an architecture — see the reasoning on
// `CorpusAdapter.listPatents`.
import { adapters } from '@/adapters';
import { useAdapterData } from '@/adapters/react';

export function Parchment() {
  const papers = useStore((s) => s.papers);
  const patents = useAdapterData(() => adapters.corpus.listPatents(), []);

  if (patents.status !== 'ready') {
    return (
      <div className="p-6 max-w-[1100px]">
        <PageHeader
          eyebrow="Reason · Parchment"
          title="Patent scope"
          subtitle="Claims expressed in the same ontology as the literature, so a Ledger record can be tested against one rather than read beside it."
        />
        {patents.status === 'failed' ? (
          // The failure is shown, not smoothed over. An empty patent list on
          // this screen would read as "no patents were found", which is the
          // one sentence the whole page exists to avoid saying by accident.
          <Callout kind="warn" title="The patent catalogue could not be read">
            {patents.error.message}
          </Callout>
        ) : (
          <Card>
            <Skeleton rows={6} />
          </Card>
        )}
      </div>
    );
  }

  const catalogued = patents.data;
  const unparsed = unparsedClaims(catalogued);
  // Both halves of the ratio were unparsed.length, so it could only ever read
  // "N of N" — it would still say "all of them" once some were parsed.
  const totalClaims = catalogued.reduce((n, pt) => n + pt.claims.length, 0);

  return (
    <div className="p-6 max-w-[1100px]">
      <PageHeader
        eyebrow="Reason · Parchment"
        title="Patent scope"
        subtitle="Claims expressed in the same ontology as the literature, so a Ledger record can be tested against one rather than read beside it."
      />

      <div className="max-w-3xl">
        <Callout kind="warn" title="The scope map is not drawn, and should not be">
          <p className="mb-2">
            All <span className="font-num">{catalogued.length}</span> entries below are real, from the
            patent landscape catalogued in OF-COR-001 §9. What the corpus holds for each is a
            curator&rsquo;s one-line description of its subject matter —{' '}
            <span className="font-num">{unparsed.length}</span> of{' '}
            <span className="font-num">{totalClaims}</span> claims carry no parsed bounds.
          </p>
          <p>
            A scope map needs claimed regions, and a region inferred from subject matter would be a
            guess wearing the clothes of an analysis. Giving a real patent invented scope is a
            worse error than inventing a patent, because a reader has no way to tell it from work.
            The map arrives when claims are fetched and parsed, and not before.
          </p>
        </Callout>
      </div>

      <section className="mt-6 mb-6">
        <SectionTitle
          right={
            <Explain label="What is anticipation?">
              A Ledger record published before a claim&rsquo;s priority date, whose value falls
              inside that claim&rsquo;s bounds, is prior art against it. Nobody searches prior art
              with a structured parameter database, because claim scope and literature values are
              never in the same units — putting them in one ontology is the whole point of this
              part. <span className="font-mono">engine/scope.ts</span> implements the arithmetic
              and refuses to run without a real date on both sides and at least one parsed bound.
            </Explain>
          }
        >
          Catalogued patents
        </SectionTitle>

        <div className="space-y-2">
          {catalogued.map((pt) => {
            const source = papers.find((p) => p.id === pt.paperId);
            return (
              <Card key={pt.id} className="p-3">
                <div className="flex items-start justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Scale size={13} className="text-ink-soft shrink-0" aria-hidden />
                      <span className="font-mono text-body">{pt.number}</span>
                      <span className="text-caption text-ink-soft">
                        {pt.jurisdiction} · {pt.status}
                      </span>
                      {pt.verifyNeeded && (
                        <span className="text-caption text-signal-warn">[verify]</span>
                      )}
                    </div>
                    <div className="text-body mt-1">{pt.title}</div>
                    <div className="text-caption text-ink-soft mt-0.5">
                      {pt.assignee}
                      {pt.priorityDate ? ` · priority ${pt.priorityDate}` : ' · no priority date on record'}
                      {source && (
                        <>
                          {' · '}
                          <a
                            href={href(`/trawl/sources/${source.id}`)}
                            className="text-accent hover:underline"
                          >
                            {source.id}
                          </a>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {pt.claims.map((c) => (
                  <div key={c.number} className="mt-2 border-l-2 border-line pl-2">
                    <div className="text-caption text-ink-soft">
                      Claim {c.number}
                      {c.independent ? ' (independent)' : ''}
                      {c.parseUncertain && (
                        <span
                          className="text-signal-warn"
                          title="Subject-matter note, not claim language — it cannot be tested against a record."
                        >
                          {' '}
                          · <AlertTriangle size={10} className="inline" aria-hidden /> no bounds
                          parsed
                        </span>
                      )}
                    </div>
                    <div className="text-caption text-ink-soft mt-1 italic">{c.rawText}</div>
                  </div>
                ))}
              </Card>
            );
          })}
        </div>
      </section>

      <section className="mt-6 max-w-3xl">
        <SectionTitle>Anticipation candidates</SectionTitle>
        <Callout kind="info" title="None can be computed yet">
          Anticipation needs a priority date on the claim and at least one parsed bound to test a
          record against. Neither is on record for any of these six, so the check returns nothing —
          which is a statement about the inputs, not a finding that no prior art exists.
        </Callout>
      </section>

      {/* The Parchment part holds both pools. This is the only place the
          corpus screen mentions the demo one, and it says which is which
          rather than implying one catalogue. */}
      <section className="mt-6 max-w-3xl">
        <SectionTitle>The demo suite&rsquo;s patent families</SectionTitle>
        <div className="text-body text-ink-soft">
          The six above are real filings catalogued in OF-COR-001 §9. The demo suite carries a
          separate, entirely synthetic set of{' '}
          <a href={href('/parchment/families')} className="text-accent hover:underline">
            fourteen families with parsed claim scope
          </a>{' '}
          — which is what the corpus entries lack, and what a scope map would need. They are kept
          apart on purpose: nothing on that page is a filing that exists.
        </div>
      </section>

      <div className="mt-5">
        <LinkButton to="/ledger">Back to the Ledger</LinkButton>
      </div>
    </div>
  );
}
