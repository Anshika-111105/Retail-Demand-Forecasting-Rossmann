# Phase 7: Machine Learning Strategy
## Retail Demand Forecasting & Inventory Optimization Platform

**Methodology Reference:** CRISP-DM — Phase 7 (Modeling & Evaluation)
**Models compared:** Prophet, XGBoost, LightGBM
**Document Version:** 1.0

---

## 1. Objective

Forecast daily `Sales` per store over the Kaggle test horizon (~6 weeks), then recommend a
production model based on business fit — not raw accuracy alone.

## 2. Why These Three Models

| Model | Why It's a Good Fit for Rossmann |
|---|---|
| **Prophet** | Purpose-built for daily business time series with strong weekly/yearly seasonality and holiday effects — matches Rossmann's `DayOfWeek`/`StateHoliday`/`SchoolHoliday` structure almost directly via its built-in seasonality and holiday-regressor support. Interpretable trend/seasonality decomposition is valuable for explaining forecasts to non-technical stakeholders. |
| **XGBoost** | Gradient-boosted trees handle the mix of categorical (`StoreType`, `Assortment`, `StateHoliday`) and numeric/engineered features (lags, rolling stats, competition distance) well, and can learn store-to-store interaction effects a per-store Prophet model cannot see. Well-suited to tabular data at this scale on local hardware. |
| **LightGBM** | Same modeling family as XGBoost but with histogram-based splitting and leaf-wise growth — materially faster training and lower memory use on ~1M rows, which matters directly on the project's 8 GB RAM constraint. Included as the memory/speed-efficient alternative to XGBoost, not a redundant duplicate. |

## 3. Feature Engineering Required Per Model

- **Prophet:** trained per store (or per `StoreType` cluster to reduce the number of models);
  requires only `ds` (date) and `y` (sales) columns plus regressor columns for `Promo`,
  `SchoolHoliday`, and a custom holiday dataframe built from `StateHoliday`. Lag/rolling features
  are unnecessary — Prophet models seasonality internally.
- **XGBoost / LightGBM:** require the full engineered feature table from
  [Phase4_Feature_Engineering_Strategy.md](Phase4_Feature_Engineering_Strategy.md) — calendar
  features, promo/holiday indicators, competition features, and lag/rolling/expanding sales
  features — plus categorical encoding (`StoreType`, `Assortment`, `StateHoliday` as native
  categoricals in both libraries, avoiding one-hot blowup across 1,115 stores).

## 4. Training Workflow

1. Load the Phase 4 feature table.
2. Exclude `Open == 0` rows from training (a closed store's `Sales = 0` is not a demand signal to
   learn from) — predictions for closed test-set days are simply set to 0 post-hoc using the
   provided `Open` flag.
3. **Prophet:** fit one model per store (or per `StoreType` segment as a lighter-weight
   alternative if per-store fitting is too slow on local hardware).
4. **XGBoost / LightGBM:** fit a single global model across all stores, with `Store` as a
   categorical feature — this lets the model share learned patterns (e.g. general promo uplift
   shape) across stores while still specializing per store via the categorical split.
5. Tune hyperparameters (tree depth, learning rate, number of estimators) via the time-series CV
   strategy below, not a single held-out split, to avoid overfitting to one arbitrary cutoff.

## 5. Validation Strategy: Time-Series Cross-Validation

Standard k-fold CV is invalid here — it would let a model train on future dates to predict the
past, leaking information no real forecast could have. Instead:

- **Rolling-origin (expanding window) CV**: pick several cutoff dates within the training period
  (e.g. every 6 weeks, mirroring the actual test horizon length), train on all data before each
  cutoff, and validate on the 6 weeks immediately after it.
- Report metrics as the **average across all cutoff folds**, not a single split, so the reported
  performance reflects consistency across different points in the yearly seasonal cycle (a model
  that only forecasts well right before Christmas is not actually good).
- The final model is retrained on the full training period before generating the actual
  `test.csv` forecast.

## 6. Performance Metrics

| Metric | What It Measures | Why It's Included |
|---|---|---|
| **MAE** | Average absolute forecast error, in sales units | Directly interpretable — "on average we're off by €X/day" — easy to communicate to store managers |
| **RMSE** | Penalizes large errors more heavily | Surfaces stores/periods where the model badly mis-forecasts (e.g. missed a promo spike entirely), which MAE can mask |
| **MAPE** | Percentage error, scale-independent | Lets small and large stores be compared on the same footing — a €50 error means very different things for a small vs. a flagship store |
| **R²** | Variance explained | A sanity check that the model captures real structure rather than predicting close to the mean everywhere |

All four are computed **excluding closed-store days** (which are deterministically zero and would
artificially inflate accuracy scores if included).

## 7. Model Recommendation Framework

Model selection is **not** "pick the lowest MAPE." The final recommendation weighs:

1. **Accuracy** (MAE/RMSE/MAPE/R² from the CV strategy above).
2. **Interpretability** — Prophet's trend/seasonality/holiday decomposition is directly useful
   for explaining *why* a forecast moved to a store manager or executive; XGBoost/LightGBM
   require a secondary feature-importance/SHAP step to get similar explainability.
3. **Training/inference cost on local hardware** — LightGBM's histogram-based training is
   expected to be materially faster than both Prophet (1,115 separate model fits) and XGBoost at
   this row count on 8 GB RAM, which matters for iteration speed during development.
4. **Operational fit** — a single global LightGBM/XGBoost model is simpler to deploy and retrain
   on a schedule than maintaining 1,115 independent Prophet models.

**Expected recommendation (to be confirmed empirically once Phase 7 modeling code is run):**
LightGBM as the primary production model — global training keeps it fast and low-memory on the
target hardware while still capturing cross-store patterns — with Prophet retained as a secondary
tool specifically for stakeholder-facing seasonality/holiday-effect explanation, since its
decomposition is far easier to present to non-technical business users than a tree-ensemble
feature-importance chart. XGBoost serves as the accuracy benchmark during development; if it does
not clearly outperform LightGBM on the time-series CV metrics, it is not worth its higher
training cost in production given the hardware constraint.

## 8. Implementation Status

Phase 7 is **fully implemented and completed**. 
- The modeling code and wrapper interfaces are implemented in `src/machine_learning/models.py`.
- Rolling-origin time-series cross-validation splits and performance metrics calculation are implemented in `src/machine_learning/validation.py`.
- The training pipeline is orchestrated by `src/machine_learning/train_pipeline.py`.
- Final trained models are saved in `models/trained/`, and combined predictions (actuals + validation OOF forecasts + future test forecasts) are exported to `models/artifacts/predictions.parquet` to feed the Streamlit dashboard.
- Average CV results across 3 folds (evaluation on open days):
  - **Prophet** (stores 1-10): MAE = 720.47, MAPE = 10.85%, R² = 0.840
  - **XGBoost**: MAE = 653.75, MAPE = 9.24%, R² = 0.911
  - **LightGBM**: MAE = 661.12, MAPE = 9.36%, R² = 0.909
- 7 unit tests in `tests/unit/test_modeling.py` successfully validate splits, wrapper interfaces, and metrics calculation.

