"""
Updates notebook section 14 now that the Power BI .pbix exists (cells 135-137 + the section 1 table row), and re-executes ONLY
the rewritten code cells (fresh kernel with the notebook's setup cells) so their saved outputs are real.
    python faculty_evidence/update_section14.py     (run from FitPulse/)
"""
import copy
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent
NB = ROOT / "FitPulse_Faculty_Demo.ipynb"

MD = """## 14. Dashboards (Power BI is the primary dashboard) and faculty-proof checklist

**Power BI** - `powerbi/FitPulse_PowerBI_Dashboard.pbix`, saved by Power BI Desktop 2.158 from a generated Power BI Project (`powerbi/build_powerbi.py`).
Five pages: Fitness Overview, Activity and Sleep, Calorie Prediction, User Segmentation, Model Evaluation (70 visuals, 34 DAX measures). It imports validated **CSV exports** of the Silver data and the saved
model results; it does **not** read HDFS (single node, replication factor 1). The five experiments (E1-E5) are shown one at a time and never combined.
Verified in Desktop: the `.pbix` reopens with data cached; card values equal independent pandas values; the Activity type slicer (Cycling) changes the cards to the expected values.
Not verified: the other slicers individually, cross-page behaviour. Full record: `faculty_evidence/powerbi/POWERBI_VALIDATION.md`.

**Streamlit** (`dashboard/app.py`) is the earlier per-user dashboard, kept as a **legacy/optional** component. It was tested with Streamlit's AppTest (below); that testing found and fixed a Windows crash
(`strftime('%-d')`). Its data source is the local SQLite database, not HDFS."""

CODE1 = '''
import json
from IPython.display import Image, display
pbix = PROJECT_ROOT / "powerbi" / "FitPulse_PowerBI_Dashboard.pbix"
print("Power BI file:", pbix.relative_to(PROJECT_ROOT), "| exists:", pbix.exists(), "| size: %s bytes" % (f"{pbix.stat().st_size:,}" if pbix.exists() else "n/a"))
for name in ("project_validation", "dashboard/dashboard_validation"):
    f = EVIDENCE / ("powerbi/" + name + ".json" if name == "project_validation" else name + ".json")
    d = json.loads(f.read_text(encoding="utf-8"))
    print(f"{name}: {d['passed']}/{d['total']} automated checks passed")
print()
print((EVIDENCE / "powerbi" / "pbix_structure_check.md").read_text(encoding="utf-8")[:1500])
shots = sorted((EVIDENCE / "powerbi" / "pbix_screenshots").glob("*.png"))
print("Real screenshots of the opened .pbix in Power BI Desktop:", [s.name for s in shots])
for s in shots:
    print(s.name)
    display(Image(filename=str(s), width=900))
'''.strip()

CODE2 = '''
mm = pd.read_csv(EVIDENCE / "model_metrics.csv")
print("faculty_evidence/model_metrics.csv - every row carries its source file; rows:", len(mm))
display(mm[mm.metric.isin(["Accuracy", "ROC AUC", "ROC-AUC", "F1 (goal-achieved class)", "MAE (kcal)", "RMSE (kcal)", "R2"])]
        .drop(columns=["source_file"]).round(4).reset_index(drop=True))
print("\\nKnown limits: RF experiments differ between notebook and report (section 13); the legacy Streamlit app's classifier is Logistic Regression "
      "(ROC-AUC 0.755 from models/metrics_report.md, an earlier training run that was not repeated); HDFS is single node; Power BI imports CSV and does not read HDFS.")
'''.strip()


def main():
    nb = nbf.read(NB, as_version=4)
    assert nb.cells[135].source.startswith("## 14."), "unexpected notebook layout"
    nb.cells[135].source = MD
    nb.cells[136].source = CODE1
    nb.cells[137].source = CODE2
    for c in nb.cells:
        if c.cell_type == "markdown" and "❌ **Power BI is not built**" in c.source:
            old = [l for l in c.source.split("\n") if "❌ **Power BI is not built**" in l][0]
            c.source = c.source.replace(old, "| Dashboard | ✅ **Power BI** (`powerbi/FitPulse_PowerBI_Dashboard.pbix`, built and checked in Power BI Desktop; imports CSV, not HDFS) is the primary dashboard (§14). The earlier Streamlit app (`dashboard/app.py`) is legacy/optional |")
    setup = [copy.deepcopy(nb.cells[i]) for i in (3, 4)]
    for c in setup:
        c.outputs, c.execution_count = [], None
    run = [copy.deepcopy(nb.cells[136]), copy.deepcopy(nb.cells[137])]
    for c in run:
        c.outputs, c.execution_count = [], None
    scratch = nbf.v4.new_notebook(cells=setup + run)
    scratch.metadata = nb.metadata
    NotebookClient(scratch, timeout=600, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
    for tgt, src in ((136, scratch.cells[2]), (137, scratch.cells[3])):
        nb.cells[tgt].outputs = src.outputs
        nb.cells[tgt].execution_count = nb.cells[tgt].execution_count or src.execution_count
    nbf.write(nb, NB)
    print("section 14 updated; errors:", [o["ename"] for c in (scratch.cells[2], scratch.cells[3]) for o in c.outputs if o.get("output_type") == "error"])


if __name__ == "__main__":
    main()
