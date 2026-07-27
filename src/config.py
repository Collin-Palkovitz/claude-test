"""Load and validate config.yaml into plain dataclasses."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class DataConfig:
    source: str = "stooq"
    db_path: str = "data/bars.db"
    start_date: str = "2004-01-01"


@dataclass
class TrendFilterConfig:
    symbol: str = "SPY"
    ma_days: int = 200


@dataclass
class MomentumRotationConfig:
    lookback_months: list[int] = field(default_factory=lambda: [3, 6, 12])
    top_n: int = 2
    min_history_days: int = 260


@dataclass
class Config:
    mode: str = "signals"
    universe: list[str] = field(default_factory=lambda: ["SPY"])
    cash_proxy: str = "BIL"
    data: DataConfig = field(default_factory=DataConfig)
    trend_filter: TrendFilterConfig = field(default_factory=TrendFilterConfig)
    momentum_rotation: MomentumRotationConfig = field(
        default_factory=MomentumRotationConfig
    )

    @property
    def all_symbols(self) -> list[str]:
        """Universe plus the cash proxy, deduplicated, order preserved."""
        symbols = list(self.universe)
        if self.cash_proxy and self.cash_proxy not in symbols:
            symbols.append(self.cash_proxy)
        if self.trend_filter.symbol not in symbols:
            symbols.append(self.trend_filter.symbol)
        return symbols


def load_config(path: str | Path = "config.yaml") -> Config:
    raw = yaml.safe_load(Path(path).read_text()) or {}
    strategies = raw.get("strategies", {})
    return Config(
        mode=raw.get("mode", "signals"),
        universe=[s.upper() for s in raw.get("universe", ["SPY"])],
        cash_proxy=(raw.get("cash_proxy") or "").upper(),
        data=DataConfig(**raw.get("data", {})),
        trend_filter=TrendFilterConfig(**strategies.get("trend_filter", {})),
        momentum_rotation=MomentumRotationConfig(
            **strategies.get("momentum_rotation", {})
        ),
    )
