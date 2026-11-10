# H7-04: two tabs on one scenario's parameter panel, and one person's override erases the other's

**Statement.** A scope's overrides travel as one row that holds the whole list, so when two tabs open on one Proforma
scenario each type a value for a different parameter, the second tab's write replaces the first tab's override on the
service, with no refusal and no word on either page.

**Contract.**

- `src/store.ts:2391`, the comment on `setOverride`: "A person's change, under their name, by scope and key: one a
  parameter."
- `src/components/ParameterPanel.tsx:14-17`: "the person types a value, a low, a high and what it rests on: each change
  is an `Override` under the reviewer name, at now, kept in the open project's rows (`setOverride`;
  lib/projectState.ts)".
- `core/openferment_core/project_state.py:156`: "the overrides of one scope are one row per key".
- `src/lib/projectState.ts:8-9`: the rows "load from `GET /api/state` when a project opens, and every change is sent
  one row at a time."

Tab B's person changed one parameter, `titre`. The service holds the result of that change as the deletion of tab A's
person's `feed_glucose_conc`, a parameter tab B never touched, and nothing says so.

**Command** (from the repository root): `bash bughunt/repro/H7-04/run.sh`

It makes a fresh database `bh_r_h7_04_overrides` (bh_db_fresh, through bh_svc_start), starts the service on
127.0.0.1:9640 over the built app in `dist/`, makes project `h7-04` and one BioSTEAM scenario `sc-h7-04-twotabs` on the
shelf flowsheet `ethanol_glucose_v0` (`PUT /api/state/scenarios/...`), checks that `GET /api/params/proforma:<id>`
names `feed_glucose_conc` and `titre`, then drives Chromium (`twotabs.mjs`):

1. Tab A sets a reviewer name in Settings and opens `/proforma/scenario/sc-h7-04-twotabs`; tab B opens the same page in
   the same browser. The service holds no override for the scope.
2. Tab A types 1.234 in the `feed_glucose_conc` row's value box. The service's `GET /api/state` is read until it holds
   it.
3. Tab B types 5.678 in the `titre` row's value box. The service is read again.
4. Tab A reloads, and its `feed_glucose_conc` row is read.

Every `PUT /api/state/overrides/proforma:<id>` each tab sends is recorded with the list it carries, and every toast
either tab shows is read off the page's live region. A `proforma:` scope binds alone and starts no worker, so no
BioSTEAM import and no model call is made. The service is stopped and the database removed at the end.

**Expected.** The service keeps both overrides, `feed_glucose_conc=1.234` (tab A) and `titre=5.678` (tab B); or, if a
write can only stand for the whole scope, a page says in words that the other tab's override was replaced.

**Observed** (run1.log and run2.log, the same both times):

- After tab A typed, the service held `[feed_glucose_conc=1.234]`; tab A sent `[feed_glucose_conc=1.234]`.
- Tab B sent `[titre=5.678]`, the scope's list as tab B loaded it with its own change added, and the service then held
  `[titre=5.678]`. Tab B showed `feed_glucose_conc` as "—" when it wrote.
- Tab A after a reload shows `feed_glucose_conc` as "—", `data-overridden="false"`.
- No toast on either tab, no refusal (both PUTs were kept).

`RESULT: DEFECT` both runs.

**Likely cause.**

- `src/lib/projectState.ts:78`: `rowsOf` keys the overrides by scope (`overrides: entries(state.overrides)`), so the
  row `changes()` sends is the scope's whole list as this tab holds it.
- `src/store.ts:2393-2400`: `setOverride` builds that list from this tab's own `parameterOverrides[scope]`, loaded once
  when the project opened (`hydrateProjectState`, `src/store.ts:1043-1084`); nothing reloads it when another tab
  writes.
- `core/openferment_core/project_state.py:601-607`: `_put` for `overrides` deletes every row of the scope and inserts
  the list it was sent, with no check against the rows it replaces.

By reading the code alone: tab A, still open, keeps showing its own override, and a run started from tab A sends tab
A's list (`ProformaScenario.tsx:596`, `overridesFor(scope)`), so it carries `feed_glucose_conc` and drops tab B's
`titre`; tab A's next edit would erase tab B's override the same way.
