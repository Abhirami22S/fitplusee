# Local vs HDFS comparison (threshold: absolute difference > 0.001)

| experiment | metric rows compared | max abs diff (metrics) | metric rows differing > 1e-6 | flagged metric rows | feature-importance rows | max abs diff (importance) | flagged importance rows |
|---|---|---|---|---|---|---|---|
| E1 | 69 | 6.76e-05 | 10 | 0 | 36 | 0 | 0 |
| E2 | 75 | 7.94e-06 | 1 | 0 | 40 | 0 | 0 |
| E3 | 66 | 0 | 0 | 0 | 9 | 0 | 0 |
| E4 | 78 | 0 | 0 | 0 | 32 | 0 | 0 |
| E5 | 60 | 5.68e-14 | 0 | 0 | 20 | 0 | 0 |

Flagged rows in total: **0** (see local_vs_hdfs_flags.csv).

## Run settings and split sizes

| experiment | item | local | HDFS | flag |
|---|---|---|---|---|
| E1 | seed | 42 | 42 |  |
| E1 | storage_mode | local | hdfs |  |
| E2 | settings | {"rf": {"depth": 5}, "gbt": {"depth": 3, "iters": 50}, "logreg": {"reg": 0.0}} | {"rf": {"depth": 5}, "gbt": {"depth": 3, "iters": 50}, "logreg": {"reg": 0.0}} |  |
| E2 | seed | 42 | 42 |  |
| E2 | storage_mode | local | hdfs |  |
| E3 | seed | 42 | 42 |  |
| E3 | storage_mode | local | hdfs |  |
| E4 | rows | {"train": 71460, "validation": 16404, "test": 12258} | {"train": 71460, "validation": 16404, "test": 12258} |  |
| E4 | settings | {"rf": {"depth": 5}, "gbt": {"depth": 5, "iters": 100}, "logreg": {"reg": 0.01}} | {"rf": {"depth": 5}, "gbt": {"depth": 5, "iters": 100}, "logreg": {"reg": 0.01}} |  |
| E4 | seed | 42 | 42 |  |
| E4 | storage_mode | local | hdfs |  |
| E5 | rows | {"train": 70085, "validation": 15052, "test": 14985} | {"train": 70085, "validation": 15052, "test": 14985} |  |
| E5 | settings | {"linreg": {"reg": 0.0}, "rf": {"depth": 10}, "gbt": {"depth": 5, "iters": 100}} | {"linreg": {"reg": 0.0}, "rf": {"depth": 10}, "gbt": {"depth": 5, "iters": 100}} |  |
| E5 | seed | 42 | 42 |  |
| E5 | storage_mode | local | hdfs |  |
