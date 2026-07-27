# etf-trader

A personal, systematic ETF trading system. Watches daily market data, generates
signals from trend and momentum rules, and (in later phases) executes trades
through a brokerage API — with risk limits and honest measurement at every step.

See [PLAN.md](PLAN.md) for the full project plan, decision gates, and the
reasoning behind every design choice.

## Status: Phase 1 — data pipeline and signal logging

No order placement of any kind exists in this codebase yet. Phase 1 produces
data and signals only, so they can be verified by eye against any charting site.

## Quickstart

```bash
pip install -r requirements.txt

# 1. Download daily price history for the configured ETF universe
python -m src.main backfill

# 2. See what the strategies would do (current targets + recent signals)
python -m src.main signals
```

Configuration lives in `config.yaml` (universe, data source, strategy
parameters). Price data is stored in a local SQLite database (`data/bars.db`,
git-ignored).

## Data sources

- **stooq** (default): free daily bars, no API key required.
- **alpaca**: set `ALPACA_API_KEY` and `ALPACA_API_SECRET` environment
  variables and change `data.source` to `alpaca` in `config.yaml`.
  Requires `pip install alpaca-py`.

## Strategies

- **trend_filter** — hold the index ETF while it closes above its 200-day
  moving average; move to cash below it.
- **momentum_rotation** — monthly, rank the universe by blended 3/6/12-month
  returns and hold the top N, with an absolute-momentum filter as a safety
  valve.

## Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

Tests run on deterministic synthetic price data — no network needed.
