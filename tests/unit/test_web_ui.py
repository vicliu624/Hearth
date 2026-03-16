from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

from fastapi.testclient import TestClient

from hearth.api.main import create_app
from hearth.crypto.ed25519 import public_key_from_seed, sign
from hearth.web.views import build_activity_bars, build_traffic_snapshot, summarize_activity_history


TEST_SOURCE_SEED = bytes.fromhex("1f" * 32)


def _build_signed_source_manifest(label: str, description: str, plugins: list[str]) -> tuple[dict, str, str]:
    public_key = f"ed25519:{public_key_from_seed(TEST_SOURCE_SEED).hex()}"
    payload = {
        "label": label,
        "description": description,
        "plugins": [{"name": item} for item in plugins],
        "public_key": public_key,
        "signature_algorithm": "ed25519",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    payload["signature"] = f"ed25519:{sign(TEST_SOURCE_SEED, canonical).hex()}"
    return payload, public_key, digest


UI_CONFIG = """
[system]
node_name = "ui-node"
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
admin_token = "ui-secret"

[[interfaces]]
name = "tcp_backbone"
type = "tcp"
enabled = true
host = "127.0.0.1"
port = 4242
""".strip()


def test_ui_missing_pages_render(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        dashboard_page = client.get("/?lang=en")
        interfaces_page = client.get("/interfaces?lang=en")
        peers_page = client.get("/peers?lang=en")
        routes_page = client.get("/routes?lang=en")
        announces_page = client.get("/announces?lang=en")

    assert dashboard_page.status_code == 200
    assert "Recorded Traffic (Last 24 Hours)" in dashboard_page.text
    assert "RX Packets" in dashboard_page.text
    assert "TX Packets" in dashboard_page.text
    assert interfaces_page.status_code == 200
    assert "Interfaces" in interfaces_page.text
    assert "tcp_backbone" in interfaces_page.text
    assert peers_page.status_code == 200
    assert "Recent Peers" in peers_page.text
    assert routes_page.status_code == 200
    assert "Route Table" in routes_page.text
    assert announces_page.status_code == 200
    assert "Recent Announcements" in announces_page.text


def test_ui_interface_control_and_system_page(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        entry = client.get("/interfaces?lang=en&token=ui-secret")
        controlled = client.post("/interfaces/tcp_backbone/control", data={"action": "restart", "selected": "tcp_backbone"})
        system_page = client.get("/system")

    assert entry.status_code == 200
    assert client.cookies.get("hearth_token") == "ui-secret"
    assert controlled.status_code == 200
    assert "Interface restarted." in controlled.text
    assert system_page.status_code == 200
    assert "System Information" in system_page.text


def test_ui_config_and_backup_forms(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    raw_text = config_path.read_text(encoding="utf-8")
    with TestClient(app) as client:
        config_page = client.get("/config?lang=en&token=ui-secret")
        validated = client.post("/config", data={"action": "validate", "raw": raw_text})
        exported = client.post("/backup", data={"action": "export", "destination_path": str(tmp_path / "ui-backup.tar.gz")})
        backup_detail = client.get("/backup/detail", params={"lang": "en", "token": "ui-secret", "archive": str(tmp_path / "ui-backup.tar.gz")})

    assert config_page.status_code == 200
    assert "Config Editor" in config_page.text
    assert validated.status_code == 200
    assert "Configuration is valid." in validated.text
    assert exported.status_code == 200
    assert "Backup exported." in exported.text
    assert backup_detail.status_code == 200
    assert "Backup Detail" in backup_detail.text
    assert "ui-backup.tar.gz" in backup_detail.text
    assert (tmp_path / "ui-backup.tar.gz").exists()


def test_dashboard_activity_history_uses_recorded_samples() -> None:
    now = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
    history = summarize_activity_history(
        [
            {
                "interface_name": "tcp_backbone",
                "rx_packets": 10,
                "tx_packets": 4,
                "error_count": 0,
                "captured_at": (now - timedelta(hours=4)).isoformat(),
            },
            {
                "interface_name": "tcp_backbone",
                "rx_packets": 22,
                "tx_packets": 9,
                "error_count": 1,
                "captured_at": (now - timedelta(hours=2)).isoformat(),
            },
            {
                "interface_name": "tcp_backbone",
                "rx_packets": 40,
                "tx_packets": 15,
                "error_count": 1,
                "captured_at": now.isoformat(),
            },
        ],
        now=now,
    )

    bars = build_activity_bars(history)
    snapshot = build_traffic_snapshot(history)

    assert len(bars) == 12
    assert any(int(point["rx_height"]) > 0 for point in bars)
    assert snapshot["rx_packets"] == "30"
    assert snapshot["tx_packets"] == "11"
    assert snapshot["error_count"] == 1


def test_ui_interface_detail_health_and_login_pages(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        interface_detail = client.get("/interfaces/tcp_backbone?lang=en")
        health_page = client.get("/health?lang=en&token=ui-secret")
        login_page = client.get("/login?lang=en")

    assert interface_detail.status_code == 200
    assert "Interface Details" in interface_detail.text
    assert "tcp_backbone" in interface_detail.text
    assert health_page.status_code == 200
    assert "Health Score" in health_page.text
    assert "Restart History" in health_page.text
    assert login_page.status_code == 200
    assert "Admin Login" in login_page.text


def test_ui_login_sets_cookie_and_redirects(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        response = client.post(
            "/login?lang=en",
            data={"token": "ui-secret", "next": "/system"},
            follow_redirects=False,
        )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/system")
    assert response.cookies.get("hearth_token") == "ui-secret"


def test_ui_peer_route_and_announce_detail_pages(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        peers_payload = client.get("/api/peers").json()
        routes_payload = client.get("/api/routes").json()
        announces_payload = client.get("/api/announces").json()
        peer_page = client.get(f"/peers/{peers_payload[0]['peer_hash']}?lang=en")
        route_page = client.get(f"/routes/{routes_payload[0]['destination_hash']}?lang=en")
        announce_page = client.get(f"/announces/{announces_payload[0]['id']}?lang=en")

    assert peer_page.status_code == 200
    assert "Peer Details" in peer_page.text
    assert peers_payload[0]["peer_hash"] in peer_page.text
    assert route_page.status_code == 200
    assert "Current State" in route_page.text
    assert routes_payload[0]["destination_hash"] in route_page.text
    assert announce_page.status_code == 200
    assert "Announcement Details" in announce_page.text
    assert announces_payload[0]["source_hash"] in announce_page.text



def test_ui_profile_security_and_audit_pages(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        login_response = client.post(
            "/login?lang=en",
            data={"token": "ui-secret", "next": "/system"},
            follow_redirects=False,
        )
        profile_page = client.get("/profile?lang=en&token=ui-secret")
        security_page = client.get("/security?lang=en&token=ui-secret")
        audit_page = client.get("/audit?lang=en&token=ui-secret")
        metrics_response = client.get("/metrics")

    assert login_response.status_code == 303
    assert profile_page.status_code == 200
    assert "Current Identity" in profile_page.text
    assert "Security Posture" in profile_page.text
    assert security_page.status_code == 200
    assert "Access Policy" in security_page.text
    assert "Browser Protection" in security_page.text
    assert audit_page.status_code == 200
    assert "Filters" in audit_page.text
    assert "auth.login_succeeded" in audit_page.text
    assert metrics_response.status_code == 200
    assert "hearth_runtime_up" in metrics_response.text


def test_ui_maintenance_users_roles_and_tokens_pages(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        maintenance_page = client.get("/maintenance?lang=en&token=ui-secret")
        users_page = client.get("/users?lang=en&token=ui-secret")
        roles_page = client.get("/roles?lang=en&token=ui-secret")
        tokens_page = client.get("/tokens?lang=en&token=ui-secret")
        created_user = client.post(
            "/users?lang=en&token=ui-secret",
            data={"action": "create_user", "username": "alice", "display_name": "Alice", "role": "operator"},
        )
        created_token = client.post(
            "/tokens?lang=en&token=ui-secret",
            data={"action": "create_token", "token_name": "alice-ops", "owner_username": "alice", "role": "operator", "scopes": "read,operate", "expires_days": "0"},
        )
        issued_token = re.search(r"htk_[A-Za-z0-9_-]+", created_token.text)
        profile_with_new_token = client.get(f"/profile?lang=en&token={issued_token.group(0)}") if issued_token else None

    assert maintenance_page.status_code == 200
    assert "Maintenance" in maintenance_page.text
    assert users_page.status_code == 200
    assert "Create User" in users_page.text
    assert roles_page.status_code == 200
    assert "Owner" in roles_page.text
    assert tokens_page.status_code == 200
    assert "Create Token" in tokens_page.text
    assert created_user.status_code == 200
    assert "User created." in created_user.text
    assert created_token.status_code == 200
    assert "Copy and store it now." in created_token.text
    assert issued_token is not None
    assert profile_with_new_token is not None
    assert profile_with_new_token.status_code == 200
    assert "alice" in profile_with_new_token.text



PLUGIN_UI_CONFIG = """
[system]
node_name = "plugin-ui-node"
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
admin_token = "ui-secret"

[[interfaces]]
name = "tcp_backbone"
type = "tcp"
enabled = true
host = "127.0.0.1"
port = 4242

[[plugins]]
name = "matrix_bridge"
enabled = true
version = "1.2.0"
type = "bridge"
source = "community"
compatibility = "hearth-1.x"
description = "Matrix bridge"
permissions = ["read", "operate"]
depends_on = ["reticulum_runtime"]
config = { channel = "alpha", mode = "hybrid" }

[[plugins]]
name = "metrics_exporter"
enabled = false
version = "0.4.0"
type = "monitor"
source = "local"
compatibility = "hearth-1.x"
description = "Exports metrics"
permissions = ["read"]
config = { format = "prometheus" }
""".strip()


def test_ui_zh_locale_falls_back_from_corrupted_translations(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(PLUGIN_UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        plugins_page = client.get("/plugins?lang=zh-CN&token=ui-secret")
        profile_page = client.get("/profile?lang=zh-CN&token=ui-secret")

    assert plugins_page.status_code == 200
    assert "Hearth Plugins" in plugins_page.text
    assert profile_page.status_code == 200
    assert "Profile" in profile_page.text
    assert "????" not in plugins_page.text
    assert "????" not in profile_page.text


def test_ui_plugin_and_service_pages(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    source_manifest = tmp_path / "community-mirror.json"
    source_payload, source_public_key, source_digest = _build_signed_source_manifest(
        "Community Mirror",
        "Shared mirror of bridge plugins.",
        ["matrix_bridge", "mqtt_bridge", "mesh_bridge"],
    )
    source_manifest.write_text(json.dumps(source_payload), encoding="utf-8")
    config_path.write_text(
        PLUGIN_UI_CONFIG
        + f"""

[[plugin_sources]]
name = "community_mirror"
index_url = "{source_manifest.as_uri()}"
label = "Community Mirror"
description = "Configured mirror"
public_key = "{source_public_key}"
signature_algorithm = "ed25519"
signature_required = true
""",
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        plugins_page = client.get("/plugins?lang=en&token=ui-secret")
        plugin_sources_page = client.get("/plugin-sources?lang=en&token=ui-secret")
        plugin_sources_refresh = client.post("/plugin-sources?lang=en&token=ui-secret", data={"action": "refresh"})
        plugin_detail_page = client.get("/plugins/matrix_bridge?lang=en&token=ui-secret")
        plugin_toggle = client.post("/plugins/metrics_exporter?lang=en&token=ui-secret", data={"action": "enable"})
        services_page = client.get("/services?lang=en&token=ui-secret")
        service_detail_page = client.get("/services/reticulum_runtime?lang=en&token=ui-secret")
        service_action = client.post("/services/observation_sync?lang=en&token=ui-secret", data={"action": "sync"})
        missing_plugin = client.get("/plugins/not-real?lang=en&token=ui-secret")

    assert plugins_page.status_code == 200
    assert "Plugin Sources" in plugins_page.text
    assert "matrix_bridge" in plugins_page.text
    assert plugin_sources_page.status_code == 200
    assert "community" in plugin_sources_page.text
    assert "Community Mirror" in plugin_sources_page.text
    assert "Plugin Sources" in plugin_sources_page.text
    assert "Index URL" in plugin_sources_page.text
    assert "Available Plugins" in plugin_sources_page.text
    assert plugin_sources_refresh.status_code == 200
    assert "Plugin sources refreshed." in plugin_sources_refresh.text
    assert "Last Sync" in plugin_sources_refresh.text
    assert "plugin-sources-index.json" in plugin_sources_refresh.text
    assert "mesh_bridge" in plugin_sources_refresh.text
    assert "Signature Status" in plugin_sources_refresh.text
    assert "Signature Algorithm" in plugin_sources_refresh.text
    assert "Public Key" in plugin_sources_refresh.text
    assert "ed25519" in plugin_sources_refresh.text
    assert "Verified" in plugin_sources_refresh.text
    assert plugin_detail_page.status_code == 200
    assert "Dependencies" in plugin_detail_page.text
    assert "Diagnostics" in plugin_detail_page.text
    assert plugin_toggle.status_code == 200
    assert "Plugin state updated." in plugin_toggle.text
    assert services_page.status_code == 200
    assert "Resource Summary" in services_page.text
    assert service_detail_page.status_code == 200
    assert "Health Checks" in service_detail_page.text
    assert "Recent Logs" in service_detail_page.text
    assert service_action.status_code == 200
    assert "Service action completed." in service_action.text
    assert missing_plugin.status_code == 404
    assert "requested plugin was not found" in missing_plugin.text



def test_ui_fleet_pages_and_config_revisions(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    original_raw = config_path.read_text(encoding="utf-8")
    updated_raw = original_raw.replace('node_name = "ui-node"', 'node_name = "ui-node-v2"', 1)
    with TestClient(app) as client:
        context = app.state.context
        fleet_page = client.get("/fleet?lang=en&token=ui-secret")
        groups_post = client.post(
            "/fleet/groups?lang=en&token=ui-secret",
            data={"action": "create_group", "name": "home-core", "description": "Home nodes", "group_type": "home"},
        )
        nodes_post = client.post(
            "/fleet/nodes?lang=en&token=ui-secret",
            data={
                "action": "register_node",
                "node_name": "relay-west",
                "group_name": "home-core",
                "tags": "relay,home",
                "version": "1.0.1",
                "health_status": "healthy",
                "runtime_status": "running",
                "region": "west",
            },
        )
        templates_post = client.post(
            "/fleet/templates?lang=en&token=ui-secret",
            data={
                "action": "create_template",
                "name": "home-default",
                "description": "Home baseline",
                "target_group": "home-core",
                "target_nodes": "relay-west",
                "template_text": "[reticulum]\nauto_start = true",
            },
        )
        inventory_page = client.get("/fleet/nodes?lang=en&token=ui-secret")
        node_detail_page = client.get("/fleet/nodes/relay-west?lang=en&token=ui-secret")
        groups_page = client.get("/fleet/groups?lang=en&token=ui-secret")
        templates_page = client.get("/fleet/templates?lang=en&token=ui-secret")
        tags_page = client.get("/fleet/tags?lang=en&token=ui-secret")
        health_page = client.get("/fleet/health?lang=en&token=ui-secret")
        events_page = client.get("/fleet/events?lang=en&token=ui-secret")
        api_docs_page = client.get("/api-docs?lang=en&token=ui-secret")
        config_saved = client.post("/config?lang=en&token=ui-secret", data={"action": "save", "raw": updated_raw})
        config_page = client.get("/config?lang=en&token=ui-secret")
        revisions = context.config_version_service.list_revisions(limit=10)
        baseline_revision_id = revisions[-1]["id"]
        config_history_page = client.get("/config/history?lang=en&token=ui-secret")
        config_review_page = client.get(f"/config/review/{baseline_revision_id}?lang=en&token=ui-secret")
        config_restore = client.post(f"/config/review/{baseline_revision_id}?lang=en&token=ui-secret")

    assert fleet_page.status_code == 200
    assert "Fleet Dashboard" in fleet_page.text
    assert groups_post.status_code == 200
    assert "Node group saved." in groups_post.text
    assert nodes_post.status_code == 200
    assert "Fleet inventory updated." in nodes_post.text
    assert templates_post.status_code == 200
    assert "Config template saved." in templates_post.text
    assert inventory_page.status_code == 200
    assert "Nodes Inventory" in inventory_page.text
    assert "relay-west" in inventory_page.text
    assert node_detail_page.status_code == 200
    assert "Node Detail" in node_detail_page.text
    assert "home-default" in node_detail_page.text
    assert groups_page.status_code == 200
    assert "Node Groups" in groups_page.text
    assert "home-core" in groups_page.text
    assert templates_page.status_code == 200
    assert "Templates" in templates_page.text
    assert "home-default" in templates_page.text
    assert tags_page.status_code == 200
    assert "Tags" in tags_page.text
    assert "relay" in tags_page.text
    assert health_page.status_code == 200
    assert "Fleet Health" in health_page.text
    assert events_page.status_code == 200
    assert "Fleet Events" in events_page.text
    assert "relay-west" in events_page.text
    assert api_docs_page.status_code == 200
    assert "Swagger UI" in api_docs_page.text
    assert "/openapi.json" in api_docs_page.text
    assert config_saved.status_code == 200
    assert "Configuration saved." in config_saved.text
    assert config_page.status_code == 200
    assert "Revision History" in config_page.text
    assert config_history_page.status_code == 200
    assert "Config History" in config_history_page.text
    assert config_review_page.status_code == 200
    assert "Config Review" in config_review_page.text
    assert config_restore.status_code == 200
    assert "Configuration revision restored." in config_restore.text



def test_ui_bridges_metrics_alerts_and_diagnostics_pages(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        PLUGIN_UI_CONFIG.replace('admin_token = "ui-secret"', 'admin_token = "change-me"\nallow_wan = true', 1),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        bridges_page = client.get("/bridges?lang=en&token=change-me")
        metrics_page = client.get("/metrics-dashboard?lang=en&token=change-me")
        alerts_page = client.get("/alerts?lang=en&token=change-me")
        diagnostics_page = client.get("/diagnostics?lang=en&token=change-me")

    assert bridges_page.status_code == 200
    assert "Bridge Services" in bridges_page.text
    assert "Matrix Bridge" in bridges_page.text
    assert metrics_page.status_code == 200
    assert "Metrics Dashboard" in metrics_page.text
    assert "Prometheus Endpoint" in metrics_page.text
    assert alerts_page.status_code == 200
    assert "Active Alerts" in alerts_page.text
    assert "Security Findings" in alerts_page.text
    assert "Hook Status" in alerts_page.text
    assert "Alert History" in alerts_page.text
    assert diagnostics_page.status_code == 200
    assert "Developer Diagnostics" in diagnostics_page.text
    assert "Runtime Snapshot" in diagnostics_page.text



def test_ui_bridge_detail_and_controls(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    source_manifest = tmp_path / "community-source.json"
    source_payload, source_public_key, source_digest = _build_signed_source_manifest(
        "Community Source",
        "Signed bridge catalog.",
        ["matrix_bridge", "mqtt_bridge"],
    )
    source_manifest.write_text(json.dumps(source_payload), encoding="utf-8")
    config_path.write_text(
        PLUGIN_UI_CONFIG
        + f"""

[[plugin_sources]]
name = "community"
index_url = "{source_manifest.as_uri()}"
label = "Community Source"
public_key = "{source_public_key}"
signature_algorithm = "ed25519"
signature_required = true
""",
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        detail_page = client.get("/bridges/matrix_bridge?lang=en&token=ui-secret")
        sync_page = client.post("/bridges/matrix_bridge?lang=en&token=ui-secret", data={"action": "sync"})
        test_delivery_page = client.post("/bridges/matrix_bridge?lang=en&token=ui-secret", data={"action": "test_delivery"})
        disable_page = client.post("/bridges/matrix_bridge?lang=en&token=ui-secret", data={"action": "disable"})

    assert detail_page.status_code == 200
    assert "Bridge Details" in detail_page.text
    assert "Source Security" in detail_page.text
    assert "Health Checks" in detail_page.text
    assert "Recent Operations" in detail_page.text
    assert "Test Delivery" in detail_page.text
    assert "Disable Bridge" in detail_page.text
    assert sync_page.status_code == 200
    assert "Bridge action completed." in sync_page.text
    assert "Signature Status" in sync_page.text
    assert "Signature Algorithm" in sync_page.text
    assert "Public Key" in sync_page.text
    assert "Verified" in sync_page.text
    assert source_digest in sync_page.text
    assert test_delivery_page.status_code == 200
    assert "Bridge action completed." in test_delivery_page.text
    assert "simulated" in test_delivery_page.text
    assert disable_page.status_code == 200
    assert "Bridge action completed." in disable_page.text
    assert "Enable Bridge" in disable_page.text


TOPOLOGY_UI_CONFIG = """
[system]
node_name = "topology-ui-node"
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
admin_token = "topology-secret"

[[interfaces]]
name = "tcp_backbone"
type = "tcp"
enabled = true
host = "127.0.0.1"
port = 4242

[[interfaces]]
name = "lan_bridge"
type = "custom"
enabled = true
""".strip()


def test_ui_topology_pages(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(TOPOLOGY_UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        topology_page = client.get("/topology?lang=en&token=topology-secret")
        network_map_page = client.get("/network-map?lang=en&token=topology-secret")
        heatmap_page = client.get("/route-heatmap?lang=en&token=topology-secret")
        critical_nodes_page = client.get("/critical-nodes?lang=en&token=topology-secret")
        insights_page = client.get("/network-insights?lang=en&token=topology-secret")

    assert topology_page.status_code == 200
    assert "Network Topology" in topology_page.text
    assert "tcp_backbone" in topology_page.text
    assert network_map_page.status_code == 200
    assert "Network Map" in network_map_page.text
    assert "lan_bridge" in network_map_page.text
    assert heatmap_page.status_code == 200
    assert "Route Heatmap" in heatmap_page.text
    assert critical_nodes_page.status_code == 200
    assert "Critical Nodes" in critical_nodes_page.text
    assert insights_page.status_code == 200
    assert "Network Insights" in insights_page.text


def test_ui_timeline_and_path_changes_pages(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "timeline-ui-node"
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
admin_token = "ui-secret"

[[interfaces]]
name = "tcp_backbone"
type = "tcp"
enabled = true
host = "127.0.0.1"
port = 4242

[[interfaces]]
name = "lan_bridge"
type = "custom"
enabled = true
""".strip(),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        context = app.state.context
        initial_routes = list(context.adapter.get_paths())
        assert len(initial_routes) >= 2
        short_destination = initial_routes[0].destination_hash[:12] + "..."

        context.database.record_event(
            "route.changed",
            "route updated for test destination",
            severity="warning",
            source="observation_service",
            payload={
                "destination_hash": initial_routes[0].destination_hash,
                "change_type": "changed",
                "via_interface": "lan_bridge",
                "next_hop": "manual-hop",
                "hop_count": 5,
                "previous": initial_routes[0].to_dict(),
                "current": {
                    **initial_routes[0].to_dict(),
                    "via_interface": "lan_bridge",
                    "next_hop": "manual-hop",
                    "hop_count": 5,
                },
            },
        )
        context.database.record_event(
            "route.removed",
            "route removed for test destination",
            severity="warning",
            source="observation_service",
            payload={
                "destination_hash": initial_routes[1].destination_hash,
                "change_type": "removed",
                "previous": initial_routes[1].to_dict(),
            },
        )

        seed_page = client.get("/path-changes?lang=en&token=ui-secret")
        timeline_page = client.get("/timeline?lang=en&token=ui-secret")
        path_changes_page = client.get("/path-changes?lang=en&token=ui-secret")

    assert seed_page.status_code == 200
    assert timeline_page.status_code == 200
    assert "Event Timeline" in timeline_page.text
    assert "route.changed" in timeline_page.text or "route.removed" in timeline_page.text
    assert path_changes_page.status_code == 200
    assert "Path Changes" in path_changes_page.text
    assert "Volatility Score" in path_changes_page.text
    assert short_destination in path_changes_page.text



def test_ui_rollout_remote_logs_and_upgrade_pages(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(UI_CONFIG, encoding="utf-8")

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        client.post(
            "/fleet/groups?lang=en&token=ui-secret",
            data={"action": "create_group", "name": "home-core", "description": "Home nodes", "group_type": "home"},
        )
        client.post(
            "/fleet/nodes?lang=en&token=ui-secret",
            data={
                "action": "register_node",
                "node_name": "relay-west",
                "group_name": "home-core",
                "tags": "relay,home",
                "version": "1.0.1",
                "health_status": "healthy",
                "runtime_status": "running",
                "region": "west",
            },
        )
        client.post(
            "/fleet/templates?lang=en&token=ui-secret",
            data={
                "action": "create_template",
                "name": "home-default",
                "description": "Home baseline",
                "target_group": "home-core",
                "target_nodes": "relay-west",
                "template_text": "[reticulum]\nauto_start = true",
            },
        )
        rollout_page = client.get("/rollout?lang=en&token=ui-secret")
        rollout_post = client.post(
            "/rollout?lang=en&token=ui-secret",
            data={"action": "apply_template", "template_name": "home-default", "target_group": "home-core", "target_nodes": "relay-west"},
        )
        upgrade_page = client.get("/upgrade?lang=en&token=ui-secret")
        upgrade_post = client.post(
            "/upgrade?lang=en&token=ui-secret",
            data={"action": "upgrade", "target_version": "1.1.0", "channel": "beta", "enable_maintenance": "true"},
        )
        remote_logs_page = client.get("/remote-logs?lang=en&token=ui-secret")

    assert rollout_page.status_code == 200
    assert "Batch Actions" in rollout_page.text
    assert rollout_post.status_code == 200
    assert "Batch action recorded." in rollout_post.text
    assert "home-default" in rollout_post.text
    assert upgrade_page.status_code == 200
    assert "Schedule Operation" in upgrade_page.text
    assert upgrade_post.status_code == 200
    assert "Upgrade operation scheduled." in upgrade_post.text
    assert remote_logs_page.status_code == 200
    assert "Remote Logs" in remote_logs_page.text
    assert "relay-west" in remote_logs_page.text


def test_ui_phase_e_management_pages(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    source_manifest = tmp_path / "signed-catalog.json"
    source_payload, source_public_key, _ = _build_signed_source_manifest(
        "Signed Catalog",
        "Catalog for install and update UI tests.",
        ["mesh_bridge", "ops_exporter"],
    )
    source_manifest.write_text(json.dumps(source_payload), encoding="utf-8")
    config_path.write_text(
        UI_CONFIG
        + f"""

[[plugin_sources]]
name = "signed_catalog"
index_url = "{source_manifest.as_uri()}"
label = "Signed Catalog"
description = "UI test catalog"
public_key = "{source_public_key}"
signature_algorithm = "ed25519"
signature_required = true
""",
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        context = app.state.context
        context.remote_log_service.ingest_entries(
            node_name="remote-east",
            entries=[
                {
                    "event_type": "remote.test",
                    "severity": "warning",
                    "source": "agent",
                    "message": "remote event",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            ],
        )

        role_post = client.post(
            "/roles?lang=en&token=ui-secret",
            data={
                "action": "create_role",
                "name": "field_ops",
                "label": "Field Ops",
                "description": "Operate field nodes",
                "permissions": "read,operate,maintenance",
            },
        )
        plugin_catalog_detail = client.get("/plugins/mesh_bridge?lang=en&token=ui-secret")
        plugin_install = client.post("/plugins/mesh_bridge?lang=en&token=ui-secret", data={"action": "install", "enabled": "true"})
        plugin_update = client.post("/plugins/mesh_bridge?lang=en&token=ui-secret", data={"action": "update"})
        plugin_uninstall = client.post("/plugins/mesh_bridge?lang=en&token=ui-secret", data={"action": "uninstall"})
        snapshot_post = client.post("/backup?lang=en&token=ui-secret", data={"action": "snapshot"})
        prune_post = client.post("/backup?lang=en&token=ui-secret", data={"action": "prune", "keep": "1", "max_age_days": "30"})
        backup_page = client.get("/backup?lang=en&token=ui-secret")
        remote_logs_sync = client.post("/remote-logs?lang=en&token=ui-secret", data={"action": "sync", "limit": "20"})
        remote_logs_page = client.get("/remote-logs?lang=en&token=ui-secret")

    assert role_post.status_code == 200
    assert "Role created." in role_post.text
    assert "field_ops" in role_post.text
    assert plugin_catalog_detail.status_code == 200
    assert "Install" in plugin_catalog_detail.text
    assert "Resolved Install Plan" in plugin_catalog_detail.text
    assert plugin_install.status_code == 200
    assert "Plugin installed." in plugin_install.text
    assert plugin_update.status_code == 200
    assert "Plugin updated from catalog." in plugin_update.text
    assert plugin_uninstall.status_code == 200
    assert "Plugin uninstalled." in plugin_uninstall.text
    assert snapshot_post.status_code == 200
    assert "Snapshot created." in snapshot_post.text
    assert prune_post.status_code == 200
    assert "Snapshots pruned." in prune_post.text
    assert backup_page.status_code == 200
    assert "Disaster Recovery Helper" in backup_page.text
    assert remote_logs_sync.status_code == 200
    assert "Remote log sync completed." in remote_logs_sync.text
    assert remote_logs_page.status_code == 200
    assert "Sync Remote Nodes" in remote_logs_page.text
    assert "remote-east" in remote_logs_page.text
