# CLAUDE.md — Working Rules for This Repository

This file exists so any future session (human or Claude) picks up this
project with the same ground rules it was started under. It summarizes
the governing build spec; if anything here conflicts with a more
detailed doc added later, the more detailed doc wins, but the
*principles* below should not be relaxed without an explicit decision
recorded in this file.

## What this project is

A deterministic, testable research engine that builds higher-timeframe
(4H / Daily / Weekly) volume profiles for a configurable universe of
equities plus ES/NQ/YM/RTY, identifies POC/VAH/VAL/HVN/LVN levels and
timeframe confluence zones, evaluates historical price reactions at
those zones, and produces a reversal score — all backed by a
reproducible backtest with no look-ahead bias.

## What this project is *not* (yet)

- Not a frontend, dashboard, or website.
- Not an options-contract selector (no calls/puts/strikes/greeks).
- Not a machine-learning system. V1 is deterministic and explainable.
- Not a claim that any level "works." The backtester exists to find out.

## Non-negotiable principles

1. **No look-ahead bias.** A historical level, regime state, or score
   may only use information available at or before its own
   activation timestamp. Every phase that touches historical
   calculation needs an explicit test proving future data cannot
   change a past result (see `tests/` "look-ahead" tests once Phase
   16 lands).
2. **Nothing is hard-coded as "true."** POC/VAH/VAL/HVN/LVN/weekly
   levels/confluence/regime-confirmation are all *hypotheses* to be
   measured, not assumptions baked into scoring logic.
3. **All strategy/methodology constants are configurable**, and live
   in a versioned parameters model — never scattered as magic numbers
   in analytics code. Every backtest run records exactly which
   parameter set produced it (reproducibility).
4. **Domain logic stays independent of FastAPI and the database.**
   `volume_profile/`, `levels/`, `regime/`, `scoring/`, `backtesting/`
   should be usable as pure Python against in-memory data in unit
   tests, with persistence mediated by `services/`.
5. **Historical levels are immutable.** New profiles create new level
   rows; nothing overwrites history.
6. **Base score vs. historical score are kept separate**, and the
   historical score must never leak future observations into the
   score of a level being evaluated at time T.
7. **Every aggregate statistic reports its sample size.** No ranking
   "best setups" off a handful of observations.
8. **No language implying certainty** ("guaranteed," "safe," "will
   bounce") anywhere in code comments, docs, or (eventually) API
   responses. This is a measurement tool, not a signal-selling tool.

## Process rules

- Work one phase at a time (see README's Phase list). Do not silently
  jump ahead. After a phase: run tests, review, fix, update docs,
  *then* stop for review before starting the next phase.
- Small, logical commits (`feat: ...`, `test: ...`), not one giant
  commit per phase.
- When a trading-methodology choice is ambiguous, implement a
  reasonable, documented default behind configuration and label it
  `ASSUMPTION` in the docstring/comment — don't silently invent
  strategy rules.

## Current status: V1-lite (scope deliberately narrowed)

The user narrowed scope from the full master spec to: real levels from
real OHLCV data, plus a *basic* liquid-OTM option suggestion — deferring
deep options scoring, historical options backtesting, market regime, and
trade-journal persistence until this core loop is validated. See
README.md's "Current scope vs. full spec" table for the exact delta.

Implemented and tested (28 tests, all against synthetic/fake data —
**no live network access was available to verify the real adapters**):
- `data/providers/tradingview/client.py` — OHLCV via a separately-run
  MrChartist/tradingview-scraper instance (HTTP, not vendored).
- `data/providers/yfinance/options.py` — options chain via `yfinance`
  (delayed, no key; explicitly NOT suitable for historical backtesting).
- `volume_profile/`, `levels/` — binning, allocation, POC/VAH/VAL,
  HVN/LVN, clustering, base score/star rating.
- `options/basic_selector.py` — DTE + liquidity filter, closest to a
  target OTM% (not the full multi-factor score from the master spec).
- `services/reversal_service.py` — orchestrates the above.
- `GET /levels/{symbol}` — public-shaped response.

Next agreed priorities (in the order the user raised them):
1. Trade-journal persistence -- DONE (journal_entries table + GET /journal).
2. Entry confirmation engine -- DONE (src/confirmation/): market
   structure (swing points, BOS/CHoCH), ICT concepts (liquidity
   sweeps, Fair Value Gaps, Order Blocks), and an approximate GEX/OI
   options-positioning check. A REACHED zone only gets an option
   suggestion if enough of these independently agree
   (confirm_min_confirmations, default 2 of 4). This replaced an
   earlier, now-reverted "magnet/vacuum/primary-target" zone-walking
   feature, and the low-volume gap-edge detector (LVN_EDGE) was also
   later removed at the user's request -- both were explicitly tried
   and explicitly dropped. If either concept comes up again, don't
   silently rebuild it without confirming the user wants it back.
3. A separate frontend project -- IN PROGRESS: a single-page app
   (frontend/index.html) is served same-origin by this FastAPI app,
   with the confirmation checklist now surfaced per zone.

Next up (not yet started): an actual auto-trading/execution layer.
Explicitly scoped separately from the confirmation engine above --
wiring real broker order execution to unvalidated signal logic is
how accounts blow up. Recommend: paper-trading simulation first,
broker integration + risk/position sizing + kill-switches after that,
only once the confirmation engine's real-world hit rate is known
(which requires the backtester from the original master spec, still
not built in this v1-lite line of work).

Phase 1 infrastructure (Docker/Postgres/Alembic/config) from the
original scaffolding still applies unchanged underneath this.
