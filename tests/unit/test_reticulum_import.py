from __future__ import annotations

from pathlib import Path

from hearth.core.config import HearthSettings
from hearth.reticulum.config_bridge import RuntimeConfigBridge
from hearth.system.reticulum_import import build_deployment_payload, parse_reticulum_config


def test_parse_reticulum_config_and_build_deployment_payload(tmp_path: Path) -> None:
    config_path = tmp_path / "reticulum" / "config"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
[reticulum]
  enable_transport = Yes
  share_instance = Yes
  instance_name = default
  discover_interfaces = Yes
  autoconnect_discovered_interfaces = 1

[logging]
  loglevel = 4

[interfaces]

  [[WiFi LAN]]
    type = AutoInterface
    enabled = yes
    devices = wlo1

  [[Public TCP]]
    type = TCPServerInterface
    enabled = yes
    listen_ip = 0.0.0.0
    listen_port = 4242
    discoverable = yes
    discovery_name = Vicliu Pi Gateway
    announce_interval = 720
    reachable_on = vicliu.i234.me
    latitude = 25.0389
    longitude = 102.7183
    height = 1891

  [[Home RNode]]
    type = RNodeInterface
    enabled = yes
    port = /dev/ttyACM0
    frequency = 491875000
    bandwidth = 125000
    txpower = 22
    spreadingfactor = 8
    codingrate = 5
    flow_control = False

  [[Bootstrap Beleth]]
    type = TCPClientInterface
    enabled = yes
    target_host = rns.beleth.net
    target_port = 4242
    bootstrap_only = yes
""".strip(),
        encoding="utf-8",
    )

    imported = parse_reticulum_config(config_path)

    assert imported.reticulum["enable_transport"] is True
    assert imported.reticulum["discover_interfaces"] is True
    assert imported.reticulum["autoconnect_discovered_interfaces"] == 1
    assert imported.logging["loglevel"] == 4
    assert [item["name"] for item in imported.interfaces] == [
        "WiFi LAN",
        "Public TCP",
        "Home RNode",
        "Bootstrap Beleth",
    ]
    assert imported.interfaces[0]["devices"] == "wlo1"

    payload = build_deployment_payload(
        data_dir=tmp_path / "data",
        host="0.0.0.0",
        port=8480,
        admin_token="secret-token",
        timezone="Asia/Shanghai",
        node_name="vicliu-gateway",
        backend="managed_rnsd",
        import_path=config_path,
        reticulum_config_dir=config_path.parent,
        identity_path=config_path.parent / "identity",
        managed_command="/home/vicliu/.local/reticulum-venv/bin/rnsd",
    )

    settings = HearthSettings.model_validate(payload)
    bridge = RuntimeConfigBridge(settings)
    rendered = bridge.render()

    assert settings.reticulum.backend == "managed_rnsd"
    assert settings.reticulum.managed_command == "/home/vicliu/.local/reticulum-venv/bin/rnsd"
    assert settings.reticulum.config_path == config_path.parent
    assert settings.reticulum.discover_interfaces is True
    assert settings.reticulum.autoconnect_discovered_interfaces == 1
    assert [item.type for item in settings.interfaces] == ["local", "tcp", "rnode", "tcp"]
    assert "type = AutoInterface" in rendered
    assert "type = TCPServerInterface" in rendered
    assert "reachable_on = vicliu.i234.me" in rendered
    assert "type = RNodeInterface" in rendered
    assert "port = /dev/ttyACM0" in rendered
    assert "type = TCPClientInterface" in rendered
    assert "bootstrap_only = yes" in rendered
