"""Benchmark warm HTTP pages against a disposable local-only node.

Use --real-runtime to include actual rnsd observations. Never reads or modifies
the installed node's config, data, or service. Requires the development extra.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path
import socket
import statistics
import sys
import tempfile
from time import perf_counter
from uuid import uuid4

from fastapi.testclient import TestClient
from hearth.api.main import create_app
from hearth.core.config import HearthSettings, dump_settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-runtime", action="store_true")
    parser.add_argument("--samples", type=int, default=20)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="hearth-benchmark-") as directory:
        root = Path(directory)
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        settings = HearthSettings.model_validate(
            {
                "system": {
                    "node_name": "benchmark-node",
                    "data_dir": str(root / "data"),
                },
                "reticulum": {
                    "backend": "managed_rnsd" if args.real_runtime else "mock_process",
                    "auto_start": True,
                    "config_path": str(root / "rns"),
                    "identity_path": str(root / "identity"),
                    "instance_name": "benchmark-" + uuid4().hex,
                    "managed_command": f"{sys.executable} -m RNS.Utilities.rnsd",
                },
                "monitor": {"watchdog_enabled": False},
                "security": {"admin_token": "benchmark-only"},
                "interfaces": [
                    {
                        "name": "loopback",
                        "type": "tcp",
                        "listen_ip": "127.0.0.1",
                        "listen_port": port,
                    }
                ],
            }
        )
        config = root / "hearth.toml"
        config.write_text(dump_settings(settings), encoding="utf-8")
        if args.real_runtime:
            from RNS import Identity

            identity = root / "rns" / "storage" / "transport_identity"
            identity.parent.mkdir(parents=True, exist_ok=True)
            Identity().to_file(str(identity))
        application = create_app(config)
        results = []
        try:
            with TestClient(application) as client:
                if args.real_runtime:

                    async def await_observation():
                        for _ in range(30):
                            state = await application.state.context.adapter.refresh()
                            if state.details.get("transport_id"):
                                return
                            await asyncio.sleep(0.1)
                        raise RuntimeError(
                            "Real runtime observations did not become available"
                        )

                    client.portal.call(await_observation)
                for path in (
                    "/",
                    "/interfaces",
                    "/routes",
                    "/health",
                    "/metrics-dashboard",
                    "/api/node/status",
                ):
                    timings = []
                    for index in range(args.samples + 1):
                        started = perf_counter()
                        response = client.get(
                            path,
                            params={"lang": "en"},
                            headers={"X-Hearth-Token": "benchmark-only"},
                        )
                        response.raise_for_status()
                        if index:
                            timings.append((perf_counter() - started) * 1000)
                    ordered = sorted(timings)
                    results.append(
                        {
                            "path": path,
                            "samples": len(timings),
                            "median_ms": round(statistics.median(timings), 2),
                            "p95_ms": round(
                                ordered[max(0, math.ceil(len(ordered) * 0.95) - 1)], 2
                            ),
                        }
                    )
        finally:
            asyncio.run(application.state.context.shutdown(stop_runtime=True))
            application.state.context.database.dispose()
        print(
            json.dumps({"real_runtime": args.real_runtime, "pages": results}, indent=2)
        )


if __name__ == "__main__":
    main()
