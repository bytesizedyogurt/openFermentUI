/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: ['class', '[data-theme="night"]'],
  theme: {
    extend: {
      colors: {
        'surface-0': 'rgb(var(--surface-0) / <alpha-value>)',
        'surface-1': 'rgb(var(--surface-1) / <alpha-value>)',
        ink: 'rgb(var(--ink) / <alpha-value>)',
        'ink-soft': 'rgb(var(--ink-soft) / <alpha-value>)',
        line: 'rgb(var(--line) / <alpha-value>)',
        accent: 'rgb(var(--accent) / <alpha-value>)',
        'accent-wash': 'rgb(var(--accent-wash) / <alpha-value>)',
        gold: 'rgb(var(--gold) / <alpha-value>)',
        'signal-warn': 'rgb(var(--signal-warn) / <alpha-value>)',
        'signal-error': 'rgb(var(--signal-error) / <alpha-value>)',
        'signal-info': 'rgb(var(--signal-info) / <alpha-value>)',
        // The demo suite's pair (OF-DEMO-002 §5). Exposed as utilities so the
        // 24 call sites that were reaching for `style={{ color: 'rgb(var(...))' }}`
        // can use a class — and, more importantly, so the /<alpha-value> form
        // works, which is why several of them needed an inline style at all.
        'signal-open': 'rgb(var(--signal-open) / <alpha-value>)',
        'signal-closed': 'rgb(var(--signal-closed) / <alpha-value>)',
      },
      fontFamily: {
        serif: ['Spectral', 'Georgia', 'serif'],
        sans: ['"IBM Plex Sans"', '-apple-system', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        caption: ['12px', '16px'],
        'table-dense': ['13px', '18px'],
        body: ['14px', '20px'],
        reading: ['16px', '24px'],
        'section-title': ['18px', '26px'],
        'page-title': ['22px', '28px'],
        display: ['28px', '34px'],
        hero: ['36px', '42px'],
      },
      borderRadius: {
        input: '4px',
        btn: '6px',
        card: '8px',
      },
    },
  },
  plugins: [],
};
