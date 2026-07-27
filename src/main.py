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

from .backtest.engine import BEAR_WINDOWS, buy_and_hold, run_backtest, window_return
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


def cmd_backtest(cfg: Config) -> int:
    store = BarStore(cfg.data.db_path)
    closes = store.load_closes(cfg.all_symbols)
    store.close()
    if closes.empty:
        print("no price data — run `python -m src.main backfill` first", file=sys.stderr)
        return 1

    cost = cfg.backtest.cost_bps
    print(
        f"backtest through {closes.index.max().date()}  "
        f"(costs: {cost} bps/side, benchmark: hold {cfg.backtest.benchmark})\n"
    )
    header = f"{'':<24}{'CAGR':>8}{'total':>10}{'max DD':>9}{'sharpe':>8}{'years':>7}"
    for strategy in build_strategies(cfg):
        weights = strategy.target_weights(closes)
        if weights.empty:
            print(f"[{strategy.name}] not enough history to backtest\n")
            continue
        result = run_backtest(closes, weights, cost_bps=cost, name=strategy.name)
        bench = buy_and_hold(closes, cfg.backtest.benchmark, weights.index[0], cost_bps=cost)

        print(f"[{strategy.name}]  ({weights.index[0].date()} -> {closes.index.max().date()})")
        print(header)
        for r in (result, bench):
            m = r.metrics
            print(
                f"  {r.name:<22}{m['cagr']:>8.1%}{m['total_return']:>10.1%}"
                f"{m['max_drawdown']:>9.1%}{m['sharpe']:>8.2f}{m['years']:>7.1f}"
            )
        for label, (start, end) in BEAR_WINDOWS.items():
            ours = window_return(result.equity, start, end)
            theirs = window_return(bench.equity, start, end)
            if ours is not None and theirs is not None:
                print(f"    {label:<20} strategy {ours:>7.1%}   benchmark {theirs:>7.1%}")
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="etf-trader")
    parser.add_argument("command", choices=["backfill", "signals", "backtest"])
    parser.add_argument("--config", default="config.yaml")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    if args.command == "backfill":
        return cmd_backfill(cfg)
    if args.command == "backtest":
        return cmd_backtest(cfg)
    return cmd_signals(cfg)


if __name__ == "__main__":
    raise SystemExit(main())
