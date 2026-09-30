from __future__ import annotations

from fastapi import HTTPException

from hearth.discovery.peers import PeerStore
from hearth.storage.db import Database


class PeerService:
    def __init__(
        self, peer_store: PeerStore, database: Database, observation_service
    ) -> None:
        self.peer_store = peer_store
        self.database = database
        self.observation_service = observation_service

    async def list_recent(self, limit: int = 100) -> list[dict]:
        return await self.observation_service.list_peers(limit)

    async def get_peer(self, peer_hash: str) -> dict:
        peer = self.peer_store.get(peer_hash)
        persisted = self.database.get_peer(peer_hash)
        if (
            self.observation_service.adapter.settings.reticulum.backend
            != "mock_process"
            and persisted is not None
            and persisted.get("source_type") != "announce"
        ):
            persisted = None
        if peer is not None:
            payload = peer.to_dict()
            if persisted is None:
                return payload
            return {
                **persisted,
                **{key: value for key, value in payload.items() if value is not None},
            }
        if persisted is None:
            raise HTTPException(status_code=404, detail="peer not found")
        return persisted
