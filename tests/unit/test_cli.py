from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from hearth.cli.main import app


CLI_CONFIG = """
[system]
node_name = "cli-node"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = true
backend = "mock_process"

[monitor]
watchdog_enabled = false

[security]
admin_token = "cli-secret"
""".strip()


def test_cli_fleet_and_system_commands(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    template_path = tmp_path / "community.toml"
    config_path.write_text(CLI_CONFIG, encoding="utf-8")
    template_path.write_text("[reticulum]\nauto_start = true", encoding="utf-8")

    runner = CliRunner()

    create_group = runner.invoke(
        app,
        [
            "fleet",
            "create-group",
            "community-core",
            "--description",
            "Main shared nodes",
            "--group-type",
            "community",
            "--config",
            str(config_path),
        ],
    )
    register_node = runner.invoke(
        app,
        [
            "fleet",
            "register-node",
            "relay-east",
            "--group-name",
            "community-core",
            "--tags",
            "relay,outdoor",
            "--version",
            "1.0.2",
            "--health-status",
            "healthy",
            "--runtime-status",
            "running",
            "--uptime-seconds",
            "7200",
            "--region",
            "east",
            "--config",
            str(config_path),
        ],
    )
    create_template = runner.invoke(
        app,
        [
            "fleet",
            "create-template",
            "community-default",
            "--template-file",
            str(template_path),
            "--description",
            "Baseline community config",
            "--target-group",
            "community-core",
            "--target-nodes",
            "relay-east",
            "--config",
            str(config_path),
        ],
    )
    overview = runner.invoke(app, ["fleet", "overview", "--config", str(config_path)])
    node_detail = runner.invoke(app, ["fleet", "node", "relay-east", "--config", str(config_path)])
    tags = runner.invoke(app, ["fleet", "tags", "--config", str(config_path)])
    health = runner.invoke(app, ["fleet", "health", "--config", str(config_path)])
    events = runner.invoke(app, ["fleet", "events", "--limit", "20", "--config", str(config_path)])
    system_info = runner.invoke(app, ["system", "info", "--config", str(config_path)])
    system_security = runner.invoke(app, ["system", "security", "--config", str(config_path)])
    enable_maintenance = runner.invoke(
        app,
        ["system", "enable-maintenance", "--reason", "cli-test", "--config", str(config_path)],
    )
    maintenance_status = runner.invoke(app, ["system", "maintenance", "--config", str(config_path)])
    disable_maintenance = runner.invoke(app, ["system", "disable-maintenance", "--config", str(config_path)])

    assert create_group.exit_code == 0, create_group.stdout
    assert json.loads(create_group.stdout)["name"] == "community-core"
    assert register_node.exit_code == 0, register_node.stdout
    assert json.loads(register_node.stdout)["node_name"] == "relay-east"
    assert create_template.exit_code == 0, create_template.stdout
    assert json.loads(create_template.stdout)["name"] == "community-default"

    assert overview.exit_code == 0, overview.stdout
    assert json.loads(overview.stdout)["total_nodes"] >= 1
    assert node_detail.exit_code == 0, node_detail.stdout
    assert json.loads(node_detail.stdout)["node_name"] == "relay-east"
    assert tags.exit_code == 0, tags.stdout
    assert any(item["name"] == "relay" for item in json.loads(tags.stdout))
    assert health.exit_code == 0, health.stdout
    assert json.loads(health.stdout)["summary"]["total_nodes"] >= 1
    assert events.exit_code == 0, events.stdout
    assert any(item["event_type"] == "fleet.node_saved" for item in json.loads(events.stdout))

    assert system_info.exit_code == 0, system_info.stdout
    assert json.loads(system_info.stdout)["summary"]["node_name"] == "cli-node"
    assert system_security.exit_code == 0, system_security.stdout
    assert len(json.loads(system_security.stdout)["roles"]) >= 1
    assert enable_maintenance.exit_code == 0, enable_maintenance.stdout
    assert json.loads(enable_maintenance.stdout)["enabled"] is True
    assert maintenance_status.exit_code == 0, maintenance_status.stdout
    assert json.loads(maintenance_status.stdout)["enabled"] is True
    assert disable_maintenance.exit_code == 0, disable_maintenance.stdout
    assert json.loads(disable_maintenance.stdout)["enabled"] is False


def test_cli_deploy_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    bundle_dir = tmp_path / "deploy-bundle"

    systemd = runner.invoke(app, ["deploy", "systemd"])
    dockerfile = runner.invoke(app, ["deploy", "dockerfile"])
    compose = runner.invoke(app, ["deploy", "compose"])
    bundle = runner.invoke(app, ["deploy", "bundle", str(bundle_dir)])

    assert systemd.exit_code == 0, systemd.stdout
    assert "[Unit]" in systemd.stdout
    assert "ExecStart=" in systemd.stdout
    assert dockerfile.exit_code == 0, dockerfile.stdout
    assert "FROM python:3.12-slim" in dockerfile.stdout
    assert "EXPOSE 8480" in dockerfile.stdout
    assert "CMD [\"hearth-api\"]" in dockerfile.stdout
    assert compose.exit_code == 0, compose.stdout
    assert "services:" in compose.stdout
    assert '"8480:8480"' in compose.stdout
    assert "dockerfile: packaging/docker/Dockerfile" in compose.stdout
    assert bundle.exit_code == 0, bundle.stdout
    payload = json.loads(bundle.stdout)
    assert payload["count"] == 4
    for item in payload["written"]:
        assert Path(item).exists()
