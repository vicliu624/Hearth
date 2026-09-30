"""Encrypted Matrix/LXMF text bridge. Run as a separate supervised process."""

from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import time
import tomllib

from hearth.bridges.store import BridgeStore, MAX_TEXT_BYTES, parse_message
from hearth.core.operations import atomic_write

HELP = (
    "Hearth ↔ LXMF 桥接\n"
    "主动发送：!lxmf <32位LXMF地址> <消息>\n"
    "回复一条来自 LXMF 的消息，可直接回信给该用户。\n"
    "!address 查看本机器人的 LXMF 地址；!help 查看说明。\n"
    "目前转发文字。机器人在本机解密并重新加密转发；不会发布地理位置。"
)


class MatrixLXMFBridge:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = json.loads(config_path.read_text())
        self.root = Path(self.config.get("data_dir", config_path.parent))
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.store = BridgeStore(self.root / "queue.sqlite3")
        self.store.recover()
        self.client = None
        self.router = None
        self.source = None
        self.last_sync = 0.0
        self.error = None
        self.enabled = True
        self.inflight = set()
        self.loop = None
        import psutil

        self.process_started_at = psutil.Process().create_time()

    def enabled_in_config(self):
        path = self.config.get("hearth_config")
        if not path:
            return True
        try:
            settings = tomllib.loads(Path(path).read_text())
            return any(
                p.get("name") == "matrix_bridge" and p.get("enabled")
                for p in settings.get("plugins", [])
            )
        except (OSError, ValueError):
            return False

    def reticulum_online(self):
        if self.source is None:
            return False
        import RNS

        return any(
            getattr(interface, "online", False)
            for interface in RNS.Transport.interfaces
        )

    def state(self, state=None):
        payload = {
            "pid": os.getpid(),
            "process_started_at": self.process_started_at,
            "updated_at": time.time(),
            "status": state
            or (
                "running"
                if self.enabled
                and time.time() - self.last_sync < 60
                and self.reticulum_online()
                and not str(self.error or "").startswith("matrix_sync")
                else "paused"
                if not self.enabled
                else "connecting"
            ),
            "room_id": self.config["room_id"],
            "bot_user": self.config["user_id"],
            "lxmf_address": self.source.hash.hex() if self.source else None,
            "encrypted": True,
            "last_sync": self.last_sync,
            "error": self.error,
            "queue": self.store.counts(),
        }
        atomic_write(self.root / "status.json", json.dumps(payload))

    def notify(self, key, text, peer=""):
        self.store.enqueue("notice:" + key, "matrix", peer, text)

    async def matrix_message(self, room, event):
        if room.room_id != self.config["room_id"]:
            return
        if (
            event.sender not in self.config["allowed_users"]
            or event.sender == self.config["user_id"]
        ):
            return
        if event.server_timestamp < self.config["started_at"]:
            return
        if not room.encrypted or not getattr(event, "decrypted", False):
            self.notify(event.event_id, "请在加密房间中发送加密消息；未转发明文消息。")
            return
        content = event.source.get("content", {})
        reply = content.get("m.relates_to", {}).get("m.in_reply_to", {}).get("event_id")
        peer = self.store.peer_for_reply(reply) if reply else None
        if event.body.strip() in ("!help", "!address"):
            self.notify(event.event_id, HELP + "\nLXMF: " + self.source.hash.hex())
            return
        try:
            parsed = parse_message(event.body, peer)
        except ValueError:
            self.notify(event.event_id, "消息太长：最多 8192 字节 UTF-8 文字。")
            return
        if not parsed:
            self.notify(
                event.event_id,
                "未发送。请回复来自 LXMF 的消息，或使用 !lxmf <地址> <消息>。",
            )
            return
        recipient, text = parsed
        if recipient == self.source.hash.hex():
            self.notify(event.event_id, "不能发送给桥接自身，以免形成循环。")
            return
        self.store.enqueue("mx:" + event.event_id, "lxmf", recipient, text)

    async def undecrypted(self, room, event):
        if (
            room.room_id != self.config["room_id"]
            or event.sender not in self.config["allowed_users"]
            or event.server_timestamp < self.config["started_at"]
        ):
            return
        self.store.save_encrypted(
            event.event_id, {**event.source, "room_id": room.room_id}
        )
        try:
            await self.client.request_room_key(event)
        except Exception:
            pass  # Durable ciphertext remains queued until the sender shares its key.

    async def retry_decryption(self):
        from nio import Event, RoomMessageText

        for event_id, payload in self.store.encrypted_ready():
            try:
                event = self.client.decrypt_event(Event.parse_event(payload))
                if isinstance(event, RoomMessageText):
                    await self.matrix_message(
                        self.client.rooms[self.config["room_id"]], event
                    )
                    self.store.remove_encrypted(event_id)
            except Exception:
                continue

    def inbound_lxmf(self, message):
        if message.source_hash == self.source.hash:
            return
        if not message.signature_validated:
            return
        raw = message.content
        if not raw or len(raw) > MAX_TEXT_BYTES:
            return
        peer = message.source_hash.hex()
        title = message.title.decode("utf-8", errors="replace") if message.title else ""
        text = raw.decode("utf-8", errors="replace")
        body = f"[LXMF {peer}]\n" + (title + "\n" if title else "") + text
        self.store.enqueue("lx:" + message.hash.hex(), "matrix", peer, body)

    def attach_reticulum(self):
        import RNS
        import LXMF

        self.rns = RNS.Reticulum(
            configdir=self.config["reticulum_config"],
            require_shared_instance=True,
            loglevel=1,
        )
        if not self.rns.is_connected_to_shared_instance:
            raise RuntimeError("Existing shared Reticulum instance required")
        identity_path = self.root / "identity"
        identity = (
            RNS.Identity.from_file(str(identity_path))
            if identity_path.exists()
            else RNS.Identity()
        )
        if not identity_path.exists():
            identity.to_file(str(identity_path))
        if identity is None:
            raise RuntimeError("Cannot load persistent LXMF identity")
        self.router = LXMF.LXMRouter(
            storagepath=str(self.root / "lxmf"), autopeer=False
        )
        self.source = self.router.register_delivery_identity(
            identity, display_name="Hearth Matrix bridge", stamp_cost=8
        )
        self.router.register_delivery_callback(self.inbound_lxmf)
        # Application delivery announce: no discoverable interface or geographic data.
        self.router.announce(self.source.hash)

    async def send_matrix(self, job):
        from nio import RoomSendResponse

        if not self.store.claim(job["id"]):
            return
        try:
            room = self.client.rooms.get(self.config["room_id"])
            if not room or not room.encrypted:
                raise RuntimeError("Encrypted room is required")
            result = await self.client.room_send(
                self.config["room_id"],
                "m.room.message",
                {"msgtype": "m.text", "body": job["body"]},
                tx_id=hashlib.sha256(job["id"].encode()).hexdigest(),
                ignore_unverified_devices=True,
            )
            if not isinstance(result, RoomSendResponse):
                raise RuntimeError("Matrix send rejected")
            self.store.complete(job["id"], result.event_id)
        except Exception as error:
            self.store.retry(job["id"], type(error).__name__)
            self.error = "matrix_send_failed"

    async def send_lxmf(self, job):
        import RNS
        import LXMF

        if not self.store.claim(job["id"]):
            return
        try:
            recipient = bytes.fromhex(job["peer"])
            if not RNS.Transport.has_path(recipient):
                RNS.Transport.request_path(recipient)
                for _ in range(40):
                    await asyncio.sleep(0.5)
                    if RNS.Transport.has_path(recipient):
                        break
            if not RNS.Transport.has_path(recipient):
                raise RuntimeError("No path")
            identity = RNS.Identity.recall(recipient)
            if identity is None:
                raise RuntimeError("Unknown recipient identity")
            destination = RNS.Destination(
                identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                "lxmf",
                "delivery",
            )
            message = LXMF.LXMessage(
                destination,
                self.source,
                job["body"],
                title="Matrix",
                desired_method=LXMF.LXMessage.DIRECT,
            )
            # Stable timestamp keeps the LXMF message ID stable across retries/restarts.
            message.timestamp = job["created"]

            def delivered(_):
                self.store.complete(job["id"])
                self.notify("delivered:" + job["id"], f"已送达 LXMF {job['peer']}。")
                self.inflight.discard(job["id"])

            def failed(_):
                self.store.retry(job["id"], "lxmf_delivery_failed")
                self.inflight.discard(job["id"])

            message.register_delivery_callback(delivered)
            message.register_failed_callback(failed)
            self.inflight.add(job["id"])
            self.router.handle_outbound(message)
        except Exception as error:
            self.store.retry(job["id"], type(error).__name__)
            self.notify(
                "retry:" + job["id"],
                "暂未送达 LXMF；桥接将自动重试。地址：" + job["peer"],
            )
            self.error = "lxmf_delivery_pending"

    async def queue_loop(self):
        while True:
            self.enabled = self.enabled_in_config()
            self.state()
            if self.enabled and self.last_sync and time.time() - self.last_sync < 60:
                job = self.store.ready("matrix")
                if job:
                    await self.send_matrix(job)
                if not self.inflight and self.reticulum_online():
                    job = self.store.ready("lxmf")
                    if job:
                        await self.send_lxmf(job)
            await asyncio.sleep(1)

    async def sync_loop(self):
        from nio import SyncResponse, RoomMessageText, MegolmEvent

        since = self.store.get("since")
        sync_filter = {
            "room": {
                "rooms": [self.config["room_id"]],
                "timeline": {"limit": 100},
                "state": {"lazy_load_members": False},
            },
            "presence": {"types": []},
        }
        while True:
            if not self.enabled:
                await asyncio.sleep(2)
                continue
            try:
                previous_time = self.store.get(
                    "last_matrix_time", self.config["started_at"]
                )
                response = await self.client.sync(
                    timeout=10000,
                    since=since,
                    sync_filter=sync_filter,
                    full_state=not self.last_sync,
                )
                if not isinstance(response, SyncResponse):
                    raise RuntimeError("Matrix sync failed")
                joined = response.rooms.join.get(self.config["room_id"])
                if joined and joined.timeline.limited:
                    token = joined.timeline.prev_batch
                    done = False
                    for _ in range(100):
                        page = await self.client.room_messages(
                            self.config["room_id"], start=token, limit=100
                        )
                        if not hasattr(page, "chunk"):
                            raise RuntimeError("History recovery failed")
                        for event in reversed(page.chunk):
                            if getattr(
                                event, "server_timestamp", 0
                            ) > previous_time and isinstance(event, RoomMessageText):
                                await self.matrix_message(
                                    self.client.rooms[self.config["room_id"]], event
                                )
                            elif getattr(
                                event, "server_timestamp", 0
                            ) > previous_time and isinstance(event, MegolmEvent):
                                await self.undecrypted(
                                    self.client.rooms[self.config["room_id"]], event
                                )
                        if (
                            not page.chunk
                            or min(
                                getattr(e, "server_timestamp", 0) for e in page.chunk
                            )
                            <= previous_time
                        ):
                            done = True
                            break
                        if page.end == token:
                            done = True
                            break
                        token = page.end
                    if not done:
                        raise RuntimeError("History gap exceeds recovery limit")
                if self.client.should_upload_keys:
                    await self.client.keys_upload()
                if self.client.should_query_keys:
                    await self.client.keys_query()
                if self.client.should_claim_keys:
                    await self.client.keys_claim(
                        self.client.get_users_for_key_claiming()
                    )
                await self.client.send_to_device_messages()
                room = self.client.rooms.get(self.config["room_id"])
                if not room or not room.encrypted:
                    raise RuntimeError("Bridge must remain joined to an encrypted room")
                await self.retry_decryption()
                since = response.next_batch
                self.store.set("since", since)
                if joined and joined.timeline.events:
                    self.store.set(
                        "last_matrix_time",
                        max(
                            previous_time,
                            max(
                                getattr(e, "server_timestamp", 0)
                                for e in joined.timeline.events
                            ),
                        ),
                    )
                self.last_sync = time.time()
                self.error = None
            except Exception as error:
                self.error = "matrix_sync_" + type(error).__name__
                self.state("error")
                await asyncio.sleep(5)

    async def run(self):
        from nio import AsyncClient, AsyncClientConfig, RoomMessageText, MegolmEvent

        self.loop = asyncio.get_running_loop()
        self.attach_reticulum()
        store_path = self.root / "matrix-keys"
        store_path.mkdir(exist_ok=True, mode=0o700)
        config = AsyncClientConfig(
            encryption_enabled=True,
            store_sync_tokens=False,
            max_limit_exceeded=3,
            max_timeouts=3,
        )
        self.client = AsyncClient(
            self.config["homeserver"],
            self.config["user_id"],
            device_id=self.config["device_id"],
            store_path=str(store_path),
            config=config,
        )
        self.client.restore_login(
            self.config["user_id"],
            self.config["device_id"],
            self.config["access_token"],
        )
        self.client.add_event_callback(self.matrix_message, RoomMessageText)
        self.client.add_event_callback(self.undecrypted, MegolmEvent)
        self.notify("welcome", HELP + "\n本机器人 LXMF 地址：" + self.source.hash.hex())
        try:
            await asyncio.gather(self.sync_loop(), self.queue_loop())
        finally:
            self.state("stopped")
            await self.client.close()


def main():
    import fcntl

    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    lock = (args.config.parent / "worker.lock").open("w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    asyncio.run(MatrixLXMFBridge(args.config).run())


if __name__ == "__main__":
    main()
