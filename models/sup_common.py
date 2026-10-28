"""
FitPulse - shared helpers for the SUPERVISED experiments E1-E5 (Spark MLlib)
============================================================================
Every experiment is supervised (a labelled target is predicted from features). Shared rules, applied by every script:

* seed 42 everywhere (Spark splits, tree models, scikit-learn cross-checks);
* hyper-parameters are chosen on the VALIDATION set only; the test set is scored once per final model;
* a leakage run (the same model with a forbidden feature added) is recorded with status INVALID, never as a result;
* results are written in one long format  experiment_id, model, metric, value, split_type, status
  (status: VALID | INVALID (leakage demonstration) | BASELINE) to exports/E<n>_results.csv for Power BI;
* test-set predictions are saved so scripts/sup_sklearn_crosscheck.py can recompute the metrics independently.

DATA NOTE (state this whenever the numbers are shown): calories_burned, distance_km, active_minutes (= workout duration),
sedentary_minutes, max_heart_rate and sleep_quality_score are PARTLY DERIVED by data/prepare_raw_dataset.py from other
columns (for example calories = MET x weight_kg x duration/60). Some "predictions" therefore partly recover a formula.
"""
import itertools
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import BinaryClassificationEvaluator, RegressionEvaluator
from pyspark.ml.feature import OneHotEncoder, StandardScaler, StringIndexer, VectorAssembler
from pyspark.ml.functions import vector_to_array
from pyspark.sql import functions as F

import spark_common as sc

ROOT = sc.ROOT
SEED = sc.SEED
EXPORTS = ROOT / "exports"
EVIDENCE = ROOT / "faculty_evidence" / "supervised"

# one metric-name convention for E1-E5, so Power BI (powerbi/export_model_evaluation.py) can read the results as they are
M_ACC, M_F1W, M_F1M = "Accuracy", "F1 (weighted)", "F1 (macro)"
M_P1, M_R1, M_F11 = "Precision (positive class)", "Recall (positive class)", "F1 (positive class)"
M_AUC, M_BASE = "ROC AUC", "Baseline accuracy (always majority class)"


def add_args(ap):
    """Storage arguments of every Spark script + where results go."""
    sc.add_storage_args(ap)
    ap.add_argument("--exports-dir", default=None, help="results CSVs for Power BI (default exports/)")
    ap.add_argument("--evidence-dir", default=None, help="logs, predictions, tuning grids (default faculty_evidence/supervised/)")


def dirs(args):
    ex = Path(args.exports_dir) if args.exports_dir else EXPORTS
    ev = Path(args.evidence_dir) if args.evidence_dir else EVIDENCE
    for d in (ex, ev, ev / "predictions"):
        d.mkdir(parents=True, exist_ok=True)
    return ex, ev


# ------------------------------------------------------------------------------------------------ results table
class Results:
    COLS = ["experiment_id", "model", "metric", "value", "split_type", "status"]

    def __init__(self, exp):
        self.exp, self.rows = exp, []

    def add(self, model, metric, value, split_type, status="VALID"):
        self.rows.append({"experiment_id": self.exp, "model": model, "metric": metric, "value": float(value),
                          "split_type": split_type, "status": status})

    def add_many(self, model, metrics, split_type, status="VALID"):
        for k, v in metrics.items():
            self.add(model, k, v, split_type, status)

    def frame(self):
        return pd.DataFrame(self.rows, columns=self.COLS)

    def save(self, exports_dir):
        path = Path(exports_dir) / f"{self.exp}_results.csv"
        self.frame().to_csv(path, index=False)
        print(f"wrote {path} ({len(self.rows)} rows)")
        return path


# ------------------------------------------------------------------------------------------------ metrics
def confusion(pred, label="label", pred_col="prediction"):
    """(tn, fp, fn, tp) counts of a binary 0/1 prediction DataFrame."""
    c = {(float(r[label]), float(r[pred_col])): int(r["count"]) for r in pred.groupBy(label, pred_col).count().collect()}
    return c.get((0.0, 0.0), 0), c.get((0.0, 1.0), 0), c.get((1.0, 0.0), 0), c.get((1.0, 1.0), 0)


def _f1(p, r):
    return 2 * p * r / (p + r) if (p + r) else 0.0


def cls_metrics(pred, label="label", raw="rawPrediction"):
    """Binary-classification metrics from the confusion counts + Spark's areaUnderROC. Returns (dict, (tn, fp, fn, tp)).
    Baseline = accuracy of always predicting the majority class of THIS set."""
    tn, fp, fn, tp = confusion(pred, label)
    n = tn + fp + fn + tp
    p1 = tp / (tp + fp) if (tp + fp) else 0.0
    r1 = tp / (tp + fn) if (tp + fn) else 0.0
    p0 = tn / (tn + fn) if (tn + fn) else 0.0
    r0 = tn / (tn + fp) if (tn + fp) else 0.0
    f1_1, f1_0 = _f1(p1, r1), _f1(p0, r0)
    w1, w0 = (tp + fn) / n, (tn + fp) / n
    auc = BinaryClassificationEvaluator(labelCol=label, rawPredictionCol=raw, metricName="areaUnderROC").evaluate(pred)
    return {M_ACC: (tp + tn) / n, M_P1: p1, M_R1: r1, M_F11: f1_1, M_F1W: w1 * f1_1 + w0 * f1_0, M_F1M: (f1_1 + f1_0) / 2,
            M_AUC: auc, M_BASE: max(tp + fn, tn + fp) / n}, (tn, fp, fn, tp)


def reg_metrics(pred, label, pred_col="prediction"):
    out = {}
    for m, name in (("mae", "MAE (kcal)"), ("rmse", "RMSE (kcal)"), ("r2", "R2")):
        out[name] = RegressionEvaluator(labelCol=label, predictionCol=pred_col, metricName=m).evaluate(pred)
    return out


# ------------------------------------------------------------------------------------------------ pipelines + tuning
def make_pipeline(num, cat, estimator, onehot=False, scale=False):
    """StringIndexer [+ OneHotEncoder] -> VectorAssembler [-> StandardScaler] -> estimator.
    Tree models use the indexed categoricals directly (nominal metadata is kept); linear models use one-hot + scaling.
    All encoders/scalers sit inside the Pipeline, so they are fitted on the TRAINING split only."""
    keep = "error" if onehot else "keep"
    stages = [StringIndexer(inputCol=c, outputCol=f"{c}_idx", handleInvalid=keep) for c in cat]
    if onehot and cat:
        stages.append(OneHotEncoder(inputCols=[f"{c}_idx" for c in cat], outputCols=[f"{c}_ohe" for c in cat]))
        cols = list(num) + [f"{c}_ohe" for c in cat]
    else:
        cols = list(num) + [f"{c}_idx" for c in cat]
    stages.append(VectorAssembler(inputCols=cols, outputCol="raw" if scale else "features"))
    if scale:
        stages.append(StandardScaler(inputCol="raw", outputCol="features", withMean=True, withStd=True))
    stages.append(estimator)
    return Pipeline(stages=stages)


def grid(**axes):
    keys = list(axes)
    return [dict(zip(keys, v)) for v in itertools.product(*axes.values())]


def tune(builder, param_grid, train, val, score):
    """Fit every grid point on TRAIN, score on VALIDATION (higher is better). Returns ((score, params, model), grid_frame).
    A grid point that fails (for example a JVM out-of-memory) is recorded, not hidden."""
    rows, best = [], None
    for params in param_grid:
        t0 = time.time()
        try:
            m = builder(**params).fit(train)
            v, status = score(m.transform(val)), "ok"
        except Exception as e:                                        # noqa: BLE001
            if "Py4J" in type(e).__name__ or isinstance(e, ConnectionError):
                # the JVM is gone (almost always java.lang.OutOfMemoryError): every later grid point would fail too
                raise RuntimeError(f"Spark JVM died at grid point {params} - lower the grid or raise FITPULSE_DRIVER_MEMORY") from e
            m, v, status = None, float("nan"), f"FAILED: {type(e).__name__}"
        rows.append({**params, "validation_score": v, "seconds": round(time.time() - t0, 1), "status": status})
        print("   ", rows[-1])
        if m is not None and (best is None or v > best[0]):
            best = (v, params, m)
    return best, pd.DataFrame(rows)


def user_hash(df, seed=SEED):
    """Deterministic 0..1 value per USER (all rows of a user share it) -> user-held-out splits."""
    return df.withColumn("u_hash", (F.abs(F.xxhash64("user_id", F.lit(seed))) % 1000) / 1000.0)


def row_hash(df, seed=SEED):
    """Deterministic 0..1 value per (user_id, date) row - the split used by the calorie model and the notebook."""
    return df.withColumn("split_u", (F.abs(F.xxhash64("user_id", "date", F.lit(seed))) % 1_000_000) / 1_000_000.0)


# ------------------------------------------------------------------------------------------------ evidence outputs
def export_predictions(pred, id_cols, path, label_col="label"):
    """Save id columns, true label, prediction and (when available) P(class 1) for the independent scikit-learn check."""
    cols = [F.col(c) for c in id_cols] + [F.col(label_col).alias("label"), F.col("prediction")]
    if "probability" in pred.columns:
        cols.append(vector_to_array("probability")[1].alias("score"))
    pdf = pred.select(*cols).toPandas().sort_values(id_cols)
    pdf.to_csv(path, index=False)
    return pdf


def feature_importance(model, names, model_name, exp):
    """Importance of the final estimator of a fitted PipelineModel: impurity importance for trees, |standardised
    coefficient| for linear models (only tree models are exported to exports/, as requested)."""
    est = model.stages[-1]
    if hasattr(est, "featureImportances"):
        vals, kind = list(est.featureImportances.toArray()), "tree impurity importance"
    else:
        vals, kind = [abs(float(c)) for c in est.coefficients.toArray()], "abs standardised coefficient"
    if len(vals) != len(names):
        raise ValueError(f"{model_name}: {len(vals)} importances vs {len(names)} feature names")
    return pd.DataFrame({"experiment_id": exp, "model": model_name, "feature": names, "importance": vals, "kind": kind})


def onehot_names(model, num, cat):
    """Feature names of a make_pipeline(..., onehot=True) model: numerics + 'column=category' (last category dropped)."""
    names = list(num)
    for i, c in enumerate(cat):
        labels = model.stages[i].labelsArray[0]
        names += [f"{c}={l}" for l in labels[:-1]]
    return names


def write_run_info(path, cfg, **kw):
    import pyspark
    info = {"experiment": kw.pop("experiment", ""), "storage_mode": cfg.mode, "silver_source": cfg.output_path, "seed": SEED,
            "pyspark": pyspark.__version__, "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), **kw}
    Path(path).write_text(json.dumps(info, indent=2, default=str), encoding="utf-8")
