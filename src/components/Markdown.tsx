// Minimal markdown renderer with first-class citation chips.
// Chips are written [[SP-004]] or [[ex-0112]] in seed content and become the
// real CitationChip component — never post-hoc decoration (§4).
import React, { type ReactNode } from 'react';
import { CitationChip } from './Chip';
import { cx } from './ui';

const CHIP_RE = /\[\[([A-Za-z0-9\-]+)\]\]/g;

export function inlineMarkdown(text: string, key = ''): ReactNode[] {
  const out: ReactNode[] = [];
  let i = 0;
  // Split on chips first, then apply emphasis within the literal segments.
  const parts = text.split(CHIP_RE);
  parts.forEach((part, idx) => {
    if (idx % 2 === 1) {
      const id = part;
      out.push(
        id.startsWith('ex-') ? (
          <CitationChip key={`${key}-c${idx}`} recordId={id} />
        ) : (
          <CitationChip key={`${key}-c${idx}`} paperId={id} />
        ),
      );
      return;
    }
    // bold, italic, code
    const tokens = part.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g);
    for (const t of tokens) {
      if (!t) continue;
      if (t.startsWith('**') && t.endsWith('**'))
        out.push(
          <strong key={`${key}-b${i++}`} className="font-semibold">
            {t.slice(2, -2)}
          </strong>,
        );
      else if (t.startsWith('*') && t.endsWith('*') && t.length > 2)
        out.push(
          <em key={`${key}-i${i++}`} className="italic">
            {t.slice(1, -1)}
          </em>,
        );
      else if (t.startsWith('`') && t.endsWith('`'))
        out.push(
          <code key={`${key}-m${i++}`} className="font-num text-[0.92em] bg-surface-0 px-1 rounded">
            {t.slice(1, -1)}
          </code>,
        );
      else out.push(<React.Fragment key={`${key}-t${i++}`}>{t}</React.Fragment>);
    }
  });
  return out;
}

export function Markdown({ md, className }: { md: string; className?: string }) {
  const lines = md.split('\n');
  const blocks: ReactNode[] = [];
  let i = 0;
  let k = 0;

  while (i < lines.length) {
    const line = lines[i];

    // table
    if (line.trim().startsWith('|') && lines[i + 1]?.includes('---')) {
      const header = line
        .split('|')
        .slice(1, -1)
        .map((c) => c.trim());
      const align = lines[i + 1]
        .split('|')
        .slice(1, -1)
        .map((c) => (c.trim().endsWith(':') ? 'right' : 'left'));
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        rows.push(
          lines[i]
            .split('|')
            .slice(1, -1)
            .map((c) => c.trim()),
        );
        i++;
      }
      blocks.push(
        <div key={k++} className="overflow-x-auto my-3">
          <table className="w-full border-collapse text-body">
            <thead>
              <tr className="border-b border-line">
                {header.map((h, hi) => (
                  <th
                    key={hi}
                    className={cx(
                      'text-caption font-medium text-ink-soft px-2 py-1.5',
                      align[hi] === 'right' ? 'text-right' : 'text-left',
                    )}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri} className="border-b border-line/60">
                  {r.map((c, ci) => (
                    <td
                      key={ci}
                      className={cx(
                        'px-2 py-1.5 align-top',
                        align[ci] === 'right' && 'text-right font-num',
                      )}
                    >
                      {inlineMarkdown(c, `t${ri}${ci}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // list
    if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ''));
        i++;
      }
      blocks.push(
        <ul key={k++} className="list-disc pl-5 my-2 space-y-1">
          {items.map((it, ii) => (
            <li key={ii}>{inlineMarkdown(it, `l${ii}`)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    // numbered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ''));
        i++;
      }
      blocks.push(
        <ol key={k++} className="list-decimal pl-5 my-2 space-y-1">
          {items.map((it, ii) => (
            <li key={ii}>{inlineMarkdown(it, `n${ii}`)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    // heading
    if (/^#{2,4}\s+/.test(line)) {
      const level = line.match(/^#+/)![0].length;
      blocks.push(
        <div
          key={k++}
          className={cx(
            'font-serif font-semibold mt-4 mb-1',
            level === 2 ? 'text-section-title' : 'text-reading',
          )}
        >
          {inlineMarkdown(line.replace(/^#+\s+/, ''), `h${k}`)}
        </div>,
      );
      i++;
      continue;
    }

    // blockquote
    if (line.trim().startsWith('> ')) {
      const quoted: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('> ')) {
        quoted.push(lines[i].replace(/^\s*>\s?/, ''));
        i++;
      }
      blocks.push(
        <blockquote
          key={k++}
          className="border-l-2 border-line pl-3 my-2 text-ink-soft font-serif italic"
        >
          {inlineMarkdown(quoted.join(' '), `q${k}`)}
        </blockquote>,
      );
      continue;
    }

    // blank
    if (line.trim() === '') {
      i++;
      continue;
    }

    // paragraph
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() !== '' && !/^\s*([-*]|\d+\.)\s+/.test(lines[i]) && !lines[i].trim().startsWith('|') && !/^#{2,4}\s/.test(lines[i]) && !lines[i].trim().startsWith('> ')) {
      para.push(lines[i]);
      i++;
    }
    // Guarantee forward progress. A line the paragraph loop refuses to consume
    // and no earlier branch claimed — most often a table's header row that has
    // streamed in before its |---| separator — would otherwise spin here
    // forever, allocating empty blocks until the tab dies. Render it as plain
    // text; the next token completes the table and it re-renders properly.
    if (para.length === 0) {
      para.push(lines[i]);
      i++;
    }
    blocks.push(
      <p key={k++} className="my-2 leading-relaxed">
        {inlineMarkdown(para.join(' '), `p${k}`)}
      </p>,
    );
  }

  return <div className={cx('text-body', className)}>{blocks}</div>;
}
