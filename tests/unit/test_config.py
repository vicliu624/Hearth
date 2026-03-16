from __future__ import annotations

from pathlib import Path

from hearth.core.config import load_settings


def test_load_settings_from_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "hearth.toml"
    config_path.write_text(
        """
[system]
node_name = "test-node"
data_dir = "./data"

[reticulum]
enabled = true
config_path = "./rns"
identity_path = "./identity"
auto_start = true

[[interfaces]]
name = "tcp_backbone"
type = "tcp"
enabled = true
""".strip(),
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.system.node_name == "test-node"
    assert settings.data_dir == (tmp_path / "data").resolve()
    assert settings.interfaces[0].type == "tcp"

