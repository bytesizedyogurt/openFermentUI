// "View as table" — the accessibility floor under every chart.
//
// A chart that cannot be read as a table is a chart a screen reader cannot read
// at all, and this repo draws a lot of bespoke SVG. It sits in a `<details>`
// rather than beside the chart because the table is the fallback, not the
// headline — and the browser suites open every `<details>` before asserting, so
// collapsed is not hidden as far as the gates are concerned.
//
// Lifted from `screens/Plant.tsx`, which held the better of the two copies:
// `whitespace-nowrap` keeps a fourteen-column cash flow from wrapping into
// unreadable ribbons, and the wrapper already scrolls sideways so nowrap costs
// the page nothing.
import { Table2 } from 'lucide-react';

import { cx } from '@/components/ui';

export function ChartTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: (string | number)[][];
}) {
  return (
    <details className="mt-2">
      <summary className="text-caption text-ink-soft cursor-pointer hover:text-ink inline-flex items-center gap-1">
        <Table2 size={12} /> View as table
      </summary>
      <div className="overflow-x-auto mt-1.5">
        <table className="w-full text-caption">
          <thead>
            <tr className="border-b border-line text-ink-soft">
              {headers.map((h, i) => (
                <th
                  key={h}
                  className={cx('py-1 whitespace-nowrap', i === 0 ? 'text-left' : 'text-right')}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} className="border-b border-line/50">
                {r.map((c, j) => (
                  <td
                    key={j}
                    className={cx(
                      'py-1 whitespace-nowrap',
                      j === 0 ? 'text-left' : 'text-right font-num',
                    )}
                  >
                    {c}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
