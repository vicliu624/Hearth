from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from hearth.core.config import HearthSettings
from hearth.reticulum.adapter import InterfaceRuntimeInfo
from hearth.reticulum.runtime import ManagedReticulumAdapter, RuntimeFileState


def write_config(tmp_path):
    path = tmp_path / "hearth.toml"
    path.write_text(
        '[system]\ndata_dir = "./data"\n[reticulum]\nauto_start = false\n[monitor]\nwatchdog_enabled = false\n',
        encoding="utf-8",
    )
    return path


def test_alerts_do_not_alert_on_their_own_transitions(tmp_path):
    import asyncio
    from hearth.core.lifecycle import build_context

    context = build_context(write_config(tmp_path))

    async def scenario():
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        summary = await context.node_service.status_summary()
        for _ in range(6):
            await context.alert_service.refresh(summary)
        alerts = context.alert_service.build_alerts(summary)
        assert not any(item["title"].startswith("alert.") for item in alerts)
        events = context.database.list_events(limit=None)
        assert len(
            [item for item in events if item["event_type"] == "alert.activated"]
        ) == len(alerts)

    asyncio.run(scenario())


def test_unknown_real_topology_is_not_reported_as_failure(tmp_path):
    import asyncio
    from hearth.core.lifecycle import build_context

    context = build_context(write_config(tmp_path))

    async def scenario():
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        context.settings.reticulum.backend = "external_process"
        insights = await context.topology_service.insights()
        assert insights["score"] is None
        assert any(row["code"] == "peers_unavailable" for row in insights["findings"])
        assert not any(row["severity"] == "critical" for row in insights["findings"])

    asyncio.run(scenario())


def test_removed_interface_history_does_not_become_current_topology(tmp_path):
    import asyncio
    from hearth.core.lifecycle import build_context

    context = build_context(write_config(tmp_path))

    async def scenario():
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        context.database.upsert_interface_runtime(
            {
                "name": "removed",
                "type": "tcp",
                "enabled": True,
                "status": "running",
                "health_status": "healthy",
                "last_seen_at": None,
                "metrics": {},
            }
        )
        snapshot = await context.topology_service.snapshot()
        assert snapshot["overview"]["interface_count"] == 0
        assert "removed" in context.database.get_interface_runtimes()

    asyncio.run(scenario())


def test_interface_names_with_slashes_work_in_api_and_web(tmp_path):
    from fastapi.testclient import TestClient
    from hearth.api.main import create_app

    path = write_config(tmp_path)
    with path.open("a", encoding="utf-8") as config:
        config.write('\n[[interfaces]]\nname="mesh/child"\ntype="custom"\n')
    with TestClient(create_app(path)) as client:
        headers = {"X-Hearth-Token": "change-me"}
        assert client.post("/api/node/start", headers=headers).status_code == 200
        detail = client.get("/api/interfaces/mesh%2Fchild")
        assert detail.status_code == 200
        assert detail.json()["name"] == "mesh/child"
        assert client.get("/api/interfaces/mesh%2Fchild/metrics").status_code == 200
        assert client.get("/interfaces/mesh%2Fchild?lang=en").status_code == 200
        assert (
            client.post(
                "/api/interfaces/mesh%2Fchild/stop", headers=headers
            ).status_code
            == 200
        )


def real_adapter():
    settings = HearthSettings()
    settings.reticulum.backend = "external_process"
    adapter = ManagedReticulumAdapter(settings)
    adapter.set_interfaces(
        [
            InterfaceRuntimeInfo(
                name="uplink",
                type="tcp",
                enabled=True,
                status="running",
                health_status="healthy",
            )
        ]
    )
    return adapter


@pytest.mark.parametrize(
    "observation", [None, ([], [], [], {"observed_at": datetime.now(timezone.utc)})]
)
def test_real_observation_never_falls_back_to_mock(monkeypatch, observation):
    adapter = real_adapter()
    monkeypatch.setattr(adapter, "_load_real_observations", lambda: observation)
    monkeypatch.setattr(adapter, "_transport_identity_ready", lambda: True)
    adapter._rebuild_observations(RuntimeFileState(pid=os.getpid(), status="running"))
    assert adapter.get_paths() == []
    assert adapter.get_announces() == []
    assert adapter.get_interfaces() == []


def test_observers_do_not_initialize_an_unready_transport_identity(monkeypatch):
    adapter = real_adapter()
    monkeypatch.setattr(adapter, "_transport_identity_ready", lambda: False)

    def unsafe_probe():
        raise AssertionError(
            "Observer must not run before the daemon identity is ready"
        )

    monkeypatch.setattr(adapter, "_load_real_observations", unsafe_probe)
    adapter._rebuild_observations(RuntimeFileState(pid=os.getpid(), status="running"))
    assert adapter._observed_runtime["observation_status"] == "unavailable"


def test_path_snapshot_is_not_an_announce(monkeypatch):
    adapter = real_adapter()
    monkeypatch.setattr(
        adapter,
        "_run_json_command",
        lambda command, args: {
            "status": {"interfaces": []},
            "paths": [{"hash": "abcd", "interface": "uplink", "hops": 1}],
        },
    )
    interfaces, paths, announces, status = adapter._load_real_observations()
    assert len(paths) == 1
    assert announces == []


def test_browser_auth_flow_and_ui_permissions(tmp_path):
    import json
    import re
    from fastapi.testclient import TestClient
    from hearth.api.main import create_app

    app = create_app(write_config(tmp_path))
    with TestClient(app) as client:
        redirect = client.get(
            "/config", headers={"Accept": "text/html"}, follow_redirects=False
        )
        assert redirect.status_code == 303
        assert redirect.headers["location"].startswith("/login?")
        assert client.get("/api/config/status").status_code == 401
        token = app.state.context.security_service.create_api_token(
            token_name="read-only", owner_username=None, role="viewer"
        )
        headers = {"X-Hearth-Token": token["token"], "Accept": "text/html"}
        response = client.get("/", headers=headers)
        shell = json.loads(
            re.search(
                r'<script id="hearth-shell" type="application/json">(.*?)</script>',
                response.text,
                re.S,
            ).group(1)
        )
        assert shell["authenticated"] is True
        assert "operate" not in shell["permissions"]
        denied = client.get("/config", headers=headers)
        assert denied.status_code == 403
        assert "无权访问此页面" in denied.text
        denied_shell = json.loads(
            re.search(
                r'<script id="hearth-shell" type="application/json">(.*?)</script>',
                denied.text,
                re.S,
            ).group(1)
        )
        assert denied_shell["responseStatus"] == 403


def test_warm_pages_do_not_probe_runtime_or_write_observations(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from sqlalchemy import event
    from hearth.api.main import create_app
    from time import perf_counter

    app = create_app(write_config(tmp_path))
    with (tmp_path / "hearth.toml").open("a", encoding="utf-8") as config:
        config.write(
            '\n[[interfaces]]\nname="test-tcp"\ntype="tcp"\nhost="127.0.0.1"\nport=4242\n'
        )
    app = create_app(tmp_path / "hearth.toml")
    with TestClient(app) as client:
        context = app.state.context

        async def forbidden():
            raise AssertionError("page request must not collect live observations")

        monkeypatch.setattr(context.adapter, "refresh", forbidden)
        writes = []

        def track(conn, cursor, statement, parameters, ctx, many):
            if statement.lstrip().split()[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
                writes.append(statement)

        event.listen(context.database.engine, "before_cursor_execute", track)
        durations = []
        for path in ["/", "/interfaces", "/peers", "/routes", "/announces", "/login"]:
            start = perf_counter()
            response = client.get(path)
            durations.append(perf_counter() - start)
            assert response.status_code == 200
        assert writes == []
        assert max(durations) < 1.0


def test_concurrent_cold_status_collects_once(tmp_path, monkeypatch):
    import asyncio
    from hearth.core.lifecycle import build_context

    context = build_context(write_config(tmp_path))

    async def scenario():
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        context.node_service._summary = None
        original = context.adapter.refresh
        calls = 0

        async def slow_probe():
            nonlocal calls
            calls += 1
            await asyncio.sleep(0.02)
            return await original()

        monkeypatch.setattr(context.adapter, "refresh", slow_probe)
        await asyncio.gather(
            *(context.node_service.status_summary() for _ in range(10))
        )
        assert calls == 1

    asyncio.run(scenario())


def test_manual_stop_survives_watchdog_and_new_context(tmp_path):
    import asyncio
    from hearth.core.lifecycle import build_context

    path = write_config(tmp_path)

    async def scenario():
        context = build_context(path)
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        try:
            await context.node_service.start()
            await context.node_service.stop()
            await context.watchdog.run_once()
            assert not context.adapter.status().running
            other = build_context(path)
            await other.startup(auto_start_runtime=True, enable_background_jobs=False)
            assert other.adapter.desired_state() == "stopped"
            assert not other.adapter.status().running
        finally:
            await context.shutdown()

    asyncio.run(scenario())


def test_save_does_not_partially_apply_and_apply_rebuilds_services(tmp_path):
    import asyncio
    from hearth.core.lifecycle import build_context

    path = write_config(tmp_path)

    async def scenario():
        context = build_context(path)
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        old_monitor = context.watchdog.settings
        payload = context.settings.model_dump(mode="json", exclude_none=True)
        payload["monitor"]["restart_cooldown_sec"] = 47
        payload["system"]["node_name"] = "new-name"
        result = context.config_service.save(payload)
        assert result["applied"] is False
        assert context.settings.system.node_name != "new-name"
        assert context.watchdog.settings is old_monitor
        assert build_context(path).settings.system.node_name != "new-name"
        await context.apply_configuration()
        assert context.settings.system.node_name == "new-name"
        assert context.watchdog.settings is context.settings.monitor
        assert context.watchdog.settings.restart_cooldown_sec == 47
        assert not context.config_service.activation_status()["pending"]
        assert build_context(path).settings.system.node_name == "new-name"

    asyncio.run(scenario())


def test_failed_apply_keeps_active_configuration(tmp_path, monkeypatch):
    import asyncio
    from hearth.core.lifecycle import build_context, ApplicationContext

    path = write_config(tmp_path)

    async def scenario():
        context = build_context(path)
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        old_name = context.settings.system.node_name
        payload = context.settings.model_dump(mode="json", exclude_none=True)
        payload["system"]["node_name"] = "bad-candidate"
        context.config_service.save(payload)

        async def fail(*args, **kwargs):
            raise RuntimeError("activation failed")

        monkeypatch.setattr(ApplicationContext, "startup", fail)
        with pytest.raises(RuntimeError, match="activation failed"):
            await context.apply_configuration()
        assert context.settings.system.node_name == old_name
        assert build_context(path).settings.system.node_name == old_name

    asyncio.run(scenario())


def test_stale_controller_cannot_restart_with_old_configuration(tmp_path):
    import asyncio
    from hearth.core.lifecycle import build_context
    from hearth.core.operations import OperationBusy

    path = write_config(tmp_path)

    async def scenario():
        first, second = build_context(path), build_context(path)
        await first.startup(auto_start_runtime=False, enable_background_jobs=False)
        await second.startup(auto_start_runtime=False, enable_background_jobs=False)
        candidate = second.settings.model_dump(mode="json", exclude_none=True)
        candidate["reticulum"]["transport_enabled"] = False
        second.config_service.save(candidate)
        await second.apply_configuration()
        with pytest.raises(OperationBusy, match="configuration changed"):
            await first.node_service.start()
        assert not first.adapter.status().running
        await first.reload_active_configuration()
        assert first.settings.reticulum.transport_enabled is False

    asyncio.run(scenario())


def test_operation_lock_excludes_child_tasks_and_other_processes(tmp_path):
    import asyncio
    import subprocess
    import sys
    from hearth.core.operations import OperationLock, OperationBusy

    path = tmp_path / "op.lock"

    async def scenario():
        lock = OperationLock(path)
        async with lock.acquire():
            async with lock.acquire():
                pass

            async def contender():
                with pytest.raises(OperationBusy):
                    async with OperationLock(path).acquire(timeout=0):
                        pass

            await asyncio.create_task(contender())
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; from hearth.core.operations import OperationLock; import sys; "
                    "OperationLock(Path(sys.argv[1])).hold().__enter__()",
                    str(path),
                ],
                capture_output=True,
                env={
                    **os.environ,
                    "PYTHONPATH": str(
                        __import__("pathlib").Path(__file__).resolve().parents[2]
                        / "src"
                    ),
                },
            )
            assert result.returncode != 0
            assert b"OperationBusy" in result.stderr
        async with OperationLock(path).acquire(timeout=0):
            pass

    asyncio.run(scenario())


def test_backup_restores_wal_snapshot_and_rolls_back_write_failure(
    tmp_path, monkeypatch
):
    import asyncio
    import sqlite3
    from contextlib import closing
    from hearth.core.lifecycle import build_context
    import hearth.services.backup_service as module

    context = build_context(write_config(tmp_path))
    asyncio.run(context.startup(auto_start_runtime=False, enable_background_jobs=False))
    with closing(sqlite3.connect(context.settings.database_path)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE backup_probe (value TEXT)")
        db.execute("INSERT INTO backup_probe VALUES ('before')")
        db.commit()
        backup = context.backup_service.export(tmp_path / "snapshot.tar.gz")
        db.execute("UPDATE backup_probe SET value='after'")
        db.commit()
    original_config = context.settings.config_path.read_bytes()
    original_write = module.atomic_write
    failed = False

    def fail_identity(path, content):
        nonlocal failed
        if path == context.settings.identity_path and not failed:
            failed = True
            raise OSError("injected identity failure")
        return original_write(path, content)

    monkeypatch.setattr(module, "atomic_write", fail_identity)
    with pytest.raises(OSError, match="injected"):
        context.backup_service.import_archive(backup["archive_path"])
    assert context.settings.config_path.read_bytes() == original_config
    with closing(sqlite3.connect(context.settings.database_path)) as db:
        assert db.execute("SELECT value FROM backup_probe").fetchone()[0] == "after"
    context.backup_service.import_archive(backup["archive_path"])
    with closing(sqlite3.connect(context.settings.database_path)) as db:
        assert db.execute("SELECT value FROM backup_probe").fetchone()[0] == "before"


def test_restore_rolls_back_if_service_activation_fails(tmp_path, monkeypatch):
    import asyncio
    from hearth.core.lifecycle import build_context, ApplicationContext

    path = write_config(tmp_path)

    async def scenario():
        context = build_context(path)
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        archive = context.backup_service.export(tmp_path / "backup.tar.gz")
        identity = context.settings.identity_path
        identity.write_text("current identity", encoding="utf-8")

        async def fail_startup(*args, **kwargs):
            raise RuntimeError("injected service activation failure")

        monkeypatch.setattr(ApplicationContext, "startup", fail_startup)
        with pytest.raises(RuntimeError, match="activation failure"):
            await context.restore_backup(archive["archive_path"])
        assert identity.read_text(encoding="utf-8") == "current identity"
        assert not context.adapter.status().running

    asyncio.run(scenario())


def test_tcp_clients_keep_distinct_connection_names():
    adapter = object.__new__(ManagedReticulumAdapter)
    names = [
        adapter._normalize_interface_name(
            f"TCPInterface[Client on LAN TCP/192.0.2.1:{port}]", "Client on LAN TCP"
        )
        for port in (1001, 1002)
    ]
    assert names[0] != names[1]
    assert names[0].endswith("/192.0.2.1:1001")
    assert (
        adapter._normalize_interface_name("TCPInterface[Uplink/example:4242]", "Uplink")
        == "Uplink"
    )


def test_topology_branches_include_more_than_300_paths(tmp_path, monkeypatch):
    import asyncio
    from hearth.core.lifecycle import build_context

    context = build_context(write_config(tmp_path))

    async def scenario():
        await context.startup(auto_start_runtime=False, enable_background_jobs=False)
        routes = [
            {
                "destination_hash": f"{i:032x}",
                "via_interface": f"Client/{i % 2}",
                "next_hop": "abc",
                "hop_count": 3,
            }
            for i in range(650)
        ]

        async def list_routes(limit=100):
            return routes[:limit]

        monkeypatch.setattr(context.route_service, "list_routes", list_routes)
        snapshot = await context.topology_service.snapshot()
        assert snapshot["overview"]["route_count"] == 650
        assert len(snapshot["branches"]) == 2
        assert sum(b["count"] for b in snapshot["branches"]) == 650
        assert all(len(b["destinations"]) == 30 for b in snapshot["branches"])

    asyncio.run(scenario())
