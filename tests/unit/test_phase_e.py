from __future__ import annotations

import asyncio
from pathlib import Path

from hearth.core.lifecycle import build_context
from hearth.reticulum.config_bridge import RuntimeConfigBridge


def _write_config(path: Path, extra: str = "") -> Path:
    path.write_text(
        (
            """
[system]
node_name = "phase-e-node"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = false
backend = "mock_process"

[monitor]
watchdog_enabled = false

[security]
admin_token = "phase-e-secret"

[[interfaces]]
name = "local_lan"
type = "local"
enabled = true
role = "transport"
devices = ["eth0"]
discovery_port = 29716
data_port = 42671

[[interfaces]]
name = "tcp_backbone"
type = "tcp"
enabled = true
role = "uplink"
host = "backbone.example.org"
port = 4242

[[interfaces]]
name = "rnode_usb"
type = "rnode"
enabled = true
device = "/dev/ttyUSB0"
baudrate = 115200
""".strip()
            + ("\n\n" + extra.strip() if extra.strip() else "")
        ),
        encoding="utf-8",
    )
    return path


def test_runtime_config_bridge_renders_real_interfaces(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "hearth.toml")
    context = build_context(config_path)
    bridge = RuntimeConfigBridge(context.settings)
    rendered = bridge.render()

    assert "type = AutoInterface" in rendered
    assert "type = TCPClientInterface" in rendered
    assert "type = RNodeInterface" in rendered
    assert "enable_transport = yes" in rendered


def test_custom_roles_and_plugin_lifecycle(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "hearth.toml")

    async def scenario() -> None:
        context = build_context(config_path)
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        try:
            created_role = context.security_service.create_role(
                name="ops_auditor",
                label="Ops Auditor",
                description="Can read and inspect operations",
                permissions=["read", "operate"],
            )
            assert created_role["name"] == "ops_auditor"
            assert any(item["name"] == "ops_auditor" for item in context.security_service.list_roles())

            installed = context.plugin_service.install_plugin("matrix_bridge", enable=True)
            installed_names = [item["name"] for item in installed["plugins"]]
            assert "matrix_bridge" in installed_names
            assert "metrics_exporter" in installed_names

            updated = context.plugin_service.update_plugin("matrix_bridge", enable=False)
            assert updated["enabled"] is False

            removed = context.plugin_service.uninstall_plugin("matrix_bridge")
            assert "matrix_bridge" in removed["removed"]
        finally:
            await context.shutdown(stop_runtime=False)

    asyncio.run(scenario())


def test_backup_snapshots_and_remote_log_ingest(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path / "hearth.toml")

    async def scenario() -> None:
        context = build_context(config_path)
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        try:
            snapshot = context.backup_service.create_snapshot()
            assert snapshot["snapshot_created"] is True
            assert len(context.backup_service.list_snapshots()) >= 1

            ingest = context.remote_log_service.ingest_entries(
                node_name="remote-east",
                entries=[
                    {
                        "event_type": "remote.test",
                        "severity": "warning",
                        "source": "agent",
                        "message": "remote event",
                        "created_at": "2026-03-15T00:00:00+00:00",
                    }
                ],
            )
            assert ingest["ingested"] == 1

            entries = await context.remote_log_service.list_entries(node_name="remote-east", limit=20)
            assert any(item["node_name"] == "remote-east" for item in entries)

            dr = context.backup_service.disaster_recovery_helper()
            assert dr["selected_archive"] is not None
            assert len(dr["steps"]) >= 3
        finally:
            await context.shutdown(stop_runtime=False)

    asyncio.run(scenario())

