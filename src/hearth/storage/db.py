from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
import json
from typing import Any, Iterator

from sqlalchemy import Select, create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from hearth.storage.models import (
    ApiTokenRecord,
    AnnounceRecord,
    Base,
    EventRecord,
    InterfaceMetricSnapshot,
    InterfaceRuntime,
    MaintenanceStateRecord,
    NodeState,
    PeerRecord,
    RestartRecord,
    RouteRecord,
    UserRecord,
    utcnow,
)


class Database:
    def __init__(self, url: str) -> None:
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, future=True, connect_args=connect_args)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def init_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_node_state(
        self,
        runtime_status: str,
        health_status: str,
        uptime_seconds: int,
        started_at: datetime | None,
        restart_count: int,
    ) -> None:
        with self.session() as session:
            record = session.scalar(select(NodeState).order_by(NodeState.id.desc()))
            if record is None:
                record = NodeState()
                session.add(record)
            record.runtime_status = runtime_status
            record.health_status = health_status
            record.uptime_seconds = uptime_seconds
            record.started_at = started_at
            record.last_check_at = utcnow()
            record.restart_count = restart_count

    def _parse_datetime(self, value: datetime | str | None) -> datetime | None:
        if value is None or isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value)

    def upsert_interface_runtime(self, payload: dict[str, Any]) -> None:
        with self.session() as session:
            statement: Select[tuple[InterfaceRuntime]] = select(InterfaceRuntime).where(
                InterfaceRuntime.interface_name == payload["name"]
            )
            record = session.scalar(statement)
            if record is None:
                record = InterfaceRuntime(interface_name=payload["name"], interface_type=payload["type"])
                session.add(record)
            record.interface_type = payload["type"]
            record.enabled = payload["enabled"]
            record.status = payload["status"]
            record.health_status = payload["health_status"]
            record.last_seen_at = payload["last_seen_at"]
            record.rx_packets = payload["metrics"].get("rx_packets", 0)
            record.tx_packets = payload["metrics"].get("tx_packets", 0)
            record.error_count = payload["metrics"].get("error_count", 0)
            record.last_error = payload.get("last_error")
            record.updated_at = utcnow()

    def get_interface_runtimes(self) -> dict[str, dict[str, Any]]:
        with self.session() as session:
            rows = session.scalars(select(InterfaceRuntime)).all()
        return {
            row.interface_name: {
                "name": row.interface_name,
                "type": row.interface_type,
                "enabled": row.enabled,
                "status": row.status,
                "health_status": row.health_status,
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
                "error_count": row.error_count,
                "restart_count": 0,
                "last_error": row.last_error,
            }
            for row in rows
        }

    def record_interface_metric_snapshots(
        self,
        payloads: list[dict[str, Any]],
        captured_at: datetime | None = None,
    ) -> None:
        recorded_at = captured_at or utcnow()
        retention_cutoff = recorded_at - timedelta(hours=48)
        with self.session() as session:
            session.execute(delete(InterfaceMetricSnapshot).where(InterfaceMetricSnapshot.captured_at < retention_cutoff))
            for payload in payloads:
                metrics = payload.get("metrics", {})
                session.add(
                    InterfaceMetricSnapshot(
                        interface_name=payload["name"],
                        rx_packets=int(metrics.get("rx_packets", 0) or 0),
                        tx_packets=int(metrics.get("tx_packets", 0) or 0),
                        error_count=int(metrics.get("error_count", 0) or 0),
                        captured_at=recorded_at,
                    )
                )

    def list_interface_metric_snapshots(self, since: datetime) -> list[dict[str, Any]]:
        with self.session() as session:
            rows = session.scalars(
                select(InterfaceMetricSnapshot)
                .where(InterfaceMetricSnapshot.captured_at >= since)
                .order_by(InterfaceMetricSnapshot.interface_name, InterfaceMetricSnapshot.captured_at)
            ).all()
        return [
            {
                "interface_name": row.interface_name,
                "rx_packets": row.rx_packets,
                "tx_packets": row.tx_packets,
                "error_count": row.error_count,
                "captured_at": row.captured_at.isoformat(),
            }
            for row in rows
        ]

    def record_event(
        self,
        event_type: str,
        message: str,
        severity: str = "info",
        source: str = "system",
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self.session() as session:
            session.add(
                EventRecord(
                    event_type=event_type,
                    message=message,
                    severity=severity,
                    source=source,
                    payload_json=json.dumps(payload or {}, ensure_ascii=False),
                )
            )

    def list_events(
        self,
        limit: int | None = 100,
        severity: str | None = None,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        with self.session() as session:
            statement = select(EventRecord).order_by(EventRecord.created_at.desc())
            if severity:
                statement = statement.where(EventRecord.severity == severity)
            if source:
                statement = statement.where(EventRecord.source == source)
            if limit is not None:
                statement = statement.limit(limit)
            rows = session.scalars(statement).all()
        return [
            {
                "id": row.id,
                "event_type": row.event_type,
                "severity": row.severity,
                "source": row.source,
                "message": row.message,
                "payload": json.loads(row.payload_json),
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    def record_restart(self, target_type: str, target_name: str, reason: str) -> None:
        with self.session() as session:
            session.add(RestartRecord(target_type=target_type, target_name=target_name, reason=reason))

    def list_restarts(
        self,
        limit: int = 50,
        target_type: str | None = None,
        target_name: str | None = None,
    ) -> list[dict[str, Any]]:
        with self.session() as session:
            statement = select(RestartRecord)
            if target_type:
                statement = statement.where(RestartRecord.target_type == target_type)
            if target_name:
                statement = statement.where(RestartRecord.target_name == target_name)
            rows = session.scalars(statement.order_by(RestartRecord.created_at.desc()).limit(limit)).all()
        return [
            {
                "target_type": row.target_type,
                "target_name": row.target_name,
                "reason": row.reason,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    def upsert_peer(self, payload: dict[str, Any]) -> None:
        with self.session() as session:
            statement: Select[tuple[PeerRecord]] = select(PeerRecord).where(PeerRecord.peer_hash == payload["peer_hash"])
            record = session.scalar(statement)
            if record is None:
                record = PeerRecord(peer_hash=payload["peer_hash"])
                session.add(record)
                record.first_seen_at = self._parse_datetime(payload.get("last_seen_at"))
            record.display_name = payload.get("display_name")
            record.last_seen_at = self._parse_datetime(payload.get("last_seen_at"))
            record.via_interface = payload.get("interface_name")
            record.hop_count = payload.get("hops")
            record.metadata_json = json.dumps(
                {
                    "source_type": payload.get("source_type"),
                },
                ensure_ascii=False,
            )


    def list_peers(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.session() as session:
            rows = session.scalars(select(PeerRecord).order_by(PeerRecord.last_seen_at.desc()).limit(limit)).all()
        return [
            {
                "peer_hash": row.peer_hash,
                "display_name": row.display_name,
                "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
                "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
                "interface_name": row.via_interface,
                "hops": row.hop_count,
                "source_type": json.loads(row.metadata_json or "{}").get("source_type"),
            }
            for row in rows
        ]

    def get_peer(self, peer_hash: str) -> dict[str, Any] | None:
        with self.session() as session:
            row = session.scalar(select(PeerRecord).where(PeerRecord.peer_hash == peer_hash))
        if row is None:
            return None
        return {
            "peer_hash": row.peer_hash,
            "display_name": row.display_name,
            "first_seen_at": row.first_seen_at.isoformat() if row.first_seen_at else None,
            "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
            "interface_name": row.via_interface,
            "hops": row.hop_count,
            "source_type": json.loads(row.metadata_json or "{}").get("source_type"),
        }
    def replace_routes(self, payloads: list[dict[str, Any]]) -> None:
        destination_hashes = {item["destination_hash"] for item in payloads}
        with self.session() as session:
            rows = session.scalars(select(RouteRecord)).all()
            for row in rows:
                if row.destination_hash not in destination_hashes:
                    session.delete(row)

            for payload in payloads:
                row = session.scalar(select(RouteRecord).where(RouteRecord.destination_hash == payload["destination_hash"]))
                if row is None:
                    row = RouteRecord(destination_hash=payload["destination_hash"])
                    session.add(row)
                row.next_hop = payload.get("next_hop")
                row.via_interface = payload.get("via_interface")
                row.hop_count = payload.get("hop_count")
                expires_at = self._parse_datetime(payload.get("expires_at"))
                updated_at = self._parse_datetime(payload.get("last_updated_at"))
                row.expires_at = expires_at
                row.updated_at = updated_at or utcnow()


    def list_routes(self, limit: int | None = 100) -> list[dict[str, Any]]:
        with self.session() as session:
            statement = select(RouteRecord).order_by(RouteRecord.updated_at.desc())
            if limit is not None:
                statement = statement.limit(limit)
            rows = session.scalars(statement).all()
        return [
            {
                "destination_hash": row.destination_hash,
                "next_hop": row.next_hop,
                "via_interface": row.via_interface,
                "hop_count": row.hop_count,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
                "last_updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]

    def get_route(self, destination_hash: str) -> dict[str, Any] | None:
        with self.session() as session:
            row = session.scalar(select(RouteRecord).where(RouteRecord.destination_hash == destination_hash))
        if row is None:
            return None
        return {
            "destination_hash": row.destination_hash,
            "next_hop": row.next_hop,
            "via_interface": row.via_interface,
            "hop_count": row.hop_count,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "last_updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
    def save_announce(self, payload: dict[str, Any]) -> None:
        received_at = self._parse_datetime(payload.get("received_at"))
        with self.session() as session:
            row = session.scalar(
                select(AnnounceRecord).where(
                    AnnounceRecord.source_hash == payload["source_hash"],
                    AnnounceRecord.via_interface == payload.get("via_interface"),
                    AnnounceRecord.received_at == received_at,
                )
            )
            if row is not None:
                return
            session.add(
                AnnounceRecord(
                    source_hash=payload["source_hash"],
                    via_interface=payload.get("via_interface"),
                    received_at=received_at or utcnow(),
                    hop_count=payload.get("hop_count"),
                    raw_summary=payload.get("raw_summary"),
                    metadata_json=json.dumps(payload.get("metadata") or {}, ensure_ascii=False),
                )
            )


    def list_announces(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.session() as session:
            rows = session.scalars(select(AnnounceRecord).order_by(AnnounceRecord.received_at.desc()).limit(limit)).all()
        return [
            {
                "id": row.id,
                "source_hash": row.source_hash,
                "via_interface": row.via_interface,
                "received_at": row.received_at.isoformat() if row.received_at else None,
                "hop_count": row.hop_count,
                "raw_summary": row.raw_summary,
                "metadata": json.loads(row.metadata_json or "{}"),
            }
            for row in rows
        ]

    def get_announce(self, announce_id: int) -> dict[str, Any] | None:
        with self.session() as session:
            row = session.scalar(select(AnnounceRecord).where(AnnounceRecord.id == announce_id))
        if row is None:
            return None
        return {
            "id": row.id,
            "source_hash": row.source_hash,
            "via_interface": row.via_interface,
            "received_at": row.received_at.isoformat() if row.received_at else None,
            "hop_count": row.hop_count,
            "raw_summary": row.raw_summary,
            "metadata": json.loads(row.metadata_json or "{}"),
        }

    def get_maintenance_state(self) -> dict[str, Any]:
        with self.session() as session:
            row = session.scalar(select(MaintenanceStateRecord).order_by(MaintenanceStateRecord.id.desc()))
        if row is None:
            return {
                "enabled": False,
                "reason": None,
                "until_at": None,
                "updated_at": None,
            }
        return {
            "enabled": row.enabled,
            "reason": row.reason,
            "until_at": row.until_at.isoformat() if row.until_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def set_maintenance_state(
        self,
        *,
        enabled: bool,
        reason: str | None = None,
        until_at: datetime | None = None,
    ) -> dict[str, Any]:
        with self.session() as session:
            row = session.scalar(select(MaintenanceStateRecord).order_by(MaintenanceStateRecord.id.desc()))
            if row is None:
                row = MaintenanceStateRecord()
                session.add(row)
            row.enabled = enabled
            row.reason = reason
            row.until_at = until_at
            row.updated_at = utcnow()
            session.flush()
            return {
                "enabled": row.enabled,
                "reason": row.reason,
                "until_at": row.until_at.isoformat() if row.until_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }

    def list_users(self) -> list[dict[str, Any]]:
        with self.session() as session:
            rows = session.scalars(select(UserRecord).order_by(UserRecord.username.asc())).all()
        return [
            {
                "username": row.username,
                "display_name": row.display_name,
                "role": row.role,
                "enabled": row.enabled,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "last_login_at": row.last_login_at.isoformat() if row.last_login_at else None,
            }
            for row in rows
        ]

    def get_user(self, username: str) -> dict[str, Any] | None:
        with self.session() as session:
            row = session.scalar(select(UserRecord).where(UserRecord.username == username))
        if row is None:
            return None
        return {
            "username": row.username,
            "display_name": row.display_name,
            "role": row.role,
            "enabled": row.enabled,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "last_login_at": row.last_login_at.isoformat() if row.last_login_at else None,
        }

    def upsert_user(
        self,
        *,
        username: str,
        display_name: str | None = None,
        role: str = "viewer",
        enabled: bool = True,
    ) -> dict[str, Any]:
        with self.session() as session:
            row = session.scalar(select(UserRecord).where(UserRecord.username == username))
            if row is None:
                row = UserRecord(username=username)
                session.add(row)
                row.created_at = utcnow()
            row.display_name = display_name or None
            row.role = role
            row.enabled = enabled
            row.updated_at = utcnow()
            session.flush()
            return {
                "username": row.username,
                "display_name": row.display_name,
                "role": row.role,
                "enabled": row.enabled,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "last_login_at": row.last_login_at.isoformat() if row.last_login_at else None,
            }

    def set_user_enabled(self, username: str, enabled: bool) -> dict[str, Any] | None:
        with self.session() as session:
            row = session.scalar(select(UserRecord).where(UserRecord.username == username))
            if row is None:
                return None
            row.enabled = enabled
            row.updated_at = utcnow()
            session.flush()
            return {
                "username": row.username,
                "display_name": row.display_name,
                "role": row.role,
                "enabled": row.enabled,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                "last_login_at": row.last_login_at.isoformat() if row.last_login_at else None,
            }

    def touch_user_login(self, username: str) -> None:
        with self.session() as session:
            row = session.scalar(select(UserRecord).where(UserRecord.username == username))
            if row is None:
                return
            row.last_login_at = utcnow()
            row.updated_at = utcnow()

    def list_api_tokens(self) -> list[dict[str, Any]]:
        with self.session() as session:
            rows = session.scalars(select(ApiTokenRecord).order_by(ApiTokenRecord.created_at.desc())).all()
        return [
            {
                "token_name": row.token_name,
                "token_hint": row.token_hint,
                "owner_username": row.owner_username,
                "role": row.role,
                "scopes": json.loads(row.scopes_json or "[]"),
                "enabled": row.enabled,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            }
            for row in rows
        ]

    def get_api_token_by_hash(self, token_hash: str) -> dict[str, Any] | None:
        with self.session() as session:
            row = session.scalar(select(ApiTokenRecord).where(ApiTokenRecord.token_hash == token_hash))
        if row is None:
            return None
        return {
            "token_name": row.token_name,
            "token_hash": row.token_hash,
            "token_hint": row.token_hint,
            "owner_username": row.owner_username,
            "role": row.role,
            "scopes": json.loads(row.scopes_json or "[]"),
            "enabled": row.enabled,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        }

    def create_api_token(
        self,
        *,
        token_name: str,
        token_hash: str,
        token_hint: str,
        owner_username: str | None,
        role: str,
        scopes: list[str],
        expires_at: datetime | None,
    ) -> dict[str, Any]:
        with self.session() as session:
            row = ApiTokenRecord(
                token_name=token_name,
                token_hash=token_hash,
                token_hint=token_hint,
                owner_username=owner_username,
                role=role,
                scopes_json=json.dumps(scopes, ensure_ascii=False),
                enabled=True,
                expires_at=expires_at,
            )
            session.add(row)
            session.flush()
            return {
                "token_name": row.token_name,
                "token_hint": row.token_hint,
                "owner_username": row.owner_username,
                "role": row.role,
                "scopes": scopes,
                "enabled": row.enabled,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            }

    def set_api_token_enabled(self, token_name: str, enabled: bool) -> dict[str, Any] | None:
        with self.session() as session:
            row = session.scalar(select(ApiTokenRecord).where(ApiTokenRecord.token_name == token_name))
            if row is None:
                return None
            row.enabled = enabled
            session.flush()
            return {
                "token_name": row.token_name,
                "token_hint": row.token_hint,
                "owner_username": row.owner_username,
                "role": row.role,
                "scopes": json.loads(row.scopes_json or "[]"),
                "enabled": row.enabled,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
                "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            }

    def touch_api_token(self, token_name: str) -> None:
        with self.session() as session:
            row = session.scalar(select(ApiTokenRecord).where(ApiTokenRecord.token_name == token_name))
            if row is None:
                return
            row.last_used_at = utcnow()
