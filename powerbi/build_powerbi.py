r"""
FitPulse - generate the Power BI Project (PBIP) from the validated CSV exports.

    python powerbi/build_powerbi.py

Produces  powerbi/project/FitPulse_PowerBI_Dashboard.pbip  +  .SemanticModel (TMDL)  +  .Report (PBIR, 5 pages)
Open the .pbip in Power BI Desktop, then File > Save as > .pbix.  This script does NOT create a .pbix (only Power BI Desktop can).

Prerequisites: Node.js, and Microsoft's authoring CLI installed project-locally once:
    npm install --prefix powerbi/_tools @microsoft/powerbi-report-authoring-cli
The CLI's `scaffold` supplies the correct PBIR skeleton/base theme and its `validate` checks the result (offline).
"""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_definition as md  # noqa: E402

PBI = Path(__file__).resolve().parent
DATA = PBI / "data"
PROJ = PBI / "project"
CLI = PBI / "_tools" / "node_modules" / ".bin" / "powerbi-report-author.cmd"
MARK = PROJ / ".generated-by-build_powerbi"
NAME = md.NAME
VC = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.11.0/schema.json"
PAGE = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
PAGES = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json"
PLATFORM = "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.1.0/schema.json"
PBISM = "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json"
NS = uuid.UUID("6f1d7c1e-0000-4000-8000-0f17b0501e00")


def uid(*parts):
    return str(uuid.uuid5(NS, "|".join(parts)))


def oid(*parts):                       # 20-hex object name for pages/visuals
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:20]


def wjson(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def wtext(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def lit(v):
    if isinstance(v, bool):
        return {"expr": {"Literal": {"Value": "true" if v else "false"}}}
    if isinstance(v, (int, float)):
        return {"expr": {"Literal": {"Value": f"{v}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(v).replace("'", "''") + "'"}}}


# ======================================================================= semantic model (TMDL)
def q(name):
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def load_schema():
    out = {}
    for t, spec in md.TABLES.items():
        df = pd.read_csv(DATA / spec["csv"])
        cols = []
        for c in df.columns:
            if c in spec.get("date_columns", []):
                kind = "date"
            elif pd.api.types.is_bool_dtype(df[c]):
                kind = "bool"
            elif pd.api.types.is_integer_dtype(df[c]):
                kind = "int"
            elif pd.api.types.is_float_dtype(df[c]):
                kind = "dec"
            else:
                kind = "text"
            cols.append((c, kind))
        out[t] = cols
    return out


TMDL_TYPE = {"date": "dateTime", "int": "int64", "dec": "double", "text": "string", "bool": "boolean"}
M_TYPE = {"date": "type date", "int": "Int64.Type", "dec": "type number", "text": "type text", "bool": "type logical"}


def table_tmdl(t, spec, cols):
    L = []
    if spec.get("description"):
        L.append(f"/// {spec['description']}")
    L.append(f"table {q(t)}")
    L.append(f"\tlineageTag: {uid('table', t)}")
    if spec.get("key_date"):
        L.append("\tdataCategory: Time")
    L.append("")
    for c, kind in cols:
        L.append(f"\tcolumn {q(c)}")
        L.append(f"\t\tdataType: {TMDL_TYPE[kind]}")
        fmt = spec.get("formats", {}).get(c) or ("yyyy-mm-dd" if kind == "date" else None)
        if fmt:
            L.append(f"\t\tformatString: {fmt}")
        if spec.get("key_date") == c:
            L.append("\t\tisKey")
        if c in spec.get("hidden", []):
            L.append("\t\tisHidden")
        L.append(f"\t\tlineageTag: {uid('col', t, c)}")
        L.append("\t\tsummarizeBy: none")
        L.append(f"\t\tsourceColumn: {c if re.fullmatch(r'[A-Za-z0-9_]+', c) else chr(34) + c + chr(34)}")
        if c in spec.get("sort_by", {}):
            L.append(f"\t\tsortByColumn: {q(spec['sort_by'][c])}")
        L.append("")
    for host, name, expr, fmt, folder in md.MEASURES:
        if host != t:
            continue
        lines = expr.split("\n")
        if len(lines) == 1:
            L.append(f"\tmeasure {q(name)} = {expr}")
        else:
            L.append(f"\tmeasure {q(name)} =")
            L += ["\t\t\t" + x for x in lines]
        L.append(f"\t\tformatString: {fmt}")
        L.append(f"\t\tdisplayFolder: {folder}")
        L.append(f"\t\tlineageTag: {uid('measure', t, name)}")
        L.append("")
    types = ", ".join('{"%s", %s}' % (c, M_TYPE[k]) for c, k in cols)
    L.append(f"\tpartition {q(t)} = m")
    L.append("\t\tmode: import")
    L.append("\t\tsource =")
    L.append("\t\t\t\tlet")
    L.append(f'\t\t\t\t\tSource = Csv.Document(File.Contents(DataFolder & "{spec["csv"]}"), [Delimiter = ",", Columns = {len(cols)}, Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),')
    L.append("\t\t\t\t\tHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),")
    L.append(f'\t\t\t\t\tTyped = Table.TransformColumnTypes(Headers, {{{types}}}, "en-US")')
    L.append("\t\t\t\tin")
    L.append("\t\t\t\t\tTyped")
    L.append("")
    return "\n".join(L)


def write_model(schema):
    sm = PROJ / f"{NAME}.SemanticModel"
    wjson(sm / "definition.pbism", {"$schema": PBISM, "version": "4.0"})
    wjson(sm / ".platform", {"$schema": PLATFORM, "metadata": {"type": "SemanticModel", "displayName": NAME},
                             "config": {"version": "2.0", "logicalId": uid("semanticmodel", NAME)}})
    d = sm / "definition"
    wtext(d / "database.tmdl", "database\n\tcompatibilityLevel: 1567\n")
    tables = list(md.TABLES)
    order = json.dumps(["DataFolder"] + tables)
    model = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3", "\tdiscourageImplicitMeasures",
             "\tsourceQueryCulture: en-US", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
             f"annotation PBI_QueryOrder = {order}", ""]
    model += [f"ref table {q(t)}" for t in tables] + [""]
    wtext(d / "model.tmdl", "\n".join(model))
    folder = str(DATA) + "\\"
    wtext(d / "expressions.tmdl",
          f'expression DataFolder = "{folder}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
          f"\tlineageTag: {uid('expression', 'DataFolder')}\n")
    rel = []
    for frm, fc, to, tc in md.RELATIONSHIPS:
        rel += [f"relationship {uid('rel', frm, fc, to, tc)}", f"\tfromColumn: {q(frm)}.{q(fc)}", f"\ttoColumn: {q(to)}.{q(tc)}", ""]
    wtext(d / "relationships.tmdl", "\n".join(rel))
    for t, spec in md.TABLES.items():
        wtext(d / "tables" / f"{t}.tmdl", table_tmdl(t, spec, schema[t]))


# ======================================================================= report (PBIR)
def proj(kind, table, name):
    if kind == "a":      # Sum aggregation of a column (function code 0)
        col = {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}
        return {"field": {"Aggregation": {"Expression": col, "Function": 0}}, "queryRef": f"Sum({table}.{name})", "nativeQueryRef": f"Sum of {name}"}
    key = "Measure" if kind == "m" else "Column"
    return {"field": {key: {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}},
            "queryRef": f"{table}.{name}", "nativeQueryRef": name}


def in_filter(table, col, values, src="f"):
    return {"Version": 2, "From": [{"Name": src, "Entity": table, "Type": 0}],
            "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": src}}, "Property": col}}],
                                            "Values": [[{"Literal": {"Value": "'" + v.replace("'", "''") + "'"}}] for v in values]}}}]}


def visual_json(page_name, i, v):
    name = oid(page_name, str(i), v["type"])
    pos = {"x": v["x"], "y": v["y"], "z": i * 1000, "height": v["h"], "width": v["w"], "tabOrder": i * 1000}
    if v["type"] == "textbox":
        paras = []
        for line in v["body"].split("\n"):
            style = {"fontSize": v.get("size", "10pt")}
            if v.get("bold"):
                style["fontWeight"] = "bold"
            if v.get("color"):
                style["color"] = v["color"]
            paras.append({"textRuns": [{"value": line, "textStyle": style}]})
        vis = {"visualType": "textbox", "objects": {"general": [{"properties": {"paragraphs": paras}}]}, "drillFilterOtherVisuals": True}
        return name, {"$schema": VC, "name": name, "position": pos, "visual": vis}
    qs = {role: {"projections": [proj(*f) for f in fl]} for role, fl in v["fields"].items()}
    vis = {"visualType": v["type"], "query": {"queryState": qs}, "drillFilterOtherVisuals": True,
           "visualContainerObjects": {"title": [{"properties": {"show": lit(True), "text": lit(v["title"])}}],
                                      "general": [{"properties": {"altText": lit(v.get("alt", v["title"]))}}]}}
    if v["type"] == "card":
        vis["objects"] = {"labels": [{"properties": {"fontSize": lit(22), "labelDisplayUnits": lit(1)}}],
                          "categoryLabels": [{"properties": {"show": lit(True), "fontSize": lit(10)}}]}
        if v.get("show_title"):
            vis["visualContainerObjects"]["title"] = [{"properties": {"show": lit(True), "text": lit(v["title"]), "fontSize": lit(9)}}]
        else:
            vis["visualContainerObjects"]["title"] = [{"properties": {"show": lit(False)}}]
    if v.get("no_total"):
        vis.setdefault("objects", {})["total"] = [{"properties": {"totals": lit(False)}}]
    if v["type"] == "slicer":
        objs = {"data": [{"properties": {"mode": lit(v.get("mode", "Dropdown"))}}]}
        if v.get("single"):
            objs["selection"] = [{"properties": {"singleSelect": lit(True)}}]
        if v.get("default"):
            t, c = v["fields"]["Values"][0][1:]
            objs["general"] = [{"properties": {"filter": {"filter": in_filter(t, c, [v["default"]])}}}]
        vis["objects"] = objs
    out = {"$schema": VC, "name": name, "position": pos, "visual": vis}
    if v.get("filters"):
        flt = []
        for k, (t, c, vals) in enumerate(v["filters"]):
            flt.append({"name": oid(name, "flt", str(k)), "field": {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}},
                        "type": "Categorical", "filter": in_filter(t, c, vals)})
        out["filterConfig"] = {"filters": flt}
    return name, out


def write_report():
    rep = PROJ / f"{NAME}.Report"
    d = rep / "definition"
    shutil.rmtree(d / "pages")
    page_ids = []
    for pg in md.PAGES:
        pid = oid("page", pg["name"])
        page_ids.append(pid)
        wjson(d / "pages" / pid / "page.json", {"$schema": PAGE, "name": pid, "displayName": pg["name"], "displayOption": "FitToPage",
                                                "height": md.H, "width": md.W,
                                                "annotations": [{"name": "description", "value": pg["description"]}]})
        for i, v in enumerate(pg["visuals"], start=1):
            vn, vj = visual_json(pg["name"], i, v)
            wjson(d / "pages" / pid / "visuals" / vn / "visual.json", vj)
    wjson(d / "pages" / "pages.json", {"$schema": PAGES, "pageOrder": page_ids, "activePageName": page_ids[0]})
    # custom theme (authoring themes outside Desktop is documented as supported via RegisteredResources + report.json entry)
    theme_dst = rep / "StaticResources" / "RegisteredResources" / "FitPulse.json"
    theme_dst.parent.mkdir(parents=True, exist_ok=True)
    theme = json.loads((PBI / "FitPulse_theme.json").read_text(encoding="utf-8"))
    theme["name"] = "FitPulse.json"          # must equal the name registered in report.json (checked by the CLI validator)
    wjson(theme_dst, theme)
    rj = json.loads((d / "report.json").read_text(encoding="utf-8"))
    rj["themeCollection"]["customTheme"] = {"name": "FitPulse.json", "reportVersionAtImport": rj["themeCollection"]["baseTheme"]["reportVersionAtImport"],
                                            "type": "RegisteredResources"}
    rj["resourcePackages"].append({"name": "RegisteredResources", "type": "RegisteredResources",
                                   "items": [{"name": "FitPulse.json", "path": "FitPulse.json", "type": "CustomTheme"}]})
    wjson(d / "report.json", rj)


def write_measures_dax():
    L = ["// FitPulse Power BI measures (GENERATED by powerbi/build_powerbi.py from powerbi/model_definition.py - edit that file, not this one).",
         "// They are already inside the generated project's semantic model; this file is the human-readable copy for the report and viva.",
         "// Granularity: fact_daily = one row per USER-DAY (100,122); dim_user = one row per USER (437).",
         "// Step goal: goal_achieved = 1 when steps >= daily_step_goal = 1.10 x the user's own average daily steps (etl/spark_etl.py); not a fixed 8,000.",
         "// Expected values: powerbi/EXPECTED_VALUES.csv (computed independently with pandas).", ""]
    for host, name, expr, fmt, folder in md.MEASURES:
        L.append(f"// [{folder}]  host table: {host}   format: {fmt}")
        L.append(f"{name} = {expr}" if "\n" not in expr else f"{name} =\n" + "\n".join("    " + x for x in expr.split("\n")))
        L.append("")
    (PBI / "measures.dax").write_text("\n".join(L), encoding="utf-8")


def main():
    if not CLI.exists():
        sys.exit(f"missing {CLI}\nrun: npm install --prefix powerbi/_tools @microsoft/powerbi-report-authoring-cli")
    if PROJ.exists():
        if not MARK.exists():
            sys.exit(f"{PROJ} exists and was not created by this script - refusing to overwrite")
        shutil.rmtree(PROJ)
    r = subprocess.run([str(CLI), "scaffold", str(PROJ), "--name", NAME, "--model-path", f"../{NAME}.SemanticModel",
                        "--page-name", "Fitness Overview", "--offline"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("scaffold failed: " + r.stdout + r.stderr)
    MARK.write_text("generated by powerbi/build_powerbi.py; safe to delete and regenerate\n")
    schema = load_schema()
    write_model(schema)
    write_report()
    write_measures_dax()
    n_vis = sum(len(p["visuals"]) for p in md.PAGES)
    print(f"generated {PROJ / (NAME + '.pbip')}\n  tables {len(md.TABLES)}, relationships {len(md.RELATIONSHIPS)}, measures {len(md.MEASURES)}, pages {len(md.PAGES)}, visuals {n_vis}")


if __name__ == "__main__":
    main()
