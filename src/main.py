"""etf-trader CLI — Phase 1: data pipeline and signal logging only.

Commands:
    python -m src.main backfill    # download daily bars into the local store
    python -m src.main signals     # print current targets + recent signals

There is deliberately no order-placement code anywhere in this phase.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from .config import Config, load_config
from .data.sources import DataSourceError, make_source
from .data.store import BarStore, backfill
from .strategies.base import Strategy, weights_to_signals
from .strategies.momentum_rotation import MomentumRotation
from .strategies.trend_filter import TrendFilter


def build_strategies(cfg: Config) -> list[Strategy]:
    return [
        TrendFilter(symbol=cfg.trend_filter.symbol, ma_days=cfg.trend_filter.ma_days),
        MomentumRotation(
            universe=cfg.universe,
            cash_proxy=cfg.cash_proxy,
            lookback_months=cfg.momentum_rotation.lookback_months,
            top_n=cfg.momentum_rotation.top_n,
            min_history_days=cfg.momentum_rotation.min_history_days,
        ),
    ]


def cmd_backfill(cfg: Config) -> int:
    source = make_source(cfg.data.source)
    store = BarStore(cfg.data.db_path)
    start = datetime.strptime(cfg.data.start_date, "%Y-%m-%d").date()
    failures = 0
    for symbol in cfg.all_symbols:
        try:
            written = backfill(store, source, [symbol], start)[symbol]
            last = store.last_date(symbol)
            print(f"  {symbol:<6} {written:>6} rows written (through {last})")
        except DataSourceError as exc:
            failures += 1
            print(f"  {symbol:<6} FAILED: {exc}", file=sys.stderr)
    store.close()
    return 1 if failures else 0


def cmd_signals(cfg: Config, recent: int = 15) -> int:
    store = BarStore(cfg.data.db_path)
    closes = store.load_closes(cfg.all_symbols)
    store.close()
    if closes.empty:
        print("no price data — run `python -m src.main backfill` first", file=sys.stderr)
        return 1

    print(f"data through {closes.index.max().date()}\n")
    for strategy in build_strategies(cfg):
        weights = strategy.target_weights(closes)
        if weights.empty:
            print(f"[{strategy.name}] not enough history yet\n")
            continue

        latest = weights.iloc[-1]
        held = latest[latest > 0]
        target = (
            "  ".join(f"{sym} {w:.0%}" for sym, w in held.items())
            if not held.empty
            else "100% cash"
        )
        print(f"[{strategy.name}] current target: {target}")

        signals = weights_to_signals(strategy.name, weights)
        for signal in signals[-recent:]:
            print(
                f"    {signal.date}  {signal.action:<9} {signal.symbol:<6} "
                f"{signal.weight_before:.0%} -> {signal.weight_after:.0%}"
            )
        print(f"    ({len(signals)} signals total over {len(weights)} trading days)\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="etf-trader")
    parser.add_argument("command", choices=["backfill", "signals"])
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    if args.command == "backfill":
        return cmd_backfill(cfg)
    return cmd_signals(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
