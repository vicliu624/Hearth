from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from hearth.core.config import load_settings
from hearth.core.lifecycle import build_context
from hearth.interfaces.tcp import TCPDriver
from hearth.reticulum.config_bridge import RuntimeConfigBridge
from hearth.reticulum.runtime import ManagedReticulumAdapter


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
    assert "enabled = yes" in rendered
    assert "instance_name = default" in rendered
    assert "discover_interfaces = no" in rendered
    assert "autoconnect_discovered_interfaces = 0" in rendered
    assert "[logging]" in rendered
    assert context.settings.runtime_managed_config_path.name == "config"


def test_tcp_driver_allows_server_mode_without_host() -> None:
    driver = TCPDriver(
        "public_tcp",
        {
            "enabled": True,
            "listen_ip": "0.0.0.0",
            "port": 4242,
            "discoverable": True,
        },
    )

    assert driver.validate_configuration() == []


def test_managed_adapter_reads_reticulum_runtime_observations(tmp_path: Path, monkeypatch) -> None:
    config_path = _write_config(tmp_path / "hearth.toml")
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'backend = "mock_process"',
            'backend = "managed_rnsd"\nmanaged_command = "python -m RNS.Utilities.rnsd"',
        ),
        encoding="utf-8",
    )

    settings = load_settings(config_path)
    settings.ensure_directories()
    adapter = ManagedReticulumAdapter(settings)
    adapter.set_interfaces([])
    settings.runtime_state_path.write_text(
        json.dumps(
            {
                "backend": "managed_rnsd",
                "status": "running",
                "pid": 12345,
                "started_at": "2026-04-02T00:00:00+00:00",
                "heartbeat_at": "2026-04-02T00:00:01+00:00",
                "command": ["python", "-m", "RNS.Utilities.rnsd"],
                "config_path": str(settings.reticulum_config_path),
                "identity_path": str(settings.identity_path),
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(adapter, "_is_pid_running", lambda pid: True)

    status_payload = {
        "interfaces": [
            {
                "name": "AutoInterface[WiFi LAN]",
                "short_name": "WiFi LAN",
                "type": "AutoInterface",
                "status": True,
                "rxb": 11,
                "txb": 22,
                "rxs": 1,
                "txs": 2,
                "announce_queue": 0,
                "held_announces": 0,
                "peers": 0,
                "bitrate": 10000000,
            },
            {
                "name": "TCPServerInterface[Public TCP/0.0.0.0:4242]",
                "short_name": "Public TCP",
                "type": "TCPServerInterface",
                "status": True,
                "rxb": 33,
                "txb": 44,
                "rxs": 3,
                "txs": 4,
                "announce_queue": 1,
                "held_announces": 2,
                "clients": 1,
                "bitrate": 10000000,
            },
        ],
        "transport_id": "abc123",
        "transport_uptime": 120,
    }
    path_payload = [
        {
            "hash": "deadbeefdeadbeef",
            "timestamp": 1775066952.1537547,
            "via": "cafebabecafebabe",
            "hops": 2,
            "expires": 1775671752.1537547,
            "interface": "TCPInterface[Bootstrap Beleth/rns.beleth.net:4242]",
        }
    ]

    def fake_run(command, **kwargs):
        joined = " ".join(command)
        if "RNS.Utilities.rnstatus" in joined:
            return SimpleNamespace(returncode=0, stdout=json.dumps(status_payload), stderr="")
        if "RNS.Utilities.rnpath" in joined:
            return SimpleNamespace(returncode=0, stdout=json.dumps(path_payload), stderr="")
        raise AssertionError(f"unexpected command: {command}")

    import hearth.reticulum.runtime as runtime_module

    monkeypatch.setattr(runtime_module.subprocess, "run", fake_run)

    status = asyncio.run(adapter.refresh())
    interfaces = adapter.get_interfaces()
    paths = adapter.get_paths()
    announces = adapter.get_announces()

    assert status.running is True
    assert status.uptime_seconds == 120
    assert status.details["transport_id"] == "abc123"
    assert {item.name for item in interfaces} == {"WiFi LAN", "Public TCP"}
    assert paths[0].destination_hash == "deadbeefdeadbeef"
    assert paths[0].via_interface == "Bootstrap Beleth"
    assert announces[0].source_hash == "deadbeefdeadbeef"
    assert announces[0].metadata["source_type"] == "path"


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

