from __future__ import annotations

from fastapi import HTTPException

from hearth.reticulum.announces import AnnounceStore
from hearth.storage.db import Database


class AnnounceService:
    def __init__(self, announce_store: AnnounceStore, database: Database, observation_service) -> None:
        self.announce_store = announce_store
        self.database = database
        self.observation_service = observation_service

    async def list_announces(self, limit: int = 100) -> list[dict]:
        await self.observation_service.sync()
        return self.database.list_announces(limit=limit)

    async def get_announce(self, announce_id: int) -> dict:
        await self.observation_service.sync()
        payload = self.database.get_announce(announce_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="announce not found")
        return payload

    async def recent(self, limit: int = 20) -> list[dict]:
        return await self.list_announces(limit=limit)
