// BioRepo → Search: the papers' own words, searched.
//
// alpha 2.0 stage 1 retired openFerment's own passage index (ADR-002, ADR-010):
// Sci RAG Kit becomes the literature layer at stage 3, and this page searches
// a project's documents through it. Until then the page says what fills it.
import { Search as SearchIcon } from 'lucide-react';
import { Card, EmptyState, PageHeader } from '@/components/ui';
import { OwnerTabs } from '@/components/OwnerTabs';
import { BIOREPO_TABS } from '@/data/tabs';

export default function BioRepoSearch() {
  return (
    <div>
      <PageHeader
        title="Search the papers"
        subtitle="Passages of a project's documents, found for a question, each cited to its document and section."
      />
      <OwnerTabs tabs={BIOREPO_TABS} />
      <Card>
        <EmptyState
          icon={<SearchIcon size={20} />}
          title="No literature index yet"
          body={
            <>
              Search reads the documents a project has ingested. Documents enter through Intake into Sci RAG
              Kit, which keeps their sections, tables and passages; search here then finds passages and cites
              them. Ingest a document in Intake first.
            </>
          }
        />
      </Card>
    </div>
  );
}
