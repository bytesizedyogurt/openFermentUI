// Guild · People (OF-BLD-013 §1.4). The list of who is on the ledger, and one
// person's ledger: a bar per skill family, every skill with its level, and
// every entry recorded about them, newest first, withdrawn ones included.
import { useState } from 'react';
import { UserPlus } from 'lucide-react';
import { useStore } from '@/store';
import { FAMILIES, SKILLS } from '@/data/skills';
import type { GuildPerson, GuildRole } from '@/data/types';
import { Button, Card, EmptyState, LinkButton, SectionTitle, cx } from '@/components/ui';
import {
  AddPersonForm,
  EvidenceRow,
  ExportLedgerButton,
  GuildHeader,
  SignoffSheet,
  useGuild,
  type GuildContext,
} from '@/components/GuildBits';
import { LevelGlyph, levelLabel } from '@/components/LevelGlyph';
import { daysBetween, isAssessor, statusOf } from '@/engine/competence';
import { href, navigate } from '@/router';

const ROLE_LABEL: Record<GuildRole, string> = { member: 'Member', lead: 'Lead', auditor: 'Auditor' };

export default function GuildPeople({ personId }: { personId?: string }) {
  const ctx = useGuild();
  if (personId) return <Ledger ctx={ctx} personId={personId} />;
  return <PeopleIndex ctx={ctx} />;
}

function PeopleIndex({ ctx }: { ctx: GuildContext }) {
  const loadSample = useStore((s) => s.guildLoadSample);
  const [adding, setAdding] = useState(false);
  const isLead = ctx.acting?.role === 'lead';
  return (
    <>
      <GuildHeader title="People" subtitle="Everyone on the ledger, what they hold, and when anyone last recorded anything about them." />
      {ctx.guild.people.length === 0 ? (
        <Card className="max-w-2xl">
          <EmptyState title="Nobody is on the ledger yet" body="Start it with yourself as its lead, or look around with a sample team first." />
          <div className="px-6 pb-6 space-y-4">
            <AddPersonForm />
            <div className="border-t border-line pt-3">
              <Button onClick={loadSample}>Show a sample team</Button>
            </div>
          </div>
        </Card>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            {!adding && (
              <Button onClick={() => setAdding(true)} disabled={!isLead} title={isLead ? undefined : 'Only the lead adds people'}>
                <UserPlus size={14} /> Add person
              </Button>
            )}
            {!isLead && <span className="text-caption text-ink-soft">Only the lead adds people. Choose the lead with Acting as.</span>}
          </div>
          {adding && (
            <Card className="p-4 max-w-2xl">
              <SectionTitle right={<Button size="sm" onClick={() => setAdding(false)}>Done</Button>}>Add someone</SectionTitle>
              <AddPersonForm />
            </Card>
          )}
          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-body border-collapse min-w-[680px]">
                <thead>
                  <tr className="border-b border-line text-left text-caption uppercase tracking-wide text-ink-soft">
                    <th className="px-4 py-2 font-normal">Person</th>
                    <th className="px-3 py-2 font-normal">Role</th>
                    <th className="px-3 py-2 font-normal text-right">Qualified</th>
                    <th className="px-3 py-2 font-normal text-right">Assessor on</th>
                    <th className="px-3 py-2 font-normal text-right">Lapsed or suspended</th>
                    <th className="px-4 py-2 font-normal text-right">Last entry</th>
                  </tr>
                </thead>
                <tbody>
                  {ctx.guild.people.map((p) => {
                    const sts = SKILLS.map((s) => statusOf(ctx.status, p.id, s.id));
                    const q = sts.filter((x) => x.effective >= 3).length;
                    const a = sts.filter((x) => x.effective === 4).length;
                    const flagged = sts.filter((x) => x.lapsed || x.suspended).length;
                    const last = ctx.guild.evidence
                      .filter((e) => e.personId === p.id)
                      .map((e) => e.at.slice(0, 10))
                      .sort()
                      .pop();
                    return (
                      <tr
                        key={p.id}
                        className={cx('border-b border-line last:border-b-0 hover:bg-ink-soft/[0.03] cursor-pointer', !p.active && 'opacity-60')}
                        onClick={() => navigate(`/guild/people/${p.id}`)}
                      >
                        <td className="px-4 py-2">
                          <a className="hover:text-accent" href={href(`/guild/people/${p.id}`)} onClick={(e) => e.stopPropagation()}>
                            {p.name}
                          </a>
                          <div className="text-caption text-ink-soft">
                            {p.title}
                            {!p.active && ' · no longer active'}
                          </div>
                        </td>
                        <td className="px-3 py-2">{ROLE_LABEL[p.role]}</td>
                        <td className="px-3 py-2 text-right font-num">{p.role === 'auditor' ? '·' : q}</td>
                        <td className="px-3 py-2 text-right font-num">{a || '·'}</td>
                        <td className={cx('px-3 py-2 text-right font-num', flagged > 0 && 'text-signal-warn')}>{flagged || '·'}</td>
                        <td className="px-4 py-2 text-right font-num text-ink-soft">{last ?? 'none'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </>
  );
}

function Ledger({ ctx, personId }: { ctx: GuildContext; personId: string }) {
  const [pairSkill, setPairSkill] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const person = ctx.personById.get(personId);

  if (!person) {
    return (
      <>
        <GuildHeader title="People" subtitle="Everyone on the ledger." />
        <Card className="max-w-2xl">
          <EmptyState
            title="Nobody by that id"
            body={`${personId} is not on the ledger this browser holds. If the sample team was shown when this link was made, it is gone after a reload.`}
            action={<LinkButton to="/guild/people">All people</LinkButton>}
          />
        </Card>
      </>
    );
  }

  const entries = ctx.guild.evidence.filter((e) => e.personId === personId).slice().reverse();
  const shown = showAll ? entries : entries.slice(0, 15);

  return (
    <>
      <GuildHeader title={person.name} subtitle={`${person.title || ROLE_LABEL[person.role]} · joined ${person.joinedAt.slice(0, 10)}`} />
      <div className="space-y-5">
        <div className="flex flex-wrap items-center gap-2">
          <ExportLedgerButton ctx={ctx} personId={personId} />
          <a className="text-accent hover:underline text-body" href={href('/guild/people')}>
            All people
          </a>
        </div>

        {ctx.acting?.role === 'lead' && <PersonSettings person={person} />}

        {person.role !== 'auditor' && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {FAMILIES.map((f) => {
                const fs = SKILLS.filter((s) => s.family === f.id);
                const q = fs.filter((s) => statusOf(ctx.status, personId, s.id).effective >= 3).length;
                return (
                  <Card key={f.id} className="p-3">
                    <div className="text-caption uppercase tracking-wide text-ink-soft">{f.short}</div>
                    <div className="font-num text-section-title mt-1">
                      {q}
                      <span className="text-ink-soft text-body"> of {fs.length}</span>
                    </div>
                    <div className="flex gap-0.5 mt-2" aria-hidden>
                      {fs.map((s) => {
                        const st = statusOf(ctx.status, personId, s.id);
                        return (
                          <span
                            key={s.id}
                            className={cx(
                              'h-1.5 flex-1 rounded-full',
                              st.effective >= 3
                                ? 'bg-accent'
                                : st.level >= 2 || st.lapsed || st.suspended
                                  ? 'bg-signal-info/60'
                                  : st.level === 1
                                    ? 'bg-signal-info/25'
                                    : 'bg-ink-soft/15',
                            )}
                          />
                        );
                      })}
                    </div>
                  </Card>
                );
              })}
            </div>

            <div>
              <SectionTitle>Skills</SectionTitle>
              <Card>
                <div className="overflow-x-auto">
                  <table className="w-full text-body border-collapse min-w-[680px]">
                    <thead>
                      <tr className="border-b border-line text-left text-caption uppercase tracking-wide text-ink-soft">
                        <th className="px-4 py-2 font-normal">Skill</th>
                        <th className="px-3 py-2 font-normal">Level</th>
                        <th className="px-3 py-2 font-normal">Confidence</th>
                        <th className="px-3 py-2 font-normal">Last performed</th>
                        <th className="px-3 py-2 font-normal">Lapses</th>
                        <th className="px-4 py-2 font-normal text-right">Supervised runs</th>
                      </tr>
                    </thead>
                    {FAMILIES.map((f) => (
                      <tbody key={f.id}>
                        <tr>
                          <td colSpan={6} className="px-4 pt-3 pb-1 text-caption uppercase tracking-wide text-ink-soft">
                            {f.name}
                          </td>
                        </tr>
                        {SKILLS.filter((s) => s.family === f.id).map((s) => {
                          const st = statusOf(ctx.status, personId, s.id);
                          const soon = st.lapsesAt && !st.lapsed && daysBetween(ctx.today, st.lapsesAt) <= 30;
                          return (
                            <tr
                              key={s.id}
                              className="border-t border-line hover:bg-ink-soft/[0.03] cursor-pointer"
                              onClick={() => setPairSkill(s.id)}
                            >
                              <td className="px-4 py-2">
                                <button type="button" className="text-left hover:text-accent" onClick={() => setPairSkill(s.id)}>
                                  {s.name}
                                </button>
                              </td>
                              <td className="px-3 py-2">
                                <span className="inline-flex items-center gap-1.5">
                                  <LevelGlyph status={st} size={12} /> {levelLabel(st)}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-ink-soft">{st.level > 0 ? st.confidence : '·'}</td>
                              <td className="px-3 py-2 font-num text-ink-soft">{st.lastPerformedAt ?? '·'}</td>
                              <td className={cx('px-3 py-2 font-num', st.lapsed || soon ? 'text-signal-warn' : 'text-ink-soft')}>
                                {st.lapsesAt ?? '·'}
                              </td>
                              <td className="px-4 py-2 font-num text-right text-ink-soft">
                                {isAssessor(ctx.status, personId, s.id) ? '·' : `${st.supervisedCount} of ${s.supervisedRuns}`}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    ))}
                  </table>
                </div>
              </Card>
            </div>
          </>
        )}

        <div>
          <SectionTitle right={<span className="text-caption text-ink-soft font-num">{entries.length} entries</span>}>Entries</SectionTitle>
          <Card className="px-4 py-1">
            {entries.length === 0 ? (
              <p className="py-3 text-body text-ink-soft">Nothing recorded yet. Open a skill above to record a sign-off.</p>
            ) : (
              <div className="divide-y divide-line">
                {shown.map((e) => (
                  <EvidenceRow key={e.id} e={e} ctx={ctx} showSkill />
                ))}
              </div>
            )}
            {entries.length > shown.length && (
              <div className="py-2">
                <Button size="sm" onClick={() => setShowAll(true)}>
                  Show all {entries.length}
                </Button>
              </div>
            )}
          </Card>
        </div>
      </div>
      <SignoffSheet personId={pairSkill ? personId : null} skillId={pairSkill} onClose={() => setPairSkill(null)} />
    </>
  );
}

/** What the lead can change about a person: title, role, whether they are active. */
function PersonSettings({ person }: { person: GuildPerson }) {
  const update = useStore((s) => s.guildUpdatePerson);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState(person.title);
  const [role, setRole] = useState<GuildRole>(person.role);
  const [active, setActive] = useState(person.active);
  if (!open)
    return (
      <Button size="sm" onClick={() => setOpen(true)}>
        Change title, role or status
      </Button>
    );
  return (
    <Card className="p-4 max-w-2xl space-y-2">
      <div className="grid sm:grid-cols-3 gap-2">
        <label className="text-caption text-ink-soft flex flex-col gap-1">
          Title
          <input id="edit-title" className="input text-body" value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label className="text-caption text-ink-soft flex flex-col gap-1">
          Role
          <select id="edit-role" className="input text-body" value={role} onChange={(e) => setRole(e.target.value as GuildRole)}>
            <option value="member">Member</option>
            <option value="lead">Lead</option>
            <option value="auditor">Auditor</option>
          </select>
        </label>
        <label className="text-caption text-ink-soft flex items-center gap-2 mt-5">
          <input id="edit-active" type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
          Active on the team
        </label>
      </div>
      <div className="flex gap-2">
        <Button
          variant="primary"
          onClick={async () => {
            if (await update({ ...person, title: title.trim(), role, active })) setOpen(false);
          }}
        >
          Save
        </Button>
        <Button onClick={() => setOpen(false)}>Cancel</Button>
      </div>
    </Card>
  );
}
