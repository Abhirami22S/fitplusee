r"""
FitPulse - automated structural check of the finished Power BI file (run AFTER you have built and saved the .pbix).

    python powerbi/check_pbix.py [path\to\FitPulse_PowerBI_Dashboard.pbix]
What it does (it can NOT render the report, so it is not a substitute for opening it in Power BI Desktop):
  * confirms the file is a genuine PBIX package (zip with a report layout and a data model),
  * lists pages and visuals, and the fields each visual uses,
  * fails if a visual references a table/column that is not in powerbi/data/_schema.json (or dim_date) or a measure not in measures.dax,
  * checks that the expected page names exist and that slicers are present.
Writes faculty_evidence/powerbi/pbix_structure_check.md.  Exit code 1 if any check fails.
Supports the classic format (Report/Layout) and the enhanced PBIR format (Report/definition/...).
"""
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT = HERE / "FitPulse_PowerBI_Dashboard.pbix"
EXPECTED_PAGES = ["Fitness Overview", "Activity and Sleep", "Calorie Prediction", "Supervised Results E3 and E4", "Model Evaluation"]
DIM_DATE = ["Date", "Year", "MonthNumber", "Month", "YearMonth", "DayOfWeek", "DayOfWeekNumber"]


def known_fields():
    schema = json.loads((HERE / "data" / "_schema.json").read_text(encoding="utf-8"))
    cols = {t: set(c) for t, c in schema.items()}
    cols["dim_date"] = set(DIM_DATE)
    measures = set()
    for line in (HERE / "measures.dax").read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z0-9 %()/\-.,]*?)\s*=", line)
        if m and not line.startswith("//") and m.group(1) != "dim_date" and not m.group(1).startswith("VAR "):
            measures.add(m.group(1).strip())
    return cols, measures


def walk(o, found):
    """Collect (kind, entity, property) from query JSON of either format."""
    if isinstance(o, dict):
        for kind in ("Column", "Measure", "Aggregation", "HierarchyLevel"):
            if kind in o and isinstance(o[kind], dict):
                node = o[kind]
                if kind == "Aggregation":
                    walk(node.get("Expression", {}), found)
                    continue
                prop = node.get("Property") or node.get("Level")
                src = node.get("Expression", {}).get("SourceRef", {})
                ent = src.get("Entity") or src.get("Source")
                if prop and ent:
                    found.append((kind, ent, prop))
        for v in o.values():
            walk(v, found)
    elif isinstance(o, list):
        for v in o:
            walk(v, found)


def parse_classic(layout):
    pages = []
    for sec in layout.get("sections", []):
        visuals = []
        for vc in sec.get("visualContainers", []):
            cfg = json.loads(vc["config"]) if isinstance(vc.get("config"), str) else vc.get("config", {})
            sv = cfg.get("singleVisual", {})
            fields, alias = [], {}
            pq = sv.get("prototypeQuery", {})
            for fr in pq.get("From", []):
                alias[fr["Name"]] = fr["Entity"]
            tmp = []
            walk(pq.get("Select", []), tmp)
            for k, ent, prop in tmp:
                fields.append((k, alias.get(ent, ent), prop))
            visuals.append({"type": sv.get("visualType", "?"), "fields": fields})
        pages.append({"name": sec.get("displayName", sec.get("name")), "visuals": visuals})
    return pages


def parse_pbir(z):
    names = z.namelist()
    pages = {}
    for n in names:
        m = re.match(r"Report/definition/pages/([^/]+)/page\.json$", n)
        if m:
            pages[m.group(1)] = {"name": json.loads(z.read(n)).get("displayName", m.group(1)), "visuals": []}
    for n in names:
        m = re.match(r"Report/definition/pages/([^/]+)/visuals/([^/]+)/visual\.json$", n)
        if m and m.group(1) in pages:
            v = json.loads(z.read(n)).get("visual", {})
            fields = []
            walk(v.get("query", {}), fields)
            pages[m.group(1)]["visuals"].append({"type": v.get("visualType", "?"), "fields": fields})
    return list(pages.values())


def check(path):
    results, lines = [], []

    def chk(name, ok, detail=""):
        results.append(bool(ok))
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {str(detail)[:200].replace('|', '/')} |")
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))

    if not Path(path).exists():
        print(f"NOT FOUND: {path}\nThe .pbix has not been created yet - nothing to check.")
        return 1
    if not zipfile.is_zipfile(path):
        chk("file is a zip package (genuine PBIX)", False, "not a zip")
        return 1
    z = zipfile.ZipFile(path)
    names = z.namelist()
    chk("PBIX package opens as a zip", True, f"{len(names)} entries, {Path(path).stat().st_size/1024:,.0f} KB")
    chk("contains a data model", any(n in ("DataModel", "DataMashup") or n.startswith("DataModel") for n in names), [n for n in names if "Model" in n or "Mashup" in n][:4])
    classic = "Report/Layout" in names
    pbir = any(n.startswith("Report/definition/") for n in names)
    chk("contains a report definition (Layout or PBIR)", classic or pbir, "classic Layout" if classic else "PBIR" if pbir else names[:8])
    if classic:
        pages = parse_classic(json.loads(z.read("Report/Layout").decode("utf-16-le")))
    elif pbir:
        pages = parse_pbir(z)
    else:
        return 1
    cols, measures = known_fields()
    chk("page count", len(pages) >= 5, [p["name"] for p in pages])
    for want in EXPECTED_PAGES:
        chk(f"page exists: {want}", any(want.lower() in (p["name"] or "").lower() for p in pages))
    bad, nvis, nslicer = [], 0, 0
    for p in pages:
        for v in p["visuals"]:
            nvis += 1
            nslicer += v["type"] == "slicer"
            for kind, ent, prop in v["fields"]:
                ok = (prop in measures) if kind == "Measure" else (ent in cols and prop in cols[ent]) or ent == "_Measures"
                if not ok:
                    bad.append(f"{p['name']}: {v['type']} -> {ent}[{prop}] ({kind})")
    chk("visuals found", nvis >= 15, f"{nvis} visuals")
    chk("slicers present", nslicer >= 2, f"{nslicer} slicers")
    chk("no visual references a nonexistent column or unknown measure", not bad, bad[:6] or "all field references resolve")
    md = ["# PBIX structure check", f"File: `{path}`", "", "| Check | Result | Detail |", "|---|---|---|"] + lines + ["", "## Pages"]
    for p in pages:
        md.append(f"* **{p['name']}** - {len(p['visuals'])} visuals: " + ", ".join(sorted({v['type'] for v in p['visuals']})))
    md += ["", "This check reads the file's metadata only. It does not render pages or test slicers; those are manual checks in Power BI Desktop (see BUILD_GUIDE.md section 8)."]
    out = ROOT / "faculty_evidence" / "powerbi"
    out.mkdir(parents=True, exist_ok=True)
    (out / "pbix_structure_check.md").write_text("\n".join(md), encoding="utf-8")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(check(sys.argv[1] if len(sys.argv) > 1 else DEFAULT))
