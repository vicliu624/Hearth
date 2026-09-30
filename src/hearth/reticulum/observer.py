"""Collect RPC observations without ever becoming the shared runtime owner."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def encode(value):
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    if (
        not (args.config / "config").is_file()
        or not (args.config / "storage" / "transport_identity").is_file()
    ):
        print(json.dumps({"error": "Runtime configuration and identity are not ready"}))
        return 2
    try:
        import RNS

        runtime = RNS.Reticulum(
            configdir=str(args.config), loglevel=-1, require_shared_instance=True
        )
        if not runtime.is_connected_to_shared_instance:
            raise RuntimeError(
                "Observer did not connect to an existing shared instance"
            )
        status = runtime.get_interface_stats()
        paths = runtime.get_path_table()
        print(json.dumps({"status": status, "paths": paths}, default=encode))
        return 0
    except Exception as error:
        print(json.dumps({"error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
