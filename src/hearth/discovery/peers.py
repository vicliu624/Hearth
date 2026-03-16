from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(slots=True)
class PeerSnapshot:
    peer_hash: str
    display_name: str | None = None
    last_seen_at: datetime | None = None
    interface_name: str | None = None
    hops: int | None = None
    source_type: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["last_seen_at"] = self.last_seen_at.isoformat() if self.last_seen_at else None
        return data


class PeerStore:
    def __init__(self) -> None:
        self._peers: dict[str, PeerSnapshot] = {}

    def list_recent(self) -> list[PeerSnapshot]:
        return sorted(self._peers.values(), key=lambda peer: peer.last_seen_at or datetime.min, reverse=True)

    def get(self, peer_hash: str) -> PeerSnapshot | None:
        return self._peers.get(peer_hash)

    def upsert(self, peer: PeerSnapshot) -> None:
        self._peers[peer.peer_hash] = peer

