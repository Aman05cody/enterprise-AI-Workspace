"""Local filesystem object storage adapter."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Optional

from eaw.application.ports.object_storage import ObjectStoragePort
from eaw.domain.common.errors import NotFoundError


class LocalObjectStorage(ObjectStoragePort):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Prevent path traversal
        safe = key.replace("\\", "/").lstrip("/")
        path = (self.root / safe).resolve()
        if not str(path).startswith(str(self.root)):
            raise ValueError("Invalid storage key")
        return path

    def put_object(
        self,
        *,
        key: str,
        body: BinaryIO | bytes,
        content_type: str,
        content_length: Optional[int] = None,
    ) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = body if isinstance(body, bytes) else body.read()
        path.write_bytes(data)
        return key

    def get_object(self, *, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise NotFoundError("File not found in storage")
        return path.read_bytes()

    def delete_object(self, *, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    def exists(self, *, key: str) -> bool:
        return self._path(key).is_file()
