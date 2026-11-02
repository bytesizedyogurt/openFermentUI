// pureOS → Propose a train (OF-BLD-020 §7.2, D12): a small chooser on pureOS's
// index — a product, the host it is made in, and optionally the train's inlet
// — whose answer is the service's, never the browser's.
//
// THE RULES ARE THE SERVICE'S. `POST /api/pureos/propose` reads the product's
// class and the properties its class's rule splits on (thermosteam's
// volatility, Biopython's ProtParam on the sequence a product's entry
// carries, whether the entry says the product is secreted) and proposes a
// train of catalogue unit types in order, each with one reason naming the
// rule, the property and the artifact that holds it; or nothing, naming each
// missing property. This file sends ids and words and shows what comes back
// (`ProposedTrainView`): no number on it comes from the browser, and no
// parameter is typed here. A proposal that proposed a train is kept in this
// session's store under a new train id (`keepProposedTrain`), where pureOS's
// Builder (/pureos/build/:trainId, OF-BLD-020 §5.3) opens it with the reasons
// beside each unit, every parameter at its library default or waiting.
//
// The products offered are the ones fermOS and geneOS have words for
// (lib/geneos.ts's PRODUCT_WORDS) and then the products on file; the hosts are
// the strains on file; the inlet is none (typed in the Builder) or a kept
// simulation's harvest. Products and strains arrive with the documents that
// report them, through Intake. The service refuses what does not fit, in words.
import { useEffect, useMemo, useState } from 'react';
import type { SimulationSummary, TrainProposal } from '@/data/types';
import { useStore } from '@/store';
import { PureosDown, PureosRefused, proposeTrain } from '@/lib/pureos';
import { PRODUCT_WORDS, productWords } from '@/lib/geneos';
import { fermosSimulations } from '@/lib/fermos';
import { Button, Callout, Card, SectionTitle } from '@/components/ui';
import { ProposedTrainView } from '@/components/ProposedTrain';

const problemOf = (e: unknown) =>
  e instanceof PureosDown
    ? `${e.message} ${e.remedy ?? ''}`.trim()
    : e instanceof PureosRefused
      ? e.message
      : e instanceof Error
        ? e.message
        : String(e);

export function ProposeTrain() {
  const hosts = useStore((s) => s.strains);
  const products = useStore((s) => s.products);
  const keepProposedTrain = useStore((s) => s.keepProposedTrain);
  const named = useMemo(() => Object.keys(PRODUCT_WORDS), []);
  const catalogue = useMemo(() => products.filter((p) => !named.includes(p.id)), [products, named]);
  const [open, setOpen] = useState(false);
  const [product, setProduct] = useState('');
  const [host, setHost] = useState('');
  const [inlet, setInlet] = useState('');
  const [sims, setSims] = useState<SimulationSummary[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const [result, setResult] = useState<{ proposal: TrainProposal; trainId: string | null } | null>(null);

  // The kept simulations a harvest can be the inlet of, read when the chooser opens.
  useEffect(() => {
    if (!open) return;
    const ctrl = new AbortController();
    fermosSimulations(ctrl.signal)
      .then(setSims)
      .catch(() => !ctrl.signal.aborted && setSims([]));
    return () => ctrl.abort();
  }, [open]);

  const productChosen = product || named[0] || catalogue[0]?.id || '';
  const hostChosen = host && hosts.some((s) => s.id === host) ? host : (hosts[0]?.id ?? '');

  const propose = () => {
    setBusy(true);
    setProblem(null);
    setResult(null);
    proposeTrain({ product: productChosen, host: hostChosen, inletRef: inlet || null })
      .then((proposal) => setResult({ proposal, trainId: keepProposedTrain(proposal) }))
      .catch((e: unknown) => setProblem(problemOf(e)))
      .finally(() => setBusy(false));
  };

  return (
    <section className="mt-5" aria-labelledby="pureos-propose" data-testid="pureos-propose">
      <SectionTitle
        right={
          <Button size="sm" onClick={() => setOpen((o) => !o)} aria-expanded={open} data-testid="pureos-propose-open">
            Propose a train
          </Button>
        }
      >
        <span id="pureos-propose">Propose a train</span>
      </SectionTitle>
      <p className="text-body text-ink-soft">
        The service proposes a train for a product and a host by written rules, each naming the property it read:
        thermosteam's boiling points and azeotrope for a small molecule, ProtParam's isoelectric point and molecular
        weight on a protein's sequence, and where the product's entry says the product is. Every parameter stays at its
        library default or waits for you in the Builder.
      </p>
      {open && (
        <Card className="p-4 mt-3 space-y-3" data-testid="pureos-propose-chooser">
          <div className="grid gap-3 md:grid-cols-3">
            <label className="block text-caption text-ink-soft">
              Product
              <select
                className="input mt-1 w-full"
                aria-label="Product"
                value={productChosen}
                onChange={(e) => setProduct(e.target.value)}
                data-testid="propose-product"
              >
                <optgroup label="Named by fermOS and geneOS">
                  {named.map((p) => (
                    <option key={p} value={p}>
                      {productWords(p).option}
                    </option>
                  ))}
                </optgroup>
                {catalogue.length > 0 && (
                  <optgroup label="Products on file">
                    {catalogue.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </optgroup>
                )}
              </select>
            </label>
            <label className="block text-caption text-ink-soft">
              Host
              <select
                className="input mt-1 w-full"
                aria-label="Host"
                value={hostChosen}
                onChange={(e) => setHost(e.target.value)}
                data-testid="propose-host"
              >
                {hosts.map((s) => (
                  <option key={s.id} value={s.id}>
                    {`${s.binomial} ${s.designation}`.trim()}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-caption text-ink-soft">
              Inlet
              <select
                className="input mt-1 w-full"
                aria-label="Inlet"
                value={inlet}
                onChange={(e) => setInlet(e.target.value)}
                data-testid="propose-inlet"
              >
                <option value="">None: typed in the Builder</option>
                {(sims ?? []).map((s) => (
                  <option key={s.artifactId} value={s.artifactId}>
                    {`${s.title} simulation ${s.artifactId}${s.product ? `, ${productWords(s.product).short}` : ''}`}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button variant="primary" onClick={propose} disabled={busy || !productChosen || !hostChosen} data-testid="propose-submit">
              {busy ? 'Proposing…' : 'Propose'}
            </Button>
            {!hostChosen && (
              <span className="text-caption text-ink-soft">
                No host is on file in geneOS yet: strains arrive with the documents that report them, through Intake.
              </span>
            )}
          </div>
          {problem && (
            <div data-testid="propose-problem">
              <Callout kind="warn" title="The service did not propose a train">
                <p className="text-ink">{problem}</p>
              </Callout>
            </div>
          )}
          {result && <ProposedTrainView proposal={result.proposal} trainId={result.trainId} />}
        </Card>
      )}
    </section>
  );
}
