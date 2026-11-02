// The project this page acts in (alpha 2.0, ADR-005): which one is open, the
// others the service holds, and a new one. Every record, run, runbook and
// conversation the service keeps belongs to a project, and every call to the
// service names the open one (lib/project.ts).
import { useState, type FormEvent } from 'react';
import { Check, FolderOpen } from 'lucide-react';
import { useStore } from '@/store';
import { Popover, cx } from './ui';

/** The projects held, the open one marked, and the form for a new one. */
export function ProjectChooser() {
  const projects = useStore((s) => s.projects);
  const problem = useStore((s) => s.projectsProblem);
  const projectId = useStore((s) => s.projectId);
  const openProject = useStore((s) => s.openProject);
  const createProject = useStore((s) => s.createProject);
  const reviewer = useStore((s) => s.reviewer.trim());
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false);
  const [refused, setRefused] = useState<string | null>(null);

  const make = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setRefused(null);
    try {
      await createProject({ name: name.trim(), description: description.trim() });
    } catch (err) {
      setRefused(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3" data-testid="project-chooser">
      {problem && <div className="text-caption text-signal-error">The projects could not be listed: {problem}</div>}
      {projects && projects.length > 0 && (
        <ul className="space-y-1" aria-label="Projects">
          {projects.map((p) => (
            <li key={p.id}>
              <button
                className={cx(
                  'w-full text-left rounded-btn px-2 py-1.5 border transition-colors',
                  p.id === projectId ? 'border-accent/40 bg-accent-wash' : 'border-line hover:border-accent/40',
                )}
                onClick={() => openProject(p.id)}
                aria-current={p.id === projectId ? 'true' : undefined}
              >
                <span className="flex items-center gap-1.5 font-medium">
                  {p.id === projectId && <Check size={13} className="text-accent shrink-0" />}
                  <span className="truncate">{p.name}</span>
                </span>
                <span className="block text-caption text-ink-soft truncate">
                  {p.description || `made by ${p.createdBy}`}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <form className="space-y-2" onSubmit={make} aria-label="New project">
        <div className="text-caption text-ink-soft">New project</div>
        <input
          className="input w-full"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Name"
          aria-label="Project name"
          maxLength={120}
        />
        <textarea
          className="input w-full min-h-[56px]"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What it is for (optional)"
          aria-label="Project description"
          maxLength={2000}
        />
        <button className="btn btn-sm btn-primary" type="submit" disabled={!name.trim() || !reviewer || busy}>
          Make it and open it
        </button>
        {!reviewer && (
          <p className="text-caption text-ink-soft">
            A project is made in a person&rsquo;s name: set your reviewer name in{' '}
            <a className="underline" href="#/settings/corpus">
              Settings
            </a>{' '}
            first.
          </p>
        )}
        {refused && <p className="text-caption text-signal-error">{refused}</p>}
      </form>
    </div>
  );
}

/** The open project's name in the top bar, opening the chooser. */
export function ProjectSwitch() {
  const projects = useStore((s) => s.projects);
  const projectId = useStore((s) => s.projectId);
  const name = projects?.find((p) => p.id === projectId)?.name ?? projectId ?? 'No project open';
  return (
    <Popover
      openOnHover={false}
      width={340}
      label="Projects"
      trigger={(p) => (
        <button {...p} className="btn btn-sm min-w-0" title="The project this page acts in" data-testid="project-switch">
          <FolderOpen size={14} className="shrink-0" />
          <span className={cx('truncate max-w-[12rem]', !projectId && 'text-signal-warn')}>{name}</span>
        </button>
      )}
    >
      <ProjectChooser />
    </Popover>
  );
}

/**
 * Above every screen while the service holds projects and none is open: the
 * screens that read the service then say what is missing rather than show a
 * project's work nobody chose.
 */
export function ProjectNeeded() {
  const projectId = useStore((s) => s.projectId);
  const projects = useStore((s) => s.projects);
  if (projectId || projects === null) return null;
  return (
    <section className="card p-4 mb-4 max-w-[720px]" data-testid="project-needed" aria-label="No project open">
      <div className="font-medium">No project is open</div>
      <p className="text-body text-ink-soft mt-1">
        Every record, run, runbook and conversation the service keeps belongs to a project.{' '}
        {projects.length ? 'Open one, or make another.' : 'Make the first one.'}
      </p>
      <div className="mt-3">
        <ProjectChooser />
      </div>
    </section>
  );
}
