from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Awaitable, Callable

import typer
import uvicorn

from hearth.api.main import create_app
from hearth.core.config import load_settings
from hearth.core.lifecycle import ApplicationContext, build_context
from hearth.system.deployment import (
    preflight_check,
    render_appliance_manifest,
    render_debian_control,
    render_docker_compose,
    render_dockerfile,
    render_migration_plan,
    render_openwrt_makefile,
    render_systemd_service,
    write_bundle,
)


app = typer.Typer(help="Hearth CLI")
interfaces_app = typer.Typer(help="Manage interfaces")
peers_app = typer.Typer(help="Inspect peers")
routes_app = typer.Typer(help="Inspect routes")
announces_app = typer.Typer(help="Inspect announces")
logs_app = typer.Typer(help="Inspect logs")
config_app = typer.Typer(help="Inspect configuration")
backup_app = typer.Typer(help="Manage backups")
fleet_app = typer.Typer(help="Manage fleet inventory")
system_app = typer.Typer(help="Inspect system status and maintenance")
plugins_app = typer.Typer(help="Manage plugins")
services_app = typer.Typer(help="Manage services")
security_app = typer.Typer(help="Manage roles, users, and API tokens")
rollout_app = typer.Typer(help="Execute rollout actions")
upgrade_app = typer.Typer(help="Execute upgrades and rollbacks")
remote_logs_app = typer.Typer(help="Collect remote logs")
deploy_app = typer.Typer(help="Render deployment artifacts")

app.add_typer(interfaces_app, name="interfaces")
app.add_typer(peers_app, name="peers")
app.add_typer(routes_app, name="routes")
app.add_typer(announces_app, name="announces")
app.add_typer(logs_app, name="logs")
app.add_typer(config_app, name="config")
app.add_typer(backup_app, name="backup")
app.add_typer(fleet_app, name="fleet")
app.add_typer(system_app, name="system")
app.add_typer(plugins_app, name="plugins")
app.add_typer(services_app, name="services")
app.add_typer(security_app, name="security")
app.add_typer(rollout_app, name="rollout")
app.add_typer(upgrade_app, name="upgrade")
app.add_typer(remote_logs_app, name="remote-logs")
app.add_typer(deploy_app, name="deploy")


def print_json(payload: object) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def emit_text(content: str, output: Path | None = None) -> None:
    if output is None:
        typer.echo(content, nl=False)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    print_json({"written": str(output), "bytes": len(content.encode("utf-8"))})


async def run_with_context(
    config: Path | None,
    action: Callable[[ApplicationContext], Awaitable[object]],
    *,
    auto_start_runtime: bool | None,
    stop_runtime: bool,
) -> object:
    context = build_context(config)
    await context.startup(auto_start_runtime=auto_start_runtime, enable_background_jobs=False)
    try:
        return await action(context)
    finally:
        await context.shutdown(stop_runtime=stop_runtime)


async def collect_diagnostics_snapshot(context: ApplicationContext) -> dict:
    summary = await context.node_service.status_summary(persist=False)
    return await context.diagnostics_service.snapshot(summary)


async def collect_system_info(context: ApplicationContext) -> dict:
    summary = await context.node_service.status_summary(persist=True)
    users = context.security_service.list_users()
    tokens = context.security_service.list_api_tokens()
    configured_admin_token = context.settings.security.admin_token.strip()
    return {
        "summary": summary,
        "maintenance": context.maintenance_service.get_state(),
        "web": {
            "host": context.settings.web.host,
            "port": context.settings.web.port,
        },
        "paths": {
            "data_dir": str(context.settings.data_dir),
            "database_path": str(context.settings.database_path),
            "runtime_dir": str(context.settings.runtime_dir),
            "config_path": str(context.settings.config_path) if context.settings.config_path else None,
            "reticulum_config_path": str(context.settings.reticulum_config_path),
            "identity_path": str(context.settings.identity_path),
        },
        "security": {
            "allow_wan": context.settings.security.allow_wan,
            "admin_token_configured": bool(configured_admin_token),
            "admin_token_default": configured_admin_token in {"", "change-me"},
            "users_total": len(users),
            "enabled_users": sum(1 for item in users if item.get("enabled")),
            "tokens_total": len(tokens),
            "enabled_tokens": sum(1 for item in tokens if item.get("enabled")),
        },
    }


async def collect_security_overview(context: ApplicationContext) -> dict:
    users = context.security_service.list_users()
    tokens = context.security_service.list_api_tokens()
    configured_admin_token = context.settings.security.admin_token.strip()
    return {
        "allow_wan": context.settings.security.allow_wan,
        "admin_token_configured": bool(configured_admin_token),
        "admin_token_default": configured_admin_token in {"", "change-me"},
        "roles": context.security_service.list_roles(),
        "users": users,
        "api_tokens": tokens,
    }


@app.command()
def serve(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    settings = load_settings(config)
    uvicorn.run(create_app(settings_path=config), host=settings.web.host, port=settings.web.port)


@app.command()
def status(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.node_service.status_summary(persist=True),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@app.command()
def start(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.node_service.start(reason="cli.start"),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@app.command()
def stop(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.node_service.stop(reason="cli.stop"),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@app.command()
def restart(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.node_service.restart(reason="cli.restart"),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@interfaces_app.command("list")
def list_interfaces(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.interface_service.list_interfaces(),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@interfaces_app.command("show")
def show_interface(name: str, config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.interface_service.get_interface(name),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@interfaces_app.command("start")
def start_interface(name: str, config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.interface_service.start(name),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@interfaces_app.command("stop")
def stop_interface(name: str, config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.interface_service.stop(name),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@interfaces_app.command("restart")
def restart_interface(name: str, config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.interface_service.restart(name),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@peers_app.command("list")
def list_peers(
    limit: int = typer.Option(default=100, min=1, max=500),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.peer_service.list_recent(limit=limit),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@routes_app.command("list")
def list_routes(
    limit: int = typer.Option(default=100, min=1, max=500),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.route_service.list_routes(limit=limit),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@announces_app.command("recent")
def recent_announces(
    limit: int = typer.Option(default=20, min=1, max=500),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.announce_service.recent(limit=limit),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@logs_app.command("tail")
def tail_logs(
    limit: int = typer.Option(default=50, min=1, max=500),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: asyncio.to_thread(context.log_service.list_entries, limit),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@config_app.command("show")
def show_config(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    print_json(load_settings(config).to_display_dict())


@config_app.command("show-raw")
def show_config_raw(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: asyncio.to_thread(context.config_service.show_raw),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@config_app.command("validate")
def validate_config_file(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, file_okay=True),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    raw = file.read_text(encoding="utf-8")
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: asyncio.to_thread(context.config_service.validate_raw, raw),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@config_app.command("save-raw")
def save_config_raw(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, file_okay=True),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    raw = file.read_text(encoding="utf-8")
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: asyncio.to_thread(context.config_service.save_raw, raw),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@backup_app.command("list")
def list_backups(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: asyncio.to_thread(context.backup_service.list_archives),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@backup_app.command("export")
def export_backup(
    destination: Path | None = typer.Argument(default=None),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: asyncio.to_thread(context.backup_service.export, destination),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@backup_app.command("import")
def import_backup(
    archive: Path = typer.Argument(..., exists=True, dir_okay=False, file_okay=True),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: asyncio.to_thread(context.backup_service.import_archive, archive),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@fleet_app.command("overview")
def fleet_overview(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.fleet_service.dashboard(),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@fleet_app.command("nodes")
def fleet_nodes(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.fleet_service.list_nodes(),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@fleet_app.command("node")
def fleet_node(node_name: str, config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.fleet_service.get_node(node_name),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@fleet_app.command("groups")
def fleet_groups(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.fleet_service.list_groups(),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@fleet_app.command("templates")
def fleet_templates(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.fleet_service.list_templates(),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@fleet_app.command("tags")
def fleet_tags(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.fleet_service.list_tags(),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@fleet_app.command("health")
def fleet_health(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.fleet_service.health_view(),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@fleet_app.command("events")
def fleet_events(
    limit: int = typer.Option(default=100, min=1, max=500),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.fleet_service.list_events(limit=limit),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@fleet_app.command("create-group")
def fleet_create_group(
    name: str,
    description: str | None = typer.Option(default=None),
    group_type: str = typer.Option(default="custom"),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.fleet_service.create_group(name=name, description=description, group_type=group_type)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@fleet_app.command("register-node")
def fleet_register_node(
    node_name: str,
    display_name: str | None = typer.Option(default=None),
    group_name: str | None = typer.Option(default=None),
    tags: str = typer.Option(default=""),
    version: str | None = typer.Option(default=None),
    health_status: str = typer.Option(default="warning"),
    runtime_status: str = typer.Option(default="offline"),
    uptime_seconds: int = typer.Option(default=0, min=0),
    dashboard_url: str | None = typer.Option(default=None),
    region: str | None = typer.Option(default=None),
    notes: str | None = typer.Option(default=None),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.fleet_service.register_node(
                node_name=node_name,
                display_name=display_name,
                group_name=group_name,
                tags=tags,
                version=version,
                health_status=health_status,
                runtime_status=runtime_status,
                uptime_seconds=uptime_seconds,
                dashboard_url=dashboard_url,
                region=region,
                notes=notes,
            ),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@fleet_app.command("create-template")
def fleet_create_template(
    name: str,
    template_file: Path | None = typer.Option(default=None, exists=True, dir_okay=False, file_okay=True),
    template_text: str | None = typer.Option(default=None),
    description: str | None = typer.Option(default=None),
    target_group: str | None = typer.Option(default=None),
    target_nodes: str = typer.Option(default=""),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    if bool(template_file) == bool(template_text):
        raise typer.BadParameter("provide exactly one of --template-file or --template-text")
    resolved_template = template_file.read_text(encoding="utf-8") if template_file else str(template_text or "")

    async def action(context: ApplicationContext) -> object:
        return context.fleet_service.create_template(
            name=name,
            description=description,
            template_text=resolved_template,
            target_group=target_group,
            target_nodes=target_nodes,
        )

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@system_app.command("info")
def system_info(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            collect_system_info,
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@system_app.command("diagnostics")
def system_diagnostics(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            collect_diagnostics_snapshot,
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@system_app.command("maintenance")
def system_maintenance(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.maintenance_service.get_state()

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@system_app.command("enable-maintenance")
def system_enable_maintenance(
    reason: str | None = typer.Option(default=None),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.maintenance_service.enable(reason=reason, actor="cli.system")

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@system_app.command("disable-maintenance")
def system_disable_maintenance(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.maintenance_service.disable(actor="cli.system")

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@system_app.command("security")
def system_security(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            collect_security_overview,
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@backup_app.command("snapshots")
def backup_snapshots(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: asyncio.to_thread(context.backup_service.list_snapshots),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@backup_app.command("snapshot")
def backup_snapshot(
    destination: Path | None = typer.Argument(default=None),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: asyncio.to_thread(context.backup_service.create_snapshot, destination),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@backup_app.command("prune")
def backup_prune(
    keep: int = typer.Option(default=10, min=1),
    max_age_days: int | None = typer.Option(default=None, min=1),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.backup_service.prune_snapshots(keep=keep, max_age_days=max_age_days)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@backup_app.command("dr")
def backup_disaster_recovery(
    archive: Path | None = typer.Argument(default=None),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.backup_service.disaster_recovery_helper(archive_path=archive)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@plugins_app.command("list")
def plugins_list(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(config, lambda context: asyncio.to_thread(context.plugin_service.list_plugins), auto_start_runtime=False, stop_runtime=False)
    )
    print_json(payload)


@plugins_app.command("catalog")
def plugins_catalog(
    refresh_sources: bool = typer.Option(default=False),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.plugin_service.list_available_plugins(refresh_sources=refresh_sources)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@plugins_app.command("install")
def plugins_install(
    name: str,
    enable: bool = typer.Option(default=True),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.plugin_service.install_plugin(name, enable=enable)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@plugins_app.command("uninstall")
def plugins_uninstall(
    name: str,
    remove_dependents: bool = typer.Option(default=False),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.plugin_service.uninstall_plugin(name, remove_dependents=remove_dependents)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@plugins_app.command("enable")
def plugins_enable(name: str, config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.plugin_service.set_plugin_enabled(name, True)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@plugins_app.command("disable")
def plugins_disable(name: str, config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.plugin_service.set_plugin_enabled(name, False)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@plugins_app.command("update")
def plugins_update(
    name: str,
    enable: bool | None = typer.Option(default=None),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.plugin_service.update_plugin(name, enable=enable)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@plugins_app.command("history")
def plugins_history(
    limit: int = typer.Option(default=50, min=1, max=200),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.plugin_service.plugin_history(limit=limit)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@services_app.command("list")
def services_list(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(config, lambda context: context.service_host_service.list_services(), auto_start_runtime=False, stop_runtime=False)
    )
    print_json(payload)


@services_app.command("show")
def services_show(name: str, config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(config, lambda context: context.service_host_service.get_service(name), auto_start_runtime=False, stop_runtime=False)
    )
    print_json(payload)


@services_app.command("control")
def services_control(
    name: str,
    action_name: str = typer.Argument(..., help="start|stop|restart"),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.service_host_service.control(name, action_name),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@security_app.command("roles")
def security_roles(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(config, lambda context: asyncio.to_thread(context.security_service.list_roles), auto_start_runtime=False, stop_runtime=False)
    )
    print_json(payload)


@security_app.command("create-role")
def security_create_role(
    name: str,
    permissions: str = typer.Option(..., help="Comma-separated permissions"),
    label: str | None = typer.Option(default=None),
    description: str | None = typer.Option(default=None),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    perms = [item.strip() for item in permissions.split(",") if item.strip()]

    async def action(context: ApplicationContext) -> object:
        return context.security_service.create_role(name=name, label=label, description=description, permissions=perms)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@security_app.command("update-role")
def security_update_role(
    name: str,
    permissions: str | None = typer.Option(default=None),
    label: str | None = typer.Option(default=None),
    description: str | None = typer.Option(default=None),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    perms = [item.strip() for item in permissions.split(",") if item.strip()] if permissions else None

    async def action(context: ApplicationContext) -> object:
        return context.security_service.update_role(name, label=label, description=description, permissions=perms)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@security_app.command("delete-role")
def security_delete_role(name: str, config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    async def action(context: ApplicationContext) -> object:
        return context.security_service.delete_role(name)

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@security_app.command("users")
def security_users(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(config, lambda context: asyncio.to_thread(context.security_service.list_users), auto_start_runtime=False, stop_runtime=False)
    )
    print_json(payload)


@security_app.command("tokens")
def security_tokens(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(
        run_with_context(config, lambda context: asyncio.to_thread(context.security_service.list_api_tokens), auto_start_runtime=False, stop_runtime=False)
    )
    print_json(payload)


@rollout_app.command("list")
def rollout_list(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(run_with_context(config, lambda context: context.rollout_service.list_rollouts(), auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@rollout_app.command("apply-template")
def rollout_apply_template(
    template_name: str,
    target_group: str | None = typer.Option(default=None),
    target_nodes: str = typer.Option(default=""),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    nodes = [item.strip() for item in target_nodes.split(",") if item.strip()]

    async def action(context: ApplicationContext) -> object:
        return await context.rollout_service.create_rollout(
            action="apply_template",
            template_name=template_name,
            target_group=target_group,
            target_nodes=nodes,
            actor="cli",
        )

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@upgrade_app.command("list")
def upgrade_list(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    payload = asyncio.run(run_with_context(config, lambda context: context.upgrade_service.list_operations(), auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@upgrade_app.command("run")
def upgrade_run(
    action_name: str,
    target_version: str,
    channel: str = typer.Option(default="stable"),
    target_group: str | None = typer.Option(default=None),
    target_nodes: str = typer.Option(default=""),
    notes: str | None = typer.Option(default=None),
    enable_maintenance: bool = typer.Option(default=False),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    nodes = [item.strip() for item in target_nodes.split(",") if item.strip()]

    async def action(context: ApplicationContext) -> object:
        return await context.upgrade_service.schedule_operation(
            action=action_name,
            target_version=target_version,
            channel=channel,
            target_group=target_group,
            target_nodes=nodes,
            notes=notes,
            enable_maintenance=enable_maintenance,
            actor="cli",
        )

    payload = asyncio.run(run_with_context(config, action, auto_start_runtime=False, stop_runtime=False))
    print_json(payload)


@remote_logs_app.command("list")
def remote_logs_list(
    node_name: str | None = typer.Option(default=None),
    level: str | None = typer.Option(default=None),
    limit: int = typer.Option(default=100, min=1, max=500),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(
            config,
            lambda context: context.remote_log_service.list_entries(node_name=node_name, level=level, limit=limit),
            auto_start_runtime=False,
            stop_runtime=False,
        )
    )
    print_json(payload)


@remote_logs_app.command("sync")
def remote_logs_sync(
    limit: int = typer.Option(default=100, min=1, max=500),
    config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True),
) -> None:
    payload = asyncio.run(
        run_with_context(config, lambda context: context.remote_log_service.sync_nodes(limit=limit), auto_start_runtime=False, stop_runtime=False)
    )
    print_json(payload)


@deploy_app.command("systemd")
def deploy_systemd(
    user: str = typer.Option(default="hearth"),
    group: str = typer.Option(default="hearth"),
    workdir: str = typer.Option(default="/opt/hearth"),
    config_path: str = typer.Option(default="/etc/hearth/hearth.toml"),
    exec_start: str = typer.Option(default="/opt/hearth/.venv/bin/hearth-api"),
    output: Path | None = typer.Option(default=None, dir_okay=False, file_okay=True),
) -> None:
    emit_text(
        render_systemd_service(
            user=user,
            group=group,
            workdir=workdir,
            config_path=config_path,
            exec_start=exec_start,
        ),
        output,
    )


@deploy_app.command("dockerfile")
def deploy_dockerfile(
    python_image: str = typer.Option(default="python:3.12-slim"),
    config_dir: str = typer.Option(default="/data"),
    expose_port: int = typer.Option(default=8480, min=1, max=65535),
    output: Path | None = typer.Option(default=None, dir_okay=False, file_okay=True),
) -> None:
    emit_text(
        render_dockerfile(
            python_image=python_image,
            config_dir=config_dir,
            expose_port=expose_port,
        ),
        output,
    )


@deploy_app.command("compose")
def deploy_compose(
    image: str = typer.Option(default="hearth:latest"),
    config_dir: str = typer.Option(default="/data"),
    host_port: int = typer.Option(default=8480, min=1, max=65535),
    container_port: int = typer.Option(default=8480, min=1, max=65535),
    output: Path | None = typer.Option(default=None, dir_okay=False, file_okay=True),
) -> None:
    emit_text(
        render_docker_compose(
            image=image,
            config_dir=config_dir,
            host_port=host_port,
            container_port=container_port,
        ),
        output,
    )


@deploy_app.command("debian-control")
def deploy_debian_control(
    package_name: str = typer.Option(default="hearth"),
    version: str = typer.Option(default="0.1.0"),
    output: Path | None = typer.Option(default=None, dir_okay=False, file_okay=True),
) -> None:
    emit_text(render_debian_control(package_name=package_name, version=version), output)


@deploy_app.command("appliance-manifest")
def deploy_appliance_manifest(
    image_name: str = typer.Option(default="hearth-appliance"),
    version: str = typer.Option(default="0.1.0"),
    output: Path | None = typer.Option(default=None, dir_okay=False, file_okay=True),
) -> None:
    emit_text(render_appliance_manifest(image_name=image_name, version=version), output)


@deploy_app.command("openwrt")
def deploy_openwrt(
    package_name: str = typer.Option(default="hearth"),
    output: Path | None = typer.Option(default=None, dir_okay=False, file_okay=True),
) -> None:
    emit_text(render_openwrt_makefile(package_name=package_name), output)


@deploy_app.command("migration-plan")
def deploy_migration_plan(
    from_version: str = typer.Option(default="0.1.0"),
    to_version: str = typer.Option(default="0.1.0"),
    output: Path | None = typer.Option(default=None, dir_okay=False, file_okay=True),
) -> None:
    emit_text(render_migration_plan(from_version=from_version, to_version=to_version), output)


@deploy_app.command("preflight")
def deploy_preflight(config: Path | None = typer.Option(default=None, exists=False, dir_okay=False, file_okay=True)) -> None:
    settings = load_settings(config)
    settings.ensure_directories()
    print_json(preflight_check(settings))


@deploy_app.command("bundle")
def deploy_bundle(directory: Path = typer.Argument(..., file_okay=False, dir_okay=True, writable=True)) -> None:
    written = write_bundle(directory)
    print_json({"written": written, "count": len(written)})


def main() -> None:
    app()


if __name__ == "__main__":
    main()
