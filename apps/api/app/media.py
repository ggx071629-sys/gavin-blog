from __future__ import annotations

import logging
import shutil
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


class MediaStorage(Protocol):
    def write_batch(self, key: str, files: Mapping[str, bytes]) -> None: ...

    def path(self, key: str, name: str) -> Path: ...

    def delete(self, key: str) -> None: ...


@dataclass(frozen=True)
class LocalMediaStorage:
    root: Path

    def _directory(self, key: str) -> Path:
        if len(key) != 32 or not key.isalnum():
            raise ValueError("invalid storage key")
        return self.root.resolve() / key

    @staticmethod
    def _file_path(directory: Path, name: str) -> Path:
        target = (directory / name).resolve()
        if target.parent != directory:
            raise ValueError("invalid media path")
        return target

    def write_batch(self, key: str, files: Mapping[str, bytes]) -> None:
        if not files:
            raise ValueError("media batch cannot be empty")
        directory = self._directory(key)
        directory.parent.mkdir(parents=True, exist_ok=True)
        if directory.exists():
            raise FileExistsError(key)
        staging = directory.parent / f".{key}.{uuid.uuid4().hex}.tmp"
        staging.mkdir()
        published = False
        try:
            for name, data in files.items():
                self._file_path(staging, name).write_bytes(data)
            staging.replace(directory)
            published = True
        finally:
            if not published and staging.exists():
                try:
                    shutil.rmtree(staging)
                except OSError:
                    logger.exception("failed to remove media staging directory %s", staging)

    def path(self, key: str, name: str) -> Path:
        directory = self._directory(key)
        target = self._file_path(directory, name)
        if not target.is_file():
            raise FileNotFoundError(name)
        return target

    def delete(self, key: str) -> None:
        directory = self._directory(key)
        if not directory.exists():
            return
        shutil.rmtree(directory)
