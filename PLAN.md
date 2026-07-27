# Systematic ETF Trading App: Project Plan

A plan for building a personal app that analyzes the stock market, generates trade signals on liquid ETFs, and executes trades automatically through a brokerage API. Built to run alongside a full-time job, prove itself with fake money first, then graduate to a small real account ($500) and earn more capital only through results.

This replaces the earlier crypto-focused plan. The architecture survived the switch almost untouched; the market, broker, strategy, and tax sections are new.

---

## 1. Why equities, and what "success" means here

Short-term trading is roughly zero-sum: for you to win, someone must lose, and you pay costs for every attempt. Equities offer something crypto and forex don't: a built-in positive expected return, because you're harvesting real economic growth, earnings, and dividends. A systematic equity approach starts with a tailwind. The system's job is discipline, risk control, and modest enhancement of returns the market already hands you, not out-trading professionals.

Two honest framings to hold onto:

- **The benchmark is buy-and-hold, not zero.** Every report this system produces compares the strategy against simply holding SPY (and against your existing ETF mix) over the same period. A bot that returns 8% while SPY returns 20% lost you 12%.
- **Your last 18 months of ETF gains happened in a rising market.** That's a genuinely good sign about your temperament and process, but don't extrapolate it as a baseline. The main documented value of the trend-following approach below is cutting drawdowns in bad markets, not beating a bull market. Expect it to roughly match buy-and-hold in good times and to earn its keep by losing much less in bad ones.

**One hard wall, agreed now: this project never touches the 401(k) or IRAs.** The retirement strategy is working; it stays exactly as it is. This system runs in a separate taxable brokerage account, capped at $500 until it earns more.

---

## 2. What we're building — the six components

```
                    ┌─────────────────┐
 Broker/Data API ─▶ │ 1. Market Data   │  daily (and intraday) bars for a
 (Alpaca)           │    Ingestion     │  small universe of liquid ETFs
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ 2. Strategy      │  turns price data into signals:
                    │    Engine        │  target portfolio / BUY / SELL
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ 3. Risk Manager  │  the veto layer: position sizing,
                    │                  │  exposure caps, loss limits
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
 Broker API ◀────── │ 4. Execution     │  places orders, tracks fills,
                    │    Engine        │  handles errors and retries
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
                    │ 5. Persistence + │  every signal, order, fill, and
                    │    Dashboard     │  P&L number recorded and visible
                    └─────────────────┘

                    ┌─────────────────┐
                    │ 6. Backtester    │  replays decades of history through
                    │    (offline)     │  components 2–3 to test strategies
                    └─────────────────┘
```

Core design decision, unchanged: **the strategy engine and risk manager don't know whether they're talking to a real broker, a paper account, or a backtest.** Same code, three modes (`backtest` / `paper` / `live`). You test the exact code that will trade real money.

A big practical win of the equity switch: the daily rhythm. The bot pulls closing data after 4pm ET, decides, and queues orders for the next session. No 3am decisions, nothing to babysit during your workday, and every trade is inspectable before and after it happens.

### 2.1 Market data ingestion
Pulls daily bars for the ETF universe from Alpaca's free data feed, backfills 20+ years of history for backtesting (deep, clean, free history is a luxury crypto never had), stores everything in SQLite, and computes indicators.

### 2.2 Strategy engine
Consumes bars, emits target positions. Strategies are plugins behind a common interface. We start with the two approaches that have the strongest evidence base in the retail-accessible literature, in order:

- **Starter strategy A: trend filter.** Hold an index ETF (e.g., SPY or QQQ) when it closes above its 200-day moving average; move to cash (or a short-term treasury ETF) when it closes below. Checked once daily. This is deliberately almost boring: it's well studied, its main effect is sidestepping deep bear markets, and you can verify every decision by eye.
- **Starter strategy B: momentum rotation.** Each month, rank a small basket of 5–8 liquid ETFs (US large cap, US small cap, international, bonds, gold) by trailing 3–12 month returns and hold the top 1–3, with the same trend filter as a safety valve. This is the "dual momentum" family, the most-documented systematic retail approach in existence.

Both trade infrequently (a few signals per month at most), which keeps costs, taxes, and operational risk low, and fits the evidence: for retail systematic equity investing, less trading is nearly always better.

### 2.3 Risk manager (the most important component)
Every signal passes through here, and this layer can veto anything:

| Rule | Starting value |
|---|---|
| Max position in any single ETF | 40% of account (rotation holds few names by design) |
| Universe | Liquid, high-volume ETFs only; no single stocks, no leverage, no inverse ETFs |
| Max daily loss (then bot halts and alerts) | 3% of account |
| Max orders per day | hard cap, e.g. 10 (runaway-bot protection) |
| Price sanity band | refuse any order priced far from the last close |
| Kill switch (flatten everything, stop) | always available |
| Account never topped up after losses | the $500 is the whole experiment |

### 2.4 Execution engine
Talks to the Alpaca API: submits orders (market-on-open or limit), confirms fills, handles partial fills and API errors, and reconciles positions against the broker's records every run. In paper mode it uses Alpaca's built-in paper trading environment, which simulates fills server-side against real market data — a large piece of Phase 3 we don't have to build. Fractional shares make a $500 account genuinely workable: the bot can hold correct position sizes in ETFs trading at $500+ per share.

### 2.5 Persistence + dashboard
SQLite recording every bar, signal, order, fill, and a running equity curve. CLI status view plus a notification (channel TBD) on every trade and a weekly summary. Headline metrics: net P&L, max drawdown, and the strategy vs. SPY vs. your existing ETF mix over the same period. Also doubles as the tax record.

### 2.6 Backtester
Replays history through the strategy and risk manager with realistic costs modeled: zero commission but real bid/ask spread (a few basis points on liquid ETFs) and overnight-gap behavior. Because ETF history runs back decades, we can test across 2000–2002, 2008, 2020, and 2022 — bear markets are exactly where these strategies are supposed to earn their keep, and we get to check.

---

## 3. Key decisions and recommendations

| Decision | Recommendation | Why |
|---|---|---|
| **Broker** | **Alpaca** (alt: Interactive Brokers) | Built API-first for exactly this use case: commission-free, fractional shares, free market data, and a first-class paper trading environment. IBKR is the fallback if you want one broker for everything. |
| **Language** | **Python** | `pandas` for bar math, `alpaca-py` official SDK, and virtually all systematic-investing literature and examples are in Python. |
| **Key libraries** | `alpaca-py`, `pandas`, `pandas-ta`, SQLite, `pydantic` | Boring, proven, well-documented. |
| **Timeframe** | Daily bars; decisions after the close | Fits a full-time job, minimizes costs and taxes, and matches where the retail evidence actually is. |
| **Universe** | 5–8 liquid ETFs, seeded from the ones you already hold | You can sanity-check every signal against instruments you understand. |
| **Runs where** | Your machine first; a ~$5/mo VPS or a scheduled cloud job later | A daily-bar bot only needs to wake up once or twice a day, so even a free-tier scheduled job can work. |
| **Account type** | New, separate **taxable** brokerage account | Never the 401(k)/IRA. Clean separation, clean records, clean experiment. |

### Proposed repo structure

```
etf-trader/
├── config.yaml              # universe, risk limits, mode (backtest/paper/live)
├── src/
│   ├── data/                # alpaca client, bar store, history backfill
│   ├── strategies/          # base interface + trend_filter.py, momentum_rotation.py
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

**Phase 1 — Data pipeline (week 1–2).** Connect to Alpaca, backfill 20+ years of daily bars for the universe, compute indicators, and log the signals both starter strategies *would* generate. No orders. Success = signals scroll by and match what you see on any charting site.

**Phase 2 — Backtester (week 2–4).** Replay history through both strategies with spread costs modeled. Tune only on older data (e.g., through 2015) and validate on data the tuning never saw (2016+). Report returns, max drawdown, and behavior in each bear market vs. buy-and-hold. Expect the honest result to be "similar returns, smaller drawdowns" rather than "beats the market" — that's a pass, not a fail.

**Phase 3 — Paper trading (weeks 4–8).** Run live against Alpaca's paper environment for at least 4 weeks. Compare results to the backtest over the same period and to SPY. Gate: paper behavior must be consistent with the backtest. (Note: these strategies trade a few times a month, so paper trading validates *plumbing and consistency* more than long-run returns — the statistical proof lives in the decades-long backtest.)

**Phase 4 — Live with $500.** Same code, `mode: live`, in the new taxable account funded with $500 — an amount already agreed as fine to lose entirely, never topped up after a drawdown. The goal is validating real execution (fills, fractional shares, API behavior in anger), not income: even a great year on $500 is under $100. Run for at least 3 months.

**Phase 5 — Earn scale.** More capital, more strategies, a web dashboard — each earned by results measured against the gates below, not by optimism.

---

## 5. Success criteria, benchmarks, and kill gates

As a get-rich project, expected value is still negative — most retail systems don't beat the market. As a structured experiment, the odds are meaningfully better than the crypto version, because the underlying asset class goes up over time and the strategy families chosen have decades of documented evidence. Realistic success: matching the market's return with meaningfully smaller drawdowns, proven over time, with the discipline automated.

| Gate | Criteria to pass | If it fails |
|---|---|---|
| End of Phase 2 (backtest) | Beats or roughly matches buy-and-hold on out-of-sample data with clearly smaller max drawdown | Iterate, max 2–3 serious strategy attempts, then reassess |
| End of Phase 3 (paper) | Paper behavior consistent with backtest; no plumbing failures | Do not go live. Fix and repeat |
| 3+ months of Phase 4 (live) | Live fills and P&L consistent with paper; no operational incidents | Halt and diagnose before any thought of more capital |
| Scaling decision | 6–12 months live, results in line with backtest expectations | Stay at $500 or stop; wanting to override a failed gate is the signal to stop |

**Hard budgets:** live capital capped at $500 until the scaling gate passes. Time budget roughly 6–10 weeks of evenings to reach the Phase 3 gate. The dignified fallback if strategy work disappoints: the identical system runs a scheduled contribute-and-rebalance portfolio — automation of exactly what's already working in your retirement accounts, which is worth having regardless.

---

## 6. Traps we're designing against

- **Overfitting.** The silent killer of every hobby quant project. Guardrails: tune on old data and judge on unseen data, few tunable parameters, deep suspicion of any backtest that looks amazing.
- **Regime dependence.** A strategy tuned on 2016–2021 says nothing about 2008. The backtest must span multiple bear markets, and reports must show per-regime behavior.
- **Overnight gaps.** Stocks close at 4pm and reopen elsewhere. Stop-losses become "exit at next open," which can be worse than the stop price. The backtester models gap-through explicitly; position sizes assume it.
- **Wash sales.** In a US taxable account, selling at a loss and rebuying the same (or substantially identical) ETF within 30 days disallows the loss for tax purposes. An active bot can generate these accidentally. The risk manager tracks recent realized losses per symbol and either blocks the rebuy or flags it; the trade log doubles as the paper trail for tax filing.
- **Pattern day trader rule.** A margin account under $25k gets frozen for 4+ day trades in 5 business days. Our daily-bar, hold-for-weeks style shouldn't come near it, but the risk manager counts same-day round trips and blocks the fourth, as a belt-and-suspenders guard.
- **Runaway-bot failure modes.** Bugs, not markets, cause the most spectacular retail losses. Safeguards: order-per-day cap, price sanity bands, idempotent order logic, position reconciliation against the broker every run, and fail-safe behavior (on any error or ambiguity: stop opening positions, alert, wait for a human).
- **Human override.** Intervening mid-drawdown or sizing up after a hot streak invalidates the experiment. Config changes happen deliberately, between sessions.
- **Paid shortcuts.** No courses, signal services, or "profitable bot" subscriptions. If a strategy is being sold, the seller's profit is the subscription.

---

## 7. Housekeeping that isn't optional

- **API key hygiene.** Alpaca keys live in environment variables or a git-ignored `.env`, never in code. Trading permission only; Alpaca accounts support regenerating keys instantly if anything leaks.
- **Taxes (US).** Positions held under a year generate short-term capital gains, taxed as ordinary income; the strategies here will produce mostly short-term gains. Every sale is a taxable event and the database is your record. At $500 the dollar amounts are trivial, but the record-keeping habits and the wash-sale guard need to exist before the account is ever bigger.
- **Retirement accounts stay untouched.** Worth restating as policy: no API keys for, no orders to, and no strategy decisions about the 401(k) or IRAs. If this system proves itself over years, deciding whether its *approach* deserves retirement money is a separate, human decision made outside this codebase.
- **Personal tool vs. product: a legal wall.** Running this on your own money requires no license. Marketing an app that trades (or recommends trades) for other people makes the operator an investment adviser under the Investment Advisers Act and state equivalents: SEC/state RIA registration, compliance program, fiduciary duties. Performance marketing of investment products is separately regulated (SEC Marketing Rule), and backtested-results claims are its most dangerous territory. Policy for this project: strictly personal, in a personal brokerage account in your own name (not a corporate account), with no company involvement, through at least a year of live results. If results ever justify productizing, the first step is a securities attorney, before any customer or any marketing. The documented track record this system produces is, conveniently, the one asset a future product would need most.

- **This is not financial advice**, and the plan assumes nothing about profitability. The system is designed so you find out with fake money and then with $500.

---

## 8. Decisions I need from you

1. **Broker:** Alpaca (my recommendation) or Interactive Brokers?
2. **ETF universe:** which ETFs do you currently hold? We'll seed the basket from those plus enough diversity for the rotation strategy (typically: US large cap, US small cap, international developed, bonds, gold).
3. **Notifications:** Telegram, Discord, email, or text?
4. **Where it runs:** your machine to start is fine; comfortable with a ~$5/month server (or a free scheduled cloud job) once it's live?

Answer those and we start Phase 1.
