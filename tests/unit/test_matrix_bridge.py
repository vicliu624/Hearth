from pathlib import Path
from types import SimpleNamespace
import asyncio
import json
import pytest
from hearth.bridges.store import BridgeStore, parse_message
from hearth.bridges.matrix_lxmf import MatrixLXMFBridge


def test_routing_is_explicit_and_reply_fallback_is_not_forwarded():
    peer = "ab" * 16
    assert parse_message("hello") is None
    assert parse_message(f"!lxmf {peer} hello") == (peer, "hello")
    assert parse_message(
        "> <bot> private quote\n> previous message\n\nanswer", peer
    ) == (peer, "answer")
    assert parse_message("!lxmf invalid hello") is None
    with pytest.raises(ValueError):
        parse_message("!lxmf " + peer + " " + "中" * 3000)


def test_queue_survives_restart_deduplicates_and_maps_replies(tmp_path):
    db = BridgeStore(tmp_path / "bridge.db")
    assert db.enqueue("lx:one", "matrix", "ab" * 16, "hello")
    assert not db.enqueue("lx:one", "matrix", "ab" * 16, "duplicate")
    assert db.claim("lx:one")
    restarted = BridgeStore(tmp_path / "bridge.db")
    restarted.recover()
    assert restarted.ready("matrix")["body"] == "hello"
    assert restarted.claim("lx:one")
    restarted.complete("lx:one", "$event")
    assert restarted.ready("matrix") is None
    assert restarted.peer_for_reply("$event") == "ab" * 16
    assert not restarted.enqueue("lx:one", "matrix", "ab" * 16, "old")
    restarted.set("since", "cursor")
    assert BridgeStore(tmp_path / "bridge.db").get("since") == "cursor"


def test_room_sender_encryption_and_loop_boundaries(tmp_path):
    config = tmp_path / "credentials.json"
    config.write_text(
        json.dumps(
            {
                "room_id": "!room:host",
                "user_id": "@bot:host",
                "allowed_users": ["@owner:host"],
                "started_at": 1000,
            }
        )
    )
    bridge = MatrixLXMFBridge(config)
    bridge.source = SimpleNamespace(hash=bytes.fromhex("cd" * 16))
    room = SimpleNamespace(room_id="!room:host", encrypted=True)

    def event(
        sender="@owner:host", event_id="$1", decrypted=True, timestamp=2000, body=None
    ):
        return SimpleNamespace(
            sender=sender,
            event_id=event_id,
            decrypted=decrypted,
            server_timestamp=timestamp,
            body=body or "!lxmf " + "ab" * 16 + " hello",
            source={"content": {}},
        )

    async def scenario():
        await bridge.matrix_message(room, event(sender="@stranger:host"))
        await bridge.matrix_message(room, event(sender="@bot:host"))
        await bridge.matrix_message(room, event(timestamp=500))
        await bridge.matrix_message(SimpleNamespace(room_id="!other:host"), event())
        assert bridge.store.ready("lxmf") is None
        await bridge.matrix_message(room, event(decrypted=False))
        assert bridge.store.ready("lxmf") is None
        await bridge.matrix_message(
            room, event(event_id="$self", body="!lxmf " + "cd" * 16 + " loop")
        )
        assert bridge.store.ready("lxmf") is None
        await bridge.matrix_message(room, event())
        await bridge.matrix_message(room, event())
        assert bridge.store.ready("lxmf")["body"] == "hello"
        assert (
            bridge.store.counts()["pending"] == 3
        )  # one message and two explanatory notices

    asyncio.run(scenario())


def test_messages_arriving_during_pause_remain_queued(tmp_path):
    config = tmp_path / "credentials.json"
    config.write_text(
        json.dumps(
            {
                "room_id": "!room:host",
                "user_id": "@bot:host",
                "allowed_users": ["@owner:host"],
                "started_at": 1000,
            }
        )
    )
    bridge = MatrixLXMFBridge(config)
    bridge.enabled = False
    bridge.source = SimpleNamespace(hash=bytes.fromhex("cd" * 16))
    room = SimpleNamespace(room_id="!room:host", encrypted=True)
    event = SimpleNamespace(
        sender="@owner:host",
        event_id="$paused",
        decrypted=True,
        server_timestamp=2000,
        body="!lxmf " + "ab" * 16 + " keep me",
        source={"content": {}},
    )
    asyncio.run(bridge.matrix_message(room, event))
    assert bridge.store.ready("lxmf")["body"] == "keep me"


def test_ciphertext_waits_for_keys_without_being_dropped(tmp_path):
    store = BridgeStore(tmp_path / "queue.db")
    store.save_encrypted("$encrypted", {"content": {"ciphertext": "test"}})
    store.save_encrypted("$encrypted", {"content": {"ciphertext": "duplicate"}})
    assert store.counts()["awaiting_keys"] == 1
    rows = store.encrypted_ready()
    assert rows[0][1]["content"]["ciphertext"] == "test"
    assert store.encrypted_ready() == []
    store.remove_encrypted("$encrypted")
    assert store.counts()["awaiting_keys"] == 0
