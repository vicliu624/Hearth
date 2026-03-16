from __future__ import annotations

from fastapi import HTTPException

from hearth.reticulum.paths import PathSnapshotStore
from hearth.storage.db import Database


class RouteService:
    def __init__(self, path_store: PathSnapshotStore, database: Database, observation_service) -> None:
        self.path_store = path_store
        self.database = database
        self.observation_service = observation_service

    async def list_routes(self, limit: int = 100) -> list[dict]:
        await self.observation_service.sync()
        entries = self.path_store.list()
        if entries:
            return [entry.to_dict() for entry in entries][:limit]
        return self.database.list_routes(limit=limit)

    async def get_route(self, destination_hash: str) -> dict:
        await self.observation_service.sync()
        for entry in self.path_store.list():
            if entry.destination_hash == destination_hash:
                return entry.to_dict()
        payload = self.database.get_route(destination_hash)
        if payload is None:
            raise HTTPException(status_code=404, detail="route not found")
        return payload

    async def summary(self) -> dict:
        routes = await self.list_routes()
        return {"count": len(routes), "routes": routes}
