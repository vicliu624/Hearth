from __future__ import annotations

from hearth.discovery.peers import PeerSnapshot, PeerStore
from hearth.reticulum.adapter import ReticulumAdapter
from hearth.reticulum.announces import AnnounceStore
from hearth.reticulum.paths import PathSnapshotStore
from hearth.storage.db import Database


class ObservationService:
    def __init__(
        self,
        adapter: ReticulumAdapter,
        peer_store: PeerStore,
        path_store: PathSnapshotStore,
        announce_store: AnnounceStore,
        database: Database,
    ) -> None:
        self.adapter = adapter
        self.peer_store = peer_store
        self.path_store = path_store
        self.announce_store = announce_store
        self.database = database

    def _route_signature(self, payload: dict[str, object]) -> tuple[object, object, object]:
        return (
            payload.get("via_interface"),
            payload.get("next_hop"),
            payload.get("hop_count"),
        )

    def _route_message(self, action: str, destination_hash: str, via_interface: str | None) -> str:
        short_hash = destination_hash if len(destination_hash) <= 12 else f"{destination_hash[:12]}..."
        if action == "added":
            return f"route discovered for {short_hash} via {via_interface or 'unknown'}"
        if action == "removed":
            return f"route removed for {short_hash}"
        return f"route updated for {short_hash}"

    def _record_route_changes(self, paths: list[dict[str, object]]) -> None:
        previous_routes = {
            str(item.get("destination_hash") or ""): item
            for item in self.database.list_routes(limit=None)
            if item.get("destination_hash")
        }
        current_routes = {
            str(item.get("destination_hash") or ""): item
            for item in paths
            if item.get("destination_hash")
        }

        for destination_hash, current in current_routes.items():
            previous = previous_routes.get(destination_hash)
            if previous is None:
                self.database.record_event(
                    "route.added",
                    self._route_message("added", destination_hash, str(current.get("via_interface") or "") or None),
                    severity="info",
                    source="observation_service",
                    payload={
                        "destination_hash": destination_hash,
                        "change_type": "added",
                        "via_interface": current.get("via_interface"),
                        "next_hop": current.get("next_hop"),
                        "hop_count": current.get("hop_count"),
                        "current": current,
                    },
                )
                continue

            if self._route_signature(previous) == self._route_signature(current):
                continue

            self.database.record_event(
                "route.changed",
                self._route_message("changed", destination_hash, str(current.get("via_interface") or "") or None),
                severity="warning",
                source="observation_service",
                payload={
                    "destination_hash": destination_hash,
                    "change_type": "changed",
                    "via_interface": current.get("via_interface"),
                    "next_hop": current.get("next_hop"),
                    "hop_count": current.get("hop_count"),
                    "previous": previous,
                    "current": current,
                },
            )

        for destination_hash, previous in previous_routes.items():
            if destination_hash in current_routes:
                continue
            self.database.record_event(
                "route.removed",
                self._route_message("removed", destination_hash, str(previous.get("via_interface") or "") or None),
                severity="warning",
                source="observation_service",
                payload={
                    "destination_hash": destination_hash,
                    "change_type": "removed",
                    "via_interface": previous.get("via_interface"),
                    "next_hop": previous.get("next_hop"),
                    "hop_count": previous.get("hop_count"),
                    "previous": previous,
                },
            )

    async def sync(self) -> dict[str, int]:
        paths = self.adapter.get_paths()
        announces = self.adapter.get_announces()
        self.path_store.replace(paths)
        self.announce_store.replace(announces)
        path_payloads = [item.to_dict() for item in paths]
        self._record_route_changes(path_payloads)
        self.database.replace_routes(path_payloads)

        peer_count = 0
        for announce in announces:
            payload = announce.to_dict()
            self.database.save_announce(payload)
            peer = PeerSnapshot(
                peer_hash=announce.source_hash,
                display_name=announce.metadata.get("display_name"),
                last_seen_at=announce.received_at,
                interface_name=announce.via_interface,
                hops=announce.hop_count,
                source_type=announce.metadata.get("source_type", "announce"),
            )
            self.peer_store.upsert(peer)
            self.database.upsert_peer(peer.to_dict())
            peer_count += 1

        return {
            "peer_count": peer_count,
            "route_count": len(paths),
            "announce_count": len(announces),
        }

    async def list_peers(self, limit: int = 100) -> list[dict]:
        await self.sync()
        items = [peer.to_dict() for peer in self.peer_store.list_recent()]
        return items[:limit] if items else self.database.list_peers(limit=limit)

    async def list_routes(self, limit: int = 100) -> list[dict]:
        await self.sync()
        items = [entry.to_dict() for entry in self.path_store.list()]
        return items[:limit] if items else self.database.list_routes(limit=limit)

    async def list_announces(self, limit: int = 100) -> list[dict]:
        await self.sync()
        items = [item.to_dict() for item in self.announce_store.recent(limit)]
        return items if items else self.database.list_announces(limit=limit)
