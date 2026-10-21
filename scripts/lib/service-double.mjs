/**
 * The service double both browser tests start (OF-BLD-014 §4.4). It answers
 * the endpoints a screen calls when it mounts, from fixtures the real code
 * generated, and stores and echoes what the browser posts so a test can read
 * what the service would have been asked. Moved out of scripts/smoke.mjs so
 * the golden path walks the same service.
 *
 *   const double = startServiceDouble({ dist, port });   // .server, .state
 */
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { serveStatic } from './serve-dist.mjs';

/**
 * `seedOnly` leaves /api/health and the overlay to the static server, as a
 * bare build served them before this double existed, so the app stays
 * on its seed exactly as with no service, while every other endpoint answers:
 * the golden path drives the seed's demo script and, from §4.4, the search
 * views, which ask their own endpoints.
 */
export function createServiceDouble({ dist, seedOnly = false }) {
  /**
   * A stand-in for openferment-core (OF-BLD-012 §5.5). The built app asks
   * /api/health at load and, when it answers, applies /api/biorepo/overlay over
   * the seed. Serving both here exercises the real hydration path on every
   * route, with an overlay fixture whose B5 text is the structural JATS
   * document the Python parser is tested against — a made-up article shape, not
   * a paper, labelled as such in the file. Guild's endpoints (OF-BLD-013) are a
   * double that stores and echoes. Nothing else under /api exists.
   */
  const OVERLAY_FIXTURE = join(process.cwd(), 'core/tests/fixtures/overlay-smoke.json');
  // OF-BLD-014 E.2 — fixtures `python -m openferment_core.demo --prototype`
  // generates through the real code, each `{_fixture, response}`.
  const PROTOTYPE = join(process.cwd(), 'core/tests/fixtures/prototype');
  const prototype = async (name) => JSON.parse(await readFile(join(PROTOTYPE, name), 'utf8')).response;
  // OF-BLD-019 §5.R — the recorded answer for the fermOS fits a query names
  // (`?fits=<JSON object>`), matched input by input, or null.
  const sameFits = (a, b) => JSON.stringify(Object.entries(a).sort()) === JSON.stringify(Object.entries(b).sort());
  const fitsAnswer = (raw, recorded) => {
    let asked = null;
    try {
      asked = JSON.parse(raw);
    } catch {
      return null;
    }
    if (!asked || typeof asked !== 'object' || Array.isArray(asked)) return null;
    return (recorded ?? []).find((r) => sameFits(asked, r.fits)) ?? null;
  };
  const HEALTH = JSON.stringify({
    ok: true,
    service: 'openferment-core (smoke double)',
    model: 'none',
    hasKey: false,
    records: 134,
    corpusError: null,
  });


  /** Decisions the double received on POST /api/biorepo/decisions (§7.3). */
  const decisions = [];
  /** Questions the double received on POST /api/biorepo/check (OF-BLD-012.1 F1.5). */
  const checks = [];
  /**
   * Guild's ledger as the double holds it (OF-BLD-013). It stores what it is
   * sent and echoes it back with the stamps the service adds; the rules are
   * guild.py's, tested in core/tests/test_guild.py, so the double refuses
   * nothing. `guildPosts` is what the browser sent, in order.
   */
  const guildLedger = { version: 1, people: [], evidence: [] };
  /**
   * Proposals as the double holds them (OF-BLD-015 §7.4): the fixture's,
   * marked done or dismissed when the browser posts. `proposalActs` is what
   * the browser sent, in order, with the person who signed it.
   */
  let proposals = null;
  const proposalActs = [];
  const guildPosts = [];
  /**
   * Practice as the double holds it (OF-BLD-013 §4). A draft is a fixed
   * scenario whose values are PR-OD-01's own, and the tutor asks why twice and
   * closes on the third answer; the rules are practice.py's, tested in
   * core/tests/test_practice.py. `practicePosts` is what the browser sent.
   */
  const practiceState = { version: 1, scenarios: [], sessions: [] };
  const practicePosts = [];
  let practiceIds = 0;
  const PRACTICE_SCENARIO = (skillId) => ({
    id: `ps-smoke-${++practiceIds}`,
    skillId,
    title: 'A reading above the linear range',
    situation: 'A flask read above the top of the linear range at step o4. The step says [v1], and the blank is [v2].',
    prompt: 'What do you do with the sample before you record it, and why?',
    watchFor: ['Dilutes into the same spent medium and reads again'],
    evidence: [
      {
        id: 'v1',
        label: 'Step o4 of PR-OD-01',
        source: { kind: 'step', protocolId: 'PR-OD-01', stepId: 'o4' },
        text: 'Read OD750 in a 10 mm cuvette against 250 mL of spent cell-free medium as the blank.',
      },
      {
        id: 'v2',
        label: 'The blank medium',
        source: { kind: 'material', protocolId: 'PR-OD-01', material: 'Spent cell-free medium' },
        text: 'Spent cell-free medium',
        value: 250,
        unit: 'mL',
      },
    ],
    steps: [{ protocolId: 'PR-OD-01', stepId: 'o4' }],
    depositionIds: [],
    model: 'smoke-double',
    usage: { inputTokens: 0, outputTokens: 0, costUsd: 0, models: [] },
    createdAt: new Date().toISOString(),
  });

  /** Questions the browser searched for (§4.4). */
  const ragSearches = [];
  const asks = [];
  const geneosCalls = [];
  const fermosCalls = [];
  const proformaRuns = [];
  /** The bindings the browser asked for with fermOS fits chosen (OF-BLD-019 §5.1): each query, as sent. */
  const proformaBinds = [];
  /**
   * What the double has on file that a test may switch (OF-BLD-019 §5.1):
   * `fermosFitsOnFile` serves GET /api/fermos/fits as a service with the
   * fixture's fit and forecast on file, else as one with none, which is how a
   * fresh install starts. `ceilingOnFile` (OF-BLD-019 §5.2) serves
   * GET /api/proforma/ceiling-check as a service with the fixture's STAND-IN
   * geneOS ceiling on file, else with none, as a fresh install starts.
   * `pureosYeastOnFile` (OF-BLD-019 §7.R) lists and serves sc-yeast-1's
   * train beside sc-pha-1's; off, the double holds the PHA run alone, so
   * pureOS's empty list for the active program is drawn.
   * `vesselSimulationsOnFile` (OF-BLD-020 §4.2, stacked on §3.3) adds
   * fermos-vessel.json's two simulations to GET /api/fermos/simulations,
   * which the vessel flow chooses from; off, the list holds only what
   * Simulate's recorded run kept, empty as a fresh install starts, so
   * fermOS → Vessel can also be driven with fits alone (§4.R).
   * `vesselDelayMs` (§4.R) holds each POST /api/fermos/vessel answer that
   * long, so a test can change the source while a design is in flight.
   * `vesselScopeDelayMs` (§8.R) holds each GET of a vessel's parameter
   * scope that long, as a cold service's first read waits on BioSTEAM.
   */
  const flags = { fermosFitsOnFile: false, ceilingOnFile: false, pureosYeastOnFile: true, vesselSimulationsOnFile: false, vesselDelayMs: 0, vesselScopeDelayMs: 0 };
  /** OF-BLD-020 §6.1: the vessel designs this double answered, newest first, as GET /api/fermos/vessels lists them. */
  const vesselsKept = [];
  /** The ceiling checks the browser asked for (OF-BLD-019 §5.2): each query, as sent. */
  const ceilingChecks = [];
  /** Reference biorefineries the browser asked to run (OF-BLD-019 §2.2). */
  const proformaReferences = [];
  /**
   * The runs this double holds, by scenario id: the artifact id of the run a
   * POST /api/proforma/run answered, as the service keeps every run it made
   * (OF-BLD-019 §3.R). A test may set or clear it, as a service with runs on
   * file or a fresh one.
   */
  const proformaRunsOnFile = new Map();
  /** thermosteam's answers the browser asked for and got (OF-BLD-019 §4.2), by question. */
  const thermoKept = new Map();
  const thermoCalls = [];
  /** pureOS's proposals the browser asked for (OF-BLD-020 §7.2): each POST /api/pureos/propose body, as sent. */
  const pureosProposals = [];
  /**
   * The parameter panel (OF-BLD-020 §2.2): each scope the browser asked for
   * (GET /api/params/{scope}, with its query) and each resolve it posted
   * (POST /api/params/{scope}/resolve, with its body), as sent.
   */
  const paramScopes = [];
  const paramResolves = [];
  /**
   * fermOS → Vessel (OF-BLD-020 §4.2): each design the browser posted
   * (POST /api/fermos/vessel), as sent. The answers are fermos-vessel.json's,
   * which demo.py --prototype made from two simulations of the real
   * fermos.simulate and, with the sim extra installed, designs by the real
   * Proforma worker on BioSTEAM (its `worker.kind` says which).
   */
  const vesselPosts = [];
  /**
   * fermOS → Simulate (OF-BLD-020 §3.3): what the browser asked to bind
   * (GET /api/fermos/bind, with its query) and to simulate (POST
   * /api/fermos/simulate, with its body), as sent; and the simulations the
   * double holds, empty as a fresh install starts, the fixture's one once a
   * simulation it recorded was asked for.
   */
  const fermosBinds = [];
  const fermosSimulates = [];
  const fermosSimulationsOnFile = [];
  /** OF-BLD-020 §6.2: each GET /api/fermos/harvest the browser made, `{ simulation, hour }` as sent (hour null for none). */
  const harvestReads = [];
  /**
   * pureOS → Builder (OF-BLD-020 §5.3): every Builder call the browser made
   * (catalogue specs, scopes, resolves, validate, check, run, from-run), each
   * `{ path, body }` as sent; and the train runs the double holds, empty as a
   * fresh install starts, the fixture's one (under the asked train's id,
   * name and person) once the browser ran the train it recorded.
   */
  const builderCalls = [];
  const trainRunsOnFile = [];
  /** The fixture's binding key for an ask: its family and strain (none: every strain). */
  const simKey = (ask) => `${ask.family}|${ask.strain ?? ''}`;
  /** Whether the double recorded this ask: ethanol on glucose from the records, until the sugar runs out. */
  const simAskRecorded = (ask) =>
    (ask.product ?? null) === 'ethanol' && (ask.sugar ?? null) === 'glucose' && (ask.startFrom ?? 'records') === 'records' &&
    !ask.fit && !ask.fitArtifact && (ask.durationPreset ?? 'until-sugar-runs-out') === 'until-sugar-runs-out';
  /**
   * A person's overrides laid on recorded values as the service lays them on:
   * each an assumption by the person it names, its interval's empty end the
   * value when one end is typed (params.held, OF-BLD-020 §2.R).
   */
  const laidOn = (values, overrides) => {
    const byKey = new Map(overrides.map((o) => [o.key, o]));
    return values.map((v) => {
      const o = byKey.get(v.key);
      if (!o) return v;
      const by = String(o.by).trim();
      const ends = o.low == null && o.high == null ? [null, null] : [o.low ?? o.value, o.high ?? o.value];
      return {
        key: v.key, value: o.value, low: ends[0], high: ends[1],
        source: { kind: 'assumption', id: null, note: `typed on ${o.at}${o.note ? `: ${o.note}` : ''}`, by },
        origin: 'assumption', identified: null, overriddenBy: by, libraryDefault: v.libraryDefault ?? null,
        recordIds: [], detail: `typed by ${by} on ${o.at}${o.note ? `: ${o.note}` : ''}`, outOfBounds: null,
      };
    });
  };
  /** The service's refusal of an override it cannot lay on, in its words, or null. */
  const overrideRefusal = (scope, overrides, keys) => {
    const stray = [...new Set(overrides.map((o) => o.scope).filter((sc) => sc !== scope))].sort();
    if (stray.length) return `an override names the scope it changes, and these were sent to ${scope}: ${stray.join(', ')}`;
    const seen = new Set();
    for (const o of overrides) {
      if (!keys.includes(o.key)) return `there is no parameter ${o.key} here; the parameters are ${keys.join(', ')}`;
      if (seen.has(o.key)) return `two overrides of ${o.key}: one person's value a parameter`;
      seen.add(o.key);
      if (!String(o.by ?? '').trim()) return `the override of ${o.key} needs a person's name: a decision needs a reviewer name`;
    }
    return null;
  };

  const server = createServer(async (req, res) => {
    try {
      const url = decodeURIComponent((req.url ?? '/').split('?')[0]);
      if (seedOnly && (url === '/api/health' || url === '/api/biorepo/overlay')) {
      // Exactly what a bare static server answers, as before this double.
      return await serveStatic(dist, url, res);
    }
    if (url === '/api/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(HEALTH);
      }
      if (url === '/api/biorepo/decisions' && req.method === 'POST') {
        // The double stores nothing and refuses nothing: it records what the
        // browser sent and echoes it back, so the test can read what
        // `biorepo.write` would have been asked to store.
        let body = '';
        for await (const chunk of req) body += chunk;
        const decision = JSON.parse(body);
        decisions.push(decision);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(decision));
      }
      if (url === '/api/biorepo/check' && req.method === 'POST') {
        // What `biorepo.write` would answer for the smoke fixture, in its
        // shape: B5's curated record is on a fetched paper, so an accept is
        // storable, and its quote is not in that text and no extractor span
        // agrees with it, so a gold decision refuses on rule 'quote'. The card
        // renders its own words for a rule it also recognises; the GATE is
        // this answer, which is the point of the endpoint.
        let body = '';
        for await (const chunk of req) body += chunk;
        const asked = JSON.parse(body);
        checks.push(asked);
        const refused = asked.gold
          ? { ok: false, rule: 'quote', why: `the quote for ${asked.recordId} fails anchoring on rule 'quote'` }
          : { ok: true, rule: null, why: null };
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(refused));
      }
      if (url === '/api/guild' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(guildLedger));
      }
      if (url === '/api/guild/checks' && req.method === 'GET') {
        // The real ledger's queue: empty here. The flow below runs its check on the sample.
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ version: 1, checks: [] }));
      }
      if (url.startsWith('/api/guild/') && req.method === 'POST') {
        let body = '';
        for await (const chunk of req) body += chunk;
        const sent = JSON.parse(body);
        guildPosts.push({ url, body: sent });
        let stored = sent;
        if (url === '/api/guild/people') {
          stored = { ...sent, addedAt: new Date().toISOString() };
          guildLedger.people = [...guildLedger.people.filter((p) => p.id !== sent.id), stored];
        } else if (url === '/api/guild/evidence') {
          stored = { ...sent, recordedAt: new Date().toISOString() };
          guildLedger.evidence.push(stored);
        } else if (url === '/api/guild/withdraw') {
          const e = guildLedger.evidence.find((x) => x.id === sent.evidenceId);
          stored = { ...e, withdrawnAt: sent.at, withdrawnBy: sent.by, withdrawReason: sent.reason };
          guildLedger.evidence = guildLedger.evidence.map((x) => (x.id === sent.evidenceId ? stored : x));
        } else if (url === '/api/guild/check') {
          stored = { ok: true, rule: null, why: null };
        }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(stored));
      }
      if (url === '/api/practice' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(practiceState));
      }
      if (url.startsWith('/api/practice/') && req.method === 'POST') {
        let body = '';
        for await (const chunk of req) body += chunk;
        const sent = JSON.parse(body);
        practicePosts.push({ url, body: sent });
        let out;
        const at = new Date().toISOString();
        if (url === '/api/practice/draft') {
          out = PRACTICE_SCENARIO(sent.skillId);
          practiceState.scenarios.push(out);
        } else if (url === '/api/practice/turn') {
          const sc = practiceState.scenarios.find((x) => x.id === sent.scenarioId);
          let held = practiceState.sessions.find((x) => x.id === sent.sessionId) ?? {
            id: `pt-smoke-${++practiceIds}`,
            scenarioId: sc.id,
            skillId: sc.skillId,
            personId: sent.personId ?? null,
            turns: [],
            observed: [],
            startedAt: at,
            closedAt: null,
            evidenceId: null,
            usage: { inputTokens: 0, outputTokens: 0, costUsd: 0, models: [] },
          };
          const answered = held.turns.filter((t) => t.role === 'trainee').length + 1;
          const close = answered >= 3;
          held = {
            ...held,
            turns: [
              ...held.turns,
              { role: 'trainee', text: sent.answer, steps: [], at },
              close
                ? { role: 'tutor', move: 'close', text: 'Look again at why step o4 dilutes into [v2].', steps: [{ protocolId: 'PR-OD-01', stepId: 'o4' }], at }
                : { role: 'tutor', move: 'why', text: 'Why would that change what the reading means?', steps: [{ protocolId: 'PR-OD-01', stepId: 'o4' }], at },
            ],
          };
          if (close) {
            held.closedAt = at;
            held.observed = [{ text: 'Chose to dilute, and was unsure why the diluent is [v2].', steps: [{ protocolId: 'PR-OD-01', stepId: 'o4' }] }];
          }
          practiceState.sessions = [...practiceState.sessions.filter((x) => x.id !== held.id), held];
          out = held;
        }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(out));
      }
      // OF-BLD-014 §3.2 — the artifact store, from the prototype fixtures.
      if (url === '/api/biorepo/artifacts' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(await prototype('artifacts.json')));
      }
      if (url.startsWith('/api/biorepo/artifacts/')) {
        const [id, action] = url.slice('/api/biorepo/artifacts/'.length).split('/');
        // OF-BLD-019 §2.R: a reference run the double serves at
        // /api/proforma/reference/:id reads back by its id too, as the
        // service keeps every artifact it returns (the cards link to it).
        const referenceRuns = await Promise.all(
          ['cornstover_benchmark', 'corn_drygrind'].map((f) => prototype(`proforma-reference-${f}.json`).then((r) => r.artifact).catch(() => null)),
        );
        const found = [...(await prototype('artifacts.json')), ...referenceRuns.filter(Boolean)].find((a) => a.id === id);
        if (!found) {
          res.writeHead(404, { 'Content-Type': 'application/json' });
          return res.end(JSON.stringify({ detail: `no artifact '${id}'` }));
        }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        if (action === 'replay' && req.method === 'POST') return res.end(JSON.stringify(await prototype('artifact-replay.json')));
        return res.end(JSON.stringify(found));
      }
      // OF-BLD-014 §4.4 — passage search, from the prototype fixtures.
    if (url === '/api/rag/status' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(await prototype('rag-status.json')));
    }
    if (url === '/api/rag/report' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(await prototype('rag-report.json')));
    }
    if (url === '/api/rag/search' && req.method === 'POST') {
      let body = '';
      for await (const chunk of req) body += chunk;
      ragSearches.push(JSON.parse(body || '{}'));
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(await prototype('rag-search.json')));
    }
    // OF-BLD-014 §7.4 — fermOS's fit and forecast of the sample run, made
    // through the real code by demo.py --prototype.
    if ((url === '/api/fermos/fit' || url === '/api/fermos/forecast') && req.method === 'POST') {
      let body = '';
      for await (const chunk of req) body += chunk;
      const asked = JSON.parse(body || '{}');
      fermosCalls.push({ path: url, ...asked });
      const fixture = await prototype(url.endsWith('fit') ? 'fermos-fit.json' : 'fermos-forecast.json');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(fixture));
    }
    // OF-BLD-020 §3.3 — fermOS → Simulate. The families, the switch off and
    // on; what binds and waits with the person's overrides laid on; the run,
    // answered with the simulation the real kinetics.py made of the
    // fixture's STAND-IN values when those are what was typed (a parameter
    // that waits is the service's 422, in its words); and the simulations on
    // file, which that run adds to.
    if (url === '/api/fermos/families' && req.method === 'GET') {
      const on = new URL(req.url ?? '/', 'http://double').searchParams.get('includeArchived') === 'true';
      const families = await prototype('fermos-families.json');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(on ? families.on : families.off));
    }
    if ((url === '/api/fermos/bind' && req.method === 'GET') || (url === '/api/fermos/simulate' && req.method === 'POST')) {
      const send = (status, body) => {
        res.writeHead(status, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(body));
      };
      const sim = await prototype('fermos-simulate.json');
      let ask;
      if (req.method === 'GET') {
        const q = new URL(req.url ?? '/', 'http://double').searchParams;
        let overrides = [];
        try {
          overrides = q.get('overrides') ? JSON.parse(q.get('overrides')) : [];
        } catch {
          return send(422, { detail: 'overrides is a JSON list of overrides, each with scope, key, value, by and at, as a run takes them' });
        }
        ask = { ...Object.fromEntries(q), strain: q.get('strain'), overrides };
        fermosBinds.push(ask);
      } else {
        let raw = '';
        for await (const chunk of req) raw += chunk;
        ask = JSON.parse(raw || '{}');
        fermosSimulates.push(ask);
      }
      const recorded = simAskRecorded(ask) ? sim.bind[simKey(ask)] : null;
      if (!recorded) return send(422, { detail: `the double holds no binding of ${ask.family} for this ask: it holds ethanol on glucose from the records` });
      if (recorded.status !== 200) return send(recorded.status, recorded.body);
      const overrides = ask.overrides ?? [];
      const scope = `fermos:family:${ask.family}`;
      const keys = recorded.body.values.map((v) => v.key);
      const why = overrideRefusal(scope, overrides, keys);
      if (why) return send(422, { detail: why });
      const values = laidOn(recorded.body.values, overrides);
      const typed = new Set(overrides.map((o) => o.key));
      const waiting = recorded.body.waiting.filter((k) => !typed.has(k));
      if (url === '/api/fermos/bind') return send(200, { values, waiting, notes: recorded.body.notes });
      if (waiting.length) {
        const family = (await prototype('fermos-families.json')).on.find((f) => f.id === ask.family);
        const label = (k) => family?.specs.find((sp) => sp.key === k)?.label ?? k;
        const lines = waiting.map((k) => `${k} (${label(k)}) ${values.find((v) => v.key === k)?.detail ?? ''}`).join('; ');
        return send(422, { detail: `${ask.family} cannot run yet: ${waiting.length} parameter${waiting.length === 1 ? ' waits' : 's wait'}. ${lines}` });
      }
      const want = sim.simulate.request;
      const same = (a, b) => JSON.stringify(a.map((o) => [o.key, o.value]).sort()) === JSON.stringify(b.map((o) => [o.key, o.value]).sort());
      if (simKey(ask) !== simKey(want) || !same(overrides, want.overrides))
        return send(422, { detail: `the double holds one simulation, of ${want.family} for ${want.strain} with the fixture's typed values; it cannot integrate another` });
      if (!fermosSimulationsOnFile.length) fermosSimulationsOnFile.push(...sim.simulations);
      return send(200, sim.simulate.body);
    }
    // The one list of kept simulations, newest first, that Simulate and
    // Vessel both read: the simulation Simulate's recorded run kept (none
    // until it runs), then, with flags.vesselSimulationsOnFile, the two
    // fermos-vessel.json's designs were made for.
    if (url === '/api/fermos/simulations' && req.method === 'GET') {
      const vessel = flags.vesselSimulationsOnFile ? (await prototype('fermos-vessel.json')).simulations : [];
      const seen = new Set(fermosSimulationsOnFile.map((s) => s.artifactId));
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify([...fermosSimulationsOnFile, ...vessel.filter((s) => !seen.has(s.artifactId))]));
    }
    // OF-BLD-020 §6.2 — a kept simulation's broth at an hour, as the real
    // fermos.harvest read it from the fixture's simulation's kept series
    // (fermos-simulate.json's `harvest`: its own hour, a person's mid-run
    // kept point, and an hour past its end, refused in its words), once
    // Simulate has kept that simulation; an hour the fixture holds no read
    // of is the double's 422 in words, and a simulation not on file the
    // service's 404.
    if (url === '/api/fermos/harvest' && req.method === 'GET') {
      const q = new URL(req.url ?? '/', 'http://double').searchParams;
      const id = q.get('simulation') ?? '';
      const hour = q.get('hour');
      harvestReads.push({ simulation: id, hour: hour == null ? null : Number(hour) });
      const answer = (status, body) => {
        res.writeHead(status, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(body));
      };
      if (!fermosSimulationsOnFile.some((x) => x.artifactId === id))
        return answer(404, { detail: `there is no kept simulation ${id} here: fermOS → Simulate keeps one` });
      const reads = (await prototype('fermos-simulate.json')).harvest.filter((r) => r.request.simulation === id);
      const entry = reads.find((r) => (hour == null ? r.request.hour == null : r.request.hour != null && Number(hour) === r.request.hour));
      if (!entry) {
        const held = reads.filter((r) => r.request.hour != null).map((r) => `${r.request.hour} h`);
        return answer(422, { detail: `the double holds the broth of simulation ${id} at its own harvest hour and at ${held.join(' and ')}; it reads no other hour` });
      }
      return answer(entry.status, entry.body);
    }
    // OF-BLD-019 §5.1 — the fits fermOS keeps, with what each can feed a
    // flowsheet, as the real code listed them over an empty store and over
    // the stand-in fit and forecast (flags.fermosFitsOnFile picks which);
    // a flowsheet the fixture does not hold is the service's 422.
    if (url === '/api/fermos/fits' && req.method === 'GET') {
      const flowsheet = new URL(req.url ?? '/', 'http://double').searchParams.get('flowsheet') ?? '';
      const answers = (await prototype('fermos-fits.json'))[flags.fermosFitsOnFile ? 'onFile' : 'none'];
      const answer = answers[flowsheet] ?? { status: 422, body: { detail: `there is no flowsheet ${flowsheet} on the shelf` } };
      res.writeHead(answer.status, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(answer.body));
    }
    // OF-BLD-014 §8.2 — a service whose simulator has yet to run: the
    // Benchmark card's empty state.
    if (url === '/api/proforma/status' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ status: 'cold', error: null }));
    }
    if (url === '/api/proforma/benchmark' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ artifact: null, simulator: { status: 'cold', error: null } }));
    }
    // OF-BLD-019 §2.1 — the shelf of flowsheets, with the program switch off
    // and, asked with ?includeArchived=true, on. `url` has lost its query
    // string, so the switch is read from the request's own URL (§3.1: the
    // index asks with the switch on and was served the switch-off shelf).
    if (url.startsWith('/api/proforma/shelf') && req.method === 'GET') {
      const on = new URL(req.url ?? '/', 'http://double').searchParams.get('includeArchived') === 'true';
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(await prototype(on ? 'proforma-shelf-archived.json' : 'proforma-shelf.json')));
    }
    // OF-BLD-019 §4.1 — pureOS's trains, read by the real code from the
    // stand-in runs: the list with the program switch off (§7.R: the yeast
    // run's train; PHA's is archived) and, asked with ?includeArchived=true,
    // on; one train by its scenario or its run's artifact id, either run's,
    // else the service's 404 in its words. With flags.pureosYeastOnFile off
    // the double holds no yeast run, so the empty list's words stay tested.
    // OF-BLD-020 §5.3 — pureOS → Builder, from pureos-builder.json, which
    // demo.py --prototype made by running the real code (the real Proforma
    // worker on BioSTEAM where the sim extra is installed, else a stand-in
    // worker; its `worker.kind` says which) over the three-unit train the
    // browser tests build: the catalogue; each type's specs the train uses;
    // each place's scope, served for a train of the same place and type under
    // the asked train's id, and its resolve laying each override on as the
    // service does; the validation and check at three moments (one unit,
    // three units, every value typed), matched by what the train holds
    // (`builderKey`, the same key demo.builder_key writes, never its id, name
    // or who typed); the run of the train with every value typed; the train
    // runs on file after it; the train read back from that run; and the
    // refusal of a run whose classes no type holds. Anything else is answered
    // in the double's own words, never as a result.
    {
      const fx = () => prototype('pureos-builder.json');
      const sendJson = (status, body) => {
        res.writeHead(status, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(body));
      };
      const readBody = async () => {
        let raw = '';
        for await (const chunk of req) raw += chunk;
        return JSON.parse(raw || '{}');
      };
      const pairs = (o) => Object.entries(o ?? {}).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
      const canon = (v) =>
        Array.isArray(v) ? v.map(canon) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, canon(v[k])])) : v;
      const valuesOf = (ps) => pairs(ps).map(([k, v]) => [k, v?.value ?? null]);
      const builderKey = (t) =>
        JSON.stringify(
          canon({
            program: t.program,
            product: t.product,
            inlet: [t.inlet?.kind ?? null, t.inlet?.ref ?? null, t.inlet?.streamId ?? null, t.inlet?.vessel ?? null, valuesOf(t.inlet?.params)],
            units: (t.units ?? []).map((u) => [u.id, u.type, valuesOf(u.params), pairs(u.outlets), u.readFrom ?? null, pairs(u.records)]),
          }),
        );
      const recordedKey = (k) => JSON.stringify(canon(JSON.parse(k)));
      const words = (x) => JSON.stringify(String(x)).slice(1, -1);
      /** The fixture's answer under another train's id, name and person, as the service would have written it for them. */
      const under = (value, f, train) => {
        let text = JSON.stringify(value);
        if (train?.id) text = text.split(words(f.trainId)).join(words(train.id));
        if (train?.name) text = text.split(words(f.train.name)).join(words(train.name));
        if (train?.by) text = text.split(words(f.by)).join(words(train.by));
        return JSON.parse(text);
      };
      const NONE = "the double holds the answers for the three-unit train the browser tests build (a typed broth, a centrifuge, a tank and a pump, with the fixture's values); it cannot judge this train";
      if (url === '/api/pureos/catalogue' && req.method === 'GET') return sendJson(200, (await fx()).catalogue);
      const specsOf = /^\/api\/pureos\/catalogue\/([^/]+)\/specs$/.exec(url);
      if (specsOf && req.method === 'GET') {
        const f = await fx();
        const id = specsOf[1];
        builderCalls.push({ path: url, body: null });
        if (f.specs[id]) return sendJson(200, f.specs[id]);
        if (!f.catalogue.some((t) => t.id === id)) return sendJson(404, { detail: `there is no unit type ${id} in the catalogue` });
        return sendJson(422, { detail: `the double holds the parameters of ${Object.keys(f.specs).join(', ')}; it cannot read ${id}'s class` });
      }
      const unitScope = /^\/api\/params\/pureos:unit:([A-Za-z0-9][A-Za-z0-9._-]{0,127}):([A-Za-z0-9][A-Za-z0-9._-]{0,127})(\/resolve)?$/.exec(url);
      if (unitScope) {
        const [, trainId, place, resolving] = unitScope;
        if (Boolean(resolving) !== (req.method === 'POST')) return sendJson(405, { detail: 'Method Not Allowed' });
        const scope = `pureos:unit:${trainId}:${place}`;
        let ask;
        if (resolving) ask = await readBody();
        else {
          const q = new URL(req.url ?? '/', 'http://double').searchParams;
          ask = { unitType: q.get('unitType'), train: q.get('train') ? JSON.parse(q.get('train')) : null };
        }
        builderCalls.push({ path: url, body: ask });
        (resolving ? paramResolves : paramScopes).push({ scope, ...ask });
        const train = ask.train ?? null;
        if (!train) return sendJson(404, { detail: `pureOS's train units are served with their train (?train=, OF-BLD-020 §5.2)` });
        if (train.id !== trainId) return sendJson(422, { detail: `this scope names train ${trainId}; the train sent is ${train.id}` });
        const f = await fx();
        const unit = place === 'inlet' ? null : (train.units ?? []).find((u) => u.id === place);
        if (place !== 'inlet' && !unit)
          return sendJson(404, { detail: `train ${trainId} has no unit ${place}; its units are ${(train.units ?? []).map((u) => u.id).join(', ') || 'none'} and its inlet` });
        if (unit && ask.unitType && ask.unitType !== unit.type) return sendJson(422, { detail: `unit ${place} of train ${trainId} is a ${unit.type}, not a ${ask.unitType}` });
        const entry = f.scopes.find((sc) => sc.unit === place && (sc.type ?? null) === (unit ? unit.type : null));
        const fits = entry && train.program === f.train.program && train.product === f.train.product && (place !== 'inlet' || train.inlet?.kind === 'typed');
        if (!fits) return sendJson(422, { detail: `the double holds the scopes of a typed broth and of ${f.scopes.filter((sc) => sc.type).map((sc) => `${sc.unit} as a ${sc.type}`).join(', ')}, in a ${f.train.program} train of ${f.train.product}; it cannot bind this place` });
        if (entry.status !== 200) return sendJson(entry.status, entry.body);
        const served = { ...under(entry.body, f, { id: trainId }), scope };
        if (!resolving) return sendJson(200, served);
        const overrides = ask.overrides ?? [];
        const why = overrideRefusal(scope, overrides, served.specs.map((sp) => sp.key));
        if (why) return sendJson(422, { detail: why });
        const specs = new Map(served.specs.map((sp) => [sp.key, sp]));
        for (const o of overrides)
          if (!specs.get(o.key).sourceRule.includes('assumption'))
            return sendJson(422, { detail: `${o.key} is the library's own default, read from its code, and takes no person's value` });
        const values = laidOn(served.values, overrides);
        const basisInputs = values
          .filter((v) => v.overriddenBy)
          .flatMap((v) => [
            { name: v.key, value: v.value, unit: specs.get(v.key).unit, source: v.source },
            ...(v.low != null ? [{ name: `${v.key} low`, value: v.low, unit: specs.get(v.key).unit, source: v.source }] : []),
            ...(v.high != null ? [{ name: `${v.key} high`, value: v.high, unit: specs.get(v.key).unit, source: v.source }] : []),
          ]);
        return sendJson(200, { scope, values, waiting: values.filter((v) => v.origin === 'waiting').map((v) => v.key), basisInputs, warnings: [], notes: served.notes });
      }
      if ((url === '/api/pureos/train/validate' || url === '/api/pureos/train/check') && req.method === 'POST') {
        const asked = await readBody();
        builderCalls.push({ path: url, body: asked });
        const train = url.endsWith('/validate') ? asked : asked.train;
        if (!train || !Array.isArray(train.units)) return sendJson(422, { detail: 'a train is sent whole: its id, name, program, product, inlet and units' });
        const f = await fx();
        const recorded = f[url.endsWith('/validate') ? 'validations' : 'checks'].find((c) => recordedKey(c.key) === builderKey(train));
        if (recorded) return sendJson(recorded.status, under(recorded.body, f, { id: train.id, name: train.name }));
        return sendJson(200, { ok: false, refusals: [NONE], places: { train: [NONE] } });
      }
      if (url === '/api/pureos/train/run' && req.method === 'POST') {
        const asked = await readBody();
        builderCalls.push({ path: url, body: asked });
        const f = await fx();
        const train = asked.train;
        if (!train || builderKey(train) !== recordedKey(f.run.key)) return sendJson(422, { detail: `${NONE}, nor run it` });
        const who = { id: train.id, name: train.name, by: String(asked.by ?? asked.overrides?.[0]?.by ?? '').trim() || null };
        const body = { ...under(f.run.body, f, who), spec: train };
        trainRunsOnFile.splice(0, trainRunsOnFile.length, { who, summaries: under(f.trainRuns, f, who), train: under(f.trainOf, f, who) });
        return sendJson(200, body);
      }
      if (url === '/api/pureos/train-runs' && req.method === 'GET') return sendJson(200, trainRunsOnFile.flatMap((r) => r.summaries));
      if (url.startsWith('/api/pureos/train/') && req.method === 'GET') {
        const key = decodeURIComponent(url.slice('/api/pureos/train/'.length));
        const held = trainRunsOnFile.find((r) => key === r.who.id || key === r.train.artifactId);
        if (held) return sendJson(200, held.train);
      }
      if (url === '/api/pureos/train/from-run' && req.method === 'POST') {
        const asked = await readBody();
        builderCalls.push({ path: url, body: asked });
        const f = await fx();
        const entry = f.fromRun.find((e) => e.request.artifactId === asked.artifactId);
        // The run's own artifact is on file only once the browser ran it, as the service keeps it then.
        const ran = trainRunsOnFile.find((r) => r.train.artifactId === asked.artifactId);
        if (!entry || (asked.artifactId === f.run.body.artifactId && !ran)) return sendJson(404, { detail: `no artifact ${asked.artifactId} is on file here` });
        if (entry.status !== 200) return sendJson(entry.status, entry.body);
        const read = ran ? under(entry.body, f, ran.who) : entry.body;
        const id = asked.trainId ?? `from-${asked.artifactId}`;
        return sendJson(200, JSON.parse(JSON.stringify(read).split(words(`from-${asked.artifactId}`)).join(words(id))));
      }
    }
    const yeastTrain = (t) => t.scenarioId === 'sc-yeast-1' || t.program === 'yeast';
    if (url === '/api/pureos/trains' && req.method === 'GET') {
      const on = new URL(req.url ?? '/', 'http://double').searchParams.get('includeArchived') === 'true';
      const listed = await prototype(on ? 'pureos-trains-archived.json' : 'pureos-trains.json');
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(flags.pureosYeastOnFile ? listed : listed.filter((t) => !yeastTrain(t))));
    }
    if (url.startsWith('/api/pureos/train/') && req.method === 'GET') {
      const key = decodeURIComponent(url.slice('/api/pureos/train/'.length));
      const trains = [await prototype('pureos-train.json'), await prototype('pureos-train-yeast.json')].filter(
        (t) => flags.pureosYeastOnFile || !yeastTrain(t),
      );
      const train = trains.find((t) => key === t.scenarioId || key === t.artifactId);
      if (!train) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ detail: `no Proforma run of ${key} is on file here: run the scenario in Proforma, and pureOS reads its train from that run` }));
      }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(train));
    }
    // OF-BLD-020 §7.2 — pureOS proposes a train: the answer the real proposer
    // gave the same ask (product, host, inlet, switch) over the exported seed,
    // with a stand-in for thermosteam's volatility (pureos-propose.json); an ask
    // the fixture never made is a 404 that says so.
    if (url === '/api/pureos/propose' && req.method === 'POST') {
      let body = '';
      for await (const chunk of req) body += chunk;
      const asked = JSON.parse(body || '{}');
      pureosProposals.push(asked);
      const keyOf = (q) => [q.product ?? '', q.host ?? '', q.inletRef ?? '', q.includeArchived ? 'on' : 'off'].join('|');
      const entry = (await prototype('pureos-propose.json')).entries.find((e) => keyOf(e.request) === keyOf(asked));
      if (!entry) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ detail: `the browser tests recorded no proposal for ${asked.product ?? 'no product'} in ${asked.host ?? 'no host'}` }));
      }
      res.writeHead(entry.status, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(entry.body));
    }
    // OF-BLD-019 §2.2 — a reference biorefinery: its shelf entry, a run made
    // through the real code with the stand-in in place of BioSTEAM, and the
    // package test's values. GET reads it; POST answers as a run would, and
    // is recorded. An id that is not a reference on the shelf is a 404.
    const reference = url.match(/^\/api\/proforma\/reference\/([A-Za-z0-9_]+)$/);
    if (reference && (req.method === 'GET' || req.method === 'POST')) {
      const id = reference[1];
      if (req.method === 'POST') proformaReferences.push(id);
      let fixture;
      try {
        fixture = await prototype(`proforma-reference-${id}.json`);
      } catch {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ detail: `${id} is not a reference biorefinery on the shelf` }));
      }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(fixture));
    }
    // OF-BLD-019 §4.2 — thermosteam's answers, made by the real thermo.py
    // over the stand-in run with a stand-in in place of thermosteam: a POST
    // answers from the fixture (200, or the service's 404 or 422 in its
    // words) and keeps what it answered, so a GET of the same question finds
    // it stored, as the service's does; a question the fixture never asked
    // is the service's 404.
    if (url === '/api/thermo/props' && (req.method === 'GET' || req.method === 'POST')) {
      const keyOf = (q) => ['artifactId', 'streamId', 'preset', 'recordId'].map((k) => q[k] ?? '').join('|');
      let asked;
      if (req.method === 'GET') {
        asked = Object.fromEntries(new URL(req.url ?? '/', 'http://double').searchParams);
      } else {
        let body = '';
        for await (const chunk of req) body += chunk;
        asked = JSON.parse(body || '{}');
      }
      thermoCalls.push({ method: req.method, ...asked });
      const entry = (await prototype('thermo-props.json')).entries.find((e) => keyOf(e.request) === keyOf(asked));
      if (!entry) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ detail: 'no run, stream or record like this is on file here' }));
      }
      if (req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ artifact: thermoKept.get(keyOf(asked)) ?? null }));
      }
      if (entry.status === 200) thermoKept.set(keyOf(asked), entry.body);
      res.writeHead(entry.status, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(entry.body));
    }
    // OF-BLD-020 §4.2 — fermOS → Vessel. The kept simulations are the one
    // list above (flags.vesselSimulationsOnFile); the vessel
    // scope of each as the real code served it (by its vesselType); a
    // resolve that lays each override on as the service does, an assumption
    // by the person it names; and a design answered by its request: the
    // recorded body for the same source, vessel type and overrides (by key
    // and value), with the person's name laid on as the service lays it on;
    // a request with no scale the real code's refusal; any other a 422 in
    // words. A scope or source the fixture lacks is the service's 404.
    {
      const vesselFixture = () => prototype('fermos-vessel.json');
      const sendJson = (status, body) => {
        res.writeHead(status, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(body));
      };
      // OF-BLD-020 §6.1: the designs kept are the ones this double answered
      // (none on a fresh install), each as VesselSummary lists it, newest
      // first, so New scenario from a vessel and a train lists what was designed.
      if (url === '/api/fermos/vessels' && req.method === 'GET') return sendJson(200, vesselsKept);
      const vm = /^\/api\/params\/fermos:vessel:([A-Za-z0-9][A-Za-z0-9._-]{0,127})(\/resolve)?$/.exec(url);
      if (vm) {
        const id = vm[1];
        const resolving = Boolean(vm[2]);
        if (resolving !== (req.method === 'POST')) return sendJson(405, { detail: 'Method Not Allowed' });
        let ask;
        if (resolving) {
          let raw = '';
          for await (const chunk of req) raw += chunk;
          ask = JSON.parse(raw || '{}');
          paramResolves.push({ scope: `fermos:vessel:${id}`, ...ask });
        } else {
          const q = new URL(req.url ?? '/', 'http://double').searchParams;
          ask = { vesselType: q.get('vesselType') };
          paramScopes.push({ scope: `fermos:vessel:${id}`, ...Object.fromEntries(q) });
          if (flags.vesselScopeDelayMs > 0) await new Promise((r) => setTimeout(r, flags.vesselScopeDelayMs));
        }
        const fx = await vesselFixture();
        // A scope is a kept simulation's or (§4.R) a kept fit's, served or refused as the real code answered.
        const sourceOf = (sc) => sc.simulation ?? sc.fit;
        const entry = fx.scopes.find((sc) => sourceOf(sc) === id && (sc.vesselType ?? null) === (ask.vesselType ?? null));
        if (entry && entry.status !== 200) return sendJson(entry.status, entry.body);
        if (!entry) {
          const known = fx.scopes.some((sc) => sourceOf(sc) === id);
          return known
            ? sendJson(422, { detail: `the double holds no ${ask.vesselType} scope of ${id}` })
            : sendJson(404, { detail: `no artifact '${id}' is on file here: a vessel is designed for a fermOS simulation (fermOS → Simulate keeps one) or, anaerobic, a kinetic fit or forecast` });
        }
        const served = entry.body;
        if (!resolving) return sendJson(200, served);
        const overrides = ask.overrides ?? [];
        const specs = new Map(served.specs.map((sp) => [sp.key, sp]));
        const scope = served.scope;
        const stray = [...new Set(overrides.map((o) => o.scope).filter((sc) => sc !== scope))].sort();
        if (stray.length) return sendJson(422, { detail: `an override names the scope it changes, and these were sent to ${scope}: ${stray.join(', ')}` });
        for (const o of overrides) {
          if (!specs.has(o.key)) return sendJson(422, { detail: `there is no parameter ${o.key} here; the parameters are ${[...specs.keys()].join(', ')}` });
          if (!String(o.by ?? '').trim()) return sendJson(422, { detail: `the override of ${o.key} needs a person's name: a decision needs a reviewer name` });
        }
        const byKey = new Map(overrides.map((o) => [o.key, o]));
        const values = served.values.map((v) => {
          const o = byKey.get(v.key);
          if (!o) return v;
          const who = String(o.by).trim();
          return {
            key: v.key, value: o.value, low: o.low ?? null, high: o.high ?? null,
            source: { kind: 'assumption', id: null, note: `typed on ${o.at}${o.note ? `: ${o.note}` : ''}`, by: who },
            origin: 'assumption', identified: null, overriddenBy: who, libraryDefault: v.libraryDefault ?? null,
            recordIds: [], detail: `typed by ${who} on ${o.at}${o.note ? `: ${o.note}` : ''}`, outOfBounds: null,
          };
        });
        return sendJson(200, {
          scope, values, waiting: values.filter((v) => v.origin === 'waiting').map((v) => v.key),
          basisInputs: values.filter((v) => v.overriddenBy).map((v) => ({ name: v.key, value: v.value, unit: specs.get(v.key).unit, source: v.source })),
          warnings: [], notes: served.notes,
        });
      }
      if (url === '/api/fermos/vessel' && req.method === 'POST') {
        let raw = '';
        for await (const chunk of req) raw += chunk;
        const asked = JSON.parse(raw || '{}');
        vesselPosts.push(asked);
        if (flags.vesselDelayMs > 0) await new Promise((r) => setTimeout(r, flags.vesselDelayMs));
        const fx = await vesselFixture();
        const keyed = (os) => JSON.stringify((os ?? []).map((o) => [o.key, o.value]).sort());
        const source = asked.simulation ?? asked.fit ?? null;
        const typed = new Map((asked.overrides ?? []).map((o) => [o.key, o]));
        const scaled = typed.has('plant_scale') || typed.has('batch_volume');
        const recorded = fx.designs.find((d) => d.status === 200 && (d.request.simulation ?? d.request.fit) === source &&
          (d.request.vesselType ?? null) === (asked.vesselType ?? null) && keyed(d.request.overrides) === keyed(asked.overrides));
        if (recorded) {
          // The person's name laid on as the service lays it on: on each value they typed, and on its basis input.
          const named = (src, key) => (typed.has(key) && src?.kind === 'assumption' ? { ...src, by: String(typed.get(key).by).trim() } : src);
          const body = recorded.body;
          const dr = body.designResults ?? {};
          const summary = {
            artifactId: body.artifactId, provenance: body.provenance, createdAt: body.createdAt, source: body.source,
            sourceTool: body.sourceTool, unitClass: body.unitClass, vesselType: body.vesselType ?? null,
            vessels: dr['Number of reactors'] ?? null, volume: dr['Reactor volume'] ?? null, installed: body.cost?.installed ?? null,
          };
          vesselsKept.splice(0, vesselsKept.length, summary, ...vesselsKept.filter((v) => v.artifactId !== summary.artifactId));
          return sendJson(200, {
            ...body,
            parameters: body.parameters.map((v) => (typed.has(v.key) ? { ...v, overriddenBy: String(typed.get(v.key).by).trim(), source: named(v.source, v.key) } : v)),
            evidence: { ...body.evidence, basis: { ...body.evidence.basis, inputs: body.evidence.basis.inputs.map((i) => ({ ...i, source: named(i.source, i.name) })) } },
          });
        }
        if (!fx.scopes.some((sc) => (sc.simulation ?? sc.fit) === source)) return sendJson(422, { detail: `no artifact '${source}' is on file here` });
        const refusal = fx.designs.find((d) => d.status === 422);
        if (!scaled && refusal) return sendJson(422, refusal.body);
        return sendJson(422, { detail: 'the double holds no design for this request: it holds the designs the browser tests ask for' });
      }
    }
    // OF-BLD-020 §2.2 — the parameter panel. GET /api/params/{scope}: a seed
    // scenario's scope, or a scenario made here by the flowsheet it names
    // (answered under the id asked), each as demo.py --prototype recorded the
    // real code's answer over the stand-in records; with fermOS fits chosen,
    // the yeast scope as the real code bound it with that choice (the choices
    // the browser tests make), any other a 422 in words. A scope no provider
    // serves yet is the service's 404; a malformed one its 422.
    // POST .../resolve lays each override on as the service does, an
    // assumption by the person it names, its interval's empty end the value
    // when one end is typed (params.held), with the basis inputs a run adds
    // for it (the value, its low and high, and the line saying the run read
    // overrides, copied from the recorded resolve), and returns the words the
    // real code returned for the recorded override outside its bounds; a key
    // the scope does not have, an override of another scope, one naming
    // nobody or one of a parameter whose rule takes no person's value is
    // refused in the service's words. OF-BLD-020 §2.R: the service binds the
    // overrides as a run binds them, so a titre typed beside a fermOS fit
    // chosen for every input is refused in the run's words; that resolve is
    // answered as demo.py recorded the real code's answer (`resolves`).
    {
      const m = /^\/api\/params\/(.+?)(\/resolve)?$/.exec(url);
      if (m) {
        const scope = m[1];
        const resolving = Boolean(m[2]);
        const send = (status, body) => {
          res.writeHead(status, { 'Content-Type': 'application/json' });
          return res.end(JSON.stringify(body));
        };
        if (resolving !== (req.method === 'POST')) return send(405, { detail: 'Method Not Allowed' });
        let ask;
        if (resolving) {
          let raw = '';
          for await (const chunk of req) raw += chunk;
          ask = JSON.parse(raw || '{}');
          paramResolves.push({ scope, ...ask });
        } else {
          const q = new URL(req.url ?? '/', 'http://double').searchParams;
          ask = { flowsheet: q.get('flowsheet'), host: q.get('host'), fits: q.get('fits') ? JSON.parse(q.get('fits')) : {} };
          paramScopes.push({ scope, ...Object.fromEntries(q) });
        }
        // OF-BLD-020 §3.3 — a family's scope, as demo.py --prototype recorded
        // the real code binding it over the stand-in yeast records (ethanol
        // on glucose, from the records, for every strain and for
        // CEN.PK113-7D); another ask is the double's 422 in its own words.
        const family = /^fermos:family:([A-Za-z0-9][A-Za-z0-9._-]{0,127})$/.exec(scope)?.[1];
        if (family) {
          const sim = await prototype('fermos-simulate.json');
          const asked = { family, ...ask, strain: ask.strain ?? null };
          if (!resolving) {
            const q = new URL(req.url ?? '/', 'http://double').searchParams;
            for (const k of ['strain', 'product', 'sugar', 'fit', 'startFrom', 'durationPreset']) asked[k] = q.get(k);
          }
          const answer = simAskRecorded(asked) ? sim.scopes[simKey(asked)] : null;
          if (!answer) return send(422, { detail: `the double holds no binding of ${scope} for this ask: it holds ethanol on glucose from the records` });
          if (answer.status !== 200) return send(answer.status, answer.body);
          const served = { ...answer.body, scope };
          if (!resolving) return send(200, served);
          const overrides = ask.overrides ?? [];
          const why = overrideRefusal(scope, overrides, served.specs.map((sp) => sp.key));
          if (why) return send(422, { detail: why });
          const specs = new Map(served.specs.map((sp) => [sp.key, sp]));
          const values = laidOn(served.values, overrides);
          const basisInputs = values
            .filter((v) => v.overriddenBy)
            .flatMap((v) => [
              { name: v.key, value: v.value, unit: specs.get(v.key).unit, source: v.source },
              ...(v.low != null ? [{ name: `${v.key} low`, value: v.low, unit: specs.get(v.key).unit, source: v.source }] : []),
              ...(v.high != null ? [{ name: `${v.key} high`, value: v.high, unit: specs.get(v.key).unit, source: v.source }] : []),
            ]);
          return send(200, { scope, values, waiting: values.filter((v) => v.origin === 'waiting').map((v) => v.key), basisInputs, warnings: [], notes: served.notes });
        }
        const kinds = {
          'fermos:family': "fermOS's model families",
          'fermos:vessel': "fermOS's vessel designs",
          'fermos:forecast': "fermOS's forecasts",
          'pureos:unit': "pureOS's train units outside the Builder's recorded train",
        };
        const other = Object.keys(kinds).find((k) => scope.startsWith(`${k}:`));
        if (other) return send(404, { detail: `this service serves no parameters for ${kinds[other]} yet` });
        const id = /^proforma:([A-Za-z0-9][A-Za-z0-9._-]{0,127})$/.exec(scope)?.[1];
        if (!id)
          return send(422, {
            detail: `a parameter scope is fermos:family:<family id>, fermos:vessel:<simulation artifact id>, fermos:forecast:<kinetic fit artifact id>, pureos:unit:<train id>:<unit id> or proforma:<scenario id>, each id letters, digits, dots, dashes and underscores; '${scope}' is none of them`,
          });
        const recorded = await prototype('params-proforma.json');
        const fits = ask.fits ?? {};
        const typed = new Set((ask.overrides ?? []).map((o) => o.key));
        const kept = Object.fromEntries(Object.entries(fits).filter(([k]) => !typed.has(k)));
        if (resolving && typed.size > 0 && Object.keys(fits).length > 0) {
          const withFits = await prototype('params-proforma-fits.json');
          const keys = [...typed].sort().join();
          const heard = scope === withFits.scope && (withFits.resolves ?? []).find((r) => sameFits(fits, r.fits) && [...r.keys].sort().join() === keys);
          if (heard) return send(heard.status, heard.body);
        }
        let answer;
        if (Object.keys(kept).length > 0) {
          const withFits = await prototype('params-proforma-fits.json');
          answer = (scope === withFits.scope || ask.flowsheet === 'ethanol_glucose_v0') && fitsAnswer(JSON.stringify(kept), withFits.answers);
          if (!answer) return send(422, { detail: `the double holds no binding of ${scope} with these fits` });
        } else if (recorded.scopes[scope]) answer = recorded.scopes[scope];
        else if (ask.flowsheet && recorded.flowsheets[ask.flowsheet]) answer = recorded.flowsheets[ask.flowsheet];
        else if (ask.flowsheet)
          answer = { status: 422, body: { detail: `there is no flowsheet ${ask.flowsheet} on the shelf; it holds ${Object.keys(recorded.flowsheets).filter((k) => k !== 'toy').join(', ')}` } };
        else
          answer = {
            status: 404,
            body: {
              detail: `there is no scenario ${id}: the seed's BioSTEAM scenarios are ${Object.keys(recorded.scopes).map((k) => k.slice('proforma:'.length)).join(', ')}, and a scenario made in a browser names the shelf flowsheet it runs (?flowsheet=)`,
            },
          };
        if (answer.status !== 200) return send(answer.status, answer.body);
        const served = { ...answer.body, scope };
        if (!resolving) return send(200, served);
        // The resolve: each override laid on as the service lays it on.
        const specs = new Map(served.specs.map((sp) => [sp.key, sp]));
        const overrides = ask.overrides ?? [];
        const stray = [...new Set(overrides.map((o) => o.scope).filter((sc) => sc !== scope))].sort();
        if (stray.length) return send(422, { detail: `an override names the scope it changes, and these were sent to ${scope}: ${stray.join(', ')}` });
        const seen = new Set();
        for (const o of overrides) {
          if (!specs.has(o.key)) return send(422, { detail: `there is no parameter ${o.key} here; the parameters are ${[...specs.keys()].join(', ')}` });
          if (seen.has(o.key)) return send(422, { detail: `two overrides of ${o.key}: one person's value a parameter` });
          seen.add(o.key);
          const sp = specs.get(o.key);
          if (!sp.sourceRule.includes('assumption'))
            return send(422, {
              detail: sp.sourceRule.includes('convention')
                ? `${o.key} is a convention${sp.convention != null ? `, ${sp.convention},` : ''} that every run states in its basis, and takes no person's value: its source rule takes no assumption`
                : `${o.key} is the library's own default, read from its code, and takes no person's value`,
            });
          if (!String(o.by ?? '').trim()) return send(422, { detail: `the override of ${o.key} needs a person's name: a decision needs a reviewer name` });
        }
        const out = recorded.resolve.body.values;
        // The recorded override outside its bounds, on the flowsheet it was recorded on, gets the real code's words.
        const flowsheet = ask.flowsheet ?? recorded.flowsheetOf[scope] ?? null;
        const flagged = (o) => {
          const r = recorded.resolve.request.overrides.find((x) => x.key === o.key && x.value === o.value && (x.low ?? null) === (o.low ?? null) && (x.high ?? null) === (o.high ?? null));
          return r && flowsheet === recorded.resolve.flowsheet ? (out.find((v) => v.key === o.key)?.outOfBounds ?? null) : null;
        };
        const byKey = new Map(overrides.map((o) => [o.key, o]));
        // params.held: one end typed, the other is the value; neither, held at itself.
        const held = (o) => (o.low == null && o.high == null ? [null, null] : [o.low ?? o.value, o.high ?? o.value]);
        const values = served.values.map((v) => {
          const o = byKey.get(v.key);
          if (!o) return v;
          const [low, high] = held(o);
          return {
            key: v.key, value: o.value, low, high,
            source: { kind: 'assumption', id: null, note: `typed on ${o.at}${o.note ? `: ${o.note}` : ''}`, by: String(o.by).trim() },
            origin: 'assumption', identified: null, overriddenBy: String(o.by).trim(), libraryDefault: v.libraryDefault ?? null,
            recordIds: [], detail: `typed by ${String(o.by).trim()} on ${o.at}${o.note ? `: ${o.note}` : ''}`, outOfBounds: flagged(o),
          };
        });
        // What a run adds for them (proforma.assumption_inputs): the value, its low and its high, then the line saying it read overrides.
        const readLine = recorded.resolve.body.basisInputs.find((i) => i.name === 'assumptions read from');
        const basisInputs = values
          .filter((v) => v.overriddenBy)
          .flatMap((v) => [
            { name: v.key, value: v.value, unit: specs.get(v.key).unit, source: v.source },
            { name: `${v.key} low`, value: v.low ?? v.value, unit: specs.get(v.key).unit, source: v.source },
            { name: `${v.key} high`, value: v.high ?? v.value, unit: specs.get(v.key).unit, source: v.source },
          ])
          .concat(overrides.length && readLine ? [readLine] : []);
        return send(200, {
          scope,
          values,
          waiting: values.filter((v) => v.origin === 'waiting').map((v) => v.key),
          basisInputs,
          warnings: values.map((v) => v.outOfBounds).filter(Boolean),
          notes: served.notes,
        });
      }
    }
    // OF-BLD-014 §8.4 — the BioSTEAM scenarios, bound over stand-in records,
    // and runs made through the real code with a stand-in evaluator.
    // OF-BLD-019 §2.3 (b): the seed's scenarios with the program switch off
    // (sc-yeast-1) and, asked with ?includeArchived=true, on (sc-pha-1 too);
    // the switch is read from the request's own URL, which keeps its query.
    if (url.startsWith('/api/proforma/scenarios') && req.method === 'GET') {
      const on = new URL(req.url ?? '/', 'http://double').searchParams.get('includeArchived') === 'true';
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(await prototype(on ? 'proforma-scenarios-archived.json' : 'proforma-scenarios.json')));
    }
    // (c): a shelf flowsheet bound as a scenario made in the browser shows it,
    // or the service's refusal in its words, each as demo.py --prototype
    // recorded it for the switch off and on.
    if (url === '/api/proforma/bind' && req.method === 'GET') {
      const q = new URL(req.url ?? '/', 'http://double').searchParams;
      const flowsheet = q.get('flowsheet') ?? '';
      // OF-BLD-019 §5.1: with fermOS fits chosen, the binding the real code
      // made with the stand-in forecast for every input it feeds; §5.R: and
      // with the other choices the browser tests make (`others`: the fit for
      // titre and yield, bound; the forecast's productivity beside the fit's
      // titre, refused), each as the real code answered; any other choice is
      // a 422 in words.
      if (q.get('fits')) {
        proformaBinds.push(Object.fromEntries(q));
        const fixture = await prototype('proforma-bind-fits.json');
        const answer = fitsAnswer(q.get('fits'), [{ fits: fixture.fits, status: 200, body: fixture.body }, ...(fixture.others ?? [])]);
        const found = flowsheet === fixture.flowsheet && answer;
        res.writeHead(found ? answer.status : 422, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(found ? answer.body : { detail: `the double holds no binding of ${flowsheet} with these fits` }));
      }
      const answers = (await prototype('proforma-bind.json'))[q.get('includeArchived') === 'true' ? 'on' : 'off'];
      const answer = answers[flowsheet] ?? {
        status: 422,
        body: { detail: `there is no flowsheet ${flowsheet} on the shelf; it holds ${Object.keys(answers).filter((k) => k !== 'toy').join(', ')}` },
      };
      res.writeHead(answer.status, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(answer.body));
    }
    // OF-BLD-019 §5.2 — a scenario's yield read against the geneOS ceiling,
    // as the real code read it over the stand-in records with no ceiling on
    // file and with the STAND-IN ceiling on file (flags.ceilingOnFile picks),
    // by the flowsheet the scenario runs: a seed's own, or the one a scenario
    // made here names, answered under the id asked; anything else is the
    // service's 422 in words.
    if (url === '/api/proforma/ceiling-check' && req.method === 'GET') {
      const q = new URL(req.url ?? '/', 'http://double').searchParams;
      ceilingChecks.push(Object.fromEntries(q));
      const scenarioId = q.get('scenarioId') ?? '';
      const seeds = await prototype('proforma-scenarios-archived.json');
      const flowsheet = seeds.find((sc) => sc.id === scenarioId)?.flowsheet ?? q.get('flowsheet') ?? '';
      const recorded = await prototype('proforma-ceiling-check.json');
      // §5.R: with fermOS fits chosen, the check the real code made of
      // sc-yeast-1 with that choice (`fitted`), read or refused in its words;
      // any other choice is a 422 in words, as the binding's is.
      if (q.get('fits')) {
        const fitted = flowsheet === 'ethanol_glucose_v0' && fitsAnswer(q.get('fits'), recorded.fitted[flags.ceilingOnFile ? 'onFile' : 'none']);
        res.writeHead(fitted ? fitted.status : 422, { 'Content-Type': 'application/json' });
        return res.end(
          JSON.stringify(
            !fitted
              ? { detail: `the double holds no ceiling check of ${flowsheet || 'no flowsheet'} with these fits` }
              : fitted.status === 200
                ? { ...fitted.body, scenarioId }
                : fitted.body,
          ),
        );
      }
      const answer = recorded[flags.ceilingOnFile ? 'onFile' : 'none'][flowsheet];
      if (!answer) {
        res.writeHead(422, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ detail: `there is no seed scenario ${scenarioId}, and ${flowsheet || 'no flowsheet'} is not one a scenario made here can run` }));
      }
      res.writeHead(answer.status, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ ...answer.body, scenarioId }));
    }
    // (d): a seed scenario's run by its id; a scenario made in the browser
    // gets the run of the seed scenario on the flowsheet it names, under its
    // own id (the stand-in's artifact still names the seed scenario in its
    // basis); anything else is the service's 422, in words.
    if (url === '/api/proforma/run' && req.method === 'POST') {
      let body = '';
      for await (const chunk of req) body += chunk;
      const asked = JSON.parse(body || '{}');
      proformaRuns.push(asked);
      const seeds = await prototype('proforma-scenarios-archived.json');
      const bySeed = { 'sc-pha-1': 'proforma-run.json', 'sc-yeast-1': 'proforma-run-yeast.json' };
      const byFlowsheet = { pha_sugar_v0: 'proforma-run.json', ethanol_glucose_v0: 'proforma-run-yeast.json' };
      const name = bySeed[asked.scenarioId] ?? (asked.scenarioId ? byFlowsheet[asked.flowsheet] : undefined);
      const refuse = (detail) => {
        res.writeHead(422, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ detail }));
      };
      if (!name)
        return refuse(
          asked.flowsheet
            ? `${asked.flowsheet} is not a flowsheet a scenario made here can run`
            : `there is no seed scenario ${asked.scenarioId}; the seed's BioSTEAM scenarios are sc-pha-1, sc-yeast-1, and a scenario made here names the flowsheet it runs`,
        );
      // Inputs that still wait are refused as the service refuses them (§3.2).
      const seed = seeds.find((sc) => sc.id === asked.scenarioId);
      const bound = seed ?? seeds.find((sc) => sc.flowsheet === asked.flowsheet);
      // OF-BLD-020 §2.2: the panel's overrides, and the older assumptions field the service still reads.
      const typed = new Set([...(asked.overrides ?? []).map((o) => o.key), ...(asked.assumptions ?? []).map((a) => a.key), ...Object.keys(asked.fits ?? {})]);
      const waiting = (bound?.inputs ?? []).filter((i) => i.binding === 'waiting' && !typed.has(i.key)).map((i) => i.key);
      if (waiting.length) return refuse(`these inputs wait for a source, a record or a named person's assumption: ${waiting.join(', ')}`);
      const run = await prototype(name);
      proformaRunsOnFile.set(asked.scenarioId, run.artifactId);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(bySeed[asked.scenarioId] ? run : { ...run, scenarioId: asked.scenarioId }));
    }
    // OF-BLD-019 §3.R — a scenario's newest run on the service: the artifact
    // of the run this double answered for it (from artifacts.json, as the
    // artifact store answers it by id), or none; a blank id is the service's
    // 422 in words.
    if (url === '/api/proforma/runs' && req.method === 'GET') {
      const sid = (new URL(req.url ?? '/', 'http://double').searchParams.get('scenarioId') ?? '').trim();
      if (!sid) {
        res.writeHead(422, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ detail: "a read of a scenario's runs names the scenario it belongs to" }));
      }
      const id = proformaRunsOnFile.get(sid);
      const artifact = id ? ((await prototype('artifacts.json')).find((a) => a.id === id) ?? null) : null;
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify({ scenarioId: sid, artifact }));
    }
    // OF-BLD-014 §6.4 — geneOS's shelf and its computations, from the toy
    // network's fixtures: a ceiling or envelope for the sugar asked, the mix.
    if (url === '/api/geneos/models' && req.method === 'GET') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(await prototype('geneos-models.json')));
    }
    if (['/api/geneos/ceiling', '/api/geneos/frontier', '/api/geneos/mix'].includes(url) && req.method === 'POST') {
      let body = '';
      for await (const chunk of req) body += chunk;
      const asked = JSON.parse(body || '{}');
      geneosCalls.push({ path: url, ...asked });
      const kind = url.split('/').pop();
      if (asked.modelId !== 'toy') {
        res.writeHead(409, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ detail: `${asked.modelId}'s file is not on this machine: run pnpm geneos:fetch` }));
      }
      const fixture = await prototype(`geneos-${kind}.json`);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(kind === 'mix' ? fixture : fixture[asked.substrate]));
    }
    // OF-BLD-014 §5.3 — Postdoc's loop, replayed from the stream
    // `demo.py --prototype` recorded through the real loop. Each step is held
    // back a moment, so the panel is seen drawing steps as they arrive.
    if ((url === '/api/ask/stream' || url === '/api/ask') && req.method === 'POST') {
      let body = '';
      for await (const chunk of req) body += chunk;
      const asked = JSON.parse(body || '{}');
      asks.push({ path: url, ...asked });
      // §9.4 — a question that asks for a draft replays the drafting loop.
      const recording = /^draft\b/i.test(String(asked.question ?? '').trim()) ? 'ask-draft-stream.jsonl' : 'ask-stream.jsonl';
      const lines = (await readFile(join(PROTOTYPE, recording), 'utf8')).trim().split('\n').map((l) => JSON.parse(l));
      const events = lines.filter((l) => l.event);
      if (url === '/api/ask') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(events.find((e) => e.event === 'plan').data));
      }
      res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' });
      // §10.3 — a replay says it is one, with the date the run was recorded
      // and whether a scripted stand-in stood in for the model.
      const head = lines[0] ?? {};
      res.write(`event: replay\ndata: ${JSON.stringify({ recordedAt: head.recordedAt ?? 'an unknown date', standIn: head.standIn !== false })}\n\n`);
      for (const e of events) {
        await new Promise((r) => setTimeout(r, 250));
        res.write(`event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`);
      }
      return res.end();
    }
    if (url.startsWith('/api/proposals') && !seedOnly) {
        if (proposals === null) proposals = await prototype('proposals.json');
        if (req.method === 'GET') {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          return res.end(JSON.stringify(proposals.filter((p) => p.state === 'proposed')));
        }
        const [id, verb] = url.slice('/api/proposals/'.length).split('/');
        let body = '';
        for await (const chunk of req) body += chunk;
        const { person, reason } = JSON.parse(body);
        const found = proposals.find((p) => p.id === id);
        if (!found || !person || person.length < 2) {
          res.writeHead(422, { 'Content-Type': 'application/json' });
          return res.end(JSON.stringify({ detail: 'a proposal is carried out or dismissed by a named person' }));
        }
        found.state = verb === 'dismiss' ? 'dismissed' : 'done';
        found.carriedOutBy = person;
        found.result = verb === 'dismiss' ? reason : `handed to ${person}: ${found.how}`;
        proposalActs.push({ id, verb, person });
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(found));
      }
      if (url === '/api/audit' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end('[]');
      }
    if (url === '/api/biorepo/overlay') {
        // Answered late on purpose: a screen mounted before the overlay arrives
        // has to cope with it arriving — Guild's queue in particular (§7.3) —
        // and a double that answered instantly would let that path go untested.
        await new Promise((r) => setTimeout(r, 700));
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(await readFile(OVERLAY_FIXTURE));
      }
      // OF-BLD-020 §6.1: the train runs pureOS keeps, as a fresh install has
      // them (none), for New scenario from a vessel and a train. Last in the
      // chain, so a handler that serves kept train runs answers first.
      if (url === '/api/pureos/train-runs' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end('[]');
      }
      if (url.startsWith('/api/')) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ detail: 'not part of the smoke double' }));
      }
      await serveStatic(dist, url, res);
    } catch (e) {
      res.writeHead(404).end('not found');
    }
  });

  return { server, state: { decisions, checks, guildLedger, guildPosts, practiceState, practicePosts, ragSearches, asks, geneosCalls, fermosCalls, proformaRuns, proformaBinds, proformaReferences, proformaRunsOnFile, proposalActs, thermoCalls, pureosProposals, ceilingChecks, paramScopes, paramResolves, vesselPosts, fermosBinds, fermosSimulates, fermosSimulationsOnFile, harvestReads, builderCalls, trainRunsOnFile, flags } };
}
