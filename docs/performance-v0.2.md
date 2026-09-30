# v0.2 performance verification

Measured on 2026-09-30 on the same Linux host, with Python 3.13 and an actual
Reticulum 1.5.5 runtime using a disposable loopback TCP interface. Each route was
warmed once, then requested 20 times through FastAPI's HTTP test client.

The baseline is repository commit `9048470`, run with the same installed Python
dependencies. These numbers measure application request handling, not WAN latency,
browser rendering, or radio throughput. No production node data is used.

| Route | Baseline median | v0.2 median | v0.2 p95 |
| --- | ---: | ---: | ---: |
| `/` | 282.83 ms | 6.23 ms | 6.95 ms |
| `/interfaces` | 553.44 ms | 4.14 ms | 4.22 ms |
| `/routes` | 278.40 ms | 4.17 ms | 4.25 ms |
| `/health` | 278.41 ms | 5.38 ms | 5.49 ms |
| `/metrics-dashboard` | 279.88 ms | 6.35 ms | 6.41 ms |
| `/api/node/status` | 279.04 ms | 2.56 ms | 2.68 ms |

The main improvement comes from removing Reticulum command execution from warm
page requests. Background collection still runs at the configured interval, and
mutations explicitly collect and verify their results. Operational React pages
refresh their displayed snapshot every 15 seconds while visible.

Regression tests verify that warm pages do not call the runtime probe or write
observations, and that concurrent cold status requests share one collection.

Reproduce with the development and Reticulum extras installed:

```sh
python scripts/benchmark_pages.py --real-runtime --samples 20
```

The harness creates its own temporary configuration, data, identity, and loopback
port and shuts down its runtime afterwards. Do not substitute a production config.
