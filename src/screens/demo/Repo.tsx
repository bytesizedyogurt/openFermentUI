// BioRepo — the Accession index, the atom page, the parameter page, the
// conflict queue (OF-DEMO-002 §2, §3.2, §3.3).
//
// These come before the archetypes in the build order for one reason: every
// archetype deep-links into them. A factor band's exclusion, a candidate's
// feedstock cost, a disclosure's supporting evidence — all of them are links
// to `/repo/a/:id`, and a seam that lands on a missing screen is not a seam.
import { useMemo, useState } from 'react';

import type { Accession, FieldId } from '@/data/demo/types';
import { ACCESSIONS, ACCESSION_BY_ID } from '@/data/demo/accessions';
import { FIELDS, FIELD_BY_ID, SOURCE_BY_ID, SEED_DISCLAIMER, ORGANISM_BY_ID } from '@/data/demo/core';
import { PATENT_BY_ID } from '@/data/demo/patents';
import { DELIVERABLES } from '@/data/demo/archetypes';
import { normalise, accessionsOnField, isContradiction, conflictPairs, reconciledPairs } from '@/lib/demo';
import { href, navigate } from '@/router';
import { PageHeader, Card, SectionTitle, EmptyState, cx } from '@/components/ui';
import { AccessionValue, reportedText, auxiliaryText } from '@/components/demo/AccessionValue';
import { DemoTick, DemoTickLegend, SOURCE_LABEL, HOLD_LABEL, demoTickClass, demoTickTitle } from '@/components/demo/DemoTick';
import { DemoContradictionRail } from '@/components/demo/DemoContradictionRail';
import { DemoFooter } from '@/components/demo/DemoFooter';

// ── /repo — the index ──────────────────────────────────────────────────

export function RepoIndex() {
  const [q, setQ] = useState('');
  const [family, setFamily] = useState<string>('all');
  const [heldOnly, setHeldOnly] = useState(false);

  const families = useMemo(
    () => [...new Set(FIELDS.map((f) => f.family))].sort(),
    [],
  );

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return ACCESSIONS.filter((a) => {
      const def = FIELD_BY_ID[a.field];
      if (family !== 'all' && def?.family !== family) return false;
      if (heldOnly && !a.hold) return false;
      if (!needle) return true;
      return (
        a.id.toLowerCase().includes(needle) ||
        a.field.toLowerCase().includes(needle) ||
        (def?.name ?? '').toLowerCase().includes(needle) ||
        (a.context.organismId ?? '').toLowerCase().includes(needle) ||
        (a.context.productId ?? '').toLowerCase().includes(needle) ||
        (a.quote ?? '').toLowerCase().includes(needle)
      );
    });
  }, [q, family, heldOnly]);

  return (
    <div className="p-6 max-w-[1400px]">
      <PageHeader
        title="BioRepo"
        subtitle={`${ACCESSIONS.length} Accessions. One quantity each, with complete provenance under a permanent identifier.`}
      />

      <div className="flex flex-wrap items-center gap-3 mb-3">
        <input
          className="input flex-1 min-w-[16rem]"
          placeholder="Filter by id, field, organism, product, or quoted text"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select className="input w-auto" value={family} onChange={(e) => setFamily(e.target.value)}>
          <option value="all">all families</option>
          {families.map((f) => (
            <option key={f} value={f}>
              {f}
            </option>
          ))}
        </select>
        <label className="text-caption text-ink-soft inline-flex items-center gap-1.5">
          <input type="checkbox" checked={heldOnly} onChange={(e) => setHeldOnly(e.target.checked)} />
          held only
        </label>
        <span className="text-caption text-ink-soft font-num">{rows.length} shown</span>
      </div>

      <DemoTickLegend />

      <Card className="mt-3 p-0 overflow-x-auto">
        <table className="w-full text-body">
          <thead className="text-caption text-ink-soft text-left">
            <tr className="border-b border-line">
              <th className="font-normal p-2">Accession</th>
              <th className="font-normal p-2">Field</th>
              <th className="font-normal p-2">Value</th>
              <th className="font-normal p-2">Context</th>
              <th className="font-normal p-2">Source</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((a) => {
              const def = FIELD_BY_ID[a.field];
              const src = SOURCE_BY_ID[a.sourceId];
              return (
                <tr
                  key={a.id}
                  className={cx('border-b border-line/50 hover:bg-[rgb(var(--accent-wash))]/30 cursor-pointer', a.hold && 'opacity-60')}
                  onClick={() => navigate(`/repo/a/${a.id}`)}
                >
                  <td className="p-2 align-top whitespace-nowrap">
                    <span className={cx(demoTickClass(a.provenance, a.sourceType), 'pl-2 font-num')} title={demoTickTitle(a.provenance, a.sourceType, a.hold)}>
                      {a.id}
                    </span>
                  </td>
                  <td className="p-2 align-top">
                    <a href={href(`/repo/p/${a.field}`)} className="hover:text-accent" onClick={(e) => e.stopPropagation()}>
                      {def?.name ?? a.field}
                    </a>
                  </td>
                  <td className="p-2 align-top font-num whitespace-nowrap">
                    {+normalise(a, ACCESSION_BY_ID).toFixed(4)} {a.normalized.unit}
                    {a.reported.unit !== a.normalized.unit && (
                      <span className="text-caption text-ink-soft ml-1.5">(orig. {reportedText(a)})</span>
                    )}
                  </td>
                  <td className="p-2 align-top text-caption text-ink-soft">
                    {[a.context.organismId, a.context.productId, a.context.scale, a.context.mode]
                      .filter(Boolean)
                      .join(' · ') || '—'}
                  </td>
                  <td className="p-2 align-top text-caption text-ink-soft">
                    {SOURCE_LABEL[a.sourceType]}
                    {src && <span className="ml-1">· {src.id}</span>}
                    {a.hold && (
                      <span className="ml-1 text-signal-warn">· held: {HOLD_LABEL[a.hold]}</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {rows.length === 0 && <EmptyState title="Nothing matches" body="No Accession in the pool matches that filter." />}
      </Card>

      <DemoFooter />
    </div>
  );
}

// ── /repo/a/:id — the atom ─────────────────────────────────────────────

export function AccessionPage({ id }: { id: string }) {
  const acc = ACCESSION_BY_ID[id];

  const uses = useMemo(
    () => (acc ? DELIVERABLES.filter((d) => d.accessionIds.includes(acc.id)) : []),
    [acc],
  );
  const siblings = useMemo(() => (acc ? accessionsOnField(acc.field) : []), [acc]);

  if (!acc) {
    return (
      <div className="p-6">
        <EmptyState
          title={`No Accession ${id}`}
          body="This pool holds no quantity under that identifier. A link that got here is stale."
        />
      </div>
    );
  }

  const def = FIELD_BY_ID[acc.field];
  const src = SOURCE_BY_ID[acc.sourceId];
  const fam = acc.patentFamilyId ? PATENT_BY_ID[acc.patentFamilyId] : undefined;
  const org = acc.context.organismId ? ORGANISM_BY_ID[acc.context.organismId] : undefined;

  return (
    <div className="p-6 max-w-[1100px]">
      <PageHeader
        title={acc.id}
        subtitle={
          <>
            <a href={href(`/repo/p/${acc.field}`)} className="hover:text-accent">
              {def?.name ?? acc.field}
            </a>
            {def && <span className="text-ink-soft"> · {def.family}</span>}
          </>
        }
      />

      {acc.hold && (
        <div className="border-l-2 border-signal-warn pl-3 py-2 mb-4 text-caption">
          <span className="text-signal-warn font-medium">Held — {HOLD_LABEL[acc.hold]}.</span>{' '}
          <span className="text-ink-soft">
            This Accession does not enter any median or aggregate. It is still on record, still
            citable, and still visible in every rail it belongs to — holding is a statement about
            what a value may be used for, not about whether it happened.
            {acc.runId && (
              <>
                {' '}
                The run behind it is{' '}
                <a href={href(`/fermos/runs/${acc.runId}`)} className="font-num hover:text-accent">
                  {acc.runId}
                </a>
                .
              </>
            )}
          </span>
        </div>
      )}

      <div className="grid lg:grid-cols-[1.4fr_1fr] gap-4">
        <div className="space-y-4">
          {/* Value */}
          <Card>
            <SectionTitle>Value</SectionTitle>
            <div className="mt-2">
              <AccessionValue id={acc.id} link={false} size="lead" />
            </div>
            {acc.reported.range && (
              <div className="text-caption text-ink-soft mt-1">
                Reported as a range: {acc.reported.range.low}–{acc.reported.range.high}{' '}
                {acc.reported.unit}
              </div>
            )}
            {acc.reported.sd !== undefined && (
              <div className="text-caption text-ink-soft mt-1 font-num">
                ± {acc.reported.sd}
                {acc.reported.n !== undefined && ` (n = ${acc.reported.n})`}
              </div>
            )}
            {acc.quote && (
              <blockquote className="mt-3 border-l-2 border-line pl-3 text-caption text-ink-soft italic">
                “{acc.quote}”
              </blockquote>
            )}
          </Card>

          {/* Derivation — the recursion */}
          <Card>
            <SectionTitle>Derivation</SectionTitle>
            <div className="text-caption text-ink-soft mt-1">{acc.derivation.note}</div>
            <div className="text-caption font-num mt-2">
              {reportedText(acc)} → {+normalise(acc, ACCESSION_BY_ID).toFixed(6)}{' '}
              {acc.normalized.unit}
              <span className="text-ink-soft ml-2">via {acc.derivation.fn}</span>
            </div>
            {acc.derivation.params && (
              <div className="text-caption text-ink-soft mt-1">
                {acc.derivation.params.kind === 'molar-ratio' &&
                  `Molar ratio: ${acc.derivation.params.numerator} over ${acc.derivation.params.denominator}.`}
                {acc.derivation.params.kind === 'molar-mass' &&
                  `Molar mass of ${acc.derivation.params.species}.`}
                {acc.derivation.params.kind === 'offset' &&
                  `Offset ${acc.derivation.params.delta} — ${acc.derivation.params.because}.`}
              </div>
            )}
            {acc.derivation.usingAccessionIds.length > 0 ? (
              <div className="mt-3">
                <div className="text-caption text-ink-soft mb-1">
                  Consumed these auxiliaries. Each is itself an Accession, which is what makes this
                  graph checkable rather than decorative:
                </div>
                <div className="space-y-1">
                  {acc.derivation.usingAccessionIds.map((auxId) => (
                    <div key={auxId} className="text-caption">
                      <a href={href(`/repo/a/${auxId}`)} className="font-num hover:text-accent">
                        {auxId}
                      </a>{' '}
                      <AccessionValue id={auxId} />
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-caption text-ink-soft mt-2">
                No auxiliary quantity was needed. The conversion closes on the unit table alone.
              </div>
            )}
          </Card>

          {/* Uses — the seam made visible */}
          <Card>
            <SectionTitle>Uses</SectionTitle>
            {uses.length ? (
              <ul className="mt-2 space-y-1">
                {uses.map((d) => (
                  <li key={d.id} className="text-caption">
                    <a href={href(deliverableRoute(d.id))} className="hover:text-accent">
                      <span className="font-num text-ink-soft mr-1.5">{d.archetype}</span>
                      {d.title}
                    </a>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-caption text-ink-soft mt-1">
                {acc.poolOnly
                  ? 'In the pool, not yet consumed by an archetype. Tagged poolOnly, so its absence here is a decision rather than an oversight.'
                  : 'No archetype deliverable consumes this Accession.'}
              </div>
            )}
          </Card>
        </div>

        <div className="space-y-4">
          {/* Provenance */}
          <Card>
            <SectionTitle>Provenance</SectionTitle>
            <dl className="mt-2 text-caption space-y-1">
              <Row k="Verification">
                <DemoTick p={acc.provenance} st={acc.sourceType} hold={acc.hold} className="pl-2">
                  {acc.provenance}
                </DemoTick>
              </Row>
              <Row k="Source type">{SOURCE_LABEL[acc.sourceType]}</Row>
              <Row k="Locator">
                <span className="font-num">{acc.locator}</span>
              </Row>
              <Row k="Confidence">
                <span className="font-num">{acc.confidence.toFixed(2)}</span>
              </Row>
              <Row k="Primary">{acc.isPrimary ? 'yes' : `no — recites ${acc.citesAccessionId ?? 'another study'}`}</Row>
            </dl>

            {src && (
              <div className="mt-3 border-t border-line pt-2 text-caption">
                <div>{src.title}</div>
                <div className="text-ink-soft">
                  {src.authors?.join(', ')}
                  {src.year ? ` · ${src.year}` : ''}
                  {src.venue ? ` · ${src.venue}` : ''}
                </div>
                {'doi' in src && (src as { doi?: string }).doi && (
                  <div className="text-ink-soft font-num mt-0.5">{(src as { doi?: string }).doi}</div>
                )}
              </div>
            )}

            {fam && (
              <div className="mt-3 border-t border-line pt-2 text-caption">
                <div className="font-num">{fam.representativeNumber}</div>
                <div className="text-ink-soft">
                  {fam.assignee} · priority {fam.priorityDate}
                </div>
                <div className="text-ink-soft mt-0.5">
                  {fam.jurisdictions.map((j) => j.code).join(', ')}
                </div>
              </div>
            )}
          </Card>

          {/* Context */}
          <Card>
            <SectionTitle>Conditions</SectionTitle>
            <dl className="mt-2 text-caption space-y-1">
              {org && (
                <Row k="Organism">
                  <a href={href(`/geneos/${org.id}`)} className="italic hover:text-accent">
                    {org.binomial}
                  </a>
                </Row>
              )}
              {acc.context.productId && <Row k="Product">{acc.context.productId}</Row>}
              {acc.context.scale && <Row k="Scale">{acc.context.scale}</Row>}
              {acc.context.mode && <Row k="Mode">{acc.context.mode}</Row>}
              {acc.context.temperatureC !== undefined && (
                <Row k="Temperature">
                  <span className="font-num">{acc.context.temperatureC} °C</span>
                </Row>
              )}
              {acc.context.ph !== undefined && (
                <Row k="pH">
                  <span className="font-num">{acc.context.ph}</span>
                </Row>
              )}
              {acc.context.doPercent !== undefined && (
                <Row k="DO">
                  <span className="font-num">{acc.context.doPercent} %</span>
                </Row>
              )}
              {acc.context.feedstock && <Row k="Feedstock">{acc.context.feedstock}</Row>}
              {acc.context.jurisdiction && <Row k="Jurisdiction">{acc.context.jurisdiction}</Row>}
            </dl>
            <div className="text-caption text-ink-soft mt-2">
              Without these the quantity is noise: the same field under a different organism or
              scale is a different measurement, not a competing one.
            </div>
          </Card>

          {/* Ledger */}
          <Card>
            <SectionTitle>Ledger</SectionTitle>
            <ol className="mt-2 space-y-1">
              {acc.ledger.map((e, i) => (
                <li key={i} className="text-caption">
                  <span className="font-num text-ink-soft">{e.at}</span>{' '}
                  <span className="text-ink-soft">{e.who}</span>
                  <div>{e.action}</div>
                  {e.propagatedTo?.length ? (
                    <div className="text-ink-soft">
                      propagated to{' '}
                      {e.propagatedTo.map((pid, j) => (
                        <span key={pid}>
                          {j > 0 && ', '}
                          <a href={href(`/repo/a/${pid}`)} className="font-num hover:text-accent">{pid}</a>
                        </span>
                      ))}
                    </div>
                  ) : null}
                </li>
              ))}
            </ol>
          </Card>
        </div>
      </div>

      {/* The field this sits on, so the reader can see the company it keeps. */}
      <Card className="mt-4">
        <SectionTitle>On this field</SectionTitle>
        <DemoContradictionRail field={acc.field} accessions={siblings} className="mt-2" />
      </Card>

      <DemoFooter />
    </div>
  );
}

function Row({ k, children }: { k: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <dt className="text-ink-soft w-28 shrink-0">{k}</dt>
      <dd className="min-w-0">{children}</dd>
    </div>
  );
}

/**
 * Where a `chip:<id>` follow-up goes.
 *
 * The archetype flows end with `chip:DLV-AR5-001|Open the decomposition tree`
 * and nothing in the UI knew what `chip:` meant — the button rendered with the
 * raw string as its label and clicking it fed that string back to the matcher
 * as a question. One resolver, covering every id kind a follow-up can name, so
 * a new chip kind is one line here rather than a new prefix nobody handles.
 */
export function chipRoute(id: string): string {
  if (id.startsWith('DLV-')) return deliverableRoute(id);
  if (id.startsWith('RB-')) return `/runbook/design/${id}`;
  if (id.startsWith('RUN-')) return `/fermos/runs/${id}`;
  if (id.startsWith('OF-A-')) return `/repo/a/${id}`;
  if (id.startsWith('PF-')) return `/parchment#${id}`;
  return '/bench';
}

/** Where a deliverable renders. One table, so no screen invents a route. */
export function deliverableRoute(deliverableId: string): string {
  const d = DELIVERABLES.find((x) => x.id === deliverableId);
  if (!d) return '/repo';
  switch (d.payload.kind) {
    case 'factor-map':
      return `/fermos/gap/${d.id}`;
    case 'route-comparison':
      return `/geneos/routes/${d.payload.productId}`;
    case 'capacity-screen':
      return `/proforma/screen/${d.payload.plantId}`;
    case 'facility-concept':
      return `/proforma/concept/${d.id}`;
    case 'problem-tree':
      return `/postdoc/tree/${d.id}`;
    case 'excursion-verdict':
      return `/fermos/runs/${d.payload.runId}`;
    default:
      return '/repo';
  }
}

// ── /repo/p/:field — the parameter page ────────────────────────────────

export function ParameterPage({ field }: { field: FieldId }) {
  const def = FIELD_BY_ID[field];
  const accs = useMemo(() => accessionsOnField(field), [field]);

  if (!def) {
    return (
      <div className="p-6">
        <EmptyState title={`No field ${field}`} body="This ontology has no parameter under that id." />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-[1100px]">
      <PageHeader title={def.name} subtitle={`${def.family} · canonical unit ${def.canonicalUnit}`} />
      <div className="text-caption text-ink-soft mb-4">{def.definition}</div>

      <Card>
        <DemoContradictionRail field={field} accessions={accs} height={180} />
      </Card>

      <Card className="mt-4 p-0 overflow-x-auto">
        <table className="w-full text-body">
          <thead className="text-caption text-ink-soft text-left">
            <tr className="border-b border-line">
              <th className="font-normal p-2">Accession</th>
              <th className="font-normal p-2">Normalised</th>
              <th className="font-normal p-2">As reported</th>
              <th className="font-normal p-2">Context</th>
              <th className="font-normal p-2">Source</th>
            </tr>
          </thead>
          <tbody>
            {accs.map((a) => (
              <tr
                key={a.id}
                className={cx('border-b border-line/50 hover:bg-[rgb(var(--accent-wash))]/30 cursor-pointer', a.hold && 'opacity-60')}
                onClick={() => navigate(`/repo/a/${a.id}`)}
              >
                <td className="p-2 whitespace-nowrap">
                  <span className={cx(demoTickClass(a.provenance, a.sourceType), 'pl-2 font-num')} title={demoTickTitle(a.provenance, a.sourceType, a.hold)}>
                    {a.id}
                  </span>
                </td>
                <td className="p-2 font-num whitespace-nowrap">
                  {+normalise(a, ACCESSION_BY_ID).toFixed(4)} {a.normalized.unit}
                </td>
                <td className="p-2 font-num text-caption text-ink-soft whitespace-nowrap">
                  {reportedText(a)}
                  {auxiliaryText(a) && <span> @ {auxiliaryText(a)}</span>}
                </td>
                <td className="p-2 text-caption text-ink-soft">
                  {[a.context.organismId, a.context.scale, a.context.mode].filter(Boolean).join(' · ') || '—'}
                </td>
                <td className="p-2 text-caption text-ink-soft">
                  {SOURCE_LABEL[a.sourceType]}
                  {a.hold && <span className="text-signal-warn"> · held</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <DemoFooter />
    </div>
  );
}

// ── /repo/contradictions — the queue ───────────────────────────────────

export function ContradictionQueue() {
  const rows = useMemo(() => {
    const out: { field: FieldId; kind: 'unresolved' | 'reconciled'; pair: [Accession, Accession] }[] = [];
    const fields = [...new Set(ACCESSIONS.map((a) => a.field))] as FieldId[];
    for (const f of fields) {
      const accs = accessionsOnField(f);
      for (const pair of conflictPairs(accs)) out.push({ field: f, kind: 'unresolved', pair });
      for (const pair of reconciledPairs(accs)) out.push({ field: f, kind: 'reconciled', pair });
    }
    return out;
  }, []);

  const unresolved = rows.filter((r) => r.kind === 'unresolved');
  const reconciled = rows.filter((r) => r.kind === 'reconciled');

  return (
    <div className="p-6 max-w-[1100px]">
      <PageHeader
        title="Contradictions"
        subtitle="Where the record disagrees with itself, and where it only looked like it did."
      />

      <div className="text-caption text-ink-soft mb-4 max-w-prose">
        A pair lands here because a curator linked it, never because two numbers are far apart.
        Spread cannot tell a disagreement from two different experiments — the furfural tolerances
        in this pool differ by a factor of two and are not in conflict, because the organisms
        differ. A system that flagged them would be as useless as one that flagged nothing.
      </div>

      <SectionTitle>Unresolved · {unresolved.length}</SectionTitle>
      {unresolved.length === 0 ? (
        <EmptyState title="None" body="No live disagreement in this pool." />
      ) : (
        <div className="space-y-4 mt-2">
          {unresolved.map(({ field, pair }) => (
            <Card key={`${pair[0].id}-${pair[1].id}`}>
              <div className="text-caption text-ink-soft mb-2">
                <a href={href(`/repo/p/${field}`)} className="hover:text-accent">
                  {FIELD_BY_ID[field]?.name ?? field}
                </a>
              </div>
              <DemoContradictionRail field={field} accessions={accessionsOnField(field)} />
            </Card>
          ))}
        </div>
      )}

      <div className="mt-6"><SectionTitle>Closed by normalisation · {reconciled.length}</SectionTitle></div>
      <div className="text-caption text-ink-soft mb-2">
        Pairs that looked like a disagreement and were not. Showing one resolve is as useful as
        showing one that does not.
      </div>
      {reconciled.length === 0 ? (
        <EmptyState title="None" body="No apparent disagreement was closed by unit conversion." />
      ) : (
        <div className="space-y-4">
          {reconciled.map(({ field, pair }) => (
            <Card key={`${pair[0].id}-${pair[1].id}`}>
              <DemoContradictionRail field={field} accessions={accessionsOnField(field)} />
            </Card>
          ))}
        </div>
      )}

      <DemoFooter />
    </div>
  );
}
