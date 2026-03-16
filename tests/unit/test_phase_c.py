from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from hearth.api.main import create_app


def test_phase_c_api_exposes_observations(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "phase-c-node"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = true
backend = "mock_process"
heartbeat_interval_sec = 1

[monitor]
watchdog_enabled = false

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
    with TestClient(app) as client:
        peers = client.get("/api/peers").json()
        routes = client.get("/api/routes").json()
        announces = client.get("/api/announces/recent").json()

    assert len(peers) >= 1
    assert len(routes) >= 1
    assert len(announces) >= 1
    assert peers[0]["interface_name"] == "tcp_backbone"
    assert routes[0]["via_interface"] == "tcp_backbone"
    assert announces[0]["via_interface"] == "tcp_backbone"


def test_dashboard_and_logs_pages_render(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "phase-c-ui"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = true
backend = "mock_process"

[monitor]
watchdog_enabled = false

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
    with TestClient(app) as client:
        dashboard = client.get("/")
        logs_page = client.get("/logs")

    assert dashboard.status_code == 200
    assert "最近节点" in dashboard.text
    assert "最近广播" in dashboard.text
    assert logs_page.status_code == 200
    assert "日志列表" in logs_page.text
