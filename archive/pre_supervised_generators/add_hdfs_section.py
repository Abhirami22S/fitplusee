"""
Adds the "HDFS Storage and Spark Integration" section to FitPulse_Faculty_Demo.ipynb WITHOUT re-running the
existing 118 cells (their saved outputs are preserved).

How the new cells get real outputs: they are executed (nbclient, fresh kernel) in a scratch notebook that holds
only the notebook's own setup cells (3, 4, 9) + the new cells. The resulting outputs are copied onto the new
cells in the real notebook. If HDFS is not reachable when this runs, the cells print "NOT VERIFIED" themselves.

    python faculty_evidence/add_hdfs_section.py          (run from the FitPulse/ folder, HDFS started)
"""
import copy
import json
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent
NB = ROOT / "FitPulse_Faculty_Demo.ipynb"
MARK = "## 11. HDFS Storage and Spark Integration"

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
new_cells = []

new_cells.append(md(r"""
## 11. HDFS Storage and Spark Integration

Sections 1-10 above were produced from **local Parquet** (`file:///`), because HDFS was not installed at the time
(§8.4 records that state). This section documents the HDFS upgrade and **every cell below runs against the live
cluster**; if HDFS is not reachable the cells say `NOT VERIFIED` and nothing is faked.

| | Local Parquet (fallback) | HDFS (this section) |
|---|---|---|
| Where | `data/processed/fitpulse_silver/` on the Windows disk | `hdfs://localhost:9000/fitpulse/silver` in the DataNode's block storage |
| Run with | `python etl/spark_etl.py` | `python etl/spark_etl.py --storage hdfs --hdfs-uri hdfs://localhost:9000` (or `.\run_fitpulse_hdfs.ps1`) |
| Served by | Windows file system | NameNode (metadata) + DataNode (blocks), Hadoop 3.4.1, single node, replication 1 |
| If the store is down | n/a | the ETL **exits with code 2** - it never falls back to local disk |

Architecture actually implemented: `Raw CSV -> prepare_raw_dataset.py -> HDFS /fitpulse/bronze -> Spark ETL (cleaning + features) -> HDFS /fitpulse/silver (Parquet, month=) -> Spark MLlib -> (SQLite export) -> Streamlit`.
Only the Bronze/Silver storage moved to HDFS; the Gold table, SQLite export and the scikit-learn models used by Streamlit still use local files.
""".strip()))

new_cells.append(code(r"""
# 11.1 Verified HDFS URI and active storage mode  (real CLI calls against the running NameNode)
import os, re, subprocess
HADOOP_DIR = TOOLS / "hadoop-3.4.1"
HDFS_ENV = {**os.environ, "HADOOP_HOME": str(HADOOP_DIR), "HADOOP_CONF_DIR": str(PROJECT_ROOT / "hadoop-conf"),
            "JAVA_HOME": str(TOOLS / "jdk17"), "HADOOP_LOG_DIR": str(TOOLS / "hdfs-logs")}

def hdfs(*args, timeout=90):
    p = subprocess.run([str(HADOOP_DIR / "bin" / "hdfs.cmd"), *args], capture_output=True, text=True,
                       env=HDFS_ENV, timeout=timeout)
    return p.returncode, (p.stdout + p.stderr).strip()

rc, uri = hdfs("getconf", "-confKey", "fs.defaultFS")
rc2, ls_root = hdfs("dfs", "-ls", "/")
HDFS_OK = rc == 0 and rc2 == 0 and uri.startswith("hdfs://")
HDFS_URI = uri.splitlines()[-1].strip() if HDFS_OK else None
HDFS_SILVER = f"{HDFS_URI}/fitpulse/silver" if HDFS_OK else None
LOCAL_SILVER_URI = "file:///" + str((PROJECT_ROOT / "data/processed/fitpulse_silver").resolve()).replace("\\", "/")

print("hdfs getconf -confKey fs.defaultFS ->", uri if HDFS_OK else f"FAILED ({uri[:200]})")
print("\n$ hdfs dfs -ls /\n" + ls_root)
if HDFS_OK:
    print(f"\nSTORAGE MODE : HDFS ({HDFS_URI})   <-- verified: both commands succeeded")
    print("Silver (HDFS):", HDFS_SILVER)
    print("Silver (local fallback, unchanged):", LOCAL_SILVER_URI)
else:
    print("\nSTORAGE MODE : NOT VERIFIED - HDFS is not reachable. Start it with .\\start_hdfs.ps1 and re-run this section.")
""".strip()))

new_cells.append(code(r"""
# 11.2 HDFS directory listing and space usage
if HDFS_OK:
    rc, out = hdfs("dfs", "-ls", "-R", "/fitpulse")
    lines = out.splitlines()
    print("$ hdfs dfs -ls -R /fitpulse   (first 12 of %d entries)" % len(lines))
    print("\n".join(lines[:12]))
    print("\n$ hdfs dfs -du -h /fitpulse")
    print(hdfs("dfs", "-du", "-h", "/fitpulse")[1])
    print("\n$ hdfs dfsadmin -report   (summary)")
    rep = hdfs("dfsadmin", "-report")[1].splitlines()
    print("\n".join(l for l in rep if l.startswith(("Configured Capacity", "DFS Used:", "Live datanodes", "Name:", "Hostname"))))
else:
    print("NOT VERIFIED - HDFS not reachable")
""".strip()))

new_cells.append(code(r"""
# 11.3 Actual Spark read FROM HDFS: schema, record count, partition layout
if HDFS_OK:
    hsilver = spark.read.parquet(HDFS_SILVER)
    print("Spark read:", HDFS_SILVER)
    print("File system class behind the path:",
          spark._jvm.org.apache.hadoop.fs.Path(HDFS_SILVER).getFileSystem(spark._jsc.hadoopConfiguration()).getClass().getName())
    print(f"Record count : {hsilver.count():,}")
    print(f"Columns      : {len(hsilver.columns)}")
    hsilver.printSchema()
    # Parquet partition layout straight from the HDFS listing
    rows = []
    for l in hdfs("dfs", "-ls", "-R", "/fitpulse/silver")[1].splitlines():
        m = re.search(r"(\d+)\s+\d{4}-\d\d-\d\d \d\d:\d\d\s+(\S+\.parquet)$", l)      # owner names may contain spaces
        if m:
            rows.append({"partition": m.group(2).split("/")[3], "bytes": int(m.group(1))})
    layout = (pd.DataFrame(rows).groupby("partition").agg(parquet_files=("bytes", "size"), size_KB=("bytes", lambda s: round(s.sum()/1024, 1))))
    layout.loc["TOTAL"] = [layout.parquet_files.sum(), round(layout.size_KB.sum(), 1)]
    display(layout)
    print("Example HDFS path:", "/fitpulse/silver/month=2024-03/part-0000x-....snappy.parquet")
else:
    print("NOT VERIFIED - HDFS not reachable")
""".strip()))

new_cells.append(code(r"""
# 11.4 Write / read-back verification with a small scratch dataset (own directory, removed afterwards)
import time as _t
if HDFS_OK:
    scratch = f"{HDFS_URI}/fitpulse/_nb_selftest_{int(_t.time())}"
    expected = {(1, "alpha", 10.5), (2, "beta", 20.25), (3, "gamma", 30.0)}
    vals = ", ".join(f"({i}, '{n}', {v}D)" for i, n, v in sorted(expected))
    spark.sql(f"SELECT * FROM VALUES {vals} AS t(id, name, value)").write.mode("errorifexists").parquet(scratch)
    back = spark.read.parquet(scratch)
    got = {(r.id, r.name, r.value) for r in back.collect()}
    print("Wrote then read back:", scratch)
    print("Schema     :", back.schema.simpleString())
    print("Row count  :", back.count(), "(expected 3)")
    print("Values     :", sorted(got))
    print("Values identical:", got == expected)
    print("\n$ hdfs dfs -ls", scratch.replace(HDFS_URI, ""))
    print(hdfs("dfs", "-ls", scratch.replace(HDFS_URI, ""))[1])
    assert got == expected and back.count() == 3
    p = spark._jvm.org.apache.hadoop.fs.Path(scratch)
    p.getFileSystem(spark._jsc.hadoopConfiguration()).delete(p, True)       # only the scratch dir created above
    print("\nScratch directory removed. WRITE/READ-BACK VERIFIED")
else:
    print("NOT VERIFIED - HDFS not reachable")
""".strip()))

new_cells.append(code(r"""
# 11.5 HDFS Silver vs local-Parquet Silver (same ETL code, different storage)
if HDFS_OK:
    lsilver = spark.read.parquet(LOCAL_SILVER_URI)
    cols = sorted(lsilver.columns)
    print(f"local rows = {lsilver.count():,} | HDFS rows = {hsilver.count():,} | same columns = {cols == sorted(hsilver.columns)}")
    only_local = lsilver.select(cols).exceptAll(hsilver.select(cols)).count()
    only_hdfs = hsilver.select(cols).exceptAll(lsilver.select(cols)).count()
    print(f"rows only in local = {only_local}, rows only in HDFS = {only_hdfs}  ->",
          "IDENTICAL" if only_local == only_hdfs == 0 else "DIFFERENT")
    rpt = json.loads((EVIDENCE / "hdfs" / "etl_hdfs_run_report.json").read_text())
    print("\nETL run report (faculty_evidence/hdfs/etl_hdfs_run_report.json):")
    print(json.dumps(rpt, indent=2))
else:
    print("NOT VERIFIED - HDFS not reachable")
""".strip()))

new_cells.append(code(r"""
# 11.6 ML re-validation on the Silver data READ FROM HDFS (scripts/hdfs_ml_validation.py, run separately; results saved)
ml = EVIDENCE / "hdfs" / "ml"
if (ml / "comparison_with_local_run.md").exists():
    print((ml / "comparison_with_local_run.md").read_text(encoding="utf-8"))
    old = pd.read_csv(EVIDENCE / "classification_results.csv"); new = pd.read_csv(ml / "classification_results.csv")
    display(old.assign(source="local Parquet (sections 1-10)").merge(new.assign(source="HDFS (this run)"), how="outer"))
    old_s = pd.read_csv(EVIDENCE / "silhouette_scores.csv"); new_s = pd.read_csv(ml / "silhouette_scores.csv")
    display(pd.concat([old_s.assign(source="local"), new_s.assign(source="HDFS")]))
else:
    print("NOT VERIFIED - run scripts/hdfs_ml_validation.py first")
""".strip()))

new_cells.append(code(r"""
# 11.7 Behaviour when HDFS is unavailable (test recorded by scripts/test_hdfs_down.ps1 while the NameNode was stopped)
f = EVIDENCE / "hdfs" / "failure_mode_test.txt"
print(f.read_text(encoding="utf-8") if f.exists() else "NOT VERIFIED - test not run yet")
""".strip()))

new_cells.append(md(r"""
**Reading this section.** The architecture claim is supported only by the cells above that print `VERIFIED` /
identical-row results. Anything printed as `NOT VERIFIED` means the check could not be run. Local Parquet remains
available as an explicit fallback (`python etl/spark_etl.py`, no flags); HDFS mode is opt-in and never degrades silently.
Limitations: single-node cluster (replication 1, so no fault tolerance), Spark still runs in `local[*]`, the
scikit-learn models and Streamlit dashboard read the local SQLite/joblib artefacts, not HDFS.
""".strip()))


def main():
    nb = nbf.read(NB, as_version=4)
    if any(MARK in "".join(c.source) for c in nb.cells if c.cell_type == "markdown"):
        sys.exit("HDFS section already present in the notebook - refusing to add it twice.")
    # scratch notebook: notebook's own setup cells + the new cells
    setup = [copy.deepcopy(nb.cells[i]) for i in (3, 4, 9)]
    for c in setup:
        c.outputs, c.execution_count = [], None
    scratch = nbf.v4.new_notebook(cells=setup + [copy.deepcopy(c) for c in new_cells])
    scratch.metadata = nb.metadata
    NotebookClient(scratch, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
    executed = scratch.cells[len(setup):]
    for c in executed:
        if c.cell_type == "code":
            for o in c.outputs:
                if o.get("output_type") == "stream" and "[Stage" in o.get("text", ""):
                    o["text"] = "\n".join(l for l in o["text"].split("\n") if "[Stage" not in l)
    # insert before the final spark.stop() cell, after "Limitations"
    insert_at = len(nb.cells) - 1
    assert "spark.stop()" in nb.cells[insert_at].source
    # next execution counts continue the notebook's numbering
    last = max((c.get("execution_count") or 0) for c in nb.cells if c.cell_type == "code")
    n = last
    for c in executed:
        if c.cell_type == "code":
            n += 1
            c.execution_count = n
            for o in c.outputs:
                if o.get("output_type") == "execute_result":
                    o["execution_count"] = n
    nb.cells[insert_at:insert_at] = executed
    # keep earlier sections honest: §8.4 text refers to the pre-HDFS state
    for c in nb.cells:
        if c.cell_type == "markdown" and c.source.startswith("### 8.4 HDFS Evidence"):
            c.source = ("### 8.4 HDFS Evidence (baseline recorded BEFORE the HDFS upgrade)\n\n"
                        "The check below looks for a Hadoop/HDFS installation and the configured default filesystem, and does not\n"
                        "assume either. **Its saved output is the local-only baseline** from the session in which sections 1-10 were\n"
                        "executed (no HDFS on that PATH). The HDFS integration and its verification are in **section 11**.")
    # statements elsewhere that were true before the upgrade
    swaps = [
        ("| Distributed storage | ⚠️ *HDFS-style* partitioned Parquet on the local filesystem. **No HDFS cluster is configured** (see §8.4) |",
         "| Distributed storage | ✅ Single-node Hadoop HDFS 3.4.1 (NameNode + DataNode, replication 1) holds Bronze and Silver; verified in **§11**. Sections 1-10 were executed on local Parquet (the explicit fallback) before HDFS existed. No fault tolerance (one node) |"),
        ("* ❌ **HDFS is not running.** Do not present HDFS screenshots. Describe it as \"HDFS-style partitioned storage, HDFS-ready\".",
         "* ✅ **Update:** this paragraph describes the state when §8.4 was recorded. HDFS has since been installed and verified (§11): claim only what §11 prints, and describe it as a single-node deployment."),
        ("* Spark runs in local mode. HDFS is not deployed; storage is HDFS-style partitioned Parquet.",
         "* Spark runs in local mode. HDFS is a single-node deployment (replication 1, §11); sections 1-10 were produced from local Parquet."),
    ]
    hits = 0
    for c in nb.cells:
        if c.cell_type == "markdown":
            for old, new in swaps:
                if old in c.source:
                    c.source = c.source.replace(old, new)
                    hits += 1
    print("text updates applied:", hits, "of", len(swaps))
    nbf.write(nb, NB)
    print("Inserted", len(executed), "cells at index", insert_at)


if __name__ == "__main__":
    main()
