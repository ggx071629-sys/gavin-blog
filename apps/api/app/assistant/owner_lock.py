from __future__ import annotations

import os
from io import BufferedRandom
from pathlib import Path
from types import TracebackType

from .errors import AssistantOwnerLockError


class ExclusiveFileLock:
    """Cross-process exclusive lock shared by API startup and provisioning."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._handle: BufferedRandom | None = None
        self._fd: int | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_BINARY"):
            flags |= os.O_BINARY
        fd = os.open(self.path, flags, 0o644)
        handle = os.fdopen(fd, "r+b")
        try:
            handle.seek(0)
            if handle.read(1) == b"":
                handle.seek(0)
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            _lock_exclusive(handle)
        except OSError as exc:
            handle.close()
            raise AssistantOwnerLockError(
                "assistant_runtime owner lock is held by another process"
            ) from exc
        self._fd = fd
        self._handle = handle

    def release(self) -> None:
        handle = self._handle
        if handle is None:
            return
        try:
            handle.seek(0)
            _unlock(handle)
        except OSError:
            pass
        finally:
            handle.close()
            self._handle = None
            self._fd = None

    def held(self) -> bool:
        return self._handle is not None

    def __enter__(self) -> ExclusiveFileLock:
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.release()


def lock_path_for(runtime_path: Path) -> Path:
    return runtime_path.with_name(runtime_path.name + ".owner.lock")


def _lock_exclusive(handle) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        return
    import fcntl

    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
