// Naming what does not exist (OF-BLD-008 §4).
//
// A placeholder screen is only honest if the absence is legible. The failure
// mode this avoids is the "coming soon" panel that lists five features in
// confident present tense and leaves a reader unsure which of them they can
// use today — so everything rendered here is visibly greyed, carries a dashed
// marker rather than a tick, and says what it is for rather than promising a
// date.
//
// Shared across geneOS, pureOS and Dominion so the three read as one decision
// rather than three separate apologies.
import { CircleDashed } from 'lucide-react';
import { Card, SectionTitle } from './ui';

export interface UnbuiltItem {
  what: string;
  why: string;
}

export function UnbuiltList({
  title,
  note,
  items,
}: {
  title: string;
  /** One line on why an empty list is on screen at all. */
  note?: string;
  items: UnbuiltItem[];
}) {
  return (
    <section aria-labelledby="unbuilt">
      <SectionTitle
        right={
          <span className="font-num text-caption text-ink-soft">
            0/{items.length} built
          </span>
        }
      >
        <span id="unbuilt">{title}</span>
      </SectionTitle>
      {note && <p className="text-body text-ink-soft mb-2 max-w-3xl">{note}</p>}
      <Card className="px-4 py-1">
        <ul>
          {items.map((item) => (
            <li
              key={item.what}
              className="py-2.5 border-b border-line/70 last:border-0 opacity-70"
            >
              <div className="flex items-baseline gap-2">
                <CircleDashed size={12} className="text-ink-soft shrink-0 mt-0.5" aria-hidden />
                <span className="font-num text-body text-ink-soft">{item.what}</span>
              </div>
              <div className="text-body text-ink-soft mt-0.5 pl-[18px]">{item.why}</div>
            </li>
          ))}
        </ul>
      </Card>
    </section>
  );
}
