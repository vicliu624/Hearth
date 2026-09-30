"""Linux integration with an actual rnsd and a loopback TCP interface."""

import asyncio
import importlib.util
import socket
import sys
from uuid import uuid4

import pytest

from hearth.core.config import HearthSettings, dump_settings
from hearth.core.lifecycle import build_context


@pytest.mark.skipif(
    sys.platform == "win32" or importlib.util.find_spec("RNS") is None,
    reason="real rnsd integration runs on Linux with the reticulum extra",
)
def test_real_runtime_interface_control_and_web_lifecycle(tmp_path):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    payload = {
        "system": {"data_dir": str(tmp_path / "data")},
        "reticulum": {
            "backend": "managed_rnsd",
            "auto_start": False,
            "managed_command": f"{sys.executable} -m RNS.Utilities.rnsd",
            "config_path": str(tmp_path / "rns"),
            "identity_path": str(tmp_path / "identity"),
            "instance_name": f"hearth-test-{uuid4().hex}",
        },
        "monitor": {"watchdog_enabled": False},
        "interfaces": [
            {
                "name": "loopback",
                "type": "tcp",
                "listen_ip": "127.0.0.1",
                "listen_port": port,
            }
        ],
    }
    path = tmp_path / "hearth.toml"
    path.write_text(
        dump_settings(HearthSettings.model_validate(payload)), encoding="utf-8"
    )

    async def scenario():
        context = build_context(path)
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        try:
            await context.node_service.start()
            for _ in range(30):
                summary = await context.node_service.refresh_state()
                if summary["health_status"] == "healthy":
                    break
                await asyncio.sleep(0.1)
            assert summary["health_status"] == "healthy", summary
            assert summary["announce_count"] == 0
            insights = await context.topology_service.insights()
            assert insights["score"] is None
            assert any(
                item.get("code") == "peers_unavailable" for item in insights["findings"]
            )
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                pass
            stopped = await context.interface_service.stop("loopback")
            assert stopped["verified"]
            assert (await context.interface_service.get_interface("loopback"))[
                "status"
            ] == "stopped"
            with socket.socket() as probe:
                assert probe.connect_ex(("127.0.0.1", port)) != 0
            started = await context.interface_service.start("loopback")
            assert started["verified"]
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                pass
            pid = context.adapter.status().pid
            await context.shutdown(stop_runtime=False)
            assert context.adapter.status().pid == pid
            await context.node_service.stop()
            await context.watchdog.run_once()
            assert not context.adapter.status().running
            assert (
                "connected to another shared local instance"
                not in (context.settings.reticulum_config_path / "logfile").read_text()
            )
            identity = (
                context.settings.reticulum_config_path
                / "storage"
                / "transport_identity"
            )
            original_identity = identity.read_bytes()
            archive = context.backup_service.export(tmp_path / "real-backup.tar.gz")
            identity.write_bytes(b"test-only damaged identity")
            await context.restore_backup(archive["archive_path"])
            assert identity.read_bytes() == original_identity
            assert not context.adapter.status().running
        finally:
            await context.shutdown(stop_runtime=True)

    asyncio.run(scenario())
