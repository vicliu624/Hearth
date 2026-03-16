from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable


Job = Callable[[], Awaitable[None]]


class AsyncScheduler:
    def __init__(self) -> None:
        self._tasks: list[asyncio.Task[None]] = []
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def task_names(self) -> list[str]:
        return [task.get_name() for task in self._tasks if not task.done()]

    def add_job(self, name: str, interval_seconds: int, job: Job) -> None:
        async def runner() -> None:
            while self._running:
                await job()
                await asyncio.sleep(interval_seconds)

        self._tasks.append(asyncio.create_task(runner(), name=f"scheduler:{name}"))

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
