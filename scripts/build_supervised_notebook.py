"""
FitPulse - rebuild FitPulse_Faculty_Demo.ipynb for the SUPERVISED experiments E1-E5.

* The notebook as it was before the conversion is copied ONCE to archive/FitPulse_Faculty_Demo_pre_supervised.ipynb and every run of
  this script starts from that archived original, so the script is idempotent.
* Replaced (and archived in archive/notebook_removed_cells.json, with their saved outputs): old sections 5-7 (split, next-day Random Forest,
  K-Means), 9-10 (final results / inference), 12-13 (calorie regression, report-aligned RF + K-Means).
* Kept unchanged with their saved outputs: sections 1-4 (dataset, quality, preprocessing), 8 (Spark evidence) and 11 (HDFS) except the few cells patched below.
* New cells (sections 5-7, 9-10, the patched cells and the two kept evidence-listing cells 88 and 90) are executed in a fresh Jupyter kernel from the project folder; their outputs are
  copied into the notebook, so source and output always agree.  They only READ exports/ and faculty_evidence/supervised/ (run the experiments first).

    python scripts/build_supervised_notebook.py [--no-execute]
"""
import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nb_supervised_cells as C  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NB = ROOT / "FitPulse_Faculty_Demo.ipynb"
ARCH = ROOT / "archive"
PRE = ARCH / "FitPulse_Faculty_Demo_pre_supervised.ipynb"
REMOVED = ARCH / "notebook_removed_cells.json"

md = nbformat.v4.new_markdown_cell
code = nbformat.v4.new_code_cell


def text(cell):
    return "".join(cell.source) if isinstance(cell.source, list) else cell.source


def sub_line(cell, startswith, new):
    lines = text(cell).split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(startswith)]
    assert len(hits) == 1, f"expected exactly one line starting with {startswith!r}, found {len(hits)}"
    lines[hits[0]] = new
    cell.source = "\n".join(lines)


def sub(cell, old, new):
    s = text(cell)
    assert s.count(old) == 1, f"expected exactly one {old!r}, found {s.count(old)}"
    cell.source = s.replace(old, new)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-execute", action="store_true", help="assemble only (new cells keep empty outputs)")
    args = ap.parse_args()

    ARCH.mkdir(exist_ok=True)
    if not PRE.exists():
        cur = NB.read_text(encoding="utf-8")
        assert "7. Clustering Problem" in cur, "refusing to archive: the current notebook is not the pre-supervised original"
        shutil.copy2(NB, PRE)
        print("archived the original notebook ->", PRE)
    src = nbformat.read(PRE, as_version=4)
    cells = src.cells
    assert len(cells) == 139 and text(cells[78]).startswith("## 7. Clustering Problem"), "unexpected original notebook layout"

    drop = list(range(42, 101)) + list(range(112, 117)) + list(range(126, 135))
    REMOVED.write_text(json.dumps({"note": "cells removed from FitPulse_Faculty_Demo.ipynb by scripts/build_supervised_notebook.py; index = position in the pre-supervised notebook",
                                   "cells": [{"index": i, **{k: cells[i][k] for k in ("cell_type", "source")},
                                              **({"outputs": cells[i]["outputs"], "execution_count": cells[i].get("execution_count")} if cells[i].cell_type == "code" else {})}
                                             for i in drop]}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("removed cells archived ->", REMOVED, f"({len(drop)} cells)")

    # ---- patches to kept cells ----
    c1 = copy.deepcopy(cells[1])
    sub_line(c1, "        │  this notebook", "        │  this notebook                 (Spark MLlib: supervised models E1-E5, sections 5-7)")
    sub_line(c1, "| Random Forest |", "| Random Forest, Logistic Regression, Gradient-Boosted Trees | ✅ supervised classifiers E1-E4 in **Spark MLlib** (§5-7): `models/sup_e1_*.py` ... `sup_e4_*.py`; the original scikit-learn model is `models/train_goal_achievement.py` |")
    sub_line(c1, "| K-Means clustering |", "| K-Means clustering | ❌ **removed**: the faculty asked for supervised learning only, so both K-Means experiments were replaced by supervised classifiers (E3, E4); the code is kept in `archive/kmeans/` |")
    sub_line(c1, "| Linear Regression (calories) |", "| Linear Regression (calories) | ✅ `models/train_calorie_regression.py` kept as **E5**, with Random Forest and GBT regressors added (`models/sup_e5_calories.py`, §7.2) |")
    sub_line(c1, "| 70/15/15 split |", "| 70/15/15 split | ✅ E1 and E5 use a seeded 70/15/15 split; E2 is **chronological**, E3 is stratified 5-fold cross-validation, E4 is **user-held-out** (§5) |")
    sub(c1, "is the primary dashboard (§14)", "is the primary dashboard (§12)")
    c36 = copy.deepcopy(cells[36])
    sub_line(c36, "| `month_sin`, `month_cos` |", "| `month_sin`, `month_cos` | Cyclical month encoding | Seasonality without one-hot | used by E2 (§6.2) |")
    sub_line(c36, "| `label` (next-day goal achieved) |", "| `steps_roll7_avg` and the other `*_roll7_avg` columns | Trailing 7-row average **including the current row** | Silver-level convenience columns. **Not used** as features of same-day or next-day goal models: their window contains the prediction day (shown as the INVALID leakage run in §6.2). E2 builds its own windows that end at -1 | see §6.2 |")
    c105 = code(C.C105_CODE)
    c111 = copy.deepcopy(cells[111])
    sub(c111, "(pipelines, Random Forest, K-Means, evaluators)", "(pipelines, Random Forest, Gradient-Boosted Trees, Logistic / Linear Regression, evaluators)")
    c123 = code(C.C123_CODE)
    c125 = copy.deepcopy(cells[125])
    s125 = text(c125)
    k = s125.index("**About the 'DIFFERENCES FOUND' line in 11.6:**")
    c125.source = s125[:k] + C.C125_PARA
    c135 = copy.deepcopy(cells[135])
    sub(c135, "## 14. Dashboards", "## 12. Dashboards")
    sub(c135, "User Segmentation, Model Evaluation (70 visuals, 34 DAX measures)", "Supervised Results E3 and E4, Model Evaluation (68 visuals, 29 DAX measures)")
    sub(c135, "The five experiments (E1-E5) are shown one at a time and never combined.",
        "Page 4 shows E3 and E4 (one chart per experiment) and page 5 shows E1-E5 with every row labelled by its experiment and evaluation split; results of different experiments are never combined.")
    sub(c135, "Verified in Desktop: the `.pbix` reopens with data cached; card values equal independent pandas values; the Activity type slicer (Cycling) changes the cards to the expected values.\n"
              "Not verified: the other slicers individually, cross-page behaviour. Full record: `faculty_evidence/powerbi/POWERBI_VALIDATION.md`.",
        "Desktop verification of the regenerated file is pending: the earlier check (card values equal independent pandas values, Activity type slicer) applied to the previous `.pbix`. "
        "Automated validation of the regenerated project: `faculty_evidence/powerbi/project_validation.md`.")
    c135.source = text(c135) + C.C135_APPEND
    c137 = code(C.C137_CODE)
    c41 = code(C.C41_CODE)

    # ---- new sections ----
    new5 = [md(C.S5_MD), code(C.S5_FACTS), code(C.S5_HELPERS)]
    new6 = [md(C.E1_MD), code(C.E1_CODE), md(C.E1_NOTE), md(C.E2_MD), code(C.E2_CODE), md(C.E2_NOTE), md(C.E3_MD), code(C.E3_CODE), md(C.E3_NOTE)]
    new7 = [md(C.E4_MD), code(C.E4_CODE), md(C.E4_NOTE), md(C.E5_MD), code(C.E5_CODE), md(C.E5_NOTE), md(C.V_MD), code(C.V_CODE)]
    new910 = [md(C.FINAL_MD), code(C.FINAL_CODE), md(C.INF_MD), code(C.INF_CODE), md(C.LIM_MD)]

    final = (list(cells[0:1]) + [c1] + list(cells[2:36]) + [c36] + list(cells[37:41]) + [c41]
             + new5 + new6 + new7
             + list(cells[101:105]) + [c105] + list(cells[106:111]) + [c111]
             + new910
             + list(cells[117:123]) + [c123] + [cells[124]] + [c125]
             + [c135, cells[136], c137, cells[138]])
    assert text(cells[40]).startswith("### 4.3") and final.index(c41) == final.index(cells[40]) + 1
    # heading renumbering inside kept cells is limited to cell 135 (14 -> 12); cell 1 above already points to the new sections

    # ---- execute the new / patched code cells in a fresh kernel and copy their outputs back ----
    to_run = [c for c in final if c.cell_type == "code" and any(c is x for x in [c41, c105, c123, c137, cells[136], cells[138]] + new5 + new6 + new7 + new910)]
    if not args.no_execute:
        ex = nbformat.v4.new_notebook()
        ex.metadata = copy.deepcopy(src.metadata)
        spark_prelude = code("from pyspark.sql import SparkSession\n"
                             "spark = (SparkSession.builder.master('local[1]').appName('nb-exec').config('spark.driver.host', '127.0.0.1')\n"
                             "         .config('spark.ui.enabled', 'false').config('spark.sql.shuffle.partitions', '2').getOrCreate())")
        ex.cells = [copy.deepcopy(cells[3]), copy.deepcopy(cells[4]), spark_prelude] + [copy.deepcopy(c) for c in to_run]
        for c in ex.cells:
            c.pop("id", None)
        client = NotebookClient(ex, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}, allow_errors=False)
        print(f"executing {len(to_run)} new/patched code cells in a fresh kernel (cwd {ROOT}) ...")
        client.execute()
        for cell, done in zip(to_run, ex.cells[3:]):
            cell["outputs"] = done["outputs"]
            cell["execution_count"] = done.get("execution_count")
        print("executed OK")
    else:
        print("--no-execute: new cells keep empty outputs")

    nb = nbformat.v4.new_notebook()
    nb.metadata = copy.deepcopy(src.metadata)
    nb.metadata["fitpulse_supervised"] = True
    nb.cells = final
    nbformat.validate(nb)
    nbformat.write(nb, NB)
    print("wrote", NB, f"({len(final)} cells; was {len(cells)})")


if __name__ == "__main__":
    main()
