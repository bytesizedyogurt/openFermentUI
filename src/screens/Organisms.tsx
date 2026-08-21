// Organisms index (OF-DES-001 §8.9). Four strains, and an honest account of
// how much of the corpus actually stands behind each one. cw15 is covered
// across every asset class; the others are not, and the card says so rather
// than padding the layout to look even.
import { useEffect, useMemo, useState } from 'react';
import { ArrowRight, ClipboardList, FlaskConical, LineChart, BookOpen, ShieldCheck } from 'lucide-react';
import type { ExtractionRecord, Paper, Strain } from '@/data/types';
import { useStore } from '@/store';
import { ProvDot, ProvenanceLegend, Tick, type ProvKind } from '@/components/Provenance';
import {
  Bar,
  Card,
  EmptyState,
  Explain,
  LinkButton,
  PageHeader,
  Skeleton,
  cx,
} from '@/components/ui';
import { delayClass } from '@/sim/latency';

import { partEyebrow } from '@/data/parts';

/** Movement · part · pool, from the one table that names the parts. */
const EYEBROW = partEyebrow('geneos', 'corpus');
// ── coverage model ─────────────────────────────────────────────────────

interface Coverage {
  strain: Strain;
  papers: number;
  records: number;
  verified: number;
  gold: number;
  unverified: number;
  protocols: number;
  scenarios: number;
  /** How many of the four asset classes have anything at all in them. */
  classes: number;
  prov: ProvKind;
}

/**
 * A record counts for a strain when it is tagged with it, or — absent a tag —
 * when its paper's organism list names it. An explicit tag for a different
 * strain always wins, so a two-organism paper never double-counts a record
 * that already knows which organism it belongs to.
 */
function recordsFor(
  records: ExtractionRecord[],
  paperById: Map<string, Paper>,
  strainId: string,
): ExtractionRecord[] {
  return records.filter((r) => {
    if (r.organism) return r.organism === strainId;
    return paperById.get(r.paperId)?.organisms.includes(strainId) ?? false;
  });
}

const COUNT_LABEL = {
  papers: 'Papers',
  verified: 'Verified records',
  protocols: 'Protocols',
  scenarios: 'Scenarios',
} as const;

function CoverageCount({
  label,
  n,
  max,
  title,
}: {
  label: string;
  n: number;
  max: number;
  title: string;
}) {
  return (
    <div title={title}>
      <div className={cx('font-num text-section-title leading-none', n === 0 && 'text-ink-soft')}>
        {n}
      </div>
      <div className="text-caption text-ink-soft mt-0.5 leading-tight">{label}</div>
      <div className="mt-1">
        <Bar
          value={n}
          max={Math.max(1, max)}
          className={n === 0 ? 'bg-ink-soft/30' : undefined}
        />
      </div>
    </div>
  );
}

function StrainCard({ c, maxes }: { c: Coverage; maxes: Record<string, number> }) {
  const s = c.strain;
  const complete = c.classes === 4 && c.verified > 0;

  return (
    <Card className="p-4 flex flex-col gap-3">
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="font-serif text-section-title font-semibold italic leading-snug">
              {s.binomial}
            </h2>
            <div className="font-num text-body mt-0.5">{s.designation}</div>
          </div>
          <span
            className={cx(
              'chip shrink-0',
              complete ? 'text-accent border-accent/40' : 'text-signal-warn border-signal-warn/40',
            )}
            title={
              complete
                ? 'Papers, verified records, protocols and scenarios all present for this strain'
                : 'At least one asset class is empty, or nothing has been verified yet'
            }
          >
            {complete ? 'full coverage' : 'partial coverage'}
          </span>
        </div>

        <div className="mt-2 flex flex-wrap gap-1.5">
          {s.badges.map((b) => (
            <span key={b} className="chip text-ink-soft">
              {b}
            </span>
          ))}
        </div>

        <p className="mt-2 text-body text-ink-soft line-clamp-3">{s.description}</p>
      </div>

      <Tick
        p={c.prov}
        className="mt-auto pt-1"
        title={
          c.prov === 'gold'
            ? 'This strain has records in the curated gold set'
            : c.prov === 'verified'
              ? 'This strain has reviewer-verified records'
              : 'Nothing for this strain has been reviewed yet'
        }
      >
        <div className="text-caption uppercase tracking-wide text-ink-soft mb-1.5">
          Corpus coverage
        </div>
        <div className="grid grid-cols-4 gap-3">
          <CoverageCount
            label={COUNT_LABEL.papers}
            n={c.papers}
            max={maxes.papers}
            title="Papers whose organism list names this strain"
          />
          <CoverageCount
            label={COUNT_LABEL.verified}
            n={c.verified}
            max={maxes.verified}
            title="Extraction records for this strain that a reviewer has verified"
          />
          <CoverageCount
            label={COUNT_LABEL.protocols}
            n={c.protocols}
            max={maxes.protocols}
            title="Protocols listing this strain among their organisms"
          />
          <CoverageCount
            label={COUNT_LABEL.scenarios}
            n={c.scenarios}
            max={maxes.scenarios}
            title="Scenarios with an assumption or dimension sourced from a record for this strain"
          />
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-caption text-ink-soft">
          <span>
            <span className="font-num text-ink">{c.records}</span> records
          </span>
          {c.gold > 0 && (
            <span className="inline-flex items-center gap-1">
              <ProvDot p="gold" />
              <span className="font-num text-ink">{c.gold}</span> gold
            </span>
          )}
          <span className="inline-flex items-center gap-1">
            <ProvDot p="unverified" />
            <span className="font-num text-ink">{c.unverified}</span> unverified
          </span>
          <span className="font-num">
            {c.classes}/4 asset classes
          </span>
        </div>

        <div className="mt-1.5 text-caption">
          {c.records === 0 ? (
            <span className="text-signal-warn">
              Nothing in the corpus is attributed to this strain.
            </span>
          ) : c.verified === 0 ? (
            <span className="text-signal-warn">
              No verified records yet — every number for this strain is an unreviewed extraction.
            </span>
          ) : c.classes < 4 ? (
            <span className="text-ink-soft">
              Thin in places:{' '}
              {[
                c.papers === 0 && 'no papers',
                c.protocols === 0 && 'no protocols',
                c.scenarios === 0 && 'no scenarios',
              ]
                .filter(Boolean)
                .join(', ')}
              . Treat what is here as a starting point, not a process answer.
            </span>
          ) : (
            <span className="text-ink-soft">
              Covered across papers, verified records, protocols and scenarios.
            </span>
          )}
        </div>
      </Tick>

      <div className="flex items-center gap-2 pt-1 border-t border-line">
        <LinkButton to={`/geneos/${s.id}`} variant="primary">
          Open <ArrowRight size={14} />
        </LinkButton>
        <span className="font-num text-caption text-ink-soft">{s.id}</span>
        <span className="font-num text-caption text-ink-soft ml-auto">BSL-{s.bsl}</span>
      </div>
    </Card>
  );
}

// ── screen ─────────────────────────────────────────────────────────────

type SortKey = 'coverage' | 'name';

export default function Organisms() {
  const strains = useStore((s) => s.strains);
  const papers = useStore((s) => s.papers);
  const records = useStore((s) => s.records);
  const protocols = useStore((s) => s.protocols);
  const scenarios = useStore((s) => s.scenarios);

  const [ready, setReady] = useState(false);
  const [sort, setSort] = useState<SortKey>('coverage');

  useEffect(() => {
    let alive = true;
    delayClass('quick').then(() => {
      if (alive) setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  const paperById = useMemo(() => new Map(papers.map((p) => [p.id, p])), [papers]);

  const coverage = useMemo<Coverage[]>(() => {
    return strains.map((strain) => {
      const recs = recordsFor(records, paperById, strain.id);
      const live = recs.filter((r) => r.status !== 'rejected');
      const ids = new Set(recs.map((r) => r.id));
      const gold = live.filter((r) => !!r.gold).length;
      const verified = live.filter((r) => r.status === 'verified').length;
      const unverified = live.filter((r) => r.status === 'unverified').length;
      const paperCount = papers.filter((p) => p.organisms.includes(strain.id)).length;
      const protocolCount = protocols.filter((p) => p.organisms.includes(strain.id)).length;
      const scenarioCount = scenarios.filter(
        (sc) =>
          sc.assumptions.some((a) => a.recordId && ids.has(a.recordId)) ||
          sc.dims.some((d) => d.sourceRecordId && ids.has(d.sourceRecordId)),
      ).length;
      const prov: ProvKind = gold > 0 ? 'gold' : verified > 0 ? 'verified' : 'unverified';
      return {
        strain,
        papers: paperCount,
        records: recs.length,
        verified,
        gold,
        unverified,
        protocols: protocolCount,
        scenarios: scenarioCount,
        classes: [paperCount, verified, protocolCount, scenarioCount].filter((n) => n > 0).length,
        prov,
      };
    });
  }, [strains, records, papers, protocols, scenarios, paperById]);

  const maxes = useMemo(
    () => ({
      papers: Math.max(1, ...coverage.map((c) => c.papers)),
      verified: Math.max(1, ...coverage.map((c) => c.verified)),
      protocols: Math.max(1, ...coverage.map((c) => c.protocols)),
      scenarios: Math.max(1, ...coverage.map((c) => c.scenarios)),
    }),
    [coverage],
  );

  const ordered = useMemo(() => {
    const list = [...coverage];
    if (sort === 'name') {
      list.sort(
        (a, b) =>
          a.strain.binomial.localeCompare(b.strain.binomial) ||
          a.strain.designation.localeCompare(b.strain.designation),
      );
    } else {
      list.sort(
        (a, b) =>
          b.classes - a.classes ||
          b.verified - a.verified ||
          b.records - a.records ||
          a.strain.designation.localeCompare(b.strain.designation),
      );
    }
    return list;
  }, [coverage, sort]);

  const totals = useMemo(
    () => ({
      records: coverage.reduce((n, c) => n + c.records, 0),
      verified: coverage.reduce((n, c) => n + c.verified, 0),
      gold: coverage.reduce((n, c) => n + c.gold, 0),
    }),
    [coverage],
  );

  const subtitle =
    'One page per organism, holding every parameter the corpus records for it. The coverage counts below describe this demonstration corpus — not the published literature.';

  if (!ready) {
    return (
      <>
        <PageHeader eyebrow={EYEBROW} title="Strains" subtitle={subtitle} />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {[0, 1, 2, 3].map((i) => (
            <Card key={i}>
              <Skeleton rows={7} />
            </Card>
          ))}
        </div>
      </>
    );
  }

  if (strains.length === 0) {
    return (
      <>
        <PageHeader eyebrow={EYEBROW} title="Strains" subtitle={subtitle} />
        <Card>
          <EmptyState
            icon={<FlaskConical size={22} />}
            title="No strains in this session"
            body="The seeded strain set is empty, which normally means the demo data was cleared. Restoring the seeded state from the corpus settings brings the organism index back."
            action={<LinkButton to="/settings/corpus">Open corpus settings</LinkButton>}
          />
        </Card>
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow={EYEBROW}
        title="Strains"
        subtitle={subtitle}
        actions={
          <div
            className="flex rounded-input border border-line overflow-hidden"
            role="group"
            aria-label="Card order"
          >
            {(
              [
                ['coverage', 'By coverage'],
                ['name', 'By name'],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setSort(key)}
                aria-pressed={sort === key}
                title={
                  key === 'coverage'
                    ? 'Best-covered strains first — asset classes, then verified records'
                    : 'Alphabetical by binomial'
                }
                className={cx(
                  'px-2.5 py-[5px] text-[12px]',
                  sort === key ? 'bg-accent-wash text-ink font-medium' : 'text-ink-soft hover:text-ink',
                )}
              >
                {label}
              </button>
            ))}
          </div>
        }
      />

      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 mb-4 text-caption text-ink-soft">
        <span className="inline-flex items-center gap-1.5">
          <FlaskConical size={13} />
          <span className="font-num text-ink">{strains.length}</span> strains
        </span>
        <span className="inline-flex items-center gap-1.5">
          <BookOpen size={13} />
          <span className="font-num text-ink">{papers.length}</span> papers in the corpus
        </span>
        <span className="inline-flex items-center gap-1.5">
          <ShieldCheck size={13} />
          <span className="font-num text-accent">{totals.verified}</span> verified records
          <span className="text-ink-soft">of</span>
          <span className="font-num text-ink">{totals.records}</span>
        </span>
        <span className="inline-flex items-center gap-1.5">
          <ProvDot p="gold" />
          <span className="font-num text-gold">{totals.gold}</span> gold
        </span>
        <span className="inline-flex items-center gap-1">
          What counts as coverage?
          <Explain label="How coverage is counted">
            Four counts, each derived live from the session store: papers whose organism list names
            the strain; extraction records for it that a reviewer has verified; protocols listing it;
            and scenarios whose assumptions or swept dimensions are sourced from one of its records.
            A record with its own organism tag counts only for that organism; an untagged record
            inherits its paper&rsquo;s organism list. Bars are drawn relative to the best-covered
            strain in this corpus, so they compare strains to each other and to nothing else.
          </Explain>
        </span>
      </div>

      <div className="mb-4">
        <ProvenanceLegend />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {ordered.map((c) => (
          <StrainCard key={c.strain.id} c={c} maxes={maxes} />
        ))}
      </div>

      <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4 text-caption text-ink-soft">
        <div className="flex items-start gap-2">
          <ClipboardList size={13} className="mt-[2px] shrink-0" />
          <span>
            Protocol counts come from each protocol&rsquo;s declared organism list, not from
            inference over its steps.
          </span>
        </div>
        <div className="flex items-start gap-2">
          <LineChart size={13} className="mt-[2px] shrink-0" />
          <span>
            A scenario counts for a strain only when one of its assumptions cites a record for that
            strain. Demo model v0 — illustrative economics, not validated.
          </span>
        </div>
      </div>
    </>
  );
}
