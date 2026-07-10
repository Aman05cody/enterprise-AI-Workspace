"""Object storage port."""

from abc import ABC, abstractmethod
from typing import BinaryIO, Optional


class ObjectStoragePort(ABC):
    @abstractmethod
    def put_object(
        self,
        *,
        key: str,
        body: BinaryIO | bytes,
        content_type: str,
        content_length: Optional[int] = None,
    ) -> str:
        """Store object; return storage key."""

    @abstractmethod
    def get_object(self, *, key: str) -> bytes:
        """Read full object bytes."""

    @abstractmethod
    def delete_object(self, *, key: str) -> None:
        """Delete object if present (idempotent)."""

    @abstractmethod
    def exists(self, *, key: str) -> bool:
        ...
