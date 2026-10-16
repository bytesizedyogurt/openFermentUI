// Guild · Matrix (OF-BLD-013 §1.4). People by skills: the training matrix a
// regulated plant keeps on paper, computed from the ledger instead of typed
// into it. Pick a protocol and the columns narrow to the skills its steps
// need, and a last column says who can run it alone, who needs a cosigner
// somewhere, and who cannot run it yet. A cell opens the sign-off sheet.
import { useMemo, useState } from 'react';
import { ChevronDown, Users } from 'lucide-react';
import { useStore } from '@/store';
import { FAMILIES, SKILLS } from '@/data/skills';
import { PROTOCOLS } from '@/data/protocols';
import type { Protocol } from '@/data/types';
import { Button, Card, EmptyState, cx } from '@/components/ui';
import { AddPersonForm, GuildHeader, SignoffSheet, useGuild } from '@/components/GuildBits';
import { LevelGlyph, LevelLegend, levelLabel } from '@/components/LevelGlyph';
import { statusOf, verdictFor } from '@/engine/competence';
import { href } from '@/router';

const VERDICT = {
  alone: { dot: 'bg-accent', text: 'Runs it alone' },
  cosign: { dot: 'bg-signal-warn', text: 'Needs a cosigner' },
  blocked: { dot: 'bg-signal-error', text: 'Cannot run it yet' },
} as const;

/** Protocols whose current version tags at least one step. */
const TAGGED: Protocol[] = PROTOCOLS.filter((p) =>
  (p.versions.find((v) => v.version === p.currentVersion) ?? p.versions[0]).steps.some((s) => (s.skills ?? []).length > 0),
);

const stepsOf = (p: Protocol) => (p.versions.find((v) => v.version === p.currentVersion) ?? p.versions[0]).steps;

export default function GuildMatrix() {
  const ctx = useGuild();
  const loadSample = useStore((s) => s.guildLoadSample);
  const [protocolId, setProtocolId] = useState<string>(TAGGED[0]?.id ?? 'all');
  const [pair, setPair] = useState<{ p: string; s: string } | null>(null);
  const protocol = TAGGED.find((p) => p.id === protocolId) ?? null;

  const columns = useMemo(() => {
    const needed = protocol ? new Set(stepsOf(protocol).flatMap((s) => s.skills ?? [])) : null;
    return FAMILIES.map((f) => ({
      family: f,
      skills: SKILLS.filter((s) => s.family === f.id && (!needed || needed.has(s.id))),
    })).filter((g) => g.skills.length > 0);
  }, [protocol]);
  const flat = columns.flatMap((g) => g.skills);

  const header = (
    <GuildHeader
      title="Matrix"
      subtitle="Who holds which skill, computed from what assessors have signed. Pick a protocol to see who can run it."
    />
  );

  if (ctx.guild.people.length === 0) {
    return (
      <>
        {header}
        <Card className="max-w-2xl">
          <EmptyState
            icon={<Users size={22} />}
            title="Nobody is on the ledger yet"
            body="The ledger starts with its lead, who adds the team and designates the first assessors. Or look around with an invented sample team first; nothing about the sample is saved."
          />
          <div className="px-6 pb-6 space-y-4">
            <AddPersonForm />
            <div className="border-t border-line pt-3">
              <Button onClick={loadSample}>Show a sample team</Button>
            </div>
          </div>
        </Card>
      </>
    );
  }

  const verdicts = new Map(
    protocol ? ctx.members.map((m) => [m.id, verdictFor(stepsOf(protocol), m.id, ctx.status)]) : [],
  );
  const counts = { alone: 0, cosign: 0, blocked: 0 };
  for (const v of verdicts.values()) counts[v.verdict] += 1;
  const uncovered = flat.filter((s) => ctx.members.every((m) => statusOf(ctx.status, m.id, s.id).effective < 3));

  return (
    <>
      {header}
      <div className="space-y-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-caption uppercase tracking-wide text-ink-soft">Protocol</span>
            <span className="relative">
              <select
                id="matrix-protocol"
                className="input pr-8 appearance-none max-w-full"
                value={protocolId}
                onChange={(e) => setProtocolId(e.target.value)}
              >
                {TAGGED.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.id} · {p.title}
                  </option>
                ))}
                <option value="all">Every skill</option>
              </select>
              <ChevronDown size={14} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-ink-soft" />
            </span>
          </label>
          {protocol && (
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 pb-1 text-body">
              {(['alone', 'cosign', 'blocked'] as const).map((k) => (
                <span key={k} className="inline-flex items-center gap-1.5">
                  <span className={cx('w-2 h-2 rounded-full', VERDICT[k].dot)} />
                  <span className="font-num">{counts[k]}</span> {VERDICT[k].text.toLowerCase()}
                </span>
              ))}
              <a className="text-accent hover:underline" href={href(`/runbooks/protocols/${protocol.id}`)}>
                Open {protocol.id}
              </a>
            </div>
          )}
        </div>

        {uncovered.length > 0 && (
          <p className="text-body text-signal-warn">
            Nobody can currently run {uncovered.map((s) => s.name).join(', ')} without a cosigner.
          </p>
        )}

        <Card className="hidden md:block">
          <div className="overflow-x-auto">
            <table className="border-collapse text-body" style={{ minWidth: 200 + flat.length * 70 + (protocol ? 190 : 0) }}>
              <thead>
                <tr>
                  <th className="sticky left-0 z-10 bg-surface-1 w-[200px]" />
                  {columns.map((g) => (
                    <th key={g.family.id} colSpan={g.skills.length} className="px-1 pt-3 pb-1 font-normal">
                      <div className="text-caption uppercase tracking-wide text-ink-soft border-b border-line pb-1 mx-1">
                        {g.family.short}
                      </div>
                    </th>
                  ))}
                  {protocol && <th />}
                </tr>
                <tr className="border-b border-line">
                  <th className="sticky left-0 z-10 bg-surface-1 text-left px-4 pb-2 align-bottom text-caption uppercase tracking-wide text-ink-soft font-normal">
                    Person
                  </th>
                  {flat.map((s) => (
                    <th key={s.id} className="w-[70px] px-1 pb-2 align-bottom font-normal">
                      <a
                        href={href(`/guild/skills/${s.id}`)}
                        className="block text-[11px] leading-[14px] text-ink hover:text-accent"
                        title={s.summary}
                      >
                        {s.name}
                      </a>
                      {s.criticality === 'critical' && <div className="text-[10px] text-signal-warn mt-0.5">critical</div>}
                    </th>
                  ))}
                  {protocol && (
                    <th className="text-left px-3 pb-2 align-bottom text-caption uppercase tracking-wide text-ink-soft font-normal w-[190px]">
                      For this protocol
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {ctx.members.map((m) => {
                  const v = verdicts.get(m.id);
                  return (
                    <tr key={m.id} className="border-b border-line last:border-b-0">
                      <td className="sticky left-0 z-10 bg-surface-1 px-4 py-2">
                        <a className="hover:text-accent" href={href(`/guild/people/${m.id}`)}>
                          {m.name}
                        </a>
                        <div className="text-caption text-ink-soft">{m.title}</div>
                      </td>
                      {flat.map((s) => {
                        const st = statusOf(ctx.status, m.id, s.id);
                        return (
                          <td key={s.id} className="text-center px-1 py-1">
                            <button
                              type="button"
                              onClick={() => setPair({ p: m.id, s: s.id })}
                              className="inline-grid place-items-center w-10 h-10 rounded-btn hover:bg-accent-wash"
                              aria-label={`${m.name}, ${s.name}: ${levelLabel(st)}`}
                            >
                              <LevelGlyph status={st} />
                            </button>
                          </td>
                        );
                      })}
                      {protocol && v && (
                        <td className="px-3 py-2">
                          <div className="flex items-center gap-1.5">
                            <span className={cx('w-2 h-2 rounded-full shrink-0', VERDICT[v.verdict].dot)} />
                            <span className="font-medium">{VERDICT[v.verdict].text}</span>
                          </div>
                          <div className="text-caption text-ink-soft">
                            {v.verdict === 'blocked'
                              ? `${v.missing.length} skill${v.missing.length === 1 ? '' : 's'} below Supervised`
                              : v.verdict === 'cosign'
                                ? `${v.cosignSteps} of ${stepsOf(protocol).length} steps`
                                : `all ${stepsOf(protocol).length} steps`}
                          </div>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr className="border-t border-line">
                  <td className="sticky left-0 z-10 bg-surface-1 px-4 py-2 text-caption text-ink-soft">Run it alone today</td>
                  {flat.map((s) => {
                    const n = ctx.members.filter((m) => statusOf(ctx.status, m.id, s.id).effective >= 3).length;
                    return (
                      <td key={s.id} className={cx('text-center text-caption font-num py-2', n <= 1 ? 'text-signal-warn' : 'text-ink-soft')}>
                        {n}
                      </td>
                    );
                  })}
                  {protocol && <td />}
                </tr>
              </tfoot>
            </table>
          </div>
        </Card>

        {/* At phone width the grid becomes a card per person. */}
        <div className="md:hidden space-y-2">
          {ctx.members.map((m) => {
            const v = verdicts.get(m.id);
            return (
              <details key={m.id} className="card">
                <summary className="list-none cursor-pointer px-3 py-2.5 flex items-center gap-3">
                  <span className="min-w-0 flex-1">
                    <span className="block font-medium">{m.name}</span>
                    <span className="block text-caption text-ink-soft">{m.title}</span>
                  </span>
                  {v && (
                    <span className="inline-flex items-center gap-1.5 text-caption shrink-0">
                      <span className={cx('w-2 h-2 rounded-full', VERDICT[v.verdict].dot)} />
                      {VERDICT[v.verdict].text}
                    </span>
                  )}
                  <ChevronDown size={14} className="text-ink-soft shrink-0" />
                </summary>
                <div className="px-3 pb-3 space-y-2">
                  {columns.map((g) => (
                    <div key={g.family.id}>
                      <div className="text-caption uppercase tracking-wide text-ink-soft mb-1">{g.family.short}</div>
                      {g.skills.map((s) => {
                        const st = statusOf(ctx.status, m.id, s.id);
                        return (
                          <button
                            key={s.id}
                            type="button"
                            onClick={() => setPair({ p: m.id, s: s.id })}
                            className="w-full flex items-center gap-2 py-1 min-h-[40px] text-left"
                          >
                            <LevelGlyph status={st} size={14} />
                            <span className="flex-1 min-w-0">{s.name}</span>
                            <span className="text-caption text-ink-soft">{levelLabel(st)}</span>
                          </button>
                        );
                      })}
                    </div>
                  ))}
                </div>
              </details>
            );
          })}
        </div>

        <LevelLegend />
      </div>
      <SignoffSheet personId={pair?.p ?? null} skillId={pair?.s ?? null} onClose={() => setPair(null)} />
    </>
  );
}
