// Home's opening (execution prompt §8.5): the person's projects and a way to
// make one, Postdoc's ask box, the open project's recent conversations, and
// what is running in it now, as live cards (TraceCards). Something is on
// screen at once, and the page stays visibly alive while work runs.
import { useState } from 'react';
import { MessageSquarePlus, Plus } from 'lucide-react';
import { useStore } from '@/store';
import { href, navigate } from '@/router';
import { TraceCards } from './TraceCards';
import { Button, Card, SectionTitle, cx } from './ui';

export function HomeStart() {
  const projects = useStore((s) => s.projects);
  const projectId = useStore((s) => s.projectId);
  const createProject = useStore((s) => s.createProject);
  const conversations = useStore((s) => s.liveConversations);
  const [name, setName] = useState('');
  const [problem, setProblem] = useState<string | null>(null);
  const [question, setQuestion] = useState('');

  const make = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setProblem(null);
    createProject({ name: name.trim() }).catch((err: unknown) => setProblem(err instanceof Error ? err.message : String(err)));
  };
  const ask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || !projectId) return;
    navigate(`/p/${encodeURIComponent(projectId)}/postdoc?q=${encodeURIComponent(question.trim())}`);
  };

  return (
    <section className="mb-7 space-y-5" data-testid="home-start">
      <div>
        <SectionTitle>Your projects</SectionTitle>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {(projects ?? []).map((p) => (
            <a key={p.id} href={`#/p/${encodeURIComponent(p.id)}`} data-testid="home-project" className="block">
              <Card className={cx('p-3 h-full hover:border-accent', p.id === projectId && 'border-accent')}>
                <div className="font-semibold text-body truncate">{p.name}</div>
                <div className="text-caption text-ink-soft truncate">{p.description || p.id}</div>
              </Card>
            </a>
          ))}
          <Card className="p-3">
            <form onSubmit={make} className="space-y-2" data-testid="new-project">
              <label className="text-caption uppercase tracking-wide text-ink-soft" htmlFor="new-project-name">
                New project
              </label>
              <div className="flex gap-2">
                <input id="new-project-name" className="input min-h-[36px] flex-1" value={name}
                  onChange={(e) => setName(e.target.value)} placeholder="What it studies" />
                <Button type="submit" disabled={!name.trim()}>
                  <Plus size={14} aria-hidden /> Make it
                </Button>
              </div>
              {problem && <p className="text-caption text-signal-warn">{problem}</p>}
            </form>
          </Card>
        </div>
      </div>
      {projectId && (
        <div className="grid gap-5 lg:grid-cols-2">
          <div className="min-w-0 space-y-3">
            <SectionTitle>Ask Postdoc</SectionTitle>
            <form onSubmit={ask} className="flex gap-2" data-testid="home-ask">
              <input className="input min-h-[40px] flex-1" value={question} onChange={(e) => setQuestion(e.target.value)}
                placeholder="A question about this project" aria-label="A question for Postdoc" />
              <Button type="submit" disabled={!question.trim()}>
                <MessageSquarePlus size={14} aria-hidden /> Ask
              </Button>
            </form>
            {conversations.length > 0 && (
              <ul className="space-y-1" data-testid="home-conversations">
                {conversations.slice(0, 5).map((c) => (
                  <li key={c.id} className="text-body flex items-baseline gap-2">
                    <a className="truncate hover:text-accent" href={href(`/postdoc/${c.id}`)}>
                      {c.title || c.turns[0]?.question || c.id}
                    </a>
                    <span className="text-caption text-ink-soft shrink-0">
                      {c.turns.length} turn{c.turns.length === 1 ? '' : 's'}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="min-w-0">
            <SectionTitle>Running now</SectionTitle>
            <TraceCards project={projectId} only="job" limit={6} />
          </div>
        </div>
      )}
    </section>
  );
}
