r"""
FitPulse - validate the GENERATED Power BI project (powerbi/project) without Power BI Desktop.

    python powerbi/validate_powerbi_project.py [--skip-external]

Checks (all read the generated files, not the Python spec):
  A. data sources exist; TMDL tables/columns match the CSV headers; relationships point at real columns
  B. every DAX measure references only existing tables / columns / measures
  C. every visual field (Column / Measure) exists in the model; page names; slicers; experiment separation on page 5
  D. emulation of each measure in pandas on the CSV exports vs powerbi/EXPECTED_VALUES.csv
     (this checks the measure LOGIC against independent expected values; it does not execute DAX)
  E. external tools when available: Microsoft's PBIR validator (node CLI) and Microsoft's TMDL deserializer (PowerShell + TOM)
Writes faculty_evidence/powerbi/project_validation.md and .json.  Exit code 1 if any check fails.
Not covered (needs Power BI Desktop): DAX execution, rendering, slicer behaviour, Power Query data load.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PBI = Path(__file__).resolve().parent
ROOT = PBI.parent
sys.path.insert(0, str(PBI))
import model_definition as md  # noqa: E402

PROJ = PBI / "project"
REPORT = PROJ / f"{md.NAME}.Report" / "definition"
SM = PROJ / f"{md.NAME}.SemanticModel" / "definition"
DATA = PBI / "data"
results = []


def check(name, ok, detail=""):
    results.append({"check": name, "passed": bool(ok), "detail": str(detail)[:300]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {str(detail)[:200]}" if detail else ""))


def unq(s):
    s = s.strip()
    return s[1:-1].replace("''", "'") if s.startswith("'") and s.endswith("'") else s


# ---------------------------------------------------------------- parse generated TMDL (independent of the spec)
def parse_tmdl():
    tables = {}
    for f in sorted((SM / "tables").glob("*.tmdl")):
        txt = f.read_text(encoding="utf-8")
        tname = unq(re.search(r"^table\s+(.+)$", txt, re.M).group(1))
        cols = [unq(m) for m in re.findall(r"^\tcolumn\s+(.+)$", txt, re.M)]
        meas = {}
        for m in re.finditer(r"^\tmeasure\s+('(?:[^']|'')+'|\S+)\s*=\s*(.*?)(?=^\t(?:measure|partition|column)\s|\Z)", txt, re.M | re.S):
            body = m.group(2)
            expr = re.split(r"^\t\t(?:formatString|displayFolder|lineageTag):", body, maxsplit=1, flags=re.M)[0]
            meas[unq(m.group(1))] = "\n".join(l.strip() for l in expr.strip().splitlines())
        csv = re.search(r'File\.Contents\(DataFolder & "([^"]+)"\)', txt)
        ncols = re.search(r"Columns = (\d+)", txt)
        tables[tname] = {"columns": cols, "measures": meas, "csv": csv.group(1) if csv else None, "ncols": int(ncols.group(1)) if ncols else None,
                         "key": re.search(r"^\t\tisKey", txt, re.M) is not None}
    rels = []
    for m in re.finditer(r"fromColumn:\s*(.+)\n\s*toColumn:\s*(.+)", (SM / "relationships.tmdl").read_text(encoding="utf-8")):
        def split(x):
            t, c = x.strip().split(".", 1)
            return unq(t), unq(c)
        rels.append((split(m.group(1)), split(m.group(2))))
    return tables, rels


def collect_fields(o, out):
    if isinstance(o, dict):
        for kind in ("Column", "Measure"):
            if kind in o and isinstance(o[kind], dict) and "Property" in o[kind]:
                ent = o[kind].get("Expression", {}).get("SourceRef", {}).get("Entity")
                if ent:
                    out.append((kind, ent, o[kind]["Property"]))
        for v in o.values():
            collect_fields(v, out)
    elif isinstance(o, list):
        for v in o:
            collect_fields(v, out)


def main(skip_external=False):
    if not PROJ.exists():
        print("project not generated - run python powerbi/build_powerbi.py")
        return 1
    tables, rels = parse_tmdl()
    # ---------------- A. data sources + schema
    check("A1 .pbip, .Report/definition.pbir and .SemanticModel/definition.pbism exist",
          (PROJ / f"{md.NAME}.pbip").exists() and (PROJ / f"{md.NAME}.Report" / "definition.pbir").exists() and (PROJ / f"{md.NAME}.SemanticModel" / "definition.pbism").exists())
    pbir = json.loads((PROJ / f"{md.NAME}.Report" / "definition.pbir").read_text(encoding="utf-8"))
    check("A2 report binds to the semantic model by relative path", pbir["datasetReference"]["byPath"]["path"] == f"../{md.NAME}.SemanticModel", pbir["datasetReference"])
    folder = re.search(r'expression DataFolder = "([^"]+)"', (SM / "expressions.tmdl").read_text(encoding="utf-8")).group(1)
    check("A3 DataFolder parameter points at an existing folder", Path(folder).is_dir(), folder)
    for t, info in tables.items():
        p = DATA / (info["csv"] or "")
        ok = p.exists()
        hdr = list(pd.read_csv(p, nrows=0).columns) if ok else []
        check(f"A4 table {t}: CSV exists and TMDL columns == CSV header", ok and hdr == info["columns"] and info["ncols"] == len(hdr), f"{info['csv']} {len(hdr)} cols")
    check("A5 tables in model == tables in spec", set(tables) == set(md.TABLES))
    for (ft, fc), (tt, tc) in rels:
        check(f"A6 relationship {ft}[{fc}] -> {tt}[{tc}] uses existing columns", ft in tables and tt in tables and fc in tables[ft]["columns"] and tc in tables[tt]["columns"])
        a, b = pd.read_csv(DATA / tables[ft]["csv"], usecols=[fc])[fc], pd.read_csv(DATA / tables[tt]["csv"], usecols=[tc])[tc]
        check(f"A7 relationship {tt}[{tc}] is unique (one side) and covers all {ft}[{fc}] values", b.is_unique and set(a.unique()) <= set(b.unique()),
              f"{a.nunique()} distinct -> {len(b)} keys")
    # ---------------- B. DAX references
    all_measures = {m for t in tables.values() for m in t["measures"]}
    check("B0 measure count in model == spec", len(all_measures) == len(md.MEASURES), len(all_measures))
    bad = []
    for t, info in tables.items():
        for name, expr in info["measures"].items():
            for tb, col in re.findall(r"(\w+)\[([^\]]+)\]", expr):
                if tb not in tables or (col not in tables[tb]["columns"] and col not in all_measures):
                    bad.append(f"{name}: {tb}[{col}]")
            for ref in re.findall(r"(?<![\w'])\[([^\]]+)\]", expr):
                if ref not in all_measures:
                    bad.append(f"{name}: [{ref}]")
    check("B1 every table[column] and [measure] referenced in DAX exists", not bad, bad[:5] or f"{len(all_measures)} measures checked")
    # ---------------- C. report
    pages = {}
    for pj in (REPORT / "pages").glob("*/page.json"):
        j = json.loads(pj.read_text(encoding="utf-8"))
        pages[j["displayName"]] = {"dir": pj.parent, "visuals": []}
        for vf in (pj.parent / "visuals").glob("*/visual.json"):
            pages[j["displayName"]]["visuals"].append(json.loads(vf.read_text(encoding="utf-8")))
    want = ["Fitness Overview", "Activity and Sleep", "Calorie Prediction", "Supervised Results E3 and E4", "Model Evaluation"]
    check("C1 the five requested pages exist with exact names", all(w in pages for w in want) and len(pages) == 5, list(pages))
    order = json.loads((REPORT / "pages" / "pages.json").read_text(encoding="utf-8"))["pageOrder"]
    check("C2 page order follows the requested sequence", [json.loads((REPORT / "pages" / pid / "page.json").read_text())["displayName"] for pid in order] == want)
    badf, nfields, nvis = [], 0, 0
    for pn, pg in pages.items():
        for v in pg["visuals"]:
            nvis += 1
            fl = []
            collect_fields(v, fl)
            for kind, ent, prop in fl:
                nfields += 1
                if ent not in tables:
                    badf.append(f"{pn}: unknown table {ent}")
                elif kind == "Measure" and prop not in tables[ent]["measures"]:
                    badf.append(f"{pn}: {ent}[{prop}] is not a measure on {ent}")
                elif kind == "Column" and prop not in tables[ent]["columns"]:
                    badf.append(f"{pn}: {ent}[{prop}] is not a column")
    expected_refs = sum(sum(len(fl) for fl in v.get("fields", {}).values()) + len(v.get("filters", [])) for pg in md.PAGES for v in pg["visuals"])
    check("C3 no visual references a nonexistent column or measure (and every spec field is present)", not badf and nfields == expected_refs, badf[:5] or f"{nvis} visuals, {nfields} field references (spec expects {expected_refs})")
    MIN = {"Supervised Results E3 and E4": (0, 5), "Model Evaluation": (1, 4)}            # (slicers, data visuals) per page; default (2, 5)
    for pn, pg in pages.items():
        n_s = sum(1 for v in pg["visuals"] if v.get("visual", {}).get("visualType") == "slicer")
        n_v = sum(1 for v in pg["visuals"] if v.get("visual", {}).get("visualType") not in ("textbox", "slicer"))
        lo_s, lo_v = MIN.get(pn, (2, 5))
        check(f"C4 page '{pn}': slicers >= {lo_s} and data visuals >= {lo_v}", n_s >= lo_s and n_v >= lo_v, f"{n_s} slicers, {n_v} data visuals")
    pos = [(pn, v["position"]) for pn, pg in pages.items() for v in pg["visuals"]]
    check("C5 every visual lies inside the 1280x720 page", all(p["x"] >= 0 and p["y"] >= 0 and p["x"] + p["width"] <= 1280 and p["y"] + p["height"] <= 720 for _, p in pos), len(pos))
    sr = pd.read_csv(DATA / "supervised_results.csv")
    ex = pd.read_csv(DATA / "experiments.csv")
    cc = pd.read_csv(DATA / "crosscheck.csv")
    check("C6 experiment ids E1-E5 preserved and distinct in experiments / supervised_results / crosscheck",
          sorted(ex.experiment_id) == ["E1", "E2", "E3", "E4", "E5"] and set(sr.experiment_id) == set(ex.experiment_id) and set(cc.experiment_id) == set(ex.experiment_id))

    def shown(v):                      # fields the visual DISPLAYS (query), not the ones it filters on
        fl = []
        collect_fields(v.get("visual", {}).get("query", {}), fl)
        return fl

    def pinned(v):                     # experiment ids fixed by a visual-level filter
        out = set()
        for fl_ in v.get("filterConfig", {}).get("filters", []):
            if fl_["field"]["Column"]["Property"] == "experiment_id":
                for vals in fl_["filter"]["Where"][0]["Condition"]["In"]["Values"]:
                    out.add(vals[0]["Literal"]["Value"].strip("'"))
        return out

    bad7, bad8 = [], []
    for pn in ("Supervised Results E3 and E4", "Model Evaluation"):
        for v in pages[pn]["visuals"]:
            fl = shown(v)
            if any(k == "Measure" and ent == "supervised_results" and prop == "Result Value" for k, ent, prop in fl):
                labelled = any(ent == "supervised_results" and prop == "experiment_id" for _, ent, prop in fl) or len(pinned(v)) == 1
                if not labelled:
                    bad7.append(f"{pn}: {v['visual']['visualType']} {v['name'][:8]}")
                if pn.startswith("Supervised Results") and not (pinned(v) and pinned(v) <= {"E3", "E4"}):
                    bad8.append(f"{pn}: {v['visual']['visualType']} {v['name'][:8]}")
    check("C7 every visual showing Result Value names its experiment (column shown, or pinned to a single experiment by a filter) - results are never mixed", not bad7, bad7[:4])
    check("C8 page 4 shows only E3 and E4: every Result Value visual is pinned by a filter to E3 and/or E4", not bad8, bad8[:4])
    p4_text = " ".join(json.dumps(v) for v in pages["Supervised Results E3 and E4"]["visuals"] if v["visual"]["visualType"] == "textbox")
    check("C9 page 4 states that E3 and E4 are never combined", "never combined" in p4_text and "E3" in p4_text and "E4" in p4_text)

    def card_title(v):                 # (visible?, text) of a card's title
        try:
            pr = v["visual"]["visualContainerObjects"]["title"][0]["properties"]
            return pr["show"]["expr"]["Literal"]["Value"] == "true", pr["text"]["expr"]["Literal"]["Value"]
        except Exception:
            return False, ""

    cc_cards = [v for v in pages["Model Evaluation"]["visuals"] if v["visual"]["visualType"] == "card"
                and any(prop.startswith("Cross-check") for _, _, prop in shown(v))]
    check("C10 page 5: both cross-check cards show a title that names hdfs_rerun/sklearn_crosscheck.csv as their source",
          len(cc_cards) == 2 and all(card_title(v)[0] and "hdfs_rerun/sklearn_crosscheck.csv" in card_title(v)[1] for v in cc_cards), [card_title(v) for v in cc_cards])
    # ---------------- D. emulate measures vs EXPECTED_VALUES
    f = pd.read_csv(DATA / "fact_daily.csv")
    exp = pd.read_csv(PBI / "EXPECTED_VALUES.csv").set_index("measure").expected_value
    t = f[f.model_split == "test"]
    e5 = sr[(sr.experiment_id == "E5") & (sr.split_type == "test")]
    pick = lambda model, status, met: float(e5[(e5.model == model) & (e5.status == status) & (e5.metric == met)].value.iloc[0])
    LR = "Linear Regression"
    emu = {
        "Total Users": (f.user_id.nunique(), "Distinct users"), "User-Days": (len(f), "Total days (rows)"), "Total Steps": (f.steps.sum(), "Total steps"),
        "Avg Daily Steps": (f.steps.mean(), "Average daily steps"), "Avg Calories Burned": (f.calories_burned.mean(), "Average calories burned"),
        "Avg Active Minutes": (f.active_minutes.mean(), "Average active minutes"), "Step-Goal Achievement %": (f.goal_achieved.mean(), "Personal step-goal achievement rate"),
        "Calorie-Goal Achievement %": (f.calorie_goal_achieved.mean(), "Calorie-goal achievement rate"), "Avg Distance (km)": (f.distance_km.mean(), "Average distance (km)"),
        "Avg Sedentary Minutes": (f.sedentary_minutes.mean(), "Average sedentary minutes"), "Avg Sleep Hours": (f.sleep_hours.mean(), "Average sleep hours"),
        "Avg Sleep Quality": (f.sleep_quality_score.mean(), "Average sleep quality"), "Avg Heart Rate": (f.avg_heart_rate.mean(), "Average heart rate (bpm)"),
        "Active Share of Waking Time %": (f.active_minutes.sum() / (f.active_minutes.sum() + f.sedentary_minutes.sum()), "Active share of waking time"),
        "Test Days": (len(t), "Test-set days"), "Test MAE (recomputed, kcal)": (t.calorie_error.abs().mean(), "Test-set MAE (kcal)"),
        "Test RMSE (recomputed, kcal)": (np.sqrt((t.calorie_error ** 2).mean()), "Test-set RMSE (kcal)"),
        "Test R2 (recomputed)": (1 - (t.calorie_error ** 2).sum() / ((t.calories_burned - t.calories_burned.mean()) ** 2).sum(), "Test-set R2"),
        "Avg Prediction Error (bias, kcal)": (t.calorie_error.mean(), "Test-set mean error / bias (kcal)"),
        "Verified Test MAE (kcal)": (pick(LR, "VALID", "MAE (kcal)"), "Test-set MAE (kcal)"), "Verified Test RMSE (kcal)": (pick(LR, "VALID", "RMSE (kcal)"), "Test-set RMSE (kcal)"),
        "Verified Test R2": (pick(LR, "VALID", "R2"), "Test-set R2"), "Baseline Test MAE (kcal)": (pick("Baseline: training mean", "BASELINE", "MAE (kcal)"), "Baseline (training mean) test MAE (kcal)"),
        "Cross-check Checks": (len(cc), "Cross-check checks"), "Cross-check Passed": (int(cc.passed.sum()), "Cross-check checks passed"),
    }
    tol = {"Test-set R2": 5e-4, "Test-set MAE (kcal)": 0.05, "Test-set RMSE (kcal)": 0.05}
    missing = [m for m in all_measures if m not in emu and m not in ("Avg Steps Prev Month", "Steps MoM %", "Avg Predicted Calories", "Result Value")]
    check("D0 every headline measure has a pandas emulation", not missing, missing)
    for m, (val, label) in emu.items():
        e = float(exp[label])
        ok = abs(val - e) <= max(tol.get(label, 0), abs(e) * 1e-6, 1e-9)
        check(f"D1 {m}: emulated {val:,.4f} vs expected '{label}' {e:,.4f}", ok)
    mon = f.assign(m=f.date.str[:7]).groupby("m").steps.mean()
    check("D3 monthly average steps (page 1 trend) equals expected for all 12 months", all(abs(mon[k] - float(exp[f"Average daily steps in {k}"])) < 1e-6 for k in mon.index))
    # ---------------- E. external validators
    if not skip_external:
        cli = PBI / "_tools" / "node_modules" / ".bin" / "powerbi-report-author.cmd"
        if cli.exists():
            r = subprocess.run([str(cli), "validate", str(PROJ / f"{md.NAME}.pbip")], capture_output=True, text=True)
            try:
                d = json.loads(r.stdout)["data"]
                check("E1 Microsoft PBIR validator (powerbi-report-author validate): 0 errors, 0 warnings", d["result"] == "succeeded" and d["errorCount"] == 0 and d["warningCount"] == 0,
                      f"{d['result']}, {d['errorCount']} errors, {d['warningCount']} warnings")
            except Exception as e:
                check("E1 Microsoft PBIR validator ran", False, f"{e}: {r.stdout[:200]} {r.stderr[:200]}")
        else:
            check("E1 Microsoft PBIR validator available", False, "run: npm install --prefix powerbi/_tools @microsoft/powerbi-report-authoring-cli")
        ps1 = PBI / "validate_tmdl.ps1"
        tom = ROOT.parent / "tools" / "nuget" / "as_pkg" / "lib" / "net45" / "Microsoft.AnalysisServices.Tabular.dll"
        if tom.exists():
            r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)], capture_output=True, text=True)
            check("E2 Microsoft TMDL deserializer (TOM) parses the semantic model", r.returncode == 0, (r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr).strip() else "")
        else:
            check("E2 TMDL deserializer available", False, "see prerequisite in powerbi/validate_tmdl.ps1")
    # no BOM / path length
    boms = [p for p in PROJ.rglob("*") if p.is_file() and p.suffix in (".json", ".tmdl", ".pbip", ".pbir", ".pbism") and p.read_bytes()[:3] == b"\xef\xbb\xbf"]
    check("F1 generated text files are UTF-8 without BOM", not boms, boms[:2])
    longest = max(len(str(p)) for p in PROJ.rglob("*"))
    check("F2 longest project path < 260 characters (Windows limit)", longest < 260, longest)
    passed = sum(r["passed"] for r in results)
    out = ROOT / "faculty_evidence" / "powerbi"
    out.mkdir(parents=True, exist_ok=True)
    (out / "project_validation.json").write_text(json.dumps({"passed": passed, "total": len(results), "checks": results}, indent=2), encoding="utf-8")
    md_lines = ["# Power BI project validation (automated; Power BI Desktop NOT used)", f"**{passed}/{len(results)} checks passed.**", "",
                "Not covered: DAX execution, Power Query data load, rendering, slicer behaviour - these need Power BI Desktop.", "", "| Check | Result | Detail |", "|---|---|---|"]
    md_lines += [f"| {r['check']} | {'PASS' if r['passed'] else 'FAIL'} | {r['detail'][:120].replace('|', '/')} |" for r in results]
    (out / "project_validation.md").write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main("--skip-external" in sys.argv))
