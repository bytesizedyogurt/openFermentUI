// Guild · Skills (OF-BLD-013 §1.4). What each skill is, what an assessor
// watches for, which protocol steps need it, and who holds it at each level.
// Skills are reference data: their definitions change by commit to
// src/data/skills.ts, so every ledger entry points at a definition someone can
// read in the history.
import type { ReactNode } from 'react';
import { Card, EmptyState, LinkButton, SectionTitle, cx } from '@/components/ui';
import { GuildHeader, useGuild } from '@/components/GuildBits';
import { LevelGlyph } from '@/components/LevelGlyph';
import { FAMILIES, FAMILY_BY_ID, SKILLS, SKILL_BY_ID } from '@/data/skills';
import { PROTOCOLS } from '@/data/protocols';
import { LEVEL_NAME, statusOf, type Level } from '@/engine/competence';
import { renderStepText } from '@/engine/scale';
import { href } from '@/router';

export default function GuildSkills({ skillId }: { skillId?: string }) {
  if (skillId) return <SkillPage skillId={skillId} />;
  return <SkillsIndex />;
}

function SkillsIndex() {
  const ctx = useGuild();
  return (
    <>
      <GuildHeader
        title="Skills"
        subtitle="The trunk skills that protocol steps need. Working definitions until the skills content pass."
      />
      <div className="space-y-5 max-w-[960px]">
        {FAMILIES.map((f) => (
          <div key={f.id}>
            <SectionTitle>{f.name}</SectionTitle>
            <Card>
              {SKILLS.filter((s) => s.family === f.id).map((s) => {
                const current = ctx.members.filter((m) => statusOf(ctx.status, m.id, s.id).effective >= 3).length;
                const assessors = ctx.members.filter((m) => statusOf(ctx.status, m.id, s.id).effective === 4).length;
                return (
                  <a
                    key={s.id}
                    href={href(`/guild/skills/${s.id}`)}
                    className="flex flex-wrap items-baseline gap-x-4 gap-y-1 px-4 py-3 border-b border-line last:border-b-0 hover:bg-ink-soft/[0.03]"
                  >
                    <span className="font-medium min-w-[180px]">{s.name}</span>
                    <span className="text-body text-ink-soft flex-1 min-w-[220px]">{s.summary}</span>
                    <span className="text-caption font-num text-ink-soft">
                      {current} can run it alone · {assessors} assessor{assessors === 1 ? '' : 's'}
                    </span>
                    {s.criticality === 'critical' && <span className="chip text-signal-warn border-signal-warn/40">critical</span>}
                  </a>
                );
              })}
            </Card>
          </div>
        ))}
      </div>
    </>
  );
}

const LADDER: Level[] = [4, 3, 2, 1];

function SkillPage({ skillId }: { skillId: string }) {
  const ctx = useGuild();
  const skill = SKILL_BY_ID[skillId];
  if (!skill) {
    return (
      <>
        <GuildHeader title="Skills" subtitle="The trunk skills that protocol steps need." />
        <Card className="max-w-2xl">
          <EmptyState title="No such skill" body={`${skillId} is not in src/data/skills.ts.`} action={<LinkButton to="/guild/skills">All skills</LinkButton>} />
        </Card>
      </>
    );
  }
  const uses = PROTOCOLS.flatMap((p) => {
    const v = p.versions.find((x) => x.version === p.currentVersion) ?? p.versions[0];
    return v.steps.filter((st) => st.skills?.includes(skillId)).map((st) => ({ p, st, v }));
  });

  return (
    <>
      <GuildHeader title={skill.name} subtitle={`${FAMILY_BY_ID[skill.family]?.name} · ${skill.summary}`} />
      <div className="grid lg:grid-cols-[minmax(0,1fr)_320px] gap-5">
        <div className="space-y-5 min-w-0">
          <div>
            <SectionTitle>What an assessor watches for</SectionTitle>
            <Card className="p-4">
              <ol className="space-y-2 list-decimal pl-5">
                {skill.mastery.map((m) => (
                  <li key={m} className="text-reading">
                    {m}
                  </li>
                ))}
              </ol>
            </Card>
          </div>
          <div>
            <SectionTitle right={<span className="text-caption text-ink-soft font-num">{uses.length} steps</span>}>Steps that need it</SectionTitle>
            <Card>
              {uses.length === 0 ? (
                <p className="px-4 py-3 text-body text-ink-soft">No protocol step names this skill yet.</p>
              ) : (
                uses.map(({ p, st, v }) => (
                  <div key={p.id + st.id} className="px-4 py-2.5 border-b border-line last:border-b-0">
                    <div className="text-caption text-ink-soft">
                      <a className="text-accent hover:underline" href={href(`/runbooks/protocols/${p.id}`)}>
                        {p.id}
                      </a>{' '}
                      · step <span className="font-num">{st.id}</span>
                    </div>
                    <div className="text-body">{renderStepText(st, v, 1)}</div>
                  </div>
                ))
              )}
            </Card>
          </div>
        </div>
        <div className="space-y-5">
          <div>
            <SectionTitle>Holders</SectionTitle>
            <Card className="p-4 space-y-3">
              {ctx.members.length === 0 && <p className="text-body text-ink-soft">Nobody is on the ledger yet.</p>}
              {ctx.members.length > 0 &&
                LADDER.map((lvl) => {
                  const people = ctx.members.filter((m) => statusOf(ctx.status, m.id, skillId).level === lvl);
                  return (
                    <div key={lvl}>
                      <div className="flex items-center gap-1.5 text-caption uppercase tracking-wide text-ink-soft mb-1">
                        <LevelGlyph level={lvl} size={11} /> {LEVEL_NAME[lvl]} <span className="font-num">· {people.length}</span>
                      </div>
                      {people.length === 0 ? (
                        <div className="text-caption text-ink-soft">Nobody</div>
                      ) : (
                        <div className="flex flex-col gap-0.5">
                          {people.map((m) => {
                            const st = statusOf(ctx.status, m.id, skillId);
                            return (
                              <div key={m.id} className="text-body flex items-baseline gap-2">
                                <a className="hover:text-accent" href={href(`/guild/people/${m.id}`)}>
                                  {m.name}
                                </a>
                                {st.lapsed && <span className="text-caption text-signal-warn">lapsed</span>}
                                {st.suspended && <span className="text-caption text-signal-error">suspended</span>}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
            </Card>
          </div>
          <div>
            <SectionTitle>How it is held</SectionTitle>
            <Card className="p-4 space-y-2 text-body">
              <Row label="Criticality">
                <span className={cx(skill.criticality === 'critical' && 'text-signal-warn')}>{skill.criticality}</span>
              </Row>
              <Row label="Recency window">
                <span className="font-num">{skill.recencyDays} days</span>
              </Row>
              <Row label="Supervised runs before a check">
                <span className="font-num">{skill.supervisedRuns}</span>
              </Row>
              <Row label="Prerequisites">
                {skill.prerequisites.length === 0
                  ? 'None'
                  : skill.prerequisites.map((p, i) => (
                      <span key={p}>
                        {i > 0 && ', '}
                        <a className="text-accent hover:underline" href={href(`/guild/skills/${p}`)}>
                          {SKILL_BY_ID[p]?.name ?? p}
                        </a>
                      </span>
                    ))}
              </Row>
              <p className="text-caption text-ink-soft pt-1">
                Defined in src/data/skills.ts and changed by commit, so every entry on the ledger points at a definition with a history.
              </p>
            </Card>
          </div>
        </div>
      </div>
    </>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-ink-soft">{label}</span>
      <span className="text-right">{children}</span>
    </div>
  );
}
