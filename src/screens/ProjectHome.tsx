// A project's home (execution prompt §8.5): the conversation on the left, the
// live trace and its cards on the right, and every view of the project one
// click away. The module screens are views inside the project:
// `/p/:project/<view>` opens one with the project open (router.tsx).
import { useStore } from '@/store';
import { href } from '@/router';
import { PageHeader } from '@/components/ui';
import { TraceCards } from '@/components/TraceCards';
import Postdoc from './Postdoc';

const VIEWS: { label: string; to: string }[] = [
  { label: 'Literature', to: '/intake' },
  { label: 'Records', to: '/biorepo' },
  { label: 'Flowsheets', to: '/proforma' },
  { label: 'Runs and studies', to: '/proforma/studies' },
  { label: 'fermOS', to: '/fermos' },
  { label: 'pureOS', to: '/pureos' },
  { label: 'geneOS', to: '/geneos' },
  { label: 'Runbooks', to: '/runbooks' },
  { label: 'Guild', to: '/guild' },
  { label: 'Primer', to: '/primer' },
  { label: 'Settings', to: '/settings' },
];

export function ProjectHome({ project }: { project: string }) {
  const projects = useStore((s) => s.projects);
  const held = projects?.find((p) => p.id === project);
  return (
    <div className="space-y-4" data-testid="project-home">
      <PageHeader
        eyebrow="Project"
        title={held?.name ?? project}
        subtitle={held?.description || 'Its documents, records, flowsheets, runs, studies, conversations and ledger.'}
      />
      <nav className="flex flex-wrap gap-2" aria-label="The project's views">
        {VIEWS.map((v) => (
          <a key={v.to} className="chip" href={href(v.to)} data-testid="project-view">
            {v.label}
          </a>
        ))}
      </nav>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div className="min-w-0">
          <Postdoc />
        </div>
        <aside className="min-w-0" aria-label="As it happens">
          <TraceCards project={project} />
        </aside>
      </div>
    </div>
  );
}
