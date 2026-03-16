from __future__ import annotations

from fastapi import HTTPException

from hearth.discovery.peers import PeerStore
from hearth.storage.db import Database


class PeerService:
    def __init__(self, peer_store: PeerStore, database: Database, observation_service) -> None:
        self.peer_store = peer_store
        self.database = database
        self.observation_service = observation_service

    async def list_recent(self, limit: int = 100) -> list[dict]:
        await self.observation_service.sync()
        items = [peer.to_dict() for peer in self.peer_store.list_recent()]
        if items:
            return items[:limit]
        return self.database.list_peers(limit=limit)

    async def get_peer(self, peer_hash: str) -> dict:
        await self.observation_service.sync()
        peer = self.peer_store.get(peer_hash)
        persisted = self.database.get_peer(peer_hash)
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
