# openFerment: start here

This folder is the whole of openFerment: the service, the built app, and a script that sets up
and starts everything on this computer.

## Start it

On a Mac, double-click **openFerment.command**. If macOS says it cannot be opened because it was
downloaded, right-click it, choose Open, then Open again.

Or, in a terminal in this folder, on a Mac or on Linux:

    bash start.sh

The first start takes five to ten minutes, because it downloads the Python packages (BioSTEAM
among them). Later starts take under a minute. When it says "openFerment is running", the app
opens in the browser. Ctrl-C in the terminal stops it.

## What you need first

- A Mac with [Homebrew](https://brew.sh), or Linux. On a Mac the script installs what is missing
  through Homebrew: uv (which brings its own Python), PostgreSQL with the pgvector extension, and
  Graphviz.
- An internet connection for the first start.
- An Anthropic API key, for Postdoc alone. The script asks for it once and keeps it in
  `core/.env` on this computer. Press Enter to skip it: the plants, the flowsheets and the TEA
  run without a key.

## What it does to this computer

- Everything stays inside this folder. The database is this folder's own, in `.openferment/pg`,
  on a port of its own, so another PostgreSQL or another openFerment on the same computer is left
  alone. Your projects are in that database and in `core/data/`.
- The service listens on this computer alone (127.0.0.1). Nothing is reachable from the network.
- To remove it all, stop it and delete this folder.

## Other commands

    bash start.sh --check     set up, say what is ready, start nothing
    bash start.sh --stop      stop the database if a start was cut off and left it running

## A first walk through it

1. Make a project on the home page.
2. Proforma, then Studies: pick `cellulosic_ethanol_v0` and run it. The run page shows the
   minimum selling price, what the price is made of, the stream table and the flowsheet.
3. On the run, change the feedstock's dry composition (the `feed.dry.` parameters, which must
   still sum to one) and run again as a scenario, then compare the two.
4. Flowsheets: open the run's record for the whole plant on one page; Full size for unit names.
5. Postdoc, with a key: ask it to run a plant and explain the price, or to look something up on
   the web. A claim from the web is marked unverified and links its pages.

`pnpm` and Node are needed only to change the app's own code; `README.md` and `CLAUDE.md` cover
development.
