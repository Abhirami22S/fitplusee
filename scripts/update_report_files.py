"""
Create CORRECTED COPIES of the report (.docx) and presentation (.pptx). The originals are never modified.
Every replacement is asserted to match; a missing target stops the script (nothing is silently skipped).
All numbers below come from files written by actual runs (faculty_evidence/report_aligned/, regression_results.csv);
they are read from those files, not typed.

    python scripts/update_report_files.py
Outputs: D:\\bigdata\\FitPulse_Report_Updated_v3.docx, D:\\bigdata\\actualfitpulseppt_v2.pptx,
         faculty_evidence/REPORT_AND_PPT_CHANGE_LOG.md
"""
import json
import sys
from pathlib import Path

import docx
import pandas as pd
from pptx import Presentation

ROOT = Path(__file__).resolve().parent.parent
EV = ROOT / "faculty_evidence"
RA = EV / "report_aligned"
SRC_DOCX = Path(r"D:\bigdata\FitPulse_Report_Updated (1).docx")
SRC_PPTX = next((q for q in (Path(r"D:\bigdata\actualfitpulseppt.pptx"), Path(r"D:\bigdata\Team 4-RA2411028010080\actualfitpulseppt.pptx")) if q.exists()),
                Path(r"D:\bigdata\actualfitpulseppt.pptx"))
OUT_DOCX = Path(r"D:\bigdata\FitPulse_Report_Updated_v3.docx")
OUT_PPTX = Path(r"D:\bigdata\actualfitpulseppt_v2.pptx")

# ---------------- measured values ----------------
m = pd.read_csv(RA / "rf_metrics.csv").set_index("Metric")
V, T = m["Validation"], m["Test"]
cm = pd.read_csv(RA / "rf_confusion_matrix.csv", index_col=0)
imp = pd.read_csv(RA / "rf_feature_importance.csv")
grid = pd.read_csv(RA / "rf_tuning_grid.csv")
ok = grid[grid.status == "ok"]
best = ok.loc[ok.validation_ROC_AUC.idxmax()]
d5 = ok[(ok.numTrees == best.numTrees) & (ok.maxDepth == 5)].validation_ROC_AUC.iloc[0]
split = pd.read_csv(RA / "rf_split_sizes.csv").set_index("Set")["Records"]
extra = pd.read_csv(RA / "rf_extra_checks.csv").set_index("Check")["Value"]
reg = pd.read_csv(EV / "regression_results.csv")
lr_t = reg[(reg.Model == "Linear Regression (selected)") & (reg.Set == "test")].iloc[0]
bl_t = reg[(reg.Model == "Baseline: training mean") & (reg.Set == "test")].iloc[0]
leak = [v for k, v in extra.items() if k.startswith("RF with steps")][0]
uh_acc = [v for k, v in extra.items() if "accuracy" in k and "User-held-out" in k][0]
uh_auc = [v for k, v in extra.items() if k == "User-held-out, ROC AUC"][0]
tn = cm.iloc[0, 0]
n0 = cm.iloc[0].sum()
f4 = lambda x: f"{x:.4f}"
pct1 = lambda x: f"{100*x:.1f}%"

log = []


def collapse(par, new):
    runs = par.runs
    runs[0].text = new
    for r in runs[1:]:
        r.text = ""


def all_pars(doc):
    for p in doc.paragraphs:
        yield p
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    yield p


def sub(doc, old, new, label, count_min=1):
    n = 0
    seen = set()
    for p in all_pars(doc):
        if p._p in seen:
            continue
        seen.add(p._p)
        txt = p.text.replace(" ", " ")          # code listings use non-breaking spaces
        if old in txt and p.runs:
            collapse(p, txt.replace(old, new))
            n += 1
    if n < count_min:
        sys.exit(f"NOT FOUND ({label}): {old[:90]!r}")
    log.append((label, old, new, n))


def cell(doc, ti, r, c, expect_prefix, new, label):
    cl = doc.tables[ti].rows[r].cells[c]
    if expect_prefix is not None and not cl.text.startswith(expect_prefix):
        sys.exit(f"table {ti} cell({r},{c}) is {cl.text!r}, expected prefix {expect_prefix!r}")
    old = cl.text
    collapse(cl.paragraphs[0], new)
    for extra_p in cl.paragraphs[1:]:
        for r_ in extra_p.runs:
            r_.text = ""
    log.append((label, old, new, 1))


def main():
    d = docx.Document(str(SRC_DOCX))
    # ---- section 1 ----
    sub(d, "Hadoop HDFS for distributed storage,", "Hadoop HDFS for distributed storage (a single-node deployment in this project),", "1.1 HDFS wording")
    sub(d, "Linear Regression is described only to complete the picture of the overall project.",
        f"Linear Regression (calorie burn) is implemented and evaluated in the project repository (test MAE {lr_t['MAE (kcal)']:.1f} kcal, RMSE {lr_t['RMSE (kcal)']:.1f} kcal, "
        f"R2 {lr_t['R2']:.3f}; the training-mean baseline has MAE {bl_t['MAE (kcal)']:.1f} kcal) but is not part of the two evaluated sections of this report.", "1.1 Linear Regression status")
    sub(d, "so a node failure does not stop the job.",
        "so a node failure does not stop the job (a property of a multi-node cluster; the single-node HDFS used in this project demonstrates the storage layer but not fault tolerance).", "1.6 fault tolerance")
    cell(d, 2, 2, 2, "Distributed storage", "Distributed storage: files are split into blocks spread across nodes and replicated (default factor 3 on a cluster; this project's single-node deployment uses factor 1) for fault tolerance.", "Table 2 HDFS row")
    cell(d, 2, 7, 2, "Interactive visualization", "Interactive visualization of goals, segments, and calorie trends for end users. Implemented as FitPulse_PowerBI_Dashboard.pbix (five pages) in Power BI Desktop; it imports CSV exports of the Silver data and the saved model results and does not read HDFS directly.", "Table 2 Power BI row (role)")
    # ---- section 2 ----
    sub(d, "reached 100% accuracy on a held-out split", f"reached {100*leak:.2f}% accuracy on a held-out split", "2.1 leakage demonstration")
    sub(d, "The best combination was numTrees = 100 and maxDepth = 20 (validation AUC 0.759, against 0.720 at maxDepth = 5).",
        f"Two of the eight combinations (100 trees at depth 15 and at depth 20) could not be run because the Spark JVM ran out of memory on the 16 GB laptop used; "
        f"of the six combinations measured, the best was numTrees = {int(best.numTrees)} and maxDepth = {int(best.maxDepth)} (validation AUC {best.validation_ROC_AUC:.4f}, against {d5:.4f} at maxDepth = 5).",
        "2.2 hyper-parameters")
    sub(d, "Reported results were computed with an equivalent scikit-learn implementation using the same 70/15/15 proportions, seed 42, and the hyperparameters above.",
        f"Reported results were computed by running this Spark MLlib code (models/spark_report_classification.py in the project repository) on the Silver dataset stored in HDFS, with seed 42, numTrees = {int(best.numTrees)} and maxDepth = {int(best.maxDepth)}.",
        "2.3 how results were computed")
    sub(d, "numTrees=100, maxDepth=20, maxBins=32, seed=42)", f"numTrees={int(best.numTrees)}, maxDepth={int(best.maxDepth)}, maxBins=32, seed=42)", "Listing 3 hyper-parameters")
    sub(d, "<HDFS_PATH>/fitpulse_raw.csv", "hdfs://localhost:9000/fitpulse/bronze/fitpulse_raw.csv", "Listings 1 and 5 data path", count_min=2)
    sub(d, "   # [Insert dataset path]", "", "Listing placeholder comments", count_min=1)
    sub(d, "The split contains 70,084 training, 15,019 validation and 15,019 test records. The values below were obtained with an equivalent scikit-learn implementation of Listings 1 to 4 (same proportions, seed and hyperparameters); running the Spark notebook may change the last decimals.",
        f"The split (Spark randomSplit, seed 42) contains {split['Training']:,} training, {split['Validation']:,} validation and {split['Test']:,} test records. The values below were measured by running Listings 1 to 4 in Spark MLlib on the HDFS-stored Silver dataset.",
        "2.4 split and provenance")
    rows = [("Accuracy", 1), ("Precision (weighted)", 2), ("Recall (weighted)", 3), ("F1 (weighted)", 4), ("Precision (goal-achieved class)", 5),
            ("Recall (goal-achieved class)", 6), ("F1 (goal-achieved class)", 7), ("ROC AUC", 8), ("Baseline accuracy (always majority class)", 9)]
    for name, r in rows:
        cell(d, 12, r, 1, None, f4(V[name]), f"Table 8 {name} validation")
        cell(d, 12, r, 2, None, f4(T[name]), f"Table 8 {name} test")
    cell(d, 13, 1, 1, None, f"{cm.iloc[0,0]:,}", "Table 9 TN")
    cell(d, 13, 1, 2, None, f"{cm.iloc[0,1]:,}", "Table 9 FP")
    cell(d, 13, 2, 1, None, f"{cm.iloc[1,0]:,}", "Table 9 FN")
    cell(d, 13, 2, 2, None, f"{cm.iloc[1,1]:,}", "Table 9 TP")
    top = imp.head(5).copy()
    top["feature"] = top["feature"].str.replace("_idx", "", regex=False)
    for i, (_, rw) in enumerate(top.iterrows(), start=1):
        cell(d, 14, i, 1, None, rw["feature"], f"Table 10 rank {i} feature")
        cell(d, 14, i, 2, None, f4(rw["importance"]), f"Table 10 rank {i} importance")
    base_t, acc_t = T["Baseline accuracy (always majority class)"], T["Accuracy"]
    sub(d, "accuracy of 73.0%, which is 11.9 percentage points above the 61.1%", f"accuracy of {pct1(acc_t)}, which is {100*(acc_t-base_t):.1f} percentage points above the {pct1(base_t)}", "2.5 accuracy")
    sub(d, "ROC AUC of 0.758", f"ROC AUC of {T['ROC AUC']:.3f}", "2.5 AUC")
    sub(d, "it finds 78.8% (recall) with a precision of 77.5%", f"it finds {pct1(T['Recall (goal-achieved class)'])} (recall) with a precision of {pct1(T['Precision (goal-achieved class)'])}", "2.5 precision/recall")
    sub(d, "it identifies 64.0% of the days on which the goal is missed (3,737 of 5,836)", f"it identifies {pct1(tn/n0)} of the days on which the goal is missed ({tn:,} of {n0:,})", "2.5 specificity")
    a, b_, c_, e_ = (top.iloc[i] for i in (0, 1, 2, 3))
    sub(d, "The most important feature is weight_kg (24.5%), followed by bmi (8.3%), calories_burned (6.9%) and height_cm (6.3%).",
        f"The most important feature is {a.feature} ({pct1(a.importance)}), followed by {b_.feature} ({pct1(b_.importance)}), {c_.feature} ({pct1(c_.importance)}) and {e_.feature} ({pct1(e_.importance)}).", "2.5 importances")
    sub(d, "(accuracy 72.5%, AUC 0.755)", f"(accuracy {pct1(uh_acc)}, AUC {uh_auc:.3f})", "2.5 user-held-out")
    sub(d, "[Insert Platform: GitHub / Google Colab / Jupyter]", "Jupyter Notebook and Python scripts, run locally (Windows, PySpark 4.0.1, Hadoop HDFS 3.4.1 single node)", "Tables 12/18 platform", count_min=2)
    # the two [Insert Notebook or Repository Name] cells are told apart by order
    seen = 0
    for p in all_pars(d):
        if "[Insert Notebook or Repository Name]" in p.text and p.runs:
            name = ("FitPulse (FitPulse_Faculty_Demo.ipynb; models/spark_report_classification.py)" if seen == 0
                    else "FitPulse (FitPulse_Faculty_Demo.ipynb)")
            collapse(p, p.text.replace("[Insert Notebook or Repository Name]", name))
            log.append(("Tables 12/18 repository name", "[Insert Notebook or Repository Name]", name, 1))
            seen += 1
    if seen != 2:
        sys.exit("expected two repository-name placeholders")
    d.save(str(OUT_DOCX))

    # ---------------- presentation ----------------
    pr = Presentation(str(SRC_PPTX))
    pp_log = []

    def pp_sub(old, new, label, count_min=1):
        n = 0
        for s_i, slide in enumerate(pr.slides, start=1):
            for sh in slide.shapes:
                if not sh.has_text_frame:
                    continue
                for para in sh.text_frame.paragraphs:
                    txt = "".join(r.text for r in para.runs)
                    if old in txt and para.runs:
                        para.runs[0].text = txt.replace(old, new)
                        for r in para.runs[1:]:
                            r.text = ""
                        n += 1
        if n < count_min:
            sys.exit(f"PPT NOT FOUND ({label}): {old!r}")
        pp_log.append((label, old, new, n))

    pp_sub("Publicly available Fitbit / Kaggle wearable fitness dataset", "Publicly available Kaggle wearable fitness dataset", "slide 3 dataset source")
    pp_sub("Distributed file system for fault-tolerant, large-scale data storage across commodity hardware clusters.",
           "Distributed file system for large-scale data storage. Deployed here as a single node (replication 1); fault tolerance needs a multi-node cluster.", "slide 4 HDFS")
    pp_sub("Model performance is evaluated using standard task-appropriate metrics pending training completion.",
           "Measured test-set results (Spark MLlib, Silver data on HDFS).", "slide 6 results heading")
    pp_sub("Numerical results to be populated upon model completion and validation testing.",
           f"Random Forest (same-day goal, steps >= 8,000): accuracy {acc_t:.3f}, ROC-AUC {T['ROC AUC']:.3f}. Linear Regression (calories): MAE {lr_t['MAE (kcal)']:.1f} kcal, RMSE {lr_t['RMSE (kcal)']:.1f} kcal, R2 {lr_t['R2']:.3f}.", "slide 6 results note")
    for lab, val in [("Accuracy", f"Accuracy {acc_t:.3f}"), ("Precision", f"Precision {T['Precision (goal-achieved class)']:.3f}"),
                     ("Recall", f"Recall {T['Recall (goal-achieved class)']:.3f}"), ("F1-Score", f"F1-Score {T['F1 (goal-achieved class)']:.3f}"),
                     ("RMSE", f"RMSE {lr_t['RMSE (kcal)']:.1f} kcal"), ("MAE", f"MAE {lr_t['MAE (kcal)']:.1f} kcal"), ("R² Score", f"R² {lr_t['R2']:.3f}")]:
        n = 0
        for slide in list(pr.slides)[5:6]:
            for sh in slide.shapes:
                if sh.has_text_frame and sh.text_frame.text.strip() == lab:
                    para = sh.text_frame.paragraphs[0]
                    para.runs[0].text = val
                    for r in para.runs[1:]:
                        r.text = ""
                    n += 1
        if n == 0:
            sys.exit(f"PPT metric label not found: {lab}")
        pp_log.append((f"slide 6 metric label {lab}", lab, val, n))
    pr.save(str(OUT_PPTX))

    md = ["# Report and presentation change log", "",
          f"Corrected copies (originals untouched): `{OUT_DOCX}` and `{OUT_PPTX}`.",
          "Every value below was read from files written by actual runs (see `faculty_evidence/report_aligned/`, `regression_results.csv`).",
          "Power BI statements in the original files are unchanged because the Power BI dashboard now exists (powerbi/FitPulse_PowerBI_Dashboard.pbix); Table 2 gains one clarifying sentence (CSV import, no direct HDFS read).",
          "Not changed: the embedded figures (Figures 1-5) and the `[Insert Implementation URL]` cells - the repository URL is not known.", "",
          "## Report (docx)", "| Where | Old | New | Matches |", "|---|---|---|---|"]
    md += [f"| {l} | {o[:110].replace('|','/')} | {n[:140].replace('|','/')} | {c} |" for l, o, n, c in log]
    md += ["", "## Presentation (pptx)", "| Where | Old | New | Matches |", "|---|---|---|---|"]
    md += [f"| {l} | {o[:110].replace('|','/')} | {n[:140].replace('|','/')} | {c} |" for l, o, n, c in pp_log]
    (EV / "REPORT_AND_PPT_CHANGE_LOG.md").write_text("\n".join(md), encoding="utf-8")
    print(f"docx: {len(log)} edits; pptx: {len(pp_log)} edits")


if __name__ == "__main__":
    main()
