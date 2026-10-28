"""
FitPulse - storage-mode helpers (local Parquet vs. real HDFS)
=============================================================
Shared by etl/spark_etl.py and the HDFS verification scripts.

Storage mode is chosen explicitly (never inferred silently):
    --storage local|hdfs        (or env FITPULSE_STORAGE, default: local)
    --hdfs-uri hdfs://host:port (or env FITPULSE_HDFS_URI, required for hdfs mode)

In HDFS mode nothing falls back to local disk: if the NameNode cannot be
reached, `require_hdfs()` raises HdfsUnavailable and the caller must exit non-zero.
"""

import os
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlparse

LOCAL_RAW = "data/raw/fitpulse_raw.csv"
LOCAL_SILVER = "data/processed/fitpulse_silver"
HDFS_RAW = "/fitpulse/bronze/fitpulse_raw.csv"
HDFS_SILVER = "/fitpulse/silver"


class HdfsUnavailable(RuntimeError):
    pass


@dataclass
class StorageConfig:
    mode: str            # "local" | "hdfs"
    hdfs_uri: str        # "" in local mode
    input_path: str
    output_path: str

    def label(self) -> str:
        if self.mode == "hdfs":
            return f"HDFS ({self.hdfs_uri})"
        return "LOCAL filesystem (Parquet fallback - NOT HDFS)"


def _qualify(hdfs_uri: str, path: str) -> str:
    if "://" in path:
        return path
    return hdfs_uri.rstrip("/") + "/" + path.lstrip("/")


def resolve(storage=None, hdfs_uri=None, input_path=None, output_path=None) -> StorageConfig:
    mode = (storage or os.environ.get("FITPULSE_STORAGE") or "local").lower()
    if mode not in ("local", "hdfs"):
        raise ValueError(f"storage must be 'local' or 'hdfs', got {mode!r}")
    if mode == "local":
        # Explicit file:/// URIs: if HADOOP_CONF_DIR points at the HDFS config, a bare relative path would
        # otherwise resolve against hdfs://.../user/<name>/ and "local" mode would silently touch HDFS.
        return StorageConfig("local", "", local_uri(input_path or LOCAL_RAW), local_uri(output_path or LOCAL_SILVER))
    uri = hdfs_uri or os.environ.get("FITPULSE_HDFS_URI")
    if not uri:
        raise HdfsUnavailable(
            "HDFS mode selected but no HDFS URI given. Pass --hdfs-uri or set FITPULSE_HDFS_URI "
            "(run_fitpulse_hdfs.ps1 reads it from `hdfs getconf -confKey fs.defaultFS`).")
    return StorageConfig("hdfs", uri.rstrip("/"), _qualify(uri, input_path or HDFS_RAW),
                         _qualify(uri, output_path or HDFS_SILVER))


def require_hdfs(cfg: StorageConfig, timeout: float = 3.0) -> None:
    """Cheap TCP probe of the NameNode RPC endpoint before any Spark work starts."""
    if cfg.mode != "hdfs":
        return
    u = urlparse(cfg.hdfs_uri)
    if u.scheme != "hdfs" or not u.hostname:
        raise HdfsUnavailable(f"Not a valid hdfs:// URI: {cfg.hdfs_uri}")
    try:
        with socket.create_connection((u.hostname, u.port or 8020), timeout=timeout):
            pass
    except OSError as e:
        raise HdfsUnavailable(
            f"HDFS mode selected but the NameNode at {u.hostname}:{u.port or 8020} is unreachable ({e}). "
            "Start it with .\\start_hdfs.ps1. Refusing to fall back to local storage.") from e


def spark_hadoop_conf(cfg: StorageConfig) -> dict:
    """Extra Spark settings: fail fast (not minutes) if the NameNode drops mid-run."""
    if cfg.mode != "hdfs":
        return {"spark.hadoop.fs.defaultFS": "file:///"}
    return {
        "spark.hadoop.ipc.client.connect.max.retries": "2",
        "spark.hadoop.ipc.client.connect.max.retries.on.timeouts": "2",
        "spark.hadoop.ipc.client.connect.timeout": "5000",
    }


def _fs(spark, path: str):
    jvm = spark._jvm
    p = jvm.org.apache.hadoop.fs.Path(local_uri(path))   # no-op for hdfs:// / file:// URIs
    return p, p.getFileSystem(spark._jsc.hadoopConfiguration())


def path_exists(spark, path: str) -> bool:
    p, fs = _fs(spark, path)
    return bool(fs.exists(p))


def verify_hdfs_reachable(spark, cfg: StorageConfig) -> None:
    """Prove the Hadoop FileSystem behind the URI really is HDFS (DistributedFileSystem)."""
    if cfg.mode != "hdfs":
        return
    try:
        p, fs = _fs(spark, cfg.hdfs_uri + "/")
        fs.exists(p)
        impl = fs.getClass().getName()
    except Exception as e:  # py4j errors
        raise HdfsUnavailable(f"HDFS NameNode did not answer a FileSystem call: {e}") from e
    if "DistributedFileSystem" not in impl:
        raise HdfsUnavailable(f"{cfg.hdfs_uri} resolved to {impl}, not HDFS DistributedFileSystem.")
    print(f"      FileSystem implementation: {impl}")


def local_uri(path: str) -> str:
    """Spark/Hadoop-friendly absolute file: URI for a local path (used for staging in local mode)."""
    if "://" in path:
        return path
    return "file:///" + os.path.abspath(path).replace("\\", "/").lstrip("/")


def staged_replace(spark, staging: str, final: str) -> None:
    """Swap a fully-written staging directory into place.

    The old dataset is only removed after the new one is in position, so a failed
    write never destroys the previous Silver data (rename is atomic on HDFS).
    """
    sp, sfs = _fs(spark, staging)
    fp, ffs = _fs(spark, final)
    ffs.mkdirs(fp.getParent())
    backup = None
    if ffs.exists(fp):
        backup = spark._jvm.org.apache.hadoop.fs.Path(local_uri(final.rstrip("/")) + f".previous-{int(time.time())}")
        if not ffs.rename(fp, backup):
            raise RuntimeError(f"could not move existing {final} aside")
    if not sfs.rename(sp, fp):
        if backup is not None:
            ffs.rename(backup, fp)  # restore
        raise RuntimeError(f"could not move staged output {staging} -> {final}")
    if backup is not None:
        ffs.delete(backup, True)    # only the superseded copy, created by this run
