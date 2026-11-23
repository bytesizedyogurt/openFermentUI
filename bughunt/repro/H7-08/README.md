# H7-08: the rail's logo drops the project from the address

**Statement.** Inside a project, the rail's logo links to `#/`, which opens Home with no project in the
address, and every rail link on that screen is then a plain path, so the address stops naming the open project.

**Contract.** `docs/decisions/ADR-009-ui.md:19-22` (Implementation 7.1): "`/p/:project` is a project's home,
and `/p/:project/<path>` a module screen as a view inside the project: the router reads the prefix off
(`Route.project`), so every screen reads the path it always read, a navigation or a link from inside a project
stays inside it (`inProject`)". The router's header says the same at `src/router.tsx:7-8`: "A link or a
navigation to a plain path from inside a project stays inside it."

**Command.** From the repository root:

    bash bughunt/repro/H7-08/run.sh

It greps the logo's anchor in `src/App.tsx` and in the built bundle in `dist/assets/`, makes a fresh database
(`bh_r_h7_08_logo`), starts the service on 127.0.0.1:9131 over the built app in `dist/`, makes one project
(`h7-08`) through the API, and runs `logo.mjs` in Chromium: open `#/p/h7-08/runbooks`, read every anchor in the
primary navigation, click the logo, read the address, the screen, the top bar, `localStorage` and the rail again,
then follow the rail's Intake link. It stops the service, drops the database and removes its data copy and work
directory on the way out. Keyless, no model call, about 14 s.

**Expected.** The logo, a link to the plain path `/` from inside a project, stays inside it as every other rail
link does: it opens `#/p/h7-08` (the project's home), and the rail's links after it keep `#/p/h7-08/`.

**Observed** (run1.log, run2.log, the same on both runs).

- At `#/p/h7-08/runbooks` the logo's href is `#/`, and all 13 other anchors in the rail keep `#/p/h7-08/`. The
  rail's own Home entry, aimed at the same `/` (`src/data/nav.ts:88`), reads `#/p/h7-08`.
- After the logo: the address is `#/`, the screen is Home with no project in the address ("Bioprocess literature
  you can operate on ..."), the top bar still names the project ("H7-08 repro") and
  `localStorage['openferment.project']` still reads `h7-08`. All 13 rail links are now plain paths
  (`#/ #/intake #/biorepo #/postdoc ...`).
- Following the rail's Intake link then gives `#/intake`: the page acts in `h7-08` from the store while its
  address names no project, so a copied or bookmarked address no longer carries the project.

**Likely cause.** `src/App.tsx:498`: the logo's anchor is written by hand as `<a href="#/" ...>`. Every other rail
anchor goes through `href()` (`src/App.tsx:517`, `href={href(item.to)}`, and `src/App.tsx:559` for Settings),
and `href()` (`src/router.tsx:86-88`) applies `inProject` (`src/router.tsx:44-47`), which turns `/` into
`/p/<project>`. The built bundle carries the same hand-written `href:"#/"`. Confidence high; the fix is
`href={href('/')}` on that one anchor.

**Severity.** S3: the project address (ADR-009 7.1) breaks on one common click, with a workaround (the rail's
Home entry, or typing the project's address); no data is lost and the screens still act in the open project.
