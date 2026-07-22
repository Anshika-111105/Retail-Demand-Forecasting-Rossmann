# Phase 4: Feature Engineering Strategy
## Retail Demand Forecasting & Inventory Optimization Platform

**Methodology Reference:** CRISP-DM — Phase 4
**Input:** `data/processed/rossmann_train_store_merged.parquet` (and the matching `test` parquet)
**Output:** a modeling-ready feature table, produced by `src/feature_engineering/`
**Document Version:** 1.0

---

## 1. Objective

Turn the merged, validated Rossmann dataset (Phase 3) into a feature table that captures the
three forces that actually move daily store demand: **calendar rhythm**, **promotional/holiday
context**, and **historical momentum** — while respecting the constraint that every feature must
be computable at inference time (i.e. never leak `Sales`/`Customers` from the future, and never
use `Customers` directly since it doesn't exist in `test.csv`).

## 2. Feature Groups

### 2.1 Calendar Features (from `Date`)

| Feature | Definition | Business Value |
|---|---|---|
| `day_of_week` | Already present (`DayOfWeek`) | Weekly seasonality — weekends/Mondays differ sharply from mid-week |
| `month` | `Date.dt.month` | Captures monthly seasonality (e.g. back-to-school, pre-holiday buildup) |
| `week_of_year` | `Date.dt.isocalendar().week` | Finer-grained seasonality than month; aligns with `Promo2SinceWeek` |
| `quarter` | `Date.dt.quarter` | Quarterly business reporting alignment |
| `year` | `Date.dt.year` | Captures year-over-year growth/decline trend |
| `is_weekend` | `day_of_week in {6, 7}` | Distinct staffing/replenishment pattern; weekends often see different basket sizes |
| `is_month_start` | `Date.dt.is_month_start` | Payday-adjacent demand spikes are common in retail at month boundaries |
| `is_month_end` | `Date.dt.is_month_end` | Same rationale — month-end budget effects on customer spending |
| `day_of_month` | `Date.dt.day` | Supports finer within-month pattern detection than start/end flags alone |

### 2.2 Promotion & Holiday Indicators

| Feature | Definition | Business Value |
|---|---|---|
| `promo_active` | `Promo` (already present) | Direct short-term demand-lift signal |
| `is_state_holiday` | `StateHoliday != "0"` | Collapses the 4-way category into a binary "is today unusual" flag for quick filtering |
| `state_holiday_type` | `StateHoliday` (a/b/c) | Preserves *which kind* of holiday — public, Easter, Christmas often have different demand shapes |
| `school_holiday_active` | `SchoolHoliday` (already present) | Family-purchase-pattern signal, distinct from state holidays |
| `promo2_active_today` | 1 if `Promo2 == 1` **and** the store's `PromoInterval` contains the current month **and** the date is on/after `Promo2SinceWeek`/`Promo2SinceYear` | Captures the *recurring* seasonal campaign correctly — `Promo2 == 1` alone only says the store is enrolled, not that a campaign is running right now |
| `promo_duration_days` | Consecutive days since the current `Promo` streak began, per store | Distinguishes day 1 of a promo (highest novelty effect) from a sustained promo run (effect often decays) |

### 2.3 Competition Features

| Feature | Definition | Business Value |
|---|---|---|
| `has_competition` | `CompetitionDistance.notna()` | Explicit flag instead of relying on raw NaN, which some models mishandle inconsistently |
| `competition_distance` | `CompetitionDistance`, missing left as a large sentinel (e.g. max observed distance) *after* `has_competition` already captures the "no competitor" case | Closer competitors are expected to suppress baseline demand |
| `competition_open_since_days` | Days between `CompetitionOpenSinceYear/Month` and current `Date` (0 or NaN-safe if competitor not yet open or unknown) | Demand erosion typically grows for a period after a competitor opens, then stabilizes — this feature lets models learn that curve |

### 2.4 Lag, Rolling, and Expanding Features (per `Store`, computed only on `Open == 1` history to avoid diluting signal with structural zeros)

| Feature | Definition | Business Value |
|---|---|---|
| `sales_lag_7` | `Sales` value 7 days prior, same store | Same-weekday-last-week is normally the strongest single predictor of daily retail demand |
| `sales_lag_14`, `sales_lag_28` | 14- and 28-day lags | Captures bi-weekly/monthly demand cycles and promotion-interval echoes |
| `sales_rolling_mean_7` / `_30` | Rolling mean of `Sales` over the trailing 7 / 30 open days | Smooths day-to-day noise into a stable recent-baseline estimate for reorder-point calculations |
| `sales_rolling_std_7` / `_30` | Rolling standard deviation over the same windows | Captures demand *volatility* — a store with high variance needs a larger safety-stock buffer than one with the same mean but low variance |
| `sales_expanding_mean` | Expanding (cumulative) mean of `Sales` up to the current date | A long-run store baseline, useful for new-ish stores where a 30-day window is still noisy |
| `customers_rolling_mean_7` | Rolling mean of `Customers` over the trailing 7 open days (**train-time only** — used to build a lookup table of historical average traffic by `Store`/`DayOfWeek`, never as a raw per-row feature, since `Customers` does not exist in `test.csv`) | Approximates expected foot traffic without leaking the unavailable raw column into inference |
| `sales_trend_7_30` | `sales_rolling_mean_7 / sales_rolling_mean_30` | A simple momentum ratio — values above 1 indicate an accelerating short-term trend versus the monthly baseline, useful as an early stockout-risk signal |

## 3. Leakage Safeguards

- All lag/rolling/expanding features are computed strictly on **past** data relative to each row
  (`shift(1)` before any rolling window) — no feature may include the current day's own `Sales`.
- `Customers` is never used as a raw per-row feature; only pre-aggregated historical
  averages (computed from training data only) may be joined in as store/day-of-week lookups.
- Rolling/lag features are computed **per store**, grouped, to avoid one store's history leaking
  into another's window.
- Feature computation for `test.csv` reuses only lag/rolling state carried forward from the end
  of the training period — never information from within the test window itself.

## 4. Implementation Notes

- Feature-building code lives in `src/feature_engineering/`, structured as small, composable
  functions (one per feature group above) so each can be unit-tested independently
  (`tests/unit/`).
- All date-derived and lag/rolling features are computed once and persisted to
  `data/processed/` as a single feature table shared by SQL exploration, the dashboard, and all
  three forecasting models — avoiding divergent feature logic between the ML and BI layers.
