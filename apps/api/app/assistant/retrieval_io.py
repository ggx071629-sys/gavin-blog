from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from typing import TypeVar

T = TypeVar("T")


class RetrievalIO:
    """Loop-owned bounded submission; cancelling a consumer cannot free a live slot."""

    def __init__(self, capacity: int) -> None:
        self._executor = ThreadPoolExecutor(
            max_workers=capacity, thread_name_prefix="assistant-retrieval",
        )
        self._slots = asyncio.Semaphore(capacity)
        self._pending: set[asyncio.Future] = set()
        self._closed = False

    async def run(self, work: Callable[[], T]) -> T:
        if self._closed:
            raise RuntimeError("retrieval IO is closed")
        await self._slots.acquire()
        try:
            if self._closed:
                raise RuntimeError("retrieval IO is closed")
            future = asyncio.get_running_loop().run_in_executor(
                self._executor, copy_context().run, work,
            )
        except BaseException:
            self._slots.release()
            raise
        self._pending.add(future)

        def completed(done: asyncio.Future) -> None:
            self._pending.discard(done)
            self._slots.release()
            # A cancelled consumer no longer awaits the provider exception.
            if not done.cancelled():
                done.exception()

        future.add_done_callback(completed)
        return await asyncio.shield(future)

    async def aclose(self) -> None:
        self._closed = True
        if self._pending:
            await asyncio.shield(asyncio.gather(*self._pending, return_exceptions=True))
        # All submitted work has completed. Never join live workers on the loop.
        self._executor.shutdown(wait=False)
