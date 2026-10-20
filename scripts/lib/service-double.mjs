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
   */
  const flags = { fermosFitsOnFile: false, ceilingOnFile: false };
  /** The ceiling checks the browser asked for (OF-BLD-019 §5.2): each query, as sent. */
  const ceilingChecks = [];
  /** Reference biorefineries the browser asked to run (OF-BLD-019 §2.2). */
  const proformaReferences = [];
  /** thermosteam's answers the browser asked for and got (OF-BLD-019 §4.2), by question. */
  const thermoKept = new Map();
  const thermoCalls = [];

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
        const found = (await prototype('artifacts.json')).find((a) => a.id === id);
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
    // stand-in run: the list with the program switch off (empty: the run is
    // PHA's) and, asked with ?includeArchived=true, on; one train by its
    // scenario or its run's artifact id, else the service's 404 in its words.
    if (url === '/api/pureos/trains' && req.method === 'GET') {
      const on = new URL(req.url ?? '/', 'http://double').searchParams.get('includeArchived') === 'true';
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(await prototype(on ? 'pureos-trains-archived.json' : 'pureos-trains.json')));
    }
    if (url.startsWith('/api/pureos/train/') && req.method === 'GET') {
      const key = url.slice('/api/pureos/train/'.length);
      const train = await prototype('pureos-train.json');
      if (key !== train.scenarioId && key !== train.artifactId) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ detail: `no Proforma run of ${key} is on file here: run the scenario in Proforma, and pureOS reads its train from that run` }));
      }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(train));
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
      // made with the stand-in forecast for every input it feeds; any other
      // choice is a 422 in words.
      if (q.get('fits')) {
        proformaBinds.push(Object.fromEntries(q));
        const fixture = await prototype('proforma-bind-fits.json');
        let asked = null;
        try {
          asked = JSON.parse(q.get('fits'));
        } catch {
          /* answered below */
        }
        const same = asked && flowsheet === fixture.flowsheet && JSON.stringify(Object.entries(asked).sort()) === JSON.stringify(Object.entries(fixture.fits).sort());
        res.writeHead(same ? 200 : 422, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(same ? fixture.body : { detail: `the double holds no binding of ${flowsheet} with these fits` }));
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
      const answer = (await prototype('proforma-ceiling-check.json'))[flags.ceilingOnFile ? 'onFile' : 'none'][flowsheet];
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
      const typed = new Set([...(asked.assumptions ?? []).map((a) => a.key), ...Object.keys(asked.fits ?? {})]);
      const waiting = (bound?.inputs ?? []).filter((i) => i.binding === 'waiting' && !typed.has(i.key)).map((i) => i.key);
      if (waiting.length) return refuse(`these inputs wait for a source, a record or a named person's assumption: ${waiting.join(', ')}`);
      const run = await prototype(name);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      return res.end(JSON.stringify(bySeed[asked.scenarioId] ? run : { ...run, scenarioId: asked.scenarioId }));
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
      if (url.startsWith('/api/')) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify({ detail: 'not part of the smoke double' }));
      }
      await serveStatic(dist, url, res);
    } catch (e) {
      res.writeHead(404).end('not found');
    }
  });

  return { server, state: { decisions, checks, guildLedger, guildPosts, practiceState, practicePosts, ragSearches, asks, geneosCalls, fermosCalls, proformaRuns, proformaBinds, proformaReferences, proposalActs, thermoCalls, ceilingChecks, flags } };
}
