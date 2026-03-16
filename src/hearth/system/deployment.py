from __future__ import annotations

import platform
from pathlib import Path
from textwrap import dedent

from hearth.core.config import HearthSettings


DEFAULT_SYSTEMD_USER = "hearth"
DEFAULT_SYSTEMD_GROUP = "hearth"
DEFAULT_SYSTEMD_WORKDIR = "/opt/hearth"
DEFAULT_SYSTEMD_CONFIG_PATH = "/etc/hearth/hearth.toml"
DEFAULT_SYSTEMD_EXEC_START = "/opt/hearth/.venv/bin/hearth-api"
DEFAULT_DOCKER_IMAGE = "hearth:latest"
DEFAULT_DOCKER_PYTHON_IMAGE = "python:3.12-slim"
DEFAULT_DOCKER_CONFIG_DIR = "/data"
DEFAULT_DOCKER_PORT = 8480


def render_debian_control(*, package_name: str = "hearth", version: str = "0.1.0") -> str:
    return dedent(
        f"""
        Source: {package_name}
        Section: net
        Priority: optional
        Maintainer: Hearth Contributors <opensource@example.invalid>
        Standards-Version: 4.7.0

        Package: {package_name}
        Architecture: all
        Depends: python3 (>= 3.12), python3-venv, systemd
        Description: Hearth personal Reticulum node controller
         Hearth packages runtime management, observability, recovery,
         configuration, and web administration for personal Reticulum nodes.
        Version: {version}
        """
    ).strip() + "\n"


def render_appliance_manifest(*, image_name: str = "hearth-appliance", version: str = "0.1.0") -> str:
    return dedent(
        f"""
        image: {image_name}
        version: {version}
        base: debian-bookworm
        packages:
          - python3
          - python3-venv
          - systemd
        services:
          - hearth.service
        volumes:
          - /var/lib/hearth
          - /etc/hearth
        ports:
          - 8480/tcp
        """
    ).strip() + "\n"


def render_openwrt_makefile(*, package_name: str = "hearth") -> str:
    return dedent(
        f"""
        include $(TOPDIR)/rules.mk

        PKG_NAME:={package_name}
        PKG_RELEASE:=1

        include $(INCLUDE_DIR)/package.mk

        define Package/{package_name}
          SECTION:=net
          CATEGORY:=Network
          TITLE:=Hearth Personal Reticulum Node
          DEPENDS:=+python3-light
        endef

        define Package/{package_name}/description
          Hearth runs and manages a personal Reticulum transport node.
        endef

        $(eval $(call BuildPackage,{package_name}))
        """
    ).strip() + "\n"


def render_migration_plan(*, from_version: str, to_version: str) -> str:
    return dedent(
        f"""
        from_version: {from_version}
        to_version: {to_version}
        steps:
          - Back up current configuration, database, and identity.
          - Verify runtime and plugin compatibility against the target version.
          - Stage deployment artifacts and enable maintenance mode.
          - Apply package or workspace upgrade.
          - Restart Hearth and verify health, interfaces, peers, and routes.
          - Keep the pre-upgrade backup until rollback is no longer needed.
        """
    ).strip() + "\n"


def preflight_check(settings: HearthSettings) -> dict[str, object]:
    config_path = settings.config_path
    checks = [
        {"name": "config_path", "ok": bool(config_path), "detail": str(config_path) if config_path else None},
        {"name": "data_dir", "ok": settings.data_dir.exists(), "detail": str(settings.data_dir)},
        {"name": "runtime_dir", "ok": settings.runtime_dir.exists(), "detail": str(settings.runtime_dir)},
        {"name": "reticulum_config_dir", "ok": settings.reticulum_config_path.exists(), "detail": str(settings.reticulum_config_path)},
        {"name": "identity_parent", "ok": settings.identity_path.parent.exists(), "detail": str(settings.identity_path.parent)},
        {"name": "python_version", "ok": tuple(map(int, platform.python_version_tuple()[:2])) >= (3, 12), "detail": platform.python_version()},
        {"name": "interfaces_configured", "ok": len(settings.interfaces) >= 1, "detail": len(settings.interfaces)},
    ]
    return {"ok": all(bool(item["ok"]) for item in checks), "checks": checks}


def render_systemd_service(
    *,
    user: str = DEFAULT_SYSTEMD_USER,
    group: str = DEFAULT_SYSTEMD_GROUP,
    workdir: str = DEFAULT_SYSTEMD_WORKDIR,
    config_path: str = DEFAULT_SYSTEMD_CONFIG_PATH,
    exec_start: str = DEFAULT_SYSTEMD_EXEC_START,
) -> str:
    return dedent(
        f"""
        [Unit]
        Description=Hearth Personal Reticulum Node
        After=network-online.target
        Wants=network-online.target

        [Service]
        Type=simple
        User={user}
        Group={group}
        WorkingDirectory={workdir}
        Environment=PYTHONUNBUFFERED=1
        Environment=HEARTH_CONFIG={config_path}
        ExecStart={exec_start}
        Restart=always
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
        """
    ).strip() + "\n"


def render_dockerfile(
    *,
    python_image: str = DEFAULT_DOCKER_PYTHON_IMAGE,
    config_dir: str = DEFAULT_DOCKER_CONFIG_DIR,
    expose_port: int = DEFAULT_DOCKER_PORT,
) -> str:
    return dedent(
        f"""
        FROM {python_image}

        ENV PYTHONUNBUFFERED=1 \
            HEARTH_CONFIG={config_dir}/hearth.toml

        WORKDIR /app

        COPY pyproject.toml README.md /app/
        COPY src /app/src

        RUN python -m pip install --upgrade pip && \
            pip install .

        EXPOSE {expose_port}
        VOLUME ["{config_dir}"]

        CMD ["hearth-api"]
        """
    ).strip() + "\n"


def render_docker_compose(
    *,
    image: str = DEFAULT_DOCKER_IMAGE,
    config_dir: str = DEFAULT_DOCKER_CONFIG_DIR,
    host_port: int = DEFAULT_DOCKER_PORT,
    container_port: int = DEFAULT_DOCKER_PORT,
) -> str:
    return dedent(
        f"""
        services:
          hearth:
            build:
              context: ../..
              dockerfile: packaging/docker/Dockerfile
            image: {image}
            container_name: hearth
            restart: unless-stopped
            ports:
              - "{host_port}:{container_port}"
            volumes:
              - ./data:{config_dir}
            environment:
              HEARTH_CONFIG: {config_dir}/hearth.toml
        """
    ).strip() + "\n"


def render_dockerignore() -> str:
    return dedent(
        """
        .git
        .github
        .pytest_cache
        .venv
        __pycache__
        *.pyc
        *.pyo
        *.pyd
        build
        dist
        data
        packaging/docker/data
        *.db
        *.sqlite
        *.sqlite3
        "."""
    ).strip() + "\n"


def write_bundle(directory: Path) -> list[str]:
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        directory / "hearth.service": render_systemd_service(),
        directory / "Dockerfile": render_dockerfile(),
        directory / "docker-compose.yml": render_docker_compose(),
        directory / ".dockerignore": render_dockerignore(),
    }
    written: list[str] = []
    for path, content in files.items():
        path.write_text(content, encoding="utf-8")
        written.append(str(path))
    return written
