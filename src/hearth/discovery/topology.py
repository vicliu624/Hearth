from __future__ import annotations

from hearth.discovery.peers import PeerStore


class TopologyView:
    def __init__(self, peer_store: PeerStore) -> None:
        self.peer_store = peer_store

    def build(self) -> dict:
        peers = [item.to_dict() for item in self.peer_store.list_recent()]
        return {"node_count": len(peers), "nodes": peers}

