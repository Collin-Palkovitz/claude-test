# Crypto Auto-Trading App: Project Plan

A plan for building a personal app that watches the crypto market in real time, generates trade signals from short-term price movements, and executes trades automatically. Written for someone new to algorithmic trading who wants to build, learn, and test safely.

---

## 1. The honest reality check (read this first)

Before any architecture: most retail trading bots lose money, and the strategy style you described ("analyzes small movements, makes trades") is the hardest kind to make profitable. Here's why, with real numbers:

- **Fees eat small movements.** On Kraken or Coinbase, a typical taker fee is 0.25–0.40% per trade. A round trip (buy + sell) costs 0.5–0.8%. If your bot is trying to capture 0.3% moves, it loses money on every winning trade.
- **Slippage makes it worse.** The price you see is not the price you get, especially on fast moves — which are exactly the moves a "small movements" bot trades.
- **You're competing with firms** running colocated servers and paying near-zero maker fees. At the seconds-to-minutes timescale, they have a structural edge you can't buy.

None of this means don't build it. It means we build it as a **learning and testing system first**, with a pipeline that tells you honestly whether a strategy makes money *after* fees and slippage — before a single real dollar is at risk. Your friend's app may well work; the only way to know if yours does is to measure it ruthlessly. That measurement machinery is most of the project.

**The rule that governs everything below: no real money until a strategy has survived (1) backtesting with fees modeled, and (2) 2–4 weeks of live paper trading.**

---

## 2. What we're building — the six components

Every auto-trading system, from hobby bot to hedge fund, is the same six pieces:

```
                    ┌─────────────────┐
 Exchange ────────▶ │ 1. Market Data   │  live prices via WebSocket,
 (Kraken/Coinbase)  │    Ingestion     │  stored as candles + order book
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ 2. Strategy      │  turns price data into signals:
                    │    Engine        │  BUY / SELL / HOLD
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ 3. Risk Manager  │  the veto layer: position sizing,
                    │                  │  stop-losses, daily loss limits
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
 Exchange ◀──────── │ 4. Execution     │  places orders, tracks fills,
                    │    Engine        │  handles errors and retries
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ 5. Persistence + │  every trade, signal, and P&L
                    │    Dashboard     │  number recorded and visible
                    └─────────────────┘

                    ┌─────────────────┐
                    │ 6. Backtester    │  replays historical data through
                    │    (offline)     │  components 2–3 to test strategies
                    └─────────────────┘
```

Key design decision: **the strategy engine and risk manager don't know whether they're talking to a real exchange, a paper-trading simulator, or a backtest.** Same code, three modes (`backtest` / `paper` / `live`). This is what makes testing trustworthy — you're testing the exact code that will trade real money.

### 2.1 Market data ingestion
Connects to the exchange's WebSocket feed, receives live trades/ticker updates, aggregates them into candles (1m, 5m, 15m), and stores everything in a local database. Also backfills historical candles via REST API so the backtester has data to work with.

### 2.2 Strategy engine
Consumes candles, computes indicators, emits signals. We start with one deliberately simple, understandable strategy — not because it's optimal, but because you need to be able to reason about why it traded:

- **Starter strategy: EMA crossover with an RSI filter.** Buy when the 9-period EMA crosses above the 21-period EMA and RSI < 70 (momentum without buying a blow-off top). Exit on the reverse cross, a stop-loss, or a take-profit target.

Strategies are plugins behind a common interface, so adding strategy #2 later doesn't touch anything else.

### 2.3 Risk manager (the most important component)
Every signal passes through here, and this layer can veto anything. Non-negotiable rules, all configurable:

| Rule | Starting value |
|---|---|
| Max risk per trade | 1% of account |
| Stop-loss on every position | always, no exceptions |
| Max daily loss (then bot halts for the day) | 3% of account |
| Max concurrent positions | 1–2 |
| Max total exposure | 25% of account |
| Kill switch (one command flattens everything and stops) | always available |
| Tradeable pairs | BTC/USD and ETH/USD only at first |

Sticking to BTC and ETH matters: they have the deepest liquidity, so slippage is smallest and your fills are closest to what the backtest assumed.

### 2.4 Execution engine
Talks to the exchange API: places orders, confirms fills, handles partial fills, timeouts, and API errors. In paper mode it simulates fills against the live price feed (including simulated fees and slippage) instead of calling the exchange. Prefers limit orders (lower "maker" fees) where the strategy allows.

### 2.5 Persistence + dashboard
SQLite database recording every candle, signal, order, fill, and a running equity curve. Start with a simple CLI status view plus a Telegram/Discord notification on every trade and daily P&L summary; a web dashboard can come later. The numbers that matter: net P&L after fees, win rate, average win vs. average loss, max drawdown, and — critically — **paper results vs. backtest results for the same period** (if they diverge a lot, the backtest is lying to you).

### 2.6 Backtester
Replays historical candles through the strategy + risk manager and produces the same metrics, **with fees and slippage modeled in** (this is where most hobby backtests cheat and why their authors lose money live). Rule of thumb: assume 0.3% fee + 0.05% slippage per side and see if the strategy still survives.

---

## 3. Key decisions and recommendations

| Decision | Recommendation | Why |
|---|---|---|
| **Exchange** | **Kraken** (alt: Coinbase Advanced Trade) | Both available in Canada with solid APIs and WebSocket feeds. Kraken has lower fees and a good sandbox. Binance is not available to Canadians. |
| **Language** | **Python** | The `ccxt` library gives one unified API across 100+ exchanges (so we're not locked in), `pandas` handles candle math, and nearly every trading tutorial/example you'll find is Python. |
| **Key libraries** | `ccxt`, `pandas`, `pandas-ta` (indicators), SQLite, `pydantic` (config) | Boring, proven, well-documented. |
| **Runs where** | Your machine first; a $5/mo VPS or small cloud box once it runs 24/7 | A bot that only trades when your laptop is open isn't a bot. But that's a Phase 4 problem. |
| **Timeframe** | 5-minute candles to start | Fast enough to feel "live," slow enough that fees don't automatically kill you and you can actually inspect what happened. True second-scale scalping is where the fee math is worst. |
| **UI** | CLI + chat notifications first, web dashboard later | Ship the engine before the chrome. |

### Proposed repo structure

```
crypto-trader/
├── config.yaml              # pairs, risk limits, mode (backtest/paper/live)
├── src/
│   ├── data/                # websocket client, candle builder, backfill
│   ├── strategies/          # base interface + ema_crossover.py
│   ├── risk/                # risk manager
│   ├── execution/           # live broker, paper broker (same interface)
│   ├── backtest/            # replay engine + metrics report
│   ├── storage/             # sqlite models
│   └── main.py              # wires it together per mode
├── notebooks/               # ad-hoc analysis of results
└── tests/
```

---

## 4. Phased roadmap

**Phase 1 — Data pipeline (week 1–2).** Connect to Kraken's WebSocket, build candles, store them, backfill 1–2 years of history, compute indicators, and log the signals the starter strategy *would* generate. No orders of any kind. Success = you can watch live signals scroll by and they match what you see on a chart.

**Phase 2 — Backtester (week 2–3).** Replay the historical data through the strategy with fees and slippage modeled. Produce the metrics report. Expect the first strategy to lose money after fees — that's the system working, not failing. Iterate on parameters honestly (beware of overfitting: if you tune until the backtest looks great, you've usually just memorized the past).

**Phase 3 — Paper trading (weeks 3–7).** Run live against real-time data with the simulated broker for at least 2–4 weeks. Compare paper results to the backtest over the same period. This is the gate: a strategy that can't make money on paper will not make money live.

**Phase 4 — Live with pocket change.** Fund the account with an amount you'd genuinely be fine losing entirely ($100–500). Same code, `mode: live`, tightest risk limits. Run for weeks. The goal here is validating execution (fills, fees, API behavior), not income.

**Phase 5 — Iterate.** More strategies, a web dashboard, more pairs, maybe more capital — each earned by results, not optimism.

---

## 5. Housekeeping that isn't optional

- **API key hygiene.** Create keys with trade permission but **withdrawals disabled** — then a leaked key can lose your trading balance but can't drain it to an attacker's wallet. Keys live in environment variables or a `.env` that's git-ignored, never in code.
- **Taxes (Canada).** Every crypto sale is a taxable event for the CRA, and a bot generates *lots* of them. Frequent trading may be treated as business income rather than capital gains. The database we're building doubles as your tax record; talk to an accountant before Phase 4 gets serious.
- **This is not financial advice**, and no part of this plan assumes the bot will be profitable. The system is designed so you find that out with fake money.

---

## 6. Decisions I need from you

1. **Exchange:** Kraken (my recommendation), Coinbase, or somewhere you already have an account?
2. **Eventual live budget** (Phase 4): what's the number you'd be truly fine losing? This calibrates the risk limits.
3. **Notifications:** Telegram, Discord, or email for trade alerts?
4. **Where it runs:** are you comfortable eventually paying ~$5/month for a small server, or should we design around your own machine?

Answer those and we start Phase 1.
