# Market Reversal Engine (V1-lite)

> **Scope note:** this repo currently implements a narrowed "V1-lite"
> slice of the full master spec: real levels from real OHLCV data, plus
> a *basic* liquid-OTM option suggestion — not yet the full options
> scoring engine, historical options backtesting, or trade journal
> persistence described in the original master prompt. Those are the
> agreed next steps once this core loop (levels + option pick) is
> validated. See "Current scope vs. full spec" below.

A deterministic, testable research engine investigating whether
higher-timeframe (4H / Daily / Weekly) volume-profile levels and
timeframe-confluence zones produce statistically meaningful price
reversals — and whether broader market direction (ES/NQ/YM/RTY)
improves or worsens the odds.

**This is a research tool. It does not claim any level is a reliable
trading signal.** The backtesting engine exists specifically to test
that hypothesis objectively, including the possibility that it's
false for some or all level types.

Not included in V1 (by design): a frontend/website, options-contract
selection (strikes/greeks/expirations), or machine learning. See
`CLAUDE.md` for the full list of governing principles.

---

## Status: V1-lite core loop working

What exists right now and is covered by tests:

- **`src/data/providers/tradingview/client.py`** — HTTP adapter for
  [MrChartist/tradingview-scraper](https://github.com/MrChartist/tradingview-scraper),
  run as its own separate service, for real OHLCV bars.
- **`src/data/providers/yfinance/options.py`** — options chain adapter
  using `yfinance` (free, delayed, no API key) for a basic liquid
  contract suggestion.
- **`src/volume_profile/`** — binning, candle-range volume allocation,
  POC/VAH/VAL (70% value area, configurable), HVN/LVN local-extrema
  detection.
- **`src/levels/`** — level generation per timeframe (4H/1D/1W) and
  clustering into confluence zones with a deterministic, unvalidated
  base score / star rating.
- **`src/options/basic_selector.py`** — filters an option chain by
  DTE/liquidity, then picks the contract closest to a target
  OTM% — a simple heuristic, not the full multi-factor scoring engine
  from the master spec.
- **`src/services/reversal_service.py`** — orchestrates all of the
  above into one `analyze_symbol()` call.
- **`GET /levels/{symbol}`** — the public-shaped endpoint: current
  price, best confluence zone + star rating, status
  (`WAITING`/`NEAR`/`REACHED`), and (if reached) a basic option pick.

28 tests pass, all against synthetic/fake data — **no live network
calls have been verified from this environment** (this sandbox can't
reach TradingView's websocket feed or Yahoo Finance; see Known
Limitations). The adapters follow each service's documented interface,
but you should smoke-test them for real once you run this outside the
sandbox.

Not yet built: trade-journal persistence, deeper options
scoring/IV-rank/expected-move, historical options backtesting, market
regime (ES/NQ/YM/RTY), and the frontend. See "Current scope vs. full
spec" below.

### Current scope vs. full spec

| Area | Master spec (full) | This repo (v1-lite) |
|---|---|---|
| OHLCV data | Licensed vendor + TradingView reference adapter | TradingView-scraper only (dev/personal use) |
| Options data | Licensed historical option-chain provider | `yfinance` live/delayed chain only — **no historical option backtesting possible with this data source** |
| Option selection | Multi-factor score (delta/IV-rank/expected-move/spread/...) | Basic: DTE + liquidity filter, closest-to-target-OTM% |
| Levels/clustering | Same methodology, DB-persisted, immutable history | Same methodology, computed on-demand, **not persisted** |
| Market regime (ES/NQ/YM/RTY) | Implemented | Not implemented yet |
| Trade journal | Full schema + P/L + win/loss tracking | Not implemented yet — flagged as the next priority |
| Backtesting | Full chronological, no-look-ahead engine | Not implemented yet |
| Frontend | Not in V1 at all | Deferred — planned as a separate "futuristic/3D" build once this loop is validated |

---

## Architecture

Modular monolith, not microservices. Domain/analytics code is kept
independent of the web framework and the database so it can be unit
tested with plain in-memory data:

```
src/
  api/            FastAPI app + routers (thin — HTTP only, Phase 14+)
  config/         Settings (infra) — strategy parameters land here too, later
  database/       SQLAlchemy engine/session/declarative base
  models/         SQLAlchemy ORM models (Phase 5+)
  schemas/        Pydantic request/response schemas (Phase 14+)
  data/           MarketDataProvider abstraction + CSV provider (Phase 2)
  volume_profile/ Binning, volume allocation, POC/VAH/VAL, HVN/LVN (Phase 4-6)
  levels/         Level generation + clustering (Phase 7-8)
  regime/         ES/NQ/YM/RTY regime + composite regime (Phase 9)
  scoring/        Base score / historical score (Phase 13)
  backtesting/    Interaction detection, MFE/MAE, backtest engine (Phase 10-12)
  services/       Orchestration layer that wires domain code to persistence
  utils/          Shared, dependency-free helpers
```

Data flow (once fully built): CSV/vendor bars → normalization/validation
→ volume profile per timeframe → level extraction → clustering →
regime evaluation → interaction detection → outcome measurement →
backtest aggregation → scoring → exposed via the API/CLI. Each stage is
a pure, independently testable module; `services/` is the only layer
allowed to talk to the database.

---

## Setup

### Prerequisites

- Docker + Docker Compose (recommended path)
- Or: Python 3.12+ and a local PostgreSQL 16 instance

### Option A — Docker Compose (recommended)

```bash
cp .env.example .env
docker compose up --build
```

This starts:
- `db`: Postgres 16 on `localhost:5432` (credentials from `.env`) — not
  used by `/levels` yet, but ready for the trade-journal work next
- `app`: FastAPI app on `localhost:8000` (auto-reload)

Then check:

```bash
curl http://localhost:8000/health
```

### Running the data providers `/levels/{symbol}` needs

`/levels/{symbol}` needs two things reachable at request time:

1. **A running `tradingview-scraper` instance**, as its own separate
   process (it is not vendored into this repo):
   ```bash
   git clone https://github.com/MrChartist/tradingview-scraper.git
   cd tradingview-scraper
   pip install -r requirements.txt -r api/requirements.txt
   uvicorn api.main:app --port 8100   # a DIFFERENT port than this app's 8000
   ```
   Then set `TRADINGVIEW_SCRAPER_BASE_URL=http://localhost:8100` in
   `.env` (already the default).
2. **`yfinance`** — no separate service needed, just installed as a
   dependency (already in `pyproject.toml`); it calls Yahoo Finance
   directly over the network.

```bash
curl http://localhost:8000/levels/NVDA
```

Once domain models exist (Phase 5+), run migrations inside the app
container:

```bash
docker compose exec app alembic upgrade head
```

### Option B — Local Python environment

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # edit DATABASE_URL to point at your local Postgres
alembic upgrade head    # no-op until Phase 5+ adds tables
uvicorn src.api.main:app --reload
```

### Running tests

Tests never require a live Postgres instance — they force
`APP_ENV=test` and an in-memory SQLite database (see
`tests/conftest.py`):

```bash
pytest
```

---

## Environment variables

See `.env.example` for the full list. Key ones:

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` \| `test` \| `production` |
| `DATABASE_URL` | SQLAlchemy connection string |
| `LOG_LEVEL` | Python logging level |
| `API_HOST` / `API_PORT` | Uvicorn bind address |

Strategy/methodology parameters (value area %, bin size, HVN/LVN
thresholds, cluster tolerance, interaction tolerance, target
percentages, invalidation rule, minimum sample size, regime weights)
are **not** environment variables — they belong to a versioned
`strategy_parameters` model (Phase 13) so every backtest run can record
exactly which parameter set produced it.

---

## Data format *(Phase 2 — not yet implemented)*

Will document: expected OHLCV CSV schema, required columns
(`symbol, timestamp, open, high, low, close, volume[, timeframe]`),
timezone handling (all internal timestamps normalized to UTC), and
session/calendar assumptions per instrument.

## Volume-profile methodology *(Phase 4-6 — not yet implemented)*

Will document: the default price-binning method and how it's
configured, the volume-allocation method (candle-range distribution),
value-area calculation and default percentage (70%, configurable,
not assumed optimal), and the HVN/LVN local-extrema detection
methodology with its configurable window/prominence parameters.

## Level & clustering methodology *(Phase 7-8 — not yet implemented)*

Will document: level immutability and activation-timestamp rules
(no look-ahead), and the deterministic clustering distance used to
group nearby levels into confluence zones.

## Market-regime methodology *(Phase 9 — not yet implemented)*

Will document: per-instrument (ES/NQ/YM/RTY) directional-state rules
and the composite regime's weighting methodology and default weights.

## Reversal definition & backtesting methodology *(Phase 10-12 — not yet implemented)*

Will document: touch/interaction detection and cooldown grouping,
approach-direction classification, target/invalidation definitions,
MFE/MAE measurement, and the in-sample/out-of-sample split used for
backtest evaluation.

---

## Known limitations (current)

- **No live network calls have been run from the environment that built
  this code** — however, the correct `timeframe` values (`4h`, `1d`,
  `1w`, lowercase) and response shape
  (`{"status": "success", "data": [...], "total": N}`) for
  `tradingview-scraper` **have since been verified against a live
  instance** (2026-09-07) and the adapter was fixed to match. The
  `yfinance` options adapter and futures/index (ES/NQ/YM/RTY) exchange
  prefixes are still unverified — test those before relying on them.
- **`yfinance` options data is delayed and best-effort** — fine for "a
  reasonably liquid contract to look at right now," not sufficient for
  historical option backtesting (no point-in-time chain snapshots).
  Anything that later needs a historical option chain must mark itself
  `OPTIONS_BACKTEST_STATUS = UNAVAILABLE` rather than substituting
  today's chain for a historical one.
- **`tradingview-scraper` is a scraper, not a licensed feed** — it can
  break silently if TradingView changes something, and can get
  rate-limited/blocked under heavy polling. Fine for personal
  research use; the provider abstraction means a licensed vendor can
  replace it later without touching `volume_profile`/`levels`/etc.
- **Nothing is persisted yet** — `/levels/{symbol}` computes everything
  on-demand from freshly-fetched bars. The database exists (Postgres +
  Alembic wired) but no domain tables/migrations exist yet; trade
  journaling is the next priority once this loop is confirmed to look
  right.
- No market regime (ES/NQ/YM/RTY), no historical backtesting, no
  authentication on the API — all out of scope for this increment (see
  "Current scope vs. full spec" above).
- This sandbox environment has no Docker daemon available for
  verification; the Docker/Postgres config has been reviewed and
  written to spec but should be smoke-tested with `docker compose up`
  in a real Docker environment before relying on it. The Python app,
  config, SQLAlchemy engine, and Alembic pipeline have been verified
  directly (see Testing).

---

## Development phases

1. **Scaffolding, config, Docker, Postgres, SQLAlchemy, Alembic, tests** ← current
2. Market-data abstraction, CSV provider, OHLCV normalization, validation
3. Timeframe/session engine
4. Volume-profile engine
5. POC / VAH / VAL
6. HVN / LVN
7. Historical level generation
8. Level clustering
9. ES/NQ/YM/RTY regime engine
10. Level interaction detection
11. MFE/MAE/reversal measurement
12. Backtesting engine
13. Scoring engine
14. FastAPI research endpoints
15. Documentation and final test suite

Each phase requires review and approval before the next begins.

---

## Disclaimer

This project measures historical behavior of price around
volume-profile levels. It does not predict future price movement, and
no output should be described or treated as "guaranteed," "safe," or
"high probability" without qualifying it with the actual measured
sample size and methodology behind it.
