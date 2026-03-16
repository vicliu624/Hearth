from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import hashlib
import json
from pathlib import Path
import threading

from fastapi.testclient import TestClient

from hearth.api.main import create_app
from hearth.crypto.ed25519 import public_key_from_seed, sign
from hearth.api.security import classify_client_host, is_client_host_allowed
from hearth.reticulum.adapter import PathEntry


TEST_SOURCE_SEED = bytes.fromhex("1f" * 32)


class _AlertWebhookHandler(BaseHTTPRequestHandler):
    deliveries: list[dict] = []

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        self.__class__.deliveries.append(json.loads(body))
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


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


def test_node_status_endpoint(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "api-node"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = true

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
        response = client.get("/api/node/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["node_name"] == "api-node"
    assert payload["runtime_status"] == "running"
    assert payload["interface_summary"]["total"] == 1


def test_dashboard_supports_english_locale(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "i18n-node"
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

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        response = client.get("/?lang=en")

    assert response.status_code == 200
    assert "Dashboard" in response.text
    assert client.cookies.get("hearth_lang") == "en"


def test_admin_routes_require_token(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "secure-node"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = false

[monitor]
watchdog_enabled = false

[security]
admin_token = "api-secret"
""".strip(),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        unauthorized = client.post("/api/node/start")
        authorized = client.post("/api/node/start", headers={"X-Hearth-Token": "api-secret"})

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    assert authorized.json()["runtime_status"] == "running"


def test_security_headers_present(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "headers-node"
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

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_network_access_helpers() -> None:
    assert classify_client_host("127.0.0.1") == "loopback"
    assert classify_client_host("192.168.50.10") == "lan"
    assert classify_client_host("8.8.8.8") == "public"

    assert is_client_host_allowed("127.0.0.1", allow_lan=False, allow_wan=False) is True
    assert is_client_host_allowed("192.168.50.10", allow_lan=True, allow_wan=False) is True
    assert is_client_host_allowed("192.168.50.10", allow_lan=False, allow_wan=False) is False
    assert is_client_host_allowed("8.8.8.8", allow_lan=True, allow_wan=False) is False
    assert is_client_host_allowed("8.8.8.8", allow_lan=True, allow_wan=True) is True


def test_route_and_announce_detail_endpoints(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "detail-api-node"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = true

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
        routes_payload = client.get("/api/routes").json()
        announces_payload = client.get("/api/announces").json()
        route_detail = client.get(f"/api/routes/{routes_payload[0]['destination_hash']}")
        announce_detail = client.get(f"/api/announces/{announces_payload[0]['id']}")

    assert route_detail.status_code == 200
    assert route_detail.json()["destination_hash"] == routes_payload[0]["destination_hash"]
    assert announce_detail.status_code == 200
    assert announce_detail.json()["id"] == announces_payload[0]["id"]



def test_metrics_and_audit_endpoints(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "metrics-node"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = true

[monitor]
watchdog_enabled = false

[security]
admin_token = "metrics-secret"

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
        metrics_response = client.get("/metrics")
        audit_response = client.get("/api/audit?token=metrics-secret&search=node")

    assert metrics_response.status_code == 200
    assert metrics_response.headers["content-type"].startswith("text/plain; version=0.0.4")
    assert "hearth_runtime_up" in metrics_response.text
    assert "hearth_interface_rx_packets_total" in metrics_response.text
    assert audit_response.status_code == 200
    payload = audit_response.json()
    assert any(item["event_type"].startswith("node.") for item in payload)


def test_security_and_maintenance_endpoints(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "security-node"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = true

[monitor]
watchdog_enabled = false

[security]
admin_token = "security-secret"

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
        created_user = client.post(
            "/api/security/users",
            headers={"X-Hearth-Token": "security-secret"},
            json={"username": "alice", "display_name": "Alice", "role": "operator"},
        )
        created_token = client.post(
            "/api/security/tokens",
            headers={"X-Hearth-Token": "security-secret"},
            json={"token_name": "alice-ops", "owner_username": "alice", "role": "operator", "scopes": ["read", "operate"]},
        )
        roles_response = client.get("/api/security/roles", headers={"X-Hearth-Token": "security-secret"})
        maintenance_update = client.post(
            "/api/maintenance",
            headers={"X-Hearth-Token": "security-secret"},
            json={"enabled": True, "reason": "upgrade", "until_hours": 2},
        )
        issued_token = created_token.json()["token"]
        maintenance_state = client.get("/api/maintenance", headers={"X-Hearth-Token": issued_token})

    assert created_user.status_code == 200
    assert created_user.json()["username"] == "alice"
    assert created_token.status_code == 200
    assert created_token.json()["token_name"] == "alice-ops"
    assert created_token.json()["token"].startswith("htk_")
    assert roles_response.status_code == 200
    assert any(item["name"] == "owner" for item in roles_response.json())
    assert maintenance_update.status_code == 200
    assert maintenance_update.json()["enabled"] is True
    assert maintenance_state.status_code == 200
    assert maintenance_state.json()["enabled"] is True



def test_plugin_and_service_endpoints(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    source_manifest = tmp_path / "community-mirror.json"
    source_payload, source_public_key, source_digest = _build_signed_source_manifest(
        "Community Mirror",
        "Shared mirror of community plugins.",
        ["matrix_bridge", "mqtt_bridge", "mesh_bridge"],
    )
    source_manifest.write_text(json.dumps(source_payload), encoding="utf-8")
    config_path.write_text(
        f"""
[system]
node_name = "plugin-api-node"
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
admin_token = "plugin-secret"

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
config = {{ channel = "alpha", mode = "hybrid" }}

[[plugins]]
name = "metrics_exporter"
enabled = false
version = "0.4.0"
type = "monitor"
source = "local"
compatibility = "hearth-1.x"
description = "Exports metrics"
permissions = ["read"]
config = {{ format = "prometheus" }}

[[plugin_sources]]
name = "community_mirror"
index_url = "{source_manifest.as_uri()}"
label = "Community Mirror"
description = "Configured mirror"
public_key = "{source_public_key}"
signature_algorithm = "ed25519"
signature_required = true
""".strip(),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        plugins_response = client.get("/api/plugins", headers={"X-Hearth-Token": "plugin-secret"})
        sources_response = client.get("/api/plugins/sources", headers={"X-Hearth-Token": "plugin-secret"})
        refresh_sources_response = client.post(
            "/api/plugins/sources/refresh",
            headers={"X-Hearth-Token": "plugin-secret"},
        )
        plugin_detail = client.get("/api/plugins/matrix_bridge", headers={"X-Hearth-Token": "plugin-secret"})
        plugin_update = client.post(
            "/api/plugins/metrics_exporter",
            headers={"X-Hearth-Token": "plugin-secret"},
            json={"enabled": True},
        )
        services_response = client.get("/api/services", headers={"X-Hearth-Token": "plugin-secret"})
        service_detail = client.get("/api/services/reticulum_runtime", headers={"X-Hearth-Token": "plugin-secret"})
        service_action = client.post(
            "/api/services/observation_sync",
            headers={"X-Hearth-Token": "plugin-secret"},
            json={"action": "sync"},
        )
        missing_service = client.post(
            "/api/services/not-real",
            headers={"X-Hearth-Token": "plugin-secret"},
            json={"action": "sync"},
        )

    assert plugins_response.status_code == 200
    assert any(item["name"] == "matrix_bridge" for item in plugins_response.json())
    assert sources_response.status_code == 200
    assert any(item["source"] == "community" for item in sources_response.json())
    assert any(item["source"] == "community_mirror" for item in sources_response.json())
    assert any("available_count" in item and "index_url" in item for item in sources_response.json())
    assert refresh_sources_response.status_code == 200
    assert refresh_sources_response.json()["refreshed"] is True
    assert Path(refresh_sources_response.json()["index_path"]).exists()
    assert refresh_sources_response.json()["source_count"] >= 3
    mirror_source = next(item for item in refresh_sources_response.json()["sources"] if item["source"] == "community_mirror")
    assert mirror_source["available_count"] == 3
    assert mirror_source["sync_state"] == "ready"
    assert mirror_source["sync_error"] is None
    assert mirror_source["signature_status"] == "verified"
    assert mirror_source["signature_algorithm"] == "ed25519"
    assert mirror_source["public_key"] == source_public_key
    assert mirror_source["trusted_source"] is True
    assert mirror_source["manifest_sha256"] == source_digest
    assert plugin_detail.status_code == 200
    assert plugin_detail.json()["diagnostics"]["dependency_count"] == 1
    assert plugin_update.status_code == 200
    assert plugin_update.json()["enabled"] is True
    assert services_response.status_code == 200
    assert any(item["name"] == "reticulum_runtime" for item in services_response.json())
    assert service_detail.status_code == 200
    assert "resource_summary" in service_detail.json()
    assert service_action.status_code == 200
    assert service_action.json()["action"] == "sync"
    assert missing_service.status_code == 404


def test_rbac_limits_security_and_operation_access(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "rbac-node"
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
admin_token = "rbac-secret"
""".strip(),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        client.post(
            "/api/security/users",
            headers={"X-Hearth-Token": "rbac-secret"},
            json={"username": "viewer_user", "display_name": "Viewer", "role": "viewer"},
        )
        client.post(
            "/api/security/users",
            headers={"X-Hearth-Token": "rbac-secret"},
            json={"username": "ops_user", "display_name": "Ops", "role": "operator"},
        )
        viewer_token_response = client.post(
            "/api/security/tokens",
            headers={"X-Hearth-Token": "rbac-secret"},
            json={"token_name": "viewer-token", "owner_username": "viewer_user", "role": "viewer", "scopes": ["read"]},
        )
        operator_token_response = client.post(
            "/api/security/tokens",
            headers={"X-Hearth-Token": "rbac-secret"},
            json={"token_name": "ops-token", "owner_username": "ops_user", "role": "operator", "scopes": ["read", "operate"]},
        )

        viewer_token = viewer_token_response.json()["token"]
        operator_token = operator_token_response.json()["token"]

        viewer_start = client.post("/api/node/start", headers={"X-Hearth-Token": viewer_token})
        operator_start = client.post("/api/node/start", headers={"X-Hearth-Token": operator_token})
        operator_security = client.get("/api/security/users", headers={"X-Hearth-Token": operator_token})
        operator_maintenance = client.get("/api/maintenance", headers={"X-Hearth-Token": operator_token})

    assert viewer_start.status_code == 403
    assert operator_start.status_code == 200
    assert operator_security.status_code == 403
    assert operator_maintenance.status_code == 200



def test_fleet_and_config_revision_endpoints(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "fleet-node"
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
admin_token = "fleet-secret"
""".strip(),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        overview = client.get("/api/fleet/overview", headers={"X-Hearth-Token": "fleet-secret"})
        created_group = client.post(
            "/api/fleet/groups",
            headers={"X-Hearth-Token": "fleet-secret"},
            json={"name": "community-core", "description": "Main shared nodes", "group_type": "community"},
        )
        created_node = client.post(
            "/api/fleet/nodes",
            headers={"X-Hearth-Token": "fleet-secret"},
            json={
                "node_name": "relay-east",
                "group_name": "community-core",
                "tags": ["relay", "outdoor"],
                "version": "1.0.2",
                "health_status": "healthy",
                "runtime_status": "running",
                "uptime_seconds": 7200,
                "region": "east",
            },
        )
        created_template = client.post(
            "/api/fleet/templates",
            headers={"X-Hearth-Token": "fleet-secret"},
            json={
                "name": "community-default",
                "description": "Baseline community config",
                "template_text": "[reticulum]\nauto_start = true",
                "target_group": "community-core",
                "target_nodes": ["relay-east"],
            },
        )
        groups = client.get("/api/fleet/groups", headers={"X-Hearth-Token": "fleet-secret"})
        nodes = client.get("/api/fleet/nodes", headers={"X-Hearth-Token": "fleet-secret"})
        node_detail = client.get("/api/fleet/nodes/relay-east", headers={"X-Hearth-Token": "fleet-secret"})
        templates = client.get("/api/fleet/templates", headers={"X-Hearth-Token": "fleet-secret"})
        tags = client.get("/api/fleet/tags", headers={"X-Hearth-Token": "fleet-secret"})
        health = client.get("/api/fleet/health", headers={"X-Hearth-Token": "fleet-secret"})
        events = client.get("/api/fleet/events", headers={"X-Hearth-Token": "fleet-secret"})
        revisions_before = client.get("/api/config/revisions", headers={"X-Hearth-Token": "fleet-secret"})
        raw_config = client.get("/api/config/raw", headers={"X-Hearth-Token": "fleet-secret"}).json()["raw"]
        updated_raw = raw_config.replace('node_name = "fleet-node"', 'node_name = "fleet-node-v2"', 1)
        saved = client.post(
            "/api/config/save-raw",
            headers={"X-Hearth-Token": "fleet-secret"},
            json={"raw": updated_raw},
        )
        revisions_after = client.get("/api/config/revisions", headers={"X-Hearth-Token": "fleet-secret"})
        compare = client.get(
            f"/api/config/revisions/{revisions_after.json()[0]['id']}/compare",
            headers={"X-Hearth-Token": "fleet-secret"},
        )
        restored = client.post(
            f"/api/config/revisions/{revisions_after.json()[-1]['id']}/restore",
            headers={"X-Hearth-Token": "fleet-secret"},
        )
        raw_after_restore = client.get("/api/config/raw", headers={"X-Hearth-Token": "fleet-secret"})
        exported_backup = client.post(
            "/api/backup/export",
            headers={"X-Hearth-Token": "fleet-secret"},
            json={"destination_path": str(tmp_path / "fleet-backup.tar.gz")},
        )
        backup_detail = client.get(
            "/api/backup/detail",
            headers={"X-Hearth-Token": "fleet-secret"},
            params={"archive_path": str(tmp_path / "fleet-backup.tar.gz")},
        )

    assert overview.status_code == 200
    assert overview.json()["total_nodes"] >= 1
    assert created_group.status_code == 200
    assert created_group.json()["name"] == "community-core"
    assert created_node.status_code == 200
    assert created_node.json()["node_name"] == "relay-east"
    assert created_template.status_code == 200
    assert created_template.json()["name"] == "community-default"
    assert groups.status_code == 200
    assert any(item["name"] == "community-core" for item in groups.json())
    assert nodes.status_code == 200
    assert any(item["node_name"] == "relay-east" for item in nodes.json())
    assert node_detail.status_code == 200
    assert node_detail.json()["node_name"] == "relay-east"
    assert any(item["name"] == "community-default" for item in node_detail.json()["templates"])
    assert templates.status_code == 200
    assert any(item["name"] == "community-default" for item in templates.json())
    assert tags.status_code == 200
    assert any(item["name"] == "relay" for item in tags.json())
    assert health.status_code == 200
    assert health.json()["summary"]["total_nodes"] >= 1
    assert events.status_code == 200
    assert any(item["event_type"] == "fleet.node_saved" for item in events.json())
    assert revisions_before.status_code == 200
    assert len(revisions_before.json()) >= 1
    assert saved.status_code == 200
    assert saved.json()["saved"] is True
    assert revisions_after.status_code == 200
    assert len(revisions_after.json()) >= 2
    assert compare.status_code == 200
    assert compare.json()["changed"] in {True, False}
    assert "affected_modules" in compare.json()
    assert restored.status_code == 200
    assert restored.json()["restored"] is True
    assert raw_after_restore.status_code == 200
    assert 'node_name = "fleet-node"' in raw_after_restore.json()["raw"]
    assert exported_backup.status_code == 200
    assert backup_detail.status_code == 200
    assert backup_detail.json()["archive_name"] == "fleet-backup.tar.gz"
    assert "manifest.json" in backup_detail.json()["included"]



def test_bridge_alert_metrics_and_diagnostics_endpoints(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "observability-node"
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
admin_token = "change-me"
allow_wan = true

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
config = { server = "https://matrix.example", mode = "hybrid" }
""".strip(),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        bridges = client.get("/api/bridges", headers={"X-Hearth-Token": "change-me"})
        alerts = client.get("/api/alerts", headers={"X-Hearth-Token": "change-me"})
        metrics_summary = client.get("/api/metrics/summary", headers={"X-Hearth-Token": "change-me"})
        diagnostics = client.get("/api/diagnostics", headers={"X-Hearth-Token": "change-me"})

    assert bridges.status_code == 200
    assert any(item["name"] == "matrix_bridge" for item in bridges.json())
    assert alerts.status_code == 200
    assert alerts.json()["summary"]["total"] >= 1
    assert any(item["category"] == "security" for item in alerts.json()["alerts"])
    assert "history" in alerts.json()
    assert "hooks" in alerts.json()
    assert metrics_summary.status_code == 200
    assert metrics_summary.json()["node_name"] == "observability-node"
    assert metrics_summary.json()["interface_summary"]["total"] == 1
    assert diagnostics.status_code == 200
    assert diagnostics.json()["runtime"]["node_name"] == "observability-node"
    assert diagnostics.json()["config_revisions"]["count"] >= 1


def test_bridge_detail_and_controls(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    source_manifest = tmp_path / "community-source.json"
    source_payload, source_public_key, source_digest = _build_signed_source_manifest(
        "Community Source",
        "Signed bridge catalog.",
        ["matrix_bridge", "mqtt_bridge"],
    )
    source_manifest.write_text(json.dumps(source_payload), encoding="utf-8")
    config_path.write_text(
        f"""
[system]
node_name = "bridge-api-node"
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
admin_token = "bridge-secret"
allow_wan = true

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
config = {{ server = "https://matrix.example", mode = "hybrid" }}

[[plugin_sources]]
name = "community"
index_url = "{source_manifest.as_uri()}"
label = "Community Source"
public_key = "{source_public_key}"
signature_algorithm = "ed25519"
signature_required = true
""".strip(),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        detail = client.get("/api/bridges/matrix_bridge", headers={"X-Hearth-Token": "bridge-secret"})
        sync = client.post(
            "/api/bridges/matrix_bridge",
            headers={"X-Hearth-Token": "bridge-secret"},
            json={"action": "sync"},
        )
        test_delivery = client.post(
            "/api/bridges/matrix_bridge",
            headers={"X-Hearth-Token": "bridge-secret"},
            json={"action": "test_delivery"},
        )
        disable = client.post(
            "/api/bridges/matrix_bridge",
            headers={"X-Hearth-Token": "bridge-secret"},
            json={"action": "disable"},
        )
        updated_detail = client.get("/api/bridges/matrix_bridge", headers={"X-Hearth-Token": "bridge-secret"})

    assert detail.status_code == 200
    assert detail.json()["plugin_name"] == "matrix_bridge"
    assert detail.json()["actions"][0] == "disable"
    assert "test_delivery" in detail.json()["actions"]
    assert len(detail.json()["health_checks"]) >= 4
    assert sync.status_code == 200
    assert sync.json()["action"] == "sync"
    assert sync.json()["result"]["source"]["signature_status"] == "verified"
    assert sync.json()["result"]["source"]["signature_algorithm"] == "ed25519"
    assert sync.json()["result"]["source"]["public_key"] == source_public_key
    assert sync.json()["result"]["source"]["manifest_sha256"] == source_digest
    assert test_delivery.status_code == 200
    assert test_delivery.json()["action"] == "test_delivery"
    assert test_delivery.json()["result"]["mode"] == "simulated"
    assert disable.status_code == 200
    assert disable.json()["action"] == "disable"
    assert disable.json()["state"]["enabled"] is False
    assert updated_detail.status_code == 200
    assert any(item["action"] == "disable" for item in updated_detail.json()["recent_operations"])
    assert any(item["action"] == "test_delivery" for item in updated_detail.json()["recent_operations"])
    assert any(item["name"] == "source_trust" for item in updated_detail.json()["health_checks"])


def test_bridge_webhook_delivery_records_history(tmp_path: Path) -> None:
    _AlertWebhookHandler.deliveries = []
    server = HTTPServer(("127.0.0.1", 0), _AlertWebhookHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config_path = tmp_path / "hearth.toml"
        source_manifest = tmp_path / "community-webhook-source.json"
        source_payload, source_public_key, _ = _build_signed_source_manifest(
            "Webhook Source",
            "Signed webhook bridge catalog.",
            ["webhook_bridge"],
        )
        source_manifest.write_text(json.dumps(source_payload), encoding="utf-8")
        config_path.write_text(
            f"""
[system]
node_name = "bridge-webhook-node"
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
admin_token = "bridge-secret"
allow_wan = true

[[plugins]]
name = "webhook_bridge"
enabled = true
version = "1.2.0"
type = "bridge"
source = "community"
compatibility = "hearth-1.x"
description = "Webhook bridge"
permissions = ["read", "operate"]
depends_on = ["reticulum_runtime"]
config = {{ url = "http://127.0.0.1:{server.server_port}/bridge-test", mode = "relay" }}

[[plugin_sources]]
name = "community"
index_url = "{source_manifest.as_uri()}"
label = "Webhook Source"
public_key = "{source_public_key}"
signature_algorithm = "ed25519"
signature_required = true
""".strip(),
            encoding="utf-8",
        )

        app = create_app(settings_path=config_path)
        with TestClient(app) as client:
            client.post(
                "/api/bridges/webhook_bridge",
                headers={"X-Hearth-Token": "bridge-secret"},
                json={"action": "sync"},
            )
            delivery = client.post(
                "/api/bridges/webhook_bridge",
                headers={"X-Hearth-Token": "bridge-secret"},
                json={"action": "test_delivery"},
            )
            detail = client.get("/api/bridges/webhook_bridge", headers={"X-Hearth-Token": "bridge-secret"})
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert delivery.status_code == 200
    assert delivery.json()["action"] == "test_delivery"
    assert delivery.json()["result"]["transport"] == "webhook"
    assert delivery.json()["result"]["status_code"] == 200
    assert len(_AlertWebhookHandler.deliveries) == 1
    assert _AlertWebhookHandler.deliveries[0]["bridge"] == "webhook_bridge"
    assert detail.status_code == 200
    assert any(item["action"] == "test_delivery" for item in detail.json()["recent_operations"])
    assert any(item["name"] == "endpoint_configured" for item in detail.json()["health_checks"])


def test_alert_webhook_delivery_and_history(tmp_path: Path) -> None:
    _AlertWebhookHandler.deliveries = []
    server = HTTPServer(("127.0.0.1", 0), _AlertWebhookHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config_path = tmp_path / "hearth.toml"
        config_path.write_text(
            f"""
[system]
node_name = "alert-hook-node"
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
admin_token = "change-me"
allow_wan = true

[alerts]
webhook_enabled = true
webhook_url = "http://127.0.0.1:{server.server_port}/alerts"
include_resolved = true
delivery_timeout_sec = 3
sync_interval_sec = 60

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
            alerts = client.get("/api/alerts", headers={"X-Hearth-Token": "change-me"})
            history = client.get("/api/alerts/history", headers={"X-Hearth-Token": "change-me"})

        assert alerts.status_code == 200
        assert alerts.json()["hooks"]["enabled"] is True
        assert any(item["transition"] == "activated" for item in history.json()["history"])
        assert len(_AlertWebhookHandler.deliveries) >= 1
        assert any(item.get("transition") == "activated" for item in _AlertWebhookHandler.deliveries)
        assert any(row["event_type"] == "alert.hook_delivered" for row in history.json()["history"])
    finally:
        server.shutdown()
        server.server_close()



def test_topology_and_network_intelligence_endpoints(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "topology-node"
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
""".strip(),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        topology = client.get("/api/topology", headers={"X-Hearth-Token": "topology-secret"})
        network_map = client.get("/api/topology/network-map", headers={"X-Hearth-Token": "topology-secret"})
        heatmap = client.get("/api/topology/route-heatmap", headers={"X-Hearth-Token": "topology-secret"})
        critical_nodes = client.get("/api/topology/critical-nodes", headers={"X-Hearth-Token": "topology-secret"})
        insights = client.get("/api/topology/insights", headers={"X-Hearth-Token": "topology-secret"})

    assert topology.status_code == 200
    topology_payload = topology.json()
    assert topology_payload["overview"]["route_count"] >= 2
    assert topology_payload["overview"]["peer_count"] >= 2
    assert any(item["interface_name"] == "tcp_backbone" for item in topology_payload["segments"])
    assert network_map.status_code == 200
    assert len(network_map.json()["segments"]) >= 2
    assert heatmap.status_code == 200
    assert any(item["interface_name"] == "lan_bridge" for item in heatmap.json()["rows"])
    assert critical_nodes.status_code == 200
    assert len(critical_nodes.json()) >= 1
    assert insights.status_code == 200
    assert "score" in insights.json()
    assert len(insights.json()["findings"]) >= 1


def test_logs_timeline_and_path_changes_endpoints(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "timeline-node"
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
admin_token = "timeline-secret"

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

        context.adapter._paths = [
            PathEntry(
                destination_hash=initial_routes[0].destination_hash,
                via_interface="lan_bridge",
                next_hop="manual-hop",
                hop_count=4,
            )
        ]

        path_changes = client.get("/api/topology/path-changes", headers={"X-Hearth-Token": "timeline-secret"})
        timeline = client.get("/api/logs/timeline", headers={"X-Hearth-Token": "timeline-secret"})

    assert path_changes.status_code == 200
    path_payload = path_changes.json()
    assert path_payload["changed"] >= 1
    assert path_payload["removed"] >= 1
    assert any(item["destination_hash"] == initial_routes[0].destination_hash for item in path_payload["recent_changes"])

    assert timeline.status_code == 200
    timeline_payload = timeline.json()
    assert timeline_payload["total"] >= 1
    assert any(str(item["event_type"]).startswith("route.") for item in timeline_payload["events"])



def test_rollout_remote_logs_and_upgrade_endpoints(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "ops-node"
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
admin_token = "ops-secret"
""".strip(),
        encoding="utf-8",
    )

    app = create_app(settings_path=config_path)
    with TestClient(app) as client:
        client.post(
            "/api/fleet/groups",
            headers={"X-Hearth-Token": "ops-secret"},
            json={"name": "community-core", "description": "Main shared nodes", "group_type": "community"},
        )
        client.post(
            "/api/fleet/nodes",
            headers={"X-Hearth-Token": "ops-secret"},
            json={
                "node_name": "relay-east",
                "group_name": "community-core",
                "tags": ["relay", "outdoor"],
                "version": "1.0.2",
                "health_status": "healthy",
                "runtime_status": "running",
                "uptime_seconds": 7200,
                "region": "east",
            },
        )
        client.post(
            "/api/fleet/templates",
            headers={"X-Hearth-Token": "ops-secret"},
            json={
                "name": "community-default",
                "description": "Baseline community config",
                "template_text": "[reticulum]\nauto_start = true",
                "target_group": "community-core",
                "target_nodes": ["relay-east"],
            },
        )

        rollout = client.post(
            "/api/rollouts",
            headers={"X-Hearth-Token": "ops-secret"},
            json={"template_name": "community-default", "target_group": "community-core", "target_nodes": ["relay-east"]},
        )
        rollout_list = client.get("/api/rollouts", headers={"X-Hearth-Token": "ops-secret"})
        remote_logs = client.get("/api/remote-logs", headers={"X-Hearth-Token": "ops-secret"})
        upgrade = client.post(
            "/api/upgrades",
            headers={"X-Hearth-Token": "ops-secret"},
            json={"action": "upgrade", "target_version": "1.1.0", "channel": "beta", "enable_maintenance": True},
        )
        upgrades = client.get("/api/upgrades", headers={"X-Hearth-Token": "ops-secret"})

    assert rollout.status_code == 200
    assert rollout.json()["template_name"] == "community-default"
    assert rollout.json()["status"] == "planned"
    assert rollout_list.status_code == 200
    assert any(item["template_name"] == "community-default" for item in rollout_list.json())
    assert remote_logs.status_code == 200
    assert any(item["node_name"] == "relay-east" for item in remote_logs.json())
    assert upgrade.status_code == 200
    assert upgrade.json()["target_version"] == "1.1.0"
    assert upgrade.json()["maintenance_enabled"] is True
    assert upgrades.status_code == 200
    assert len(upgrades.json()["operations"]) >= 1
    assert len(upgrades.json()["revisions"]) >= 1
