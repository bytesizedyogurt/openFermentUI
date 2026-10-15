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
      asks.push({ path: url, ...JSON.parse(body || '{}') });
      const lines = (await readFile(join(PROTOTYPE, 'ask-stream.jsonl'), 'utf8')).trim().split('\n').map((l) => JSON.parse(l));
      const events = lines.filter((l) => l.event);
      if (url === '/api/ask') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        return res.end(JSON.stringify(events.find((e) => e.event === 'plan').data));
      }
      res.writeHead(200, { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache' });
      for (const e of events) {
        await new Promise((r) => setTimeout(r, 250));
        res.write(`event: ${e.event}\ndata: ${JSON.stringify(e.data)}\n\n`);
      }
      return res.end();
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

  return { server, state: { decisions, checks, guildLedger, guildPosts, practiceState, practicePosts, ragSearches, asks, geneosCalls } };
}
