from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import sys
import time


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_state(
    state_file: Path,
    *,
    pid: int,
    restart_count: int,
    config_path: str,
    identity_path: str,
    status: str,
    started_at: str,
    heartbeat_at: str,
    last_exit_code: int | None = None,
    last_error: str | None = None,
) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "backend": "mock_process",
        "status": status,
        "pid": pid,
        "started_at": started_at,
        "heartbeat_at": heartbeat_at,
        "restart_count": restart_count,
        "last_exit_code": last_exit_code,
        "command": list(sys.argv),
        "config_path": config_path,
        "identity_path": identity_path,
        "last_error": last_error,
    }
    temp_file = state_file.with_suffix(state_file.suffix + ".tmp")
    temp_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_file.replace(state_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Hearth managed mock Reticulum runtime")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--heartbeat-interval", type=float, default=2.0)
    parser.add_argument("--restart-count", type=int, default=0)
    parser.add_argument("--config-path", required=True)
    parser.add_argument("--identity-path", required=True)
    args = parser.parse_args()

    state_file = Path(args.state_file)
    started_at = utcnow()
    running = True

    def handle_shutdown(signum, frame) -> None:  # type: ignore[override]
        nonlocal running
        running = False

    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_shutdown)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, handle_shutdown)

    pid = os.getpid()  # type: ignore[name-defined]
    try:
        while running:
            write_state(
                state_file,
                pid=pid,
                restart_count=args.restart_count,
                config_path=args.config_path,
                identity_path=args.identity_path,
                status="running",
                started_at=started_at,
                heartbeat_at=utcnow(),
            )
            time.sleep(max(args.heartbeat_interval, 0.2))
    except Exception as exc:
        write_state(
            state_file,
            pid=pid,
            restart_count=args.restart_count,
            config_path=args.config_path,
            identity_path=args.identity_path,
            status="crashed",
            started_at=started_at,
            heartbeat_at=utcnow(),
            last_exit_code=1,
            last_error=str(exc),
        )
        raise
    write_state(
        state_file,
        pid=pid,
        restart_count=args.restart_count,
        config_path=args.config_path,
        identity_path=args.identity_path,
        status="stopped",
        started_at=started_at,
        heartbeat_at=utcnow(),
        last_exit_code=0,
    )


if __name__ == "__main__":
    main()
