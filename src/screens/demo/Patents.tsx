// The demo suite's patent families (OF-DEMO-002 §4.6).
//
// WHY THIS IS A SEPARATE SCREEN FROM `/parchment`. Parchment is the Parchment
// part, and the part holds both pools — but the two pools do not share a file.
// `Parchment.tsx` reads the casein corpus through `adapters.corpus`, and the
// demo pool reads its modules directly; a screen doing both would be half
// behind the seam and half in front of it, and the seam is the thing keeping
// an `ExtractionRecord` (a catalogued claim awaiting verification) from being
// averaged with an `Accession` (a normalised quantity with complete
// provenance). So: one part, one rail entry, two screens, each labelled with
// the pool it reads.
//
// WHY IT EXISTS AT ALL. Three link families pointed at `/parchment#PF-003` —
// the demo patent chip, the FTO flag on a factor band, and `chipRoute` — and
// all three landed on "Route not found", because the hash router had no
// concept of a second `#` and `/parchment` renders `PT-*` corpus patents with
// no `id=` anchors in any case. The router now parses the fragment; this
// screen is what the fragment resolves to.
//
// THE ASYMMETRY IS THE POINT and it is meant to be pre-verbal (OF-DEMO-003
// §2). Eight jurisdictions enclosed against three never entered should be
// visible as a shape before anybody reads a label, which is why the header
// counts positions rather than families: fourteen families is a catalogue,
// and "42 of 154 positions never nationalised" is a finding.
import { Scale, FlaskConical } from 'lucide-react';

import { PATENT_FAMILIES } from '@/data/demo/patents';
import { FIELD_BY_ID, DEMO_NOW } from '@/data/demo/core';
import { monthsToExpiry, jurisdictionRollup } from '@/lib/demo';
import { href } from '@/router';
import { Card, PageHeader, SectionTitle, Callout } from '@/components/ui';
import { ClaimChip } from '@/components/demo/ClaimOverlay';
import { AccessionValue } from '@/components/demo/AccessionValue';
import { DemoFooter } from '@/components/demo/DemoFooter';

import { partEyebrow } from '@/data/parts';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('parchment', 'demo');
/** Loud states first, so a scan hits enclosure before it hits an open door. */
const RANK: Record<string, number> = {
  enclosed: 0,
  expiring: 1,
  pending: 2,
  'never-nationalised': 3,
  expired: 4,
  'no-claim-found': 5,
};

export function DemoPatents() {
  // One definition of "open", shared with the Bench. Two screens counting the
  // same positions two ways is how a reader ends up unable to tell which figure
  // is the finding.
  const roll = jurisdictionRollup();
  const { total: positionCount, enclosed, open } = roll;

  return (
    <>
      <PageHeader
        eyebrow={EYEBROW}
        title="Patent families"
        subtitle={`${PATENT_FAMILIES.length} families across ${positionCount} national positions. Claim scope is expressed in the same field vocabulary as an Accession, so a recited range and a measured value can be compared rather than read beside each other.`}
      />

      <div className="max-w-3xl">
        <Callout kind="warn" title="Every number and assignee on this page is synthetic">
          <p className="mb-2">
            The publication series are provably impossible — US publication years beyond the
            present, EP numbers beyond current numbering — so nothing here can be mistaken for a
            filing that exists, and no real company appears anywhere in it.
          </p>
          <p>
            What is real is the <em>shape</em>: which enzymatic step attracts the claims, how
            families cluster on the commercially decisive one, and the fact that the great
            majority of fermentation patents are never nationalised beyond US/EP/CN/JP/KR. Of the{' '}
            <span className="font-num">{positionCount}</span> positions below,{' '}
            <span className="font-num text-signal-closed">{enclosed}</span> are enclosed and{' '}
            <span className="font-num text-signal-open">{open}</span> are open ground. That
            asymmetry is the argument, and it survives the numbers being invented.
          </p>
        </Callout>
      </div>

      <section className="mt-6">
        <SectionTitle>Families</SectionTitle>
        <div className="space-y-3">
          {PATENT_FAMILIES.map((fam) => {
            const sorted = [...fam.jurisdictions].sort(
              (a, b) => (RANK[a.status] ?? 9) - (RANK[b.status] ?? 9),
            );
            return (
              // The anchor. `id` is the family id so `/parchment/families#PF-003`
              // resolves; `scroll-mt` keeps the heading clear of the sticky
              // header once `useFragmentScroll` brings it into view.
              <Card key={fam.id} id={fam.id} className="p-4 scroll-mt-4">
                <div className="flex items-start gap-2 flex-wrap">
                  <Scale size={13} className="text-ink-soft shrink-0 mt-1" aria-hidden />
                  <span className="font-num text-caption text-ink-soft">{fam.id}</span>
                  <span className="font-mono text-body">{fam.representativeNumber}</span>
                  <span className="text-caption text-ink-soft ml-auto font-num">
                    priority {fam.priorityDate} · {fam.termYears}-year term
                  </span>
                </div>

                <div className="text-body mt-1">{fam.title}</div>
                <div className="text-caption text-ink-soft mt-0.5">{fam.assignee}</div>

                <div className="mt-3">
                  <div className="text-caption text-ink-soft mb-1">Where it was actually taken</div>
                  <div className="flex flex-wrap gap-1">
                    {sorted.map((j) => (
                      <ClaimChip
                        key={j.code}
                        jurisdiction={j.code}
                        status={j.status}
                        familyIds={[fam.id]}
                      />
                    ))}
                  </div>
                </div>

                <div className="mt-3">
                  <div className="text-caption text-ink-soft mb-1">Independent claim scope</div>
                  <ul className="space-y-1.5">
                    {fam.claimScope.map((cs, i) => (
                      <li key={i} className="border-l-2 border-line pl-2">
                        <div className="text-caption">{cs.element}</div>
                        {cs.recitedRange && (
                          <div className="text-caption text-ink-soft font-num">
                            recites {FIELD_BY_ID[cs.recitedRange.field]?.name ?? cs.recitedRange.field}{' '}
                            {cs.recitedRange.low}–{cs.recitedRange.high} {cs.recitedRange.unit}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>

                {fam.examples.length > 0 && (
                  <div className="mt-3">
                    <div className="text-caption text-ink-soft mb-1 flex items-center gap-1">
                      <FlaskConical className="w-3 h-3" aria-hidden />
                      Working examples
                    </div>
                    <ul className="space-y-1.5">
                      {fam.examples.map((ex) => (
                        <li key={ex.number} className="border-l-2 border-line pl-2">
                          <div className="text-caption">
                            <span className="font-num">{ex.number}</span>
                            {/* A comparative example is an example the filer
                                needed to FAIL. It is the most interesting row
                                on the page and it is marked as such. */}
                            {ex.comparative && (
                              <span className="text-signal-warn ml-1.5">comparative</span>
                            )}
                          </div>
                          <div className="text-caption text-ink-soft">{ex.summary}</div>
                          {ex.accessionIds.length > 0 && (
                            <div className="flex flex-wrap gap-x-3 gap-y-1 mt-0.5">
                              {ex.accessionIds.map((id) => (
                                <AccessionValue key={id} id={id} />
                              ))}
                            </div>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="text-caption text-ink-soft mt-3 max-w-prose">{fam.notes}</div>

                {/* The soonest expiry the family has, stated in months rather
                    than as a date, because "31 months" is a decision and
                    "2031-03-14" is a fact you still have to do arithmetic on. */}
                {(() => {
                  const soonest = fam.jurisdictions
                    .map((j) => (j.expiry ? monthsToExpiry(j.expiry, DEMO_NOW) : null))
                    .filter((m): m is number => m !== null)
                    .sort((a, b) => a - b)[0];
                  return soonest === undefined ? null : (
                    <div className="text-caption text-ink-soft mt-2 font-num">
                      soonest expiry in {soonest} months, counted from the frozen present of{' '}
                      {DEMO_NOW}
                    </div>
                  );
                })()}
              </Card>
            );
          })}
        </div>
      </section>

      <div className="mt-5 text-caption">
        <a href={href('/parchment')} className="text-accent hover:underline">
          ← the β-casein corpus&rsquo;s catalogued patents
        </a>
      </div>

      <DemoFooter />
    </>
  );
}
