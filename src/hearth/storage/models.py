from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class NodeState(Base):
    __tablename__ = "node_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    runtime_status: Mapped[str] = mapped_column(String(32), default="stopped")
    health_status: Mapped[str] = mapped_column(String(32), default="warning")
    uptime_seconds: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    restart_count: Mapped[int] = mapped_column(Integer, default=0)


class InterfaceRuntime(Base):
    __tablename__ = "interface_runtime"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interface_name: Mapped[str] = mapped_column(String(120), unique=True)
    interface_type: Mapped[str] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default="stopped")
    health_status: Mapped[str] = mapped_column(String(32), default="warning")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rx_packets: Mapped[int] = mapped_column(Integer, default=0)
    tx_packets: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InterfaceMetricSnapshot(Base):
    __tablename__ = "interface_metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    interface_name: Mapped[str] = mapped_column(String(120))
    rx_packets: Mapped[int] = mapped_column(Integer, default=0)
    tx_packets: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EventRecord(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(32), default="info")
    source: Mapped[str] = mapped_column(String(64), default="system")
    message: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PeerRecord(Base):
    __tablename__ = "peers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    peer_hash: Mapped[str] = mapped_column(String(128), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    via_interface: Mapped[str | None] = mapped_column(String(120), nullable=True)
    hop_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class RouteRecord(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    destination_hash: Mapped[str] = mapped_column(String(128), unique=True)
    next_hop: Mapped[str | None] = mapped_column(String(128), nullable=True)
    via_interface: Mapped[str | None] = mapped_column(String(120), nullable=True)
    hop_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AnnounceRecord(Base):
    __tablename__ = "announces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_hash: Mapped[str] = mapped_column(String(128))
    via_interface: Mapped[str | None] = mapped_column(String(120), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    hop_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")


class RestartRecord(Base):
    __tablename__ = "restart_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    target_type: Mapped[str] = mapped_column(String(64))
    target_name: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MaintenanceStateRecord(Base):
    __tablename__ = "maintenance_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    until_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(120), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(64), default="viewer")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiTokenRecord(Base):
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_name: Mapped[str] = mapped_column(String(120), unique=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    token_hint: Mapped[str] = mapped_column(String(32), default="")
    owner_username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    role: Mapped[str] = mapped_column(String(64), default="viewer")
    scopes_json: Mapped[str] = mapped_column(Text, default="[]")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConfigRevisionRecord(Base):
    __tablename__ = "config_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    revision_label: Mapped[str] = mapped_column(String(160), default="snapshot")
    source: Mapped[str] = mapped_column(String(64), default="config")
    actor: Mapped[str] = mapped_column(String(120), default="system")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), default="")
    raw_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FleetNodeRecord(Base):
    __tablename__ = "fleet_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_key: Mapped[str] = mapped_column(String(160), unique=True)
    node_name: Mapped[str] = mapped_column(String(160))
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    version: Mapped[str] = mapped_column(String(64), default="unknown")
    health_status: Mapped[str] = mapped_column(String(32), default="warning")
    runtime_status: Mapped[str] = mapped_column(String(32), default="offline")
    uptime_seconds: Mapped[int] = mapped_column(Integer, default=0)
    dashboard_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    local: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(64), default="inventory")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class NodeGroupRecord(Base):
    __tablename__ = "node_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_type: Mapped[str] = mapped_column(String(64), default="custom")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ConfigTemplateRecord(Base):
    __tablename__ = "config_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_text: Mapped[str] = mapped_column(Text)
    target_group: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_nodes_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)



class RolloutRecord(Base):
    __tablename__ = "rollouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(64), default="apply_template")
    template_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_group: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_nodes_json: Mapped[str] = mapped_column(Text, default="[]")
    resolved_nodes_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(32), default="planned")
    actor: Mapped[str] = mapped_column(String(120), default="system")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UpgradeOperationRecord(Base):
    __tablename__ = "upgrade_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(32), default="upgrade")
    current_version: Mapped[str] = mapped_column(String(64), default="unknown")
    target_version: Mapped[str] = mapped_column(String(160), default="unknown")
    channel: Mapped[str] = mapped_column(String(64), default="stable")
    target_group: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_nodes_json: Mapped[str] = mapped_column(Text, default="[]")
    resolved_nodes_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(32), default="planned")
    maintenance_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(120), default="system")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
