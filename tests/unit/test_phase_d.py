from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi.testclient import TestClient

from hearth.api.main import create_app
from hearth.core.lifecycle import build_context


def run(coro):
    return asyncio.run(coro)


def test_config_raw_validate_and_save(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "phase-d"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = false

[monitor]
watchdog_enabled = false

[security]
admin_token = "phase-d-secret"

[[interfaces]]
name = "tcp_backbone"
type = "tcp"
enabled = true
host = "127.0.0.1"
port = 4242
""".strip(),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    headers = {"X-Hearth-Token": "phase-d-secret"}
    with TestClient(app) as client:
        invalid = client.post(
            "/api/config/validate-raw",
            headers=headers,
            json={
                "raw": """
[system]
node_name = "bad"

[[interfaces]]
name = "dup"
type = "tcp"

[[interfaces]]
name = "dup"
type = "tcp"
""".strip()
            },
        )
        assert invalid.status_code == 200
        invalid_payload = invalid.json()
        assert invalid_payload["valid"] is False

        valid_text = config_path.read_text(encoding="utf-8").replace('node_name = "phase-d"', 'node_name = "phase-d-updated"')
        saved = client.post("/api/config/save-raw", headers=headers, json={"raw": valid_text})
        assert saved.status_code == 200
        saved_payload = saved.json()
        assert saved_payload["saved"] is True
        assert saved_payload["backup_path"] is not None

    assert 'node_name = "phase-d-updated"' in config_path.read_text(encoding="utf-8")


def test_backup_export_and_import(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "phase-d-backup"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = false

[monitor]
watchdog_enabled = false
""".strip(),
        encoding="utf-8",
    )

    context = build_context(config_path)
    run(context.startup(auto_start_runtime=False, enable_background_jobs=False))
    try:
        original_config = config_path.read_text(encoding="utf-8")
        original_identity = context.settings.identity_path.read_text(encoding="utf-8")

        archive_path = tmp_path / "backup.tar.gz"
        exported = context.backup_service.export(archive_path)
        assert exported["exported"] is True
        assert archive_path.exists()

        config_path.write_text(original_config.replace("phase-d-backup", "modified"), encoding="utf-8")
        context.settings.identity_path.write_text("modified-identity\n", encoding="utf-8")

        imported = context.backup_service.import_archive(archive_path)
        assert imported["imported"] is True
        assert imported["pre_restore_backup"]
    finally:
        run(context.shutdown(stop_runtime=False))

    assert config_path.read_text(encoding="utf-8") == original_config
    assert context.settings.identity_path.read_text(encoding="utf-8") == original_identity


def test_phase_d_pages_render(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "phase-d-pages"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = false

[monitor]
watchdog_enabled = false

[security]
admin_token = "phase-d-secret"
""".strip(),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        config_page = client.get("/config?token=phase-d-secret&lang=en")
        backup_page = client.get("/backup")

        assert client.cookies.get("hearth_token") == "phase-d-secret"
        assert client.cookies.get("hearth_lang") == "en"

    assert config_page.status_code == 200
    assert "Current config path" in config_page.text
    assert backup_page.status_code == 200
    assert "Backup Plan" in backup_page.text
