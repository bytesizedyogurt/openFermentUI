# H4-02: custom_train_v1's cost card closes on a price per kg of stream while its lines are per kg of product contained

**Statement.** A `custom_train_v1` run states its price's basis flow as the product the train's product stream
contains, while the TEA breakdown sets `productPrice` to the TEA's price per kg of the whole stream; the cost
card's closing row (9.0791) is on another basis than its lines, which sum to 9.1546, the run's base price, and the
note under it says the lines sum to 9.0791 and that the TEA solved another price, both false.

**Contract it breaks.**

- `core/openferment_core/flowsheets/__init__.py:20-21`: "`tea`, `product`, `feedstock`, the solved `price` (USD per
  kg of the product stream), `basis_flow` (kg/hr the price is per)". `custom_train_v1.parts` hands a `price` per kg
  of the stream with a `basis_flow` of the product contained, so its price is per one flow and its basis flow is
  another.
- `src/components/figures/CostWaterfall.tsx:7-9`: "The last row is the product price the breakdown was read at
  (`TeaBreakdown.productPrice`), read from the run, never a sum the browser made; the lines sum to it by
  construction in the service." For this run the lines sum to the base price, and the last row is another number.

**Command** (from the repository root): `bash bughunt/repro/H4-02/run.sh`

It makes a fresh database `bh_r_h4_02_card`, starts a keyless service on 127.0.0.1:9030 serving the built app,
makes one project, and with person-assumptions typed in `chain.py` makes a fermOS `batch_v1` simulation, its vessel
design, an `ethanol_glucose_v0` run read into a train (`/api/pureos/train/from-run`) and the train run, then the
composite run (`POST /api/proforma/run`, flowsheet `custom_train_v1`) from the vessel and the train run. It reads
the run's page in Chromium (`screen.mjs`), compares the card with the service's numbers, and cleans up. The card's
screenshot is kept as `screen-composite.png`.

**Expected.** The closing row is 9.1546 USD per kg of Ethanol contained in the train's product stream (the sum of
the lines and the run's base-case price), labelled "Base-case price", with no note of a second price.

**Observed** (run1.log and run2.log). Lines 2.8848 + 0 + 1.0575 + 3.9195 + 1.2928, summing to 9.1546 = `basePrice`;
`tea.productPrice` 9.0791; product stream `T304_outlet` 123.448 kg/h holding 122.430 kg/h Ethanol and 1.018 kg/h
Water; 9.0791 x 123.448 / 122.430 = 9.1546, one price on two bases. The page closes on "Price the lines are read
at 9.0791" in "USD per kg of Ethanol contained in the train's product stream" and its note reads "The breakdown is
read at the product's set price, 9.0791 USD per kg of Ethanol contained in the train's product stream, and its
lines sum to that price. The TEA solves the price at its internal rate of return to 9.1546 ..., the run's base-case
price."

**Likely cause.**

- `core/openferment_core/workers/proforma_worker.py:452`: `"productPrice": _num(product.price)` (the stream's price
  per kg of stream, set from `parts["price"]`) beside `"basisFlow": _num(parts.get("basis_flow", product.F_mass))`;
  the lines divide by `basisFlow` (line 469), so they sum to `product.price x product.F_mass / basisFlow`, which
  equals `product.price` only when the basis flow is the stream's mass.
- `core/openferment_core/flowsheets/custom_train_v1.py:384-386`: `parts` returns `"price": b.price` (per kg of
  `b.product`) with `"basis_flow": float(b.product.imass[b.product_chemical])`, the product contained; its
  `evaluate` (line 358) converts the price to per kg contained for `basePrice`, and `parts` leaves it per kg of
  stream.
- The client then shows the mismatch as two prices: `src/screens/ProformaBiosteam.tsx:221,227` pass
  `tea.productPrice` to `priceNote` and `waterfallTotal` (`src/components/figures/CostWaterfall.tsx:76-92`), whose
  words assume the lines sum to `productPrice`.

The gap is the product stream's impurity (here 0.8 %); `core/tests/test_proforma.py:381` holds the lines' sum to the
base price for `ethanol_glucose_v0` alone, whose basis flow is its product stream, and no test holds it for
`custom_train_v1`.
