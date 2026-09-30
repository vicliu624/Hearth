"""One OS-backed mutation boundary shared by the server, CLI and recovery jobs."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, contextmanager
from contextvars import ContextVar
import os
from pathlib import Path
import tempfile
import threading


class OperationBusy(RuntimeError):
    pass


_held: ContextVar[dict] = ContextVar("hearth_operation_locks", default={})


def atomic_write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(
                content.encode("utf-8") if isinstance(content, str) else content
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class OperationLock:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()

    @contextmanager
    def hold(self):
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        owner = (threading.get_ident(), task)
        key = str(self.path)
        if _held.get().get(key) == owner:
            yield
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+b") as stream:
            stream.seek(0, os.SEEK_END)
            if not stream.tell():
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise OperationBusy(
                    "Another node operation is in progress; retry when it finishes"
                ) from exc
            token = _held.set({**_held.get(), key: owner})
            try:
                yield
            finally:
                _held.reset(token)
                stream.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(stream, fcntl.LOCK_UN)

    @asynccontextmanager
    async def acquire(self, timeout: float = 30):
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            manager = self.hold()
            try:
                manager.__enter__()
                break
            except OperationBusy:
                if asyncio.get_running_loop().time() >= deadline:
                    raise
                await asyncio.sleep(0.05)
        try:
            yield
        finally:
            manager.__exit__(None, None, None)
