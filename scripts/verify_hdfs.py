"""
FitPulse - HDFS verification. Runs REAL commands / Spark jobs against the running cluster, saves their
actual output under faculty_evidence/hdfs/, and exits non-zero if an essential check fails.

    python scripts/verify_hdfs.py --hdfs-uri hdfs://localhost:9000 [--local-silver data/processed/fitpulse_silver]
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
import storage  # noqa: E402

EVID = ROOT / "faculty_evidence" / "hdfs"
results = []


def check(name, ok, detail=""):
    results.append({"check": name, "passed": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))
    return ok


def run_cli(fname, args, env=None):
    p = subprocess.run(["hdfs.cmd"] + args, capture_output=True, text=True, env=env)
    out = f"$ hdfs {' '.join(args)}\n(exit code {p.returncode})\n\n{p.stdout}{p.stderr}"
    (EVID / fname).write_text(out, encoding="utf-8")
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hdfs-uri", required=True)
    ap.add_argument("--hdfs-silver", default="/fitpulse/silver")
    ap.add_argument("--local-silver", default=str(ROOT / "data/processed/fitpulse_silver"))
    a = ap.parse_args()
    EVID.mkdir(parents=True, exist_ok=True)
    os.chdir(ROOT)

    # ---- 1. CLI evidence ----
    p = run_cli("01_fs_defaultFS.txt", ["getconf", "-confKey", "fs.defaultFS"])
    check("fs.defaultFS is an hdfs:// URI", p.returncode == 0 and p.stdout.strip().startswith("hdfs://"), p.stdout.strip())
    p = run_cli("02_ls_root.txt", ["dfs", "-ls", "/"])
    check("hdfs dfs -ls /", p.returncode == 0)
    p = run_cli("03_ls_recursive_fitpulse.txt", ["dfs", "-ls", "-R", "/fitpulse"])
    check("hdfs dfs -ls -R /fitpulse", p.returncode == 0)
    month_dirs = [l.split()[-1] for l in p.stdout.splitlines() if "/month=" in l and l.startswith("d")]
    parquet_files = [l for l in p.stdout.splitlines() if l.strip().endswith(".parquet")]
    check("Silver has month= partition directories", len(month_dirs) > 0,
          f"{len(month_dirs)} partitions, {len(parquet_files)} parquet files")
    p = run_cli("04_du_fitpulse.txt", ["dfs", "-du", "-h", "/fitpulse"])
    check("hdfs dfs -du -h /fitpulse", p.returncode == 0)
    p = run_cli("05_dfsadmin_report.txt", ["dfsadmin", "-report"])
    check("DataNode live (dfsadmin -report)", p.returncode == 0 and "Live datanodes (1)" in p.stdout)
    # fsck goes over HTTP and the Windows account name contains a space -> HTTP 400; use a space-free Hadoop user
    # (HDFS permission checking is disabled in hdfs-site.xml, so this only affects the request URL).
    p = run_cli("06_fsck_silver.txt", ["fsck", a.hdfs_silver, "-files", "-blocks"],
                env={**os.environ, "HADOOP_USER_NAME": "fitpulse"})
    check("fsck reports Silver HEALTHY", "is HEALTHY" in p.stdout)
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='java.exe'\" | ForEach-Object { "
          "$_.ProcessId.ToString() + ' ' + (($_.CommandLine -split ' ') | Where-Object {$_ -like 'org.apache.hadoop*'}) }")
    jps = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True)
    (EVID / "07_daemon_processes.txt").write_text(jps.stdout, encoding="utf-8")
    check("NameNode + DataNode JVMs running", "namenode.NameNode" in jps.stdout and "datanode.DataNode" in jps.stdout)

    # ---- 2. Spark checks ----
    from pyspark.sql import SparkSession
    cfg = storage.resolve("hdfs", a.hdfs_uri)
    b = (SparkSession.builder.appName("FitPulse-HDFS-Verify").master("local[*]")
         .config("spark.driver.host", "127.0.0.1").config("spark.sql.shuffle.partitions", "8")
         .config("spark.driver.memory", "2g"))
    for k, v in storage.spark_hadoop_conf(cfg).items():
        b = b.config(k, v)
    spark = b.getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    lines = []

    # 2a write/read-back self-test (own scratch dir, removed afterwards)
    test_path = f"{a.hdfs_uri}/fitpulse/_selftest_{int(time.time())}"
    expected = {(1, "alpha", 10.5), (2, "beta", 20.25), (3, "gamma", 30.0)}
    # built with Spark SQL (JVM only) so the self-test does not depend on Python workers
    values = ", ".join(f"({i}, '{n}', {v}D)" for i, n, v in sorted(expected))
    spark.sql(f"SELECT * FROM VALUES {values} AS t(id, name, value)").write.mode("errorifexists").parquet(test_path)
    back = spark.read.parquet(test_path)
    rows = {(r.id, r.name, r.value) for r in back.collect()}
    check("Self-test: write small Parquet to HDFS and read it back",
          back.count() == 3 and rows == expected, f"{test_path}, schema={back.schema.simpleString()}")
    lines += [f"SELF-TEST path: {test_path}", back.schema.simpleString(), str(sorted(rows)), ""]
    fs_p, fs = storage._fs(spark, test_path)
    fs.delete(fs_p, True)

    # 2b Silver read from HDFS
    silver_uri = a.hdfs_uri + a.hdfs_silver
    silver = spark.read.parquet(silver_uri)
    n = silver.count()
    parts = sorted(r[0] for r in silver.select("month").distinct().collect())
    check("Spark reads Silver from HDFS", n > 0, f"{silver_uri}: {n:,} rows, {len(silver.columns)} columns")
    check("Silver partitions (Spark) match HDFS directory listing", len(parts) == len(month_dirs),
          f"{len(parts)} months: {parts[0]}..{parts[-1]}")
    lines += [f"SILVER on HDFS: {silver_uri}", f"rows={n}", f"columns={len(silver.columns)}",
              "partitions=" + ", ".join(parts), "", "SCHEMA:", silver._jdf.schema().treeString()]
    rpt = EVID / "etl_hdfs_run_report.json"
    if rpt.exists():
        r = json.loads(rpt.read_text())
        check("ETL report: storage_mode == hdfs", r["storage_mode"] == "hdfs", r["output_path"])
        check("ETL report: rows written == rows read back == rows Spark reads now",
              r["silver_rows_written"] == r["silver_rows_read_back"] == n,
              f"bronze={r['bronze_rows']:,} clean={r['clean_rows']:,} silver={r['silver_rows_written']:,}")
        lines += ["", f"ETL rows: bronze={r['bronze_rows']} clean={r['clean_rows']} silver={r['silver_rows_written']}"]

    # 2c local vs HDFS comparison
    if Path(a.local_silver).exists():
        local = spark.read.parquet(storage.local_uri(a.local_silver))
        ln = local.count()
        cols_equal = sorted(local.columns) == sorted(silver.columns)
        check("Local vs HDFS Silver: same row count", ln == n, f"local={ln:,} hdfs={n:,}")
        check("Local vs HDFS Silver: same columns", cols_equal)
        if cols_equal:
            cols = sorted(local.columns)
            a_minus_b = local.select(cols).exceptAll(silver.select(cols)).count()
            b_minus_a = silver.select(cols).exceptAll(local.select(cols)).count()
            check("Local vs HDFS Silver: identical rows (exceptAll both directions)",
                  a_minus_b == 0 and b_minus_a == 0, f"local-hdfs={a_minus_b}, hdfs-local={b_minus_a}")
            lines += ["", f"COMPARISON local({ln}) vs hdfs({n}): local-minus-hdfs={a_minus_b}, hdfs-minus-local={b_minus_a}"]
    else:
        check("Local Silver present for comparison", False, f"{a.local_silver} not found")
    (EVID / "08_spark_hdfs_checks.txt").write_text("\n".join(lines), encoding="utf-8")
    spark.stop()

    passed = sum(r["passed"] for r in results)
    summary = {"hdfs_uri": a.hdfs_uri, "passed": passed, "total": len(results), "checks": results,
               "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")}
    (EVID / "verification_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\n{passed}/{len(results)} checks passed -> {EVID}")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
