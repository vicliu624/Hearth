from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class NodeRuntimeStatus:
    status: str
    running: bool
    started_at: datetime | None
    uptime_seconds: int
    restart_count: int = 0
    pid: int | None = None
    backend: str | None = None
    last_heartbeat_at: datetime | None = None
    last_exit_code: int | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["started_at"] = self.started_at.isoformat() if self.started_at else None
        data["last_heartbeat_at"] = self.last_heartbeat_at.isoformat() if self.last_heartbeat_at else None
        return data


@dataclass(slots=True)
class PathEntry:
    destination_hash: str
    via_interface: str | None = None
    next_hop: str | None = None
    hop_count: int | None = None
    expires_at: datetime | None = None
    last_updated_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "destination_hash": self.destination_hash,
            "via_interface": self.via_interface,
            "next_hop": self.next_hop,
            "hop_count": self.hop_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_updated_at": self.last_updated_at.isoformat() if self.last_updated_at else None,
        }


@dataclass(slots=True)
class InterfaceRuntimeInfo:
    name: str
    type: str
    enabled: bool
    status: str
    health_status: str
    last_seen_at: datetime | None = None
    metrics: dict[str, int] = field(default_factory=dict)
    last_error: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "enabled": self.enabled,
            "status": self.status,
            "health_status": self.health_status,
            "last_seen_at": self.last_seen_at,
            "metrics": self.metrics,
            "last_error": self.last_error,
        }


@dataclass(slots=True)
class AnnounceEvent:
    source_hash: str
    via_interface: str | None = None
    received_at: datetime | None = None
    hop_count: int | None = None
    raw_summary: str | None = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source_hash": self.source_hash,
            "via_interface": self.via_interface,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "hop_count": self.hop_count,
            "raw_summary": self.raw_summary,
            "metadata": self.metadata,
        }


class ReticulumAdapter(ABC):
    @abstractmethod
    async def refresh(self) -> NodeRuntimeStatus:
        raise NotImplementedError

    @abstractmethod
    async def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def restart(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> NodeRuntimeStatus:
        raise NotImplementedError

    @abstractmethod
    def get_paths(self) -> list[PathEntry]:
        raise NotImplementedError

    @abstractmethod
    def get_interfaces(self) -> list[InterfaceRuntimeInfo]:
        raise NotImplementedError

    @abstractmethod
    def set_interfaces(self, interfaces: list[InterfaceRuntimeInfo]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_announces(self) -> list[AnnounceEvent]:
        raise NotImplementedError
