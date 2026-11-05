// The strain catalogue (OF-DES-001 §8.9) — geneOS's Hosts view since
// OF-BLD-011 §7.3, because choosing a chassis is a genetic design decision
// rather than a reactor one. An honest account of how much of the corpus
// actually stands behind each strain: each card counts its papers, verified
// records, protocols and scenarios, and says plainly when a class is empty.
//
// The catalogue is the project's strain catalogue, which the store reads
// through lib/catalogues.ts (alpha 2.2 E.9): each card names a strain as its
// entry does, its species, its name, the other names papers give it and its
// note, and a strain is kept on the Catalogues screen.
import { useMemo, useState } from 'react';
import { ArrowRight, ClipboardList, FlaskConical, LineChart, BookOpen, ShieldCheck } from 'lucide-react';
import type { Strain } from '@/lib/catalogues';
import { namesStrain, strainNames } from '@/lib/geneos';
import type { ExtractionRecord } from '@/lib/review';
import { useStore } from '@/store';
import { ProvDot, ProvenanceLegend, Tick, type ProvKind } from '@/components/Provenance';
import {
  Bar,
  Callout,
  Card,
  EmptyState,
  Explain,
  LinkButton,
  PageHeader,
  cx,
} from '@/components/ui';

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
 * A record counts for a strain when its organism tag names it: anchoring resolves the wording a paper uses to a
 * strain's id by the name and the other names its entry keeps (validate.strain_id on the service).
 */
function recordsFor(records: ExtractionRecord[], strainId: string): ExtractionRecord[] {
  return records.filter((r) => r.organism === strainId);
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
  const aliases = s.aliases ?? [];

  return (
    <Card className="p-4 flex flex-col gap-3" data-testid="strain-card" data-strain={s.id}>
      <div>
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            {s.species ? (
              <>
                <h2 className="font-serif text-section-title font-semibold italic leading-snug">{s.species}</h2>
                <div className="font-num text-body mt-0.5">{s.name}</div>
              </>
            ) : (
              <h2 className="font-serif text-section-title font-semibold leading-snug">{s.name}</h2>
            )}
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

        {aliases.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5" aria-label="Other names">
            {aliases.map((a) => (
              <span key={a} className="chip text-ink-soft" title="Another name papers give this strain">
                {a}
              </span>
            ))}
          </div>
        )}

        {s.note && <p className="mt-2 text-body text-ink-soft line-clamp-3">{s.note}</p>}
      </div>

      <Tick
        p={c.prov}
        className="mt-auto pt-1"
        title={
          c.prov === 'gold'
            ? 'This strain has records in the gold set'
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
            title="Papers holding a record for this strain"
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
            title="Scenarios whose name, description or product names this strain"
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
        <LinkButton to={`/geneos/hosts/${s.id}`} variant="primary">
          Open <ArrowRight size={14} />
        </LinkButton>
        <span className="font-num text-caption text-ink-soft">{s.id}</span>
        {s.program && (
          <span className="text-caption text-ink-soft ml-auto" title="The chemical set its trains use, as pureOS names it">
            chemical set <span className="font-num">{s.program}</span>
          </span>
        )}
      </div>
    </Card>
  );
}

// ── screen ─────────────────────────────────────────────────────────────

type SortKey = 'coverage' | 'name';

export default function Organisms({ embedded = false }: { embedded?: boolean } = {}) {
  const strains = useStore((s) => s.strains);
  const read = useStore((s) => s.cataloguesRead);
  const problem = useStore((s) => s.cataloguesProblem);
  const papers = useStore((s) => s.papers);
  const records = useStore((s) => s.records);
  const protocols = useStore((s) => s.protocols);
  const scenarios = useStore((s) => s.scenarios);

  const [sort, setSort] = useState<SortKey>('coverage');

  const coverage = useMemo<Coverage[]>(() => {
    return strains.map((strain) => {
      const recs = recordsFor(records, strain.id);
      const live = recs.filter((r) => r.status !== 'rejected');
      const gold = live.filter((r) => !!r.gold).length;
      const verified = live.filter((r) => r.status === 'verified').length;
      const unverified = live.filter((r) => r.status === 'unverified').length;
      // The papers the strain's records were read from.
      const paperCount = new Set(recs.map((r) => r.paperId)).size;
      const protocolCount = protocols.filter((p) => (p.organisms ?? []).includes(strain.id)).length;
      const scenarioCount = scenarios.filter((sc) => namesStrain(sc, strainNames(strain))).length;
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
  }, [strains, records, protocols, scenarios]);

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
          (a.strain.species ?? '').localeCompare(b.strain.species ?? '') ||
          a.strain.name.localeCompare(b.strain.name),
      );
    } else {
      list.sort(
        (a, b) =>
          b.classes - a.classes ||
          b.verified - a.verified ||
          b.records - a.records ||
          a.strain.name.localeCompare(b.strain.name),
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
    'One page per organism, holding every parameter this project\'s records give for it. The coverage counts below describe this project\'s records, not the published literature.';

  if (strains.length === 0) {
    return (
      <>
        {!embedded && <PageHeader eyebrow="geneOS · Hosts" title="Organisms" subtitle={subtitle} />}
        {problem && (
          <div className="mb-4">
            <Callout kind="warn" title="The project's strains could not be read">
              <span data-testid="hosts-problem">{problem}</span>
            </Callout>
          </div>
        )}
        {!read && !problem ? (
          <p className="text-body text-ink-soft" data-testid="hosts-reading">
            Reading the project&rsquo;s strain catalogue…
          </p>
        ) : (
          <Card>
            <EmptyState
              icon={<FlaskConical size={22} />}
              title="No strain is on file yet"
              body="The project's strain catalogue holds no strain yet. Each strain kept there gets a card here, counting the papers, records, protocols and scenarios that stand behind it."
              action={<LinkButton to="/catalogues">Keep a strain on the Catalogues screen</LinkButton>}
            />
          </Card>
        )}
      </>
    );
  }

  return (
    <>
      {/* Suppressed when geneOS mounts this as its Hosts view — the owner's
          header is already on screen and two would read as two pages.
          OF-BLD-011 §7.3 moved the mount from fermOS to geneOS; this file is
          unchanged apart from where it is mounted and where its links point. */}
      <PageHeader
        eyebrow={embedded ? undefined : 'geneOS · Hosts'}
        title={embedded ? null : 'Organisms'}
        subtitle={embedded ? undefined : subtitle}
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
                    : 'Alphabetical by species, then by name'
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
            Four counts, each derived live from the session store: papers holding a record for the
            strain; extraction records for it that a reviewer has verified; protocols listing it;
            and scenarios that name it in their name, description or product.
            A record counts for the strain its organism tag names, which the service resolves from the
            paper&rsquo;s wording by the names the strain&rsquo;s entry keeps. Bars are drawn relative to the best-covered
            strain in this corpus, so they compare strains to each other and to nothing else.
          </Explain>
        </span>
      </div>

      {problem && (
        <div className="mb-4">
          <Callout kind="warn" title="The project's strains could not be read again">
            {problem} The cards below are the strains as last read.
          </Callout>
        </div>
      )}

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
            A scenario counts for a strain when its name, description or product names the strain by
            one of the names its entry keeps.
          </span>
        </div>
      </div>
    </>
  );
}
