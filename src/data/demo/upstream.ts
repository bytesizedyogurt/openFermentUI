// What each part will be derived from.
//
// Every part of this system is a REPLACEMENT BOUNDARY — the thing you could
// swap out without touching the others — and for most of them the thing that
// eventually sits behind the boundary already exists as open-source software.
// This table names it, per part, in one place.
//
// ── WHY ONE TABLE AND NOT A LINE OF PROSE PER SCREEN ──────────────────────
//
// Twelve screens each carrying their own sentence about their own upstream is
// twelve sentences that drift. This is the same rule the rest of the repo
// follows for the collection→model map and the snapshot framing: the statement
// lives once, and the screens render it.
//
// ── THE `status` FIELD IS THE POINT ───────────────────────────────────────
//
// It is very easy to write a slide that says "powered by AlphaFold" about
// software that has never called AlphaFold. The three values keep that from
// happening by accident:
//
//   'ported'    code from this project is IN this repository, now. BioSTEAM is
//               the only one — its costing primitives and TEA are ported to
//               TypeScript in `src/engine/biosteam/`, checked against the
//               Python source by `pnpm check:biosteam`.
//   'named'     the repository has DECIDED on this dependency and says so in
//               CLAUDE.md, a server manifest, or an adapter docstring. Nothing
//               calls it yet. This is the honest state of most of the table.
//   'candidate' an obvious fit that nobody has committed to. Stated as a
//               candidate so a reader does not mistake a plausible choice for
//               a made decision.
//
// Nothing in this table may claim more than the repository can show. A part
// with no decided upstream says so rather than borrowing a famous name.
import type { ArchetypeId } from './types';

export type UpstreamStatus = 'ported' | 'named' | 'candidate';

export interface UpstreamDep {
  name: string;
  /** What it would do here, in one clause. Never what it does in general. */
  role: string;
  status: UpstreamStatus;
  /** Where the decision is recorded, for `named`. */
  recordedIn?: string;
  url?: string;
}

export interface PartUpstream {
  /** Matches the route family the screen sits under. */
  part: string;
  label: string;
  /** One sentence on what this part owns. */
  owns: string;
  deps: UpstreamDep[];
  /**
   * Where a part is deliberately NOT going to wrap anything, or where the
   * decision is open. Rendered as prominently as the dependencies are.
   */
  openQuestion?: string;
}

export const UPSTREAM: PartUpstream[] = [
  {
    part: 'repo',
    label: 'BioRepo',
    owns: 'The corpus: Accessions, parameter pages, the Ledger, contradictions.',
    deps: [
      {
        name: 'PaperQA2',
        role: 'retrieval over the literature — the corpus server declares search_papers and refuses it rather than reimplementing a substring filter',
        status: 'named',
        recordedIn: 'CLAUDE.md · servers/corpus/manifest.json',
        url: 'https://github.com/Future-House/paper-qa',
      },
      {
        name: 'Pydantic',
        role: 'the canonical entity schema, from which the TypeScript types are generated',
        status: 'ported',
        recordedIn: 'packages/core',
      },
    ],
  },
  {
    part: 'geneos',
    label: 'geneOS',
    owns: 'The intracellular domain: host competence, construct feasibility, pathway routes, the stoichiometric ceiling.',
    deps: [
      {
        name: 'COBRApy',
        role: 'flux balance analysis — predict_flux is declared and refuses until a genome-scale model exists',
        status: 'named',
        recordedIn: 'CLAUDE.md · servers/cell/manifest.json',
        url: 'https://github.com/opencobra/cobrapy',
      },
      {
        name: 'Escher',
        role: 'pathway map rendering over the flux solution',
        status: 'named',
        recordedIn: 'OF-DES-001',
        url: 'https://escher.github.io',
      },
      {
        name: 'AlphaFold',
        role: 'structure prediction for an expressed construct, which is upstream of any claim about whether a host can fold it',
        status: 'candidate',
      },
    ],
    openQuestion:
      'Nothing here predicts expression from sequence. The competence matrix is curated from literature, and a structure predictor would tell you whether a protein folds — not whether this chassis secretes it.',
  },
  {
    part: 'fermos',
    label: 'fermOS',
    owns: 'The extracellular domain: cultivation physics, the process space, the recovery train, run adjudication.',
    deps: [
      {
        name: 'BioSTEAM',
        role: 'unit operations and the flowsheet the process space is solved on',
        status: 'ported',
        recordedIn: 'src/engine/biosteam/ · pnpm check:biosteam',
        url: 'https://github.com/BioSTEAMDevelopmentGroup/biosteam',
      },
      {
        name: 'ThermoSTEAM',
        role: 'thermodynamic property packages behind the unit models',
        status: 'named',
        recordedIn: 'MIGRATION.md — deliberately NOT ported; the TypeScript port stops at the unit layer',
        url: 'https://github.com/BioSTEAMDevelopmentGroup/thermosteam',
      },
    ],
  },
  {
    part: 'proforma',
    label: 'Proforma',
    owns: 'Techno-economics against an explicit regional and temporal basis.',
    deps: [
      {
        name: 'BioSTEAM',
        role: 'the TEA — equipment sizing, capital cost correlations, and the discounted cash flow solved at NPV = 0',
        status: 'ported',
        recordedIn: 'src/engine/biosteam/ · servers/economics/manifest.json',
        url: 'https://github.com/BioSTEAMDevelopmentGroup/biosteam',
      },
    ],
    openQuestion:
      'Cost model authoring is BioSTEAM’s and a human’s. The economics server declares solve_plant and refuses it: no minimum selling price is available from a server that has not run the flowsheet.',
  },
  {
    part: 'postdoc',
    label: 'Postdoc',
    owns: 'The agent layer — multi-objective search under Rule 1, which is that no quantity comes from model weights.',
    deps: [
      {
        name: 'Model Context Protocol',
        role: 'the transport every subsystem is reached over; five server skeletons exist under servers/',
        status: 'ported',
        recordedIn: 'servers/ · scripts/check-servers.mjs',
        url: 'https://modelcontextprotocol.io',
      },
      {
        name: 'PaperQA2',
        role: 'the retrieval step inside a turn, so a cited passage is retrieved rather than recalled',
        status: 'named',
        recordedIn: 'CLAUDE.md',
        url: 'https://github.com/Future-House/paper-qa',
      },
    ],
    openQuestion:
      'The model itself is deliberately unnamed. Rule 1 means no number in an answer may come from weights, so which model runs the loop is a smaller decision here than it looks — every quantity traces to an Accession or to a computation over Accessions either way.',
  },
  {
    part: 'assay',
    label: 'Audit',
    owns: 'Independent error measurement across producers, published per field.',
    deps: [
      {
        name: 'Inspect AI',
        role: 'the scorer — extraction metrics against a gold set',
        status: 'ported',
        recordedIn: 'packages/assay · pnpm check:python',
        url: 'https://inspect.aisi.org.uk',
      },
    ],
    openQuestion:
      'No extractor has been run, so there are no scores. The screen shows what it can measure and says plainly what it cannot.',
  },
  {
    part: 'notary',
    label: 'Notary',
    owns: 'Publication into examiner-searchable venues with provable dates.',
    deps: [
      {
        name: 'in-toto',
        role: 'attestation binding a disclosure to what was actually done to produce it',
        status: 'named',
        recordedIn: 'servers/guild/manifest.json',
        url: 'https://in-toto.io',
      },
    ],
    openQuestion:
      'No tool here publishes anything, deliberately. Disclosure drafting is reversible; publication with a provable date is not, and an MCP tool that triggered it is exactly the tool not to hand an agent.',
  },
  {
    part: 'parchment',
    label: 'Parchment',
    owns: 'Patent claims, scope, and the unclaimed space between them.',
    deps: [],
    openQuestion:
      'No upstream is decided. Every claim in this corpus carries parseUncertain: true and bounds: [] — nothing here parses a claim into machine-readable limits yet, and the scope tools refuse rather than returning an empty hit list that reads as “unencumbered”.',
  },
  {
    part: 'openlab',
    label: 'Guild',
    owns: 'The execution and advocacy network. A Chapter is one lab.',
    deps: [
      {
        name: 'ORCID',
        role: 'contributor identity, so a Common Seal binds work to a person rather than to a string',
        status: 'named',
        recordedIn: 'servers/guild/manifest.json',
        url: 'https://orcid.org',
      },
      {
        name: 'in-toto',
        role: 'the attestation format a Seal would be expressed in',
        status: 'named',
        recordedIn: 'servers/guild/manifest.json',
        url: 'https://in-toto.io',
      },
    ],
    openQuestion:
      'No chapter registry exists. The Guild server returns an empty list with a notice saying so, rather than inventing an institution to populate it.',
  },
  {
    part: 'trawl',
    label: 'Intake',
    owns: 'Ingestion, extraction, normalisation and quality assessment, over literature and patents.',
    deps: [
      {
        name: 'PaperQA2',
        role: 'parsing and passage extraction at ingest',
        status: 'named',
        recordedIn: 'CLAUDE.md',
        url: 'https://github.com/Future-House/paper-qa',
      },
      {
        name: 'Inspect AI',
        role: 'scoring an extractor run against the gold set before its output is trusted',
        status: 'named',
        recordedIn: 'packages/assay',
        url: 'https://inspect.aisi.org.uk',
      },
    ],
  },
  {
    part: 'ledger',
    label: 'Ledger',
    owns: 'Append-only change history with correction propagation.',
    deps: [
      {
        name: 'PostgreSQL',
        role: 'the append-only store — DDL generated from the Pydantic models, immutability enforced by triggers and REVOKE rather than by convention',
        status: 'ported',
        recordedIn: 'packages/core/seed',
      },
    ],
  },
  {
    part: 'runbook',
    label: 'Runbook',
    owns: 'Protocol generation with decisive-measurement selection.',
    deps: [
      {
        name: 'openferment-core',
        role: 'protocol scaling and version diff — Python because they drive physical lab work',
        status: 'ported',
        recordedIn: 'packages/core/protocol · pnpm check:protocol',
      },
    ],
  },
  {
    part: 'learn',
    label: 'Primer',
    owns: 'The teaching layer. It raises the PHOSITA baseline.',
    deps: [],
    openQuestion: 'No upstream. The curriculum is written, not generated.',
  },
];

export const UPSTREAM_BY_PART: Record<string, PartUpstream> = Object.fromEntries(
  UPSTREAM.map((u) => [u.part, u]),
);

/** Which part a route belongs to. First segment, with the demo aliases folded in. */
export function partForPath(path: string): string {
  const seg = path.replace(/^#?\//, '').split('/')[0] ?? '';
  // The Bench is the home, not a part: it shows the state of both pools rather
  // than owning a concern, so it has no upstream note. It used to claim
  // Postdoc's, which put "Postdoc will be derived from Model Context Protocol"
  // at the foot of a page that is not Postdoc.
  if (seg === '' || seg === 'bench') return '';
  return seg;
}

/** Every archetype's part, so the Bench can show what each one will rest on. */
export const ARCHETYPE_PART: Record<ArchetypeId, string> = {
  AR1: 'fermos',
  AR2: 'geneos',
  AR3: 'proforma',
  AR4: 'proforma',
  AR5: 'postdoc',
  AR6: 'fermos',
};
