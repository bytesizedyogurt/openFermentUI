-- openFerment seed schema — GENERATED, do not edit.
--
-- Derived from the Pydantic models in
-- packages/core/openferment_core/schema/. A field added to a model becomes a
-- column here the next time this is emitted; a column edited here is a column
-- that disagrees with the model, which is the failure this migration exists to
-- remove (CLAUDE.md, "Do not hand-maintain a type in both").
--
-- Regenerate:  python3 packages/core/seed/cli.py emit --dialect postgres
-- Dialect:     postgres

CREATE FUNCTION of_append_only() RETURNS trigger
LANGUAGE plpgsql AS $of_append_only$
BEGIN
    RAISE EXCEPTION USING
        ERRCODE = 'P0001',
        MESSAGE = format('openFerment: %I is append-only. A correction is a new row that supersedes an earlier one; UPDATE and DELETE are not how this table changes.', TG_TABLE_NAME),
        HINT    = 'INSERT the corrected row with supersedes set to the row_id it replaces.';
END;
$of_append_only$;

CREATE TABLE "papers" (
    "id" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "authors" JSONB NOT NULL,
    "year" BIGINT NOT NULL,
    "venue" TEXT NOT NULL,
    "organisms" JSONB NOT NULL,
    "topics" JSONB NOT NULL,
    "abstract" TEXT NOT NULL,
    "sections" JSONB NOT NULL,
    "ingest" TEXT NOT NULL
        CHECK ("ingest" IN ('complete', 'catalogued', 'stage:fetch', 'stage:parse', 'stage:chunk', 'stage:embed', 'stage:extract', 'failed:fetch', 'failed:parse', 'shelf')),
    "thread" TEXT NOT NULL
        CHECK ("thread" IN ('A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O')),
    "source_type" TEXT NOT NULL
        CHECK ("source_type" IN ('journal-article', 'review', 'thesis', 'patent', 'book', 'industry-report', 'preprint')),
    "doi" TEXT,
    "pmcid" TEXT,
    "pmid" TEXT,
    "text_source" TEXT NOT NULL CHECK ("text_source" IN ('full-text', 'curation-note')),
    "open_access" BOOLEAN NOT NULL,
    "tranche" SMALLINT NOT NULL CHECK ("tranche" IN (1, 2, 3)),
    "verify_needed" BOOLEAN,
    "corpus_role" TEXT,
    "coverage_disputed" JSONB,
    CONSTRAINT "papers_pk" PRIMARY KEY ("id")
);

COMMENT ON TABLE "papers" IS 'Corpus entries (OF-COR-001 §1).';

COMMENT ON COLUMN "papers"."id" IS 'Corpus entry id, e.g. ''H1'' — thread letter plus index (OF-COR-001 §1).';

COMMENT ON COLUMN "papers"."year" IS '0 where the year is genuinely unknown. A sentinel rather than a guess: see invariant 4 in CLAUDE.md.';

COMMENT ON COLUMN "papers"."abstract" IS 'For ''catalogued'' papers this is the curator''s summary from OF-COR-001, NOT the publisher''s abstract. `textSource` says which.';

COMMENT ON COLUMN "papers"."doi" IS 'The authoritative record key — never the author string (OF-COR-001 header).';

COMMENT ON COLUMN "papers"."text_source" IS 'Whether `sections` hold the paper''s own text or the curator''s notes.';

COMMENT ON COLUMN "papers"."open_access" IS 'Openly retrievable vs. needs institutional access (OF-COR-001 §19).';

COMMENT ON COLUMN "papers"."tranche" IS 'Ingestion tranche: 1 = open-access core, 2 = remainder, 3 = v1.1.';

COMMENT ON COLUMN "papers"."verify_needed" IS 'Author string not fully resolved — must be checked at ingest ([verify]).';

COMMENT ON COLUMN "papers"."corpus_role" IS 'Why this entry earns its place, from the corpus document.';

COMMENT ON COLUMN "papers"."coverage_disputed" IS 'A reader filed "something''s missing" against this source (OF-FE-003 §8.4). Recall failure is the failure that hides: a wrong value gets clicked and corrected, a missed one is invisible forever. This flag is the only thing in the system that surfaces it, so it returns the source to the review queue rather than sitting as a passive annotation.';

CREATE TABLE "records" (
    "row_id" BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    "id" TEXT NOT NULL,
    "paper_id" TEXT NOT NULL,
    "section_id" TEXT NOT NULL,
    "quote" TEXT NOT NULL,
    "field" TEXT NOT NULL
        CHECK ("field" IN ('expression_pct_tsp', 'titer_intracellular', 'titer_secreted', 'secreted_fraction', 'fold_improvement', 'transformation_efficiency', 'time_to_colony', 'phosphate_count', 'phosphorylation_degree', 'phospho_site_position', 'glycan_species', 'kinase_identity', 'micelle_diameter', 'micellar_fraction', 'gelation_ph', 'calcium_binding', 'melt_stretch_length', 'growth_rate_mu', 'final_biomass_density', 'volumetric_productivity', 'medium_component_conc', 'disruption_protein_yield', 'disruption_energy', 'minimum_selling_price')),
    "value_num" DOUBLE PRECISION,
    "value_txt" TEXT,
    "unit" TEXT NOT NULL,
    "si" JSONB NOT NULL,
    "confidence" DOUBLE PRECISION NOT NULL,
    "status" TEXT NOT NULL CHECK ("status" IN ('unverified', 'verified', 'rejected')),
    "provenance" TEXT NOT NULL
        CHECK ("provenance" IN ('gold', 'verified', 'curated', 'unverified', 'user', 'industry-estimate', 'demo', 'unsourced')),
    "organism" TEXT,
    "component_tag" TEXT,
    "gold" JSONB,
    "gold_only" BOOLEAN,
    "extractor_run" TEXT CHECK ("extractor_run" IN ('v0.3', 'v0.4', 'v0.4r')),
    "reject_reason" TEXT,
    "corrected" JSONB,
    "reviewer" TEXT,
    "is_primary" BOOLEAN NOT NULL,
    "evidence_class" TEXT NOT NULL
        CHECK ("evidence_class" IN ('literature', 'patent', 'computed', 'experiment', 'correction')),
    "cites_record_id" TEXT,
    "method" TEXT
        CHECK ("method" IN ('LC-ESI-MS', 'MALDI-MS', 'Phos-tag', 'urea-PAGE', 'urea-PAGE + phosphatase', 'SDS-PAGE mobility', 'Ethyl Stains-All', 'CD spectroscopy', 'SAXS', 'SANS', 'DLS', 'cryo-TEM', 'HPLC', 'gravimetric', 'spectrophotometric', 'process model', 'undetermined')),
    "numbering" TEXT CHECK ("numbering" IN ('precursor', 'mature')),
    "curation_ref" TEXT,
    "range" JSONB,
    "comparative_baseline" TEXT,
    "negative_result" BOOLEAN,
    "supersedes" BIGINT REFERENCES "records" ("row_id"),
    "inserted_at" TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT "records_supersedes_key" UNIQUE ("supersedes"),
    CONSTRAINT "records_value_one_arm" CHECK (((CASE WHEN "value_num" IS NULL THEN 0 ELSE 1 END) + (CASE WHEN "value_txt" IS NULL THEN 0 ELSE 1 END)) = 1)
);

CREATE INDEX "records_id_idx" ON "records" ("id");

CREATE INDEX "records_paper_id_idx" ON "records" ("paper_id");

CREATE TRIGGER "records_append_only"
BEFORE UPDATE OR DELETE ON "records"
FOR EACH ROW EXECUTE FUNCTION of_append_only();

CREATE TRIGGER "records_append_only_truncate"
BEFORE TRUNCATE ON "records"
FOR EACH STATEMENT EXECUTE FUNCTION of_append_only();

REVOKE UPDATE, DELETE, TRUNCATE ON TABLE "records" FROM PUBLIC;

CREATE VIEW "records_current" AS
SELECT "r".* FROM "records" AS "r"
WHERE NOT EXISTS (SELECT 1 FROM "records" AS "s" WHERE "s"."supersedes" = "r"."row_id");

COMMENT ON TABLE "records" IS 'Extraction records. APPEND-ONLY: a correction is a new row whose `supersedes` points at the row it replaces.';

COMMENT ON COLUMN "records"."row_id" IS 'Surrogate key. `ExtractionRecord.id` stops being unique the moment a correction is appended — the corrected row carries the SAME record id — so the natural key cannot be the primary key. Nothing outside this table''s own supersession chain refers to a row_id.';

COMMENT ON COLUMN "records"."value_num" IS 'Categorical fields (kinase_identity, glycan_species) carry a string. [the double arm of `value`]';

COMMENT ON COLUMN "records"."value_txt" IS 'Categorical fields (kinase_identity, glycan_species) carry a string. [the text arm of `value`]';

COMMENT ON COLUMN "records"."provenance" IS 'Explicit provenance. Extractor output is ''unverified'' until reviewed; values transcribed from OF-COR-001 are ''curated''; market figures are ''industry-estimate'' and never enter the gold set.';

COMMENT ON COLUMN "records"."extractor_run" IS 'Absent for curated records — they did not come from an extractor run.';

COMMENT ON COLUMN "records"."is_primary" IS 'False. This paper is quoting someone else''s measurement (OF-COR-001 §19, fifth trap). Citation-of-a-citation is the most common false-independence error in literature aggregation: 15 mg/L appears in both C2 (the measurement) and C6 (a citation of it), and a strip plot that counts both overstates consensus. Aggregate statistics must filter on this.';

COMMENT ON COLUMN "records"."evidence_class" IS 'What kind of thing produced this value. Every seeded record is ''literature''; the field is required so that a prediction written by geneOS or a measurement deposited by openLab cannot enter the store wearing the same face as a paper. `check:seed` enforces its presence.';

COMMENT ON COLUMN "records"."cites_record_id" IS 'When not primary, the record this one is quoting.';

COMMENT ON COLUMN "records"."method" IS 'How the value was measured. Mandatory for PTM and functional fields (OF-COR-001 §17 Rule 1) — ''undetermined'' is a legitimate answer and means the analysis was never done, not that the result was negative.';

COMMENT ON COLUMN "records"."numbering" IS 'Required on phospho_site_position — mature and precursor differ by 15.';

COMMENT ON COLUMN "records"."curation_ref" IS 'Where in OF-COR-001 a ''curated'' value was transcribed from, e.g. ''§9 H4''.';

COMMENT ON COLUMN "records"."range" IS 'A value the source states as a range rather than a point.';

COMMENT ON COLUMN "records"."comparative_baseline" IS 'For comparative claims ("12-fold higher than X"), the baseline.';

COMMENT ON COLUMN "records"."negative_result" IS 'Value is a reported negative/absent result, not a missing measurement.';

COMMENT ON COLUMN "records"."supersedes" IS 'The correction link, pointing BACKWARD from the new row to the one it replaces. Backward because the alternative — a `superseded_by` on the older row — would have to be filled in by an UPDATE, and UPDATE is exactly what this table forbids. UNIQUE, so a chain cannot fork and leave `records_current` ambiguous.';

COMMENT ON COLUMN "records"."inserted_at" IS 'When the row reached the store. NOT the same clock as `AuditEvent.at`, which is corpus data about when a curator acted; this one is the database''s own record of arrival order and is the only thing that can order two rows the loader wrote in the same batch.';

CREATE TABLE "ontology" (
    "id" TEXT NOT NULL
        CHECK ("id" IN ('expression_pct_tsp', 'titer_intracellular', 'titer_secreted', 'secreted_fraction', 'fold_improvement', 'transformation_efficiency', 'time_to_colony', 'phosphate_count', 'phosphorylation_degree', 'phospho_site_position', 'glycan_species', 'kinase_identity', 'micelle_diameter', 'micellar_fraction', 'gelation_ph', 'calcium_binding', 'melt_stretch_length', 'growth_rate_mu', 'final_biomass_density', 'volumetric_productivity', 'medium_component_conc', 'disruption_protein_yield', 'disruption_energy', 'minimum_selling_price')),
    "family" TEXT NOT NULL
        CHECK ("family" IN ('expression', 'ptm', 'functional', 'cultivation', 'downstream')),
    "name" TEXT NOT NULL,
    "definition" TEXT NOT NULL,
    "canonical_unit" TEXT NOT NULL,
    "range" JSONB NOT NULL CHECK (jsonb_array_length("range") = 2),
    "notes" TEXT NOT NULL,
    "categorical" BOOLEAN,
    "requires_method" BOOLEAN,
    "refuse_conversion_to" JSONB,
    CONSTRAINT "ontology_pk" PRIMARY KEY ("id")
);

COMMENT ON TABLE "ontology" IS 'Parameter ontology v1 (§17).';

COMMENT ON COLUMN "ontology"."canonical_unit" IS ''''' for categorical fields (kinase_identity, glycan_species).';

COMMENT ON COLUMN "ontology"."categorical" IS 'Categorical fields hold a string value, not a number.';

COMMENT ON COLUMN "ontology"."requires_method" IS 'OF-COR-001 §17 Rule 1: a value without its method is not interpretable.';

COMMENT ON COLUMN "ontology"."refuse_conversion_to" IS 'Unit families this field must NOT be auto-converted into, with the reason. OF-COR-001 §17 Rule 2: %TSP and g/L are not interconvertible without cell density and total-protein fraction. The engine refuses and says why.';

CREATE TABLE "strains" (
    "id" TEXT NOT NULL,
    "binomial" TEXT NOT NULL,
    "designation" TEXT NOT NULL,
    "taxonomy" JSONB NOT NULL,
    "description" TEXT NOT NULL,
    "badges" JSONB NOT NULL,
    "bsl" SMALLINT NOT NULL CHECK ("bsl" IN (1, 2)),
    "notes" JSONB NOT NULL,
    CONSTRAINT "strains_pk" PRIMARY KEY ("id")
);

COMMENT ON TABLE "strains" IS 'Hosts a measurement was made in.';

CREATE TABLE "protocols" (
    "id" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "category" TEXT NOT NULL
        CHECK ("category" IN ('media', 'culture', 'analytics', 'harvest', 'fermentation', 'sop')),
    "organisms" JSONB NOT NULL,
    "bsl" SMALLINT NOT NULL CHECK ("bsl" IN (1, 2)),
    "purpose" TEXT NOT NULL,
    "versions" JSONB NOT NULL,
    "current_version" TEXT NOT NULL,
    "provenance_note" TEXT NOT NULL,
    CONSTRAINT "protocols_pk" PRIMARY KEY ("id")
);

COMMENT ON TABLE "protocols" IS 'Protocols and their versions.';

CREATE TABLE "scenarios" (
    "id" TEXT NOT NULL,
    "model_id" TEXT NOT NULL CHECK ("model_id" IN ('S1', 'S2', 'S3')),
    "name" TEXT NOT NULL,
    "description" TEXT NOT NULL,
    "product" TEXT NOT NULL,
    "dims" JSONB NOT NULL,
    "point" JSONB NOT NULL,
    "assumptions" JSONB NOT NULL,
    "pinned" BOOLEAN NOT NULL,
    CONSTRAINT "scenarios_pk" PRIMARY KEY ("id")
);

COMMENT ON TABLE "scenarios" IS 'Cost scenarios. COST_MODELS stays in TS.';

CREATE TABLE "learn_modules" (
    "id" TEXT NOT NULL,
    "index" BIGINT NOT NULL,
    "title" TEXT NOT NULL,
    "blurb" TEXT NOT NULL,
    "lessons" JSONB NOT NULL,
    "outline" JSONB,
    CONSTRAINT "learn_modules_pk" PRIMARY KEY ("id")
);

COMMENT ON TABLE "learn_modules" IS 'Learn track modules.';

COMMENT ON COLUMN "learn_modules"."index" IS 'Ordering index of the module within the Learn track.';

COMMENT ON COLUMN "learn_modules"."outline" IS 'Planned lesson headings for a module whose lessons are not written yet. An empty `lessons` list with an outline is a stated gap, not a defect.';

CREATE TABLE "audit_event" (
    "record_row_id" BIGINT NOT NULL REFERENCES "records" ("row_id"),
    "ordinal" BIGINT NOT NULL,
    "at" TEXT NOT NULL,
    "who" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "from" JSONB,
    "to" JSONB,
    CONSTRAINT "audit_event_pk" PRIMARY KEY ("record_row_id", "ordinal")
);

CREATE TRIGGER "audit_event_append_only"
BEFORE UPDATE OR DELETE ON "audit_event"
FOR EACH ROW EXECUTE FUNCTION of_append_only();

CREATE TRIGGER "audit_event_append_only_truncate"
BEFORE TRUNCATE ON "audit_event"
FOR EACH STATEMENT EXECUTE FUNCTION of_append_only();

REVOKE UPDATE, DELETE, TRUNCATE ON TABLE "audit_event" FROM PUBLIC;

COMMENT ON TABLE "audit_event" IS 'One AuditEvent, mirroring `ExtractionRecord.audit`. Append-only: the audit trail of an append-only table cannot itself be editable.';

COMMENT ON COLUMN "audit_event"."record_row_id" IS 'Parent link for the externalised array. Points at the ROW, not at the record id: two rows may share a record id across a correction, and an audit event belongs to one of them.';

COMMENT ON COLUMN "audit_event"."ordinal" IS 'Position in `ExtractionRecord.audit`. A JSON array is ordered and SQL rows are not, so without this the trail comes back in whatever order the plan produced and the record no longer round-trips.';
