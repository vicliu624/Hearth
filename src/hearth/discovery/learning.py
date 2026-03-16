from __future__ import annotations

from hearth.discovery.peers import PeerSnapshot, PeerStore


class DiscoveryLearning:
    def __init__(self, peer_store: PeerStore) -> None:
        self.peer_store = peer_store

    def ingest(self, snapshot: PeerSnapshot) -> None:
        self.peer_store.upsert(snapshot)

