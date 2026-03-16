from __future__ import annotations

import asyncio
from pathlib import Path

from hearth.core.lifecycle import build_context


def write_config(tmp_path: Path, *, interface_block: str = "", monitor_block: str = "") -> Path:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        f"""
[system]
node_name = "phase-b-node"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = false
backend = "mock_process"
heartbeat_interval_sec = 1
health_timeout_sec = 5
shutdown_timeout_sec = 2

[monitor]
watchdog_enabled = false
auto_restart_runtime = true
auto_restart_interface = true
restart_cooldown_sec = 0
{monitor_block}

{interface_block}
""".strip(),
        encoding="utf-8",
    )
    return config_path


def run(coro):
    return asyncio.run(coro)


def test_runtime_persists_across_contexts(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        interface_block="""
[[interfaces]]
name = "tcp_backbone"
type = "tcp"
enabled = true
host = "127.0.0.1"
port = 4242
""",
    )

    context = build_context(config_path)
    run(context.startup(auto_start_runtime=False, enable_background_jobs=False))
    try:
        summary = run(context.node_service.start(reason="test.runtime_persist"))
        assert summary["runtime_status"] == "running"
    finally:
        run(context.shutdown(stop_runtime=False))

    second_context = build_context(config_path)
    run(second_context.startup(auto_start_runtime=False, enable_background_jobs=False))
    try:
        summary = run(second_context.node_service.status_summary(persist=True))
        assert summary["runtime_status"] == "running"
        assert summary["runtime"]["pid"] is not None
    finally:
        run(second_context.shutdown(stop_runtime=True))


def test_watchdog_restarts_runtime(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        interface_block="""
[[interfaces]]
name = "tcp_backbone"
type = "tcp"
enabled = true
host = "127.0.0.1"
port = 4242
""",
    )

    context = build_context(config_path)
    run(context.startup(auto_start_runtime=False, enable_background_jobs=False))
    try:
        run(context.node_service.start(reason="test.watchdog.runtime"))
        run(context.adapter.stop())
        before = run(context.node_service.status_summary(persist=True))
        assert before["runtime_status"] == "stopped"

        run(context.watchdog.run_once())

        after = run(context.node_service.status_summary(persist=True))
        assert after["runtime_status"] == "running"
        assert any(entry["event_type"] == "watchdog.runtime_restart" for entry in context.log_service.list_entries())
    finally:
        run(context.shutdown(stop_runtime=True))


def test_watchdog_restarts_failed_interface(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        interface_block="""
[[interfaces]]
name = "faulty_custom"
type = "custom"
enabled = true
mock_fail_starts = 1
""",
    )

    context = build_context(config_path)
    run(context.startup(auto_start_runtime=False, enable_background_jobs=False))
    try:
        initial = run(context.node_service.start(reason="test.watchdog.interface"))
        faulty = next(item for item in initial["interfaces"] if item["name"] == "faulty_custom")
        assert faulty["status"] == "error"

        run(context.watchdog.run_once())

        recovered = run(context.node_service.status_summary(persist=True))
        recovered_interface = next(item for item in recovered["interfaces"] if item["name"] == "faulty_custom")
        assert recovered_interface["status"] == "running"
        assert any(entry["event_type"] == "watchdog.interface_restart" for entry in context.log_service.list_entries())
    finally:
        run(context.shutdown(stop_runtime=True))


def test_watchdog_pauses_during_maintenance(tmp_path: Path) -> None:
    config_path = write_config(
        tmp_path,
        interface_block="""
[[interfaces]]
name = "tcp_backbone"
type = "tcp"
enabled = true
host = "127.0.0.1"
port = 4242
""",
    )

    context = build_context(config_path)
    run(context.startup(auto_start_runtime=False, enable_background_jobs=False))
    try:
        run(context.node_service.start(reason="test.maintenance.watchdog"))
        run(context.adapter.stop())
        context.maintenance_service.enable(reason="upgrade", actor="test")

        run(context.watchdog.run_once())

        after = run(context.node_service.status_summary(persist=True))
        assert after["runtime_status"] == "stopped"
        assert after["maintenance"]["enabled"] is True
        assert not any(entry["event_type"] == "watchdog.runtime_restart" for entry in context.log_service.list_entries())
    finally:
        run(context.shutdown(stop_runtime=True))
