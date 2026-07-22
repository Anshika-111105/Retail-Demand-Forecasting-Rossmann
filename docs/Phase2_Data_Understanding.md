# Phase 2: Data Understanding
## Retail Demand Forecasting & Inventory Optimization Platform

**Project Type:** Retail Analytics / Predictive Analytics Portfolio Project
**Methodology Reference:** CRISP-DM — Phase 2
**Author:** Anshika
**Document Version:** 1.0
**Selected Dataset:** M5 Forecasting – Accuracy (Walmart, Kaggle)

---

## 1. Purpose of This Phase

Phase 2 builds directly on the business objectives defined in Phase 1. Its goal is to collect the raw data, describe its structure, explore it at a high level, and verify its quality — establishing whether the data can actually support the demand forecasting and inventory optimization goals set out earlier, before any modeling work begins.

---

## 2. Dataset Selection Summary

Five candidate datasets were evaluated against project requirements (real retail data, multiple stores/products, long time series, inventory relevance, forecasting suitability, SQL/BI/dashboard compatibility).

| Dataset | Product-Level | Multi-Store | Promotions | Holidays | Prices | Overall Score |
|---|---|---|---|---|---|---|
| **M5 Forecasting (selected)** | ✅ | ✅ | Limited | ✅ | ✅ | **10/10** |
| Corporación Favorita | ✅ | ✅ | ✅ | ✅ | Partial | 9.8/10 |
| Rossmann Store Sales | ❌ | ✅ | ✅ | ✅ | ❌ | 9.0/10 |
| Walmart Recruiting | ❌ | ✅ | Holiday only | ✅ | ❌ | 8.7/10 |
| Store Item Demand (synthetic) | ✅ | ✅ | ❌ | ❌ | ❌ | 7.5/10 |

**Decision:** M5 Forecasting – Accuracy selected as the primary dataset. Corporación Favorita retained as a documented second choice / potential extension dataset for richer promotional analysis.

**Rationale:** M5 offers the strongest combination of product-level daily demand, multi-store/multi-region structure, calendar and pricing data, and compatibility with both classical statistical and modern ML/DL forecasting approaches — directly supporting the RetailX business scenario defined in Phase 1.

---

## 3. Data Source

- **Source:** Kaggle — M5 Forecasting – Accuracy competition (organized by Walmart / University of Nicosia)
- **URL:** https://www.kaggle.com/competitions/m5-forecasting-accuracy
- **License/Access:** Public Kaggle competition dataset, downloadable via Kaggle API or manual download
- **Format:** CSV files (multiple related tables)

---

## 4. Initial Data Collection

The M5 dataset is distributed as a set of relational CSV files rather than a single flat file. Expected core files:

| File | Description |
|---|---|
| `sales_train_validation.csv` / `sales_train_evaluation.csv` | Daily unit sales per product, per store, over the full time span |
| `calendar.csv` | Date-level metadata: day of week, month, year, events, SNAP (promotion-like) flags |
| `sell_prices.csv` | Weekly selling price per product, per store |
| `sample_submission.csv` | Format reference for forecast submission (not needed for this project's dashboard use case, but useful for understanding forecast horizon conventions) |

**Collection method:** Download via Kaggle API (`kaggle competitions download -c m5-forecasting-accuracy`) or manual download into a raw data directory, then load into Pandas/SQL for profiling.

---

## 5. Data Description

### 5.1 Scale
- **Products (SKUs):** 42,840
- **Stores:** 10 Walmart stores
- **States:** California, Texas, Wisconsin
- **Categories:** Food, Household, Hobbies
- **Time span:** 5+ years of daily data
- **Time series count:** 42,000+ individual product–store combinations

### 5.2 Table-Level Schema (Expected)

**`sales_train_*.csv`** — wide format, one row per product-store, one column per day
- `id`, `item_id`, `dept_id`, `cat_id`, `store_id`, `state_id`
- `d_1, d_2, ..., d_n` — daily unit sales columns

**`calendar.csv`** — one row per date
- `date`, `wm_yr_wk`, `weekday`, `wday`, `month`, `year`, `d`
- `event_name_1`, `event_type_1`, `event_name_2`, `event_type_2`
- `snap_CA`, `snap_TX`, `snap_WI` (promotion/assistance-program flags)

**`sell_prices.csv`** — one row per store-item-week
- `store_id`, `item_id`, `wm_yr_wk`, `sell_price`

### 5.3 Key Dimensions for This Project
- **Product hierarchy:** `item_id` → `dept_id` → `cat_id`
- **Location hierarchy:** `store_id` → `state_id`
- **Time hierarchy:** `date` → `wday`/`weekday` → `month` → `year`, plus event/holiday flags

This hierarchy directly maps onto the Phase 1 business questions (store performance, category performance, seasonal/holiday impact, product-level demand).

---

## 6. Data Exploration (Planned Initial Checks)

Before deep EDA (Phase 3 territory), Phase 2 focuses on lightweight structural exploration to confirm fitness for purpose:

- **Shape check:** Row/column counts for each file; confirm `sales_train` wide format needs melting to long format (`date`, `item_id`, `store_id`, `sales`) for time-series work
- **Date range check:** Confirm calendar spans the expected 5+ years and aligns with `d_1...d_n` columns in sales data
- **Join integrity:** Confirm `item_id` + `store_id` keys join cleanly between sales and prices tables; confirm `d` / `wm_yr_wk` keys join cleanly between sales, calendar, and prices
- **Category/store distribution:** Row counts per `cat_id`, `dept_id`, `store_id`, `state_id` to confirm balanced coverage
- **Sales value range:** Min/max/zero-inflation check on daily unit sales (retail time series are typically sparse/intermittent, especially at SKU level — important for later model choice)
- **Price coverage:** Confirm `sell_price` is not populated for all product-weeks (products not yet launched or discontinued will have gaps — expected, not an error)
- **Event/holiday coverage:** Count and list distinct `event_name_1/2` values to understand seasonal markers available for feature engineering

---

## 7. Data Quality Verification

| Quality Dimension | Planned Check | Why It Matters |
|---|---|---|
| **Completeness** | Missing values in calendar events, prices, sales | Missing prices are expected (pre-launch/discontinued items); missing sales should not exist in a well-formed wide table |
| **Consistency** | Matching keys (`item_id`, `store_id`, `d`, `wm_yr_wk`) across tables | Broken joins would silently corrupt merged feature tables |
| **Validity** | Non-negative unit sales; valid date ranges; valid category/store codes | Invalid values would distort demand forecasts and KPIs |
| **Uniqueness** | No duplicate `id` rows in sales table | Duplicates would double-count demand |
| **Sparsity/Intermittency** | Proportion of zero-sales days per SKU | Determines whether intermittent-demand-aware models (e.g., Croston's method) may be needed alongside Prophet/XGBoost |
| **Timeliness/Coverage** | Confirm no unexplained gaps in the daily date sequence | Gaps would break lag/rolling-window feature engineering |

Findings from this verification step will be documented in a short **Data Quality Report** at the start of Phase 3 (Data Preparation), including any remediation plan (imputation, exclusion, or flagging of affected SKUs/stores).

---

## 8. Relation Back to Business Objectives (Phase 1 Traceability)

| Phase 1 Business Objective | Supported By |
|---|---|
| Sales performance (revenue trends, top stores/regions) | `sales_train` × `sell_prices` × `store_id`/`state_id` |
| Product performance (best/worst sellers, declining demand) | `sales_train` × `item_id`/`dept_id`/`cat_id` |
| Inventory management (stockout/overstock risk, reorder signals) | Derived from sales velocity + (no native inventory table — noted as a gap, see Section 9) |
| Demand forecasting (daily/monthly, holiday impact) | `sales_train` × `calendar` (events, SNAP flags) |
| Executive decision support | Aggregated views across all of the above |

---

## 9. Known Gaps & Limitations

- **No native inventory/stock-level table.** M5 provides sales (demand realized), not stock-on-hand. Inventory KPIs (stockout rate, overstock rate, days of inventory outstanding) will need to be **simulated or approximated** — e.g., by defining synthetic starting inventory and reorder policies on top of forecasted demand — and this assumption must be clearly documented wherever those KPIs appear in the dashboard.
- **Limited promotion granularity.** SNAP flags are a partial proxy for promotional effect, not a full promotions calendar (unlike Rossmann or Favorita).
- **Price is weekly, not daily.** Price-elasticity features will be at weekly granularity even though sales are daily.

These gaps do not block the project but should be stated explicitly in the final platform documentation so forecasts and inventory KPIs are presented with the correct caveats.

---

## 10. Next Steps (Phase 3 Preview)

Phase 3 — **Data Preparation** — will involve:
- Melting `sales_train` from wide to long format
- Merging sales, calendar, and price tables into a unified analytical table
- Handling missing prices and zero-inflated sales
- Engineering initial time, event, and lag-based features
- Defining the simulated inventory logic needed to support Phase 1's inventory KPIs
